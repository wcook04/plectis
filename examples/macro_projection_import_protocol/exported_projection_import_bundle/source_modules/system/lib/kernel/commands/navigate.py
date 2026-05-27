"""
[PURPOSE]
- Teleology: Navigate and phase-lifecycle commands for the kernel CLI -- frontier,
  phase management, observe-plan compilation, raw-seed/synth-seed sync, orientation,
  and the full pulse self-assessment surface.
- Mechanism: Each cmd_* function delegates to KernelNavigation for deterministic
  context compilation or directly reads/writes phase-family artifacts on disk.

[INTERFACE]
- Exports: cmd_info, cmd_pulse, cmd_agent_wake_packet, cmd_agent_recent_activity, cmd_frontier, cmd_recent_obsidian, cmd_working_set, cmd_bootstrap_task, cmd_extract_note, cmd_extract_note_structure, cmd_set_focus, cmd_phase_demote_stale_focus, cmd_add_phase, cmd_new_family, cmd_new_phase, cmd_activate_phase, cmd_sync_raw_seed, cmd_resolve_raw_seed_ref, cmd_annotate_raw_seed, cmd_sync_synth, cmd_close_phase, cmd_add_workstream, cmd_execution_map, cmd_map, cmd_stale, cmd_doc_gaps, cmd_obsidian_family, cmd_paths, cmd_atlas, cmd_orient, cmd_docs_route, cmd_skill_find, cmd_command_card, cmd_paper_module, cmd_paper_module_coverage, cmd_paper_module_route, cmd_facts, cmd_fact, cmd_fact_audit, cmd_paper_module_facts, cmd_process_summary, cmd_system_view, cmd_list_docs_route_focus, cmd_set_docs_route_focus, cmd_orient_task, cmd_context, cmd_trace, cmd_doctrine, cmd_doctrine_runtime, cmd_locate, cmd_run_context, cmd_data_roots, cmd_lens, cmd_plan_phase, cmd_phase, cmd_phase_step, cmd_phase_assimilate, cmd_phase_resume, cmd_closeout_audit, cmd_phase_harbor, cmd_phase_deposit, cmd_phase_dock, cmd_phase_begin, cmd_ingest_phase_deposit, cmd_phase_observe, cmd_campaign_loop, cmd_plan_batch, cmd_plan_sync, cmd_impact, cmd_compile_batch, cmd_compile, cmd_verify
  cmd_doctrine_triple,
- Private helpers: _load_kernel_skills, _path_status, _active_plan_summary, _skill_payload, _compiled_bundle_count, _resolve_phase_session_manifest, _phase_command_token, _phase_dock_command, _phase_begin_status, _git_scope_summary, _resolve_write_packet_path, _pulse_age_label, _pulse_frontier_anchor, _pulse_latest_saved_plan, _pulse_latest_runtime, _pulse_doctrine_summary, _pulse_workspace_summary, _pulse_recommended_actions, _pulse_snapshot, _focus_snapshot, _load_markdown_frontmatter, _update_markdown_frontmatter, _current_default_phase_stub, _current_default_plan_stub, _default_promotion_payload, _attach_scaffold_default_promotion, _normalize_new_phase_number, _normalize_new_phase_title, _new_phase_id, _new_phase_dir_name, _load_json_file, _phase_payload_from_navigation_dict, _family_marker_aliases, _resolve_phase_family_entry, _discover_phase_family_dir, _normalize_new_family_title, _new_family_dir_name, _normalize_new_family_parent_path, _normalize_new_phase_parent_path, _resolve_phase_entry_for_lifecycle, _resolve_family_entry_for_raw_seed, _family_file_from_entry, _phase_scaffold_path_for_entry, _phase_file_from_entry, _compile_phase_observe_plan_payload, _write_next_pass_plan_payload, _run_observe_plan_sync, _rewrite_verify_command, _resolve_doc_registry_path, _resolve_raw_seed_and_index_for_family, _load_mission_params

[FLOW]
- kernel.py dispatch calls the relevant cmd_* function based on CLI flags.
- Navigation commands build a NavigationResult via KernelNavigation and emit JSON.
- Phase lifecycle commands (new/sync/close/activate) read and mutate family artifacts.
- Observe-plan compilation (phase-observe, campaign-loop) generates observe_plan.json files.

[DEPENDENCIES]
- system.lib.kernel.state: REPO_ROOT, KERNEL_VERSION, and all observe/apply/codex path constants
- system.lib.kernel.output: emit_json, emit_json_with_code, emit_navigation, navigation_output_full
- system.lib.kernel.helpers: safe_load_json, parse_iso_datetime
- system.lib.kernel_navigation: KernelNavigation, NavigationResult
- kernel (lazy, temporary): shared helpers still in kernel.py (_validate_observe_payload, etc.)
- system.lib.phase_scaffold, system.lib.raw_seed_registry, system.lib.observe_apply_contracts,
  system.lib.phase_harbor, system.lib.phase_dock, system.lib.phase_activation (all direct imports)

[CONSTRAINTS]
- Navigation commands are read-only.
- Phase-lifecycle commands mutate disk only when --live is passed.
- Fails: Returns 1 on missing artifacts, unresolvable tokens, or malformed input.
- When-needed: Open when the kernel CLI task is about semantic navigation, phase lifecycle, docs-route routing, pulse state, or observe-plan compilation rather than apply or run inspection.
- Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_phase.py; system/lib/kernel_nav_lens.py; kernel.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import io
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator, Mapping, Sequence

from system.lib.kernel import state
from system.lib.kernel.output import (
    emit_json,
    emit_json_with_code,
    emit_navigation,
    navigation_output_full,
)
from system.lib.kernel.helpers import (
    parse_iso_datetime,
    read_runs_dir_value,
    safe_load_json,
    safe_load_json_with_error,
)
from system.lib.kernel.pulse_cache import (
    PULSE_CLOSEOUT_AUDIT_FRESHNESS_POLICY,
    PULSE_CLOSEOUT_AUDIT_INPUT_PATHS,
    PULSE_CLOSEOUT_AUDIT_KEY,
    PULSE_CLOSEOUT_AUDIT_NODE_ID,
    PULSE_PROVIDER_PLANE_LIVENESS_FRESHNESS_POLICY,
    PULSE_PROVIDER_PLANE_LIVENESS_KEY,
    PULSE_PROVIDER_PLANE_LIVENESS_NODE_ID,
    refresh_provider_plane_liveness_cache,
)
from system.lib.kernel_navigation import KernelNavigation, NavigationResult, normalize_repo_kernel_command
from system.lib.kernel_navigation import _should_skip_repo_scan_dir
from system.lib.navigation_trace import record_attention_event, record_navigation_result
from system.lib.markdown_routing import parse_frontmatter, render_markdown_document
from system.lib.work_ledger_commands import WORK_LEDGER_SEED_SPEED_COMMAND
from system.lib.derived_fact_hologram import (
    AUDIT_PATH as FACT_AUDIT_PATH,
    LEDGER_PATH as FACT_LEDGER_PATH,
    NAVIGATION_CACHE_PATH as FACT_NAVIGATION_CACHE_PATH,
    build_fact_hologram,
    fact_by_id,
    filter_facts,
    search_facts,
)
from system.lib.agent_entrypoint_audit import (
    AUDIT_PATH as AGENT_ENTRYPOINT_AUDIT_PATH,
    AXIS_REGISTRY_PATH as AGENT_ENTRYPOINT_AXIS_REGISTRY_PATH,
    ENTRYPOINT_REGISTRY_PATH as AGENT_ENTRYPOINT_REGISTRY_PATH,
    PER_ENTRYPOINT_PATH as AGENT_ENTRYPOINT_PER_ENTRYPOINT_PATH,
    SUMMARY_PATH as AGENT_ENTRYPOINT_SUMMARY_PATH,
    build_agent_entrypoint_audit,
    select_entrypoint,
    summarize_entrypoints,
)
from system.lib.agent_execution_trace import (
    AUDIT_PATH as PROCESS_AUDIT_PATH,
    LEDGER_PATH as PROCESS_LEDGER_PATH,
    NAVIGATION_CACHE_PATH as PROCESS_NAVIGATION_CACHE_PATH,
    PATTERNS_PATH as PROCESS_PATTERNS_PATH,
    SUMMARY_PATH as PROCESS_SUMMARY_PATH,
    TRACE_RULES_PATH as PROCESS_TRACE_RULES_PATH,
    build_agent_execution_trace,
    build_process_trace_route_packet,
    compare_agents,
    select_session,
)
from system.lib.raw_seed_projection_coverage import (
    build_raw_seed_projection_coverage,
    select_theme,
)

# ---------------------------------------------------------------------------
# External library imports (used by phase-lifecycle and observe commands)
# ---------------------------------------------------------------------------
from system.lib.codex_paths import canonicalize_write_path
from system.lib.observe_assets import observe_asset_paths
from system.lib.observe_apply_contracts import (
    OBSERVE_APPLY_AUTHORITY_INDEX_PATH,
    OBSERVE_APPLY_STANDARD_PATHS,
    BRIDGE_COMPILABLE_EXECUTION_MODES,
    PENDING_SYNTH_AUTHORING,
    PHASE_SCAFFOLD_VERSION,
    SYNCED_SYNTH_AUTHORING,
    build_phase_closeout_payload,
    build_subphase_close_promotion_entry,
    canonical_json_text,
    normalize_assimilation_targets,
    normalize_synth_payload,
    render_synth_seed_markdown,
    validate_synth_seed_payload,
)
from system.lib.observe_sessions import (
    load_session_candidates,
    normalize_phase_token,
    session_resolution_sort_key,
)
from system.lib.autonomous_seed import (
    default_autonomous_seed_path,
    validate_seed_heartbeat_references,
    write_autonomous_seed,
)
from system.lib.continuation_packet import (
    build_continuation_packet,
    write_continuation_packet,
)
from system.lib.phase_activation import load_explicit_active_phase, preview_or_apply_family_activation
from system.lib.phase_dock import preflight_phase_dock, run_phase_dock
from system.lib.phase_harbor import (
    bootstrap_phase_harbor,
    ingest_phase_deposit_response,
)
from system.lib.phase_memory import default_phase_memory_path, write_phase_memory
from system.lib.phase_scaffold import (
    PHASE_FAMILY_MARKER_FILENAME,
    execute_phase_family_scaffold_spec,
    execute_phase_scaffold,
    execute_phase_scaffold_spec,
)
from system.lib.raw_seed_registry import (
    agent_seed_json_path_for_family,
    agent_seed_markdown_path_for_family,
    agent_seed_snapshot_path_for_family,
    annotate_raw_seed_payload,
    build_agent_seed_payload_for_family,
    build_raw_seed_payload,
    build_raw_seed_payload_for_family,
    load_raw_seed_payload,
    project_raw_seed_index_slice,
    raw_seed_index_path_for_family,
    raw_seed_json_path_for_family,
    raw_seed_markdown_path_for_family,
    raw_seed_principles_path_for_family,
    raw_seed_snapshot_path_for_family,
    raw_seed_term_ledger_path_for_family,
    render_agent_seed_markdown,
    render_raw_seed_markdown,
    resolve_raw_seed_ref,
)
from system.lib.synth_seed_delta_merge import apply_synth_seed_delta
from system.lib.standards_registry import STANDARDS_REGISTRY_PATH
from system.lib.system_vocabulary import list_system_terms, render_system_term
from system.lib.kind_atlas import build_kind_atlas
from system.lib.kind_band_contract_audit import build_kind_band_contract_audit
from system.lib.navigation_surface_contracts import (
    ATLAS_PROJECTION,
    CONTROL_ENTRY,
    DEBUG_TRACE,
    DRILLDOWN,
    ENTRY_REPLACEMENT,
    atlas_projection_contract,
    debug_trace_block,
    debug_trace_contract,
    surface_contract,
)

from system.lib.navigation_context_rosetta import build_navigation_context_rosetta
from system.lib.standard_option_surface import build_option_surface
from system.lib.campaign_router import (
    CAMPAIGN_ONLY_LANE_IDS,
    PROVIDER_METABOLISM_LANE_ID,
    build_campaign_packet,
    build_campaign_write_guard,
    classify_campaign_lane,
)
from system.lib.campaign_state_transition import (
    CampaignTransitionError,
    register_campaign_dispatch,
    sync_campaign_state_from_receipt,
)
from system.lib.hidden_substrate_reconciliation import (
    build_hidden_substrate_affordance_reconciliation,
    write_hidden_substrate_affordance_reconciliation,
)
from system.lib.phase_task_alignment import (
    build_phase_task_alignment,
    navigation_enforcement_residual_lane,
    phase_residual_lane_catalog,
)
from system.lib.command_output_projection import (
    command_projection,
    make_currentness,
    make_omission_receipt,
    make_row_id,
    make_validation_contract,
    row_band_unavailable,
)
from system.lib.command_output_audit import (
    build_command_output_duplication_audit,
    build_command_output_projection_audit,
)
from system.lib.observe_runtime import (
    grouped_runtime_status_payload as _lib_grouped_runtime_status_payload,
)
from system.lib import seed_pipeline_controller as phase_step_controller
from system.lib.utils import resolve_runs_dir
from system.lib.workstream_scaffold import execute_workstream_scaffold

NAVIGATION_METABOLISM_TIMEOUT_ENV = "AIW_NAVIGATION_METABOLISM_TIMEOUT_MS"
NAVIGATION_METABOLISM_QUICK_TIMEOUT_MS = 15000
NAVIGATION_METABOLISM_TIMEOUT_WORK_ITEM_ID = "lifecycle-navigation-metabolism-budget-probe-timeout"


# ---------------------------------------------------------------------------
# Lazy imports from kernel.py for shared helpers not yet extracted.
# These create a temporary reverse dependency that will be removed when
# the remaining command groups are extracted.
# ---------------------------------------------------------------------------

def _kernel_validate_observe_payload(*args: Any, **kwargs: Any) -> Any:
    from kernel import _validate_observe_payload
    return _validate_observe_payload(*args, **kwargs)


def _kernel_observe_launch_profile_default(*args: Any, **kwargs: Any) -> Any:
    from kernel import _observe_launch_profile_default
    return _observe_launch_profile_default(*args, **kwargs)


def _kernel_observe_runtime_kind(*args: Any, **kwargs: Any) -> Any:
    from kernel import _observe_runtime_kind
    return _observe_runtime_kind(*args, **kwargs)


def _kernel_load_session_manifest_payload(*args: Any, **kwargs: Any) -> Any:
    from kernel import _load_session_manifest_payload
    return _load_session_manifest_payload(*args, **kwargs)


def _kernel_resolve_write_plan_path(*args: Any, **kwargs: Any) -> Any:
    from kernel import _resolve_write_plan_path
    return _resolve_write_plan_path(*args, **kwargs)


def _kernel_truncate_text(*args: Any, **kwargs: Any) -> Any:
    from kernel import _truncate_text
    return _truncate_text(*args, **kwargs)


def _kernel_run_bridge_preflight(*args: Any, **kwargs: Any) -> Any:
    from kernel import _run_bridge_preflight
    return _run_bridge_preflight(*args, **kwargs)


def _kernel_summarize_observe_plan_payload(*args: Any, **kwargs: Any) -> Any:
    from kernel import _summarize_observe_plan_payload
    return _summarize_observe_plan_payload(*args, **kwargs)


def _kernel_resolve_session_manifest(*args: Any, **kwargs: Any) -> Any:
    from kernel import _resolve_session_manifest
    return _resolve_session_manifest(*args, **kwargs)


def _kernel_repo_root_resolved() -> Path:
    return state.REPO_ROOT.resolve()


def _kernel_coerce_bridge_workers_arg(*args: Any, **kwargs: Any) -> Any:
    from kernel import _coerce_bridge_workers_arg
    return _coerce_bridge_workers_arg(*args, **kwargs)


def _kernel_safe_read_text(*args: Any, **kwargs: Any) -> Any:
    from kernel import _safe_read_text
    return _safe_read_text(*args, **kwargs)


def _kernel_normalize_launch_profile(*args: Any, **kwargs: Any) -> Any:
    from kernel import _normalize_launch_profile
    return _normalize_launch_profile(*args, **kwargs)


def _kernel_build_next_pass_plan_payload(*args: Any, **kwargs: Any) -> Any:
    from kernel import _build_next_pass_plan_payload
    return _build_next_pass_plan_payload(*args, **kwargs)


def _kernel_repo_venv_python() -> Path:
    from kernel import _repo_venv_python
    return _repo_venv_python()


# ---------------------------------------------------------------------------
# Private helpers (used exclusively by commands in this module)
# ---------------------------------------------------------------------------


def _load_kernel_skills() -> list[dict]:
    """Load kernel skill definitions from schema, if present."""
    if not state.KERNEL_SKILLS_SCHEMA.exists():
        return []
    try:
        payload = json.loads(state.KERNEL_SKILLS_SCHEMA.read_text(encoding="utf-8"))
    except Exception:
        return []
    skills = payload.get("skills", [])
    if not isinstance(skills, list):
        return []
    return [s for s in skills if isinstance(s, dict)]


def _skill_registry_payload() -> dict[str, Any]:
    path = state.REPO_ROOT / "codex/doctrine/skills/skill_registry.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


COMMAND_CARD_REGISTRY_REL = "codex/doctrine/command_cards/agent_movement.json"


def _repo_root_for_static_registry() -> Path:
    repo_root = getattr(state, "REPO_ROOT", None)
    if isinstance(repo_root, Path):
        return repo_root
    return Path(__file__).resolve().parents[4]


def _command_card_registry_path() -> Path:
    return _repo_root_for_static_registry() / COMMAND_CARD_REGISTRY_REL


def _command_card_registry_payload() -> dict[str, Any]:
    path = _command_card_registry_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _query_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.casefold()) if token}


def _skill_search_text(skill: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("id", "title", "kind", "file", "description"):
        chunks.append(str(skill.get(key) or ""))
    for item in skill.get("triggers") or []:
        chunks.append(str(item or ""))
    context_pack_anchors = skill.get("context_pack_anchors")
    if isinstance(context_pack_anchors, Mapping):
        for item in context_pack_anchors.get("trigger_phrases") or []:
            chunks.append(str(item or ""))
    holographic = skill.get("holographic")
    if isinstance(holographic, Mapping):
        chunks.extend(str(value or "") for value in holographic.values())
    compression_passport = skill.get("compression_passport")
    if isinstance(compression_passport, Mapping):
        for item in compression_passport.get("cluster_keys") or []:
            chunks.append(str(item or ""))
    agent_surface = skill.get("agent_surface")
    if isinstance(agent_surface, Mapping):
        chunks.extend(str(value or "") for value in agent_surface.values())
    return " ".join(chunks)


def build_skill_find_payload(query: str, *, limit: int = 8) -> dict[str, Any]:
    """Return explicit-debug skill-registry matches without forcing raw JSON reads."""
    raw = str(query or "").strip()
    if not raw:
        raise ValueError("skill-find requires a query")
    registry = _skill_registry_payload()
    query_lower = raw.casefold()
    normalized_query = re.sub(r"[^a-z0-9]+", " ", query_lower).strip()
    query_tokens = _query_tokens(raw)

    matches: list[dict[str, Any]] = []
    for family in registry.get("families") or []:
        if not isinstance(family, Mapping):
            continue
        family_id = str(family.get("family_id") or "").strip()
        family_title = str(family.get("title") or "").strip()
        for skill in family.get("skills") or []:
            if not isinstance(skill, Mapping):
                continue
            if str(skill.get("status") or "active") != "active":
                continue
            skill_id = str(skill.get("id") or "").strip()
            title = str(skill.get("title") or "").strip()
            file_path = str(skill.get("file") or "").strip()
            searchable = _skill_search_text(skill)
            searchable_lower = searchable.casefold()
            searchable_norm = re.sub(r"[^a-z0-9]+", " ", searchable_lower).strip()
            skill_tokens = _query_tokens(searchable)

            score = 0
            reasons: list[str] = []
            if query_lower == skill_id.casefold():
                score += 1800
                reasons.append(f"id_exact:{skill_id}")
            elif query_lower.replace(" ", "_") == skill_id.casefold():
                score += 1650
                reasons.append(f"id_normalized:{skill_id}")
            if title and query_lower == title.casefold():
                score += 1500
                reasons.append(f"title_exact:{title}")
            elif title and normalized_query and normalized_query in re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip():
                score += 800
                reasons.append(f"title_contains:{title}")
            if normalized_query and normalized_query in searchable_norm:
                score += 520
                reasons.append("phrase_contains")
            overlap = sorted(query_tokens & skill_tokens)
            if overlap:
                score += len(overlap) * 120
                reasons.extend([f"token_overlap:{token}" for token in overlap[:5]])
            if score <= 0:
                continue
            matches.append(
                {
                    "id": skill_id,
                    "title": title,
                    "family_id": family_id,
                    "family_title": family_title,
                    "file": file_path,
                    "description": str(skill.get("description") or "").strip(),
                    "score": score,
                    "matched_on": reasons,
                    "entry": ((skill.get("agent_surface") or {}).get("entry") if isinstance(skill.get("agent_surface"), Mapping) else None),
                }
            )
    matches.sort(key=lambda item: (int(item.get("score") or 0), str(item.get("id") or "")), reverse=True)
    return {
        "kind": "kernel.navigate.skill_find",
        "schema_version": "skill_find_debug_trace_v1",
        "surface_role": DEBUG_TRACE,
        "first_contact_allowed": False,
        "debug": True,
        "query": raw,
        "registry_path": "codex/doctrine/skills/skill_registry.json",
        "matches": matches[:limit],
        "match_count": len(matches),
        "surface_contract": debug_trace_contract(
            surface_id="skill_find",
            command="./repo-python kernel.py --skill-find",
            query=raw,
        ),
        "next": [
            {
                "command": "./repo-python kernel.py --row skills:<skill_id> --band card",
                "reason": "Open a selected stable skill id as a drilldown, not as a broad search result.",
            }
        ],
    }


def _command_card_search_text(card: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    for key in (
        "id",
        "command",
        "use_when",
        "returns",
        "avoid_when",
        "cost_class",
        "owning_skill",
    ):
        chunks.append(str(card.get(key) or ""))
    for key in ("usual_next_commands", "route_aliases", "tests"):
        raw_items = card.get(key)
        if isinstance(raw_items, Sequence) and not isinstance(raw_items, (str, bytes)):
            chunks.extend(str(item or "") for item in raw_items)
    return " ".join(chunks)


def _command_card_score(card: Mapping[str, Any], raw: str) -> tuple[int, list[str]]:
    query_lower = raw.casefold()
    normalized_query = re.sub(r"[^a-z0-9]+", " ", query_lower).strip()
    query_tokenized = query_lower.replace("-", "_").replace(" ", "_")
    query_tokens = _query_tokens(raw)
    card_id = str(card.get("id") or "").strip()
    command = str(card.get("command") or "").strip()
    aliases = [
        str(item or "").strip()
        for item in card.get("route_aliases") or []
        if str(item or "").strip()
    ]
    searchable = _command_card_search_text(card)
    searchable_lower = searchable.casefold()
    searchable_norm = re.sub(r"[^a-z0-9]+", " ", searchable_lower).strip()
    card_tokens = _query_tokens(searchable)
    score = 0
    reasons: list[str] = []
    if query_lower == card_id.casefold() or query_tokenized == card_id.casefold():
        score += 2000
        reasons.append(f"id_exact:{card_id}")
    for alias in aliases:
        alias_lower = alias.casefold()
        alias_norm = re.sub(r"[^a-z0-9]+", " ", alias_lower).strip()
        if query_lower == alias_lower or normalized_query == alias_norm:
            score += 1700
            reasons.append(f"alias_exact:{alias}")
        elif normalized_query and normalized_query in alias_norm:
            score += 900
            reasons.append(f"alias_contains:{alias}")
    if command and normalized_query and normalized_query in re.sub(r"[^a-z0-9]+", " ", command.casefold()).strip():
        score += 650
        reasons.append("command_contains")
    if normalized_query and normalized_query in searchable_norm:
        score += 520
        reasons.append("phrase_contains")
    overlap = sorted(query_tokens & card_tokens)
    if overlap:
        score += len(overlap) * 120
        reasons.extend([f"token_overlap:{token}" for token in overlap[:6]])
    return score, reasons


def build_command_card_payload(query: str | None, *, limit: int = 6, debug: bool = True) -> dict[str, Any]:
    raw = str(query or "all").strip() or "all"
    if not debug:
        return debug_trace_block(
            surface_id="command_card",
            command="./repo-python kernel.py --command-card",
            query=raw,
        )
    registry = _command_card_registry_payload()
    cards = [
        dict(card)
        for card in registry.get("cards") or []
        if isinstance(card, Mapping) and str(card.get("id") or "").strip()
    ]
    list_all = raw.casefold() in {"all", "list", "*", "__all__"}
    scored: list[dict[str, Any]] = []
    if list_all:
        for card in cards:
            scored.append({**card, "score": None, "matched_on": ["list_all"]})
    else:
        for card in cards:
            score, reasons = _command_card_score(card, raw)
            if score <= 0:
                continue
            scored.append({**card, "score": score, "matched_on": reasons})
        scored.sort(key=lambda item: (int(item.get("score") or 0), str(item.get("id") or "")), reverse=True)
    returned = scored[: max(1, int(limit))]
    top = returned[0] if returned else None
    next_commands = [
        {"command": str(command), "reason": "Usual next command from the top command card."}
        for command in (top.get("usual_next_commands") if isinstance(top, Mapping) else []) or []
        if str(command or "").strip()
    ]
    return {
        "kind": "kernel.navigate.command_card",
        "schema_version": "command_card_lookup_v1",
        "surface_role": DEBUG_TRACE,
        "first_contact_allowed": False,
        "debug": True,
        "query": {"command": "command-card", "request": raw},
        "summary": {
            "registry_id": registry.get("registry_id"),
            "match_count": len(scored),
            "returned_count": len(returned),
            "top_id": top.get("id") if isinstance(top, Mapping) else None,
            "top_cost_class": top.get("cost_class") if isinstance(top, Mapping) else None,
        },
        "sources": {
            "live": [COMMAND_CARD_REGISTRY_REL],
            "derived": [],
        },
        "payload": {
            "registry": {
                "path": COMMAND_CARD_REGISTRY_REL,
                "purpose": registry.get("purpose"),
                "owning_skill": registry.get("owning_skill"),
            },
            "cards": returned,
        },
        "surface_contract": debug_trace_contract(
            surface_id="command_card",
            command="./repo-python kernel.py --command-card",
            query=raw,
        ),
        "next": next_commands
        or [
            {
                "command": "./repo-python kernel.py --docs-route \"agent movement efficiency\"",
                "reason": "Route from command memory into the broader diagnostics training loop.",
            }
        ],
        "warnings": [] if returned else [f"No command card matched {raw!r}."],
    }


def _path_status(path: Path) -> dict[str, object]:
    return {
        "path": state.rel(path),
        "exists": path.exists(),
    }


def _active_plan_summary() -> dict[str, object] | None:
    if not state.OBSERVE_PLAN.exists():
        return None

    try:
        plan = json.loads(state.OBSERVE_PLAN.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc), "path": state.rel(state.OBSERVE_PLAN)}

    return _kernel_summarize_observe_plan_payload(plan, path=state.rel(state.OBSERVE_PLAN))


def _pulse_effective_active_plan(
    runtime: Mapping[str, Any] | None,
    active_plan: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(active_plan, Mapping) or not active_plan:
        return None
    if isinstance(runtime, Mapping) and str(runtime.get("kind") or "").strip() == "orchestration_state":
        active_driver = str(runtime.get("state") or "").strip()
        if active_driver and active_driver != "observe_session":
            return None
    return dict(active_plan)


def _skill_payload() -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for entry in _load_kernel_skills():
        payload.append(
            {
                "name": entry.get("name"),
                "description": entry.get("description"),
                "kernel_commands": entry.get("kernel_commands", []),
            }
        )
    return payload


def _compiled_bundle_count() -> int:
    if not state.COMPILED_DIR.exists():
        return 0
    return len([path for path in state.COMPILED_DIR.glob("*.json") if path.is_file()])


def _resolve_phase_session_manifest(
    phase_entry: Mapping[str, Any],
    *,
    ref: str | None = None,
) -> Path | None:
    token = str(ref or "latest").strip() or "latest"
    if token != "latest":
        return _kernel_resolve_session_manifest(token)
    phase_id = (
        str(phase_entry.get("phase_id") or "").strip().replace(".", "_").replace("-", "_")
        or str(phase_entry.get("phase_number") or "").strip().replace(".", "_").replace("-", "_")
    )
    phase_dir = str(phase_entry.get("phase_dir") or "").strip()
    candidates = load_session_candidates(
        state.REPO_ROOT,
        sessions_root=state.REPO_ROOT / "obsidian" / "meta" / "observe_sessions",
        include_provisional=False,
        include_compiled_apply=False,
    )
    matching: list[dict[str, Any]] = []
    for candidate in candidates:
        manifest_path = candidate.get("manifest_path")
        if not isinstance(manifest_path, Path):
            continue
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
        session_continuity = payload.get("session_continuity") if isinstance(payload.get("session_continuity"), Mapping) else {}
        artifact_roots = payload.get("artifact_roots") if isinstance(payload.get("artifact_roots"), Mapping) else {}
        candidate_phase_id = normalize_phase_token(
            candidate.get("phase_id") or session_continuity.get("campaign_id")
        )
        workspace_dir = (
            canonicalize_write_path(str(candidate.get("workspace_dir") or "").strip())
            or canonicalize_write_path(str(artifact_roots.get("workspace_dir") or "").strip())
            or ""
        )
        inferred_phase_dir = ""
        if workspace_dir:
            workspace_path = Path(workspace_dir)
            inferred_phase_dir = (
                canonicalize_write_path(workspace_path.parent.as_posix())
                or workspace_path.parent.as_posix()
            )
        candidate_phase_dir = (
            canonicalize_write_path(str(candidate.get("phase_dir") or "").strip())
            or inferred_phase_dir
            or str(candidate.get("phase_dir") or "").strip()
        )
        if (phase_id and candidate_phase_id == phase_id) or (phase_dir and candidate_phase_dir == phase_dir):
            matching.append(candidate)
    if not matching:
        return _kernel_resolve_session_manifest(token)
    best_candidate = max(
        matching,
        key=lambda candidate: session_resolution_sort_key(candidate, intent="read"),
    )
    manifest_path = best_candidate.get("manifest_path")
    return manifest_path if isinstance(manifest_path, Path) else None


def _phase_command_token(phase_entry: Mapping[str, Any], phase_token: str | None) -> str:
    for candidate in (
        phase_token,
        phase_entry.get("phase_id"),
        phase_entry.get("phase_number"),
        phase_entry.get("phase_dir"),
    ):
        token = str(candidate or "").strip()
        if token:
            return token
    return "latest"


def _phase_dock_command(
    phase_ref: str,
    *,
    operation: str,
    session_ref: str | None = None,
    consumer: str = "bridge",
    bridge_provider: str | None = None,
    bridge_route: str | None = None,
    bridge_timeout_s: float = 0.0,
    live: bool = False,
    resume: bool = True,
    write_packet_to: str | None = None,
    write_dock_to: str | None = None,
) -> str:
    parts = ["python3", "kernel.py", "--phase-dock", shlex.quote(phase_ref)]
    if operation and operation != "extract_subphase_seed":
        parts.extend(["--dock-operation", shlex.quote(operation)])
    if operation == "evolve_subphase_seed":
        parts.extend(["--dock-session", shlex.quote(str(session_ref or "latest"))])
    if consumer and consumer != "bridge":
        parts.extend(["--dock-consumer", shlex.quote(consumer)])
    if bridge_provider:
        parts.extend(["--dock-provider", shlex.quote(bridge_provider)])
    if bridge_route:
        parts.extend(["--dock-route", shlex.quote(bridge_route)])
    if bridge_timeout_s and bridge_timeout_s > 0:
        parts.extend(["--dock-timeout-s", str(float(bridge_timeout_s))])
    if write_packet_to:
        parts.extend(["--write-packet", shlex.quote(write_packet_to)])
    if write_dock_to:
        parts.extend(["--write-dock-packet", shlex.quote(write_dock_to)])
    if not resume:
        parts.append("--dock-no-resume")
    if live:
        parts.append("--live")
    return " ".join(parts)


def _phase_begin_status(items: Sequence[Mapping[str, Any]]) -> str:
    if any(str(item.get("status") or "").strip() == "blocked" for item in items):
        return "blocked"
    if any(str(item.get("status") or "").strip() == "warning" for item in items):
        return "warning"
    return "ready"


def _git_scope_summary(root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "status": "warning",
            "detail": f"Git worktree scope could not be inspected: {exc}.",
            "error": str(exc),
        }
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or f"`git status` exited with {result.returncode}."
        return {
            "status": "warning",
            "detail": f"Git worktree scope could not be inspected: {detail}",
            "exit_code": result.returncode,
        }

    lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return {
            "status": "ready",
            "detail": "Git worktree is clean.",
            "summary": {"total": 0, "staged": 0, "unstaged": 0, "untracked": 0},
            "sample_paths": [],
        }

    staged = 0
    unstaged = 0
    untracked = 0
    sample_paths: list[str] = []
    for line in lines:
        code = line[:2]
        path = line[3:].strip() if len(line) > 3 else ""
        if path and len(sample_paths) < 8:
            sample_paths.append(path)
        if code == "??":
            untracked += 1
            continue
        if code[:1] not in {"", " "}:
            staged += 1
        if len(code) > 1 and code[1] not in {"", " "}:
            unstaged += 1
    total = len(lines)
    return {
        "status": "warning",
        "detail": (
            f"Git worktree has {total} changed path(s): {staged} staged, {unstaged} unstaged, {untracked} untracked."
        ),
        "summary": {"total": total, "staged": staged, "unstaged": unstaged, "untracked": untracked},
        "sample_paths": sample_paths,
    }


def _resolve_write_packet_path(write_packet_to: str | None) -> Path:
    if not write_packet_to:
        raise ValueError("write_packet_to is required")
    candidate = Path(write_packet_to).expanduser()
    if not candidate.is_absolute():
        candidate = (state.REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(_kernel_repo_root_resolved())
    return candidate


def _pulse_age_label(value: object) -> str | None:
    stamp = parse_iso_datetime(value)
    if stamp is None:
        return None
    now = datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    delta = max(0, int((now - stamp).total_seconds()))
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def _pulse_active_phase_from_bootstrap_live() -> dict[str, Any] | None:
    bootstrap_live_path = state.REPO_ROOT / "codex/doctrine/agent_bootstrap_live.json"
    if not bootstrap_live_path.is_file():
        return None
    payload = safe_load_json(bootstrap_live_path)
    if not isinstance(payload, Mapping):
        return None
    live_bindings = payload.get("live_bindings")
    if not isinstance(live_bindings, Mapping):
        return None
    phase_dir = canonicalize_write_path(str(live_bindings.get("active_phase_dir") or "").strip())
    if not phase_dir:
        return None
    return {
        "phase_dir": phase_dir,
        "phase_id": str(live_bindings.get("active_phase_id") or "").strip() or None,
        "phase_number": str(live_bindings.get("active_phase_number") or "").strip() or None,
        "phase_title": str(live_bindings.get("active_phase_title") or "").strip() or None,
        "family_dir": canonicalize_write_path(str(live_bindings.get("active_family_dir") or "").strip()) or None,
        "generated_at": payload.get("generated_at"),
        "source_path": state.rel(bootstrap_live_path),
    }


def _first_nonblank_markdown_line(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    return stripped.lstrip("#").strip()
    except OSError:
        return ""
    return ""


def _pulse_frontier_anchor(
    navigator: KernelNavigation,
    limit: int = 5,
    *,
    stale_ok: bool = True,
    active_phase: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    active: Mapping[str, Any] | None = active_phase if stale_ok and isinstance(active_phase, Mapping) else None
    if active is None and stale_ok:
        active = _pulse_active_phase_from_bootstrap_live()
    active_source = "agent_bootstrap_live_active_phase" if active else "explicit_active_phase"
    try:
        if active is None:
            active = load_explicit_active_phase(state.REPO_ROOT)
    except Exception:
        active = None
    if isinstance(active, Mapping):
        phase_dir = canonicalize_write_path(str(active.get("phase_dir") or "").strip())
        if phase_dir:
            candidates: list[Path] = []
            for name in ("pipeline_signal.md", "pipeline_attention.md", "synth_seed.md"):
                path = state.REPO_ROOT / phase_dir / name
                if path.exists():
                    candidates.append(path)
            if candidates:
                try:
                    path = max(candidates, key=lambda item: item.stat().st_mtime)
                    stat = path.stat()
                    rel_path = state.rel(path)
                    title = str(active.get("phase_title") or "").strip() or path.stem
                    first_line = _first_nonblank_markdown_line(path)
                    return {
                        "path": rel_path,
                        "title": title,
                        "first_line": first_line,
                        "top_level_dir": "obsidian",
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "mtime_epoch": int(stat.st_mtime),
                        "signals": ["active_phase"],
                        "source": active_source,
                    }
                except OSError:
                    pass

    try:
        result = navigator.build_frontier(limit)
    except Exception:
        return None
    payload = result.payload if isinstance(result.payload, dict) else {}
    items = payload.get("recent_markdown")
    if not isinstance(items, list) or not items:
        return None
    obsidian_first = next(
        (
            item
            for item in items
            if isinstance(item, dict) and str(item.get("path") or "").startswith("obsidian/")
        ),
        None,
    )
    candidate = obsidian_first if isinstance(obsidian_first, dict) else items[0]
    return candidate if isinstance(candidate, dict) else None


def _pulse_latest_saved_plan(prefix: str | None = None) -> dict[str, Any] | None:
    if not state.OBSERVE_PLANS_DIR.exists():
        return None
    plans = []
    for path in state.OBSERVE_PLANS_DIR.glob("*.json"):
        if prefix and not path.name.startswith(prefix):
            continue
        plans.append(path)
    if not plans:
        return None
    latest = max(plans, key=lambda item: item.stat().st_mtime)
    payload = safe_load_json(latest)
    if not payload:
        return {"path": state.rel(latest), "error": "unreadable"}
    summary = _kernel_summarize_observe_plan_payload(payload, path=state.rel(latest))
    summary["mtime"] = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc).isoformat()
    return summary


def _pulse_latest_runtime(
    *,
    exact: bool = False,
    active_phase: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        if exact:
            from system.control.orchestration import load_orchestration_state

            orchestration = load_orchestration_state(repo_root=state.REPO_ROOT, refresh=False)
        else:
            state_path = state.REPO_ROOT / ORCHESTRATION_STATE_REL
            orchestration = safe_load_json(state_path) if state_path.is_file() else {}
            if not isinstance(orchestration, Mapping) or not orchestration:
                orchestration = {}
            activation = active_phase if isinstance(active_phase, Mapping) and active_phase else None
            if activation is None:
                activation = _pulse_active_phase_from_bootstrap_live() or load_explicit_active_phase(state.REPO_ROOT)
            if (
                isinstance(activation, Mapping)
                and activation
                and orchestration
                and not _pulse_cached_orchestration_phase_matches(orchestration, activation)
            ):
                return _pulse_phase_rearm_runtime(activation, orchestration)
            if not orchestration:
                from system.control.orchestration import load_orchestration_state

                orchestration = load_orchestration_state(repo_root=state.REPO_ROOT, refresh=False)

        action = _pulse_selected_action(orchestration)
        gate = orchestration.get("gate") if isinstance(orchestration.get("gate"), dict) else {}
        el = orchestration.get("event_log")
        return {
            "kind": "orchestration_state",
            "state": orchestration.get("active_driver"),
            "updated_at": orchestration.get("updated_at"),
            "summary": action.get("summary"),
            "command": action.get("command"),
            "gate_reason": gate.get("gate_reason"),
            "can_continue": bool(action.get("launch_recommended_now")),
            "drivers": orchestration.get("drivers"),
            "event_log": el if isinstance(el, dict) else None,
            "coordination": orchestration.get("coordination") if isinstance(orchestration.get("coordination"), dict) else None,
            "source": "exact_orchestration_loader" if exact else "persisted_orchestration_projection",
        }
    except Exception:
        pass

    runtime = _lib_grouped_runtime_status_payload(state.REPO_ROOT, state.OBSERVE_HISTORY_DIR, "latest")
    if not isinstance(runtime, dict) or not runtime or str(runtime.get("kind") or "").strip() != "grouped_observe":
        return None
    groups = runtime.get("groups")
    pending: list[str] = []
    completed_count = 0
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            label = str(group.get("label") or "").strip()
            grp_state = str(group.get("state") or "").strip()
            if label and grp_state in {"pending", "queued", "running", "retryable_failed"}:
                pending.append(label)
            if grp_state in {"completed", "done", "success"}:
                completed_count += 1
    total_groups = runtime.get("total_groups")
    completed_groups = runtime.get("completed_groups")
    rt_state = str(runtime.get("state") or "").strip()
    if not completed_groups and completed_count:
        completed_groups = completed_count
    if not completed_groups and rt_state == "completed" and total_groups and not pending:
        completed_groups = total_groups
    return {
        "observe_id": runtime.get("observe_id"),
        "state": rt_state,
        "provider": runtime.get("provider"),
        "started_at": runtime.get("started_at"),
        "updated_at": runtime.get("updated_at"),
        "wave_index": runtime.get("wave_index"),
        "wave_total": runtime.get("wave_total"),
        "total_groups": total_groups,
        "completed_groups": completed_groups,
        "can_continue": bool(runtime.get("can_continue")),
        "pending_group_labels": pending[:6],
        "latest_artifact": (
            runtime.get("resume_surface", {}).get("latest_artifact")
            if isinstance(runtime.get("resume_surface"), dict)
            else None
        ),
        "history_entry": (
            runtime.get("artifacts", {}).get("history_entry")
            if isinstance(runtime.get("artifacts"), dict)
            else None
        ),
    }


def _pulse_doctrine_summary(navigator: KernelNavigation, *, exact: bool = False) -> dict[str, Any]:
    if not exact:
        repo_root = getattr(state, "REPO_ROOT", navigator.root)
        derived_path = repo_root / "codex" / "derived" / "map.json"
        derived = safe_load_json(derived_path) if derived_path.is_file() else {}
        doctrine_index = derived.get("doctrine_index") if isinstance(derived, Mapping) else {}
        entries = list(doctrine_index.get("entries") or []) if isinstance(doctrine_index, Mapping) else []
        if entries:
            drift = [entry for entry in entries if isinstance(entry, Mapping) and str(entry.get("drift_risk") or "low") != "low"]
            graph = [entry for entry in entries if isinstance(entry, Mapping) and str(entry.get("graph_risk") or "low") != "low"]
            try:
                source_path = state.rel(derived_path)
            except Exception:
                source_path = str(derived_path.relative_to(repo_root))
            return {
                "total_docs": len(entries),
                "drift_docs": len(drift),
                "graph_docs": len(graph),
                "hotspots": [],
                "hotspots_deferred": True,
                "hotspot_command": "./repo-python kernel.py --stale --full",
                "hotspot_deferred_reason": (
                    "quick pulse reads a materialized doctrine projection; stale hotspot examples "
                    "are deferred so cleared rows do not masquerade as live route truth"
                ),
                "source": source_path,
                "freshness_policy": "materialized_doctrine_index_projection",
                "exact_staleness": False,
            }

    entries = list(navigator.doctrine_entries)
    drift = [entry for entry in entries if str(entry.get("drift_risk") or "low") != "low"]
    graph = [entry for entry in entries if str(entry.get("graph_risk") or "low") != "low"]
    hotspots: list[dict[str, Any]] = []
    for entry in sorted(
        drift,
        key=lambda item: (-len(item.get("drift_reasons", [])), str(item.get("file_path") or "")),
    )[:5]:
        hotspots.append(
            {
                "id": entry.get("id"),
                "path": entry.get("file_path"),
                "kind": entry.get("kind"),
                "drift_reasons": list(entry.get("drift_reasons", []))[:4],
            }
        )
    return {
        "total_docs": len(entries),
        "drift_docs": len(drift),
        "graph_docs": len(graph),
        "hotspots": hotspots,
        "source": "KernelNavigation.doctrine_entries",
        "freshness_policy": "live_scan",
        "exact_staleness": bool(exact),
    }


def _load_annex_landing_index_summary(index_path: Path) -> dict[str, Any]:
    text = index_path.read_text(encoding="utf-8")
    try:
        prefix_marker = '\n  "by_axis"'
        prefix_end = text.find(prefix_marker)
        if prefix_end < 0:
            return json.loads(text)

        prefix = text[:prefix_end].rstrip()
        if prefix.endswith(","):
            prefix = prefix[:-1]
        index_head = json.loads(f"{prefix}\n}}")

        adoption_summary: dict[str, Any] = {}
        adoption_key = '"adoption_summary"'
        adoption_index = text.find(adoption_key)
        if adoption_index >= 0:
            adoption_colon = text.find(":", adoption_index + len(adoption_key))
            adoption_start = text.find("{", adoption_colon)
            if adoption_start >= 0:
                decoded, _ = json.JSONDecoder().raw_decode(text[adoption_start:])
                adoption_summary = dict(decoded) if isinstance(decoded, Mapping) else {}

        return {
            "pattern_count": index_head.get("pattern_count"),
            "annex_count": index_head.get("annex_count"),
            "distillation_status_counts": index_head.get("distillation_status_counts"),
            "adoption_summary": adoption_summary,
        }
    except Exception:
        return json.loads(text)


def _pulse_annex_landing_summary() -> dict[str, Any]:
    """Read annexes/annex_distillation_index.json and surface the pattern landing rate.

    Why this row exists in pulse: codex/doctrine/skills/annex/annex_pattern_transfer.md §Diagnostic
    item 4 — without surfacing the landing rate at orientation time, cold agents never see the
    drift signal and the annex up-propagation move stays under-fired.
    """
    index_path = state.REPO_ROOT / "annexes" / "annex_distillation_index.json"
    summary: dict[str, Any] = {
        "available": False,
        "total_patterns": 0,
        "adopted_count": 0,
        "evaluated_count": 0,
        "proposed_count": 0,
        "rejected_count": 0,
        "deferred_count": 0,
        "landing_rate_pct": 0.0,
        "under_fire": False,
    }
    if not index_path.is_file():
        return summary
    try:
        data = _load_annex_landing_index_summary(index_path)
    except Exception:
        return summary
    total = int(data.get("pattern_count") or 0)
    adoption = data.get("adoption_summary") if isinstance(data.get("adoption_summary"), Mapping) else {}
    status_counts = adoption.get("status_counts") if isinstance(adoption.get("status_counts"), Mapping) else {}
    adopted = int(status_counts.get("adopted") or 0)
    evaluated = int(status_counts.get("evaluated") or 0)
    proposed = int(status_counts.get("proposed") or 0)
    rejected = int(status_counts.get("rejected") or 0)
    deferred = int(status_counts.get("deferred") or 0)
    rate = (adopted / total * 100.0) if total else 0.0
    summary.update(
        {
            "available": True,
            "total_patterns": total,
            "adopted_count": adopted,
            "evaluated_count": evaluated,
            "proposed_count": proposed,
            "rejected_count": rejected,
            "deferred_count": deferred,
            "landing_rate_pct": round(rate, 1),
            "under_fire": rate < 5.0,
            "annex_count": int(data.get("annex_count") or 0),
            "placeholder_count": int(
                (data.get("distillation_status_counts") or {}).get("placeholder") or 0
            ),
        }
    )
    return summary


def _pulse_workspace_summary() -> dict[str, Any]:
    observe_plan_count = len(list(state.OBSERVE_PLANS_DIR.glob("*.json"))) if state.OBSERVE_PLANS_DIR.exists() else 0
    snapshot_count = len(list(state.APPLY_SNAPSHOTS.iterdir())) if state.APPLY_SNAPSHOTS.exists() else 0
    dump_count = len([path for path in state.OBSERVE_DUMPS.iterdir() if path.is_dir()]) if state.OBSERVE_DUMPS.exists() else 0
    manifest_count = len(list(state.PLAN_DIR.glob("*.json"))) if state.PLAN_DIR.exists() else 0
    return {
        "observe_plan_count": observe_plan_count,
        "observe_dump_count": dump_count,
        "plan_manifest_count": manifest_count,
        "apply_snapshot_count": snapshot_count,
    }


def _pulse_closeout_git_state() -> dict[str, Any]:
    try:
        from system.lib.git_state_snapshot import (
            build_closeout_git_state_conditions,
            compact_closeout_git_state_conditions,
        )

        return compact_closeout_git_state_conditions(
            build_closeout_git_state_conditions(state.REPO_ROOT, path_limit=5, recent_limit=1)
        )
    except Exception as exc:
        return {
            "schema": "closeout_git_state_summary_v0",
            "status": "unknown",
            "reason": "pulse_closeout_git_state_failed",
            "error": str(exc)[:240],
            "drilldowns": {
                "closeout_conditions": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions"
            },
        }


_CLOSEOUT_CLOSED_WAVE_STATUSES = {"completed", "assimilated", "closed", "done", "archived"}
_CLOSEOUT_PENDING_STATES = {"pending_resume", "pending_assimilation"}
_CLOSEOUT_ACTIONABLE_STATES = _CLOSEOUT_PENDING_STATES | {
    "failed_recovery_pending",
    "historic_failed",
    "inflight",
    "orphaned_session",
}
_CLOSEOUT_DISPOSITION_LEDGER_PATH = "state/closeout/closeout_dispositions.jsonl"


def _load_closeout_dispositions() -> dict[str, dict[str, Any]]:
    """Read the closeout disposition ledger and return rows keyed by observe_id.

    Schema (one JSON object per line, schema=closeout_disposition_v1):
      observe_id (str), phase_id (str), disposition (str),
      recovery_required (bool), reason (str), evidence_refs (list[str]),
      source_workitem (str), source_event (str), dispositioned_by (str),
      created_at (iso8601 str), previous_closeout_state (str).

    Only rows with recovery_required=False are returned; recovery_required=True
    rows are still failure obligations and must remain actionable.
    """
    ledger_path = state.REPO_ROOT / _CLOSEOUT_DISPOSITION_LEDGER_PATH
    if not ledger_path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(row, dict):
                    continue
                if row.get("recovery_required") is True:
                    continue
                obs = str(row.get("observe_id") or "").strip()
                if not obs:
                    continue
                out[obs] = row
    except OSError:
        return {}
    return out


_PHASE_RESUME_STATE_FILENAME = "_subphase_controller_state.json"
_PHASE_RESUME_STATE_VERSION = "subphase_controller_state_v1"
_PHASE_RESUME_PACKET_VERSION = "phase_resume_packet_v1"


def _dedupe_resume_strings(values: Sequence[object], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
        if limit is not None and len(output) >= limit:
            break
    return output


def _phase_assimilation_surface(phase_entry: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = {
        "phase_id": None,
        "phase_number": None,
        "phase_title": None,
        "phase_dir": None,
        "current_wave_id": None,
        "current_wave_status": None,
        "delta_path": None,
        "delta_exists": False,
        "continuation_summary_path": None,
        "continuation_summary_exists": False,
    }
    if not isinstance(phase_entry, Mapping):
        return payload
    payload["phase_id"] = str(phase_entry.get("phase_id") or "").strip() or None
    payload["phase_number"] = str(phase_entry.get("phase_number") or "").strip() or None
    payload["phase_title"] = str(phase_entry.get("phase_title") or "").strip() or None
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or str(phase_entry.get("phase_dir") or "").strip()
    payload["phase_dir"] = phase_dir or None
    try:
        scaffold_path = _phase_scaffold_path_for_entry(phase_entry)
        synth_path = _phase_file_from_entry(phase_entry, "synth_seed.json")
        scaffold_payload = safe_load_json(scaffold_path)
        synth_payload = safe_load_json(synth_path)
        if not isinstance(synth_payload, Mapping):
            return payload
        normalized = normalize_synth_payload(
            synth_payload,
            phase_scaffold=scaffold_payload if isinstance(scaffold_payload, Mapping) else None,
        )
        if not isinstance(normalized, Mapping):
            return payload
        current_wave = normalized.get("current_wave") if isinstance(normalized.get("current_wave"), Mapping) else {}
        assimilation_targets = normalize_assimilation_targets(
            normalized.get("assimilation_targets"),
            phase_scaffold=scaffold_payload if isinstance(scaffold_payload, Mapping) else None,
        )
        delta_rel = canonicalize_write_path(str(assimilation_targets.get("delta_path") or "").strip()) or ""
        continuation_rel = canonicalize_write_path(str(assimilation_targets.get("continuation_summary_path") or "").strip()) or ""
        payload["current_wave_id"] = str(current_wave.get("wave_id") or "").strip() or None
        payload["current_wave_status"] = str(current_wave.get("status") or "").strip() or None
        payload["delta_path"] = delta_rel or None
        payload["delta_exists"] = bool(delta_rel and (state.REPO_ROOT / delta_rel).exists())
        payload["continuation_summary_path"] = continuation_rel or None
        payload["continuation_summary_exists"] = bool(continuation_rel and (state.REPO_ROOT / continuation_rel).exists())
    except Exception:
        return payload
    return payload


def _iter_phase_scaffold_paths(repo_root: Path) -> list[Path]:
    obsidian_root = repo_root / "obsidian"
    if not obsidian_root.exists():
        return []
    paths: list[Path] = []
    for current_root, dirnames, filenames in os.walk(obsidian_root):
        relative_base = Path(current_root).relative_to(repo_root)
        dirnames[:] = [
            name
            for name in dirnames
            if not _should_skip_repo_scan_dir(relative_base, name)
        ]
        if "phase_scaffold.json" in filenames:
            paths.append(Path(current_root) / "phase_scaffold.json")
    return sorted(paths)


def _closeout_phase_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for scaffold_path in _iter_phase_scaffold_paths(state.REPO_ROOT):
        payload = safe_load_json(scaffold_path)
        if not isinstance(payload, Mapping):
            continue
        phase_dir = (
            canonicalize_write_path(str(payload.get("phase_dir") or "").strip())
            or state.rel(scaffold_path.parent)
        )
        phase_id = str(payload.get("phase_id") or "").strip() or None
        if not phase_id and not phase_dir:
            continue
        entries.append(
            {
                "phase_id": phase_id,
                "phase_number": str(payload.get("phase_number") or "").strip() or None,
                "phase_title": str(payload.get("phase_title") or "").strip() or None,
                "phase_dir": phase_dir,
                "family_dir": canonicalize_write_path(str(payload.get("family_dir") or "").strip()) or None,
                "spec_path": state.rel(scaffold_path),
            }
        )
    return entries


def _build_closeout_audit_payload(
    *,
    limit: int = 10,
    candidate_scan_limit: int | None = None,
) -> dict[str, Any]:
    sessions_root = state.REPO_ROOT / "obsidian" / "meta" / "observe_sessions"
    phase_entries = [
        entry
        for entry in _closeout_phase_entries()
        if isinstance(entry, Mapping) and (str(entry.get("phase_id") or "").strip() or str(entry.get("phase_dir") or "").strip())
    ]
    phase_by_id: dict[str, Mapping[str, Any]] = {}
    phase_by_dir: dict[str, Mapping[str, Any]] = {}
    for entry in phase_entries:
        phase_id = normalize_phase_token(entry.get("phase_id") or entry.get("phase_number"))
        phase_dir = canonicalize_write_path(str(entry.get("phase_dir") or "").strip()) or str(entry.get("phase_dir") or "").strip()
        if phase_id:
            phase_by_id[phase_id] = entry
        if phase_dir:
            phase_by_dir[phase_dir] = entry

    candidates = sorted(
        load_session_candidates(
            state.REPO_ROOT,
            sessions_root=sessions_root,
            include_provisional=True,
            include_compiled_apply=False,
            manifest_limit=candidate_scan_limit,
            root_limit=candidate_scan_limit,
        ),
        key=lambda candidate: session_resolution_sort_key(candidate, intent="read"),
        reverse=True,
    )
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for candidate in candidates:
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
        session_continuity = payload.get("session_continuity") if isinstance(payload, Mapping) and isinstance(payload.get("session_continuity"), Mapping) else {}
        artifact_roots = payload.get("artifact_roots") if isinstance(payload, Mapping) and isinstance(payload.get("artifact_roots"), Mapping) else {}
        workspace_dir = canonicalize_write_path(str(candidate.get("workspace_dir") or "").strip()) or canonicalize_write_path(str(artifact_roots.get("workspace_dir") or "").strip()) or ""
        inferred_phase_dir = ""
        if workspace_dir:
            workspace_path = Path(workspace_dir)
            inferred_phase_dir = canonicalize_write_path(workspace_path.parent.as_posix()) or workspace_path.parent.as_posix()
        phase_id = normalize_phase_token(candidate.get("phase_id") or session_continuity.get("campaign_id"))
        phase_dir = (
            canonicalize_write_path(str(candidate.get("phase_dir") or "").strip())
            or inferred_phase_dir
            or str(candidate.get("phase_dir") or "").strip()
        )
        session_slug = str(candidate.get("session_slug") or "").strip()
        dedupe_key = phase_id or phase_dir or session_slug
        if not dedupe_key or dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        deduped.append(dict(candidate))

    dispositions_by_obs = _load_closeout_dispositions()

    items: list[dict[str, Any]] = []
    summary = {
        "total_candidates": len(candidates),
        "audited_phases": 0,
        "pending_closeout_count": 0,
        "failed_recovery_count": 0,
        "failed_dispositioned_count": 0,
        "failed_unresolved_count": 0,
        "failed_historic_count": 0,
        "failed_historic_dispositioned_count": 0,
        "inflight_count": 0,
        "closed_count": 0,
        "orphaned_count": 0,
        "orphaned_dispositioned_count": 0,
        "candidate_scan_limit": candidate_scan_limit,
        "candidate_scan_limited": candidate_scan_limit is not None,
    }

    for candidate in deduped:
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
        session_continuity = payload.get("session_continuity") if isinstance(payload, Mapping) and isinstance(payload.get("session_continuity"), Mapping) else {}
        artifact_roots = payload.get("artifact_roots") if isinstance(payload, Mapping) and isinstance(payload.get("artifact_roots"), Mapping) else {}
        workspace_dir = canonicalize_write_path(str(candidate.get("workspace_dir") or "").strip()) or canonicalize_write_path(str(artifact_roots.get("workspace_dir") or "").strip()) or ""
        inferred_phase_dir = ""
        if workspace_dir:
            workspace_path = Path(workspace_dir)
            inferred_phase_dir = canonicalize_write_path(workspace_path.parent.as_posix()) or workspace_path.parent.as_posix()
        phase_id = normalize_phase_token(candidate.get("phase_id") or session_continuity.get("campaign_id"))
        phase_dir = (
            canonicalize_write_path(str(candidate.get("phase_dir") or "").strip())
            or inferred_phase_dir
            or str(candidate.get("phase_dir") or "").strip()
        )
        phase_entry = phase_by_id.get(phase_id or "") or phase_by_dir.get(phase_dir or "")
        assimilation = _phase_assimilation_surface(phase_entry)
        round_id = str(session_continuity.get("round_id") or "").strip() or None
        lifecycle_stage = str(candidate.get("lifecycle_stage") or "unknown").strip() or "unknown"
        current_wave_id = str(assimilation.get("current_wave_id") or "").strip() or None
        current_wave_status = str(assimilation.get("current_wave_status") or "").strip().lower() or None
        same_wave = bool(round_id and current_wave_id and round_id == current_wave_id)

        closeout_state = "unknown"
        reason = "Session lifecycle could not be classified against the current phase wave."
        if phase_entry is None:
            closeout_state = "orphaned_session"
            reason = "Session has no resolvable live phase entry."
            summary["orphaned_count"] += 1
        elif lifecycle_stage == "inflight":
            closeout_state = "inflight"
            reason = "Detached observe session is still running."
            summary["inflight_count"] += 1
        elif lifecycle_stage in {"failed", "apply_failed"}:
            closeout_state = "failed_recovery_pending" if same_wave or not current_wave_id else "historic_failed"
            reason = "Detached observe session failed and the owning wave is still the live phase surface."
            summary["failed_recovery_count"] += 1
        elif lifecycle_stage in {"done_pending_compile", "compiled_pending_apply"}:
            if same_wave and current_wave_status not in _CLOSEOUT_CLOSED_WAVE_STATUSES:
                if assimilation.get("delta_exists") or assimilation.get("continuation_summary_exists"):
                    closeout_state = "pending_assimilation"
                    reason = "Session finished and closeout artifacts exist, but the owning wave is still open."
                else:
                    closeout_state = "pending_resume"
                    reason = "Session finished, but no synth-evolution or continuation artifacts were written for the live wave."
                summary["pending_closeout_count"] += 1
            else:
                closeout_state = "session_complete"
                reason = "Session completed and no longer matches the current live wave."
                summary["closed_count"] += 1
        elif lifecycle_stage == "applied":
            closeout_state = "applied"
            reason = "Session already carries a successful apply receipt."
            summary["closed_count"] += 1
        else:
            closeout_state = lifecycle_stage
            summary["closed_count"] += 1

        observe_id_val = str(candidate.get("observe_id") or "").strip()
        disposition_record = dispositions_by_obs.get(observe_id_val) if observe_id_val else None
        is_dispositioned = bool(disposition_record) and closeout_state in _CLOSEOUT_ACTIONABLE_STATES
        if is_dispositioned and closeout_state == "failed_recovery_pending":
            summary["failed_dispositioned_count"] += 1

        phase_ref = _phase_command_token(phase_entry, None) if isinstance(phase_entry, Mapping) else None
        session_ref = str(candidate.get("observe_id") or candidate.get("session_slug") or "").strip() or None
        commands: list[dict[str, str]] = []
        if session_ref:
            commands.append(
                {
                    "command": f"python3 kernel.py --read-session {shlex.quote(session_ref)}",
                    "reason": "Read the persisted session digest and authoritative resume artifact.",
                }
            )
        if phase_ref:
            commands.append(
                {
                    "command": f"python3 kernel.py --phase {shlex.quote(phase_ref)}",
                    "reason": "Inspect the live phase card and current wave state.",
                }
            )
            if not is_dispositioned and closeout_state in _CLOSEOUT_PENDING_STATES | {"failed_recovery_pending"}:
                commands.append(
                    {
                        "command": f"python3 kernel.py --phase-resume {shlex.quote(phase_ref)}",
                        "reason": "Compile the phase-native resume packet and next-step lifecycle for this subphase.",
                    }
                )
                commands.append(
                    {
                        "command": f"python3 kernel.py --phase-resume {shlex.quote(phase_ref)} --live",
                        "reason": "Write the subphase controller state plus resume/attention artifacts beside the phase.",
                    }
                )
            if not is_dispositioned and closeout_state in _CLOSEOUT_PENDING_STATES:
                commands.append(
                    {
                        "command": f"python3 kernel.py --phase-begin {shlex.quote(phase_ref)} --operation evolve_subphase_seed",
                        "reason": "Preview the missing synth-evolution seam for this finished observe session.",
                    }
                )
                commands.append(
                    {
                        "command": f"python3 kernel.py --phase-assimilate {shlex.quote(phase_ref)}",
                        "reason": "Preview the wave closeout step once synth evolution and continuation state are ready.",
                    }
                )
        item = {
            "phase_id": assimilation.get("phase_id") or phase_id,
            "phase_number": assimilation.get("phase_number") or candidate.get("phase_number"),
            "phase_title": assimilation.get("phase_title") or candidate.get("phase_title"),
            "phase_dir": assimilation.get("phase_dir") or phase_dir or None,
            "session_slug": candidate.get("session_slug"),
            "observe_id": candidate.get("observe_id"),
            "manifest_path": state.rel(candidate.get("manifest_path")) if isinstance(candidate.get("manifest_path"), Path) else candidate.get("manifest_path"),
            "session_status": candidate.get("status"),
            "lifecycle_stage": lifecycle_stage,
            "closeout_state": closeout_state,
            "reason": reason,
            "round_id": round_id,
            "current_wave_id": assimilation.get("current_wave_id"),
            "current_wave_status": assimilation.get("current_wave_status"),
            "delta_path": assimilation.get("delta_path"),
            "delta_exists": bool(assimilation.get("delta_exists")),
            "continuation_summary_path": assimilation.get("continuation_summary_path"),
            "continuation_summary_exists": bool(assimilation.get("continuation_summary_exists")),
            "primary_artifact": candidate.get("primary_artifact"),
            "disposition": disposition_record if is_dispositioned else None,
            "recommended_commands": commands,
        }
        items.append(item)
        summary["audited_phases"] += 1

    actionable_items = [
        item for item in items
        if str(item.get("closeout_state") or "").strip() in _CLOSEOUT_ACTIONABLE_STATES
        and not item.get("disposition")
    ]
    dispositioned_items = [item for item in items if item.get("disposition")]
    orphaned_items = [
        item for item in items
        if str(item.get("closeout_state") or "").strip() == "orphaned_session"
        and not item.get("disposition")
    ]
    historic_items = [
        item for item in items
        if str(item.get("closeout_state") or "").strip() == "historic_failed"
        and not item.get("disposition")
    ]

    # failed_unresolved_count must reflect actionable, non-dispositioned recovery
    # obligations only — not raw lifecycle failures. historic_failed rows
    # (round_id != current_wave_id) are abandoned branches and surface separately
    # as failed_historic_count so they do not drive "need recovery" alerting.
    summary["failed_unresolved_count"] = sum(
        1 for item in actionable_items
        if str(item.get("closeout_state") or "").strip() == "failed_recovery_pending"
    )
    summary["failed_historic_count"] = len(historic_items)
    summary["failed_historic_dispositioned_count"] = sum(
        1 for item in dispositioned_items
        if str(item.get("closeout_state") or "").strip() == "historic_failed"
    )
    summary["orphaned_count"] = len(orphaned_items)
    summary["orphaned_dispositioned_count"] = sum(
        1 for item in dispositioned_items
        if str(item.get("closeout_state") or "").strip() == "orphaned_session"
    )

    recommended: list[dict[str, str]] = []
    if summary["pending_closeout_count"] or summary["failed_unresolved_count"]:
        recommended.append(
            {
                "command": "python3 kernel.py --closeout-audit",
                "reason": "Detached subphase sessions have finished or failed without phase closeout; inspect the audit before spawning more work.",
            }
        )
    if actionable_items:
        first = actionable_items[0]
        first_commands = first.get("recommended_commands") if isinstance(first.get("recommended_commands"), list) else []
        for command in first_commands[:2]:
            if isinstance(command, Mapping) and str(command.get("command") or "").strip():
                recommended.append(
                    {
                        "command": str(command.get("command") or "").strip(),
                        "reason": str(command.get("reason") or "").strip() or "Follow the first problematic closeout item.",
                    }
                )
    return {
        "kind": "kernel.closeout_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "items": items[: max(0, int(limit))],
        "actionable_items": actionable_items[: max(0, int(limit))],
        "dispositioned_items": dispositioned_items[: max(0, int(limit))],
        "historic_items": historic_items[: max(0, int(limit))],
        "orphaned_items": orphaned_items[: max(0, int(limit))],
        "recommended_actions": recommended[:3],
    }


def _phase_resume_artifact_paths(phase_entry: Mapping[str, Any]) -> dict[str, str]:
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    if not phase_dir:
        raise ValueError("phase_dir is required for phase resume artifacts.")
    return {
        "state_path": canonicalize_write_path(f"{phase_dir}/{_PHASE_RESUME_STATE_FILENAME}") or "",
        "resume_json_path": canonicalize_write_path(f"{phase_dir}/pipeline_resume.json") or "",
        "resume_md_path": canonicalize_write_path(f"{phase_dir}/pipeline_resume.md") or "",
        "attention_json_path": canonicalize_write_path(f"{phase_dir}/pipeline_attention.json") or "",
        "attention_md_path": canonicalize_write_path(f"{phase_dir}/pipeline_attention.md") or "",
        "continuation_packet_path": canonicalize_write_path(f"{phase_dir}/continuation_packet.json") or "",
    }


def _phase_resume_audit_item(phase_entry: Mapping[str, Any]) -> dict[str, Any]:
    phase_id = normalize_phase_token(phase_entry.get("phase_id") or phase_entry.get("phase_number"))
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    audit_payload = _build_closeout_audit_payload(limit=100000)
    for item in audit_payload.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        item_phase_id = normalize_phase_token(item.get("phase_id") or item.get("phase_number"))
        item_phase_dir = canonicalize_write_path(str(item.get("phase_dir") or "").strip()) or ""
        if (phase_id and item_phase_id == phase_id) or (phase_dir and item_phase_dir == phase_dir):
            return dict(item)

    assimilation = _phase_assimilation_surface(phase_entry)
    current_wave_id = str(assimilation.get("current_wave_id") or "").strip() or None
    current_wave_status = str(assimilation.get("current_wave_status") or "").strip().lower() or None
    sessions_root = state.REPO_ROOT / "obsidian" / "meta" / "observe_sessions"
    candidates = sorted(
        load_session_candidates(
            state.REPO_ROOT,
            sessions_root=sessions_root,
            include_provisional=True,
            include_compiled_apply=False,
        ),
        key=lambda candidate: session_resolution_sort_key(candidate, intent="read"),
        reverse=True,
    )
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        candidate_phase_id = normalize_phase_token(candidate.get("phase_id") or candidate.get("phase_number"))
        candidate_phase_dir = canonicalize_write_path(str(candidate.get("phase_dir") or "").strip()) or ""
        workspace_dir = canonicalize_write_path(str(candidate.get("workspace_dir") or "").strip()) or ""
        if workspace_dir and not candidate_phase_dir:
            candidate_phase_dir = canonicalize_write_path(str(Path(workspace_dir).parent.as_posix())) or ""
        if not ((phase_id and candidate_phase_id == phase_id) or (phase_dir and candidate_phase_dir == phase_dir)):
            continue

        payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
        session_continuity = payload.get("session_continuity") if isinstance(payload.get("session_continuity"), Mapping) else {}
        round_id = str(session_continuity.get("round_id") or "").strip() or None
        lifecycle_stage = str(candidate.get("lifecycle_stage") or "unknown").strip() or "unknown"
        same_wave = bool(round_id and current_wave_id and round_id == current_wave_id)
        closeout_state = "session_complete"
        reason = "Detached observe session no longer blocks the live phase surface."
        if lifecycle_stage == "inflight":
            closeout_state = "inflight"
            reason = "Detached observe session is still running."
        elif lifecycle_stage in {"failed", "apply_failed"}:
            closeout_state = "failed_recovery_pending" if same_wave or not current_wave_id else "historic_failed"
            reason = "Detached observe session failed and the owning wave is still the live phase surface."
        elif lifecycle_stage in {"done_pending_compile", "compiled_pending_apply"} and same_wave and current_wave_status not in _CLOSEOUT_CLOSED_WAVE_STATUSES:
            if assimilation.get("delta_exists") or assimilation.get("continuation_summary_exists"):
                closeout_state = "pending_assimilation"
                reason = "Session finished and closeout artifacts exist, but the owning wave is still open."
            else:
                closeout_state = "pending_resume"
                reason = "Session finished, but no synth-evolution or continuation artifacts were written for the live wave."
        return {
            "phase_id": assimilation.get("phase_id") or phase_id,
            "phase_number": assimilation.get("phase_number") or phase_entry.get("phase_number"),
            "phase_title": assimilation.get("phase_title") or phase_entry.get("phase_title"),
            "phase_dir": assimilation.get("phase_dir") or phase_dir,
            "session_slug": candidate.get("session_slug"),
            "observe_id": candidate.get("observe_id"),
            "manifest_path": state.rel(candidate.get("manifest_path")) if isinstance(candidate.get("manifest_path"), Path) else candidate.get("manifest_path"),
            "session_status": candidate.get("status"),
            "lifecycle_stage": lifecycle_stage,
            "closeout_state": closeout_state,
            "reason": reason,
            "round_id": round_id,
            "current_wave_id": assimilation.get("current_wave_id"),
            "current_wave_status": assimilation.get("current_wave_status"),
            "delta_path": assimilation.get("delta_path"),
            "delta_exists": bool(assimilation.get("delta_exists")),
            "continuation_summary_path": assimilation.get("continuation_summary_path"),
            "continuation_summary_exists": bool(assimilation.get("continuation_summary_exists")),
            "primary_artifact": candidate.get("primary_artifact"),
            "recommended_commands": [],
        }

    return {
        "phase_id": assimilation.get("phase_id") or phase_id,
        "phase_number": assimilation.get("phase_number") or phase_entry.get("phase_number"),
        "phase_title": assimilation.get("phase_title") or phase_entry.get("phase_title"),
        "phase_dir": assimilation.get("phase_dir") or phase_dir,
        "session_slug": None,
        "observe_id": None,
        "session_status": None,
        "lifecycle_stage": "none",
        "closeout_state": "ready_for_next_wave",
        "reason": "No detached observe closeout gap is active for this subphase.",
        "round_id": None,
        "current_wave_id": assimilation.get("current_wave_id"),
        "current_wave_status": assimilation.get("current_wave_status"),
        "delta_path": assimilation.get("delta_path"),
        "delta_exists": bool(assimilation.get("delta_exists")),
        "continuation_summary_path": assimilation.get("continuation_summary_path"),
        "continuation_summary_exists": bool(assimilation.get("continuation_summary_exists")),
        "primary_artifact": None,
        "recommended_commands": [],
    }


def _phase_resume_recent_history(meta_ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries = [
        dict(item)
        for item in (meta_ledger.get("entries") or [])
        if isinstance(item, Mapping)
    ]
    recent = entries[-5:]
    return [
        {
            "entry_id": str(item.get("entry_id") or "").strip() or None,
            "timestamp": str(item.get("timestamp") or "").strip() or None,
            "action": str(item.get("action") or "").strip() or None,
            "summary": str(item.get("summary") or "").strip() or None,
        }
        for item in recent
    ]


def _phase_resume_compression(meta_ledger: Mapping[str, Any], synth: Mapping[str, Any]) -> dict[str, Any]:
    entries = [
        dict(item)
        for item in (meta_ledger.get("entries") or [])
        if isinstance(item, Mapping)
    ]
    recent_entries = entries[-5:]
    recent_done = _dedupe_resume_strings(
        [value for entry in recent_entries for value in (entry.get("what_was_done") or [])],
        limit=8,
    )
    recent_learnings = _dedupe_resume_strings(
        [value for entry in recent_entries for value in (entry.get("what_was_learned") or [])],
        limit=8,
    )
    recent_open_questions = _dedupe_resume_strings(
        [value for entry in recent_entries for value in (entry.get("open_questions_remaining") or [])],
        limit=8,
    )
    return {
        "entry_count": len(entries),
        "recent_entry_ids": _dedupe_resume_strings([entry.get("entry_id") for entry in recent_entries], limit=5),
        "recent_summaries": _dedupe_resume_strings([entry.get("summary") for entry in recent_entries], limit=5),
        "recent_done": recent_done,
        "recent_learnings": recent_learnings,
        "recent_open_questions": recent_open_questions,
        "next_step_posture": str(synth.get("next_step_posture") or "").strip() or None,
    }


def _phase_resume_scope_files(synth: Mapping[str, Any]) -> list[str]:
    working_set = synth.get("working_set") if isinstance(synth.get("working_set"), list) else []
    current_wave = synth.get("current_wave") if isinstance(synth.get("current_wave"), Mapping) else {}
    return _dedupe_resume_strings(
        [
            *(item.get("path") for item in working_set if isinstance(item, Mapping)),
            *(current_wave.get("target_paths") or []),
        ],
        limit=12,
    )


def _phase_resume_closeout_surface(
    phase_entry: Mapping[str, Any],
    scaffold_payload: Mapping[str, Any],
) -> dict[str, Any]:
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    phase_ref = _phase_command_token(phase_entry, None) or str(phase_entry.get("phase_id") or "").strip()
    whiteboard_contract = (
        dict(scaffold_payload.get("whiteboard_contract"))
        if isinstance(scaffold_payload.get("whiteboard_contract"), Mapping)
        else {}
    )
    closeout_rel = canonicalize_write_path(str(whiteboard_contract.get("phase_closeout_path") or "").strip()) or (
        canonicalize_write_path(f"{phase_dir}/phase_closeout.json") or ""
    )
    return {
        "phase_closeout_path": closeout_rel or None,
        "phase_closeout_exists": bool(closeout_rel and (state.REPO_ROOT / closeout_rel).exists()),
        "preview_command": f"python3 kernel.py --close-phase {shlex.quote(phase_ref)}" if phase_ref else None,
        "live_command": f"python3 kernel.py --close-phase {shlex.quote(phase_ref)} --live" if phase_ref else None,
    }


def _phase_resume_controller_stage(
    *,
    closeout_state: str,
    closeout_exists: bool,
    scaffold_payload: Mapping[str, Any],
) -> str:
    scaffold_status = str(
        scaffold_payload.get("status")
        or scaffold_payload.get("authoring_status")
        or ""
    ).strip().lower()
    if closeout_exists or scaffold_status == "closed":
        return "closed"
    if closeout_state in {"pending_resume", "failed_recovery_pending"}:
        return "recovery_required"
    if closeout_state == "pending_assimilation":
        return "assimilation_required"
    if closeout_state == "inflight":
        return "waiting_for_runtime"
    if closeout_state == "orphaned_session":
        return "orphaned_runtime"
    return "ready_for_next_wave"


def _phase_resume_next_action(
    *,
    phase_entry: Mapping[str, Any],
    closeout_state: str,
    controller_stage: str,
) -> dict[str, Any]:
    phase_ref = _phase_command_token(phase_entry, None) or str(phase_entry.get("phase_id") or "").strip()
    if controller_stage == "recovery_required":
        return {
            "key": "recover_wave",
            "summary": "The latest detached observe wave finished without synth evolution or landed in a failed-recovery state. Recover the wave into synth artifacts first.",
            "command": f"./repo-python kernel.py --phase-dock {shlex.quote(phase_ref)} --dock-operation evolve_subphase_seed --dock-session latest --live",
        }
    if controller_stage == "assimilation_required":
        return {
            "key": "assimilate_wave",
            "summary": "The synth-evolution artifacts exist. Assimilate them into the live synth and ledger now.",
            "command": f"./repo-python kernel.py --phase-assimilate {shlex.quote(phase_ref)} --live",
        }
    if controller_stage == "waiting_for_runtime":
        return {
            "key": "inspect_runtime",
            "summary": "The detached observe runtime is still in flight. Read the phase card or session digest instead of launching more work.",
            "command": f"python3 kernel.py --phase {shlex.quote(phase_ref)}",
        }
    if controller_stage == "orphaned_runtime":
        return {
            "key": "inspect_orphaned_runtime",
            "summary": "The latest session no longer resolves back to a live phase entry. Inspect the session and reconcile it before resuming.",
            "command": f"python3 kernel.py --phase {shlex.quote(phase_ref)}",
        }
    if controller_stage == "closed":
        return {
            "key": "inspect_closed_subphase",
            "summary": "This subphase is already closed. Read the closeout and family memory surfaces rather than resuming work.",
            "command": f"python3 kernel.py --phase {shlex.quote(phase_ref)}",
        }
    return {
        "key": "resume_subphase",
        "summary": (
            "The subphase has no detached closeout gap. Resume from the live synth packet and let the phase controller choose the next bounded wave."
            if closeout_state == "ready_for_next_wave"
            else "Resume from the live synth packet and phase controller state."
        ),
        "command": f"python3 kernel.py --phase-step {shlex.quote(phase_ref)} --live",
    }


def _phase_resume_attention(
    *,
    closeout_state: str,
    reason: str,
    next_action: Mapping[str, Any],
    controller_stage: str,
) -> dict[str, Any]:
    needs_attention = controller_stage in {"recovery_required", "orphaned_runtime"}
    wake_requested = controller_stage in {"recovery_required", "assimilation_required"}
    summary = reason or "Resume from the persisted subphase artifacts."
    if controller_stage == "closed":
        summary = "The subphase is already closed. Use the closeout packet and family memory as the continuity surface."
    elif controller_stage == "ready_for_next_wave":
        summary = "The subphase is resumable from the live synth and ledger surfaces."
    return {
        "needs_attention": needs_attention,
        "pause_pipeline": False,
        "wake_requested": wake_requested,
        "reason_key": closeout_state or controller_stage,
        "summary": summary,
        "details": _dedupe_resume_strings(
            [
                reason,
                str(next_action.get("summary") or "").strip(),
            ],
            limit=4,
        ),
    }


def _build_phase_resume_bundle(phase_entry: Mapping[str, Any]) -> dict[str, Any]:
    scaffold_path = _phase_scaffold_path_for_entry(phase_entry)
    synth_path = _phase_file_from_entry(phase_entry, "synth_seed.json")
    meta_ledger_path = _phase_file_from_entry(phase_entry, "meta_ledger.json")
    scaffold_payload = safe_load_json(scaffold_path)
    synth_payload = safe_load_json(synth_path)
    meta_ledger = safe_load_json(meta_ledger_path)
    if not isinstance(scaffold_payload, Mapping):
        raise ValueError(f"Invalid phase_scaffold.json: {state.rel(scaffold_path)}")
    if not isinstance(synth_payload, Mapping):
        raise ValueError(f"Invalid synth_seed.json: {state.rel(synth_path)}")
    if not isinstance(meta_ledger, Mapping):
        raise ValueError(f"Invalid meta_ledger.json: {state.rel(meta_ledger_path)}")

    normalized = normalize_synth_payload(synth_payload, phase_scaffold=scaffold_payload)
    if not isinstance(normalized, Mapping):
        raise ValueError("Could not normalize synth_seed.json for phase resume.")

    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    if not phase_dir:
        raise ValueError("phase_dir is required for phase resume.")
    phase_ref = _phase_command_token(phase_entry, None) or str(phase_entry.get("phase_id") or "").strip()
    current_wave = dict(normalized.get("current_wave") or {})
    family_dir = canonicalize_write_path(str(phase_entry.get("family_dir") or "").strip()) or ""
    latest_session = _phase_resume_audit_item(phase_entry)
    closeout_surface = _phase_resume_closeout_surface(phase_entry, scaffold_payload)
    controller_stage = _phase_resume_controller_stage(
        closeout_state=str(latest_session.get("closeout_state") or "").strip(),
        closeout_exists=bool(closeout_surface.get("phase_closeout_exists")),
        scaffold_payload=scaffold_payload,
    )
    next_action = _phase_resume_next_action(
        phase_entry=phase_entry,
        closeout_state=str(latest_session.get("closeout_state") or "").strip(),
        controller_stage=controller_stage,
    )
    attention = _phase_resume_attention(
        closeout_state=str(latest_session.get("closeout_state") or "").strip(),
        reason=str(latest_session.get("reason") or "").strip(),
        next_action=next_action,
        controller_stage=controller_stage,
    )
    artifact_paths = _phase_resume_artifact_paths(phase_entry)
    compression = _phase_resume_compression(meta_ledger, normalized)
    recent_history = _phase_resume_recent_history(meta_ledger)
    scope_files = _phase_resume_scope_files(normalized)
    observe_manifest_path = str(latest_session.get("manifest_path") or "").strip() or None
    state_payload = {
        "kind": "subphase_controller_state",
        "schema_version": _PHASE_RESUME_STATE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_id": f"SUBPHASE_{str(phase_entry.get('phase_id') or '').strip()}",
        "phase_id": phase_entry.get("phase_id"),
        "phase_number": phase_entry.get("phase_number"),
        "phase_title": phase_entry.get("phase_title"),
        "phase_dir": phase_dir,
        "family_dir": family_dir or None,
        "stage": controller_stage,
        "controller_phase": "subphase_resume",
        "current_layer_kind": "subphase",
        "current_layer_id": str(phase_entry.get("phase_id") or phase_entry.get("phase_number") or "").strip() or None,
        "current_task_id": str(current_wave.get("wave_id") or "").strip() or None,
        "gate_reason": attention.get("reason_key"),
        "routing_decision": {
            "decision": next_action.get("key"),
            "summary": next_action.get("summary"),
            "closeout_state": latest_session.get("closeout_state"),
        },
        "cycle": int((normalized.get("meta") or {}).get("current_cycle") or 0),
        "observe_session_id": latest_session.get("observe_id"),
        "observe_manifest_path": observe_manifest_path,
        "observe_plan_path": str((normalized.get("assimilation_targets") or {}).get("observe_plan_path") or "").strip() or None,
        "meta_ledger_path": state.rel(meta_ledger_path),
        "synth_seed_path": state.rel(synth_path),
        "phase_scaffold_path": state.rel(scaffold_path),
        "continuation_summary_path": latest_session.get("continuation_summary_path"),
        "synth_delta_path": latest_session.get("delta_path"),
        "phase_closeout_path": closeout_surface.get("phase_closeout_path"),
        "next_action": next_action,
        "history": recent_history,
    }
    recommended_commands = {
        "status": f"python3 kernel.py --phase-resume {shlex.quote(phase_ref)}",
        "write_resume": f"python3 kernel.py --phase-resume {shlex.quote(phase_ref)} --live",
        "advance": f"python3 kernel.py --phase-resume {shlex.quote(phase_ref)} --live --advance",
        "inspect_phase": f"python3 kernel.py --phase {shlex.quote(phase_ref)}",
        "next_step": str(next_action.get("command") or "").strip(),
        "close_phase_preview": closeout_surface.get("preview_command"),
        "close_phase_live": closeout_surface.get("live_command"),
    }
    source_context = {
        "generated_at": state_payload["generated_at"],
        "repo_root": str(state.REPO_ROOT),
        "pipeline_id": state_payload["pipeline_id"],
        "state_path": artifact_paths["state_path"],
        "phase_dir": phase_dir,
        "family_dir": family_dir or None,
        "artifact_dir": phase_dir,
        "stage": controller_stage,
        "cycle": state_payload["cycle"],
        "controller_phase": state_payload["controller_phase"],
        "current_layer_id": state_payload["current_layer_id"],
        "current_layer_kind": state_payload["current_layer_kind"],
        "current_task_id": state_payload["current_task_id"],
        "gate_reason": state_payload.get("gate_reason"),
        "routing_decision": state_payload.get("routing_decision"),
        "observe_session_id": latest_session.get("observe_id"),
        "observe_manifest_path": observe_manifest_path,
        "observe_plan_path": state_payload.get("observe_plan_path"),
        "resume_contract_path": None,
        "cycle_summary_path": latest_session.get("continuation_summary_path"),
        "cycle_assimilation_path": latest_session.get("delta_path"),
        "active_scope": {
            "active_scope_files": scope_files,
            "active_scope_count": len(scope_files),
            "known_relevant_files": scope_files,
            "known_relevant_count": len(scope_files),
            "selected_shard_count": 0,
            "controller_phase": "subphase_resume",
            "current_layer_kind": "subphase",
            "current_layer_id": str(phase_entry.get("phase_id") or phase_entry.get("phase_number") or "").strip() or None,
            "current_task_id": str(current_wave.get("wave_id") or "").strip() or None,
        },
        "codex_attention": attention,
        "next_action": next_action,
        "latest_history": recent_history,
        "recommended_commands": recommended_commands,
        "artifacts": {
            "resume_json_path": artifact_paths["resume_json_path"],
            "resume_md_path": artifact_paths["resume_md_path"],
            "attention_json_path": artifact_paths["attention_json_path"],
            "attention_md_path": artifact_paths["attention_md_path"],
        },
        "resume_artifact_paths": _dedupe_resume_strings(
            [
                artifact_paths["state_path"],
                artifact_paths["resume_json_path"],
                artifact_paths["attention_json_path"],
                state.rel(synth_path),
                state.rel(meta_ledger_path),
                state.rel(scaffold_path),
                latest_session.get("delta_path"),
                latest_session.get("continuation_summary_path"),
                closeout_surface.get("phase_closeout_path"),
            ]
        ),
        "key_files": scope_files,
    }
    continuation_packet = build_continuation_packet(
        state.REPO_ROOT,
        wait_kind="pipeline_signal",
        artifact_dir=phase_dir,
        source_context=source_context,
    )
    resume_payload = {
        "kind": "phase_resume_packet",
        "schema_version": _PHASE_RESUME_PACKET_VERSION,
        "generated_at": state_payload["generated_at"],
        "state_path": artifact_paths["state_path"],
        "continuation_packet_path": continuation_packet.get("continuation_packet_path"),
        "continuation_packet_fingerprint": continuation_packet.get("continuation_packet_fingerprint"),
        "phase": {
            "phase_id": phase_entry.get("phase_id"),
            "phase_number": phase_entry.get("phase_number"),
            "phase_title": phase_entry.get("phase_title"),
            "phase_dir": phase_dir,
            "family_dir": family_dir or None,
        },
        "lifecycle": {
            "controller_stage": controller_stage,
            "closeout_state": latest_session.get("closeout_state"),
            "reason": latest_session.get("reason"),
            "session_lifecycle_stage": latest_session.get("lifecycle_stage"),
        },
        "wave": {
            "wave_id": current_wave.get("wave_id"),
            "status": current_wave.get("status"),
            "mode": normalized.get("execution_mode"),
            "stage_kind": current_wave.get("stage_kind"),
        },
        "latest_session": {
            "observe_id": latest_session.get("observe_id"),
            "session_slug": latest_session.get("session_slug"),
            "session_status": latest_session.get("session_status"),
            "lifecycle_stage": latest_session.get("lifecycle_stage"),
            "round_id": latest_session.get("round_id"),
            "primary_artifact": latest_session.get("primary_artifact"),
        },
        "assimilation": {
            "delta_path": latest_session.get("delta_path"),
            "delta_exists": bool(latest_session.get("delta_exists")),
            "continuation_summary_path": latest_session.get("continuation_summary_path"),
            "continuation_summary_exists": bool(latest_session.get("continuation_summary_exists")),
        },
        "closeout": closeout_surface,
        "compression": compression,
        "next_action": next_action,
        "codex_attention": attention,
        "recommended_commands": recommended_commands,
        "resume_artifact_paths": source_context["resume_artifact_paths"],
    }
    attention_payload = {
        "generated_at": state_payload["generated_at"],
        "phase_id": phase_entry.get("phase_id"),
        "phase_number": phase_entry.get("phase_number"),
        "phase_title": phase_entry.get("phase_title"),
        "state_path": artifact_paths["state_path"],
        "continuation_packet_path": continuation_packet.get("continuation_packet_path"),
        "continuation_packet_fingerprint": continuation_packet.get("continuation_packet_fingerprint"),
        "controller_stage": controller_stage,
        "closeout_state": latest_session.get("closeout_state"),
        **attention,
        "next_action": next_action,
    }
    public_payload = {
        "kind": "kernel.phase_resume",
        "mode": "preview",
        "status": "preview_ready",
        "phase": resume_payload["phase"],
        "lifecycle": resume_payload["lifecycle"],
        "wave": resume_payload["wave"],
        "latest_session": resume_payload["latest_session"],
        "next_action": next_action,
        "closeout": closeout_surface,
        "compression": compression,
        "artifacts": artifact_paths,
        "recommended_commands": recommended_commands,
        "writes": [
            {"path": artifact_paths["state_path"], "kind": "subphase_controller_state"},
            {"path": artifact_paths["resume_json_path"], "kind": "pipeline_resume"},
            {"path": artifact_paths["resume_md_path"], "kind": "pipeline_resume_note"},
            {"path": artifact_paths["attention_json_path"], "kind": "pipeline_attention"},
            {"path": artifact_paths["attention_md_path"], "kind": "pipeline_attention_note"},
            {"path": continuation_packet.get("continuation_packet_path"), "kind": "continuation_packet"},
        ],
    }
    return {
        "public_payload": public_payload,
        "state_payload": state_payload,
        "resume_payload": resume_payload,
        "attention_payload": attention_payload,
        "continuation_packet": continuation_packet,
        "artifact_paths": artifact_paths,
    }


def _write_phase_resume_bundle(bundle: Mapping[str, Any]) -> list[dict[str, str]]:
    artifact_paths = dict(bundle.get("artifact_paths") or {})
    state_payload = dict(bundle.get("state_payload") or {})
    resume_payload = dict(bundle.get("resume_payload") or {})
    attention_payload = dict(bundle.get("attention_payload") or {})
    continuation_packet = dict(bundle.get("continuation_packet") or {})

    writes: list[dict[str, str]] = []
    for rel_path, payload, kind in (
        (artifact_paths.get("state_path"), state_payload, "subphase_controller_state"),
        (artifact_paths.get("resume_json_path"), resume_payload, "pipeline_resume"),
        (artifact_paths.get("attention_json_path"), attention_payload, "pipeline_attention"),
    ):
        rel = str(rel_path or "").strip()
        if not rel:
            continue
        target = state.REPO_ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical_json_text(payload), encoding="utf-8")
        writes.append({"path": rel, "kind": kind})

    resume_md_rel = str(artifact_paths.get("resume_md_path") or "").strip()
    if resume_md_rel:
        resume_md_lines = [
            "# Subphase Resume Packet",
            "",
            f"- Phase: `{((resume_payload.get('phase') or {}).get('phase_number') or (resume_payload.get('phase') or {}).get('phase_id') or '')}`",
            f"- Title: `{((resume_payload.get('phase') or {}).get('phase_title') or '')}`",
            f"- Controller stage: `{((resume_payload.get('lifecycle') or {}).get('controller_stage') or '')}`",
            f"- Closeout state: `{((resume_payload.get('lifecycle') or {}).get('closeout_state') or '')}`",
            f"- Wave: `{((resume_payload.get('wave') or {}).get('wave_id') or '')}` / `{((resume_payload.get('wave') or {}).get('status') or '')}`",
            f"- Continuation packet: `{resume_payload.get('continuation_packet_path') or ''}`",
            "",
            f"Next action: `{((resume_payload.get('next_action') or {}).get('command') or '')}`",
            "",
            "## Compression",
            *(f"- {item}" for item in ((resume_payload.get('compression') or {}).get('recent_summaries') or [])),
        ]
        target = state.REPO_ROOT / resume_md_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(resume_md_lines).rstrip() + "\n", encoding="utf-8")
        writes.append({"path": resume_md_rel, "kind": "pipeline_resume_note"})

    attention_md_rel = str(artifact_paths.get("attention_md_path") or "").strip()
    if attention_md_rel:
        attention_md_lines = [
            "# Subphase Attention Surface",
            "",
            f"- Phase: `{attention_payload.get('phase_number') or attention_payload.get('phase_id') or ''}`",
            f"- Reason key: `{attention_payload.get('reason_key') or ''}`",
            f"- Needs attention: `{bool(attention_payload.get('needs_attention'))}`",
            f"- Wake requested: `{bool(attention_payload.get('wake_requested'))}`",
            "",
            f"{attention_payload.get('summary') or ''}",
            "",
            f"Next action: `{((attention_payload.get('next_action') or {}).get('command') or '')}`",
        ]
        target = state.REPO_ROOT / attention_md_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(attention_md_lines).rstrip() + "\n", encoding="utf-8")
        writes.append({"path": attention_md_rel, "kind": "pipeline_attention_note"})

    continuation_rel, _ = write_continuation_packet(
        state.REPO_ROOT,
        artifact_dir=str((resume_payload.get("phase") or {}).get("phase_dir") or ""),
        packet=continuation_packet,
    )
    writes.append({"path": continuation_rel, "kind": "continuation_packet"})
    return writes


def _run_phase_resume_next_action(
    *,
    phase_token: str | None,
    next_action: Mapping[str, Any],
    force: bool = False,
) -> tuple[int, dict[str, Any] | None, str]:
    action_key = str(next_action.get("key") or "").strip()
    if action_key == "recover_wave":
        runner = lambda: cmd_phase_dock(
            phase_token,
            operation="evolve_subphase_seed",
            session_ref="latest",
            consumer=None,
            bridge_provider=None,
            bridge_route=None,
            bridge_timeout_s=0.0,
            live=True,
            write_packet_to=None,
            write_dock_to=None,
            resume=True,
        )
    elif action_key == "assimilate_wave":
        runner = lambda: cmd_phase_assimilate(phase_token, live=True)
    elif action_key == "resume_subphase":
        runner = lambda: cmd_phase_step(phase_token, live=True, force=force)
    elif action_key == "close_subphase":
        runner = lambda: cmd_close_phase(phase_token, live=True)
    else:
        raise ValueError(
            "phase-resume --advance requires a live lifecycle edge "
            f"(got `{action_key or 'unknown'}`)."
        )

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = runner()
    raw = stdout.getvalue().strip()
    payload: dict[str, Any] | None = None
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = None
    return code, payload, raw


REACTIONS_LEDGER_REL = "tools/meta/control/reactions_ledger.jsonl"
_REACTIONS_LEDGER_TAIL_CHUNK_BYTES = 64 * 1024
ORCHESTRATION_STATE_REL = "tools/meta/control/orchestration_state.json"


def _profile_phase(profile_sink: list[dict[str, Any]] | None, phase: str, started: float) -> None:
    if profile_sink is not None:
        profile_sink.append({"phase": phase, "ms": round((perf_counter() - started) * 1000, 3)})


def _iter_text_lines_newest_first(path: Path, *, chunk_size: int | None = None) -> Iterator[str]:
    """Yield text lines from a file tail-first without decoding the whole file."""
    read_size_limit = max(1, int(chunk_size or _REACTIONS_LEDGER_TAIL_CHUNK_BYTES))
    try:
        position = path.stat().st_size
        if position <= 0:
            return
        carry = b""
        with path.open("rb") as handle:
            while position > 0:
                read_size = min(read_size_limit, position)
                position -= read_size
                handle.seek(position)
                parts = handle.read(read_size).split(b"\n")
                if carry:
                    parts[-1] += carry
                carry = parts[0]
                for raw in reversed(parts[1:]):
                    raw = raw.strip()
                    if raw:
                        yield raw.decode("utf-8", errors="replace")
            if carry.strip():
                yield carry.strip().decode("utf-8", errors="replace")
    except OSError:
        return


def _pulse_selected_action(state_payload: Mapping[str, Any]) -> dict[str, Any]:
    actions = state_payload.get("agent_actions") if isinstance(state_payload.get("agent_actions"), list) else []
    if actions:
        first = actions[0]
        if isinstance(first, Mapping):
            return {
                "mode": str(first.get("mode") or "").strip() or None,
                "summary": str(first.get("summary") or "").strip(),
                "command": str(first.get("command") or "").strip() or None,
                "launch_recommended_now": bool(first.get("launch_recommended_now")),
            }
    decision = state_payload.get("decision") if isinstance(state_payload.get("decision"), Mapping) else {}
    return {
        "mode": str(decision.get("immediate_mode") or state_payload.get("active_driver") or "").strip() or None,
        "summary": str(decision.get("summary") or "").strip(),
        "command": str(decision.get("command") or "").strip() or None,
        "launch_recommended_now": bool(decision.get("launch_recommended_now")),
    }


def _pulse_cached_phase_driver(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    drivers = payload.get("drivers")
    if isinstance(drivers, Mapping):
        candidate = drivers.get("phase_pipeline")
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(drivers, list):
        for driver in drivers:
            if isinstance(driver, Mapping) and str(driver.get("driver_id") or "").strip() == "phase_pipeline":
                return driver
    return {}


def _pulse_active_phase_token(activation: Mapping[str, Any]) -> str:
    for key in ("phase_id", "phase_number", "phase_title"):
        token = str(activation.get(key) or "").strip()
        if token:
            return token.replace(".", "_") if key == "phase_id" else token
    phase_dir = str(activation.get("phase_dir") or "").strip()
    return phase_dir or "latest"


def _pulse_cached_orchestration_phase_matches(payload: Mapping[str, Any], activation: Mapping[str, Any]) -> bool:
    phase_driver = _pulse_cached_phase_driver(payload)
    if not phase_driver:
        return False
    active_dir = canonicalize_write_path(str(activation.get("phase_dir") or "").strip())
    driver_dir = canonicalize_write_path(str(phase_driver.get("phase_dir") or "").strip())
    if active_dir and driver_dir:
        return active_dir == driver_dir

    active_aliases = {
        str(activation.get(key) or "").strip().replace(".", "_").lower()
        for key in ("phase_id", "phase_number", "phase_title")
        if str(activation.get(key) or "").strip()
    }
    driver_aliases = {
        str(phase_driver.get(key) or "").strip().replace(".", "_").lower()
        for key in ("phase_ref", "phase_id", "phase_number", "phase_title")
        if str(phase_driver.get(key) or "").strip()
    }
    return bool(active_aliases & driver_aliases) if active_aliases or driver_aliases else True


def _pulse_phase_rearm_runtime(
    activation: Mapping[str, Any],
    cached_payload: Mapping[str, Any],
) -> dict[str, Any]:
    phase_token = _pulse_active_phase_token(activation)
    command = f"python3 pipeline_overnight.py --phase {phase_token} --wake-agent auto --sleep-policy keep_awake"
    coordination = cached_payload.get("coordination") if isinstance(cached_payload.get("coordination"), Mapping) else {}
    if not coordination:
        coordination = {
            "current_owner": {
                "actor_id": "control_room_manager",
                "driver_id": "no_active_runtime_phase",
            },
            "next_handoff": {
                "actor_id": "human_operator",
                "mode": "manual_documentation",
            },
        }
    return {
        "kind": "orchestration_state",
        "state": "no_active_runtime_phase",
        "updated_at": activation.get("changed_at") or activation.get("active_phase_changed_at") or cached_payload.get("updated_at"),
        "summary": "No non-deprecated phase runtime is armed. Bootstrap the active 09.x line explicitly instead of reviving legacy pipeline residue.",
        "command": command,
        "gate_reason": "no_active_runtime_phase",
        "can_continue": False,
        "drivers": cached_payload.get("drivers"),
        "event_log": cached_payload.get("event_log") if isinstance(cached_payload.get("event_log"), Mapping) else None,
        "coordination": coordination,
        "source": "quick_phase_rearm_projection",
        "projection_status": "phase_patched_without_reaction_refresh",
    }


def _pulse_ready_deferred_reactions(*, limit: int = 5) -> list[dict[str, Any]]:
    """Project reactions that are ready to fire but aren't winning the tick.

    The reactions engine's `build_reactions_snapshot` already evaluates every
    reaction's `would_fire_now` and `preview_reason`, but only ONE reaction
    fires per tick (the highest-priority `can_fire` winner).  Lower-priority
    reactions that are simultaneously fireable show up in the snapshot with
    `would_fire_now=True, preview_reason="would fire"` — but without an
    agent-entry projection, an operator looking at pulse cannot tell that
    a safe autonomous reaction is *ready and deferred* by scheduler priority,
    not silently broken.

    Per `local_to_general_propagation.md` § "Autonomy must surface through
    the agent entrypoint": the durable engine state distinguishes "ready
    but losing" from "not ready," and pulse is the surface where the
    operator should see the distinction.

    Returns up to `limit` compact items::

        {
          "reaction_id":   str,
          "operation_id":  str | None,
          "priority":      str,
          "preview_reason":str,                 # always "would fire" here
          "target_row_id": str,                 # rendered from action.parameters
          "blocked_by":    str | None,          # active_reaction_id if any
        }

    Tolerant: empty list on import error, snapshot error, or missing data;
    never raises.  Pulse uses the cached snapshot lane so agent-entry HUDs do
    not recompute live reaction signals.
    """
    try:
        from tools.meta.control import reactions_engine as _engine

        try:
            snapshot = _engine.build_reactions_snapshot(state.REPO_ROOT, signal_mode="cached")
        except TypeError:
            snapshot = _engine.build_reactions_snapshot(state.REPO_ROOT)
    except Exception:
        return []
    if not isinstance(snapshot, dict):
        return []
    active = str(snapshot.get("active_reaction_id") or "").strip() or None
    # Barrier ownership: when the engine is awaiting a barrier, the barrier
    # owner is the actual blocker for every other fireable reaction, even
    # though state.active_reaction_id may be stale or unset.  Consult
    # awaiting_barriers first so READY (DEFERRED) names the real cause
    # ("blocked by hologram_stale running operation_completion") rather
    # than the misleading "deferred by scheduler priority."
    barriers = snapshot.get("awaiting_barriers")
    barrier_owner: str | None = None
    barrier_kind: str | None = None
    if isinstance(barriers, list) and barriers:
        first = barriers[0] if isinstance(barriers[0], dict) else None
        if first:
            barrier_owner = str(first.get("reaction_id") or "").strip() or None
            barrier_kind = str(first.get("kind") or "").strip() or None
    blocker = barrier_owner or active
    bound = max(1, int(limit))
    deferred: list[dict[str, Any]] = []
    for reaction in snapshot.get("reactions") or []:
        if not isinstance(reaction, dict):
            continue
        if not reaction.get("would_fire_now"):
            continue
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        if not reaction_id:
            continue
        # The active winner shows up via AUTONOMOUS FIRES once it fires.
        # The barrier owner is actively running its operation, not deferred.
        # Exclude both so READY (DEFERRED) only lists genuinely-waiting
        # candidates.
        if active and reaction_id == active:
            continue
        if barrier_owner and reaction_id == barrier_owner:
            continue
        action = reaction.get("action") if isinstance(reaction.get("action"), dict) else {}
        params = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
        deferred.append(
            {
                "reaction_id": reaction_id,
                "operation_id": action.get("operation_id"),
                "priority": str(reaction.get("priority") or "").strip(),
                "preview_reason": str(reaction.get("preview_reason") or "").strip(),
                "target_row_id": str(params.get("target_row_id") or "").strip(),
                "blocked_by": blocker,
                "barrier_kind": barrier_kind if barrier_owner else None,
            }
        )
        if len(deferred) >= bound:
            break
    return deferred


def _pulse_recent_autonomous_fires(*, limit: int = 5) -> list[dict[str, Any]]:
    """Tail recent reaction-fire rows from the reactions ledger and project compact items.

    Surfaces autonomous reaction fires (kind=="reaction_fired") at the agent
    entrypoint per `local_to_general_propagation.md` § Governing principles
    "Autonomy must surface through the agent entrypoint."  Without this,
    enabled-by-default reactions like
    `provider_transform_materialize_after_catalog_signal` would fire
    invisibly — the operator experiences this repo through agents, so agent
    entry surfaces are the product surface.

    Returns newest-first list of compact items::

        {
          "reaction_id":     str,
          "operation_id":    str,
          "fired_at":        ISO timestamp str,
          "target_row_id":   str (from parameters; "" if absent),
          "signal_digest":   str,
          "ledger_path":     repo-relative ledger path,
        }

    Tolerant: empty list on missing or unreadable ledger; never raises.
    """
    ledger_path = state.REPO_ROOT / REACTIONS_LEDGER_REL
    rel_path = state.rel(ledger_path)
    if not ledger_path.is_file():
        return []
    bound = max(1, int(limit))
    rows: list[dict[str, Any]] = []
    for line in _iter_text_lines_newest_first(ledger_path):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        if str(parsed.get("kind") or "") != "reaction_fired":
            continue
        params = parsed.get("parameters") if isinstance(parsed.get("parameters"), dict) else {}
        rows.append(
            {
                "reaction_id": str(parsed.get("reaction_id") or "").strip(),
                "operation_id": str(parsed.get("operation_id") or "").strip(),
                "fired_at": str(parsed.get("fired_at") or parsed.get("recorded_at") or "").strip(),
                "target_row_id": str(params.get("target_row_id") or "").strip(),
                "signal_digest": str(parsed.get("signal_digest") or "").strip(),
                "ledger_path": rel_path,
            }
        )
        if len(rows) >= bound:
            break
    return rows


def _pulse_recommended_actions(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    runtime = snapshot.get("latest_runtime") if isinstance(snapshot.get("latest_runtime"), dict) else {}
    builder = snapshot.get("builder") if isinstance(snapshot.get("builder"), dict) else {}
    active_plan = snapshot.get("active_plan") if isinstance(snapshot.get("active_plan"), dict) else {}
    docfix_plan = snapshot.get("latest_docfix_plan") if isinstance(snapshot.get("latest_docfix_plan"), dict) else {}
    doctrine = snapshot.get("doctrine") if isinstance(snapshot.get("doctrine"), dict) else {}
    routing = snapshot.get("routing_projection") if isinstance(snapshot.get("routing_projection"), dict) else {}
    closeout = snapshot.get("closeout_gap") if isinstance(snapshot.get("closeout_gap"), dict) else {}
    closeout_limited = bool(closeout.get("candidate_scan_limited"))
    provider_plane = snapshot.get("provider_plane") if isinstance(snapshot.get("provider_plane"), dict) else {}
    active_execution = (
        snapshot.get("active_execution_constellation")
        if isinstance(snapshot.get("active_execution_constellation"), Mapping)
        else {}
    )
    live_campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    active_execution_hot = _pulse_has_hot_execution(active_execution)

    campaign_rows = [item for item in live_campaigns if isinstance(item, Mapping)]
    if campaign_rows:
        first_campaign = campaign_rows[0]
        command = str(first_campaign.get("drilldown_command") or "").strip()
        workitem_id = str(
            first_campaign.get("workitem_id") or first_campaign.get("id") or ""
        ).strip()
        title = _pulse_short_text(first_campaign.get("title"), limit=100)
        if command:
            actions.append(
                {
                    "command": command,
                    "reason": (
                        f"Currently hot Task Ledger campaign"
                        f"{f' {workitem_id}' if workitem_id else ''}"
                        f"{f': {title}' if title else ''}."
                    ),
                }
            )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    awareness_cards = (
        live_sessions.get("awareness_cards")
        if isinstance(live_sessions.get("awareness_cards"), list)
        else []
    )
    heartbeat_gap_rows = (
        live_sessions.get("heartbeat_gap_claim_sessions")
        if isinstance(live_sessions.get("heartbeat_gap_claim_sessions"), list)
        else []
    )
    active_claim_count = int(session_counts.get("active_claims") or 0)
    session_rows = (
        live_sessions.get("sessions")
        if isinstance(live_sessions.get("sessions"), list)
        else []
    )
    if active_claim_count or session_rows or awareness_cards:
        drilldowns = (
            live_sessions.get("drilldown_commands")
            if isinstance(live_sessions.get("drilldown_commands"), Mapping)
            else {}
        )
        command = str(drilldowns.get("cards") or "").strip()
        if command:
            actions.append(
                {
                    "command": command,
                    "reason": (
                        "Currently hot Work Ledger sessions/claims are the live Type A substrate; "
                        "open the compact seed-speed packet before reviving dormant phase runtime."
                    ),
                }
            )

    rt_state = str(runtime.get("state") or "").strip()
    kind = str(runtime.get("kind") or "").strip()
    control_plane_locked = kind == "orchestration_state"
    dormant_control_plane = control_plane_locked and (
        rt_state == "no_active_runtime_phase"
        or str(runtime.get("gate_reason") or "").strip() == "no_active_runtime_phase"
    )
    deferred_runtime_action: dict[str, str] | None = None
    if control_plane_locked:
        command = str(runtime.get("command") or "").strip()
        summary = str(runtime.get("summary") or "").strip()
        if command:
            runtime_action = {
                "command": command,
                "reason": summary or "Control-plane authority already selected the next runtime action from disk state.",
            }
            if dormant_control_plane and active_execution_hot:
                runtime_action["reason"] = (
                    "Dormant declared-phase rearm action; use only when intentionally "
                    "restarting that phase after checking the hot Task/Work Ledger surfaces."
                )
                deferred_runtime_action = runtime_action
            else:
                actions.append(runtime_action)
        else:
            actions.append(
                {
                    "command": "python3 run_control_room.py",
                    "reason": "The control plane is blocked on review; use the control room instead of launching another driver blind.",
                }
            )
    residual_lanes = snapshot.get("residual_lanes") if isinstance(snapshot.get("residual_lanes"), list) else []
    navigation_lane = next(
        (
            item
            for item in residual_lanes
            if isinstance(item, Mapping) and str(item.get("lane_id") or "") == "navigation_enforcement"
        ),
        None,
    )
    if isinstance(navigation_lane, Mapping):
        entry_command = str(navigation_lane.get("entry_command") or "").strip()
        if entry_command:
            active_phase_label = _pulse_active_execution_phase_label(active_execution)
            actions.append(
                {
                    "command": entry_command,
                    "reason": (
                        f"{active_phase_label} has a legal navigation-enforcement residual lane; use the coverage matrix "
                        "when the task is about first-contact coverage, route behavior, or process-audit navigation failures."
                    ),
                }
            )
    provider_actions = (
        provider_plane.get("recommended_next_actions")
        if isinstance(provider_plane.get("recommended_next_actions"), list)
        else []
    )
    if provider_actions:
        first = provider_actions[0] if isinstance(provider_actions[0], Mapping) else {}
        command = str(first.get("command") or "").strip()
        if command:
            actions.append(
                {
                    "command": command,
                    "reason": str(
                        first.get("why")
                        or "Provider plane has a finite advisory next action surfaced through liveness."
                    ),
                }
            )
    _closeout_unresolved = int(
        closeout.get("failed_unresolved_count")
        if closeout.get("failed_unresolved_count") is not None
        else closeout.get("failed_recovery_count") or 0
    )
    if int(closeout.get("pending_closeout_count") or 0) > 0 or _closeout_unresolved > 0:
        actions.append(
            {
                "command": "python3 kernel.py --closeout-audit",
                "reason": (
                    f"{closeout.get('pending_closeout_count') or 0} finished sessions still need closeout and "
                    f"{_closeout_unresolved} need recovery."
                ),
            }
        )
    if kind == "grouped_observe" and rt_state and rt_state not in {"completed", "cancelled", "failed"}:
        actions.append(
            {
                "command": "python3 kernel.py --observe-status latest",
                "reason": f"Grouped observe runtime is still {rt_state}; inspect it before launching new bridge work.",
            }
        )
        if runtime.get("can_continue"):
            actions.append(
                {
                    "command": "python3 kernel.py --observe-continue latest",
                    "reason": "The latest observe runtime is resumable and still has pending or retryable groups.",
                }
            )

    if builder.get("exists") and int(builder.get("stale_phases") or 0) > 0:
        stale_names = ",".join(builder.get("stale_phase_names", [])[:9])
        command = (
            f"python3 kernel.py --build --build-phases {stale_names}"
            if stale_names
            else "python3 kernel.py --build status"
        )
        actions.append(
            {
                "command": command,
                "reason": f"Hologram has {builder.get('stale_phases')} stale phases; rebuild only the stale slices first.",
            }
        )
    elif not builder.get("exists"):
        actions.append(
            {
                "command": "python3 kernel.py --build",
                "reason": "No hologram artifacts exist yet; build them before relying on self-model or compiled navigation.",
            }
        )

    docfix_path = str(docfix_plan.get("path") or "").strip()
    if not control_plane_locked and docfix_path and rt_state in {"", "completed", "cancelled", "failed"}:
        actions.append(
            {
                "command": f"python3 kernel.py --launch-observe --plan {docfix_path} --bridge --provider chatgpt",
                "reason": "A docfix observe plan already exists; launch it instead of re-scanning the repo.",
            }
        )
    elif not control_plane_locked and not docfix_path:
        actions.append(
            {
                "command": "python3 kernel.py --remediate",
                "reason": "No saved docfix plan is available; generate one from the miner/builder loop first.",
            }
        )

    active_plan_path = str(active_plan.get("path") or "").strip()
    if active_plan_path and not control_plane_locked:
        actions.append(
            {
                "command": f"python3 kernel.py --launch-observe --plan {active_plan_path}",
                "reason": "There is already an active observe plan on disk; validate or launch it before drafting another.",
            }
        )

    # Surface autonomous reaction fires the operator has not yet inspected.
    # Per the "Autonomy must surface through the agent entrypoint" governing
    # principle in local_to_general_propagation.md, every safe-bounded
    # autonomous fire must produce an agent-visible recommended action — the
    # ledger alone is durable but not at-entry-visible until pulse projects it.
    recent_fires = (
        snapshot.get("recent_autonomous_fires")
        if isinstance(snapshot.get("recent_autonomous_fires"), list)
        else []
    )
    materialize_fires = [
        fire
        for fire in recent_fires
        if isinstance(fire, dict)
        and fire.get("operation_id") == "provider_transform_materialize"
    ]
    # Deferred-but-ready provider materialization should also surface as a
    # recommended action: the reaction is fireable now but losing scheduler
    # priority, so the operator can either inspect via the materialize-row-job
    # CLI directly or wait for the engine to pick it.
    deferred_ready = (
        snapshot.get("ready_deferred_reactions")
        if isinstance(snapshot.get("ready_deferred_reactions"), list)
        else []
    )
    deferred_materialize = [
        item
        for item in deferred_ready
        if isinstance(item, dict)
        and item.get("operation_id") == "provider_transform_materialize"
    ]
    if not materialize_fires and deferred_materialize:
        item = deferred_materialize[0]
        target_row_id = str(item.get("target_row_id") or "").strip()
        reaction_id = str(item.get("reaction_id") or "").strip()
        blocked_by = str(item.get("blocked_by") or "").strip()
        barrier_kind = str(item.get("barrier_kind") or "").strip()
        if target_row_id:
            if blocked_by and barrier_kind:
                blocked_clause = (
                    f", blocked by {blocked_by} running {barrier_kind}"
                )
            elif blocked_by:
                blocked_clause = f", blocked by {blocked_by}"
            else:
                blocked_clause = ", waiting for the next available scheduler slot"
            actions.append(
                {
                    "command": (
                        f"./repo-python tools/meta/control/type_a_worker_harness.py "
                        f'materialize-row-job --target-row-id "{target_row_id}"'
                    ),
                    "reason": (
                        f"Autonomous draft materialization is READY but deferred "
                        f"({reaction_id or 'reaction'}, target_row_id={target_row_id}"
                        f"{blocked_clause}); inspect now via the CLI or wait for the "
                        f"engine to schedule it."
                    ),
                }
            )

    if materialize_fires:
        fire = materialize_fires[0]
        target_row_id = str(fire.get("target_row_id") or "").strip()
        reaction_id = str(fire.get("reaction_id") or "").strip()
        ledger = str(fire.get("ledger_path") or "").strip() or REACTIONS_LEDGER_REL
        if target_row_id:
            actions.append(
                {
                    "command": (
                        f"./repo-python tools/meta/control/type_a_worker_harness.py "
                        f'materialize-row-job --target-row-id "{target_row_id}"'
                    ),
                    "reason": (
                        f"Autonomous draft materialization fired ({reaction_id or 'reaction'}, "
                        f"target_row_id={target_row_id}); re-run the materializer to inspect the "
                        f"draft transform_job. Ledger: {ledger}."
                    ),
                }
            )
        else:
            actions.append(
                {
                    "command": f"cat {ledger}",
                    "reason": (
                        f"Autonomous draft materialization fired ({reaction_id or 'reaction'}); "
                        f"ledger row missing target_row_id, inspect ledger directly."
                    ),
                }
            )

    if int(doctrine.get("drift_docs") or 0) > 0:
        actions.append(
            {
                "command": "python3 kernel.py --stale",
                "reason": f"{doctrine.get('drift_docs')} doctrine docs show drift risk; inspect the stale report before trusting old guidance.",
            }
        )
        actions.append(
            {
                "command": "python3 kernel.py --doctrine-runtime",
                "reason": "Doctrine drift flagged; load codex/doctrine/doctrine_runtime.json via kernel (paths, mech_016 audit line, recovery macros).",
            }
        )

    if routing.get("stale"):
        actions.append(
            {
                "command": "./repo-python tools/meta/factory/build_routing_projection.py",
                "reason": "Generated routing block drifted; refresh AGENTS.md and routing_hologram.json before trusting first-hop entry docs.",
            }
        )

    if deferred_runtime_action:
        actions.append(deferred_runtime_action)

    actions.append(
        {
            "command": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
            "reason": "Recover the current note family, manifest, and continuation artifacts before widening search.",
        }
    )

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in actions:
        command = normalize_repo_kernel_command(str(item.get("command") or "").strip())
        if not command or command in seen:
            continue
        seen.add(command)
        deduped.append({"command": command, "reason": str(item.get("reason") or "").strip()})
    return deduped[:5]


def _pulse_active_execution_phase_label(active_execution: Mapping[str, Any]) -> str:
    anchor = (
        active_execution.get("declared_anchor")
        if isinstance(active_execution.get("declared_anchor"), Mapping)
        else {}
    )
    phase_id = str(anchor.get("phase_id") or "").strip()
    if not phase_id:
        stale_pointers = (
            active_execution.get("stale_decorative_pointers")
            if isinstance(active_execution.get("stale_decorative_pointers"), list)
            else []
        )
        for pointer in stale_pointers:
            if not isinstance(pointer, Mapping):
                continue
            phase_id = str(pointer.get("declared_phase_id") or pointer.get("phase_id") or "").strip()
            if phase_id:
                break
    return phase_id or "The active phase"


def _pulse_task_ledger_priority() -> dict[str, Any]:
    """Read-only Task Ledger priority surfacing for pulse.

    Surfaces the top ready/rank-1 WorkItem so cold agents see the P0 instead
    of routing past it into the active phase's runtime lane.
    """
    from system.lib.task_ledger_priority import priority_constellation

    constellation = priority_constellation(state.REPO_ROOT)
    top_schedulable = constellation.get("top_schedulable_workitem")
    top = constellation.get("top_ready_workitem")
    return {
        **constellation,
        "drilldown_command": (
            top_schedulable.get("drilldown_command")
            if isinstance(top_schedulable, Mapping)
            else top.get("drilldown_command")
            if isinstance(top, Mapping)
            else None
        ),
    }


_PULSE_CLOSEOUT_AUDIT_CACHE_TTL_S = 60.0
_PULSE_PROVIDER_PLANE_CACHE_TTL_S = 300.0


def _refresh_pulse_closeout_audit_cache(*, force_refresh: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    from system.lib.command_node_cache import cached_command_node

    def _build() -> dict[str, Any]:
        payload = _build_closeout_audit_payload(limit=5, candidate_scan_limit=120)
        return json.loads(json.dumps(payload, default=str))

    payload, cache_status = cached_command_node(
        state.REPO_ROOT,
        node_id=PULSE_CLOSEOUT_AUDIT_NODE_ID,
        key=PULSE_CLOSEOUT_AUDIT_KEY,
        input_paths=PULSE_CLOSEOUT_AUDIT_INPUT_PATHS,
        ttl_s=_PULSE_CLOSEOUT_AUDIT_CACHE_TTL_S,
        builder=_build,
        freshness_policy=PULSE_CLOSEOUT_AUDIT_FRESHNESS_POLICY,
        dynamic_inputs_manifested=False,
        force_refresh=force_refresh,
    )
    return dict(payload), cache_status


def _pulse_provider_plane_liveness(*, exact: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    if exact:
        try:
            return refresh_provider_plane_liveness_cache(
                state.REPO_ROOT,
                ttl_s=_PULSE_PROVIDER_PLANE_CACHE_TTL_S,
                force_refresh=True,
            )
        except Exception as build_exc:  # pragma: no cover - pulse must survive artifact skew
            return {
                "schema": "provider_plane_liveness_v0",
                "status": "error",
                "error": f"{type(build_exc).__name__}: {build_exc}",
            }, {
                "status": "error",
                "reason": "provider_plane_liveness_failed",
                "error_type": type(build_exc).__name__,
                "error": str(build_exc)[:240],
            }

    try:
        from system.lib.command_node_cache import peek_cached_command_node

        payload, cache_status = peek_cached_command_node(
            state.REPO_ROOT,
            node_id=PULSE_PROVIDER_PLANE_LIVENESS_NODE_ID,
            key=PULSE_PROVIDER_PLANE_LIVENESS_KEY,
            freshness_policy=PULSE_PROVIDER_PLANE_LIVENESS_FRESHNESS_POLICY,
            dynamic_inputs_manifested=False,
        )
        if isinstance(payload, Mapping):
            return dict(payload), cache_status
        return {
            "schema": "provider_plane_liveness_v0",
            "status": "deferred_missing_cache",
            "reason": "quick_pulse_does_not_probe_provider_plane",
            "repair_command": "./repo-python kernel.py --provider-plane-liveness",
        }, cache_status
    except Exception as exc:
        return {
            "schema": "provider_plane_liveness_v0",
            "status": "deferred_error",
            "reason": "provider_plane_cache_peek_failed",
            "repair_command": "./repo-python kernel.py --provider-plane-liveness",
        }, {
            "status": "deferred_error",
            "reason": "provider_plane_cache_peek_failed",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
        }


def _pulse_closeout_audit(*, exact: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    if exact:
        return _refresh_pulse_closeout_audit_cache(force_refresh=True)

    try:
        from system.lib.command_node_cache import peek_cached_command_node

        payload, cache_status = peek_cached_command_node(
            state.REPO_ROOT,
            node_id=PULSE_CLOSEOUT_AUDIT_NODE_ID,
            key=PULSE_CLOSEOUT_AUDIT_KEY,
            freshness_policy=PULSE_CLOSEOUT_AUDIT_FRESHNESS_POLICY,
            dynamic_inputs_manifested=False,
        )
        if isinstance(payload, Mapping):
            return dict(payload), cache_status
        return {
            "kind": "kernel.closeout_audit",
            "summary": {
                "status": "deferred_missing_cache",
                "pending_closeout_count": 0,
                "failed_unresolved_count": 0,
                "failed_dispositioned_count": 0,
                "failed_historic_count": 0,
                "inflight_count": 0,
                "orphaned_count": 0,
                "candidate_scan_limited": True,
                "reason": "quick_pulse_does_not_rebuild_closeout_audit",
                "repair_command": "./repo-python kernel.py --closeout-audit",
            },
            "actionable_items": [],
        }, cache_status
    except Exception as exc:
        return {
            "kind": "kernel.closeout_audit",
            "summary": {
                "status": "deferred_error",
                "pending_closeout_count": 0,
                "failed_unresolved_count": 0,
                "failed_dispositioned_count": 0,
                "failed_historic_count": 0,
                "inflight_count": 0,
                "orphaned_count": 0,
                "candidate_scan_limited": True,
                "reason": "closeout_cache_peek_failed",
                "repair_command": "./repo-python kernel.py --closeout-audit",
            },
            "actionable_items": [],
        }, {
            "status": "deferred_error",
            "reason": "closeout_cache_peek_failed",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
        }


def _pulse_routing_projection_status(*, exact: bool) -> dict[str, Any]:
    if exact:
        from system.lib.routing_projection import routing_status

        status = routing_status(state.REPO_ROOT)
        status["exact_staleness"] = True
        status["staleness_status"] = "exact"
        return status

    artifact_path = state.REPO_ROOT / "codex" / "doctrine" / "routing_hologram.json"
    payload = safe_load_json(artifact_path) if artifact_path.is_file() else {}
    if not isinstance(payload, Mapping):
        payload = {}
    return {
        "artifact_path": state.rel(artifact_path),
        "exists": artifact_path.is_file(),
        "stale": False,
        "drift_targets": [],
        "input_sha256": payload.get("input_sha256"),
        "check_command": "python3 kernel.py --routing-check",
        "refresh_command": "./repo-python tools/meta/factory/build_routing_projection.py",
        "source_paths": list(payload.get("source_paths") or []),
        "source_worktree_state": {
            "status": "deferred_for_pulse_hot_path",
            "reason": "Quick pulse reads the generated routing artifact without recomputing source coupling.",
        },
        "source_coupling": {
            "status": "deferred_for_pulse_hot_path",
            "artifact_matches_current_worktree": None,
            "safe_to_commit_generated_outputs_without_sources": None,
            "dirty_source_paths": [],
            "reason": "Run `./repo-python kernel.py --pulse --full` or `python3 kernel.py --routing-check` for exact routing source coupling.",
        },
        "exact_staleness": False,
        "staleness_status": "deferred_for_pulse_hot_path",
    }


def _pulse_organisation_control_plane_hint() -> dict[str, Any]:
    return {
        "available": True,
        "surface_role": CONTROL_ENTRY,
        "command": "./repo-python kernel.py --organisation-control-plane --band card --context-budget 12000",
        "full_command": "./repo-python kernel.py --organisation-control-plane --context-budget 12000",
        "freshness_policy": "deferred_eval_use_compact_command",
        "reason": (
            "Lane-level cockpit for closeout, dirty ownership, Task Ledger, "
            "generated-state, stale-doctrine, and documentation freshness pressure."
        ),
    }


def _pulse_worktree_summary_segment(worktrees: Mapping[str, Any]) -> str:
    segment = f" worktrees={worktrees.get('linked_count') or 0}:{worktrees.get('status') or 'unknown'}"
    dirty_status = str(worktrees.get("dirty_status") or "").strip()
    dirty_known = worktrees.get("dirty_status_known")
    dirty_unknown_count = worktrees.get("dirty_unknown_count")
    dirty_not_checked_count = worktrees.get("dirty_status_not_checked_count")
    if dirty_status and dirty_known is False:
        segment += f" worktree_dirty={dirty_status}"
        dirty_boundary_count = dirty_unknown_count if dirty_unknown_count is not None else dirty_not_checked_count
        if dirty_boundary_count:
            segment += f":{dirty_boundary_count}"
    elif worktrees.get("dirty_linked_count"):
        segment += f" worktree_dirty={worktrees.get('dirty_linked_count')}"
    return segment


def _pulse_short_text(value: object, *, limit: int = 96) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _pulse_workitem_dependency_lines(workitem: Mapping[str, Any]) -> list[str]:
    summary = (
        workitem.get("dependency_summary")
        if isinstance(workitem.get("dependency_summary"), Mapping)
        else {}
    )
    if not summary:
        return []
    schedulable = summary.get("schedulable")
    schedulable_text = "unknown" if schedulable is None else str(bool(schedulable)).lower()
    line = (
        "  dependency:"
        f" schedulable={schedulable_text}"
        f" hard_deps={summary.get('hard_dep_count') or 0}"
        f" unsatisfied={summary.get('unsatisfied_dep_count') or 0}"
        f" downstream_unlocks={summary.get('downstream_unlock_count') or 0}"
    )
    lines = [line]
    edges = (
        summary.get("top_downstream_unlock_edges")
        if isinstance(summary.get("top_downstream_unlock_edges"), list)
        else []
    )
    for edge in edges[:2]:
        if not isinstance(edge, Mapping):
            continue
        edge_id = str(edge.get("id") or "unknown").strip() or "unknown"
        title = _pulse_short_text(edge.get("title"), limit=88)
        waiting = "waiting" if edge.get("waiting_on_this") else "linked"
        unsatisfied = edge.get("downstream_unsatisfied_dep_count") or 0
        line = f"  unlocks: {edge_id} | {waiting} | downstream_unsatisfied={unsatisfied}"
        if title and title != edge_id:
            line += f" | {title}"
        lines.append(line)
    signal = (
        workitem.get("priority_signal")
        if isinstance(workitem.get("priority_signal"), Mapping)
        else {}
    )
    if signal and (
        signal.get("waiting_downstream_unlock_count")
        or signal.get("downstream_unsatisfied_dep_total")
    ):
        lines.append(
            "  unlock pressure:"
            f" score={signal.get('unlock_pressure_score') or 0}"
            f" waiting_downstream={signal.get('waiting_downstream_unlock_count') or 0}"
            f" downstream_unsatisfied={signal.get('downstream_unsatisfied_dep_total') or 0}"
        )
    return lines


def _pulse_workitem_pressure_suffix(workitem: Mapping[str, Any]) -> str:
    signal = (
        workitem.get("priority_signal")
        if isinstance(workitem.get("priority_signal"), Mapping)
        else {}
    )
    if not signal:
        return ""
    waiting = int(signal.get("waiting_downstream_unlock_count") or 0)
    downstream_unsatisfied = int(signal.get("downstream_unsatisfied_dep_total") or 0)
    score = int(signal.get("unlock_pressure_score") or 0)
    if not (waiting or downstream_unsatisfied or score):
        return ""
    return f" | pressure={score} waiting={waiting} downstream_unsatisfied={downstream_unsatisfied}"


def _pulse_workitem_summary_line(
    prefix: str,
    workitem: Mapping[str, Any],
    *,
    include_pressure: bool = False,
) -> str:
    wid = str(workitem.get("id") or "unknown").strip() or "unknown"
    rank = workitem.get("rank")
    rank_text = f"rank={rank}" if rank is not None else "rank=unranked"
    state_text = str(workitem.get("state") or "unknown").strip() or "unknown"
    title = _pulse_short_text(workitem.get("title"), limit=88)
    line = f"  {prefix}: {wid} | {rank_text} | state={state_text}"
    if include_pressure:
        line += _pulse_workitem_pressure_suffix(workitem)
    if title and title != wid:
        line += f" | {title}"
    return line


def _pulse_workitem_rows(value: object, *, limit: int = 3) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[Mapping[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping) and item.get("id"):
            rows.append(item)
        if len(rows) >= limit:
            break
    return rows


def _pulse_has_hot_execution(active_execution: Mapping[str, Any]) -> bool:
    campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    stale_pointers = (
        active_execution.get("stale_decorative_pointers")
        if isinstance(active_execution.get("stale_decorative_pointers"), list)
        else []
    )
    return bool(
        campaigns
        or stale_pointers
        or int(session_counts.get("active_claims") or 0) > 0
        or int(session_counts.get("effective_active_sessions") or 0) > 0
    )


def _pulse_seed_first_action_line(session_rows: list[Mapping[str, Any]]) -> str | None:
    if not session_rows:
        return None
    first = session_rows[0]
    session_id = _pulse_short_text(first.get("session_id"), limit=72) or "unknown_session"
    claim_count = int(first.get("claim_count") or 0)
    command = str(first.get("drilldown") or "").strip()
    if not command and session_id != "unknown_session":
        command = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-status --session-id {shlex.quote(session_id)} --full"
        )
    line = f"  seed first action: inspect active claim session {session_id}"
    if claim_count:
        line += f" | claims={claim_count}"
    if command:
        line += f" | open: {command}"
    return line


def _pulse_hot_now_lines(active_execution: Mapping[str, Any]) -> list[str]:
    """Render the action-backed liveness packet for the compact pulse view."""
    if not active_execution:
        return []

    anchor = (
        active_execution.get("declared_anchor")
        if isinstance(active_execution.get("declared_anchor"), Mapping)
        else {}
    )
    campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    sessions = (
        live_sessions.get("sessions")
        if isinstance(live_sessions.get("sessions"), list)
        else []
    )
    awareness_cards = (
        live_sessions.get("awareness_cards")
        if isinstance(live_sessions.get("awareness_cards"), list)
        else []
    )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    stale_pointers = (
        active_execution.get("stale_decorative_pointers")
        if isinstance(active_execution.get("stale_decorative_pointers"), list)
        else []
    )

    lines: list[str] = []
    if stale_pointers:
        phase_id = str(
            anchor.get("phase_id")
            or (stale_pointers[0] or {}).get("declared_phase_id")
            or "declared_phase"
        ).strip()
        lines.append(
            f"  declared phase: {phase_id} is contextual/dormant; "
            "liveness comes from Task Ledger + Work Ledger"
        )

    campaign_rows = [item for item in campaigns if isinstance(item, Mapping)]
    if campaign_rows:
        lines.append(f"  campaigns: {len(campaign_rows)} surfaced from Task Ledger")
        for item in campaign_rows[:3]:
            workitem_id = str(item.get("workitem_id") or item.get("id") or "unknown").strip()
            rank = item.get("rank")
            rank_text = f"rank={rank}" if rank is not None else "rank=unranked"
            state_text = str(item.get("state") or "unknown").strip() or "unknown"
            title = _pulse_short_text(item.get("title"), limit=88)
            line = f"  - campaign: {workitem_id} | {rank_text} | state={state_text}"
            if title and title != workitem_id:
                line += f" | {title}"
            lines.append(line)
        first_open = str(campaign_rows[0].get("drilldown_command") or "").strip()
        if first_open:
            lines.append(f"  open campaign: {first_open}")

    active_claims = int(session_counts.get("active_claims") or 0)
    effective_sessions = int(session_counts.get("effective_active_sessions") or 0)
    orphaned_sessions = int(session_counts.get("orphaned_active_sessions") or 0)
    claim_collision_count = int(session_counts.get("claim_collisions") or 0)
    heartbeat_gap_count = int(session_counts.get("claim_session_heartbeat_gap_count") or 0)
    heartbeat_gap_rows = (
        live_sessions.get("heartbeat_gap_claim_sessions")
        if isinstance(live_sessions.get("heartbeat_gap_claim_sessions"), list)
        else []
    )
    heartbeat_gap_status = str(live_sessions.get("heartbeat_gap_status") or "").strip()
    session_rows = [item for item in sessions if isinstance(item, Mapping)]
    if active_claims or effective_sessions or session_rows:
        bits = [f"active_claims={active_claims}", f"effective_sessions={effective_sessions}"]
        if orphaned_sessions:
            bits.append(f"orphaned={orphaned_sessions}")
        drilldowns = (
            live_sessions.get("drilldown_commands")
            if isinstance(live_sessions.get("drilldown_commands"), Mapping)
            else {}
        )
        command_key = "cards" if active_claims or session_rows else "overview"
        command_label = "open" if command_key == "cards" else "overview"
        cards_command = str(drilldowns.get(command_key) or "").strip()
        no_heartbeat_command = str(drilldowns.get("seed_speed_no_heartbeat") or "").strip()
        work_ledger_line = f"  work ledger: {' '.join(bits)}"
        if cards_command:
            work_ledger_line += f" | {command_label}: {cards_command}"
        if no_heartbeat_command and no_heartbeat_command != cards_command:
            work_ledger_line += f" | no-heartbeat: {no_heartbeat_command}"
        lines.append(work_ledger_line)
        if claim_collision_count:
            collision_word = "collision" if claim_collision_count == 1 else "collisions"
            collision_verb = "blocks" if claim_collision_count == 1 else "block"
            seed_speed_command = str(drilldowns.get("seed_speed") or drilldowns.get("cards") or "").strip()
            collision_line = (
                f"  claim collisions: {claim_collision_count} active {collision_word} "
                f"{collision_verb} seed widening"
            )
            if seed_speed_command:
                collision_line += f" | open: {seed_speed_command}"
            lines.append(collision_line)
        if heartbeat_gap_count:
            session_word = "session" if heartbeat_gap_count == 1 else "sessions"
            verb = "needs" if heartbeat_gap_count == 1 else "need"
            gap_line = (
                f"  heartbeat gaps: {heartbeat_gap_count} claim {session_word} "
                f"{verb} session-heartbeat"
            )
            has_direct_gap_fix = any(
                isinstance(row, Mapping) and str(row.get("heartbeat_command") or "").strip()
                for row in heartbeat_gap_rows
            )
            seed_speed_command = str(drilldowns.get("seed_speed") or drilldowns.get("cards") or "").strip()
            if has_direct_gap_fix:
                gap_line += " | fix below"
            elif seed_speed_command:
                gap_line += f" | open: {seed_speed_command}"
            lines.append(gap_line)
            for item in [row for row in heartbeat_gap_rows if isinstance(row, Mapping)][:2]:
                session_id = _pulse_short_text(item.get("session_id"), limit=72) or "unknown_session"
                claim_count = int(item.get("active_claim_count") or 0)
                scope = _pulse_short_text(item.get("scope_ref"), limit=104)
                heartbeat_command = str(item.get("heartbeat_command") or "").strip()
                line = f"  - heartbeat gap: {session_id} | claims={claim_count}"
                if scope:
                    line += f" scope={scope}"
                if heartbeat_command:
                    line += f" | fix: {heartbeat_command}"
                lines.append(line)
        elif heartbeat_gap_status == "deferred_by_fast_path" and active_claims:
            seed_action = None if awareness_cards else _pulse_seed_first_action_line(session_rows)
            if seed_action:
                lines.append(seed_action)
            elif claim_collision_count or not awareness_cards:
                seed_speed_command = str(drilldowns.get("seed_speed") or drilldowns.get("cards") or "").strip()
                gap_line = "  heartbeat gaps: not checked in fast pulse"
                if seed_speed_command:
                    gap_line += f" | open: {seed_speed_command}"
                lines.append(gap_line)
        elif not claim_collision_count and session_rows and not awareness_cards:
            seed_action = _pulse_seed_first_action_line(session_rows)
            if seed_action:
                lines.append(seed_action)
        awareness_rows = [item for item in awareness_cards if isinstance(item, Mapping)]
        for item in awareness_rows[:3]:
            session_id = _pulse_short_text(item.get("session_id"), limit=72) or "unknown_session"
            freshness = str(item.get("freshness_state") or "unknown").strip() or "unknown"
            pass_state = str(item.get("pass_state") or "").strip()
            source = str(item.get("source") or "").strip()
            line = f"  - pass: {session_id} | freshness={freshness}"
            if pass_state:
                line += f" state={pass_state}"
            elif source:
                line += f" source={source}"
            lines.append(line)
            current_line = _pulse_short_text(item.get("current_pass_line"), limit=132)
            result_line = _pulse_short_text(item.get("last_pass_result_line"), limit=132)
            if current_line:
                lines.append(f"    now: {current_line}")
            elif source == "projected_unknown":
                lines.append("    now: unknown current pass")
            if result_line:
                lines.append(f"    done: {result_line}")
        legacy_session_rows = [] if awareness_rows else session_rows
        for item in legacy_session_rows[:3]:
            session_id = _pulse_short_text(item.get("session_id"), limit=72) or "unknown_session"
            line = (
                f"  - session: {session_id}"
                f" | claims={item.get('claim_count') or 0}"
                f" paths={item.get('path_count') or 0}"
            )
            phase_id = str(item.get("phase_id") or "").strip()
            if phase_id:
                line += f" phase={phase_id}"
            leased_until = str(item.get("leased_until") or "").strip()
            if leased_until:
                line += f" lease_until={leased_until}"
            lines.append(line)
            paths = [str(path) for path in (item.get("paths") or []) if str(path).strip()]
            if paths:
                focus = _pulse_short_text(paths[0], limit=104)
                extra = int(item.get("path_count") or len(paths)) - 1
                suffix = f" (+{extra} paths)" if extra > 0 else ""
                lines.append(f"    focus: {focus}{suffix}")

    return lines


def _pulse_snapshot(exact: bool = False, profile_sink: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from tools.meta import builder
    from system.control.documentation_route_focus import load_documentation_route_focus, summarize_active_focus

    phase_started = perf_counter()
    navigator = KernelNavigation(state.REPO_ROOT)
    _profile_phase(profile_sink, "navigation_init", phase_started)

    phase_started = perf_counter()
    docs_route_focus = summarize_active_focus(load_documentation_route_focus(state.REPO_ROOT))
    _profile_phase(profile_sink, "documentation_route_focus", phase_started)

    quick_active_phase = _pulse_active_phase_from_bootstrap_live() if not exact else None

    phase_started = perf_counter()
    frontier_anchor = _pulse_frontier_anchor(navigator, stale_ok=not exact, active_phase=quick_active_phase)
    _profile_phase(profile_sink, "frontier_anchor", phase_started)

    phase_started = perf_counter()
    docfix_plan = _pulse_latest_saved_plan(prefix="docfix_")
    _profile_phase(profile_sink, "latest_docfix_plan", phase_started)

    phase_started = perf_counter()
    runtime = _pulse_latest_runtime(exact=exact, active_phase=quick_active_phase)
    _profile_phase(profile_sink, "latest_runtime", phase_started)

    phase_started = perf_counter()
    active_plan = _pulse_effective_active_plan(runtime, _active_plan_summary())
    _profile_phase(profile_sink, "active_plan", phase_started)

    phase_started = perf_counter()
    doctrine = _pulse_doctrine_summary(navigator, exact=exact)
    _profile_phase(profile_sink, "doctrine_summary", phase_started)

    phase_started = perf_counter()
    workspace = _pulse_workspace_summary()
    _profile_phase(profile_sink, "workspace_summary", phase_started)

    phase_started = perf_counter()
    closeout_git_state = _pulse_closeout_git_state()
    _profile_phase(profile_sink, "closeout_git_state", phase_started)

    phase_started = perf_counter()
    annex_landing = _pulse_annex_landing_summary()
    _profile_phase(profile_sink, "annex_landing", phase_started)

    phase_started = perf_counter()
    provider_plane, provider_plane_cache_status = _pulse_provider_plane_liveness(exact=exact)
    _profile_phase(profile_sink, "provider_plane_liveness", phase_started)

    phase_started = perf_counter()
    closeout_audit, closeout_cache_status = _pulse_closeout_audit(exact=exact)
    _profile_phase(profile_sink, "closeout_audit", phase_started)

    phase_started = perf_counter()
    builder_status = builder.hologram_status(str(state.REPO_ROOT), exact_staleness=exact)
    _profile_phase(profile_sink, "hologram_status", phase_started)
    stale_phase_names = [
        name
        for name, phase in (builder_status.get("phases") or {}).items()
        if isinstance(phase, dict) and phase.get("stale")
    ]

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(state.REPO_ROOT),
        "frontier_anchor": frontier_anchor,
        "active_plan": active_plan,
        "latest_docfix_plan": docfix_plan,
        "latest_runtime": runtime,
        "builder": {
            "exists": bool(builder_status.get("exists")),
            "all_current": bool(builder_status.get("all_current")),
            "total_phases": builder_status.get("total_phases"),
            "total_artifacts": builder_status.get("total_artifacts"),
            "stale_phases": builder_status.get("stale_phases"),
            "stale_phase_names": stale_phase_names,
            "exact_staleness": bool(builder_status.get("exact_staleness")),
            "staleness_status": builder_status.get("staleness_status"),
        },
        "doctrine": doctrine,
        "workspace": workspace,
        "closeout_git_state": closeout_git_state,
        "annex_landing": annex_landing,
        "provider_plane": provider_plane,
        "closeout_gap": {
            **dict(closeout_audit.get("summary") or {}),
            "items": list(closeout_audit.get("actionable_items") or [])[:5],
        },
        "doctrine_runtime": {
            "spec_path": state.rel(state.DOCTRINE_RUNTIME_SPEC),
            "spec_exists": state.DOCTRINE_RUNTIME_SPEC.is_file(),
            "emit_command": "./repo-python kernel.py --doctrine-runtime",
            "pulse_full_hint": "./repo-python kernel.py --pulse --full",
        },
        "documentation_plane": {
            "documentation_theory_index": "codex/doctrine/documentation_theory_index.json",
            "agent_bootstrap": "codex/doctrine/agent_bootstrap.json",
            "documentation_plane_map": "docs/documentation_plane_map.md",
            "documentation_route_focus": docs_route_focus,
            "docs_route_example": "./repo-python kernel.py --docs-route documentation",
            "docs_route_focus_hint": "./repo-python kernel.py --list-docs-route-focus | ./repo-python kernel.py --set-docs-route-focus <preset_id>",
            "orient_task_hint": "./repo-python kernel.py --orient-task <note-or-token>",
            "system_view_command": "./repo-python kernel.py --system-view [PHASE_TOKEN]",
        },
        "organisation_control_plane": _pulse_organisation_control_plane_hint(),
        "routing_projection": _pulse_routing_projection_status(exact=exact),
        "pulse_mode": "exact" if exact else "quick",
        "pulse_cache": {
            "closeout_audit": closeout_cache_status,
            "provider_plane_liveness": provider_plane_cache_status,
        },
        "task_ledger_priority": None,
        "residual_lanes": [navigation_enforcement_residual_lane()],
        "recent_autonomous_fires": None,
        "ready_deferred_reactions": None,
        "decision_tree": [
            {
                "intent": "orientation",
                "command": f"./repo-python kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
                "reason": "Recover the current note family, manifest, and observe continuity.",
            },
            {
                "intent": "runtime_resume",
                "command": "./repo-python kernel.py --observe-status latest",
                "reason": "Inspect the newest grouped observe runtime before launching more bridge work.",
            },
            {
                "intent": "documentation_repair",
                "command": "./repo-python kernel.py --remediate --bridge --provider chatgpt",
                "reason": "Close documentation gaps through the miner -> observe -> apply loop.",
            },
            {
                "intent": "rebuild_state",
                "command": "./repo-python kernel.py --build status",
                "reason": "Check whether the hologram and self-model are current before trusting them.",
            },
            {
                "intent": "doctrine_freshness",
                "command": "./repo-python kernel.py --stale",
                "reason": "Inspect drift across living maps, doctrine, and planning artifacts.",
            },
            {
                "intent": "doctrine_control_plane",
                "command": "./repo-python kernel.py --doctrine-runtime",
                "reason": "Emit doctrine_runtime.json: artifact graph, scaling policy, mech_016 audit launch, pipeline recovery macros.",
            },
        ],
    }
    phase_started = perf_counter()
    snapshot["task_ledger_priority"] = _pulse_task_ledger_priority()
    _profile_phase(profile_sink, "task_ledger_priority", phase_started)

    phase_started = perf_counter()
    try:
        from system.lib.active_execution_constellation import build_active_execution_constellation

        priority = (
            snapshot.get("task_ledger_priority")
            if isinstance(snapshot.get("task_ledger_priority"), Mapping)
            else {}
        )
        top_schedulable = (
            priority.get("top_schedulable_workitem")
            if isinstance(priority.get("top_schedulable_workitem"), Mapping)
            else None
        )
        top_ready = (
            priority.get("top_ready_workitem")
            if isinstance(priority.get("top_ready_workitem"), Mapping)
            else None
        )
        snapshot["active_execution_constellation"] = build_active_execution_constellation(
            state.REPO_ROOT,
            active_phase=quick_active_phase if isinstance(quick_active_phase, Mapping) else None,
            work_priority=priority,
            top_schedulable_workitem=top_schedulable,
            top_ready_workitem=top_ready,
            include_runtime_status=False,
            campaign_limit=4,
            claim_limit=8,
            session_limit=6,
        )
    except Exception as exc:  # pragma: no cover - pulse must degrade on sidecar skew.
        snapshot["active_execution_constellation"] = {
            "kind": "active_execution_constellation",
            "schema_version": "active_execution_constellation_v0",
            "authority_posture": "projection_not_source_authority",
            "status": "unavailable",
            "reason": type(exc).__name__,
            "error": str(exc)[:240],
        }
    _profile_phase(profile_sink, "active_execution_constellation", phase_started)

    phase_started = perf_counter()
    snapshot["recent_autonomous_fires"] = _pulse_recent_autonomous_fires(limit=5)
    _profile_phase(profile_sink, "recent_autonomous_fires", phase_started)

    phase_started = perf_counter()
    snapshot["ready_deferred_reactions"] = _pulse_ready_deferred_reactions(limit=5)
    _profile_phase(profile_sink, "ready_deferred_reactions", phase_started)

    phase_started = perf_counter()
    snapshot["recommended_actions"] = _pulse_recommended_actions(snapshot)
    _profile_phase(profile_sink, "recommended_actions", phase_started)
    return snapshot


def _focus_snapshot(card: dict[str, Any]) -> dict[str, Any]:
    return {
        key: card.get(key)
        for key in ("focus_status", "focus_label", "focus_handoff")
        if key in card
    }


def _load_markdown_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = _kernel_safe_read_text(path)
    if text is None:
        raise ValueError(f"Could not read markdown note: {state.rel(path)}")
    card, body = parse_frontmatter(text)
    return dict(card), body


def _update_markdown_frontmatter(
    rel_path: str,
    *,
    status_value: str | None = None,
    clear_status: bool = False,
    label_value: str | None = None,
    clear_label: bool = False,
    handoff_value: str | None = None,
    clear_handoff: bool = False,
    live: bool = False,
) -> dict[str, Any] | None:
    note_path = state.REPO_ROOT / rel_path
    if not note_path.exists():
        return None
    card, body = _load_markdown_frontmatter(note_path)
    updated = dict(card)
    changes: list[dict[str, Any]] = []

    def _set_or_clear(key: str, value: str | None, clear_flag: bool) -> None:
        if clear_flag:
            if key in updated:
                previous = updated.pop(key)
                changes.append({"field": key, "before": previous, "after": None})
            return
        if value is None:
            return
        previous = updated.get(key)
        if previous == value:
            return
        updated[key] = value
        changes.append({"field": key, "before": previous, "after": value})

    _set_or_clear("focus_status", status_value, clear_status)
    _set_or_clear("focus_label", label_value, clear_label)
    _set_or_clear("focus_handoff", handoff_value, clear_handoff)

    if not changes:
        return None

    if live:
        note_path.write_text(render_markdown_document(updated, body), encoding="utf-8")

    return {
        "path": rel_path,
        "before": _focus_snapshot(card),
        "after": _focus_snapshot(updated),
        "changes": changes,
    }


def _current_default_phase_stub() -> dict[str, Any] | None:
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        entry = navigator._resolve_phase_entry("__active__")
    except ValueError:
        return None
    canonical = entry.get("canonical_entry") if isinstance(entry.get("canonical_entry"), Mapping) else {}
    path = canonicalize_write_path(str(canonical.get("path") or "").strip()) or None
    return {
        "phase_id": entry.get("phase_id"),
        "phase_number": entry.get("phase_number"),
        "phase_title": entry.get("phase_title"),
        "canonical_path": path,
        "focus_status": canonical.get("focus_status"),
        "focus_label": canonical.get("focus_label"),
    }


def _current_default_plan_stub() -> dict[str, Any] | None:
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        entry = navigator._resolve_plan_entry("__active__", kind="implementation_note")
    except ValueError:
        return None
    return {
        "plan_id": entry.get("plan_id"),
        "path": canonicalize_write_path(str(entry.get("path") or "").strip()) or None,
        "status": entry.get("status"),
        "focus_status": entry.get("focus_status"),
        "focus_label": entry.get("focus_label"),
    }


def _default_promotion_payload(
    *,
    before_phase: dict[str, Any] | None,
    observe_seed_path: str | None,
    phase_id: str | None,
    before_plan: dict[str, Any] | None,
    plan_path: str | None,
    plan_id: str | None,
    live: bool,
    source_command: str,
) -> dict[str, Any]:
    observe_rel = canonicalize_write_path(str(observe_seed_path or "").strip()) or None
    plan_rel = canonicalize_write_path(str(plan_path or "").strip()) or None
    writes: list[dict[str, Any]] = []

    if observe_rel:
        update = _update_markdown_frontmatter(
            observe_rel,
            status_value="active",
            label_value=state.AUTO_DEFAULT_PHASE_LABEL,
            handoff_value=state.AUTO_DEFAULT_PHASE_HANDOFF,
            live=live,
        )
        if update:
            update["reason"] = "promote_phase_default"
            writes.append(update)

        prior_phase_path = canonicalize_write_path(str((before_phase or {}).get("canonical_path") or "").strip()) or None
        if prior_phase_path and prior_phase_path != observe_rel:
            prior_card, _ = _load_markdown_frontmatter(state.REPO_ROOT / prior_phase_path)
            clear_update = _update_markdown_frontmatter(
                prior_phase_path,
                clear_status=str(prior_card.get("focus_status") or "").strip().lower() == "active",
                clear_label=str(prior_card.get("focus_label") or "").strip() == state.AUTO_DEFAULT_PHASE_LABEL,
                clear_handoff=str(prior_card.get("focus_handoff") or "").strip() == state.AUTO_DEFAULT_PHASE_HANDOFF,
                live=live,
            )
            if clear_update:
                clear_update["reason"] = "clear_previous_phase_default"
                writes.append(clear_update)

    if plan_rel:
        update = _update_markdown_frontmatter(
            plan_rel,
            status_value="active",
            label_value=AUTO_DEFAULT_PLAN_LABEL,
            handoff_value=AUTO_DEFAULT_PLAN_HANDOFF,
            live=live,
        )
        if update:
            update["reason"] = "promote_plan_default"
            writes.append(update)

        prior_plan_path = canonicalize_write_path(str((before_plan or {}).get("path") or "").strip()) or None
        if prior_plan_path and prior_plan_path != plan_rel:
            prior_card, _ = _load_markdown_frontmatter(state.REPO_ROOT / prior_plan_path)
            clear_update = _update_markdown_frontmatter(
                prior_plan_path,
                clear_status=str(prior_card.get("focus_status") or "").strip().lower() == "active",
                clear_label=str(prior_card.get("focus_label") or "").strip() == AUTO_DEFAULT_PLAN_LABEL,
                clear_handoff=str(prior_card.get("focus_handoff") or "").strip() == AUTO_DEFAULT_PLAN_HANDOFF,
                live=live,
            )
            if clear_update:
                clear_update["reason"] = "clear_previous_plan_default"
                writes.append(clear_update)

    after_phase = _current_default_phase_stub()
    after_plan = _current_default_plan_stub() if plan_rel else before_plan
    phase_changed = bool(after_phase and observe_rel and str(after_phase.get("canonical_path") or "") == observe_rel)
    plan_changed = bool(after_plan and plan_rel and str(after_plan.get("path") or "") == plan_rel)
    return {
        "source_command": source_command,
        "mode": "live" if live else "preview",
        "explicit_notice": (
            "This scaffold explicitly promotes the new phase/plan as the default unlabeled target instead of relying on modified-time fallback."
        ),
        "phase_default": {
            "before": before_phase,
            "after": after_phase,
            "target_observe_seed": observe_rel,
            "phase_id": phase_id,
            "changed": phase_changed,
            "would_change": bool(not live and observe_rel and str((before_phase or {}).get("canonical_path") or "") != observe_rel),
        },
        "plan_default": {
            "before": before_plan,
            "after": after_plan,
            "target_plan": plan_rel,
            "plan_id": plan_id,
            "changed": plan_changed,
            "would_change": bool(not live and plan_rel and str((before_plan or {}).get("path") or "") != plan_rel),
        }
        if plan_rel
        else None,
        "writes": writes,
    }


def _attach_scaffold_default_promotion(
    payload: Mapping[str, Any],
    *,
    live: bool,
    source_command: str,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Attach the canonical `default_promotion` preview or apply payload to scaffold and activation responses so callers can see which unlabeled phase or plan default would move.
    - Mechanism: Read phase and founding-phase metadata from the scaffold payload, derive canonical synth-seed and plan targets, call `_default_promotion_payload()`, and append family activation state through `preview_or_apply_family_activation()`.
    - Reads: Scaffold payload phase metadata, current default phase/plan stubs, and canonicalized synth-seed or plan paths.
    - Writes: Promotion and family-activation artifacts only when `live` is true.
    - When-needed: Open when `default_promotion` appears in phase scaffold or activation output and you need the authoritative seam that computes or attaches that payload.
    - Escalates-to: _default_promotion_payload; system/lib/phase_activation.py
    - Navigation-group: kernel_lib
    """
    result = dict(payload)
    phase_payload = result.get("phase") if isinstance(result.get("phase"), Mapping) else {}
    founding_phase = result.get("founding_phase") if isinstance(result.get("founding_phase"), Mapping) else {}

    phase_id = str(phase_payload.get("phase_id") or founding_phase.get("phase_id") or "").strip() or None
    phase_number = str(phase_payload.get("phase_number") or founding_phase.get("phase_number") or "").strip() or None
    phase_title = str(phase_payload.get("phase_title") or founding_phase.get("phase_title") or "").strip() or None
    phase_dir = canonicalize_write_path(
        str(phase_payload.get("phase_dir") or founding_phase.get("phase_dir") or "").strip()
    ) or None
    family_dir = canonicalize_write_path(
        str(phase_payload.get("family_dir") or founding_phase.get("family_dir") or "").strip()
    ) or None
    observe_seed_path = str(
        phase_payload.get("synth_seed_markdown_path")
        or phase_payload.get("observe_seed_path")
        or founding_phase.get("synth_seed_markdown_path")
        or founding_phase.get("observe_seed_path")
        or ""
    ).strip()
    if not observe_seed_path:
        if phase_dir:
            observe_seed_path = canonicalize_write_path(f"{phase_dir}/synth_seed.md") or observe_seed_path

    plan_path = str(phase_payload.get("plan_path") or "").strip() or None
    plan_id = str(phase_payload.get("phase_id") or "").strip() or None

    before_phase = _current_default_phase_stub()
    before_plan = _current_default_plan_stub() if plan_path else None
    result["default_promotion"] = _default_promotion_payload(
        before_phase=before_phase,
        observe_seed_path=observe_seed_path,
        phase_id=phase_id,
        before_plan=before_plan,
        plan_path=plan_path,
        plan_id=plan_id,
        live=live,
        source_command=source_command,
    )
    result["family_activation"] = preview_or_apply_family_activation(
        state.REPO_ROOT,
        family_dir=family_dir,
        phase_id=phase_id,
        phase_number=phase_number,
        phase_title=phase_title,
        phase_dir=phase_dir,
        source_command=source_command,
        live=live,
    )
    return result


def _normalize_new_phase_number(value: str) -> str:
    phase_number = str(value or "").strip()
    if not phase_number or not re.fullmatch(r"\d+(?:\.\d+)*", phase_number):
        raise ValueError("--number must look like 7.2 or 07.2")
    return phase_number


def _normalize_new_phase_title(phase_number: str, title: str) -> str:
    clean_title = " ".join(str(title or "").strip().split())
    if not clean_title:
        raise ValueError("--title is required with --new-phase")
    if re.match(rf"^phase\s*{re.escape(phase_number)}\b", clean_title, flags=re.IGNORECASE):
        return clean_title
    return f"Phase {phase_number} - {clean_title}"


def _new_phase_id(phase_number: str) -> str:
    return phase_number.replace(".", "_")


def _new_phase_dir_name(phase_number: str, phase_title: str) -> str:
    clean_title = re.sub(r'[\\/:*?"<>|]+', " - ", phase_title).strip()
    clean_title = re.sub(r"\s+", " ", clean_title)
    return f"{phase_number} - {clean_title}"


def _phase_short_name(phase_number: str, phase_title: str) -> str:
    short_name = " ".join(str(phase_title or "").strip().split())
    patterns = [
        rf"^phase\s*{re.escape(phase_number)}\s*[-:]\s*",
        rf"^phase\s*{re.escape(phase_number)}\s*",
    ]
    for pattern in patterns:
        short_name = re.sub(pattern, "", short_name, flags=re.IGNORECASE).strip()
    short_name = re.sub(r"^(?:\[?\s*closed\s*\]?|closed)\s*[-:]\s*", "", short_name, flags=re.IGNORECASE).strip()
    short_name = re.sub(r"^(?:\[?\s*closed\s*\]?|closed)\s+", "", short_name, flags=re.IGNORECASE).strip()
    short_name = re.sub(r"\s*[-:]\s*(?:\[?\s*closed\s*\]?|closed)$", "", short_name, flags=re.IGNORECASE).strip()
    short_name = re.sub(r"\s+(?:\[?\s*closed\s*\]?|closed)$", "", short_name, flags=re.IGNORECASE).strip()
    return short_name or "Closed Packet"


def _closed_phase_title(phase_number: str, phase_title: str) -> str:
    return f"Phase {phase_number} - CLOSED - {_phase_short_name(phase_number, phase_title)}"


def _closed_phase_dir_name(phase_number: str, phase_title: str) -> str:
    clean_title = re.sub(r'[\\/:*?"<>|]+', " - ", _phase_short_name(phase_number, phase_title)).strip()
    clean_title = re.sub(r"\s+", " ", clean_title)
    return f"{phase_number} - CLOSED - {clean_title}"


def _closed_phase_dir(phase_dir: str, phase_number: str, phase_title: str) -> str:
    parent_dir = canonicalize_write_path(str(Path(phase_dir).parent).replace("\\", "/")) or ""
    if not parent_dir:
        return canonicalize_write_path(_closed_phase_dir_name(phase_number, phase_title)) or phase_dir
    return canonicalize_write_path(f"{parent_dir}/{_closed_phase_dir_name(phase_number, phase_title)}") or phase_dir


def _rewrite_phase_strings(
    value: Any,
    *,
    old_phase_title: str,
    new_phase_title: str,
    old_phase_dir: str,
    new_phase_dir: str,
) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _rewrite_phase_strings(
                item,
                old_phase_title=old_phase_title,
                new_phase_title=new_phase_title,
                old_phase_dir=old_phase_dir,
                new_phase_dir=new_phase_dir,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _rewrite_phase_strings(
                item,
                old_phase_title=old_phase_title,
                new_phase_title=new_phase_title,
                old_phase_dir=old_phase_dir,
                new_phase_dir=new_phase_dir,
            )
            for item in value
        ]
    if isinstance(value, str):
        rewritten = value
        if old_phase_dir:
            rewritten = rewritten.replace(old_phase_dir, new_phase_dir)
        if old_phase_title:
            rewritten = rewritten.replace(old_phase_title, new_phase_title)
        return rewritten
    return value


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _phase_payload_from_navigation_dict(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    phase = payload.get("phase")
    if isinstance(phase, Mapping):
        return dict(phase)
    nested_payload = payload.get("payload")
    if isinstance(nested_payload, Mapping):
        nested_phase = nested_payload.get("phase")
        if isinstance(nested_phase, Mapping):
            return dict(nested_phase)
    return {}


def _family_marker_aliases(payload: Mapping[str, Any], family_dir: str, marker_rel: str) -> set[str]:
    aliases: set[str] = set()
    for value in (
        payload.get("family_id"),
        payload.get("family_number"),
        payload.get("family_title"),
        payload.get("family_dir"),
        family_dir,
        marker_rel,
        Path(family_dir).name if family_dir else None,
    ):
        token = str(value or "").strip()
        if not token:
            continue
        aliases.add(token)
        aliases.add(token.casefold())
        aliases.add(token.replace(".", "_"))
        aliases.add(token.replace("_", "."))
    family_number = str(payload.get("family_number") or "").strip()
    if family_number:
        try:
            aliases.add(str(int(family_number)))
        except ValueError:
            pass
    return {item for item in aliases if item}


def _resolve_phase_family_entry(requested: str) -> dict[str, str] | None:
    token = str(requested or "").strip()
    if not token:
        return None

    obsidian_root = state.REPO_ROOT / "obsidian"
    if not obsidian_root.exists():
        return None

    candidate = Path(token)
    candidate_rel = ""
    if candidate.is_absolute():
        try:
            candidate_rel = canonicalize_write_path(str(candidate.resolve().relative_to(state.REPO_ROOT)))
        except ValueError:
            candidate_rel = ""
    else:
        candidate_rel = canonicalize_write_path(token) or ""

    for marker_path in sorted(obsidian_root.rglob(PHASE_FAMILY_MARKER_FILENAME)):
        payload = _load_json_file(marker_path)
        if not isinstance(payload, Mapping):
            continue
        marker_rel = canonicalize_write_path(str(marker_path.relative_to(state.REPO_ROOT)))
        family_dir = canonicalize_write_path(str(payload.get("family_dir") or marker_path.parent.relative_to(state.REPO_ROOT)))
        if not family_dir:
            continue
        aliases = _family_marker_aliases(payload, family_dir, marker_rel)
        if token in aliases or token.casefold() in aliases or candidate_rel in aliases:
            return {
                "family_id": str(payload.get("family_id") or "").strip() or _new_phase_id(str(payload.get("family_number") or "")),
                "family_number": str(payload.get("family_number") or "").strip(),
                "family_title": str(payload.get("family_title") or Path(family_dir).name).strip(),
                "family_dir": family_dir,
                "marker_path": marker_rel,
            }
    return None


def _discover_phase_family_dir(phase_dir: str) -> str | None:
    token = canonicalize_write_path(str(phase_dir or "").strip()) or ""
    if not token:
        return None
    phase_abs = state.REPO_ROOT / token
    obsidian_root = (state.REPO_ROOT / "obsidian").resolve()
    if not phase_abs.exists():
        return None
    for current in [phase_abs, *phase_abs.parents]:
        try:
            current.relative_to(obsidian_root)
        except ValueError:
            break
        marker_path = current / PHASE_FAMILY_MARKER_FILENAME
        if marker_path.exists():
            marker_payload = _load_json_file(marker_path) or {}
            family_dir = canonicalize_write_path(
                str(marker_payload.get("family_dir") or current.relative_to(state.REPO_ROOT))
            )
            if family_dir:
                return family_dir
        if all((current / name).exists() for name in ("raw_seed.md", "meta_ledger.json", "reference_ledger.json")):
            return canonicalize_write_path(str(current.relative_to(state.REPO_ROOT)))
    return None


def _normalize_new_family_title(family_number: str, title: str) -> str:
    clean_title = " ".join(str(title or "").strip().split())
    if not clean_title:
        raise ValueError("--title is required with --new-family")
    clean_title = re.sub(
        rf"^phase\s*{re.escape(family_number)}\s*[-:]\s*",
        "",
        clean_title,
        flags=re.IGNORECASE,
    ).strip()
    return clean_title or str(title or "").strip()


def _new_family_dir_name(family_number: str, family_title: str) -> str:
    clean_title = re.sub(r'[\\/:*?"<>|]+', " - ", family_title).strip()
    clean_title = re.sub(r"\s+", " ", clean_title)
    return f"{family_number} - {clean_title}"


def _normalize_new_family_parent_path(requested: str | None, *, seed_from: str | None = None) -> tuple[str, str]:
    token = str(requested or "").strip()
    if token:
        family_entry = _resolve_phase_family_entry(token)
        if family_entry is not None:
            family_dir = str(family_entry.get("family_dir") or "").strip()
            if family_dir:
                parent_dir = canonicalize_write_path(str(Path(family_dir).parent))
                if parent_dir:
                    return Path(parent_dir).name, parent_dir

        navigator = KernelNavigation(state.REPO_ROOT)
        try:
            phase_payload = navigator.build_phase(token).to_dict(state.KERNEL_VERSION, full=True)
            phase_entry = _phase_payload_from_navigation_dict(phase_payload)
            phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
            if phase_dir:
                family_dir = canonicalize_write_path(str(phase_entry.get("family_dir") or "").strip()) or _discover_phase_family_dir(phase_dir)
                anchor_dir = family_dir or phase_dir
                parent_dir = canonicalize_write_path(str(Path(anchor_dir).parent))
                if parent_dir:
                    return Path(parent_dir).name, parent_dir
        except ValueError:
            pass
    elif seed_from:
        seed_candidate = Path(str(seed_from))
        if seed_candidate.is_absolute():
            try:
                seed_rel = canonicalize_write_path(str(seed_candidate.resolve().relative_to(state.REPO_ROOT)))
            except ValueError:
                seed_rel = ""
        else:
            seed_rel = canonicalize_write_path(str(seed_candidate)) or ""
        if seed_rel:
            source_family_dir = _discover_phase_family_dir(str(Path(seed_rel).parent))
            anchor_dir = source_family_dir or canonicalize_write_path(str(Path(seed_rel).parent))
            if anchor_dir:
                parent_dir = canonicalize_write_path(str(Path(anchor_dir).parent))
                if parent_dir:
                    return Path(parent_dir).name, parent_dir

    if not token:
        raise ValueError("--parent is required with --new-family unless --seed-from can infer it.")

    candidate = Path(token)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(state.REPO_ROOT)
        except ValueError as exc:
            raise ValueError("--parent must stay inside the repo") from exc
    normalized = canonicalize_write_path(str(candidate)) or canonicalize_write_path(token)
    if not normalized:
        raise ValueError(f"Could not resolve --parent: {token}")
    parent_path = state.REPO_ROOT / normalized
    parent_dir = normalized
    if parent_path.exists() and parent_path.is_file():
        parent_dir = canonicalize_write_path(str(Path(normalized).parent))
    if not parent_dir or not parent_dir.startswith("obsidian/"):
        raise ValueError("--parent must resolve to an obsidian path, an existing phase token, or a phase family token")
    return Path(parent_dir).name, parent_dir.rstrip("/")


def _phase_number_parts(value: str) -> tuple[str, ...]:
    token = str(value or "").strip()
    return tuple(part for part in token.split(".") if part)


def _canonical_phase_number_parts(value: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for part in _phase_number_parts(value):
        if part.isdigit():
            normalized.append(str(int(part)))
        else:
            normalized.append(part.casefold())
    return tuple(normalized)


def _shared_phase_prefix_length(left: str, right: str) -> int:
    left_parts = _canonical_phase_number_parts(left)
    right_parts = _canonical_phase_number_parts(right)
    shared = 0
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part != right_part:
            break
        shared += 1
    return shared


def _phase_entry_for_exact_phase_number(
    navigator: KernelNavigation,
    phase_number: str,
) -> dict[str, Any] | None:
    target_parts = _canonical_phase_number_parts(phase_number)
    if not target_parts:
        return None
    matches = [
        dict(entry)
        for entry in navigator.phase_entries
        if _canonical_phase_number_parts(str(entry.get("phase_number") or "").strip()) == target_parts
    ]
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(f"Phase number is ambiguous even after exact normalization: {phase_number}")
    return matches[0]


def _normalize_new_phase_parent_path(
    requested: str,
    *,
    requested_phase_number: str | None = None,
) -> dict[str, str | None]:
    token = str(requested or "").strip()
    if not token:
        raise ValueError("--parent is required with --new-phase")

    family_entry = _resolve_phase_family_entry(token)
    if family_entry is not None:
        family_dir = str(family_entry.get("family_dir") or "").strip()
        if family_dir:
            parent_label = str(family_entry.get("family_title") or family_entry.get("family_id") or token).strip()
            return {
                "requested_parent": token,
                "parent_label": parent_label,
                "parent_dir": family_dir,
                "parent_phase_id": None,
                "family_dir": family_dir,
                "resolution_kind": "family",
                "resolution_reason": "Resolved --parent directly to a phase family root.",
                "matched_phase_id": None,
                "matched_phase_number": None,
                "matched_ancestor_phase_id": None,
                "matched_ancestor_phase_number": None,
            }

    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        phase_payload = navigator.build_phase(token).to_dict(state.KERNEL_VERSION, full=True)
    except ValueError:
        phase_payload = None

    if phase_payload is not None:
        phase_entry = _phase_payload_from_navigation_dict(phase_payload)
        phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
        if phase_dir:
            parent_label = str(phase_entry.get("phase_title") or phase_entry.get("phase_id") or token).strip()
            parent_phase_id = str(phase_entry.get("phase_id") or "").strip() or None
            matched_phase_number = str(phase_entry.get("phase_number") or "").strip()
            family_dir = (
                canonicalize_write_path(str(phase_entry.get("family_dir") or "").strip())
                or _discover_phase_family_dir(phase_dir)
                or phase_dir
            )
            if requested_phase_number:
                requested_parts = _phase_number_parts(requested_phase_number)
                matched_parts = _phase_number_parts(matched_phase_number)
                requested_canonical_parts = _canonical_phase_number_parts(requested_phase_number)
                matched_canonical_parts = _canonical_phase_number_parts(matched_phase_number)
                shared_prefix = _shared_phase_prefix_length(matched_phase_number, requested_phase_number)

                if requested_canonical_parts == matched_canonical_parts:
                    raise ValueError(
                        f"--number {requested_phase_number} matches resolved parent phase {matched_phase_number}; "
                        "use a family token/path for sibling phases or a descendant number to nest."
                    )

                if (
                    requested_canonical_parts == matched_canonical_parts[: len(requested_canonical_parts)]
                    and len(requested_canonical_parts) < len(matched_canonical_parts)
                ):
                    raise ValueError(
                        f"--number {requested_phase_number} is an ancestor of resolved parent phase {matched_phase_number}; "
                        "pass the intended ancestor or family token/path directly instead of a descendant phase token."
                    )

                if matched_canonical_parts and requested_canonical_parts and shared_prefix == 0:
                    raise ValueError(
                        f"--number {requested_phase_number} is outside the family anchored by parent phase {matched_phase_number}; "
                        "pass the target family token/path instead of an existing phase token."
                    )

                if (
                    matched_canonical_parts
                    and requested_canonical_parts
                    and shared_prefix == len(matched_canonical_parts)
                    and len(requested_canonical_parts) > len(matched_canonical_parts)
                ):
                    return {
                        "requested_parent": token,
                        "parent_label": parent_label,
                        "parent_dir": phase_dir,
                        "parent_phase_id": parent_phase_id,
                        "family_dir": family_dir,
                        "resolution_kind": "phase",
                        "resolution_reason": "Resolved --parent to an existing phase and preserved nesting because the requested phase number is a descendant.",
                        "matched_phase_id": parent_phase_id,
                        "matched_phase_number": matched_phase_number or None,
                        "matched_ancestor_phase_id": None,
                        "matched_ancestor_phase_number": None,
                    }

                if matched_canonical_parts and requested_canonical_parts and 0 < shared_prefix < len(requested_canonical_parts):
                    if shared_prefix == 1:
                        family_entry = _resolve_phase_family_entry(family_dir) or {}
                        family_label = str(
                            family_entry.get("family_title")
                            or family_entry.get("family_id")
                            or Path(family_dir).name
                        ).strip()
                        return {
                            "requested_parent": token,
                            "parent_label": family_label,
                            "parent_dir": family_dir,
                            "parent_phase_id": None,
                            "family_dir": family_dir,
                            "resolution_kind": "phase_to_family_autolift",
                            "resolution_reason": (
                                f"Resolved --parent to phase {matched_phase_number}, but requested --number {requested_phase_number} "
                                "is a sibling or cousin outside that phase subtree; using the family root instead."
                            ),
                            "matched_phase_id": parent_phase_id,
                            "matched_phase_number": matched_phase_number or None,
                            "matched_ancestor_phase_id": None,
                            "matched_ancestor_phase_number": ".".join(requested_parts[:shared_prefix]) or None,
                        }

                    ancestor_number = ".".join(requested_parts[:shared_prefix])
                    ancestor_entry = _phase_entry_for_exact_phase_number(navigator, ancestor_number)
                    if ancestor_entry is None:
                        raise ValueError(
                            f"--number {requested_phase_number} shares ancestor phase {ancestor_number}, but that ancestor could not be resolved; "
                            "pass the intended parent token/path explicitly."
                        )
                    ancestor_dir = canonicalize_write_path(str(ancestor_entry.get("phase_dir") or "").strip()) or ""
                    ancestor_phase_id = str(ancestor_entry.get("phase_id") or "").strip() or None
                    if not ancestor_dir or not ancestor_phase_id:
                        raise ValueError(
                            f"--number {requested_phase_number} shares ancestor phase {ancestor_number}, but that ancestor could not be resolved cleanly; "
                            "pass the intended parent token/path explicitly."
                        )
                    ancestor_label = str(ancestor_entry.get("phase_title") or ancestor_phase_id or ancestor_number).strip()
                    return {
                        "requested_parent": token,
                        "parent_label": ancestor_label,
                        "parent_dir": ancestor_dir,
                        "parent_phase_id": ancestor_phase_id,
                        "family_dir": family_dir,
                        "resolution_kind": "phase_to_ancestor_autolift",
                        "resolution_reason": (
                            f"Resolved --parent to phase {matched_phase_number}, but requested --number {requested_phase_number} "
                            f"belongs under shared ancestor {ancestor_number}; using that ancestor as the parent."
                        ),
                        "matched_phase_id": parent_phase_id,
                        "matched_phase_number": matched_phase_number or None,
                        "matched_ancestor_phase_id": ancestor_phase_id,
                        "matched_ancestor_phase_number": ancestor_number,
                    }

            return {
                "requested_parent": token,
                "parent_label": parent_label,
                "parent_dir": phase_dir,
                "parent_phase_id": parent_phase_id,
                "family_dir": family_dir,
                "resolution_kind": "phase",
                "resolution_reason": "Resolved --parent directly to an existing phase token/path.",
                "matched_phase_id": parent_phase_id,
                "matched_phase_number": matched_phase_number or None,
                "matched_ancestor_phase_id": None,
                "matched_ancestor_phase_number": None,
            }

    candidate = Path(token)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(state.REPO_ROOT)
        except ValueError as exc:
            raise ValueError("--parent must stay inside the repo") from exc
    normalized = canonicalize_write_path(str(candidate)) or canonicalize_write_path(token)
    if not normalized:
        raise ValueError(f"Could not resolve --parent: {token}")
    parent_path = state.REPO_ROOT / normalized
    parent_dir = normalized
    if parent_path.exists() and parent_path.is_file():
        parent_dir = canonicalize_write_path(str(Path(normalized).parent))
    if not parent_dir or not parent_dir.startswith("obsidian/"):
        raise ValueError("--parent must resolve to an obsidian path, an existing phase token, or a phase family token")
    parent_label = Path(parent_dir).name
    return {
        "requested_parent": token,
        "parent_label": parent_label,
        "parent_dir": parent_dir.rstrip("/"),
        "parent_phase_id": None,
        "family_dir": "",
        "resolution_kind": "literal_path",
        "resolution_reason": "Resolved --parent as a literal obsidian path because it did not match a phase family or phase token.",
        "matched_phase_id": None,
        "matched_phase_number": None,
        "matched_ancestor_phase_id": None,
        "matched_ancestor_phase_number": None,
    }


def _active_phase_entry_for_lifecycle(phase_token: str | None) -> dict[str, Any] | None:
    activation = load_explicit_active_phase(state.REPO_ROOT)
    if not isinstance(activation, Mapping):
        return None

    phase_dir = canonicalize_write_path(str(activation.get("phase_dir") or "").strip()) or ""
    if not phase_dir:
        return None

    phase_id = str(activation.get("phase_id") or "").strip()
    phase_number = str(activation.get("phase_number") or "").strip()
    phase_title = str(activation.get("phase_title") or "").strip()
    requested = str(phase_token or "").strip()
    normalized_requested = canonicalize_write_path(requested) if requested else ""
    synth_md_path = canonicalize_write_path(f"{phase_dir}/synth_seed.md") or ""
    synth_json_path = canonicalize_write_path(f"{phase_dir}/synth_seed.json") or ""
    scaffold_path = canonicalize_write_path(f"{phase_dir}/phase_scaffold.json") or ""
    matches = {
        "",
        "__active__",
        phase_id,
        phase_number,
        phase_title,
        phase_dir,
        synth_md_path,
        synth_json_path,
        scaffold_path,
    }
    if requested and requested not in matches and normalized_requested not in matches:
        return None

    scaffold_payload = safe_load_json(state.REPO_ROOT / scaffold_path)
    if not isinstance(scaffold_payload, Mapping):
        return None

    family_dir = (
        canonicalize_write_path(str(activation.get("family_dir") or "").strip())
        or canonicalize_write_path(str(scaffold_payload.get("family_dir") or "").strip())
        or _discover_phase_family_dir(phase_dir)
        or ""
    )
    lifecycle = activation.get("lifecycle") if isinstance(activation.get("lifecycle"), Mapping) else {}
    canonical_entry_path = synth_md_path if (state.REPO_ROOT / synth_md_path).exists() else synth_json_path
    return {
        "phase_id": phase_id or str(scaffold_payload.get("phase_id") or "").strip() or None,
        "phase_number": phase_number or str(scaffold_payload.get("phase_number") or "").strip() or None,
        "phase_title": phase_title or str(scaffold_payload.get("phase_title") or "").strip() or None,
        "phase_dir": phase_dir,
        "family_dir": family_dir or None,
        "status": str(lifecycle.get("state") or scaffold_payload.get("status") or "").strip() or None,
        "lifecycle": dict(lifecycle),
        "spec_path": scaffold_path,
        "manifest_path": None,
        "canonical_entry": {
            "path": canonical_entry_path,
            "role": "synth_seed",
        },
        "entries": {
            "synth_seed": {
                "path": canonical_entry_path,
                "role": "synth_seed",
            }
        },
        "family_paths": [item for item in [canonical_entry_path, synth_json_path, scaffold_path] if item],
        "family_members": [],
        "archive_members": [],
    }


def _resolve_phase_entry_for_lifecycle(phase_token: str | None) -> tuple[KernelNavigation, dict[str, Any]]:
    active_entry = _active_phase_entry_for_lifecycle(phase_token)
    if active_entry is not None:
        return KernelNavigation(state.REPO_ROOT), active_entry

    navigator = KernelNavigation(state.REPO_ROOT)
    return navigator, navigator._resolve_phase_entry(phase_token)


def _resolve_family_entry_for_raw_seed(family_token: str | None) -> dict[str, str]:
    token = str(family_token or "").strip()
    if token and token != "__active__":
        family_entry = _resolve_phase_family_entry(token)
        if family_entry is None:
            raise ValueError(f"Could not resolve family token: {token}")
        return family_entry

    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        phase_entry = navigator._resolve_phase_entry(None)
    except ValueError:
        phase_entry = {}
    family_dir = canonicalize_write_path(str(phase_entry.get("family_dir") or "").strip()) if phase_entry else ""
    if not family_dir and phase_entry:
        family_dir = _discover_phase_family_dir(canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or "")
    if family_dir:
        family_entry = _resolve_phase_family_entry(family_dir)
        if family_entry is not None:
            return family_entry

    matches: list[dict[str, str]] = []
    obsidian_root = state.REPO_ROOT / "obsidian"
    if obsidian_root.exists():
        for marker_path in sorted(obsidian_root.rglob(PHASE_FAMILY_MARKER_FILENAME)):
            payload = _load_json_file(marker_path)
            if not isinstance(payload, Mapping):
                continue
            marker_rel = canonicalize_write_path(str(marker_path.relative_to(state.REPO_ROOT)))
            family_dir = canonicalize_write_path(str(payload.get("family_dir") or marker_path.parent.relative_to(state.REPO_ROOT)))
            if not family_dir:
                continue
            matches.append(
                {
                    "family_id": str(payload.get("family_id") or "").strip(),
                    "family_number": str(payload.get("family_number") or "").strip(),
                    "family_title": str(payload.get("family_title") or "").strip(),
                    "family_dir": family_dir,
                    "marker_path": marker_rel,
                }
            )
    if len(matches) == 1:
        return matches[0]
    raise ValueError("Could not resolve an active phase family. Pass an explicit family token.")


def _family_file_from_entry(family_entry: Mapping[str, Any], filename: str) -> Path:
    family_dir = canonicalize_write_path(str(family_entry.get("family_dir") or "").strip()) or ""
    if not family_dir:
        raise ValueError("Family entry is missing family_dir.")
    return state.REPO_ROOT / family_dir / filename


AGENT_SEED_REJECTION_MESSAGE = "Agent voice belongs in agent_seed.md. Use --append-agent-seed --author <agent_id>."
_AGENT_HEADING_DATE_RE = re.compile(r"(?P<year>\d{4})[-_ ](?P<month>\d{2})[-_ ](?P<day>\d{2})")
_AGENT_AUTHORED_HEADING_RE = re.compile(r"^\s*##\s*agent-authored\b", re.IGNORECASE)


def _agent_seed_standard() -> dict[str, Any]:
    repo_root = getattr(state, "REPO_ROOT", Path(__file__).resolve().parents[5])
    path = Path(repo_root) / "codex/standards/observe_apply/std_agent_seed.json"
    payload = safe_load_json(path) if path.exists() else {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _supported_agent_seed_authors() -> tuple[list[str], str]:
    standard = _agent_seed_standard()
    paragraph_shape = standard.get("paragraph_shape") if isinstance(standard.get("paragraph_shape"), Mapping) else {}
    authored_by = paragraph_shape.get("authored_by") if isinstance(paragraph_shape, Mapping) else {}
    literals = [
        str(item).strip()
        for item in (authored_by.get("allowed_literals") or [])
        if str(item).strip()
    ] if isinstance(authored_by, Mapping) else []
    if not literals:
        literals = ["claude_code", "codex", "agent_collective"]
    pattern = (
        str(authored_by.get("regex") or "").strip()
        if isinstance(authored_by, Mapping)
        else ""
    ) or r"^claude_subagent_[a-z0-9_]+$"
    return literals, pattern


def _agent_identity_heading_re() -> re.Pattern[str]:
    literals, regex = _supported_agent_seed_authors()
    escaped = "|".join(re.escape(item) for item in literals if item)
    prefix = rf"(?:{escaped}|{regex.strip('^$')})" if escaped else regex.strip("^$")
    return re.compile(rf"^\s*##\s*(?:{prefix})\b", re.IGNORECASE)


def _is_agent_heading_line(line: str) -> bool:
    stripped = str(line or "").strip()
    if not stripped:
        return False
    return bool(_AGENT_AUTHORED_HEADING_RE.match(stripped) or _agent_identity_heading_re().match(stripped))


def _is_agent_heading_token(token: str) -> bool:
    stripped = str(token or "").strip()
    if not stripped:
        return False
    if stripped.lower().startswith("agent-authored"):
        return True
    return bool(re.match(_agent_identity_heading_re().pattern.replace(r"^\s*##\s*", r"^\s*"), stripped, re.IGNORECASE))


def _first_nonempty_line(text: str) -> str:
    for line in str(text or "").splitlines():
        if line.strip():
            return line
    return ""


def _detect_agent_heading_lines(text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for index, line in enumerate(str(text or "").splitlines(), start=1):
        if _is_agent_heading_line(line):
            matches.append({"line": index, "heading": line.strip()})
    return matches


def _normalize_gesture_text(value: str) -> str:
    token = re.sub(r"[_-]+", " ", str(value or "").strip())
    token = re.sub(r"\s+", " ", token).strip()
    return token or "agent note"


def _derive_agent_seed_gesture(body: str) -> str:
    for raw_line in str(body or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("<!--"):
            continue
        line = re.sub(r"^#+\s*", "", line)
        words = re.split(r"\s+", line)
        return _normalize_gesture_text(" ".join(words[:10]))
    return "agent note"


def _parse_historical_agent_heading(heading: str) -> dict[str, str]:
    raw_heading = str(heading or "").strip()
    stripped = re.sub(r"^\s*#+\s*", "", raw_heading).strip()
    lowered = stripped.casefold()
    body = stripped
    if lowered.startswith("agent-authored"):
        body = re.sub(r"^agent-authored(?:\s*[—:-]\s*|\s+|-+)", "", stripped, flags=re.IGNORECASE).strip("-—: ,")

    date_match = _AGENT_HEADING_DATE_RE.search(body)
    author = ""
    gesture = body
    date_token = datetime.now(timezone.utc).strftime("%Y %m %d")
    if date_match:
        date_token = f"{date_match.group('year')} {date_match.group('month')} {date_match.group('day')}"
        before = body[: date_match.start()].strip(" -—,:")
        after = body[date_match.end() :].strip(" -—,:")
        gesture = " ".join(part for part in [before, after] if part).strip()
        candidate = before.split(",", 1)[0].strip() if before else ""
        literals, regex = _supported_agent_seed_authors()
        if candidate in literals or re.match(regex, candidate):
            author = candidate
            gesture = after or ""
    if not author:
        identity_match = re.match(_agent_identity_heading_re().pattern.replace(r"^\s*##\s*", r"^\s*"), body, re.IGNORECASE)
        if identity_match:
            author = identity_match.group(0).strip()
            author = re.split(r"[\s,]", author, maxsplit=1)[0].strip()
    if not author:
        author = "agent_collective"
    return {
        "author": author.casefold(),
        "date_token": date_token,
        "gesture": _normalize_gesture_text(gesture),
    }


def _family_seed_artifacts(
    family_payload: Mapping[str, Any],
    family_entry: Mapping[str, Any],
) -> dict[str, str]:
    family_dir = canonicalize_write_path(str(family_payload.get("family_dir") or family_entry.get("family_dir") or "").strip()) or ""
    if not family_dir:
        raise ValueError("family_dir is required on phase_family.json.")
    return {
        "family_dir": family_dir,
        "raw_seed_path": canonicalize_write_path(str(family_payload.get("raw_seed_path") or "").strip()) or raw_seed_markdown_path_for_family(family_dir),
        "raw_seed_json_path": canonicalize_write_path(str(family_payload.get("raw_seed_json_path") or "").strip()) or raw_seed_json_path_for_family(family_dir),
        "raw_seed_snapshot_path": canonicalize_write_path(str(family_payload.get("raw_seed_snapshot_path") or "").strip()) or raw_seed_snapshot_path_for_family(family_dir),
        "agent_seed_path": canonicalize_write_path(str(family_payload.get("agent_seed_path") or "").strip()) or agent_seed_markdown_path_for_family(family_dir),
        "agent_seed_json_path": canonicalize_write_path(str(family_payload.get("agent_seed_json_path") or "").strip()) or agent_seed_json_path_for_family(family_dir),
        "agent_seed_snapshot_path": canonicalize_write_path(str(family_payload.get("agent_seed_snapshot_path") or "").strip()) or agent_seed_snapshot_path_for_family(family_dir),
    }


def _migration_ledger_path_for_family(family_payload: Mapping[str, Any]) -> Path:
    family_number = str(
        family_payload.get("family_number")
        or family_payload.get("family_id")
        or "unknown"
    ).strip().replace(".", "_").replace("-", "_")
    return state.REPO_ROOT / f"state/agent_seed_migration/2026_04_20_phase_{family_number}.json"


def _load_or_init_migration_ledger(path: Path, *, family_payload: Mapping[str, Any]) -> dict[str, Any]:
    existing = safe_load_json(path) if path.exists() else {}
    if isinstance(existing, Mapping):
        ledger = dict(existing)
    else:
        ledger = {}
    ledger.setdefault("kind", "agent_seed_migration")
    ledger.setdefault("schema_version", "agent_seed_migration_v1")
    ledger.setdefault("migration_date", "2026_04_20")
    ledger.setdefault("family_id", str(family_payload.get("family_id") or "").strip())
    ledger.setdefault("family_number", str(family_payload.get("family_number") or "").strip())
    ledger.setdefault("family_title", str(family_payload.get("family_title") or "").strip())
    ledger.setdefault("family_dir", str(family_payload.get("family_dir") or "").strip())
    ledger.setdefault("section_id_map", {})
    ledger.setdefault("paragraph_id_map", {})
    ledger.setdefault("records", [])
    return ledger


def _phase_scaffold_path_for_entry(phase_entry: Mapping[str, Any]) -> Path:
    spec_path = canonicalize_write_path(str(phase_entry.get("spec_path") or "").strip()) or ""
    if not spec_path:
        phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
        if not phase_dir:
            raise ValueError("Phase entry is missing both spec_path and phase_dir.")
        spec_path = canonicalize_write_path(f"{phase_dir}/phase_scaffold.json") or ""
    candidate = state.REPO_ROOT / spec_path
    if not candidate.exists():
        raise ValueError(f"phase_scaffold.json not found: {spec_path}")
    return candidate


def _phase_file_from_entry(phase_entry: Mapping[str, Any], filename: str) -> Path:
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    if not phase_dir:
        raise ValueError("Phase entry is missing phase_dir.")
    return state.REPO_ROOT / phase_dir / filename


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _wave_ledger_entry(
    *,
    phase_entry: Mapping[str, Any],
    wave: Mapping[str, Any],
    normalized_synth: Mapping[str, Any],
    archived_synth_path: str,
    delta_path: str,
    continuation_summary_path: str,
    files_touched: list[str],
    legacy_cycle_index: int | None = None,
) -> dict[str, Any]:
    continuation_payload = safe_load_json(state.REPO_ROOT / continuation_summary_path) if continuation_summary_path else {}
    routing_outcome = ""
    learning_summary = ""
    artifact_paths = [archived_synth_path]
    if delta_path:
        artifact_paths.append(delta_path)
    if continuation_summary_path and (state.REPO_ROOT / continuation_summary_path).exists():
        artifact_paths.append(continuation_summary_path)
    if isinstance(continuation_payload, Mapping):
        routing_outcome = str(
            continuation_payload.get("routing_outcome")
            or continuation_payload.get("last_wave_outcome")
            or continuation_payload.get("status")
            or ""
        ).strip()
        learning_summary = str(
            continuation_payload.get("learning_summary")
            or continuation_payload.get("summary")
            or continuation_payload.get("notes")
            or ""
        ).strip()
        if isinstance(continuation_payload.get("artifacts"), list):
            artifact_paths.extend(
                [
                    canonicalize_write_path(str(item)) or str(item).strip()
                    for item in continuation_payload.get("artifacts", [])
                    if str(item).strip()
                ]
            )
        if isinstance(continuation_payload.get("artifact_paths"), list):
            artifact_paths.extend(
                [
                    canonicalize_write_path(str(item)) or str(item).strip()
                    for item in continuation_payload.get("artifact_paths", [])
                    if str(item).strip()
                ]
            )
    return {
        "wave_id": str(wave.get("wave_id") or "").strip() or "wave_001",
        "track_id": str(wave.get("track_id") or "").strip() or None,
        "mode": str(wave.get("mode") or normalized_synth.get("execution_mode") or "").strip() or None,
        "legacy_cycle_index": int(legacy_cycle_index if legacy_cycle_index is not None else normalized_synth.get("meta", {}).get("current_cycle") or 0),
        "routing_outcome": routing_outcome or None,
        "files_touched": files_touched,
        "artifacts": sorted({item for item in artifact_paths if item}),
        "archived_synth_path": archived_synth_path,
        "learning_summary": learning_summary or str(normalized_synth.get("next_step_posture") or "").strip() or None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": f"Closed {str(wave.get('wave_id') or 'wave')} for {str(phase_entry.get('phase_title') or phase_entry.get('phase_id') or '').strip()}.",
    }


_PHASE_STEP_CHECKPOINT_LABEL = "wave_checkpoint"


def _phase_step_family_dir(phase_entry: Mapping[str, Any]) -> str:
    family_dir = canonicalize_write_path(str(phase_entry.get("family_dir") or "").strip()) or ""
    if family_dir:
        return family_dir
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    return _discover_phase_family_dir(phase_dir) or ""


def _ensure_phase_family_autonomous_seed(phase_entry: Mapping[str, Any]) -> dict[str, Any]:
    family_dir = _phase_step_family_dir(phase_entry)
    if not family_dir:
        return {}
    json_rel, markdown_rel, payload = write_autonomous_seed(state.REPO_ROOT, family_dir=family_dir)
    return {
        "family_dir": family_dir,
        "autonomous_seed_path": json_rel,
        "autonomous_seed_markdown_path": markdown_rel,
        "payload": payload,
    }


def _phase_step_cycle_dir(*, phase_dir: str, legacy_cycle_index: int) -> str:
    return canonicalize_write_path(f"{phase_dir}/cycle_{max(0, int(legacy_cycle_index))}") or ""


def _phase_step_result_note_path(*, cycle_dir: str) -> str:
    return canonicalize_write_path(f"{cycle_dir}/phase_step_result.md") or ""


def _phase_step_label(raw_group: Mapping[str, Any], *, index: int) -> str:
    base = (
        str(raw_group.get("group_id") or "").strip()
        or str(raw_group.get("label") or "").strip()
        or str(raw_group.get("title") or "").strip()
        or f"group_{index:02d}"
    )
    return re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower() or f"group_{index:02d}"


def _phase_step_group_aliases(raw_group: Mapping[str, Any], *, index: int) -> list[str]:
    aliases: list[str] = []
    for candidate in (
        str(raw_group.get("group_id") or "").strip(),
        str(raw_group.get("label") or "").strip()
        or "",
        str(raw_group.get("title") or "").strip(),
        f"group_{index:02d}",
    ):
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", candidate).strip("_").lower()
        if normalized and normalized not in aliases:
            aliases.append(normalized)
    return aliases


def _phase_step_targets(
    raw_group: Mapping[str, Any],
    *,
    fallback_paths: Sequence[str],
    stage_kind: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in raw_group.get("targets", []) if isinstance(raw_group.get("targets"), list) else []:
        if isinstance(item, Mapping):
            file_path = canonicalize_write_path(str(item.get("file") or "").strip()) or ""
            if file_path:
                output.append(
                    {
                        "file": file_path,
                        "scope": str(item.get("scope") or "full").strip() or "full",
                        **({"name": str(item.get("name")).strip()} if str(item.get("name") or "").strip() else {}),
                    }
                )
        elif str(item).strip():
            file_path = canonicalize_write_path(str(item).strip()) or ""
            if file_path:
                output.append({"file": file_path, "scope": "full"})
    reads = raw_group.get("reads") if isinstance(raw_group.get("reads"), list) else []
    for item in reads:
        file_path = canonicalize_write_path(str(item).strip()) or ""
        if file_path:
            output.append({"file": file_path, "scope": "full"})
    if not output:
        for item in fallback_paths:
            file_path = canonicalize_write_path(str(item).strip()) or ""
            if file_path:
                output.append({"file": file_path, "scope": "full"})
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in output:
        identity = (
            str(row.get("file") or "").strip(),
            str(row.get("scope") or "").strip(),
            str(row.get("name") or "").strip(),
        )
        if not identity[0] or identity in seen:
            continue
        seen.add(identity)
        deduped.append(_phase_step_budget_target(row, stage_kind=stage_kind))
    return deduped


def _phase_step_roster_entry(
    *,
    label: str,
    title: str,
    question: str,
    targets: Sequence[Mapping[str, Any]],
) -> str:
    reads = [str(item.get("file") or "").strip() for item in targets if str(item.get("file") or "").strip()]
    target_summary = ", ".join(reads[:3])
    if len(reads) > 3:
        target_summary += f", plus {len(reads) - 3} more paths"
    statement = question or title or label
    if target_summary:
        return f"`{label}` owns {statement} It reads {target_summary}."
    return f"`{label}` owns {statement}."


_PHASE_STEP_AUTO_OUTLINE_THRESHOLD_BYTES = 100_000


def _phase_step_budget_target(target: Mapping[str, Any], *, stage_kind: str) -> dict[str, Any]:
    payload = dict(target)
    scope = str(payload.get("scope") or "full").strip() or "full"
    if scope != "full":
        return payload
    file_path = canonicalize_write_path(str(payload.get("file") or "").strip()) or ""
    if not file_path:
        return payload
    resolved = (state.REPO_ROOT / file_path).resolve()
    if not resolved.exists() or not resolved.is_file():
        return payload
    try:
        file_size = resolved.stat().st_size
    except OSError:
        return payload
    if file_size < _PHASE_STEP_AUTO_OUTLINE_THRESHOLD_BYTES:
        return payload
    notes = str(payload.get("notes") or "").strip()
    auto_note = (
        f"Auto-demoted to outline for phase-step prompt budget during `{stage_kind}` "
        f"(size={file_size} bytes)."
    )
    payload["scope"] = "outline"
    payload["notes"] = f"{notes} {auto_note}".strip() if notes else auto_note
    return payload


def _phase_step_context_files(
    *,
    scaffold_path: Path,
    synth_path: Path,
) -> list[str]:
    return sorted(
        {
            item
            for item in (
                state.rel(scaffold_path),
                state.rel(synth_path),
            )
            if item
        }
    )


def _phase_step_stage_prompt(stage_kind: str) -> str:
    if stage_kind == "solution_space":
        return "Evaluate bounded approaches, tradeoffs, and scope fit. Surface candidate solutions rather than implementation details."
    if stage_kind == "plan_space":
        return "Sequence a concrete plan that is ready for operator-gated apply or higher-level handoff."
    return "Surface scoped facts, open questions, and boundary corrections before advancing the wave."


def _compile_phase_step_observe_plan(
    *,
    phase_entry: Mapping[str, Any],
    scaffold_payload: Mapping[str, Any],
    synth_payload: Mapping[str, Any],
    autonomous_seed_path: str | None,
    preview: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = normalize_synth_payload(synth_payload, phase_scaffold=scaffold_payload) or {}
    current_wave = normalized.get("current_wave") if isinstance(normalized.get("current_wave"), Mapping) else {}
    phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
    phase_id = str(phase_entry.get("phase_id") or phase_entry.get("phase_number") or "").strip() or "phase"
    wave_id = str(current_wave.get("wave_id") or "wave_001").strip()
    stage_kind = str(current_wave.get("stage_kind") or "problem_space").strip().lower() or "problem_space"
    legacy_cycle_index = int(preview.get("legacy_cycle_index") or 0)
    cycle_dir = _phase_step_cycle_dir(phase_dir=phase_dir, legacy_cycle_index=legacy_cycle_index)
    plan_context_files = _phase_step_context_files(
        scaffold_path=_phase_scaffold_path_for_entry(phase_entry),
        synth_path=_phase_file_from_entry(phase_entry, "synth_seed.json"),
    )
    fallback_paths = [
        str(item).strip()
        for item in (current_wave.get("target_paths") or [])
        if str(item).strip()
    ]
    raw_groups = [
        dict(item)
        for item in (current_wave.get("groups") or [])
        if isinstance(item, Mapping)
    ]
    if not raw_groups:
        raw_groups = [
            {
                "title": "primary_probe",
                "answer": str(current_wave.get("bounded_question") or "").strip() or "Advance the bounded wave.",
                "reads": fallback_paths,
                "depends_on": [],
            }
        ]
    label_aliases: dict[str, str] = {}
    probe_specs: list[dict[str, Any]] = []
    for index, raw_group in enumerate(raw_groups, start=1):
        label = _phase_step_label(raw_group, index=index)
        title = str(raw_group.get("title") or raw_group.get("label") or label).strip()
        for alias in _phase_step_group_aliases(raw_group, index=index):
            label_aliases[alias] = label
        label_aliases[title] = label
        targets = _phase_step_targets(raw_group, fallback_paths=fallback_paths, stage_kind=stage_kind)
        role = str(raw_group.get("role") or "probe").strip().lower() or "probe"
        if role == "reducer":
            role = "synthesis"
        response_file = (
            canonicalize_write_path(str(raw_group.get("response_path") or raw_group.get("response_file") or "").strip())
            or str(raw_group.get("response_path") or raw_group.get("response_file") or "").strip()
        )
        target_path = (
            canonicalize_write_path(str(raw_group.get("target_path") or "").strip())
            or str(raw_group.get("target_path") or "").strip()
        )
        response_surface = raw_group.get("response_surface")
        question = (
            str(raw_group.get("answer") or "").strip()
            or str(raw_group.get("question") or "").strip()
            or str(current_wave.get("bounded_question") or "").strip()
            or "Advance the bounded wave."
        )
        probe_specs.append(
            {
                "label": label,
                "title": title,
                "role": role,
                "targets": targets,
                "question": question,
                "response_file": response_file,
                "target_path": target_path,
                "response_surface": (
                    dict(response_surface)
                    if isinstance(response_surface, Mapping)
                    else str(response_surface).strip() if str(response_surface or "").strip() else None
                ),
                "incoming_queries": [
                    dict(item)
                    for item in (raw_group.get("incoming_queries") or [])
                    if isinstance(item, Mapping)
                ],
                "depends_on": [
                    str(item).strip()
                    for item in (raw_group.get("depends_on") or [])
                    if str(item).strip()
                ],
            }
        )
    for spec in probe_specs:
        resolved: list[str] = []
        for item in spec["depends_on"]:
            resolved.append(
                label_aliases.get(
                    item,
                    label_aliases.get(
                        re.sub(r"[^a-zA-Z0-9]+", "_", item).strip("_").lower(),
                        _phase_step_label({"label": item}, index=1),
                    ),
                )
            )
        spec["depends_on"] = [item for item in resolved if item and item != spec["label"]]
    roster_by_label: dict[str, list[str]] = {}
    for spec in probe_specs:
        siblings = [item for item in probe_specs if item["label"] != spec["label"]]
        roster: list[str] = []
        for sibling in siblings[:8]:
            roster.append(
                _phase_step_roster_entry(
                    label=sibling["label"],
                    title=sibling["title"],
                    question=sibling["question"],
                    targets=sibling["targets"],
                )
            )
        if len(siblings) > 8:
            roster.append(f"{len(siblings) - 8} additional sibling groups exist outside this compact roster.")
        roster_by_label[spec["label"]] = roster
    probe_groups = [
        {
            "label": spec["label"],
            "role": spec["role"] or "probe",
            "situation": f"phase_step:{stage_kind}",
            "question": spec["question"],
            "acceptance": "Return a JSON receipt with files examined, grounded facts, open questions, insufficiencies, and optional cross-group queries.",
            "notes": _phase_step_stage_prompt(stage_kind),
            "output_contract": [
                "files_examined",
                "facts",
                "open_questions",
                "insufficiencies",
                "cross_group_queries",
                "summary",
            ],
            "response_schema": phase_step_controller.phase_step_probe_schema(stage_kind),
            "json_only": True,
            "downstream_consumer": _PHASE_STEP_CHECKPOINT_LABEL,
            "context_files": [],
            "sibling_scope_roster": roster_by_label.get(spec["label"], []),
            "incoming_queries": spec["incoming_queries"],
            "depends_on": spec["depends_on"],
            "targets": spec["targets"],
            **({"response_file": spec["response_file"]} if spec.get("response_file") else {}),
            **({"target_path": spec["target_path"]} if spec.get("target_path") else {}),
            **({"response_surface": spec["response_surface"]} if spec.get("response_surface") else {}),
        }
        for spec in probe_specs
    ]
    checkpoint_group = {
        "label": _PHASE_STEP_CHECKPOINT_LABEL,
        "role": "evaluation",
        "situation": f"phase_step_checkpoint:{stage_kind}",
        "question": (
            f"Using the upstream probe receipts for `{wave_id}`, decide whether the wave should clarify, advance, "
            "reframe, escalate, abort, or complete within the legal transition matrix for this stage."
        ),
        "acceptance": "Return one JSON checkpoint receipt with decision, checkpoint_summary, current_focus, insufficiencies, and any carry-forward posture.",
        "notes": (
            f"Apply rubric `{str(preview.get('checkpoint_policy', {}).get('rubric_id') or '')}` and keep the decision inside the legal transition set "
            f"for `{stage_kind}`."
        ).strip(),
        "output_contract": [
            "decision",
            "checkpoint_summary",
            "current_focus",
            "insufficiencies",
            "next_step_posture",
            "carry_forward_posture",
            "bounded_question",
            "target_paths",
            "success_signals",
            "confirmed_facts",
            "locked_decisions",
            "active_risks",
            "orientation_patch",
        ],
        "response_schema": phase_step_controller.phase_step_checkpoint_schema(stage_kind),
        "json_only": True,
        "downstream_consumer": "phase_assimilate",
        "context_files": [],
        "depends_on": [group["label"] for group in probe_groups],
        "targets": [],
    }
    success_signals = [str(item).strip() for item in (current_wave.get("success_signals") or []) if str(item).strip()]
    carry_forward_posture = str(
        current_wave.get("carry_forward_posture")
        or normalized.get("next_step_posture")
        or ""
    ).strip() or None
    return {
        "schema_version": "1.0",
        "template_version": f"phase_step:{phase_id}@1.0",
        "prompt": "Wave-Native Subphase Stepper v1",
        "notes": str(current_wave.get("objective") or "").strip() or None,
        "goal_question": str(current_wave.get("bounded_question") or "").strip() or "Advance the bounded wave.",
        "success_criteria": "\n".join(success_signals) if success_signals else None,
        "wait_notes": f"Return JSON receipts only. Stage `{stage_kind}`. Wave `{wave_id}`.",
        "dump_dir": cycle_dir,
        "result_note_path": _phase_step_result_note_path(cycle_dir=cycle_dir) or None,
        "context_files": plan_context_files,
        "context_merge_mode": "merge",
        "campaign_id": phase_id,
        "round_id": wave_id,
        "round_index": legacy_cycle_index + 1,
        "carry_forward_posture": carry_forward_posture,
        "problem_text": str(current_wave.get("objective") or "").strip() or None,
        "cycle_dir": cycle_dir or None,
        "cycle_context_mode": "minimal",
        "raw_seed_family": _phase_step_family_dir(phase_entry) or None,
        "groups": [*probe_groups, checkpoint_group],
    }


def _compile_phase_observe_plan_payload(
    phase_token: str | None,
    *,
    write_plan_to: str | None = None,
    shard_packet_request: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    """
    - Teleology: Materialize the exact token `build_phase_observe` into a validated observe-plan payload and resolved write target.
    - When-needed: Open when `build_phase_observe` coverage should route to the navigate-layer seam that validates and persists the compiled observe plan before launch.
    - Escalates-to: system/lib/kernel_nav_phase.py; system/lib/kernel/commands/navigate.py::cmd_phase_observe
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    result = navigator.build_phase_observe(
        phase_token,
        write_plan_to=write_plan_to,
        shard_packet_request=shard_packet_request,
    )
    try:
        target_path = _kernel_resolve_write_plan_path(write_plan_to)
    except ValueError as exc:
        raise ValueError(f"write path must remain inside repo: {write_plan_to}") from exc
    observe_plan = result.payload.get("observe_plan")
    if not isinstance(observe_plan, dict):
        raise ValueError("phase observe builder did not return a valid observe plan payload")
    errors, warnings = _kernel_validate_observe_payload(observe_plan)
    if errors:
        raise ValueError("invalid phase observe plan: " + "; ".join(errors))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(observe_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return observe_plan, target_path, {"warnings": warnings, "result": result.payload}


def _write_next_pass_plan_payload(
    manifest_path: Path,
    manifest_payload: Mapping[str, Any],
    *,
    target_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    next_plan, _prior_plan_path, metadata = _kernel_build_next_pass_plan_payload(manifest_path, manifest_payload)
    errors, warnings = _kernel_validate_observe_payload(next_plan)
    if errors:
        raise ValueError("invalid next-pass plan: " + "; ".join(errors))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(next_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return next_plan, {"warnings": warnings, **metadata}


def _run_observe_plan_sync(
    *,
    plan_path: Path,
    plan_payload: Mapping[str, Any],
    bridge_enabled: bool,
    bridge_provider: str | None,
    bridge_max_chars: int,
    bridge_timeout_s: float,
    bridge_workers: Any,
    launch_profile: str | None = None,
) -> tuple[str, dict[str, Any]]:
    runtime_kind = _kernel_observe_runtime_kind(dict(plan_payload))
    resolved_launch_profile = _kernel_normalize_launch_profile(launch_profile, default=_kernel_observe_launch_profile_default())
    launch_metadata = {
        "launch_mode": "campaign_loop",
        "runtime": runtime_kind,
        "launch_profile": resolved_launch_profile,
        "requested_workers": _kernel_coerce_bridge_workers_arg(bridge_workers),
        "bridge_provider_requested": str(bridge_provider or "").strip() or None,
        "bridge_provider_used": str(bridge_provider or "").strip() or None,
        "launch_dispatch": "local",
    }
    if runtime_kind == "observe_session":
        from tools.meta.apply.observe_session_runner import run_session_once

        summary = run_session_once(
            repo_root=state.REPO_ROOT,
            plan_path=plan_path,
            bridge_enabled=bridge_enabled,
            provider=bridge_provider,
            timeout_s=bridge_timeout_s,
            max_workers=_kernel_coerce_bridge_workers_arg(bridge_workers),
            bridge_max_chars=bridge_max_chars,
            launch_profile=resolved_launch_profile,
            launch_metadata=launch_metadata,
        )
        return runtime_kind, summary
    from tools.meta.apply.run_observe_plan import run_once

    summary = run_once(
        repo_root=state.REPO_ROOT,
        plan_path=plan_path,
        result_path=state.OBSERVE_RESULT,
        history_dir=state.OBSERVE_HISTORY_DIR,
        sentence_count=0,
        sticky_dump_dir=True,
        bridge_enabled=bridge_enabled,
        bridge_provider=bridge_provider,
        bridge_max_chars=bridge_max_chars,
        bridge_timeout_s=bridge_timeout_s,
        bridge_workers=_kernel_coerce_bridge_workers_arg(bridge_workers),
        launch_profile=resolved_launch_profile,
        launch_metadata=launch_metadata,
    )
    return runtime_kind, summary


def _rewrite_verify_command(command: str) -> str:
    stripped = str(command).strip()
    venv_python = _kernel_repo_venv_python()
    if not stripped or not venv_python.exists():
        return str(command)
    try:
        tokens = shlex.split(stripped)
    except ValueError:
        return str(command)
    if not tokens:
        return str(command)
    first = tokens[0]
    current_name = Path(first).name.lower()
    venv_rel = "./repo-python"
    try:
        if Path(first).resolve().samefile(venv_python):
            return str(command)
    except Exception:
        pass
    if current_name == "pytest":
        return shlex.join([venv_rel, "-m", "pytest", *tokens[1:]])
    if current_name.startswith("python"):
        if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] == "pytest":
            return shlex.join([venv_rel, "-m", "pytest", *tokens[3:]])
        return shlex.join([venv_rel, *tokens[1:]])
    return str(command)


# WARNING: _resolve_doc_registry_path NOT FOUND



# WARNING: _resolve_raw_seed_and_index_for_family NOT FOUND



# WARNING: _load_mission_params NOT FOUND



# ---------------------------------------------------------------------------
# Public command functions
# ---------------------------------------------------------------------------


INFO_NAVIGATION_KIND = "kernel.navigate.info"


def _info_active_execution_entry(
    profile_sink: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    started = perf_counter()
    try:
        from system.lib.active_execution_constellation import build_active_execution_constellation

        active_execution = build_active_execution_constellation(
            state.REPO_ROOT,
            include_runtime_status=False,
            campaign_limit=3,
            claim_limit=0,
            session_limit=0,
        )
    except Exception:
        _profile_phase(profile_sink, "info_active_execution_entry", started)
        return {}, []
    _profile_phase(profile_sink, "info_active_execution_entry", started)

    anchor = (
        active_execution.get("declared_anchor")
        if isinstance(active_execution.get("declared_anchor"), Mapping)
        else {}
    )
    campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    awareness_cards = (
        live_sessions.get("awareness_cards")
        if isinstance(live_sessions.get("awareness_cards"), list)
        else []
    )
    stale_pointers = (
        active_execution.get("stale_decorative_pointers")
        if isinstance(active_execution.get("stale_decorative_pointers"), list)
        else []
    )
    has_live_work = bool(
        campaigns
        or int(session_counts.get("active_claims") or 0)
        or stale_pointers
        or str(anchor.get("status") or "") == "declared_anchor_runtime_dormant"
    )
    if not has_live_work:
        return {}, []

    compact_campaigns: list[dict[str, Any]] = []
    for campaign in campaigns[:3]:
        if not isinstance(campaign, Mapping):
            continue
        compact_campaigns.append(
            {
                key: campaign.get(key)
                for key in ("workitem_id", "rank", "state", "title", "drilldown_command")
                if campaign.get(key) not in (None, "", [], {})
            }
        )
    drilldowns = (
        live_sessions.get("drilldown_commands")
        if isinstance(live_sessions.get("drilldown_commands"), Mapping)
        else {}
    )
    entry = {
        "kind": active_execution.get("kind") or "active_execution_constellation",
        "view_profile": "info_live_work_entry",
        "declared_anchor": {
            key: anchor.get(key)
            for key in ("phase_id", "status", "runtime_state", "runtime_gate_reason")
            if anchor.get(key) not in (None, "", [], {})
        },
        "live_campaigns": compact_campaigns,
        "live_sessions": {
            "counts": {
                key: session_counts.get(key)
                for key in ("active_claims", "effective_active_sessions", "orphaned_active_sessions")
                if session_counts.get(key) not in (None, "", [], {})
            },
            "awareness_cards": [
                {
                    key: card.get(key)
                    for key in (
                        "session_id",
                        "actor",
                        "freshness_state",
                        "pass_state",
                        "current_pass_line",
                        "last_pass_result_line",
                        "source",
                    )
                    if isinstance(card, Mapping) and card.get(key) not in (None, "", [], {})
                }
                for card in awareness_cards[:2]
                if isinstance(card, Mapping)
            ],
            "drilldown_commands": {
                key: drilldowns.get(key)
                for key in ("cards", "seed_speed_no_heartbeat", "overview")
                if drilldowns.get(key)
            },
        },
        "liveness_summary": (
            "Declared phase is contextual/dormant; choose live work from WorkItems and claims."
            if str(anchor.get("status") or "") == "declared_anchor_runtime_dormant"
            else "Verify live WorkItems and claims before using phase context."
        ),
        "authority_order": ["Task Ledger WorkItems", "Work Ledger claims", "phase/working-set context"],
    }
    if stale_pointers and isinstance(stale_pointers[0], Mapping):
        entry["stale_decorative_pointer"] = {
            key: stale_pointers[0].get(key)
            for key in ("pointer", "replacement_surface")
            if stale_pointers[0].get(key) not in (None, "", [], {})
        }

    next_actions: list[dict[str, str]] = []
    for campaign in compact_campaigns:
        command = str(campaign.get("drilldown_command") or "").strip()
        if command:
            workitem_id = str(campaign.get("workitem_id") or "").strip()
            next_actions.append(
                {
                    "command": command,
                    "reason": (
                        "Open the hot Task Ledger WorkItem before phase/subphase context"
                        f"{f' ({workitem_id})' if workitem_id else ''}."
                    ),
                }
            )
            break
    work_ledger_cards = str(drilldowns.get("cards") or "").strip()
    if work_ledger_cards and int(session_counts.get("active_claims") or 0):
        next_actions.append(
            {
                "command": work_ledger_cards,
                "reason": "Open the compact active-seed session packet before using phase or working-set files as the write set.",
            }
        )
    next_actions.append(
        {
            "command": "./repo-python kernel.py --pulse",
            "reason": "Use pulse for the compact runtime/control-plane view after the first live-work handle.",
        }
    )
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for action in next_actions:
        command = str(action.get("command") or "").strip()
        if not command or command in seen:
            continue
        seen.add(command)
        deduped.append(action)
    return entry, deduped[:3]


def _info_compact_result(profile_sink: list[dict[str, Any]] | None = None) -> NavigationResult:
    """Build the default compact --info result without materializing the full manifest."""
    started = perf_counter()
    warnings: list[str] = []
    if not state.MAP_FILE.exists():
        warnings.append("derived map missing; run `python3 kernel.py --build` for optional enrichment")
    if not state.KERNEL_SKILLS_SCHEMA.exists():
        warnings.append("kernel skills schema missing")
    if not (state.REPO_ROOT / "codex" / "doctrine" / "skills" / "kernel" / "navigate.md").exists():
        warnings.append("navigate skill doc missing")
    _profile_phase(profile_sink, "warning_checks", started)

    minimum_read_sets: dict[str, Any] = {}
    bootstrap_sequence: list[dict[str, Any]] = []
    try:
        from system.lib.agent_bootstrap_projection import (
            load_agent_bootstrap_config,
            normalize_bootstrap_sequence,
            normalize_minimum_read_sets,
        )

        bootstrap_cfg = load_agent_bootstrap_config(state.REPO_ROOT)
        minimum_read_sets = normalize_minimum_read_sets(bootstrap_cfg.get("minimum_read_sets"))
        bootstrap_sequence = normalize_bootstrap_sequence(bootstrap_cfg.get("bootstrap_sequence"))
    except Exception:
        pass
    _profile_phase(profile_sink, "bootstrap_config", started)

    docs_focus_summary: dict[str, Any] = {}
    try:
        from system.control.documentation_route_focus import (
            load_documentation_route_focus,
            summarize_active_focus,
        )

        docs_focus_summary = summarize_active_focus(load_documentation_route_focus(state.REPO_ROOT))
    except Exception:
        pass
    _profile_phase(profile_sink, "docs_focus", started)

    active_execution_entry, active_execution_next = _info_active_execution_entry(profile_sink)
    live_work_entry_loop = [
        "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        WORK_LEDGER_SEED_SPEED_COMMAND,
        "./repo-python kernel.py --working-set 5  # phase context only after live-work check",
    ]
    phase_context_loop = [
        "python3 kernel.py --phase [<phase-id-or-token>]  # contextual packet, not sole liveness authority",
        "python3 kernel.py --phase-observe [<phase-id-or-token>]",
        "python3 kernel.py --add-workstream <spec.json> [--live]",
    ]
    compact_bootstrap_rules = [
        "Use active_execution_entry, --preflight, or --pulse to choose current work from Task Ledger WorkItems and Work Ledger claims before phase/subphase context.",
        "Use --pulse when you need one compact view of open loops, stale builder state, doctrine drift, and the best next commands before committing to one subsystem.",
        "Prefer compiled kernel context over raw file walking when the target is not already known.",
        "Use --frontier only for markdown recency questions; it is not the live-work authority.",
        "Use --working-set when the task is a continuation of recent obsidian planning work; it now treats dormant phase state as context.",
    ]
    payload = {
        "repo_root": str(state.REPO_ROOT),
        "entrypoint": state.KERNEL_ENTRYPOINT,
        "entry_docs": {
            "codex": "codex/CODEX.md",
            "agent_quickstart": "codex/doctrine/operations/agent_quickstart.md",
            "kernel_bootstrap": "codex/doctrine/skills/kernel/bootstrap.md",
            "kernel_navigate": "codex/doctrine/skills/kernel/navigate.md",
            "documentation_theory_index": "codex/doctrine/documentation_theory_index.json",
            "agent_bootstrap": "codex/doctrine/agent_bootstrap.json",
            "docs_index": "docs/README.md",
            "documentation_plane_map": "docs/documentation_plane_map.md",
        },
        "bootstrap_policy": {
            "rules": compact_bootstrap_rules,
        },
        "active_execution_entry": active_execution_entry or None,
        "documentation_routes": {
            "docs_route_command": "python3 kernel.py --docs-route <query-or-path>",
            "docs_route_focus": docs_focus_summary or None,
            "bootstrap_sequence": bootstrap_sequence,
            "minimum_read_set_ids": sorted(minimum_read_sets.keys()),
        },
        "planning_surfaces": {
            "live_work_entry_loop": live_work_entry_loop,
            "phase_context_loop": phase_context_loop,
            "plan_execution_loop": live_work_entry_loop + phase_context_loop,
        },
        "observe_surfaces": {
            "agent_loop": [
                "Decide the bounded groups and the downstream synthesis need yourself.",
                "Use python3 kernel.py --phase-observe <phase-id-or-token> when the active seed projection, natively synth_seed.md, or a legacy observe_seed.md already names the group decomposition and you want a deterministic runnable plan.",
                "Use python3 kernel.py --draft-observe ... only if you want bridge help rendering that grouped decomposition into JSON.",
            ],
        },
        "stable_command_groups": {group: list(flags) for group, flags in state.STABLE_COMMANDS.items()},
        "doctrine_control_plane": {
            "runtime_spec": state.rel(state.DOCTRINE_RUNTIME_SPEC),
            "emit_command": "python3 kernel.py --doctrine-runtime",
            "pulse_full_command": "python3 kernel.py --pulse --full",
        },
        "frontier_deferred": {
            "command": f"python3 kernel.py --frontier {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
            "reason": "Compact --info does not scan markdown recency; use --frontier when note recency matters, not as current-work authority.",
        },
    }
    _profile_phase(profile_sink, "payload_compact", started)

    return NavigationResult(
        kind=INFO_NAVIGATION_KIND,
        query={"command": "info"},
        payload=payload,
        live_sources=[
            "kernel.py",
            "codex/CODEX.md",
            "codex/_index.md",
            "codex/doctrine/operations/codex_change_protocol.md",
            "codex/doctrine/skills/kernel/bootstrap.md",
            "codex/doctrine/skills/kernel/_schema.json",
            "codex/standards/std_work_note.json",
            "codex/standards/std_plan_note.json",
        ],
        derived_sources=[state.rel(state.MAP_FILE)] if state.MAP_FILE.exists() else [],
        suggested_next=(
            active_execution_next
            or [
                {"command": "python3 kernel.py --pulse", "reason": "See the current control-plane state and highest-leverage next commands in one view"},
                {"command": "python3 kernel.py --docs-route documentation", "reason": "Resolve the machine-owned minimum read set for documentation-plane orientation"},
                {"command": f"python3 kernel.py --frontier {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}", "reason": "Sync with recent markdown work before deeper exploration"},
            ]
        ),
        warnings=warnings,
        compact_hints={},
    )


def cmd_info() -> int:
    """[ACTION]
    - Teleology: Emit the bootstrap manifest that agents should read before widening search.
    - Mechanism: Gather bootstrap config, minimum read sets, docs-route focus, and core entry-doc pointers into one navigation payload.
    - Guarantee: Returns 0 after emitting the bootstrap navigation result.
    - Fails: None for normal degraded bootstrap assembly; missing optional artifacts become warnings.
    - When-needed: Open when a fresh kernel session needs the bounded bootstrap packet before any deeper navigation.
    - Escalates-to: system/lib/kernel_navigation.py; kernel.py
    - Navigation-group: kernel_lib
    """
    if not navigation_output_full(INFO_NAVIGATION_KIND):
        return emit_navigation(_info_compact_result())

    warnings: list[str] = []
    if not state.MAP_FILE.exists():
        warnings.append("derived map missing; run `python3 kernel.py --build` for optional enrichment")
    if not state.KERNEL_SKILLS_SCHEMA.exists():
        warnings.append("kernel skills schema missing")
    if not (state.REPO_ROOT / "codex" / "doctrine" / "skills" / "kernel" / "navigate.md").exists():
        warnings.append("navigate skill doc missing")

    bootstrap_cfg: dict[str, Any] = {}
    minimum_read_sets: dict[str, Any] = {}
    bootstrap_sequence: list[dict[str, Any]] = []
    situation_routes: list[dict[str, Any]] = []
    runtime_control_plane: dict[str, Any] = {}
    docs_focus_summary: dict[str, Any] = {}
    try:
        from system.lib.agent_bootstrap_projection import (
            load_agent_bootstrap_config,
            normalize_bootstrap_sequence,
            normalize_minimum_read_sets,
            normalize_runtime_control_plane,
            normalize_situation_routes,
        )

        bootstrap_cfg = load_agent_bootstrap_config(state.REPO_ROOT)
        minimum_read_sets = normalize_minimum_read_sets(bootstrap_cfg.get("minimum_read_sets"))
        bootstrap_sequence = normalize_bootstrap_sequence(bootstrap_cfg.get("bootstrap_sequence"))
        situation_routes = normalize_situation_routes(
            bootstrap_cfg.get("situation_routes"),
            minimum_read_sets=minimum_read_sets or None,
        )
        runtime_control_plane = normalize_runtime_control_plane(bootstrap_cfg.get("runtime_control_plane"))
    except Exception:
        pass
    try:
        from system.control.documentation_route_focus import (
            load_documentation_route_focus,
            summarize_active_focus,
        )

        docs_focus_summary = summarize_active_focus(load_documentation_route_focus(state.REPO_ROOT))
    except Exception:
        pass

    active_execution_entry, active_execution_next = _info_active_execution_entry()
    live_work_entry_loop = [
        "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        WORK_LEDGER_SEED_SPEED_COMMAND,
        f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}  # phase context only after live-work check",
    ]
    phase_context_loop = [
        "python3 kernel.py --phase [<phase-id-or-token>]  # contextual packet, not sole liveness authority",
        "python3 kernel.py --phase-observe [<phase-id-or-token>]",
        "python3 kernel.py --add-workstream <spec.json> [--live]",
    ]

    payload = {
        "repo_root": str(state.REPO_ROOT),
        "roots": {
            "substrate": "codex/substrate",
            "doctrine": "codex/doctrine",
            "doctrine_runtime_spec": "codex/doctrine/doctrine_runtime.json",
            "derived": "codex/derived",
            "standards": "codex/standards",
        },
        "entrypoint": state.KERNEL_ENTRYPOINT,
        "entry_docs": {
            "codex": "codex/CODEX.md",
            "root_index": "codex/_index.md",
            "system_map": "codex/doctrine/system_map.json",
            "system_view": "obsidian/<phase>/system_view.json",
            "documentation_theory_index": "codex/doctrine/documentation_theory_index.json",
            "agent_bootstrap": "codex/doctrine/agent_bootstrap.json",
            "docs_index": "docs/README.md",
            "agent_instruction_router": "docs/agent_instruction_router.md",
            "documentation_plane_map": "docs/documentation_plane_map.md",
            "orchestration_state_doc": "docs/orchestration_state.md",
            "documentation_route_focus": "tools/meta/control/documentation_route_focus.json",
            "doctrine_index": "codex/doctrine/doctrine_index.md",
            "doctrine_runtime": "codex/doctrine/doctrine_runtime.json",
            "standards_registry": STANDARDS_REGISTRY_PATH,
            "agent_quickstart": "codex/doctrine/operations/agent_quickstart.md",
            "change_protocol": "codex/doctrine/operations/codex_change_protocol.md",
            "runtime_change_protocol": "codex/doctrine/operations/runtime_change_protocol.md",
            "kernel_principles": "codex/doctrine/references/kernel_principles.md",
            "kernel_bootstrap": "codex/doctrine/skills/kernel/bootstrap.md",
            "kernel_navigate": "codex/doctrine/skills/kernel/navigate.md",
            "kernel_localize": "codex/doctrine/skills/kernel/localize.md",
            "planning_framework": "codex/doctrine/skills/kernel/planning_framework.md",
            "kernel_plan": "codex/doctrine/skills/kernel/plan.md",
            "observe_patterns": "codex/doctrine/skills/kernel/observe_patterns.md",
            "observe_authoring": "codex/doctrine/skills/kernel/observe_plan_authoring.md",
            "kernel_implement": "codex/doctrine/skills/kernel/implement.md",
            "kernel_apply": "codex/doctrine/skills/kernel/apply.md",
            "kernel_remediate": "codex/doctrine/skills/kernel/remediate.md",
        },
        "bootstrap_policy": {
            "default_mode": "query_first",
            "current_step": "info_loaded",
            "read_budget": "Read root docs for routing, sync the recent markdown frontier, then switch to kernel navigation before deep file reads.",
            "rules": [
                "Use active_execution_entry, --preflight, or --pulse to choose current work from Task Ledger WorkItems and Work Ledger claims before phase/subphase context.",
                "Use --pulse when you need one compact view of open loops, stale builder state, doctrine drift, and the best next commands before committing to one subsystem.",
                "Prefer compiled kernel context over raw file walking when the target is not already known.",
                "Use --frontier only for markdown recency questions; it is not the live-work authority.",
                "Use --working-set when the task is a continuation of recent obsidian planning work; it now treats dormant phase state as context.",
                "Use --bootstrap-task <note-or-token> when the target note is already known and you want the bounded task-entry packet: frontmatter, read order, entrypoints, and latest artifacts.",
                "Use --obsidian-family <note-or-token> when the intended note family is already known and you want explicit family recovery instead of recency-based anchor selection.",
                "Use --orient-task plus --lens self:* and --compile to localize vague file work through the self-model before repo-wide grep or raw tree walks.",
                "Use --set-focus <note-or-token> to preview or write folder-scoped focus metadata when the continuity packet needs an explicit active note, later-use badge, or reopening handoff.",
                "Use --execution-map [artifact-or-latest] when planner memory exists and you need repeat-avoidance plus declared resume entrypoints before reopening the search space.",
                "Use --map [boundary-or-latest] when living boundary memory already exists and you need section previews, focus-path freshness, and companion-packet context before launching more observe work.",
                "Use python3 kernel.py --system-view [PHASE_TOKEN] to browse the active phase's generated system_view.json and any active focus directive without mutating controller artifacts.",
                "Use doctrine for meaning and policy only after atlas/orient/context has narrowed the question.",
                "When you land in codex/standards without a known family, open codex/standards/standards_registry.json or run --standards before reading individual std_*.json files.",
                "Open codex/doctrine/system_map.json (or run python3 kernel.py --system-map) for the holographic index of concepts, mechanisms, kernel clusters, and factory lanes before walking doctrine piecemeal.",
                "For documentation-plane and artifact-kind routing (shared minimum_read_sets with codex/doctrine/agent_bootstrap.json), run python3 kernel.py --docs-route <query-or-path>; vague documentation tasks may also use python3 kernel.py --orient-task <token> so documentation-like queries resolve through the same graph.",
                "Documentation route priorities can be shifted by control-plane focus presets (tools/meta/control/documentation_route_focus.json): python3 kernel.py --list-docs-route-focus and python3 kernel.py --set-docs-route-focus <preset_id> (also run_control_room.py --list-docs-focus / --set-docs-focus).",
                "For the JSON doctrine control plane (concepts, mechanisms, routing, loops), run python3 kernel.py --doctrine-runtime before opening many con_*/mech_* files.",
                "For phased implementation work, identify the active note on the frontier, then use the planning and implement skills to turn it into governed batch work.",
                "Treat derived artifacts as optional machine context, not as sole source truth.",
                "Use paths diagnostics only when debugging kernel surfaces or missing files.",
                "Never use raw --tree or grep for system understanding when a semantic lens is available. Use --lens doc:<id>, --lens mission:<name>, --lens node:<id>, --lens run:<id>, or --lens self:global|self:boundary:<id>|self:path:<token> to get a focused boundary or localization surface first.",
                "If the active task exposes a small kernel continuity or observe-UX defect that is directly blocking the work, fix it in the same pass rather than treating kernel improvement as separate cleanup.",
            ],
        },
        "active_execution_entry": active_execution_entry or None,
        "documentation_routes": {
            "docs_route_command": "python3 kernel.py --docs-route <query-or-path>",
            "system_view_command": "python3 kernel.py --system-view [PHASE_TOKEN]",
            "docs_route_focus": docs_focus_summary or None,
            "theory_index": "codex/doctrine/documentation_theory_index.json",
            "agent_bootstrap": "codex/doctrine/agent_bootstrap.json",
            "documentation_plane_map": "docs/documentation_plane_map.md",
            "bootstrap_sequence": bootstrap_sequence,
            "situation_routes": situation_routes,
            "minimum_read_set_ids": sorted(minimum_read_sets.keys()),
            "runtime_control_plane": runtime_control_plane or None,
        },
        "source_truth_policy": [
            {
                "layer": "substrate",
                "path": "codex/substrate",
                "role": "runtime source truth",
                "use_for": ["node definitions", "contracts", "configs", "refs", "dossiers", "plan manifests"],
                "avoid_for": ["narrative interpretation", "workflow policy"],
            },
            {
                "layer": "doctrine",
                "path": "codex/doctrine",
                "role": "authored meaning and operating guidance",
                "use_for": ["mission theory", "component intent", "runbooks", "skills"],
                "avoid_for": ["assuming runtime state", "defining artifact inventory"],
            },
            {
                "layer": "derived",
                "path": "codex/derived",
                "role": "generated machine navigation",
                "use_for": ["topology summaries", "compiled bundles", "drift signals"],
                "avoid_for": ["manual edits", "source truth overrides"],
            },
            {
                "layer": "state",
                "path": "state/runs",
                "role": "runtime evidence",
                "use_for": ["run investigation", "artifact inspection", "grade review"],
                "avoid_for": ["architecture claims", "authoring canon"],
            },
            {
                "layer": "runtime_workspace",
                "path": "tools/meta/apply",
                "role": "mutable observe/apply workspace",
                "use_for": ["active observe plans", "observe dumps/history", "apply results", "runtime evidence"],
                "avoid_for": ["authored doctrine", "machine standards", "generated navigation source"],
            },
            {
                "layer": "planning_notes",
                "path": "obsidian",
                "role": "active build packets and operator planning notes",
                "use_for": ["implementation note context", "execution narrative", "frontier sync", "observe-session mirrored artifacts"],
                "avoid_for": ["runtime truth", "machine batch state"],
            },
        ],
        "temporal_contract_model": {
            "feeds": {
                "time_authority": "T-n snapshot",
                "role": "deterministic sensing layer",
                "artifacts": "feed artifacts define the baseline state Lab is allowed to reason from",
            },
            "lab": {
                "time_authority": "T-n only",
                "question": "What should happen by T given the T-n state?",
                "outputs": {
                    "cp1": "lab_decide emits the locked CP1 thesis checkpoint",
                    "cp2": "lab_director emits forward CP2 directional consequences",
                },
                "note": "Feed replay records snapshot provenance only; it does not imply a realized-truth pairing.",
            },
            "oracle": {
                "time_authority": "realized T plus T-n lineage",
                "question": "What would the correct structured call have looked like given realized evidence?",
                "outputs": {
                    "cp2": "oracle_cp2_emitter emits realized CP2 reconstruction",
                },
                "note": "Oracle shares CP2 schema for comparability, not because it is another predictor.",
            },
            "evolve": {
                "status": "not_canonicalized",
                "rule": "Doctrine and dossier changes remain explicit authoring steps after review.",
            },
        },
        "planning_surfaces": {
            "manifest_dir": "codex/substrate/plan",
            "plan_note_standard": "codex/standards/std_plan_note.json",
            "work_note_standard": "codex/standards/std_work_note.json",
            "execution_map_standard": "codex/standards/std_execution_map.json",
            "living_map_standard": "codex/standards/std_living_map.json",
            "manifest_rule": "Use machine-readable plan manifests as companions to the active implementation note, not replacements for it.",
            "anchor_override": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT} --anchor <note-or-token>",
            "task_bootstrap": "python3 kernel.py --bootstrap-task <note-or-token>",
            "task_orient": "python3 kernel.py --orient-task <task-or-note>",
            "phase_lookup": "python3 kernel.py --phase [<phase-id-or-token>]",
            "phase_observe": "python3 kernel.py --phase-observe [<phase-id-or-token>] [--write-plan <file>]",
            "workstream_bootstrap": "python3 kernel.py --add-workstream <spec.json> [--live]",
            "explicit_family_lookup": "python3 kernel.py --obsidian-family <note-or-token>",
            "focus_update": "python3 kernel.py --set-focus <note-or-token> [--focus-status <status>] [--focus-label <text>] [--focus-handoff <text>] [--live]",
            "execution_map_lookup": "python3 kernel.py --execution-map [artifact-or-latest]",
            "living_map_lookup": "python3 kernel.py --map [boundary-or-latest]",
            "live_work_entry_loop": live_work_entry_loop,
            "phase_context_loop": phase_context_loop,
            "locate_example": "python3 kernel.py --locate 06_1_manifest",
            "compile_batch": "python3 kernel.py --compile-batch [current|<id>]",
            "compile_files": "python3 kernel.py --compile <path-or-token> [<path-or-token> ...]",
            "focus_rule": "Keep focus state in frontmatter, not filenames. Preview with --set-focus first; add --live only after the write plan matches intent.",
            "plan_execution_loop": [
                *live_work_entry_loop,
                *phase_context_loop,
                "python3 kernel.py --plan-phase",
                "python3 kernel.py --plan-batch <id>",
                "python3 kernel.py --compile-batch <id>",
                "python3 kernel.py --impact <file>",
                "python3 kernel.py --verify <id>",
                "python3 kernel.py --plan-sync <plan_id>",
            ],
        },
        "observe_surfaces": {
            "agent_loop": [
                "Decide the bounded groups and the downstream synthesis need yourself.",
                "Use python3 kernel.py --phase-observe <phase-id-or-token> when the active seed projection, natively synth_seed.md, or a legacy observe_seed.md already names the group decomposition and you want a deterministic runnable plan.",
                "Use python3 kernel.py --draft-observe ... only if you want bridge help rendering that grouped decomposition into JSON.",
                "Launch through python3 kernel.py --launch-observe --plan <file> --bridge --provider <x> --bridge-workers auto --launch-profile experimental --detach --no-sticky-dump-dir.",
                "Detached launch now waits for a matching launch receipt; if receipt confirmation fails, treat it as a failed launch rather than investigating bridge state mid-turn.",
                "After dispatch, stop the turn and resume from the stored artifact instead of narrating bridge state.",
            ],
            "phase_seed_plan": "python3 kernel.py --phase-observe <phase-id-or-token> [--write-plan <file>]  # deterministic phase-seed -> observe_plan compiler",
            "draft_plan": "python3 kernel.py --draft-observe \"<problem>\" --questions \"<q1>\" ... --source-paths <md...> --boundary <map-or-note> --write-plan <file>  # optional scaffolder after you already decided the groups",
            "launch": "python3 kernel.py --launch-observe --plan <file> --bridge --provider gemini --bridge-workers auto --launch-profile experimental --detach --no-sticky-dump-dir",
            "launch_and_yield_rule": "Launch And Yield: once bridge work is dispatched, stop the turn and recover from the stored observe/session artifact on the next cue.",
            "compat_session_surfaces": {
                "draft_session": "python3 kernel.py --draft-session \"<problem>\" --source-paths <md...> --write-plan <file>",
                "read_session": "python3 kernel.py --read-session latest",
                "list_sessions": "python3 kernel.py --list-sessions",
            },
            "post_run_synthesis": "python3 kernel.py --synthesize latest --provider chatgpt",
            "digest_refresh": "python3 kernel.py --digest-observe latest",
            "stale_report": "python3 kernel.py --stale",
            "doc_gap_report": "python3 kernel.py --doc-gaps",
            "friction_log": "python3 kernel.py --friction <text>",
            "pattern_guide": state.rel(state.OBSERVE_PATTERN_GUIDE),
            "latest_suggestion": state.rel(state.OBSERVE_PLAN_SUGGESTION),
            "runtime_history": state.rel(state.OBSERVE_HISTORY),
            "runtime_history_entries_root": state.rel(state.OBSERVE_HISTORY_ENTRIES_DIR),
            "session_manifests_root": state.rel(state.OBSERVE_SESSION_ROOT),
            "resume_commands": [
                "python3 kernel.py --list-observes",
                "python3 kernel.py --read-observe latest",
                "python3 kernel.py --read-observe latest --open",
                "python3 kernel.py --digest-observe latest",
                "python3 kernel.py --list-sessions",
                "python3 kernel.py --read-session latest",
            ],
            "continuation_rule": "Use the stored continuation contract in the session manifest or observe history entry instead of guessing which response artifact to read next. Prefer digest -> typed result note -> synthesis -> raw drilldown.",
        },
        "available_skills": _skill_payload(),
        "stable_command_groups": {group: list(flags) for group, flags in state.STABLE_COMMANDS.items()},
        "optical_capabilities": {
            "principle": "Resolve the semantic boundary first, then expand only that boundary.",
            "primary_command": "python3 kernel.py --lens <target>",
            "targets": [
                {
                    "target": "doc:<doc_id>",
                    "shows": "Focused tree, doctrine-linked files, and hologram summaries for the document boundary.",
                },
                {
                    "target": "mission:<name>",
                    "shows": "Mission node files, upstream substrate, tool modules, and governing doctrine files.",
                },
                {
                    "target": "node:<node_id>",
                    "shows": "One node's substrate boundary: node JSON, contracts, related doctrine, and tool module if present.",
                },
                {
                    "target": "run:<run_id>",
                    "shows": "Run-state files plus the code behind failed or suspicious nodes.",
                },
                {
                    "target": "self:global",
                    "shows": "Canonical self-model boundary cards, gap signals, and the compressed localization index.",
                },
                {
                    "target": "self:boundary:<id>",
                    "shows": "Matched anchors, focus paths, and confidence signals inside one self-model boundary.",
                },
                {
                    "target": "self:path:<token>",
                    "shows": "Ranked localized anchors for one token, stem, or symbol-bearing path hint.",
                },
            ],
            "deepening_command": "python3 kernel.py --hologram <file>",
            "localization_confirmation_command": "python3 kernel.py --compile <path-or-token>",
        },
        "recommended_sequence": [
            {
                "step": 1,
                "command": f"python3 kernel.py --frontier {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
                "purpose": "Sync the current frontier of work from the freshest markdown notes",
            },
            {
                "step": 2,
                "command": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
                "purpose": "If this is a continuation of recent obsidian work, recover the active note family, manifest, and observe artifacts",
            },
            {
                "step": 3,
                "command": "python3 kernel.py --orient-task <task-or-note>",
                "purpose": "Resolve a task description, note token, plan id, file token, mission, or doctrine token into the tightest orientation packet",
            },
            {
                "step": 4,
                "command": "python3 kernel.py --bootstrap-task <note-or-token>",
                "purpose": "If the target work note is already known, recover the bounded task-entry packet before widening search",
            },
            {
                "step": 5,
                "command": "python3 kernel.py --obsidian-family <note-or-token>",
                "purpose": "If the intended obsidian family is already known, recover it directly without relying on recent-note auto selection",
            },
            {
                "step": 6,
                "command": "python3 kernel.py --set-focus <note-or-token>",
                "purpose": "If the family packet needs an explicit active note or a reusable later-use badge/handoff, preview the frontmatter update before writing it with --live",
            },
            {
                "step": 7,
                "command": "python3 kernel.py --execution-map latest",
                "purpose": "If planner memory exists, reopen the latest execution map before repeating exploration",
            },
            {
                "step": 8,
                "command": "python3 kernel.py --map latest",
                "purpose": "If boundary memory exists, reopen the latest living map before launching new observe work against the same surface",
            },
            {
                "step": 9,
                "command": "python3 kernel.py --atlas",
                "purpose": "Get the system-wide topology and mission layout",
            },
            {
                "step": 10,
                "command": "python3 kernel.py --locate <token>",
                "purpose": "Resolve a node, doctrine doc, contract, config, ref, or plan manifest deterministically",
            },
            {
                "step": 11,
                "command": "python3 kernel.py --orient <mission>",
                "purpose": "Get a mission-level briefing with doctrine and wave order",
            },
            {
                "step": 12,
                "command": "python3 kernel.py --context <node_id>",
                "purpose": "Compile node-level summary before deep reads or edits; use --context-view for metadata, topology, standards, doctrine, or full expansion",
            },
            {
                "step": 13,
                "command": "python3 kernel.py --compile-batch [current|<id>]",
                "purpose": "Compile the current implementation slice into file cards, schema keys, exports, and cross-file links instead of grepping raw files",
            },
            {
                "step": 14,
                "command": "python3 kernel.py --lens <doc:...|mission:...|node:...|run:...|self:global|self:boundary:<id>|self:path:<token>>",
                "purpose": "Expand only the resolved semantic boundary or self-model localization surface when you need a focused tree or ranked file set",
            },
            {
                "step": 15,
                "command": "python3 kernel.py --paths",
                "purpose": "Use path diagnostics only when you need to debug kernel surfaces",
            },
        ],
        "question_router": [
            {
                "question": "What has the operator been working on most recently?",
                "command": f"python3 kernel.py --frontier {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
                "follow_with": "Open the freshest markdown note directly if the title or trailing line matches the task.",
                "stop_when": "You know the top recent notes, their sizes, keywords, and first/last content lines.",
            },
            {
                "question": "What note family, manifest, and observe artifacts should I reload before resuming recent work?",
                "command": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}",
                "follow_with": "Use --plan-phase and --read-observe on the specific family surfaced by the continuity packet; add --anchor <note-or-token> when recent markdown noise would otherwise pick the wrong family.",
                "stop_when": "You know the anchor note, sibling obsidian notes, current manifest batch, and stored observe continuation surface.",
            },
            {
                "question": "What exact note, read order, and latest artifacts should I use to re-enter a known task?",
                "command": "python3 kernel.py --bootstrap-task <note-or-token>",
                "follow_with": "Read the preferred entrypoints and latest relevant artifacts before widening search or launching new observe work.",
                "stop_when": "You know the anchor frontmatter, dependency order, working set, preferred entrypoints, and the latest continuation artifacts.",
            },
            {
                "question": "What frontmatter, sections, and structured blocks does this markdown note actually contain?",
                "command": "python3 kernel.py --extract-note-structure <note-or-token> --extract-note-mode full",
                "follow_with": "Switch to --extract-note-mode sections or frontmatter when you want a narrower payload, or use --extract-note when you need reference/path projection too.",
                "stop_when": "You know the note's frontmatter keys, section bodies, structured blocks, and extracted tags without manually scanning markdown.",
            },
            {
                "question": "What was already explored, what was duplicated, and what should I reopen before searching again?",
                "command": "python3 kernel.py --execution-map latest",
                "follow_with": "Use the preferred_entrypoints and latest_artifacts fields before reopening duplicate surfaces or launching new work.",
                "stop_when": "You know the declared working set, duplicate surfaces, latest artifacts, and next actions from the planner-memory artifact.",
            },
            {
                "question": "What does the current boundary-memory note already claim, and is it stale against the focus paths?",
                "command": "python3 kernel.py --map [boundary-or-latest]",
                "follow_with": "Read the staleness and companion-packet checks before launching new observe work or planning writeback.",
                "stop_when": "You know the map sections, declared focus paths, freshness heuristics, and companion note relationships.",
            },
            {
                "question": "What exact obsidian note family should I reload when I already know the anchor note or token?",
                "command": "python3 kernel.py --obsidian-family <note-or-token>",
                "follow_with": "Then use --plan-phase, --plan-batch, or --read-observe against the explicit family packet without relying on recent-note auto selection.",
                "stop_when": "You know the exact family around the requested note, plus the related manifest and observe continuation surfaces.",
            },
            {
                "question": "What do I read first for documentation, runtime control, or a repo path whose owning authority is unclear?",
                "command": "python3 kernel.py --docs-route <query-or-path>",
                "follow_with": "Use the returned minimum read set and authority surfaces before opening more prose; documentation-like --orient-task queries delegate here too.",
                "stop_when": "You have the governing authority layer, the minimum sufficient read set, the local artifacts, and the next commands.",
            },
            {
                "question": "How do I mark one note active, or preserve a useful later-use badge/handoff, without renaming files in the active folder?",
                "command": "python3 kernel.py --set-focus <note-or-token>",
                "follow_with": "Add --focus-status completed, --focus-label <TEXT>, or --focus-handoff <TEXT> as needed; rerun with --live only after the previewed writes match intent.",
                "stop_when": "You know the exact frontmatter writes the kernel will make, the target family scope, and the post-update note family you want to reload.",
            },
            {
                "question": "What is this system?",
                "command": "python3 kernel.py --atlas",
                "follow_with": "Read codex/CODEX.md only if you need layer semantics or canonical layout.",
                "stop_when": "You can name the missions, waves, and main entrypoints.",
            },
            {
                "question": "What is this mission?",
                "command": "python3 kernel.py --orient <mission>",
                "follow_with": "Read the mission doctrine header only if policy or theory is still unclear.",
                "stop_when": "You know the mission nodes, wave order, and governing doctrine doc.",
            },
            {
                "question": "Which files matter for this situation when the exact path is still unclear?",
                "command": "python3 kernel.py --orient-task <task-or-note>",
                "follow_with": "If the route still needs file narrowing, use python3 kernel.py --lens self:global to choose a boundary, then --lens self:boundary:<id> or --lens self:path:<token>, and confirm the top matches with --compile before raw grep.",
                "stop_when": "You have a stable 5-12 file working set or a single compiled file candidate.",
            },
            {
                "question": "What is this node or token?",
                "command": "python3 kernel.py --locate <token>",
                "follow_with": "Then run python3 kernel.py --context <node_id> for the matched node, or add --context-view standards|metadata|topology when you already know the slice you need.",
                "stop_when": "You have a canonical entity type and path.",
            },
            {
                "question": "What touches this node?",
                "command": "python3 kernel.py --context <node_id>",
                "follow_with": "Use python3 kernel.py --context <node_id> --context-view topology for the topology slice, or --trace when the full chain matters.",
                "stop_when": "You know the direct upstream/downstream and the execution touchpoints.",
            },
            {
                "question": "What standards and contracts govern this node?",
                "command": "python3 kernel.py --context <node_id> --context-view standards",
                "follow_with": "Use python3 kernel.py --standards for the full standards catalog once you know the node-specific standard family.",
                "stop_when": "You know the node schema standard, doctrine schema, and contract paths that govern this node.",
            },
            {
                "question": "What metadata or execution policy does this node carry?",
                "command": "python3 kernel.py --context <node_id> --context-view metadata",
                "follow_with": "Use python3 kernel.py --context <node_id> --context-view full only if the summary metadata still leaves ambiguity.",
                "stop_when": "You know platform, routing class, boundary, config surface, and execution policy without reading raw node JSON.",
            },
            {
                "question": "What doctrine governs this?",
                "command": "python3 kernel.py --doctrine <doc_id>",
                "follow_with": "Read the full doctrine file only if the structured header is insufficient.",
                "stop_when": "You have the purpose, scope, claims, and interfaces for the governing doc.",
            },
            {
                "question": "What is the doctrine control plane, runtime loops, and scaling policy for this repo?",
                "command": "python3 kernel.py --doctrine-runtime",
                "follow_with": "Then open codex/doctrine/doctrine_registry.json and doctrine_surface.json (compressed_briefing, raw_seed_assimilation).",
                "stop_when": "You know canonical paths, mech_016 launch line, phase pipeline drivers, parallelism policy, and gate types.",
            },
            {
                "question": "What are the kernel design principles or the one-minute protocol?",
                "command": "python3 kernel.py --doctrine kernel_principles",
                "follow_with": "Read codex/CODEX.md only if you need the full root definition after the doctrine summary.",
                "stop_when": "You know the kernel's startup, planning, apply, and context-slicing standards.",
            },
            {
                "question": "What happened in this run?",
                "command": "python3 kernel.py --run-context <run_id>",
                "note": "Accepts suffix (da71e9), 'latest', or 'latest:<mission>' (e.g. latest:lab).",
                "follow_with": "Use python3 kernel.py --run-artifact <run_id> <node_id> to read specific artifacts.",
                "stop_when": "You know the grade, artifact inventory, and relevant node outcomes.",
            },
            {
                "question": "What did Lab predict?",
                "command": "python3 kernel.py --run-predictions <run_id>",
                "follow_with": "Use --run-evidence <run_id> to see the evidence Lab used.",
                "stop_when": "You have the prediction targets, directions, and prices.",
            },
            {
                "question": "What evidence did Lab use?",
                "command": "python3 kernel.py --run-evidence <run_id>",
                "follow_with": "Use --run-predictions <run_id> to see what Lab concluded from this evidence.",
                "stop_when": "You have evidence entries grouped by lane with ledger IDs.",
            },
            {
                "question": "Where did this run's data actually come from?",
                "command": "python3 kernel.py --run-lineage <run_id>",
                "follow_with": "Use --run-timeline <subject> <truth> before comparing runs.",
                "stop_when": "You know the root run, lineage chain, and market session.",
            },
            {
                "question": "What does a Python file in the system actually do?",
                "command": "python3 kernel.py --hologram <file>",
                "note": "The builder generates a Python AST map in codex/hologram/system/. Use --hologram without args to list all files, then --hologram <file> for full tags and function list. Do NOT use raw jq on codex/hologram/system/ directly.",
                "follow_with": "Use --quick 'question' --files <path> if deeper code evidence is needed.",
                "stop_when": "You have the PURPOSE, FLOW, INTERFACE, and function/class surface for the file.",
            },
            {
                "question": "How do I author or refine an observe plan?",
                "command": "python3 kernel.py --standards",
                "follow_with": "Then run python3 kernel.py --prompt '4A' or '6A', read codex/doctrine/skills/kernel/observe_plan_authoring.md, decide the group split yourself, and use --draft-observe only if you want bridge help rendering that grouped plan into JSON. Launch through --launch-observe and let the kernel pick the internal runtime.",
                "stop_when": "You know the relevant standards root, the canonical observe standards, prompt variants, and active runtime plan path.",
            },
            {
                "question": "What is the canonical packet for this phase family, even before the plan is locked?",
                "command": "python3 kernel.py --phase <phase-id-or-token>",
                "follow_with": "Use --bootstrap-task on the canonical entry note for bounded task recovery, or --plan-phase once you need strict batch execution state.",
                "stop_when": "You know the canonical phase entry, the raw/reference/observe/plan surfaces, and whether a manifest-backed plan exists.",
            },
            {
                "question": "How do I execute the current phased implementation plan?",
                "command": "python3 kernel.py --plan-phase",
                "follow_with": "Then run python3 kernel.py --plan-batch <id>, --impact <file>, and --verify <id> before editing outside the current batch.",
                "stop_when": "You know the active plan note, matching manifest, current batch, and batch acceptance gate.",
            },
            {
                "question": "What batch of the active implementation plan am I in?",
                "command": "python3 kernel.py --plan-phase",
                "follow_with": "Use python3 kernel.py --plan-batch <id> for the exact file slice.",
                "stop_when": "You know the current batch, dependencies, and next acceptance gate.",
            },
            {
                "question": "What breaks if I change this file?",
                "command": "python3 kernel.py --impact <file>",
                "follow_with": "Use python3 kernel.py --plan-batch <id> for the owning batch or python3 kernel.py --context <node_id> for touched nodes.",
                "stop_when": "You know the owning batch, doctrine claims, node touchpoints, and declared acceptance commands.",
            },
            {
                "question": "Where is the machine-readable build plan state?",
                "command": "python3 kernel.py --locate 06_1_manifest",
                "follow_with": "Open the resolved JSON manifest under codex/substrate/plan/ and compare it against the current frontier note.",
                "stop_when": "You have the canonical plan-manifest path and know which implementation note it complements.",
            },
            {
                "question": "Do the active plan note and manifest still agree?",
                "command": "python3 kernel.py --plan-sync <plan_id>",
                "follow_with": "If drift exists, reconcile the note, manifest, or both before continuing implementation.",
                "stop_when": "You have a pass/fail answer on manifest linkage, batch parity, and reconciliation metadata.",
            },
            {
                "question": "How accurate were Lab's predictions?",
                "command": "python3 kernel.py --run-grade-predictions <subject> <truth>",
                "note": "Do NOT write manual jq/python3 scripts. Verify temporal ordering with --run-timeline first.",
                "follow_with": "Use --run-compare <subject> <truth> for the full price delta breakdown.",
                "stop_when": "You have direction hits, price errors, and overall accuracy.",
            },
            {
                "question": "What moved between two runs?",
                "command": "python3 kernel.py --run-compare <subject> <truth>",
                "note": "Check --run-timeline and --run-lineage first to confirm the truth run is realized truth, not a replay source.",
                "follow_with": "Use --run-grade-predictions if Lab predictions were the original question.",
                "stop_when": "You have price deltas sorted by magnitude with prediction targets highlighted.",
            },
            {
                "question": "I am reading a doctrine doc and need to see the actual code it governs.",
                "command": "python3 kernel.py --lens doc:<doc_id>",
                "note": "The --lens command reads the doc's focus_paths and returns PURPOSE, FLOW, classes, and function surface for every governed file. No raw grep or cat needed.",
                "follow_with": "Use --hologram <file> for full AST detail on a specific file.",
                "stop_when": "You have the holographic summary of every Python file in the doc's focus_paths.",
            },
            {
                "question": "I need a focused code view of a mission, node, or failed run without reading the whole repo.",
                "command": "python3 kernel.py --lens mission:<name>  OR  python3 kernel.py --lens node:<node_id>  OR  python3 kernel.py --lens run:<run_id>",
                "note": "mission: resolves the mission boundary. node: resolves one node's contracts/docs/tool module. run: resolves run-state files plus the code behind interesting nodes.",
                "follow_with": "Use --context <node_id> or --hologram <file> to go deeper on a specific piece.",
                "stop_when": "You can see holographic summaries for every relevant Python file in the boundary.",
            },
            {
                "question": "Why is the kernel failing to find something?",
                "command": "python3 kernel.py --paths",
                "follow_with": "Return to --info or --atlas after diagnostics.",
                "stop_when": "You have confirmed missing or stale kernel-managed surfaces.",
            },
            {
                "question": "How do I change codex markdown or substrate JSON safely?",
                "command": "read codex/doctrine/operations/codex_change_protocol.md",
                "follow_with": "Then run python3 kernel.py --build after the authored change set is complete.",
                "stop_when": "You know which doctrine, router, and generated surfaces must move together.",
            },
            {
                "question": "How do runtime/path changes propagate safely?",
                "command": "read codex/doctrine/operations/runtime_change_protocol.md",
                "follow_with": "Then run python3 kernel.py --paths, --standards, and --build after the change.",
                "stop_when": "You know which runtime callers, diagnostics surfaces, and generated outputs must move together.",
            },
        ],
        "change_router": [
            {
                "change_type": "doctrine_markdown",
                "source_paths": ["codex/doctrine/**/*.md"],
                "must_update": ["frontmatter", "structured block", "affected router docs"],
                "verify_with": ["python3 kernel.py --build"],
            },
            {
                "change_type": "node_json",
                "source_paths": ["codex/substrate/nodes/**/*.json"],
                "must_update": ["nearest mission/component doctrine", "contract doctrine when checkpoint semantics change"],
                "verify_with": ["python3 kernel.py --scratchpad", "python3 kernel.py --build"],
            },
            {
                "change_type": "contract_json_or_md",
                "source_paths": ["codex/substrate/contracts/*"],
                "must_update": [
                    "codex/doctrine/flows/contracts_and_grading.md",
                    "lab/oracle mission doctrine when checkpoint meaning changes",
                    "validators or audit code if enforcement changed",
                ],
                "verify_with": ["python3 kernel.py --scratchpad", "python3 kernel.py --build", "targeted tests"],
            },
            {
                "change_type": "plan_manifest",
                "source_paths": ["codex/substrate/plan/*.json"],
                "must_update": ["matching planning docs when batch meaning changed", "kernel routing docs if manifest naming or discoverability changed"],
                "verify_with": ["python3 kernel.py --locate 06_1_manifest", "python3 kernel.py --paths"],
            },
            {
                "change_type": "root_router_or_bootstrap",
                "source_paths": ["codex/CODEX.md", "codex/_index.md", "codex/doctrine/doctrine_index.md"],
                "must_update": ["agent_quickstart", "kernel bootstrap docs", "kernel.py --info payload if routing changed"],
                "verify_with": ["python3 kernel.py --info", "python3 kernel.py --build"],
            },
            {
                "change_type": "runtime_path_contract",
                "source_paths": [
                    "kernel.py",
                    "system/lib/observe_assets.py",
                    "system/lib/tree_snapshot.py",
                    "system/server/meta_service.py",
                    "tools/meta/builder.py",
                    "tools/meta/apply/observe_session.py",
                ],
                "must_update": ["shared resolver", "kernel diagnostics", "generated observe outputs", "runtime change doctrine if contract meaning changed"],
                "verify_with": ["python3 kernel.py --paths", "python3 kernel.py --standards", "python3 kernel.py --build", "targeted tests"],
            },
        ],
        "stop_conditions": [
            "Do not read whole directories when a single --orient, --context, or --run-context payload already answers the question.",
            "Do not read full doctrine narratives until the structured header or mission briefing proves they matter.",
            "Do not jump to raw node JSON when --context-view metadata|topology|standards already answers the question.",
            "Do not use raw --tree when a semantic --lens target is already known.",
            "Do not start observe-mode until the target file or node is known.",
        ],
        "anti_patterns": [
            "Starting with raw cat, grep, or tree walks for system understanding.",
            "Expanding node context to the full payload before deciding whether you actually need metadata, topology, doctrine, standards, or contracts.",
            "Using raw --tree instead of --lens after the semantic boundary is already known.",
            "Ignoring the recent markdown frontier when the active task may have shifted through notes or voice captures.",
            "Treating planning notes as proof without checking the current code or kernel state.",
            "Treating codex/derived/map.json as the only source of truth.",
            "Reading multiple mission docs before resolving the active mission.",
            "Using --paths as the primary orientation command.",
        ],
        "derived_artifacts": {
            "map": _path_status(state.MAP_FILE),
            "compiled_dir": {
                **_path_status(state.COMPILED_DIR),
                "bundle_count": _compiled_bundle_count(),
            },
        },
        "observe_state": {
            "active_plan": _active_plan_summary(),
            "dump_count": len([path for path in state.OBSERVE_DUMPS.iterdir() if path.is_dir()]) if state.OBSERVE_DUMPS.exists() else 0,
        },
        "doctrine_control_plane": {
            "runtime_spec": state.rel(state.DOCTRINE_RUNTIME_SPEC),
            "runtime_spec_exists": state.DOCTRINE_RUNTIME_SPEC.is_file(),
            "emit_command": "python3 kernel.py --doctrine-runtime",
            "pulse_full_command": "python3 kernel.py --pulse --full",
            "registry": "codex/doctrine/doctrine_registry.json",
            "standards_group_id": "doctrine",
            "assimilation": "codex/doctrine/doctrine_surface.json (raw_seed_assimilation)",
            "routing": "codex/doctrine/doctrine_routing.json",
        },
    }
    compact_hints: dict[str, Any] = {}
    try:
        frontier_result = KernelNavigation(state.REPO_ROOT).build_frontier(state.MARKDOWN_FRONTIER_DEFAULT_LIMIT)
    except ValueError:
        frontier_result = None
    if frontier_result is not None:
        compact_hints["recent_frontier"] = frontier_result.payload.get("recent_markdown", [])
        warnings.extend(frontier_result.warnings)
    result = NavigationResult(
        kind="kernel.navigate.info",
        query={"command": "info"},
        payload=payload,
        live_sources=[
            "kernel.py",
            "codex/CODEX.md",
            "codex/_index.md",
            "codex/doctrine/operations/codex_change_protocol.md",
            "codex/doctrine/skills/kernel/bootstrap.md",
            "codex/doctrine/skills/kernel/_schema.json",
            "codex/standards/std_work_note.json",
            "codex/standards/std_plan_note.json",
        ],
        derived_sources=[state.rel(state.MAP_FILE)] if state.MAP_FILE.exists() else [],
        suggested_next=(
            active_execution_next
            + [
                {"command": "python3 kernel.py --docs-route documentation", "reason": "Resolve the machine-owned minimum read set for documentation-plane orientation"},
                {"command": f"python3 kernel.py --frontier {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}", "reason": "Use only when markdown recency, not live-work selection, is the question"},
                {"command": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}", "reason": "Recover phase/note context after live WorkItems and claims are checked"},
            ]
            if active_execution_next
            else [
                {"command": "python3 kernel.py --pulse", "reason": "See the current control-plane state and highest-leverage next commands in one view"},
                {"command": "python3 kernel.py --docs-route documentation", "reason": "Resolve the machine-owned minimum read set for documentation-plane orientation"},
                {"command": f"python3 kernel.py --frontier {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}", "reason": "Sync with recent markdown work before deeper exploration"},
                {"command": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT}", "reason": "Recover the active obsidian work cluster when the task is a continuation"},
                {"command": "python3 kernel.py --bootstrap-task <note-or-token>", "reason": "Recover the bounded task-entry packet when the target note is already known"},
                {"command": "python3 kernel.py --obsidian-family <note-or-token>", "reason": "Recover a known obsidian note family directly when the anchor note is already known"},
                {"command": "python3 kernel.py --execution-map latest", "reason": "Recover planner-memory and duplicate-surface guidance before reopening the search space"},
                {"command": "python3 kernel.py --map latest", "reason": "Recover living boundary memory and focus-path freshness before launching new observe work"},
                {"command": "python3 kernel.py --plan-phase", "reason": "If the task is phased implementation work, resolve the active batch before editing"},
                {"command": "python3 kernel.py --atlas", "reason": "System-wide topology briefing"},
                {"command": "python3 kernel.py --locate <token>", "reason": "Resolve a target before deep reading"},
                {"command": "python3 kernel.py --orient <mission>", "reason": "Mission-level briefing"},
                {"command": "python3 kernel.py --context <node_id>", "reason": "Node-level summary context"},
                {"command": "python3 kernel.py --context <node_id> --context-view standards", "reason": "Node-specific standards, doctrine schema, and contract surfaces"},
                {"command": "python3 kernel.py --lens <doc:...|mission:...|node:...|run:...>", "reason": "Expand only the resolved semantic boundary when deeper optics are needed"},
            ]
        ),
        warnings=warnings,
        compact_hints=compact_hints,
    )
    return emit_navigation(result)


def cmd_pulse() -> int:
    """
    [ACTION]
    - Teleology: Emit a compact operator-facing self-assessment of the repo's active loops.
    - Mechanism: Fuses frontier, active observe plans, latest grouped runtime, builder staleness,
      doctrine drift, and workspace counts into one summary plus recommended commands.
    - Reads: Kernel navigation, builder hologram status, observe/apply workspace files.
    - Writes: None.
    - Fails: Returns 1 only if pulse assembly raises an unexpected exception.
    - When-needed: Open when you need one compact status surface for open loops, stale builder state, docs focus, and next commands before choosing a subsystem.
    - Escalates-to: system/lib/kernel_nav_phase.py; system/lib/kernel_nav_lens.py; kernel.py
    - Navigation-group: kernel_lib
    """
    try:
        snapshot = _pulse_snapshot(exact=True) if state.NAVIGATION_FULL_OUTPUT else _pulse_snapshot()
    except Exception as exc:
        print(f"ERROR: failed to build pulse: {exc}", file=sys.stderr)
        return 1

    if state.NAVIGATION_FULL_OUTPUT:
        return emit_json(snapshot)

    frontier = snapshot.get("frontier_anchor") if isinstance(snapshot.get("frontier_anchor"), dict) else {}
    active_plan = snapshot.get("active_plan") if isinstance(snapshot.get("active_plan"), dict) else {}
    runtime = snapshot.get("latest_runtime") if isinstance(snapshot.get("latest_runtime"), dict) else {}
    builder = snapshot.get("builder") if isinstance(snapshot.get("builder"), dict) else {}
    doctrine = snapshot.get("doctrine") if isinstance(snapshot.get("doctrine"), dict) else {}
    workspace = snapshot.get("workspace") if isinstance(snapshot.get("workspace"), dict) else {}
    closeout_git_state = snapshot.get("closeout_git_state") if isinstance(snapshot.get("closeout_git_state"), dict) else {}
    docfix = snapshot.get("latest_docfix_plan") if isinstance(snapshot.get("latest_docfix_plan"), dict) else {}
    routing = snapshot.get("routing_projection") if isinstance(snapshot.get("routing_projection"), dict) else {}
    residual_lanes = snapshot.get("residual_lanes") if isinstance(snapshot.get("residual_lanes"), list) else []
    active_execution = (
        snapshot.get("active_execution_constellation")
        if isinstance(snapshot.get("active_execution_constellation"), Mapping)
        else {}
    )

    print("KERNEL PULSE")
    print(f"  generated: {snapshot.get('generated_at')}")
    print(f"  repo: {state.REPO_ROOT.name}")
    print()
    print("CURRENT")
    if frontier:
        frontier_path = str(frontier.get("path") or "").strip() or "unknown"
        frontier_line = f"  frontier: {frontier_path}"
        age = _pulse_age_label(frontier.get("modified_at"))
        if age:
            frontier_line += f" ({age})"
        print(frontier_line)
    else:
        print("  frontier: unavailable")

    if active_plan and not active_plan.get("error"):
            print(
                "  active plan:"
                f" {active_plan.get('path')} | {active_plan.get('runtime')} |"
                f" groups={active_plan.get('group_count')} files={active_plan.get('total_files')}"
            )
    else:
        print("  active plan: none")

    if routing:
        routing_line = "  routing: stale" if routing.get("stale") else "  routing: current"
        drift_targets = routing.get("drift_targets") if isinstance(routing.get("drift_targets"), list) else []
        if drift_targets:
            routing_line += f" | drift={','.join(str(item) for item in drift_targets)}"
        source_coupling = (
            routing.get("source_coupling")
            if isinstance(routing.get("source_coupling"), Mapping)
            else {}
        )
        coupling_status = str(source_coupling.get("status") or "").strip()
        if coupling_status and coupling_status != "clean_source_inputs_and_artifacts":
            routing_line += f" | source_coupling={coupling_status}"
            dirty_sources = source_coupling.get("dirty_source_paths")
            if isinstance(dirty_sources, list) and dirty_sources:
                preview = ",".join(str(path) for path in dirty_sources[:2])
                routing_line += f" ({preview})"
        artifact_path = str(routing.get("artifact_path") or "").strip()
        if artifact_path:
            routing_line += f" | artifact={artifact_path}"
        print(routing_line)

    if runtime:
        if runtime.get("kind") == "orchestration_state":
            runtime_line = f"  orchestration: {runtime.get('state') or 'unknown'}"
            if runtime.get("gate_reason"):
                runtime_line += f" | gate={runtime.get('gate_reason')}"
            age = _pulse_age_label(runtime.get("updated_at"))
            if age:
                runtime_line += f" | updated={age}"
            print(runtime_line)
            el = runtime.get("event_log") if isinstance(runtime.get("event_log"), dict) else {}
            if el.get("path"):
                eid = el.get("latest_event_id") or "n/a"
                print(f"  orchestration event log: {el.get('path')} | latest_event={eid}")
            if runtime.get("command"):
                stale_pointers = (
                    active_execution.get("stale_decorative_pointers")
                    if isinstance(active_execution.get("stale_decorative_pointers"), list)
                    else []
                )
                if stale_pointers:
                    print(f"  dormant runtime action (context): {runtime.get('command')}")
                else:
                    print(f"  next control action: {runtime.get('command')}")
            coordination = runtime.get("coordination") if isinstance(runtime.get("coordination"), dict) else {}
            current_owner = coordination.get("current_owner") if isinstance(coordination.get("current_owner"), dict) else {}
            next_handoff = coordination.get("next_handoff") if isinstance(coordination.get("next_handoff"), dict) else {}
            active_directive = coordination.get("active_directive") if isinstance(coordination.get("active_directive"), dict) else {}
            if current_owner.get("actor_id"):
                print(f"  current owner: {current_owner.get('actor_id')} | driver={current_owner.get('driver_id') or 'unknown'}")
            if next_handoff.get("actor_id") or next_handoff.get("mode"):
                print(
                    f"  next handoff: {next_handoff.get('actor_id') or 'unknown'} | "
                    f"mode={next_handoff.get('mode') or 'unknown'}"
                )
            if active_directive.get("active"):
                print(
                    f"  active directive: {active_directive.get('task') or active_directive.get('summary') or 'active'}"
                )
        else:
            runtime_line = (
                f"  latest observe: {runtime.get('state') or 'unknown'}"
                f" | provider={runtime.get('provider') or '?'}"
                f" | groups={runtime.get('completed_groups') or 0}/{runtime.get('total_groups') or 0}"
            )
            age = _pulse_age_label(runtime.get("updated_at"))
            if age:
                runtime_line += f" | updated={age}"
            print(runtime_line)
    else:
        print("  orchestration: unavailable")
    navigation_lane = next(
        (
            item
            for item in residual_lanes
            if isinstance(item, Mapping) and str(item.get("lane_id") or "") == "navigation_enforcement"
        ),
        None,
    )
    if isinstance(navigation_lane, Mapping):
        entry_command = str(navigation_lane.get("entry_command") or "").strip()
        if entry_command:
            print(f"  navigation residual available: {entry_command}")
    organisation_plane = (
        snapshot.get("organisation_control_plane")
        if isinstance(snapshot.get("organisation_control_plane"), Mapping)
        else {}
    )
    if organisation_plane.get("command"):
        print(f"  organisation control plane: {organisation_plane.get('command')}")
        freshness = str(organisation_plane.get("freshness_policy") or "").strip()
        if freshness:
            print(f"  organisation control plane freshness: {freshness}")
    if active_execution:
        anchor = (
            active_execution.get("declared_anchor")
            if isinstance(active_execution.get("declared_anchor"), Mapping)
            else {}
        )
        campaigns = (
            active_execution.get("live_campaigns")
            if isinstance(active_execution.get("live_campaigns"), list)
            else []
        )
        live_sessions = (
            active_execution.get("live_sessions")
            if isinstance(active_execution.get("live_sessions"), Mapping)
            else {}
        )
        session_counts = (
            live_sessions.get("counts")
            if isinstance(live_sessions.get("counts"), Mapping)
            else {}
        )
        scope_candidates = (
            active_execution.get("supervised_scope_candidates")
            if isinstance(active_execution.get("supervised_scope_candidates"), list)
            else []
        )
        projection_freshness = (
            active_execution.get("projection_freshness")
            if isinstance(active_execution.get("projection_freshness"), Mapping)
            else {}
        )
        demotion_guard = (
            active_execution.get("demotion_guard")
            if isinstance(active_execution.get("demotion_guard"), Mapping)
            else {}
        )
        print(
            "  active execution:"
            f" declared={anchor.get('phase_id') or 'none'}"
            f" status={anchor.get('status') or active_execution.get('status') or 'unknown'}"
            f" | campaigns={len(campaigns)}"
            f" claims={session_counts.get('active_claims') or 0}"
            f" scope_candidates={len(scope_candidates)}"
            f" freshness={projection_freshness.get('status') or 'unknown'}"
            f" demotion_guard={demotion_guard.get('status') or 'unknown'}"
        )
        stale_pointers = (
            active_execution.get("stale_decorative_pointers")
            if isinstance(active_execution.get("stale_decorative_pointers"), list)
            else []
        )
        if stale_pointers:
            first_pointer = stale_pointers[0] if isinstance(stale_pointers[0], Mapping) else {}
            print(
                "  active execution stale pointer:"
                f" {first_pointer.get('pointer') or 'unknown'} -> "
                f"{first_pointer.get('replacement_surface') or 'Task Ledger + Work Ledger'}"
            )
    if closeout_git_state:
        publication = (
            closeout_git_state.get("publication")
            if isinstance(closeout_git_state.get("publication"), Mapping)
            else {}
        )
        recommended = (
            closeout_git_state.get("recommended_lane")
            if isinstance(closeout_git_state.get("recommended_lane"), Mapping)
            else {}
        )
        worktrees = (
            closeout_git_state.get("worktrees")
            if isinstance(closeout_git_state.get("worktrees"), Mapping)
            else {}
        )
        scoped_gate = (
            closeout_git_state.get("scoped_work_gate")
            if isinstance(closeout_git_state.get("scoped_work_gate"), Mapping)
            else {}
        )
        line = (
            "  git state:"
            f" dirty={closeout_git_state.get('dirty_total')}"
            f" staged={closeout_git_state.get('staged_total')}"
            f" ahead={closeout_git_state.get('ahead')}"
            f" behind={closeout_git_state.get('behind')}"
            f" publication={publication.get('status') or 'unknown'}"
            f"{_pulse_worktree_summary_segment(worktrees)}"
            f" closeout_ready={str(bool(closeout_git_state.get('closeout_ready'))).lower()}"
        )
        if "scoped_work_allowed" in closeout_git_state:
            scoped_status = str(scoped_gate.get("status") or "").strip()
            if not scoped_status:
                scoped_status = "allowed" if closeout_git_state.get("scoped_work_allowed") else "blocked"
            line += f" scoped_work={scoped_status}"
        scoped_lane = str(scoped_gate.get("required_lane") or "").strip()
        if scoped_lane:
            line += f" scoped_lane={scoped_lane}"
        lane = str(recommended.get("lane") or "").strip()
        if lane and lane != "closeout_ready":
            line += f" | lane={lane}"
        print(line)
    closeout = snapshot.get("closeout_gap") if isinstance(snapshot.get("closeout_gap"), dict) else {}
    closeout_limited = bool(closeout.get("candidate_scan_limited"))
    failed_unresolved = int(
        closeout.get("failed_unresolved_count")
        if closeout.get("failed_unresolved_count") is not None
        else closeout.get("failed_recovery_count") or 0
    )
    failed_dispositioned = int(closeout.get("failed_dispositioned_count") or 0)
    failed_historic = int(closeout.get("failed_historic_count") or 0)
    actionable_closeout_count = (
        int(closeout.get("pending_closeout_count") or 0)
        + failed_unresolved
        + int(closeout.get("inflight_count") or 0)
    )
    orphaned_count = int(closeout.get("orphaned_count") or 0)
    if actionable_closeout_count > 0:
        line = (
            "  closeout gap:"
            f" pending={closeout.get('pending_closeout_count') or 0}"
            f" failed={failed_unresolved}"
            f" inflight={closeout.get('inflight_count') or 0}"
        )
        if failed_dispositioned:
            line += f" dispositioned={failed_dispositioned}"
        if failed_historic:
            line += f" historical={failed_historic}"
        print(line)
    elif failed_dispositioned or failed_historic:
        bits: list[str] = []
        if failed_dispositioned:
            bits.append(f"dispositioned={failed_dispositioned}")
        if failed_historic:
            bits.append(f"historical={failed_historic}")
        label = "closeout recent history" if closeout_limited else "closeout history"
        print(f"  {label}: {' '.join(bits)} (no actionable recovery in scanned sessions)")
        closeout_items = closeout.get("items") if isinstance(closeout.get("items"), list) else []
        if closeout_items:
            phase_labels = ", ".join(
                str(item.get("phase_number") or item.get("phase_id") or item.get("session_slug") or "").strip()
                for item in closeout_items[:3]
                if str(item.get("phase_number") or item.get("phase_id") or item.get("session_slug") or "").strip()
            )
            if phase_labels:
                print(f"  closeout phases: {phase_labels}")
    elif orphaned_count > 0:
        print(f"  orphaned observe sessions: {orphaned_count}")
    closeout_cache = (
        (snapshot.get("pulse_cache") or {}).get("closeout_audit")
        if isinstance(snapshot.get("pulse_cache"), Mapping)
        else {}
    )
    if isinstance(closeout_cache, Mapping):
        closeout_cache_status = str(closeout_cache.get("status") or "").strip()
        if closeout_cache_status and closeout_cache_status not in {"hit", "waited_hit"}:
            print(
                "  closeout audit:"
                f" {closeout_cache_status} | freshness={closeout_cache.get('freshness_policy') or 'unknown'}"
            )

    dp = snapshot.get("documentation_plane") if isinstance(snapshot.get("documentation_plane"), dict) else {}
    if dp.get("docs_route_example"):
        print(f"  docs route: {dp.get('docs_route_example')}")
    drf = dp.get("documentation_route_focus") if isinstance(dp.get("documentation_route_focus"), dict) else {}
    if drf.get("active_preset_id"):
        label = str(drf.get("label") or "").strip()
        suffix = f" ({label})" if label else ""
        print(f"  docs focus: {drf.get('active_preset_id')}{suffix}")

    if docfix and not docfix.get("error"):
        print(
            f"  latest docfix: {docfix.get('path')} | groups={docfix.get('group_count')} files={docfix.get('total_files')}"
        )
    else:
        print("  latest docfix: none")

    if builder.get("exists"):
        staleness_status = str(builder.get("staleness_status") or "").strip()
        label = (
            "quick"
            if staleness_status == "deferred_for_pulse_hot_path"
            else "current"
            if builder.get("all_current")
            else "stale"
        )
        stale_names = ", ".join(builder.get("stale_phase_names", [])[:6]) or "none"
        freshness_suffix = " | freshness=deferred" if staleness_status == "deferred_for_pulse_hot_path" else ""
        print(
            f"  hologram: {label} | artifacts={builder.get('total_artifacts')} |"
            f" stale_phases={builder.get('stale_phases')} ({stale_names})"
            f"{freshness_suffix}"
        )
    else:
        print("  hologram: missing")

    print(
        f"  doctrine: docs={doctrine.get('total_docs')} | drift={doctrine.get('drift_docs')} |"
        f" graph={doctrine.get('graph_docs')}"
    )
    print(
        f"  workspace: observe_plans={workspace.get('observe_plan_count')} |"
        f" dumps={workspace.get('observe_dump_count')} |"
        f" plan_manifests={workspace.get('plan_manifest_count')} |"
        f" apply_snapshots={workspace.get('apply_snapshot_count')}"
    )

    annex_landing = snapshot.get("annex_landing") if isinstance(snapshot.get("annex_landing"), dict) else {}
    if annex_landing.get("available"):
        total = int(annex_landing.get("total_patterns") or 0)
        adopted = int(annex_landing.get("adopted_count") or 0)
        rate = annex_landing.get("landing_rate_pct") or 0.0
        suffix = " — under-fire" if annex_landing.get("under_fire") else ""
        annex_count = annex_landing.get("annex_count") or 0
        placeholder_count = annex_landing.get("placeholder_count") or 0
        print(
            f"  annex landing: {adopted}/{total} patterns adopted ({rate}%){suffix}"
            f" | annexes={annex_count} placeholder={placeholder_count}"
        )

    hot_now_lines = _pulse_hot_now_lines(active_execution)
    if hot_now_lines:
        print()
        print("HOT NOW")
        for line in hot_now_lines:
            print(line)

    provider_plane = snapshot.get("provider_plane") if isinstance(snapshot.get("provider_plane"), dict) else {}
    if provider_plane and provider_plane.get("status") != "error":
        from system.lib.provider_plane_liveness import provider_plane_pulse_lines

        lines = provider_plane_pulse_lines(provider_plane)
        if lines:
            print()
            print("PROVIDER PLANE")
            for line in lines:
                print(line)
    provider_cache = (
        (snapshot.get("pulse_cache") or {}).get("provider_plane_liveness")
        if isinstance(snapshot.get("pulse_cache"), Mapping)
        else {}
    )
    if isinstance(provider_cache, Mapping):
        provider_cache_status = str(provider_cache.get("status") or "").strip()
        if provider_cache_status and provider_cache_status not in {"hit", "waited_hit"}:
            print(
                "  provider plane:"
                f" {provider_cache_status} | freshness={provider_cache.get('freshness_policy') or 'unknown'}"
            )

    # TOP PRIORITY block: surface the rank-1 ready Task Ledger WorkItem so a
    # cold agent does not route past the P0 into the active phase's runtime
    # lane. The active phase remains visible above; this block adds the
    # WorkItem layer that pulse used to omit entirely.
    priority = (
        snapshot.get("task_ledger_priority")
        if isinstance(snapshot.get("task_ledger_priority"), Mapping)
        else {}
    )
    top_workitem = (
        priority.get("top_schedulable_workitem")
        if isinstance(priority.get("top_schedulable_workitem"), Mapping)
        else priority.get("top_ready_workitem")
        if isinstance(priority.get("top_ready_workitem"), Mapping)
        else None
    )
    if top_workitem and top_workitem.get("id"):
        print()
        print("TOP PRIORITY (Task Ledger)")
        rank_label = top_workitem.get("rank")
        rank_str = f"rank={rank_label}" if rank_label is not None else "rank=unranked"
        state_str = f"state={top_workitem.get('state') or 'unknown'}"
        source_view = str(top_workitem.get("source_view") or "").strip()
        source_suffix = f" | source={source_view}" if source_view else ""
        print(f"  workitem: {top_workitem.get('id')} | {rank_str} | {state_str}{source_suffix}")
        title = top_workitem.get("title")
        if title:
            print(f"  title: {title}")
        snippet = top_workitem.get("statement_snippet")
        if snippet:
            print(f"  statement: {snippet}")
        for line in _pulse_workitem_dependency_lines(top_workitem):
            print(line)
        view_counts = priority.get("view_counts") if isinstance(priority.get("view_counts"), Mapping) else {}
        dependency_blocked_count = int(view_counts.get("dependency_blocked") or 0)
        unlocks_count = int(view_counts.get("unlocks_by_rank") or 0)
        unlock_pressure_count = int(view_counts.get("unlock_pressure") or 0)
        if dependency_blocked_count or unlocks_count:
            print(
                "  blocker constellation:"
                f" dependency_blocked={dependency_blocked_count}"
                f" unlocks_by_rank={unlocks_count}"
                f" unlock_pressure={unlock_pressure_count}"
            )
            schedulable_pressure = _pulse_workitem_rows(
                priority.get("top_schedulable_unlock_pressure_workitems")
            )
            if schedulable_pressure:
                print("  schedulable unlock pressure:")
                for row in schedulable_pressure[:3]:
                    print(_pulse_workitem_summary_line("candidate", row, include_pressure=True))
            global_pressure = _pulse_workitem_rows(
                priority.get("top_global_unlock_pressure_workitems")
            )
            if global_pressure:
                print("  hidden/global unlock pressure: not necessarily schedulable")
                print("  hidden unlock pressure:")
                for row in global_pressure[:3]:
                    print(_pulse_workitem_summary_line("hidden", row, include_pressure=True))
            top_blocked = (
                priority.get("top_dependency_blocked_workitem")
                if isinstance(priority.get("top_dependency_blocked_workitem"), Mapping)
                else {}
            )
            if top_blocked:
                print(_pulse_workitem_summary_line("top blocked", top_blocked))
                blocked_summary = (
                    top_blocked.get("dependency_summary")
                    if isinstance(top_blocked.get("dependency_summary"), Mapping)
                    else {}
                )
                if blocked_summary:
                    print(
                        "  blocked deps:"
                        f" unsatisfied={blocked_summary.get('unsatisfied_dep_count') or 0}"
                        f" downstream_unlocks={blocked_summary.get('downstream_unlock_count') or 0}"
                    )
            blocked_rows = _pulse_workitem_rows(priority.get("top_dependency_blocked_workitems"))
            if len(blocked_rows) > 1:
                print("  blocked queue:")
                for row in blocked_rows[:3]:
                    print(_pulse_workitem_summary_line("blocked", row, include_pressure=True))
        drilldown = top_workitem.get("drilldown_command")
        if drilldown:
            print(f"  open: {drilldown}")

    hotspots = doctrine.get("hotspots") if isinstance(doctrine.get("hotspots"), list) else []
    if hotspots:
        print()
        print("HOTSPOTS")
        for item in hotspots[:3]:
            reasons = ", ".join(item.get("drift_reasons", [])[:2])
            print(f"  - {item.get('path')} ({reasons or 'drift'})")
    elif doctrine.get("hotspots_deferred"):
        print()
        print("HOTSPOTS")
        print(
            "  deferred:"
            f" {doctrine.get('hotspot_deferred_reason') or 'quick pulse defers live hotspot examples'}"
        )
        if doctrine.get("hotspot_command"):
            print(f"  open: {doctrine.get('hotspot_command')}")

    # Render recent autonomous reaction fires so the operator sees what the
    # system did between agent sessions.  Per
    # local_to_general_propagation.md § "Autonomy must surface through the
    # agent entrypoint", machine-snapshot visibility is necessary but not
    # sufficient — pulse text is the surface a fresh agent reads first.
    recent_fires = (
        snapshot.get("recent_autonomous_fires")
        if isinstance(snapshot.get("recent_autonomous_fires"), list)
        else []
    )
    if recent_fires:
        print()
        print("AUTONOMOUS FIRES")
        ledger_path = REACTIONS_LEDGER_REL
        for fire in recent_fires[:3]:
            if not isinstance(fire, dict):
                continue
            reaction_id = str(fire.get("reaction_id") or "unknown").strip() or "unknown"
            operation_id = str(fire.get("operation_id") or "unknown").strip() or "unknown"
            target_row_id = str(fire.get("target_row_id") or "").strip()
            fire_path = str(fire.get("ledger_path") or "").strip()
            if fire_path:
                ledger_path = fire_path
            line = f"  - {reaction_id} -> {operation_id}"
            if target_row_id:
                line += f" target={target_row_id}"
            age = _pulse_age_label(fire.get("fired_at"))
            if age:
                line += f" ({age})"
            print(line)
        print(f"  ledger: {ledger_path}")

    # Render reactions that are ready to fire but losing scheduler priority,
    # so the operator can distinguish "ready and deferred" from "not ready"
    # or "broken." Per the new "Autonomy must surface through the agent
    # entrypoint" governing principle, this is the visibility surface that
    # prevents scheduler starvation from masquerading as quietness.
    deferred_ready = (
        snapshot.get("ready_deferred_reactions")
        if isinstance(snapshot.get("ready_deferred_reactions"), list)
        else []
    )
    if deferred_ready:
        print()
        print("READY (DEFERRED)")
        for item in deferred_ready[:3]:
            if not isinstance(item, dict):
                continue
            reaction_id = str(item.get("reaction_id") or "unknown").strip() or "unknown"
            operation_id = str(item.get("operation_id") or "unknown").strip() or "unknown"
            priority = str(item.get("priority") or "").strip()
            target_row_id = str(item.get("target_row_id") or "").strip()
            blocked_by = str(item.get("blocked_by") or "").strip()
            barrier_kind = str(item.get("barrier_kind") or "").strip()
            line = f"  - {reaction_id} -> {operation_id}"
            if target_row_id:
                line += f" target={target_row_id}"
            if priority:
                line += f" priority={priority}"
            if blocked_by:
                if barrier_kind:
                    line += f" blocked_by={blocked_by}({barrier_kind})"
                else:
                    line += f" blocked_by={blocked_by}"
            print(line)

    print()
    print("NEXT")
    for index, item in enumerate(snapshot.get("recommended_actions", [])[:4], start=1):
        print(f"  {index}. {item.get('command')}")
        print(f"     {item.get('reason')}")

    print()
    print("ROUTES")
    for item in snapshot.get("decision_tree", [])[:6]:
        print(f"  {item.get('intent')}: {item.get('command')}")
    return 0


def _preflight_active_phase() -> dict[str, Any]:
    try:
        phase = load_explicit_active_phase(state.REPO_ROOT)
    except Exception as exc:
        return {"active": False, "error": str(exc)}
    if not isinstance(phase, Mapping) or not phase:
        return {"active": False}
    return {
        "active": True,
        "phase_id": phase.get("phase_id"),
        "phase_number": phase.get("phase_number"),
        "phase_title": phase.get("phase_title"),
        "phase_dir": phase.get("phase_dir"),
        "family_dir": phase.get("family_dir"),
    }


def _preflight_compact_workitem(workitem: object) -> dict[str, Any] | None:
    if not isinstance(workitem, Mapping) or not workitem.get("id"):
        return None
    compact = {
        key: workitem.get(key)
        for key in ("id", "title", "rank", "state", "source_view", "drilldown_command")
        if workitem.get(key) not in (None, "", [], {})
    }
    dependency_summary = (
        workitem.get("dependency_summary")
        if isinstance(workitem.get("dependency_summary"), Mapping)
        else None
    )
    if dependency_summary:
        compact["dependency_summary"] = {
            key: dependency_summary.get(key)
            for key in (
                "schedulable",
                "hard_dep_count",
                "unsatisfied_dep_count",
                "downstream_unlock_count",
                "upstream_dependency_count",
            )
            if dependency_summary.get(key) not in (None, "", [], {})
        }
        edges = (
            dependency_summary.get("top_downstream_unlock_edges")
            if isinstance(dependency_summary.get("top_downstream_unlock_edges"), list)
            else []
        )
        if edges:
            compact["dependency_summary"]["top_downstream_unlock_edges"] = edges[:2]
    priority_signal = (
        workitem.get("priority_signal")
        if isinstance(workitem.get("priority_signal"), Mapping)
        else None
    )
    if priority_signal:
        compact["priority_signal"] = {
            key: priority_signal.get(key)
            for key in (
                "unlock_pressure_score",
                "waiting_downstream_unlock_count",
                "downstream_unsatisfied_dep_total",
                "max_downstream_unsatisfied_dep_count",
                "downstream_unlock_count",
                "source_view",
            )
            if priority_signal.get(key) not in (None, "", [], {})
        }
    return compact


def _preflight_compact_work_priority(priority: object) -> dict[str, Any]:
    if not isinstance(priority, Mapping):
        return {}
    drilldowns = (
        priority.get("drilldown_commands")
        if isinstance(priority.get("drilldown_commands"), Mapping)
        else {}
    )
    def compact_rows(key: str) -> list[dict[str, Any]]:
        rows = priority.get(key) if isinstance(priority.get(key), list) else []
        compacted = [_preflight_compact_workitem(row) for row in rows[:3]]
        return [row for row in compacted if row]

    blocker_constellation = (
        priority.get("blocker_constellation")
        if isinstance(priority.get("blocker_constellation"), Mapping)
        else {}
    )
    return {
        "schema_version": priority.get("schema_version")
        or "task_ledger_priority_constellation_v1",
        "view_counts": dict(priority.get("view_counts") or {})
        if isinstance(priority.get("view_counts"), Mapping)
        else {},
        "top_schedulable_workitem": _preflight_compact_workitem(
            priority.get("top_schedulable_workitem")
        ),
        "top_dependency_blocked_workitem": _preflight_compact_workitem(
            priority.get("top_dependency_blocked_workitem")
        ),
        "top_schedulable_workitems": compact_rows("top_schedulable_workitems"),
        "top_schedulable_unlock_pressure_workitems": compact_rows(
            "top_schedulable_unlock_pressure_workitems"
        ),
        "top_dependency_blocked_workitems": compact_rows("top_dependency_blocked_workitems"),
        "top_global_unlock_pressure_workitems": compact_rows(
            "top_global_unlock_pressure_workitems"
        ),
        "dynamic_focus": dict(priority.get("dynamic_focus") or {})
        if isinstance(priority.get("dynamic_focus"), Mapping)
        else {},
        "blocker_constellation": {
            key: blocker_constellation.get(key)
            for key in (
                "schedulable_count",
                "ready_count",
                "dependency_blocked_count",
                "unlock_pressure_count",
                "unlocks_by_rank_count",
            )
            if blocker_constellation.get(key) not in (None, "", [], {})
        },
        "drilldown_commands": {
            key: drilldowns.get(key)
            for key in (
                "organizer_report",
                "task_ledger_cluster",
                "top_schedulable_card",
                "highest_schedulable_unlock_pressure_card",
                "highest_global_unlock_pressure_card",
                "top_blocked_card",
            )
            if drilldowns.get(key)
        },
    }


def _preflight_compact_active_execution(active_execution: object) -> dict[str, Any]:
    if not isinstance(active_execution, Mapping):
        return {}

    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    session_rows = (
        live_sessions.get("sessions")
        if isinstance(live_sessions.get("sessions"), list)
        else []
    )
    drilldowns = (
        live_sessions.get("drilldown_commands")
        if isinstance(live_sessions.get("drilldown_commands"), Mapping)
        else {}
    )
    awareness_cards = (
        live_sessions.get("awareness_cards")
        if isinstance(live_sessions.get("awareness_cards"), list)
        else []
    )
    heartbeat_gap_rows = (
        live_sessions.get("heartbeat_gap_claim_sessions")
        if isinstance(live_sessions.get("heartbeat_gap_claim_sessions"), list)
        else []
    )

    compact_sessions: list[dict[str, Any]] = []
    for session in session_rows[:3]:
        if not isinstance(session, Mapping):
            continue
        compact_session = {
            key: session.get(key)
            for key in (
                "session_id",
                "actor",
                "phase_id",
                "claim_count",
                "path_count",
                "leased_until",
                "drilldown",
            )
            if session.get(key) not in (None, "", [], {})
        }
        paths = [str(path) for path in (session.get("paths") or []) if str(path).strip()]
        if paths:
            compact_session["paths"] = paths[:3]
        work_item_ids = [
            str(work_item_id)
            for work_item_id in (session.get("work_item_ids") or [])
            if str(work_item_id).strip()
        ]
        if work_item_ids:
            compact_session["work_item_ids"] = work_item_ids[:3]
        compact_sessions.append(compact_session)

    compact_awareness_cards: list[dict[str, Any]] = []
    for card in awareness_cards[:3]:
        if not isinstance(card, Mapping):
            continue
        compact_awareness_cards.append(
            {
                key: card.get(key)
                for key in (
                    "session_id",
                    "actor",
                    "freshness_state",
                    "pass_state",
                    "current_pass_line",
                    "last_pass_result_line",
                    "source",
                )
                if card.get(key) not in (None, "", [], {})
            }
        )

    compact_heartbeat_gap_rows: list[dict[str, Any]] = []
    for row in heartbeat_gap_rows[:2]:
        if not isinstance(row, Mapping):
            continue
        compact_heartbeat_gap_rows.append(
            {
                key: row.get(key)
                for key in (
                    "session_id",
                    "actor",
                    "phase_id",
                    "active_claim_count",
                    "heartbeat_source",
                    "freshness_state",
                    "scope_ref",
                    "heartbeat_command",
                )
                if row.get(key) not in (None, "", [], {})
            }
        )

    campaign_rows = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    compact_campaigns: list[dict[str, Any]] = []
    for campaign in campaign_rows[:3]:
        if not isinstance(campaign, Mapping):
            continue
        compact_campaigns.append(
            {
                key: campaign.get(key)
                for key in ("workitem_id", "id", "rank", "state", "title", "drilldown_command")
                if campaign.get(key) not in (None, "", [], {})
            }
        )

    anchor = (
        active_execution.get("declared_anchor")
        if isinstance(active_execution.get("declared_anchor"), Mapping)
        else {}
    )
    stale_pointers = (
        active_execution.get("stale_decorative_pointers")
        if isinstance(active_execution.get("stale_decorative_pointers"), list)
        else []
    )
    return {
        "kind": active_execution.get("kind") or "active_execution_constellation",
        "schema_version": active_execution.get("schema_version")
        or "active_execution_constellation_v0",
        "view_profile": "preflight_compact",
        "declared_anchor": dict(anchor),
        "stale_decorative_pointers": stale_pointers[:2],
        "live_campaigns": compact_campaigns,
        "live_sessions": {
            "counts": {
                key: session_counts.get(key)
                for key in (
                    "active_claims",
                    "effective_active_sessions",
                    "orphaned_active_sessions",
                    "claim_collisions",
                    "claim_session_heartbeat_gap_count",
                )
                if session_counts.get(key) not in (None, "", [], {})
            },
            "sessions": compact_sessions,
            "awareness_cards": compact_awareness_cards,
            "heartbeat_gap_status": live_sessions.get("heartbeat_gap_status"),
            "first_action": live_sessions.get("first_action"),
            "first_action_kind": live_sessions.get("first_action_kind"),
            "first_action_command": live_sessions.get("first_action_command"),
            "first_action_ref": live_sessions.get("first_action_ref"),
            "heartbeat_gap_claim_sessions": compact_heartbeat_gap_rows,
            "drilldown_commands": {
                key: drilldowns.get(key)
                for key in ("cards", "seed_speed", "seed_speed_no_heartbeat", "full", "claims")
                if drilldowns.get(key)
            },
        },
        "omission_receipt": {
            "omitted": [
                "live session claim refs",
                "awareness cards beyond first three",
                "full claim topology",
                "demotion guard blocker topology",
            ],
            "reason": "Preflight needs the hot-thread decision and owner drilldowns; full pulse carries detailed execution topology.",
            "drilldown": "./repo-python kernel.py --pulse --full",
        },
    }


def _preflight_build_card(snapshot: Mapping[str, Any], active_phase: Mapping[str, Any]) -> dict[str, Any]:
    runtime = snapshot.get("latest_runtime") if isinstance(snapshot.get("latest_runtime"), Mapping) else {}
    builder = snapshot.get("builder") if isinstance(snapshot.get("builder"), Mapping) else {}
    routing = snapshot.get("routing_projection") if isinstance(snapshot.get("routing_projection"), Mapping) else {}
    doctrine = snapshot.get("doctrine") if isinstance(snapshot.get("doctrine"), Mapping) else {}
    closeout = snapshot.get("closeout_gap") if isinstance(snapshot.get("closeout_gap"), Mapping) else {}
    recommended = snapshot.get("recommended_actions") if isinstance(snapshot.get("recommended_actions"), list) else []
    work_priority = _preflight_compact_work_priority(snapshot.get("task_ledger_priority"))
    active_execution = _preflight_compact_active_execution(
        snapshot.get("active_execution_constellation")
    )

    driver = str(runtime.get("driver") or runtime.get("kind") or runtime.get("state") or "unknown")
    gate_reason = str(runtime.get("gate_reason") or runtime.get("gate") or runtime.get("state") or "unknown")
    armed = not (driver == "no_active_runtime_phase" or gate_reason == "no_active_runtime_phase")

    paper_status = str(doctrine.get("paper_module_sidecar_status") or doctrine.get("paper_modules_status") or "")
    if not paper_status:
        paper_status = "current" if not doctrine.get("paper_module_sidecars_stale") else "stale"
    paper_stale = "stale" in paper_status or paper_status not in {"", "current", "in_sync", "ok"}

    bootstrap = doctrine.get("agent_bootstrap") if isinstance(doctrine.get("agent_bootstrap"), Mapping) else {}
    bootstrap_stale = bool(bootstrap.get("stale") or doctrine.get("agent_bootstrap_stale"))
    bootstrap_drift = list(bootstrap.get("drift") or doctrine.get("agent_bootstrap_drift") or [])

    stale_phase_names = list(builder.get("stale_phase_names") or [])
    doctrine_drift = int(doctrine.get("drift_docs") or 0)
    closeout_count = (
        int(closeout.get("pending_closeout_count") or 0)
        + int(
            closeout.get("failed_unresolved_count")
            if closeout.get("failed_unresolved_count") is not None
            else closeout.get("failed_recovery_count") or 0
        )
        + int(closeout.get("inflight_count") or 0)
    )

    do_not = [
        "Do not edit raw_seed.md directly; voice appends route through python3 kernel.py --append-raw-seed, and agent prose routes through --append-agent-seed.",
        "Do not hand-edit generated live-context regions in AGENTS.md / CLAUDE.md / CODEX.md; regenerate via ./repo-python tools/meta/factory/build_agent_bootstrap_projection.py.",
        "Do not create a new git branch for this work; the repo runs on flat main.",
        "Do not run broad git stash/apply/reset/restore/clean in this shared dirty tree; use ./repo-git for mutating git operations.",
    ]
    if not armed:
        do_not.append("Do not revive deprecated runtime residue; the orchestration driver is dormant. Bootstrap the active phase line explicitly instead.")
    if stale_phase_names:
        do_not.append(
            "Do not trust system hologram data "
            f"(stale phases: {', '.join(str(name) for name in stale_phase_names)}) before `python3 kernel.py --build` finishes on the stale slices."
        )
    if paper_stale:
        do_not.append("Do not refresh agent bootstrap regions before the paper-module index catches up; run ./repo-python tools/meta/factory/build_paper_module_index.py first.")
    if doctrine_drift:
        do_not.append(f"Do not trust old doctrine guidance; {doctrine_drift} docs show drift risk. Inspect `./repo-python kernel.py --stale` first.")
    if closeout_count:
        do_not.append(f"Do not launch another campaign before closing {closeout_count} sessions via `./repo-python kernel.py --closeout-audit`.")

    recommended_actions: list[dict[str, str]] = []
    for action in recommended:
        if not isinstance(action, Mapping):
            continue
        command = str(action.get("command") or "").strip()
        if not command:
            continue
        compact_action = {"command": command}
        reason = str(action.get("reason") or "").strip()
        if reason:
            compact_action["reason"] = reason
        recommended_actions.append(compact_action)
        if len(recommended_actions) >= 4:
            break
    next_safe = recommended_actions[0] if recommended_actions else {}
    return {
        "kind": "kernel.preflight.card",
        "schema_version": "preflight_card_v1",
        "generated_at": snapshot.get("generated_at"),
        "phase": dict(active_phase),
        "runtime": {
            "driver": driver,
            "gate_reason": gate_reason,
            "armed": armed,
            "next_control_action": runtime.get("command"),
        },
        "active_execution": active_execution,
        "work_priority": work_priority,
        "freshness": {
            "system_hologram": {
                "status": "current" if builder.get("all_current") else "stale",
                "stale_phase_names": stale_phase_names,
                "stale_phase_count": int(builder.get("stale_phases") or len(stale_phase_names)),
            },
            "paper_module_sidecars": {
                "status": "stale" if paper_stale else "current",
                "detail": paper_status or "unknown",
            },
            "agent_bootstrap_regions": {
                "status": "stale" if bootstrap_stale else "current",
                "drift": bootstrap_drift,
            },
            "routing_projection": "stale" if routing.get("stale") else "current",
            "doctrine_drift_count": doctrine_drift,
            "closeout_gap_count": closeout_count,
        },
        "next_safe_command": {
            "command": next_safe.get("command"),
            "reason": next_safe.get("reason"),
        },
        "recommended_actions": recommended_actions,
        "do_not": do_not,
        "drilldown": [
            {"id": "phase_card", "command": "./repo-python kernel.py --phase"},
            {"id": "full_pulse", "command": "./repo-python kernel.py --pulse"},
            {"id": "nav_hologram", "command": "./repo-python kernel.py --nav-hologram"},
            {"id": "docs_route", "command": "./repo-python kernel.py --docs-route documentation"},
            {"id": "doctrine_freshness", "command": "./repo-python kernel.py --stale"},
            {"id": "closeout_audit", "command": "./repo-python kernel.py --closeout-audit"},
        ],
    }


def cmd_preflight() -> int:
    try:
        card = _preflight_card()
    except Exception as exc:
        print(f"ERROR: failed to build pulse snapshot for preflight: {exc}", file=sys.stderr)
        return 1
    if state.NAVIGATION_FULL_OUTPUT:
        return emit_json(card)

    phase = card["phase"]
    runtime = card["runtime"]
    active_execution = (
        card.get("active_execution")
        if isinstance(card.get("active_execution"), Mapping)
        else {}
    )
    work_priority = card.get("work_priority") if isinstance(card.get("work_priority"), Mapping) else {}
    freshness = card["freshness"]
    next_safe = card["next_safe_command"]
    recommended_actions = (
        card.get("recommended_actions")
        if isinstance(card.get("recommended_actions"), list)
        else []
    )

    print("KERNEL PREFLIGHT — agent-start card")
    print(f"  generated: {card.get('generated_at')}")
    print()
    print("PHASE")
    if phase.get("active"):
        print(f"  active: {phase.get('phase_number') or phase.get('phase_id')} | {phase.get('phase_title')}")
        print(f"  family_dir: {phase.get('family_dir') or 'unknown'}")
    else:
        print("  active: none")
        if phase.get("error"):
            print(f"  error: {phase.get('error')}")
    print()
    print("RUNTIME")
    print(f"  driver: {runtime.get('driver')} | gate: {runtime.get('gate_reason')}")
    print(f"  armed: {'yes' if runtime.get('armed') else 'no (driver is dormant)'}")
    if runtime.get("next_control_action"):
        action_label = (
            "next control action"
            if runtime.get("armed")
            else "dormant runtime action (context)"
        )
        print(f"  {action_label}: {runtime.get('next_control_action')}")
    print()
    hot_now_lines = _pulse_hot_now_lines(active_execution)
    if hot_now_lines:
        print("HOT NOW")
        for line in hot_now_lines:
            print(line)
        print()
    top_workitem = (
        work_priority.get("top_schedulable_workitem")
        if isinstance(work_priority.get("top_schedulable_workitem"), Mapping)
        else {}
    )
    if top_workitem:
        print("WORK PRIORITY")
        print(_pulse_workitem_summary_line("top schedulable", top_workitem))
        for line in _pulse_workitem_dependency_lines(top_workitem):
            print(line)
        view_counts = (
            work_priority.get("view_counts")
            if isinstance(work_priority.get("view_counts"), Mapping)
            else {}
        )
        dependency_blocked_count = int(view_counts.get("dependency_blocked") or 0)
        unlocks_count = int(view_counts.get("unlocks_by_rank") or 0)
        unlock_pressure_count = int(view_counts.get("unlock_pressure") or 0)
        print(
            "  blocker constellation:"
            f" dependency_blocked={dependency_blocked_count}"
            f" unlocks_by_rank={unlocks_count}"
            f" unlock_pressure={unlock_pressure_count}"
        )
        schedulable_pressure = _pulse_workitem_rows(
            work_priority.get("top_schedulable_unlock_pressure_workitems"),
            limit=1,
        )
        if schedulable_pressure and schedulable_pressure[0].get("id") != top_workitem.get("id"):
            print(
                _pulse_workitem_summary_line(
                    "highest schedulable unlock pressure",
                    schedulable_pressure[0],
                    include_pressure=True,
                )
            )
        global_pressure = _pulse_workitem_rows(
            work_priority.get("top_global_unlock_pressure_workitems"),
            limit=1,
        )
        if global_pressure:
            print(
                _pulse_workitem_summary_line(
                    "hidden unlock pressure",
                    global_pressure[0],
                    include_pressure=True,
                )
            )
            print("  hidden/global unlock pressure: not necessarily schedulable")
        blocked_rows = _pulse_workitem_rows(
            work_priority.get("top_dependency_blocked_workitems"),
            limit=1,
        )
        if blocked_rows:
            print(_pulse_workitem_summary_line("top dependency blocked", blocked_rows[0]))
            print("  blocked queue: dependency-blocked work requires upstream clearing")
        drilldowns = (
            work_priority.get("drilldown_commands")
            if isinstance(work_priority.get("drilldown_commands"), Mapping)
            else {}
        )
        open_cmd = str(drilldowns.get("top_schedulable_card") or "").strip()
        if open_cmd:
            print(f"  open: {open_cmd}")
        print()
    print("FRESHNESS")
    hologram = freshness["system_hologram"]
    stale_names = ", ".join(hologram.get("stale_phase_names") or [])
    suffix = f" ({hologram.get('stale_phase_count')} phases: {stale_names})" if stale_names else ""
    print(f"  system hologram: {hologram.get('status')}{suffix}")
    paper = freshness["paper_module_sidecars"]
    print(f"  paper-module sidecars: {paper.get('status')} ({paper.get('detail')})")
    bootstrap = freshness["agent_bootstrap_regions"]
    drift = ", ".join(bootstrap.get("drift") or [])
    drift_suffix = f" (drift: {drift})" if drift else ""
    print(f"  agent bootstrap regions: {bootstrap.get('status')}{drift_suffix}")
    print(f"  routing projection: {freshness.get('routing_projection')}")
    print(f"  doctrine drift: {freshness.get('doctrine_drift_count')} docs")
    print(f"  closeout gap: {freshness.get('closeout_gap_count')} sessions")
    print()
    if recommended_actions:
        print("NEXT HOT ACTIONS")
        for index, action in enumerate(recommended_actions[:4], start=1):
            if not isinstance(action, Mapping):
                continue
            command = str(action.get("command") or "").strip()
            if not command:
                continue
            print(f"  {index}. {command}")
            reason = str(action.get("reason") or "").strip()
            if reason:
                print(f"     reason: {reason}")
    else:
        print("NEXT SAFE COMMAND")
        print(f"  {next_safe.get('command') or 'none'}")
        if next_safe.get("reason"):
            print(f"  reason: {next_safe.get('reason')}")
    print()
    print("DO NOT")
    for warning in card["do_not"]:
        print(f"  - {warning}")
    print()
    print("DRILLDOWN")
    for item in card["drilldown"]:
        print(f"  {item.get('id')}: {item.get('command')}")
    return 0


def _preflight_card(profile_sink: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        snapshot = _pulse_snapshot(profile_sink=profile_sink)
    except Exception as exc:
        raise RuntimeError(f"failed to build pulse snapshot for preflight: {exc}") from exc
    return _preflight_build_card(snapshot, _preflight_active_phase())


def cmd_frontier(limit: int = state.MARKDOWN_FRONTIER_DEFAULT_LIMIT) -> int:
    """[ACTION]
    - Teleology: Emit the recent markdown frontier used to sync operator context.
    - Mechanism: Delegate to `KernelNavigation.build_frontier` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the frontier packet.
    - Fails: Returns 1 when the requested limit is invalid for the navigator.
    - When-needed: Open when the task is a continuation of recent markdown planning work and you need the freshest frontier before reading notes.
    - Escalates-to: system/lib/kernel_navigation.py; kernel.py
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_frontier(limit)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_recent_obsidian(limit: int = state.MARKDOWN_FRONTIER_DEFAULT_LIMIT) -> int:
    """[ACTION]
    - Teleology: Emit only the most recently edited Obsidian notes when broader markdown frontier context would add noise.
    - Mechanism: Delegate to `KernelNavigation.build_recent_obsidian()` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the recent-obsidian packet.
    - Fails: Returns 1 when the navigator rejects the requested limit.
    - When-needed: Open when note recovery should stay strictly inside recent Obsidian markdown instead of mixing in other markdown surfaces.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_notes.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_recent_obsidian(limit)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_working_set(limit: int = state.MARKDOWN_FRONTIER_DEFAULT_LIMIT, anchor: str | None = None) -> int:
    """[ACTION]
    - Teleology: Emit the continuity packet for the recent obsidian work cluster.
    - Mechanism: Delegate to `KernelNavigation.build_working_set` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the working-set packet.
    - Fails: Returns 1 when the navigator rejects the request.
    - When-needed: Open when recent markdown work must be reconstructed as one bounded continuity bundle instead of scanning notes manually.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_phase.py
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_working_set(limit, anchor=anchor)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_bootstrap_task(anchor: str, limit: int = state.MARKDOWN_FRONTIER_DEFAULT_LIMIT) -> int:
    """[ACTION]
    - Teleology: Emit a bounded task-entry packet when the operator already knows the anchor note, path, or token to recover from.
    - Mechanism: Delegate to `KernelNavigation.build_bootstrap_task()` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the bootstrap-task packet.
    - Fails: Returns 1 when the navigator cannot resolve the requested anchor or rejects the limit.
    - When-needed: Open when a continuation should start from one explicit note or token instead of recency-based working-set recovery.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_notes.py; system/lib/kernel_nav_phase.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_bootstrap_task(anchor, limit=limit)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_extract_note(targets: Sequence[str]) -> int:
    """[ACTION]
    - Teleology: Emit flattened markdown-note packets for one or more resolved note targets when raw note bodies need bounded extraction.
    - Mechanism: Delegate to `KernelNavigation.build_extract_note()` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the extracted-note packet.
    - Fails: Returns 1 when any requested note token or path cannot be resolved by the navigator.
    - When-needed: Open when one or more markdown notes must be extracted into structured navigation output without opening them manually in the editor.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_notes.py; system/lib/markdown_routing.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_extract_note(targets)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_extract_note_structure(target: str, *, mode: str = "full") -> int:
    """[ACTION]
    - Teleology: Emit the structural view of one markdown note when frontmatter, headings, and note sections are needed without full content extraction.
    - Mechanism: Delegate to `KernelNavigation.extract_note_structure()` with the requested mode and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the note-structure packet.
    - Fails: Returns 1 when the navigator cannot resolve the note target or rejects the requested mode.
    - When-needed: Open when note debugging depends on frontmatter and section structure rather than flattened note content.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_notes.py; system/lib/markdown_routing.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.extract_note_structure(path=target, mode=mode)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_set_focus(
    selector: str,
    *,
    focus_status: str | None = None,
    focus_label: str | None = None,
    focus_handoff: str | None = None,
    focus_scope: str = "family",
    clear_focus_status: bool = False,
    clear_focus_label: bool = False,
    clear_focus_handoff: bool = False,
    live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Preview or apply focus metadata updates so one Obsidian note or family can advertise active status, label, or handoff state to later navigation surfaces.
    - Mechanism: Resolve the requested target through `KernelNavigation.build_obsidian_family()`, stage frontmatter mutations for the chosen scope, and emit either a preview packet or live write result.
    - Reads: Obsidian family navigation, markdown frontmatter, and focus-related CLI arguments.
    - Writes: Focus metadata frontmatter on the targeted note or note family only when `live` is true.
    - Fails: Returns 1 on invalid selector, scope, mutually exclusive clear/set flags, invalid status choice, or unresolved focus target.
    - When-needed: Open when operator continuity needs note-family focus status, label, or handoff metadata previewed or applied through the kernel CLI.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/markdown_routing.py; docs/orchestration_state.md
    - Navigation-group: kernel_lib
    """
    requested = str(selector or "").strip()
    if not requested:
        print("ERROR: --set-focus requires a note/path/token", file=sys.stderr)
        return 1
    if focus_scope not in {"family", "note"}:
        print("ERROR: --focus-scope must be one of: family, note", file=sys.stderr)
        return 1
    if focus_status is not None and focus_status not in state.FOCUS_STATUS_CHOICES:
        print(
            "ERROR: --focus-status must be one of: " + ", ".join(state.FOCUS_STATUS_CHOICES),
            file=sys.stderr,
        )
        return 1
    if clear_focus_status and focus_status is not None:
        print("ERROR: --focus-status cannot be combined with --clear-focus-status", file=sys.stderr)
        return 1
    if clear_focus_label and focus_label is not None:
        print("ERROR: --focus-label cannot be combined with --clear-focus-label", file=sys.stderr)
        return 1
    if clear_focus_handoff and focus_handoff is not None:
        print("ERROR: --focus-handoff cannot be combined with --clear-focus-handoff", file=sys.stderr)
        return 1

    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        family_result = navigator.build_obsidian_family(requested, limit=state.MARKDOWN_FRONTIER_DEFAULT_LIMIT)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    family_payload = family_result.payload
    resolved_anchor = family_payload.get("anchor")
    if not isinstance(resolved_anchor, dict) or not str(resolved_anchor.get("path") or "").strip():
        print(f"ERROR: Could not resolve focus target: {requested}", file=sys.stderr)
        return 1
    target_path = str(resolved_anchor.get("path") or "").strip()
    target_title = str(resolved_anchor.get("title") or Path(target_path).stem).strip()
    family_members = [
        item
        for item in list((family_payload.get("family") or {}).get("members", []))
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    family_paths = [str(item.get("path") or "").strip() for item in family_members]

    explicit_mutation_requested = any(
        (
            focus_status is not None,
            clear_focus_status,
            focus_label is not None,
            clear_focus_label,
            focus_handoff is not None,
            clear_focus_handoff,
        )
    )
    requested_status = focus_status
    defaulted_to_active = False
    if not explicit_mutation_requested:
        requested_status = "active"
        defaulted_to_active = True

    updates_by_path: dict[str, dict[str, Any]] = {}

    def _stage_update(
        rel_path: str,
        *,
        reason: str,
        status_value: str | None = None,
        clear_status_value: bool = False,
        label_value: str | None = None,
        clear_label_value: bool = False,
        handoff_value: str | None = None,
        clear_handoff_value: bool = False,
    ) -> None:
        note_path = state.REPO_ROOT / rel_path
        card, body = _load_markdown_frontmatter(note_path)
        updated_card = dict(card)
        before = _focus_snapshot(card)
        changes: list[dict[str, Any]] = []

        def _set_or_clear(key: str, value: Any, clear_flag: bool) -> None:
            if clear_flag:
                if key in updated_card:
                    previous = updated_card.pop(key)
                    changes.append({"field": key, "before": previous, "after": None})
                return
            if value is None:
                return
            previous = updated_card.get(key)
            if previous == value:
                return
            updated_card[key] = value
            changes.append({"field": key, "before": previous, "after": value})

        _set_or_clear("focus_status", status_value, clear_status_value)
        _set_or_clear("focus_label", label_value, clear_label_value)
        _set_or_clear("focus_handoff", handoff_value, clear_handoff_value)

        if not changes:
            return

        updates_by_path[rel_path] = {
            "path": rel_path,
            "reason": reason,
            "title": Path(rel_path).stem,
            "before": before,
            "after": _focus_snapshot(updated_card),
            "changes": changes,
            "card": updated_card,
            "body": body,
        }

    _stage_update(
        target_path,
        reason="target_note",
        status_value=requested_status,
        clear_status_value=clear_focus_status,
        label_value=focus_label,
        clear_label_value=clear_focus_label,
        handoff_value=focus_handoff,
        clear_handoff_value=clear_focus_handoff,
    )

    if requested_status == "active" and focus_scope == "family":
        for rel_path in family_paths:
            if rel_path == target_path:
                continue
            sibling_card, _ = _load_markdown_frontmatter(state.REPO_ROOT / rel_path)
            if str(sibling_card.get("focus_status") or "").strip().lower() == "active":
                _stage_update(
                    rel_path,
                    reason="clear_sibling_active",
                    clear_status_value=True,
                )

    writes = list(updates_by_path.values())
    if live:
        for item in writes:
            note_path = state.REPO_ROOT / str(item["path"])
            note_path.write_text(
                render_markdown_document(item["card"], str(item["body"])),
                encoding="utf-8",
            )

    result_payload: dict[str, Any] = {
        "kind": "kernel.focus_update",
        "requested": requested,
        "mode": "live" if live else "preview",
        "target": {
            "path": target_path,
            "title": target_title,
        },
        "scope": focus_scope,
        "requested_updates": {
            "focus_status": requested_status,
            "defaulted_to_active": defaulted_to_active,
            "clear_focus_status": clear_focus_status,
            "focus_label": focus_label,
            "clear_focus_label": clear_focus_label,
            "focus_handoff": focus_handoff,
            "clear_focus_handoff": clear_focus_handoff,
        },
        "seed_context": family_payload.get("seed_context"),
        "focus_board_before": family_payload.get("focus_board"),
        "family_paths": family_paths,
        "writes": [
            {
                "path": item["path"],
                "reason": item["reason"],
                "before": item["before"],
                "after": item["after"],
                "changes": item["changes"],
            }
            for item in writes
        ],
        "live_required": bool(writes) and not live,
        "warnings": list(family_result.warnings),
        "next": [
            {
                "command": f"python3 kernel.py --working-set {state.MARKDOWN_FRONTIER_DEFAULT_LIMIT} --anchor {shlex.quote(target_path)}",
                "reason": "Reload the family packet after the focus update.",
            },
            {
                "command": f"python3 kernel.py --bootstrap-task {shlex.quote(target_path)}",
                "reason": "Reload the bounded task-entry packet for the updated note family.",
            },
        ],
    }
    if not writes:
        result_payload["status"] = "no_op"
        result_payload["message"] = "No focus frontmatter changes were required."
    elif live:
        post_navigator = KernelNavigation(state.REPO_ROOT)
        post_family = post_navigator.build_obsidian_family(target_path, limit=state.MARKDOWN_FRONTIER_DEFAULT_LIMIT)
        result_payload["status"] = "applied"
        result_payload["focus_board_after"] = post_family.payload.get("focus_board")
    else:
        result_payload["status"] = "preview_ready"

    return emit_json(result_payload)


def cmd_phase_demote_stale_focus(
    phase_token: str | None = None,
    *,
    limit: int = 1,
    live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Demote old phase notes that still advertise active/default focus while another phase is explicitly active.
    - Mechanism: Reuse the `--phase` lifecycle conflict detector, clear stale focus frontmatter from the selected conflicts, and append a JSONL archive receipt under the active phase archive directory.
    - Reads: The resolved phase card, lifecycle focus conflicts, and markdown frontmatter for conflicting notes.
    - Writes: Conflicting note frontmatter plus `archive/phase_focus_demotions.jsonl` only when `live` is true.
    - Fails: Returns 1 on invalid limit, unresolved phase, missing active phase directory, or unreadable conflicting note.
    - When-needed: Open when `--phase` reports stale active/default focus metadata on non-active phase notes and the cleanup must be auditable rather than a one-off frontmatter edit.
    - Escalates-to: system/lib/kernel_nav_phase.py::PhaseNavigationMixin._phase_lifecycle_enforcement; codex/doctrine/skills/kernel/phase_note_lifecycle.md
    """
    if limit < 0:
        print("ERROR: --phase-demote-limit must be >= 0", file=sys.stderr)
        return 1

    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_phase(phase_token)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    phase_payload = result.payload.get("phase") if isinstance(result.payload.get("phase"), Mapping) else {}
    lifecycle = (
        result.payload.get("phase_lifecycle_enforcement")
        if isinstance(result.payload.get("phase_lifecycle_enforcement"), Mapping)
        else {}
    )
    explicit_active = (
        lifecycle.get("explicit_active_phase")
        if isinstance(lifecycle.get("explicit_active_phase"), Mapping)
        else {}
    )
    active_phase_id = str(explicit_active.get("phase_id") or phase_payload.get("phase_id") or "").strip() or None
    active_phase_number = (
        str(explicit_active.get("phase_number") or phase_payload.get("phase_number") or "").strip() or None
    )
    active_phase_dir = (
        canonicalize_write_path(str(explicit_active.get("phase_dir") or phase_payload.get("phase_dir") or "").strip())
        or None
    )
    phase_ref = str(active_phase_id or active_phase_number or "").strip() or None
    if not active_phase_dir:
        print("ERROR: Could not resolve active phase directory for stale-focus demotion", file=sys.stderr)
        return 1

    archive_record_rel = canonicalize_write_path(f"{active_phase_dir.rstrip('/')}/archive/phase_focus_demotions.jsonl")
    conflicts = [
        item
        for item in list(lifecycle.get("focus_conflicts") or [])
        if isinstance(item, Mapping) and str(item.get("path") or "").strip()
    ]
    selected = conflicts[:limit]
    demotions: list[dict[str, Any]] = []

    demoted_at = datetime.now(timezone.utc).isoformat()
    for item in selected:
        rel_path = canonicalize_write_path(str(item.get("path") or "").strip())
        if not rel_path:
            continue
        note_path = state.REPO_ROOT / rel_path
        try:
            card, body = _load_markdown_frontmatter(note_path)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        updated = dict(card)
        changes: list[dict[str, Any]] = []
        for key in ("focus_status", "focus_label", "focus_handoff"):
            if key not in updated:
                continue
            previous = updated.pop(key)
            changes.append({"field": key, "before": previous, "after": None})
        if not changes:
            continue

        demotion = {
            "kind": "phase_focus_demotion",
            "demoted_at": demoted_at,
            "active_phase_id": active_phase_id,
            "active_phase_number": active_phase_number,
            "active_phase_dir": active_phase_dir,
            "target_path": rel_path,
            "target_phase_id": str(item.get("phase_id") or "").strip() or None,
            "target_phase_number": str(item.get("phase_number") or "").strip() or None,
            "target_phase_dir": canonicalize_write_path(str(item.get("phase_dir") or "").strip()) or None,
            "claims": list(item.get("claims") or []),
            "reason": "non_active_phase_claimed_active_or_default_focus",
            "before": _focus_snapshot(card),
            "after": _focus_snapshot(updated),
            "changes": changes,
            "archive_record_path": archive_record_rel,
        }
        demotions.append({**demotion, "card": updated, "body": body})

    if live and demotions:
        for demotion in demotions:
            rel_path = str(demotion["target_path"])
            note_path = state.REPO_ROOT / rel_path
            note_path.write_text(
                render_markdown_document(dict(demotion["card"]), str(demotion["body"])),
                encoding="utf-8",
            )
        archive_path = state.REPO_ROOT / archive_record_rel
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with archive_path.open("a", encoding="utf-8") as handle:
            for demotion in demotions:
                record = {
                    key: value
                    for key, value in demotion.items()
                    if key not in {"card", "body"}
                }
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    public_demotions = [
        {key: value for key, value in demotion.items() if key not in {"card", "body"}}
        for demotion in demotions
    ]
    next_commands: list[dict[str, str]] = []
    command_phase_ref = shlex.quote(str(phase_ref or phase_token or "__active__"))
    if public_demotions and not live:
        next_commands.append(
            {
                "command": (
                    f"python3 kernel.py --phase-demote-stale-focus {command_phase_ref} "
                    f"--phase-demote-limit {limit} --live"
                ),
                "reason": "Apply the previewed stale-focus demotion and append the archive receipt.",
            }
        )
    remaining_count = max(len(conflicts) - len(selected), 0)
    if remaining_count > 0 and (live or not public_demotions):
        next_commands.append(
            {
                "command": (
                    f"python3 kernel.py --phase-demote-stale-focus {command_phase_ref} "
                    "--phase-demote-limit 1 --live"
                ),
                "reason": "Continue demoting the next stale active/default focus claim after reviewing this receipt.",
            }
        )
    if phase_ref:
        next_commands.append(
            {
                "command": f"python3 kernel.py --phase {shlex.quote(phase_ref)}",
                "reason": "Reload lifecycle enforcement and confirm the stale-focus count changed as expected.",
            }
        )

    payload = {
        "kind": "kernel.phase_demote_stale_focus",
        "mode": "live" if live else "preview",
        "status": "applied" if live and public_demotions else "preview_ready" if public_demotions else "no_op",
        "phase": {
            "phase_id": phase_payload.get("phase_id"),
            "phase_number": phase_payload.get("phase_number"),
            "phase_dir": phase_payload.get("phase_dir"),
        },
        "explicit_active_phase": dict(explicit_active) if explicit_active else None,
        "archive_record_path": archive_record_rel,
        "conflict_count": len(conflicts),
        "selected_count": len(selected),
        "demotion_count": len(public_demotions),
        "remaining_conflict_count": remaining_count,
        "demotions": public_demotions,
        "live_required": bool(public_demotions) and not live,
        "warnings": list(result.warnings),
        "next": next_commands,
    }
    if live and public_demotions:
        payload["written"] = [
            {"path": item["target_path"], "kind": "focus_metadata_demotion"}
            for item in public_demotions
        ] + [{"path": archive_record_rel, "kind": "phase_focus_demotion_ledger"}]
    return emit_json(payload)


def cmd_add_phase(spec_path: str, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Preview or write one new phase or sub-phase scaffold from an explicit JSON spec instead of assembling the packet by hand.
    - Mechanism: Validate the requested spec path, delegate to `execute_phase_scaffold()`, attach the default promotion metadata, and emit the resulting scaffold payload.
    - Reads: The requested phase scaffold spec JSON plus scaffold helpers under `system.lib.phase_scaffold`.
    - Writes: Phase scaffold artifacts only when `live` is true.
    - Fails: Returns 1 when the spec path is missing or scaffold generation raises `ValueError`.
    - When-needed: Open when a new phase or sub-phase should be scaffolded from a prepared JSON spec through the kernel CLI.
    - Escalates-to: system/lib/phase_scaffold.py; system/lib/kernel/commands/navigate.py::cmd_new_phase; docs/synth_first_scaffold_contract.md
    - Navigation-group: kernel_lib
    """
    requested = str(spec_path or "").strip()
    if not requested:
        print("ERROR: --add-phase requires a JSON spec path", file=sys.stderr)
        return 1
    try:
        payload = execute_phase_scaffold(state.REPO_ROOT, requested, live=live)
        payload = _attach_scaffold_default_promotion(
            payload,
            live=live,
            source_command="add-phase",
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(payload)


def cmd_new_family(
    parent: str | None,
    number: str,
    title: str,
    seed_from: str | None = None,
    *,
    live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Preview or write a new phase-family root with its blackboard artifacts when a fresh family needs to be introduced into the note lattice.
    - Mechanism: Normalize the requested family number, title, and parent path, derive `family_dir`, build a family scaffold spec, and delegate to `execute_phase_family_scaffold_spec()`.
    - Reads: The requested parent, title, optional seed token, and family-scaffold helpers.
    - Writes: Family scaffold artifacts only when `live` is true.
    - Fails: Returns 1 when family-number/title normalization, parent resolution, or family scaffold execution raises `ValueError`.
    - When-needed: Open when a new family root should be scaffolded from CLI arguments rather than from a hand-authored family spec file.
    - Escalates-to: system/lib/phase_scaffold.py; system/lib/kernel/commands/navigate.py::cmd_add_workstream; docs/synth_first_scaffold_contract.md
    - Navigation-group: kernel_lib
    """
    try:
        family_number = _normalize_new_phase_number(number)
        family_title = _normalize_new_family_title(family_number, title)
        parent_label, parent_dir = _normalize_new_family_parent_path(parent, seed_from=seed_from)
        family_dir = canonicalize_write_path(f"{parent_dir}/{_new_family_dir_name(family_number, family_title)}")
        if not family_dir:
            raise ValueError("Could not derive family_dir for --new-family")
        spec = {
            "family_id": _new_phase_id(family_number),
            "family_number": family_number,
            "family_title": family_title,
            "family_dir": family_dir,
            "parent": parent_label,
        }
        seed_token = str(seed_from or "").strip()
        if seed_token:
            spec["raw_seed_source_path"] = seed_token
        payload = execute_phase_family_scaffold_spec(state.REPO_ROOT, spec, live=live)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = dict(payload)
    payload["requested"] = {
        "parent": str(parent or "").strip() or None,
        "number": family_number,
        "title": str(title or "").strip(),
        "seed_from": str(seed_from or "").strip() or None,
        "family_id": _new_phase_id(family_number),
    }
    return emit_json(payload)


def cmd_new_phase(
    parent: str,
    number: str,
    title: str,
    seed_path: str | None = None,
    *,
    goal: str | None = None,
    why_now: str | None = None,
    live: bool = False,
    bootstrap_via_bridge: bool = False,
    bridge_enabled: bool = False,
    bridge_provider: str | None = None,
    bridge_timeout_s: float = 0.0,
) -> int:
    """[ACTION]
    - Teleology: Preview or write a doctrine-backed phase packet from parent, number, and title so a new standard phase can enter the family with the expected synth-first scaffolding.
    - Mechanism: Normalize numbering, reconcile requested parent lineage against the requested phase number, derive `phase_id` and `phase_dir`, delegate to `execute_phase_scaffold_spec()`, attach default promotion metadata, and optionally prepare or run bridge bootstrap for the new phase.
    - Reads: Parent phase context, requested phase metadata, scaffold helpers, and optional bridge-bootstrap settings.
    - Writes: Phase scaffold artifacts only when `live` is true; may also invoke live bridge dock/bootstrap work when `bootstrap_via_bridge` is requested with valid bridge settings.
    - Fails: Returns 1 when normalization, scaffold execution, or optional bridge bootstrap raises `ValueError`, or when required live bridge flags are inconsistent.
    - When-needed: Open when a new doctrine-backed phase must be scaffolded from CLI arguments and may need immediate bridge bootstrap preparation.
    - Escalates-to: system/lib/phase_scaffold.py; system/lib/phase_dock.py; docs/synth_first_scaffold_contract.md
    - Navigation-group: kernel_lib
    """
    try:
        phase_number = _normalize_new_phase_number(number)
        phase_title = _normalize_new_phase_title(phase_number, title)
        parent_resolution = _normalize_new_phase_parent_path(parent, requested_phase_number=phase_number)
        parent_label = str(parent_resolution.get("parent_label") or "").strip()
        parent_dir = canonicalize_write_path(str(parent_resolution.get("parent_dir") or "").strip()) or ""
        parent_phase_id = str(parent_resolution.get("parent_phase_id") or "").strip() or None
        resolved_family_dir = canonicalize_write_path(str(parent_resolution.get("family_dir") or "").strip()) or ""
        phase_id = _new_phase_id(phase_number)
        phase_dir = canonicalize_write_path(f"{parent_dir}/{_new_phase_dir_name(phase_number, phase_title)}")
        if not phase_dir:
            raise ValueError("Could not derive phase_dir for --new-phase")
        family_dir = resolved_family_dir or phase_dir
        spec = {
            "phase_id": phase_id,
            "phase_number": phase_number,
            "phase_title": phase_title,
            "phase_dir": phase_dir,
            "parent": parent_label,
            "parent_phase_id": parent_phase_id,
            "parent_phase_dir": parent_dir if parent_phase_id else None,
            "family_dir": family_dir,
            "requested_goal": str(goal or "").strip() or None,
            "requested_problem_statement": str(why_now or "").strip() or None,
        }
        payload = execute_phase_scaffold_spec(state.REPO_ROOT, spec, live=live)
        payload = _attach_scaffold_default_promotion(
            payload,
            live=live,
            source_command="new-phase",
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = dict(payload)
    payload["requested"] = {
        "parent": str(parent or "").strip(),
        "number": phase_number,
        "title": str(title or "").strip(),
        "goal": str(goal or "").strip() or None,
        "why_now": str(why_now or "").strip() or None,
        "phase_id": phase_id,
        "parent_phase_id": parent_phase_id,
        "family_dir": family_dir,
    }
    payload["parent_resolution"] = dict(parent_resolution)
    parent_reason = str(parent_resolution.get("resolution_reason") or "").strip()
    if parent_reason and str(parent_resolution.get("resolution_kind") or "").strip() in {
        "phase_to_family_autolift",
        "phase_to_ancestor_autolift",
    }:
        warnings = list(payload.get("warnings") or [])
        if parent_reason not in warnings:
            warnings.append(parent_reason)
        payload["warnings"] = warnings
    if bootstrap_via_bridge:
        if not live:
            payload["bridge_bootstrap"] = {
                "status": "preview_ready",
                "phase_id": phase_id,
                "command": f"python3 kernel.py --phase-dock {shlex.quote(phase_id)} --dock-operation extract_subphase_seed --live",
            }
        else:
            if not bridge_enabled:
                print("ERROR: --bootstrap-via-bridge requires --bridge when used with --new-phase --live", file=sys.stderr)
                return 1
            if bridge_timeout_s <= 0:
                print("ERROR: --bridge-timeout-s must be > 0", file=sys.stderr)
                return 1
            navigator = KernelNavigation(state.REPO_ROOT)
            try:
                phase_entry = navigator._resolve_phase_entry(phase_id)
                payload["bridge_bootstrap"] = run_phase_dock(
                    state.REPO_ROOT,
                    phase_entry,
                    phase_entries=navigator.phase_entries,
                    operation="extract_subphase_seed",
                    consumer="bridge",
                    bridge_provider=bridge_provider,
                    bridge_timeout_s=bridge_timeout_s,
                    live=True,
                )
            except ValueError as exc:
                print(f"ERROR: phase bootstrap via bridge failed: {exc}", file=sys.stderr)
                return 1
    return emit_json(payload)


def cmd_activate_phase(phase_token: str | None = None, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Preview or apply activation of one resolved phase so downstream kernel and pipeline defaults point at the intended active phase.
    - Mechanism: Resolve the requested phase entry, derive its canonical family and phase paths, attach default-promotion metadata, compute whether activation changed anything, and emit the resulting activation payload.
    - Reads: Phase entries, scaffold promotion state, and the requested phase token or active-phase fallback.
    - Writes: Activation/default-promotion artifacts only when `live` is true.
    - Fails: Returns 1 when the phase token cannot be resolved, required family or phase paths are missing, or activation preparation raises `ValueError`.
    - When-needed: Open when a phase should become the active default for kernel navigation and downstream resume flows.
    - Escalates-to: system/lib/phase_activation.py; system/lib/kernel_navigation.py; pipeline_advance.py
    - Navigation-group: kernel_lib
    """
    try:
        _navigator, phase_entry = _resolve_phase_entry_for_lifecycle(phase_token)
        phase_dir = canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip()) or ""
        if not phase_dir:
            raise ValueError("Phase entry is missing phase_dir.")
        family_dir = (
            canonicalize_write_path(str(phase_entry.get("family_dir") or "").strip())
            or _discover_phase_family_dir(phase_dir)
            or ""
        )
        if not family_dir:
            raise ValueError("Could not resolve family_dir for phase activation.")

        payload: dict[str, Any] = {
            "kind": "kernel.activate_phase",
            "phase": {
                "phase_id": phase_entry.get("phase_id"),
                "phase_number": phase_entry.get("phase_number"),
                "phase_title": phase_entry.get("phase_title"),
                "phase_dir": phase_dir,
                "family_dir": family_dir,
                "synth_seed_markdown_path": canonicalize_write_path(f"{phase_dir}/synth_seed.md"),
            },
            "requested": {
                "phase": str(phase_token or "__active__").strip() or "__active__",
            },
        }
        payload = _attach_scaffold_default_promotion(
            payload,
            live=live,
            source_command="activate-phase",
        )
        default_writes = list(((payload.get("default_promotion") or {}).get("writes") or []))
        activation_changed = bool(((payload.get("family_activation") or {}).get("changed_fields") or []))
        changed = bool(default_writes) or activation_changed
        payload["mode"] = "live" if live else "preview"
        payload["status"] = (
            "applied"
            if live and changed
            else "preview_ready"
            if (not live and changed)
            else "no_op"
        )
        if not changed:
            payload["message"] = "Phase was already the active default."
        # Reflex: when activation actually changed live state, refresh the bootstrap
        # projection so agent_bootstrap_live.json + adapter live blocks stop carrying
        # the previous active phase. The env-gated try_refresh_after_controller_write
        # is the opt-in opportunistic path; here we want it on by default because the
        # operator just explicitly changed the active phase. Failure is swallowed to
        # avoid breaking activation; the residual surfaces in the next --entry call.
        bootstrap_refresh: dict[str, Any] = {"attempted": False}
        if live and changed:
            bootstrap_refresh["attempted"] = True
            try:
                from system.lib.agent_bootstrap_projection import run_projection as _run_bootstrap_projection
                _run_bootstrap_projection(
                    repo_root,
                    dry_run=False,
                    write_agents=True,
                    source_event="cmd_activate_phase",
                )
                bootstrap_refresh["ok"] = True
            except Exception as exc:  # noqa: BLE001
                bootstrap_refresh["ok"] = False
                bootstrap_refresh["error"] = f"{type(exc).__name__}: {exc}"
        payload["bootstrap_refresh"] = bootstrap_refresh
        payload["next"] = [
            {
                "command": f"python3 kernel.py --phase {shlex.quote(str(phase_entry.get('phase_id') or phase_dir))}",
                "reason": "Reload the resolved active phase packet after activation.",
            },
            {
                "command": "python3 pipeline_advance.py --write-resume",
                "reason": "Refresh the downstream resume packet against the activated phase.",
            },
            {
                "command": "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py",
                "reason": "Rebuild bootstrap projection if the inline reflex above did not run or failed.",
            },
        ]
        return emit_json(payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _seed_substrate_paths(artifacts: Mapping[str, str], *, substrate: str) -> tuple[str, str, str]:
    token = str(substrate or "raw_seed").strip()
    return (
        str(artifacts.get(f"{token}_path") or "").strip(),
        str(artifacts.get(f"{token}_json_path") or "").strip(),
        str(artifacts.get(f"{token}_snapshot_path") or "").strip(),
    )


def _raw_seed_compressed_projection_summary(
    *,
    family_payload: Mapping[str, Any],
    family_token: str | None,
    live: bool,
) -> dict[str, Any]:
    family_ref = str(
        family_payload.get("family_number")
        or family_payload.get("family_id")
        or family_token
        or ""
    ).strip()
    if not family_ref:
        return {
            "status": "skipped",
            "reason": "missing_family_ref",
        }
    if not live:
        return {
            "status": "planned",
            "reason": "preview_does_not_write_derived_projection",
            "family": family_ref,
        }

    try:
        from system.lib.raw_seed_compressed_projection import build_raw_seed_compressed_projection

        manifest = build_raw_seed_compressed_projection(
            family=family_ref,
            repo_root=state.REPO_ROOT,
            write=True,
        )
    except Exception as exc:
        return {
            "status": "error",
            "family": family_ref,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

    return {
        "status": "written",
        "family": family_ref,
        "output_path": str(manifest.get("output_path") or ""),
        "manifest_path": str((manifest.get("paths") or {}).get("compressed_manifest") or ""),
        "projection_id": str(manifest.get("projection_id") or ""),
        "actual_bytes": int(manifest.get("actual_bytes") or 0),
        "ok": bool(manifest.get("ok")),
        "coverage": manifest.get("coverage") or {},
    }


def _sync_seed_substrate(family_token: str | None, *, substrate: str, live: bool = False) -> int:
    try:
        family_entry = _resolve_family_entry_for_raw_seed(family_token)
        marker_path = state.REPO_ROOT / str(family_entry.get("marker_path") or "")
        if not marker_path.exists():
            raise ValueError(f"phase_family.json not found: {str(family_entry.get('marker_path') or '').strip()}")
        family_payload = safe_load_json(marker_path)
        if not isinstance(family_payload, dict):
            raise ValueError(f"Invalid phase_family.json: {state.rel(marker_path)}")
        artifacts = _family_seed_artifacts(family_payload, family_entry)
        family_dir = artifacts["family_dir"]
        markdown_rel, json_rel, snapshot_rel = _seed_substrate_paths(artifacts, substrate=substrate)
        if not markdown_rel:
            raise ValueError(f"Could not derive {substrate}.md path.")
        if not json_rel:
            raise ValueError(f"Could not derive {substrate}.json path.")
        if not snapshot_rel:
            raise ValueError(f"Could not derive {substrate}.snapshot.md path.")

        markdown_path = state.REPO_ROOT / markdown_rel
        json_path = state.REPO_ROOT / json_rel
        snapshot_path = state.REPO_ROOT / snapshot_rel

        if substrate == "raw_seed" and not markdown_path.exists():
            raise ValueError(f"raw_seed.md not found: {markdown_rel}")
        existing_text = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
        existing_payload = load_raw_seed_payload(json_path) if json_path.exists() else {}
        normalized = build_raw_seed_payload(
            raw_seed_text=existing_text,
            raw_seed_path=markdown_rel,
            family_payload={
                **family_payload,
                "family_dir": family_dir,
                "raw_seed_path": artifacts["raw_seed_path"],
                "raw_seed_json_path": artifacts["raw_seed_json_path"],
                "agent_seed_path": artifacts["agent_seed_path"],
                "agent_seed_json_path": artifacts["agent_seed_json_path"],
            },
            existing_payload=existing_payload,
            substrate=substrate,
        )
        warnings: list[dict[str, Any]] = []
        if substrate == "raw_seed":
            for section in normalized.get("sections") or []:
                if not isinstance(section, Mapping):
                    continue
                heading = str(section.get("heading") or "").strip()
                if not _is_agent_heading_token(heading):
                    continue
                paragraph_ids = [
                    str(item).strip()
                    for item in (section.get("paragraph_ids") or [])
                    if str(item).strip()
                ]
                warnings.append(
                    {
                        "kind": "agent_heading_in_raw_seed",
                        "heading": heading,
                        "section_id": str(section.get("id") or "").strip(),
                        "paragraph_id": paragraph_ids[0] if paragraph_ids else None,
                        "message": "Agent-authored headings inside raw_seed.md are contract violations.",
                        "recommended_command": (
                            f"python3 kernel.py --migrate-agent-section {paragraph_ids[0]}"
                            if paragraph_ids
                            else None
                        ),
                    }
                )
        term_ledger = normalized.pop("_ephemeral_term_ledger", None) if substrate == "raw_seed" else None
        rendered_markdown = render_raw_seed_markdown(normalized, substrate=substrate)
        revision_rows = [
            paragraph
            for paragraph in normalized.get("paragraphs", [])
            if isinstance(paragraph, Mapping)
            and isinstance(paragraph.get("sync_provenance"), Mapping)
            and str((paragraph.get("sync_provenance") or {}).get("status") or "") == "modified_after_sync"
        ]
        compressed_projection: dict[str, Any] | None = None

        if live:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(canonical_json_text(normalized), encoding="utf-8")
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(existing_text, encoding="utf-8")
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(rendered_markdown, encoding="utf-8")
            if substrate == "raw_seed":
                family_payload["raw_seed_json_path"] = json_rel
                family_payload["raw_seed_snapshot_path"] = snapshot_rel
                family_payload["raw_seed_principles_path"] = (
                    canonicalize_write_path(str(family_payload.get("raw_seed_principles_path") or "").strip())
                    or raw_seed_principles_path_for_family(family_dir)
                )
            else:
                family_payload["agent_seed_path"] = markdown_rel
                family_payload["agent_seed_json_path"] = json_rel
                family_payload["agent_seed_snapshot_path"] = snapshot_rel
            marker_path.write_text(canonical_json_text(family_payload), encoding="utf-8")
            if term_ledger:
                ledger_rel = raw_seed_term_ledger_path_for_family(family_dir)
                if ledger_rel:
                    ledger_path = state.REPO_ROOT / ledger_rel
                    try:
                        ledger_path.parent.mkdir(parents=True, exist_ok=True)
                        ledger_path.write_text(canonical_json_text(term_ledger), encoding="utf-8")
                    except OSError:
                        pass
            if substrate == "raw_seed":
                compressed_projection = _raw_seed_compressed_projection_summary(
                    family_payload=family_payload,
                    family_token=family_token,
                    live=live,
                )
        elif substrate == "raw_seed":
            compressed_projection = _raw_seed_compressed_projection_summary(
                family_payload=family_payload,
                family_token=family_token,
                live=live,
            )

        payload = {
            "kind": f"kernel.sync_{substrate}",
            "mode": "live" if live else "preview",
            "status": "applied" if live else "preview_ready",
            "family": {
                "family_id": family_payload.get("family_id"),
                "family_number": family_payload.get("family_number"),
                "family_title": family_payload.get("family_title"),
                "family_dir": family_dir,
                f"{substrate}_path": markdown_rel,
                f"{substrate}_json_path": json_rel,
                f"{substrate}_snapshot_path": snapshot_rel,
            },
            "writes": [
                {"path": markdown_rel, "kind": f"{substrate}_note"},
                {"path": json_rel, "kind": f"{substrate}_registry"},
                {"path": snapshot_rel, "kind": f"{substrate}_snapshot"},
                *(
                    [{"path": raw_seed_term_ledger_path_for_family(family_dir), "kind": "raw_seed_term_ledger"}]
                    if substrate == "raw_seed" and term_ledger and raw_seed_term_ledger_path_for_family(family_dir)
                    else []
                ),
                {"path": state.rel(marker_path), "kind": "phase_family_marker"},
                *(
                    [
                        {"path": str(compressed_projection.get("output_path") or ""), "kind": "raw_seed_compressed_markdown"},
                        {"path": str(compressed_projection.get("manifest_path") or ""), "kind": "raw_seed_compressed_manifest"},
                    ]
                    if substrate == "raw_seed"
                    and compressed_projection
                    and compressed_projection.get("status") == "written"
                    else []
                ),
            ],
            "summary": {
                "sections": int((normalized.get("document") or {}).get("total_sections") or 0),
                "paragraphs": int((normalized.get("document") or {}).get("total_paragraphs") or 0),
                "notes": len(normalized.get("notes") or []),
                "rendered_markdown_chars": len(rendered_markdown),
                "modified_after_sync_paragraphs": len(revision_rows),
            },
            "standards": {
                "authority_index": OBSERVE_APPLY_AUTHORITY_INDEX_PATH,
                substrate: (
                    OBSERVE_APPLY_STANDARD_PATHS.get(substrate)
                    if substrate in OBSERVE_APPLY_STANDARD_PATHS
                    else f"codex/standards/observe_apply/std_{substrate}.json"
                ),
                "phase_family": OBSERVE_APPLY_STANDARD_PATHS["phase_family"],
            },
        }
        if compressed_projection is not None:
            payload["raw_seed_compressed_projection"] = compressed_projection
            if compressed_projection.get("status") == "error":
                payload.setdefault("warnings", []).append(
                    {
                        "kind": "raw_seed_compressed_projection_refresh_failed",
                        "message": compressed_projection.get("message"),
                        "error_type": compressed_projection.get("error_type"),
                    }
                )
        if revision_rows:
            payload["modified_after_sync"] = [
                {
                    "paragraph_id": str(paragraph.get("id") or ""),
                    "previous_fingerprint": str((paragraph.get("sync_provenance") or {}).get("previous_fingerprint") or ""),
                    "current_fingerprint": str((paragraph.get("sync_provenance") or {}).get("current_fingerprint") or ""),
                    "revision_count": int((paragraph.get("sync_provenance") or {}).get("revision_count") or 0),
                }
                for paragraph in revision_rows
            ]
        if warnings:
            payload.setdefault("warnings", []).extend(warnings)
        return emit_json(payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_sync_raw_seed(family_token: str | None = None, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Recompile one family's raw-seed substrate so markdown, JSON, snapshot, and companion raw-seed artifacts stay aligned.
    - Mechanism: Resolve the requested family, normalize raw-seed paths, rebuild the raw-seed payload, render markdown, and optionally persist the JSON, markdown, snapshot, marker, and term-ledger artifacts.
    - Reads: Phase-family marker data, existing raw-seed markdown, and raw-seed registry helpers.
    - Writes: Raw-seed JSON, markdown, snapshot, phase-family marker, and optional term-ledger artifacts only when `live` is true.
    - Fails: Returns 1 when family resolution fails, required raw-seed paths are missing, or raw-seed compilation raises `ValueError`.
    - When-needed: Open when a family's `raw_seed.md` must be synchronized back into its JSON-first substrate and companion artifacts.
    - Escalates-to: system/lib/raw_seed_registry.py; docs/synth_first_scaffold_contract.md; system/lib/kernel/commands/navigate.py::cmd_resolve_raw_seed_ref
    - Navigation-group: kernel_lib
    """
    return _sync_seed_substrate(family_token, substrate="raw_seed", live=live)


def cmd_sync_agent_seed(family_token: str | None = None, *, live: bool = False) -> int:
    return _sync_seed_substrate(family_token, substrate="agent_seed", live=live)


def cmd_resolve_raw_seed_ref(family_token: str, ref: str) -> int:
    """[ACTION]
    - Teleology: Resolve one raw-seed reference token into its concrete family paragraph or section payload without opening the full raw-seed artifact by hand.
    - Mechanism: Resolve the requested family, load its raw-seed payload, resolve the requested reference through `resolve_raw_seed_ref()`, and emit the resolved target metadata.
    - Reads: Family marker metadata, raw-seed JSON, and the requested reference token.
    - Writes: None.
    - Fails: Returns 1 when the family cannot be resolved, the raw-seed payload is missing or invalid, or the requested reference cannot be resolved.
    - When-needed: Open when a raw-seed paragraph or section reference must be resolved deterministically for navigation, authoring, or observe-plan context.
    - Escalates-to: system/lib/raw_seed_registry.py; system/lib/kernel_navigation.py; system/lib/kernel/commands/navigate.py::cmd_sync_raw_seed
    - Navigation-group: kernel_lib
    """
    try:
        family_entry = _resolve_family_entry_for_raw_seed(family_token)
        marker_path = state.REPO_ROOT / str(family_entry.get("marker_path") or "")
        family_payload = safe_load_json(marker_path)
        if not isinstance(family_payload, dict):
            raise ValueError(f"Invalid phase_family.json: {state.rel(marker_path)}")
        family_dir = canonicalize_write_path(str(family_payload.get("family_dir") or family_entry.get("family_dir") or "").strip()) or ""
        raw_seed_json_rel = canonicalize_write_path(str(family_payload.get("raw_seed_json_path") or "").strip()) or raw_seed_json_path_for_family(family_dir)
        if not raw_seed_json_rel:
            raise ValueError("Could not derive raw_seed.json path.")
        raw_seed_json_path = state.REPO_ROOT / raw_seed_json_rel
        payload = safe_load_json(raw_seed_json_path) if raw_seed_json_path.exists() else None
        if not isinstance(payload, dict):
            family_payload["raw_seed_json_path"] = raw_seed_json_rel
            payload = build_raw_seed_payload_for_family(state.REPO_ROOT, family_payload)
        resolved = resolve_raw_seed_ref(payload, ref)
        if resolved is None:
            raise ValueError(f"Could not resolve raw seed ref: {ref}")
        return emit_json(
            {
                "kind": "kernel.resolve_raw_seed_ref",
                "family": {
                    "family_id": family_payload.get("family_id"),
                    "family_number": family_payload.get("family_number"),
                    "family_title": family_payload.get("family_title"),
                    "family_dir": family_dir,
                    "raw_seed_json_path": raw_seed_json_rel,
                },
                "requested": {
                    "family": family_token,
                    "ref": ref,
                },
                "resolution": resolved,
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_annotate_raw_seed(family_token: str, ref: str, field: str, value: str, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Preview or apply one targeted raw-seed field annotation so section or paragraph metadata can be refined without rebuilding the entire family payload by hand.
    - Mechanism: Resolve the requested family, load or rebuild its raw-seed payload, apply `annotate_raw_seed_payload()` to the requested ref and field, and optionally persist the updated raw-seed JSON.
    - Reads: Family marker metadata, raw-seed JSON when present, and the requested annotation tuple (`ref`, `field`, `value`).
    - Writes: The family's `raw_seed.json` only when `live` is true.
    - Fails: Returns 1 when family resolution fails, the raw-seed path cannot be derived, or the requested annotation target is invalid.
    - When-needed: Open when one raw-seed paragraph or section field needs a bounded annotation that must survive later `--sync-raw-seed` runs.
    - Escalates-to: system/lib/raw_seed_registry.py; system/lib/kernel/commands/navigate.py::cmd_sync_raw_seed; system/lib/kernel_navigation.py
    - Navigation-group: kernel_lib
    """
    try:
        family_entry = _resolve_family_entry_for_raw_seed(family_token)
        marker_path = state.REPO_ROOT / str(family_entry.get("marker_path") or "")
        family_payload = safe_load_json(marker_path)
        if not isinstance(family_payload, dict):
            raise ValueError(f"Invalid phase_family.json: {state.rel(marker_path)}")
        family_dir = canonicalize_write_path(str(family_payload.get("family_dir") or family_entry.get("family_dir") or "").strip()) or ""
        raw_seed_json_rel = canonicalize_write_path(str(family_payload.get("raw_seed_json_path") or "").strip()) or raw_seed_json_path_for_family(family_dir)
        if not raw_seed_json_rel:
            raise ValueError("Could not derive raw_seed.json path.")
        raw_seed_json_path_obj = state.REPO_ROOT / raw_seed_json_rel
        existing = load_raw_seed_payload(raw_seed_json_path_obj) if raw_seed_json_path_obj.exists() else None
        if not isinstance(existing, dict) or not existing:
            family_payload["raw_seed_json_path"] = raw_seed_json_rel
            existing = build_raw_seed_payload_for_family(state.REPO_ROOT, family_payload)
        updated = annotate_raw_seed_payload(existing, ref, field, value)
        if live:
            raw_seed_json_path_obj.parent.mkdir(parents=True, exist_ok=True)
            raw_seed_json_path_obj.write_text(canonical_json_text(updated), encoding="utf-8")
        return emit_json(
            {
                "kind": "kernel.annotate_raw_seed",
                "mode": "live" if live else "preview",
                "status": "applied" if live else "preview_ready",
                "family": {
                    "family_id": family_payload.get("family_id"),
                    "family_dir": family_dir,
                    "raw_seed_json_path": raw_seed_json_rel,
                },
                "annotation": {
                    "ref": ref,
                    "field": field,
                    "value": value,
                },
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _write_atomic_text(path: Path, text: str, *, prefix: str) -> None:
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=prefix,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    try:
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _parse_captured_json_output(text: str) -> dict[str, Any]:
    payload = str(text or "").strip()
    if not payload:
        return {}
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        for line in reversed(payload.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                continue
            break
        else:
            raise
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _seed_root_heading(*, substrate: str, family_payload: Mapping[str, Any], family_entry: Mapping[str, Any]) -> str:
    family_number = str(
        family_payload.get("family_number")
        or family_payload.get("family_id")
        or family_entry.get("family_number")
        or family_entry.get("family_id")
        or ""
    ).strip()
    if not family_number:
        return ""
    title = "Raw Seed" if substrate == "raw_seed" else "Agent Seed"
    return f"# Phase {family_number} {title}"


def _append_seed_substrate(
    family_token: str,
    text: str,
    *,
    substrate: str,
    heading: str | None = None,
    auto_sync: bool = True,
    live: bool = False,
) -> int:
    import hashlib
    import io

    body = (text or "").strip()
    if not body:
        print("ERROR: Content is empty after stripping whitespace.", file=sys.stderr)
        return 1
    if substrate == "raw_seed":
        if heading and _is_agent_heading_token(heading):
            print(f"ERROR: {AGENT_SEED_REJECTION_MESSAGE}", file=sys.stderr)
            return 1
        first_line = _first_nonempty_line(body)
        if _is_agent_heading_line(first_line):
            print(f"ERROR: {AGENT_SEED_REJECTION_MESSAGE}", file=sys.stderr)
            return 1

    try:
        family_entry = _resolve_family_entry_for_raw_seed(family_token)
        marker_path = state.REPO_ROOT / str(family_entry.get("marker_path") or "")
        if not marker_path.exists():
            raise ValueError(f"phase_family.json not found: {str(family_entry.get('marker_path') or '').strip()}")
        family_payload = safe_load_json(marker_path)
        if not isinstance(family_payload, dict):
            raise ValueError(f"Invalid phase_family.json: {state.rel(marker_path)}")
        artifacts = _family_seed_artifacts(family_payload, family_entry)
        family_dir = artifacts["family_dir"]
        markdown_rel, _, snapshot_rel = _seed_substrate_paths(artifacts, substrate=substrate)
        if not markdown_rel:
            raise ValueError(f"Could not derive {substrate}.md path.")
        markdown_path = state.REPO_ROOT / markdown_rel

        lines: list[str] = []
        if heading:
            lines.extend([f"## {heading.strip()}", ""])
        if substrate == "raw_seed":
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            lines.extend([f"<!-- appended {ts} -->", ""])
        lines.append(body)
        append_block = "\n".join(lines).rstrip() + "\n"
        fingerprint = hashlib.sha1(append_block.strip().encode("utf-8")).hexdigest()[:12]
        existing_text = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""

        if not live:
            return emit_json(
                {
                    "kind": f"kernel.append_{substrate}",
                    "mode": "preview",
                    "status": "preview_ready",
                    "family": {
                        "family_id": family_payload.get("family_id"),
                        "family_dir": family_dir,
                        f"{substrate}_path": markdown_rel,
                    },
                    "append": {
                        "fingerprint": fingerprint,
                        "lines": len(append_block.splitlines()),
                        "chars": len(append_block),
                        "heading": heading,
                        "preview": append_block[:500] + ("..." if len(append_block) > 500 else ""),
                    },
                    "auto_sync": auto_sync,
                }
            )

        root_heading = _seed_root_heading(substrate=substrate, family_payload=family_payload, family_entry=family_entry)
        new_content = existing_text
        if not new_content.strip() and root_heading:
            new_content = f"{root_heading}\n\n"
        separator = "\n\n" if new_content and not new_content.endswith("\n\n") else ("\n" if new_content and not new_content.endswith("\n") else "")
        new_content = new_content + separator + append_block.rstrip() + "\n"

        if snapshot_rel:
            snapshot_path = state.REPO_ROOT / snapshot_rel
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(existing_text, encoding="utf-8")
        _write_atomic_text(markdown_path, new_content, prefix=f".{substrate}_append_")

        result: dict[str, Any] = {
            "kind": f"kernel.append_{substrate}",
            "mode": "live",
            "status": "appended",
            "family": {
                "family_id": family_payload.get("family_id"),
                "family_dir": family_dir,
                f"{substrate}_path": markdown_rel,
            },
            "append": {
                "fingerprint": fingerprint,
                "lines": len(append_block.splitlines()),
                "chars": len(append_block),
                "heading": heading,
                "size_before": len(existing_text.encode("utf-8")),
                "size_after": markdown_path.stat().st_size,
            },
        }
        if auto_sync:
            old_stdout = sys.stdout
            try:
                sys.stdout = io.StringIO()
                if substrate == "raw_seed":
                    sync_rc = cmd_sync_raw_seed(family_token, live=True)
                else:
                    sync_rc = cmd_sync_agent_seed(family_token, live=True)
                sync_out = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            result[f"sync_{substrate}"] = {"returncode": sync_rc}
            try:
                sync_data = _parse_captured_json_output(sync_out)
                result[f"sync_{substrate}"]["summary"] = sync_data.get("summary", {})
                if sync_data.get("warnings"):
                    result[f"sync_{substrate}"]["warnings"] = sync_data.get("warnings")
            except json.JSONDecodeError:
                pass
            if substrate == "raw_seed":
                try:
                    sys.stdout = io.StringIO()
                    from system.lib.kernel.commands.substrate import cmd_sync_raw_seed_index

                    index_rc = cmd_sync_raw_seed_index(family_token, live=True)
                finally:
                    sys.stdout = old_stdout
                result["sync_raw_seed_index"] = {"returncode": index_rc}
        return emit_json(result)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_append_raw_seed(
    family_token: str,
    text: str,
    *,
    heading: str | None = None,
    auto_sync: bool = True,
    live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Append new content to a family's raw_seed.md and optionally re-sync JSON and index in one atomic operation.
    - Mechanism: Resolve the family, build a content block with optional heading and timestamp, dedup-check against existing content, write a snapshot backup, atomically append to raw_seed.md, and optionally chain --sync-raw-seed + --sync-raw-seed-index.
    - Reads: Phase-family marker data, existing raw_seed.md for dedup checking.
    - Writes: raw_seed.md (append-only), raw_seed.snapshot.md (backup), and when auto_sync is true also raw_seed.json, re-rendered raw_seed.md, and raw_seed_index.json — all only when `live` is true.
    - Fails: Returns 1 when family resolution fails, content is empty, or the write path cannot be resolved.
    - When-needed: Open when new raw-seed content (session voice, brainstorm, pasted transcript) must enter the raw-seed substrate and become navigable via JSON annotations.
    - Escalates-to: system/lib/kernel/commands/navigate.py::cmd_sync_raw_seed; system/lib/raw_seed_registry.py
    - Navigation-group: kernel_lib
    """
    return _append_seed_substrate(
        family_token,
        text,
        substrate="raw_seed",
        heading=heading,
        auto_sync=auto_sync,
        live=live,
    )


def cmd_append_agent_seed(
    family_token: str,
    text: str,
    *,
    author: str,
    gesture: str | None = None,
    live: bool = False,
) -> int:
    literals, regex = _supported_agent_seed_authors()
    author_token = str(author or "").strip()
    if not author_token:
        print("ERROR: --author is required for --append-agent-seed.", file=sys.stderr)
        return 1
    if author_token not in literals and not re.match(regex, author_token):
        print(f"ERROR: Unsupported agent author: {author_token}", file=sys.stderr)
        return 1
    heading = f"{author_token} {datetime.now(timezone.utc).strftime('%Y %m %d')} {_normalize_gesture_text(gesture or _derive_agent_seed_gesture(text))}"
    return _append_seed_substrate(
        family_token,
        text,
        substrate="agent_seed",
        heading=heading,
        auto_sync=True,
        live=live,
    )


def cmd_migrate_agent_section(paragraph_id: str, *, live: bool = False) -> int:
    try:
        family_entry = _resolve_family_entry_for_raw_seed(None)
        marker_path = state.REPO_ROOT / str(family_entry.get("marker_path") or "")
        family_payload = safe_load_json(marker_path)
        if not isinstance(family_payload, dict):
            raise ValueError(f"Invalid phase_family.json: {state.rel(marker_path)}")
        artifacts = _family_seed_artifacts(family_payload, family_entry)
        family_dir = artifacts["family_dir"]

        raw_seed_md_path = state.REPO_ROOT / artifacts["raw_seed_path"]
        if not raw_seed_md_path.exists():
            raise ValueError(f"raw_seed.md not found: {artifacts['raw_seed_path']}")
        raw_seed_text = raw_seed_md_path.read_text(encoding="utf-8")
        raw_seed_payload = build_raw_seed_payload(
            raw_seed_text=raw_seed_text,
            raw_seed_path=artifacts["raw_seed_path"],
            family_payload={**family_payload, **artifacts},
            existing_payload=load_raw_seed_payload(state.REPO_ROOT / artifacts["raw_seed_json_path"]),
            substrate="raw_seed",
        )
        paragraph = next(
            (
                dict(item)
                for item in (raw_seed_payload.get("paragraphs") or [])
                if isinstance(item, Mapping) and str(item.get("id") or "").strip() == str(paragraph_id or "").strip()
            ),
            None,
        )
        if not paragraph:
            raise ValueError(f"Could not resolve raw-seed paragraph: {paragraph_id}")
        section_id = str(paragraph.get("section_id") or "").strip()
        section = next(
            (
                dict(item)
                for item in (raw_seed_payload.get("sections") or [])
                if isinstance(item, Mapping) and str(item.get("id") or "").strip() == section_id
            ),
            None,
        )
        if not section:
            raise ValueError(f"Could not resolve owning section for paragraph: {paragraph_id}")
        old_heading = str(section.get("heading") or "").strip()
        if not _is_agent_heading_token(old_heading):
            raise ValueError("Owning section is not an agent-authored heading and cannot be migrated.")

        heading_parts = _parse_historical_agent_heading(old_heading)
        new_heading = f"{heading_parts['author']} {heading_parts['date_token']} {heading_parts['gesture']}".strip()
        raw_paragraphs_by_id = {
            str(item.get("id") or "").strip(): dict(item)
            for item in (raw_seed_payload.get("paragraphs") or [])
            if isinstance(item, Mapping) and str(item.get("id") or "").strip()
        }
        migrated_paragraphs = [
            raw_paragraphs_by_id[pid]
            for pid in [str(item).strip() for item in (section.get("paragraph_ids") or []) if str(item).strip()]
            if pid in raw_paragraphs_by_id
        ]
        if not migrated_paragraphs:
            raise ValueError("Agent-authored section has no paragraphs to migrate.")

        migrated_lines: list[str] = [f"## {new_heading}", ""]
        for idx, item in enumerate(migrated_paragraphs):
            migrated_lines.extend(str(item.get("raw_markdown") or "").splitlines() or [""])
            references = [
                str(ref).strip()
                for ref in (item.get("references") or [])
                if str(ref).strip()
            ]
            if references:
                migrated_lines.append("")
                migrated_lines.extend(references)
            if idx != len(migrated_paragraphs) - 1:
                migrated_lines.append("")
                migrated_lines.append("")
        migrated_block = "\n".join(migrated_lines).rstrip() + "\n"

        agent_seed_path = state.REPO_ROOT / artifacts["agent_seed_path"]
        existing_agent_text = agent_seed_path.read_text(encoding="utf-8") if agent_seed_path.exists() else ""
        root_heading = _seed_root_heading(substrate="agent_seed", family_payload=family_payload, family_entry=family_entry)
        next_agent_text = existing_agent_text
        if not next_agent_text.strip() and root_heading:
            next_agent_text = f"{root_heading}\n\n"
        separator = "\n\n" if next_agent_text and not next_agent_text.endswith("\n\n") else ("\n" if next_agent_text and not next_agent_text.endswith("\n") else "")
        next_agent_text = next_agent_text + separator + migrated_block
        prospective_agent_payload = build_raw_seed_payload(
            raw_seed_text=next_agent_text,
            raw_seed_path=artifacts["agent_seed_path"],
            family_payload={**family_payload, **artifacts},
            existing_payload=load_raw_seed_payload(state.REPO_ROOT / artifacts["agent_seed_json_path"]),
            substrate="agent_seed",
        )
        matching_sections = [
            dict(item)
            for item in (prospective_agent_payload.get("sections") or [])
            if isinstance(item, Mapping) and str(item.get("heading") or "").strip() == new_heading
        ]
        if not matching_sections:
            raise ValueError("Could not locate migrated section in prospective agent_seed payload.")
        new_section = sorted(
            matching_sections,
            key=lambda item: (int(item.get("line_start") or 0), str(item.get("id") or "")),
        )[-1]
        new_paragraph_ids = [str(item).strip() for item in (new_section.get("paragraph_ids") or []) if str(item).strip()]
        if len(new_paragraph_ids) != len(migrated_paragraphs):
            raise ValueError("Paragraph count changed during migration preview.")

        lines = raw_seed_text.splitlines(keepends=True)
        ordered_sections = [
            dict(item)
            for item in sorted(
                [s for s in (raw_seed_payload.get("sections") or []) if isinstance(s, Mapping) and str(s.get("id") or "").strip() != "sec_root"],
                key=lambda item: (int(item.get("line_start") or 0), str(item.get("id") or "")),
            )
        ]
        section_index = next(
            (index for index, item in enumerate(ordered_sections) if str(item.get("id") or "").strip() == section_id),
            None,
        )
        if section_index is None:
            raise ValueError("Could not locate section ordering for migration.")
        start = max(0, int(section.get("line_start") or 1) - 1)
        if start > 0 and lines[start - 1].strip().startswith("<!-- RAW_SEED_SECTION"):
            start -= 1
        while start > 0 and not lines[start - 1].strip():
            start -= 1
        if section_index + 1 < len(ordered_sections):
            next_section = ordered_sections[section_index + 1]
            end = max(0, int(next_section.get("line_start") or 1) - 1)
            if end > 0 and lines[end - 1].strip().startswith("<!-- RAW_SEED_SECTION"):
                end -= 1
        else:
            end = len(lines)
        next_raw_seed_text = "".join([*lines[:start], *lines[end:]]).rstrip() + "\n"

        old_section_id = str(section.get("id") or "").strip()
        section_map = {old_section_id: str(new_section.get("id") or "").strip()}
        paragraph_map = {
            str(old_item.get("id") or "").strip(): new_paragraph_ids[index]
            for index, old_item in enumerate(migrated_paragraphs)
        }
        ledger_path = _migration_ledger_path_for_family(family_payload)
        ledger = _load_or_init_migration_ledger(ledger_path, family_payload=family_payload)
        preview_payload = {
            "kind": "kernel.migrate_agent_section",
            "mode": "live" if live else "preview",
            "status": "applied" if live else "preview_ready",
            "family": {
                "family_id": family_payload.get("family_id"),
                "family_number": family_payload.get("family_number"),
                "family_title": family_payload.get("family_title"),
                "family_dir": family_dir,
                "raw_seed_path": artifacts["raw_seed_path"],
                "agent_seed_path": artifacts["agent_seed_path"],
            },
            "migration": {
                "source_section_id": old_section_id,
                "source_heading": old_heading,
                "target_section_id": section_map[old_section_id],
                "target_heading": new_heading,
                "section_id_map": section_map,
                "paragraph_id_map": paragraph_map,
            },
            "writes": [
                {"path": artifacts["agent_seed_path"], "kind": "agent_seed_note"},
                {"path": artifacts["raw_seed_path"], "kind": "raw_seed_note"},
                {"path": state.rel(ledger_path), "kind": "agent_seed_migration_ledger"},
            ],
        }
        if not live:
            return emit_json(preview_payload)

        _write_atomic_text(agent_seed_path, next_agent_text, prefix=".agent_seed_migration_")
        _write_atomic_text(raw_seed_md_path, next_raw_seed_text, prefix=".raw_seed_migration_")
        old_stdout = sys.stdout
        try:
            sys.stdout = io.StringIO()
            agent_sync_rc = cmd_sync_agent_seed(None, live=True)
            agent_sync_out = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        if agent_sync_rc != 0:
            raise ValueError("agent_seed sync failed during migration.")
        try:
            sys.stdout = io.StringIO()
            raw_sync_rc = cmd_sync_raw_seed(None, live=True)
            raw_sync_out = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        if raw_sync_rc != 0:
            raise ValueError("raw_seed sync failed during migration.")
        try:
            sys.stdout = io.StringIO()
            from system.lib.kernel.commands.substrate import cmd_sync_raw_seed_index

            raw_index_rc = cmd_sync_raw_seed_index(None, live=True)
        finally:
            sys.stdout = old_stdout

        agent_sync_payload = _parse_captured_json_output(agent_sync_out)
        raw_sync_payload = _parse_captured_json_output(raw_sync_out)
        ledger_section_map = dict(ledger.get("section_id_map") or {})
        ledger_paragraph_map = dict(ledger.get("paragraph_id_map") or {})
        ledger_section_map.update(section_map)
        ledger_paragraph_map.update(paragraph_map)
        ledger["section_id_map"] = ledger_section_map
        ledger["paragraph_id_map"] = ledger_paragraph_map
        records = list(ledger.get("records") or [])
        records.append(
            {
                "migrated_at": datetime.now(timezone.utc).isoformat(),
                "source_section_id": old_section_id,
                "source_heading": old_heading,
                "target_section_id": section_map[old_section_id],
                "target_heading": new_heading,
                "paragraph_id_map": paragraph_map,
            }
        )
        ledger["records"] = records
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(canonical_json_text(ledger), encoding="utf-8")

        preview_payload["migration"]["agent_sync_summary"] = agent_sync_payload.get("summary", {})
        preview_payload["migration"]["raw_sync_summary"] = raw_sync_payload.get("summary", {})
        preview_payload["sync_agent_seed"] = {"returncode": agent_sync_rc}
        preview_payload["sync_raw_seed"] = {"returncode": raw_sync_rc}
        preview_payload["sync_raw_seed_index"] = {"returncode": raw_index_rc}
        return emit_json(preview_payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_sync_synth(phase_token: str | None = None, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Re-sync one phase's synth packet so `synth_seed.json`, `synth_seed.md`, and the owning scaffold stay aligned with the current synth contract.
    - Mechanism: Resolve the phase entry, normalize the current synth payload against its scaffold, validate it, render markdown, update scaffold authoring status, and optionally persist the synchronized artifacts.
    - Reads: Phase scaffold data, current `synth_seed.json`, and synth normalization and rendering helpers.
    - Writes: `synth_seed.json`, `synth_seed.md`, and `phase_scaffold.json` only when `live` is true.
    - Fails: Returns 1 when the phase cannot be resolved, scaffold or synth artifacts are missing or invalid, or synth normalization raises `ValueError`; emits a validation-failed payload when contract validation returns errors.
    - When-needed: Open when a phase's synth artifacts need deterministic normalization and markdown re-projection after edits to the JSON payload or scaffold contract.
    - Escalates-to: system/lib/observe_apply_contracts.py; docs/synth_first_scaffold_contract.md; system/lib/kernel/commands/navigate.py::cmd_close_phase
    - Navigation-group: kernel_lib
    """
    try:
        _navigator, phase_entry = _resolve_phase_entry_for_lifecycle(phase_token)
        scaffold_path = _phase_scaffold_path_for_entry(phase_entry)
        scaffold_payload, scaffold_error = safe_load_json_with_error(scaffold_path)
        if not isinstance(scaffold_payload, dict):
            detail = f": {scaffold_error}" if scaffold_error else ""
            raise ValueError(f"Invalid phase_scaffold.json: {state.rel(scaffold_path)}{detail}")
        synth_json_path = _phase_file_from_entry(phase_entry, "synth_seed.json")
        if not synth_json_path.exists():
            raise ValueError(f"synth_seed.json not found: {state.rel(synth_json_path)}")
        current_payload, synth_error = safe_load_json_with_error(synth_json_path)
        if not isinstance(current_payload, dict):
            detail = f": {synth_error}" if synth_error else ""
            raise ValueError(f"Invalid synth_seed.json: {state.rel(synth_json_path)}{detail}")
        normalized = normalize_synth_payload(current_payload, phase_scaffold=scaffold_payload)
        if not isinstance(normalized, dict):
            raise ValueError("Could not normalize synth_seed.json")
        normalized["authoring_status"] = "authored"
        normalized_meta = dict(normalized.get("meta") or {})
        normalized_meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        normalized["meta"] = normalized_meta
        errors = validate_synth_seed_payload(normalized, phase_scaffold=scaffold_payload, allow_pending=False)
        synth_markdown_path = _phase_file_from_entry(phase_entry, "synth_seed.md")
        synth_markdown = render_synth_seed_markdown(
            normalized,
            phase_scaffold_path=state.rel(scaffold_path),
            synth_seed_json_path=state.rel(synth_json_path),
        )
        updated_scaffold = dict(scaffold_payload)
        updated_scaffold["authoring_status"] = SYNCED_SYNTH_AUTHORING
        updated_scaffold["updated_at"] = datetime.now(timezone.utc).isoformat()
        if errors:
            return emit_json(
                {
                    "kind": "kernel.sync_synth",
                    "mode": "live" if live else "preview",
                    "status": "validation_failed",
                    "phase": {
                        "phase_id": phase_entry.get("phase_id"),
                        "phase_number": phase_entry.get("phase_number"),
                        "phase_title": phase_entry.get("phase_title"),
                        "phase_dir": phase_entry.get("phase_dir"),
                    },
                    "errors": errors,
                    "standards": {
                        "authority_index": OBSERVE_APPLY_AUTHORITY_INDEX_PATH,
                        "synth_seed": OBSERVE_APPLY_STANDARD_PATHS["synth_seed"],
                    },
                }
            )
        if live:
            synth_json_path.write_text(canonical_json_text(normalized), encoding="utf-8")
            synth_markdown_path.write_text(synth_markdown, encoding="utf-8")
            scaffold_path.write_text(canonical_json_text(updated_scaffold), encoding="utf-8")
        return emit_json(
            {
                "kind": "kernel.sync_synth",
                "mode": "live" if live else "preview",
                "status": "applied" if live else "preview_ready",
                "phase": {
                    "phase_id": phase_entry.get("phase_id"),
                    "phase_number": phase_entry.get("phase_number"),
                    "phase_title": phase_entry.get("phase_title"),
                    "phase_dir": phase_entry.get("phase_dir"),
                },
                "writes": [
                    {"path": state.rel(synth_json_path), "kind": "synth_seed"},
                    {"path": state.rel(synth_markdown_path), "kind": "synth_seed_note"},
                    {"path": state.rel(scaffold_path), "kind": "phase_scaffold_spec"},
                ],
                "standards": {
                    "authority_index": OBSERVE_APPLY_AUTHORITY_INDEX_PATH,
                    "synth_seed": OBSERVE_APPLY_STANDARD_PATHS["synth_seed"],
                    "phase_scaffold": OBSERVE_APPLY_STANDARD_PATHS["phase_scaffold"],
                },
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_close_phase(phase_token: str | None = None, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Preview or apply subphase close-out so the current phase's synth output is promoted into the correct parent or family meta-ledger and the scaffold is marked closed.
    - Mechanism: Resolve the target phase, load scaffold, synth, and meta-ledger artifacts, build the close-phase promotion entry plus `phase_closeout.json`, append the promotion entry to the correct promotion target ledger, update the local ledger and scaffold status, and optionally persist the result.
    - Reads: Phase scaffold, synth payload, local meta ledger, parent or family promotion target ledger, and phase navigation context.
    - Writes: Promotion target meta ledger, local `meta_ledger.json`, `phase_closeout.json`, and `phase_scaffold.json` only when `live` is true.
    - Fails: Returns 1 when the phase cannot be resolved, required scaffold/synth/meta-ledger artifacts are missing or invalid, or promotion-target metadata cannot be determined.
    - When-needed: Open when a phase is ready to close and its synthesized result must be promoted into the next ledger surface with a deterministic close-out packet.
    - Escalates-to: system/lib/observe_apply_contracts.py; system/lib/kernel_navigation.py; docs/synth_first_scaffold_contract.md
    - Navigation-group: kernel_lib
    """
    try:
        navigator, phase_entry = _resolve_phase_entry_for_lifecycle(phase_token)
        scaffold_path = _phase_scaffold_path_for_entry(phase_entry)
        scaffold_payload = safe_load_json(scaffold_path)
        if not isinstance(scaffold_payload, dict):
            raise ValueError(f"Invalid phase_scaffold.json: {state.rel(scaffold_path)}")
        synth_json_path = _phase_file_from_entry(phase_entry, "synth_seed.json")
        subphase_meta_ledger_path = _phase_file_from_entry(phase_entry, "meta_ledger.json")
        synth_payload = safe_load_json(synth_json_path)
        subphase_meta_ledger = safe_load_json(subphase_meta_ledger_path)
        if not isinstance(synth_payload, dict):
            raise ValueError(f"Invalid synth_seed.json: {state.rel(synth_json_path)}")
        if not isinstance(subphase_meta_ledger, dict):
            raise ValueError(f"Invalid subphase meta ledger: {state.rel(subphase_meta_ledger_path)}")
        if str(phase_entry.get("status") or "").strip().lower() == "closed":
            raise ValueError(
                f"Phase is already closed: {str(phase_entry.get('phase_id') or phase_entry.get('phase_number') or '').strip()}"
            )

        old_phase_title = str(scaffold_payload.get("phase_title") or phase_entry.get("phase_title") or "").strip()
        old_phase_dir = (
            canonicalize_write_path(str(scaffold_payload.get("phase_dir") or "").strip())
            or canonicalize_write_path(str(phase_entry.get("phase_dir") or "").strip())
            or ""
        )
        phase_number = str(scaffold_payload.get("phase_number") or phase_entry.get("phase_number") or "").strip()
        if not old_phase_title or not old_phase_dir or not phase_number:
            raise ValueError("phase_title, phase_dir, and phase_number are required to close a phase.")
        new_phase_title = _closed_phase_title(phase_number, old_phase_title)
        new_phase_dir = _closed_phase_dir(old_phase_dir, phase_number, old_phase_title)
        rename_required = new_phase_dir != old_phase_dir

        rewritten_scaffold = _rewrite_phase_strings(
            scaffold_payload,
            old_phase_title=old_phase_title,
            new_phase_title=new_phase_title,
            old_phase_dir=old_phase_dir,
            new_phase_dir=new_phase_dir,
        )
        normalized_synth = normalize_synth_payload(synth_payload, phase_scaffold=scaffold_payload) or synth_payload
        rewritten_synth = _rewrite_phase_strings(
            normalized_synth,
            old_phase_title=old_phase_title,
            new_phase_title=new_phase_title,
            old_phase_dir=old_phase_dir,
            new_phase_dir=new_phase_dir,
        )
        rewritten_subphase_ledger = _rewrite_phase_strings(
            subphase_meta_ledger,
            old_phase_title=old_phase_title,
            new_phase_title=new_phase_title,
            old_phase_dir=old_phase_dir,
            new_phase_dir=new_phase_dir,
        )

        updated_scaffold = dict(rewritten_scaffold)
        whiteboard_contract = (
            dict(updated_scaffold.get("whiteboard_contract"))
            if isinstance(updated_scaffold.get("whiteboard_contract"), Mapping)
            else {}
        )
        phase_closeout_rel = (
            canonicalize_write_path(str(whiteboard_contract.get("phase_closeout_path") or "").strip())
            or f"{new_phase_dir.rstrip('/')}/phase_closeout.json"
        )
        whiteboard_contract["phase_closeout_path"] = phase_closeout_rel
        updated_scaffold["whiteboard_contract"] = whiteboard_contract
        updated_scaffold["schema_version"] = PHASE_SCAFFOLD_VERSION
        updated_scaffold["phase_title"] = new_phase_title
        updated_scaffold["phase_dir"] = new_phase_dir
        updated_scaffold["authoring_status"] = "closed"
        updated_scaffold["status"] = "closed"
        updated_scaffold["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated_synth = dict(rewritten_synth)
        updated_synth["authoring_status"] = "closed"
        synth_meta = dict(updated_synth.get("meta") or {})
        synth_meta["phase_title"] = new_phase_title
        synth_meta["phase_dir"] = new_phase_dir
        synth_meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        if synth_meta:
            synth_meta["controller_phase"] = "closed"
        updated_synth["meta"] = synth_meta
        current_wave = dict(updated_synth.get("current_wave") or {})
        if current_wave:
            wave_status = str(current_wave.get("status") or "").strip().lower()
            if wave_status in {"", "in_progress", "active", "planned", "open"}:
                current_wave["status"] = "completed"
            updated_synth["current_wave"] = current_wave
        work_items = updated_synth.get("work_items")
        if isinstance(work_items, list):
            normalized_work_items: list[Any] = []
            for item in work_items:
                if not isinstance(item, Mapping):
                    normalized_work_items.append(item)
                    continue
                updated_item = dict(item)
                item_status = str(updated_item.get("status") or "").strip().lower()
                if item_status in {"", "active", "in_progress", "planned", "open"}:
                    updated_item["status"] = "done"
                normalized_work_items.append(updated_item)
            updated_synth["work_items"] = normalized_work_items
        synth_errors = validate_synth_seed_payload(updated_synth, phase_scaffold=updated_scaffold, allow_pending=False)
        if synth_errors:
            raise ValueError(f"Closed synth payload failed validation: {'; '.join(synth_errors)}")

        parent_phase_id = str(updated_scaffold.get("parent_phase_id") or "").strip()
        family_dir = canonicalize_write_path(str(updated_scaffold.get("family_dir") or "").strip()) or ""
        if parent_phase_id:
            parent_entry = navigator._resolve_phase_entry(parent_phase_id)
            promotion_target_path = _phase_file_from_entry(parent_entry, "meta_ledger.json")
            promotion_target_kind = "parent_subphase_meta_ledger"
        else:
            if not family_dir:
                raise ValueError("family_dir is required to close a top-level subphase.")
            promotion_target_path = state.REPO_ROOT / family_dir / "meta_ledger.json"
            promotion_target_kind = "family_meta_ledger"
        promotion_target = safe_load_json(promotion_target_path)
        if not isinstance(promotion_target, dict):
            raise ValueError(f"Invalid promotion target meta ledger: {state.rel(promotion_target_path)}")
        updated_target = _rewrite_phase_strings(
            promotion_target,
            old_phase_title=old_phase_title,
            new_phase_title=new_phase_title,
            old_phase_dir=old_phase_dir,
            new_phase_dir=new_phase_dir,
        )
        target_entries = updated_target.get("entries")
        if not isinstance(target_entries, list):
            raise ValueError(f"Promotion target ledger is missing entries list: {state.rel(promotion_target_path)}")
        promotion_entry = build_subphase_close_promotion_entry(
            updated_scaffold,
            updated_synth,
            rewritten_subphase_ledger,
        )
        closeout_payload = build_phase_closeout_payload(
            updated_scaffold,
            updated_synth,
            rewritten_subphase_ledger,
            promotion_target_path=state.rel(promotion_target_path),
            promotion_entry=promotion_entry,
        )
        updated_target["entries"] = [*target_entries, promotion_entry]
        updated_subphase_ledger = dict(rewritten_subphase_ledger)
        local_entries = updated_subphase_ledger.get("entries")
        if not isinstance(local_entries, list):
            local_entries = []
        updated_subphase_ledger["entries"] = [
            *local_entries,
            {
                "cycle": int(updated_scaffold.get("current_cycle") or 0),
                "entry_id": promotion_entry["entry_id"],
                "timestamp": promotion_entry["timestamp"],
                "action": "subphase_closed",
                "summary": promotion_entry["summary"],
                "what_was_done": [f"Promoted this subphase into `{state.rel(promotion_target_path)}`."],
                "what_was_learned": promotion_entry.get("what_was_learned", []),
                "shards_addressed": promotion_entry.get("shards_addressed", []),
                "files_changed": [],
                "open_questions_remaining": [],
            },
        ]
        new_phase_dir_path = state.REPO_ROOT / new_phase_dir
        new_scaffold_path = new_phase_dir_path / "phase_scaffold.json"
        new_synth_json_path = state.REPO_ROOT / (
            canonicalize_write_path(str(whiteboard_contract.get("synth_seed_path") or "").strip())
            or f"{new_phase_dir.rstrip('/')}/synth_seed.json"
        )
        new_synth_markdown_path = state.REPO_ROOT / (
            canonicalize_write_path(str(whiteboard_contract.get("synth_seed_markdown_path") or "").strip())
            or f"{new_phase_dir.rstrip('/')}/synth_seed.md"
        )
        new_subphase_meta_ledger_path = state.REPO_ROOT / (
            canonicalize_write_path(str(whiteboard_contract.get("meta_ledger_path") or "").strip())
            or f"{new_phase_dir.rstrip('/')}/meta_ledger.json"
        )
        phase_closeout_path = state.REPO_ROOT / phase_closeout_rel
        synth_markdown = render_synth_seed_markdown(
            updated_synth,
            phase_scaffold_path=state.rel(new_scaffold_path),
            synth_seed_json_path=state.rel(new_synth_json_path),
        )

        family_marker_path = state.REPO_ROOT / family_dir / PHASE_FAMILY_MARKER_FILENAME if family_dir else None
        updated_family_marker: dict[str, Any] | None = None
        phase_memory_rel = default_phase_memory_path(family_dir) if family_dir else ""
        autonomous_seed_rel = default_autonomous_seed_path(family_dir) if family_dir else ""
        phase_memory_write: dict[str, Any] | None = (
            {"path": phase_memory_rel, "kind": "phase_memory"} if phase_memory_rel else None
        )
        autonomous_seed_write: dict[str, Any] | None = (
            {"path": autonomous_seed_rel, "kind": "autonomous_seed"} if autonomous_seed_rel else None
        )
        if family_marker_path and family_marker_path.exists():
            family_marker_payload = safe_load_json(family_marker_path)
            if isinstance(family_marker_payload, dict):
                rewritten_family_marker = _rewrite_phase_strings(
                    family_marker_payload,
                    old_phase_title=old_phase_title,
                    new_phase_title=new_phase_title,
                    old_phase_dir=old_phase_dir,
                    new_phase_dir=new_phase_dir,
                )
                updated_family_marker = dict(rewritten_family_marker)
                phase_memory_rel = (
                    canonicalize_write_path(str(updated_family_marker.get("phase_memory_path") or "").strip())
                    or phase_memory_rel
                )
                autonomous_seed_rel = (
                    canonicalize_write_path(str(updated_family_marker.get("autonomous_seed_path") or "").strip())
                    or autonomous_seed_rel
                )
                if phase_memory_rel:
                    phase_memory_write = {"path": phase_memory_rel, "kind": "phase_memory"}
                if autonomous_seed_rel:
                    autonomous_seed_write = {"path": autonomous_seed_rel, "kind": "autonomous_seed"}

        if live:
            old_phase_dir_path = state.REPO_ROOT / old_phase_dir
            if rename_required:
                if new_phase_dir_path.exists():
                    raise ValueError(f"Closed phase directory already exists: {state.rel(new_phase_dir_path)}")
                if not old_phase_dir_path.exists():
                    raise ValueError(f"Original phase directory not found for rename: {old_phase_dir}")
                new_phase_dir_path.parent.mkdir(parents=True, exist_ok=True)
                old_phase_dir_path.rename(new_phase_dir_path)
            promotion_target_path.write_text(canonical_json_text(updated_target), encoding="utf-8")
            new_subphase_meta_ledger_path.write_text(canonical_json_text(updated_subphase_ledger), encoding="utf-8")
            new_synth_json_path.write_text(canonical_json_text(updated_synth), encoding="utf-8")
            new_synth_markdown_path.write_text(synth_markdown, encoding="utf-8")
            phase_closeout_path.write_text(canonical_json_text(closeout_payload), encoding="utf-8")
            new_scaffold_path.write_text(canonical_json_text(updated_scaffold), encoding="utf-8")
            if family_marker_path and updated_family_marker is not None:
                family_marker_path.write_text(canonical_json_text(updated_family_marker), encoding="utf-8")
            if family_dir:
                phase_memory_rel, _phase_memory_payload = write_phase_memory(
                    state.REPO_ROOT,
                    family_dir=family_dir,
                )
                phase_memory_write = {"path": phase_memory_rel, "kind": "phase_memory"}
                autonomous_seed_rel, _autonomous_seed_markdown_rel, _autonomous_seed_payload = write_autonomous_seed(
                    state.REPO_ROOT,
                    family_dir=family_dir,
                )
                autonomous_seed_write = {"path": autonomous_seed_rel, "kind": "autonomous_seed"}
        return emit_json(
            {
                "kind": "kernel.close_phase",
                "mode": "live" if live else "preview",
                "status": "applied" if live else "preview_ready",
                "phase": {
                    "phase_id": phase_entry.get("phase_id"),
                    "phase_number": phase_number,
                    "phase_title": new_phase_title,
                    "phase_dir": new_phase_dir,
                },
                "rename": {
                    "applied": rename_required,
                    "from_phase_title": old_phase_title,
                    "to_phase_title": new_phase_title,
                    "from_phase_dir": old_phase_dir,
                    "to_phase_dir": new_phase_dir,
                },
                "promotion_target": {
                    "path": state.rel(promotion_target_path),
                    "kind": promotion_target_kind,
                },
                "promotion_entry": promotion_entry,
                "closeout": {
                    "path": phase_closeout_rel,
                    "kind": "phase_closeout",
                    "payload": closeout_payload,
                },
                "writes": [
                    {"path": state.rel(promotion_target_path), "kind": promotion_target_kind},
                    {"path": state.rel(new_subphase_meta_ledger_path), "kind": "subphase_meta_ledger"},
                    {"path": state.rel(new_synth_json_path), "kind": "synth_seed"},
                    {"path": state.rel(new_synth_markdown_path), "kind": "synth_seed_note"},
                    {"path": phase_closeout_rel, "kind": "phase_closeout"},
                    {"path": state.rel(new_scaffold_path), "kind": "phase_scaffold_spec"},
                    *([phase_memory_write] if phase_memory_write else []),
                    *([autonomous_seed_write] if autonomous_seed_write else []),
                    *(
                        [{"path": state.rel(family_marker_path), "kind": "phase_family_marker"}]
                        if family_marker_path and updated_family_marker is not None
                        else []
                    ),
                ],
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_add_workstream(spec_path: str, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Preview or write a new workstream root plus founding phase packet from one JSON scaffold spec instead of assembling the family and phase artifacts manually.
    - Mechanism: Validate the requested spec path, delegate to `execute_workstream_scaffold()`, attach the default promotion metadata, and emit the resulting scaffold payload.
    - Reads: The requested workstream scaffold spec JSON and workstream scaffold helpers.
    - Writes: Workstream scaffold artifacts only when `live` is true.
    - Fails: Returns 1 when the spec path is missing or workstream scaffold generation raises `ValueError`.
    - When-needed: Open when a fresh top-level workstream should be scaffolded from a prepared JSON spec through the kernel CLI.
    - Escalates-to: system/lib/workstream_scaffold.py; docs/synth_first_scaffold_contract.md; system/lib/kernel/commands/navigate.py::cmd_new_family
    - Navigation-group: kernel_lib
    """
    requested = str(spec_path or "").strip()
    if not requested:
        print("ERROR: --add-workstream requires a JSON spec path", file=sys.stderr)
        return 1
    try:
        payload = execute_workstream_scaffold(state.REPO_ROOT, requested, live=live)
        payload = _attach_scaffold_default_promotion(
            payload,
            live=live,
            source_command="add-workstream",
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(payload)


def cmd_execution_map(selector: str = "latest") -> int:
    """[ACTION]
    - Teleology: Emit one execution-map planner-memory packet when the task needs bounded execution memory for a resolved planning surface.
    - Mechanism: Delegate to `KernelNavigation.build_execution_map()` using the requested selector and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the execution-map packet.
    - Fails: Returns 1 when the navigator cannot resolve the requested selector.
    - When-needed: Open when execution-memory notes or latest planner state should be recovered by token or path instead of manual note browsing.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_notes.py; system/lib/kernel/commands/navigate.py::cmd_map
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_execution_map(selector)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_map(selector: str = "latest") -> int:
    """[ACTION]
    - Teleology: Emit one living-map boundary-memory packet when the task needs the bounded map surface for a resolved note, token, or latest map artifact.
    - Mechanism: Delegate to `KernelNavigation.build_map()` using the requested selector and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the living-map packet.
    - Fails: Returns 1 when the navigator cannot resolve the requested selector.
    - When-needed: Open when a living-map or boundary-memory artifact should be recovered directly instead of searching through broader markdown context.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_notes.py; system/lib/kernel/commands/navigate.py::cmd_execution_map
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_map(selector)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_stale() -> int:
    """[ACTION]
    - Teleology: Emit one stale-report packet so the kernel CLI can show documentation-memory drift before the next refresh decision.
    - Mechanism: Call `KernelNavigation.build_stale_report()` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the stale-report payload.
    - Fails: Returns 1 when stale-report assembly raises ValueError.
    - When-needed: Open when living maps, execution maps, idea packets, or doctrine docs need one bounded drift report instead of manual packet-by-packet inspection.
    - Escalates-to: system/lib/kernel_nav_map.py::MapExecutionMixin.build_stale_report; system/lib/kernel_nav_notes.py::NoteExtractMixin.build_bootstrap_task; system/lib/kernel_nav_frontier.py::FrontierMixin.build_frontier
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_stale_report()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_doc_gaps() -> int:
    """[ACTION]
    - Teleology: Emit one documentation-gap packet so the kernel CLI can expose uncovered high-value runtime surfaces before new note authoring begins.
    - Mechanism: Call `KernelNavigation.build_doc_gap_report()` and emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the documentation-gap payload.
    - Fails: Returns 1 when documentation-gap assembly raises ValueError.
    - When-needed: Open when important control-plane or runtime surfaces need a bounded covered-vs-uncovered checklist instead of reviewing living maps manually.
    - Escalates-to: system/lib/kernel_nav_map.py::MapExecutionMixin.build_doc_gap_report; system/lib/kernel_nav_notes.py::NoteExtractMixin.build_bootstrap_task; system/lib/kernel_nav_phase.py::PhasePlanMixin.build_phase
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_doc_gap_report()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_obsidian_family(anchor: str, limit: int = state.MARKDOWN_FRONTIER_DEFAULT_LIMIT) -> int:
    """[ACTION]
    - Teleology: Emit one explicit obsidian-family packet when the anchor note is already known and recency-based selection would add noise.
    - Mechanism: Call `KernelNavigation.build_obsidian_family()` with the requested anchor and limit, then emit the resulting navigation payload.
    - Guarantee: Returns 0 after emitting the explicit-family payload for the resolved anchor.
    - Fails: Returns 1 when the anchor is empty or the navigator cannot resolve it to an obsidian family.
    - When-needed: Open when a known obsidian note, path, or token should anchor family recovery directly instead of using recent-obsidian or generic working-set selection.
    - Escalates-to: system/lib/kernel_nav_frontier.py::FrontierMixin.build_obsidian_family; system/lib/kernel_nav_notes.py::NoteExtractMixin.build_working_set; system/lib/kernel_nav_phase.py::PhasePlanMixin.build_phase
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_obsidian_family(anchor, limit=limit)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_paths() -> int:
    """
    [ACTION]
    - Teleology: Emit a comprehensive JSON catalog of all kernel path constants and their existence status.
    - Guarantee: Returns 0 after emitting the path catalog navigation result.
    - Fails: None for normal degraded path assembly; missing paths are flagged with `exists: false`.
    """
    runs_dir = resolve_runs_dir(state.REPO_ROOT, read_runs_dir_value())
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        active_plan_payload = navigator.build_plan_phase().payload
        active_implementation_plan = active_plan_payload.get("plan")
    except ValueError:
        active_implementation_plan = None

    path_catalog = {
        "observe": {
            "apply_dir": _path_status(state.APPLY_DIR),
            "observe_plan": _path_status(state.OBSERVE_PLAN),
            "observe_plan_suggestion": _path_status(state.OBSERVE_PLAN_SUGGESTION),
            "observe_result": _path_status(state.OBSERVE_RESULT),
            "observe_dumps": _path_status(state.OBSERVE_DUMPS),
            "observe_history_dir": _path_status(state.OBSERVE_HISTORY_DIR),
            "observe_history_json": _path_status(state.OBSERVE_HISTORY),
            "observe_history_md": _path_status(state.OBSERVE_HISTORY_MD),
            "observe_history_entries_dir": _path_status(state.OBSERVE_HISTORY_ENTRIES_DIR),
            "observe_history_prompts_dir": _path_status(state.OBSERVE_HISTORY_PROMPTS_DIR),
            "observe_sticky_dump_marker": _path_status(state.OBSERVE_STICKY_DUMP_MARKER),
            "observe_sessions_dir": _path_status(state.OBSERVE_SESSION_ROOT),
            "tree_md": _path_status(state.TREE_MD),
            "tree_manifest": _path_status(state.TREE_MANIFEST),
        },
        "documentation": {
            "observe_guide": _path_status(state.STD_FRAMEWORK),
            "observe_patterns_guide": _path_status(state.OBSERVE_PATTERN_GUIDE),
            "observe_authoring_guide": _path_status(state.OBSERVE_PROMPT),
            "implement_guide": _path_status(observe_asset_paths(state.REPO_ROOT).implement_guide),
            "apply_guide": _path_status(state.APPLY_GUIDE),
            "kernel_principles": _path_status(state.KERNEL_PRINCIPLES_DOC),
            "runtime_change_protocol": _path_status(observe_asset_paths(state.REPO_ROOT).runtime_change_protocol),
            "etf_reference": _path_status(observe_asset_paths(state.REPO_ROOT).etf_reference),
        },
        "planning": {
            "plan_dir": {
                **_path_status(state.PLAN_DIR),
                "manifest_count": len([p for p in state.PLAN_DIR.glob("*.json")]) if state.PLAN_DIR.exists() else 0,
                "manifests": sorted(state.rel(path) for path in state.PLAN_DIR.glob("*.json")) if state.PLAN_DIR.exists() else [],
            },
            "std_work_note": _path_status(state.STD_WORK_NOTE),
            "std_plan_note": _path_status(state.STD_PLAN_NOTE),
        },
        "standards": {
            "root": _path_status(state.CODEX_STANDARDS_DIR),
            "standards_registry": _path_status(state.STANDARDS_REGISTRY),
            "core_authority_index": _path_status(state.CODEX_STANDARDS_DIR / "core_authority_index.json"),
            "std_markdown_doc": _path_status(state.STD_MARKDOWN_DOC),
            "std_work_note": _path_status(state.STD_WORK_NOTE),
            "std_plan_note": _path_status(state.STD_PLAN_NOTE),
            "std_observe_session": _path_status(state.STD_OBSERVE_SESSION),
            "std_node_reasoning": _path_status(state.STD_NODE_REASONING),
            "std_node_tool": _path_status(state.STD_NODE_TOOL),
            "std_apply": _path_status(state.STD_APPLY),
            "observe_dir": _path_status(state.STANDARDS_DIR),
            "observe_authority_index": _path_status(state.CODEX_STANDARDS_DIR / "observe" / "observe_authority_index.json"),
            "observe_apply_authority_index": _path_status(state.REPO_ROOT / OBSERVE_APPLY_AUTHORITY_INDEX_PATH),
            "annex_authority_index": _path_status(state.CODEX_STANDARDS_DIR / "annex" / "annex_authority_index.json"),
            "principles_authority_index": _path_status(state.CODEX_STANDARDS_DIR / "principles" / "principles_authority_index.json"),
            "std_general": _path_status(state.STD_GENERAL),
            "std_search": _path_status(state.STD_SEARCH),
            "prompts_md": _path_status(state.STD_PROMPTS_MD),
            "prompts_json": _path_status(state.STD_PROMPTS_JSON),
            "templates": _path_status(state.STD_TEMPLATES),
        },
        "apply": {
            "apply_plan": _path_status(state.APPLY_PLAN),
            "apply_result": _path_status(state.APPLY_RESULT),
            "apply_loop_result": _path_status(state.APPLY_LOOP_RESULT),
            "apply_history": _path_status(state.APPLY_HISTORY),
            "apply_snapshots": _path_status(state.APPLY_SNAPSHOTS),
            "std_apply": _path_status(state.STD_APPLY),
        },
        "scratchpad": {
            "scratchpad_py": _path_status(state.SCRATCHPAD_PY),
            "scratchpad_prompt": _path_status(state.SCRATCHPAD_PROMPT),
        },
        "infrastructure": {
            "builder_py": _path_status(state.BUILDER_PY),
            "map_file": _path_status(state.MAP_FILE),
            "compiled_dir": {
                **_path_status(state.COMPILED_DIR),
                "bundle_count": _compiled_bundle_count(),
            },
            "master_config": _path_status(state.MASTER_CONFIG),
            "runs_dir": {
                **_path_status(runs_dir),
                "run_count": len([p for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("RUN_")]) if runs_dir.exists() else 0,
            },
        },
        "kernel_skills": {
            "schema": _path_status(state.KERNEL_SKILLS_SCHEMA),
            "skills": _skill_payload(),
        },
    }
    payload = {
        "repo_root": str(state.REPO_ROOT),
        "path_catalog": path_catalog,
        "active_plan": _active_plan_summary(),
        "active_implementation_plan": active_implementation_plan,
        "stable_command_groups": {group: list(flags) for group, flags in state.STABLE_COMMANDS.items()},
    }
    result = NavigationResult(
        kind="kernel.navigate.paths",
        query={"command": "paths"},
        payload=payload,
        live_sources=[
            "kernel.py",
            "tools/meta/apply/",
            "codex/substrate/plan/",
            "codex/derived/",
            "master_config.json",
        ],
        derived_sources=[state.rel(state.MAP_FILE)] if state.MAP_FILE.exists() else [],
        suggested_next=[
            {"command": "python3 kernel.py --info", "reason": "Return to the bootstrap manifest"},
            {"command": "python3 kernel.py --atlas", "reason": "Return to topology navigation"},
        ],
        warnings=[],
    )
    return emit_navigation(result)


def cmd_atlas() -> int:
    """[ACTION]
    - Teleology: Emit the repo-scale topology atlas.
    - Mechanism: Delegate to `KernelNavigation.build_atlas` and emit the navigation result.
    - Guarantee: Returns 0 after emitting the atlas.
    - Fails: None.
    - When-needed: Open when the task needs a broad topology briefing before narrowing to a boundary or file set.
    - Escalates-to: system/lib/kernel_nav_lens.py; kernel.py
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    return emit_navigation(navigator.build_atlas())


def cmd_orient(mission: str) -> int:
    """
    [ACTION]
    - Teleology: Emit orientation context for a named mission or task token.
    - Guarantee: Returns 0 after emitting the orient navigation result.
    - Fails: Returns 1 when the navigator cannot resolve the mission token.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_orient(mission)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


_DEFAULT_HIDDEN_DEBUG_KEYS = {
    "score",
    "score_before_focus",
    "focus_delta",
    "runtime_state_delta",
    "baseline_priority",
    "matched_priority_tags",
    "focus_reasons",
    "runtime_state_reasons",
    "matched_on",
    "overlay_priority_why",
    "alternatives",
}


def _strip_default_debug_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_default_debug_fields(item)
            for key, item in value.items()
            if str(key) not in _DEFAULT_HIDDEN_DEBUG_KEYS
        }
    if isinstance(value, list):
        return [_strip_default_debug_fields(item) for item in value]
    return value


def _docs_route_surface_result(result: NavigationResult, *, request: str, debug: bool) -> NavigationResult:
    payload = json.loads(json.dumps(result.payload))
    if not debug:
        payload = _strip_default_debug_fields(payload)
    payload["surface_role"] = DRILLDOWN
    payload["first_contact_allowed"] = False
    payload["control_replacement"] = ENTRY_REPLACEMENT
    payload["debug_trace_command"] = f"./repo-python kernel.py --docs-route {shlex.quote(str(request or '').strip())} --debug"
    payload["debug_fields_visible"] = bool(debug)
    payload["surface_contract"] = surface_contract(
        surface_id="docs_route",
        command="./repo-python kernel.py --docs-route",
        surface_role=DRILLDOWN,
        authority_plane="drilldown",
        first_contact_allowed=False,
        replacement=ENTRY_REPLACEMENT,
        debug_command=payload["debug_trace_command"],
        allowed_callers=[
            "entry_packet.selected_lane",
            "selected_route_drilldown",
            "operator_debug" if debug else "explicit_operator_browse",
        ],
        banned_callers=[
            "agent_first_contact",
            "route_selection_without_entry_packet",
        ],
        default_output_policy={
            "selected_route": "visible",
            "debug_fields": "hidden",
            "ranked_matches": "hidden",
        },
        debug_output_policy={
            "requires_flag": "--debug",
            "field_names": "visible",
        },
    )
    return NavigationResult(
        kind=result.kind,
        query=result.query,
        payload=payload,
        live_sources=result.live_sources,
        derived_sources=result.derived_sources,
        suggested_next=result.suggested_next,
        warnings=result.warnings,
        derived_required=result.derived_required,
        compact_hints=result.compact_hints,
    )


def cmd_docs_route(request: str, *, debug: bool = False) -> int:
    """[ACTION]
    - Teleology: Route a path or query to its governing documentation surface.
    - Mechanism: Delegate to `KernelNavigation.build_docs_route` and emit the ranked documentation route payload.
    - Guarantee: Returns 0 after emitting the docs-route result.
    - Fails: Returns 1 when the navigator cannot resolve the request.
    - When-needed: Open when a task needs the minimum read set or authority surface for a path/query instead of raw repo search.
    - Escalates-to: system/lib/kernel_navigation.py; system/control/documentation_route_focus.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_docs_route(request)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    result = _docs_route_surface_result(result, request=request, debug=debug)
    record_navigation_result(
        state.REPO_ROOT,
        event_kind="docs_route",
        query=request,
        command="kernel.py --docs-route",
        payload=result.payload,
    )
    return emit_navigation(result)


def cmd_skill_find(query: str, *, limit: int = 8, debug: bool = False) -> int:
    """Emit bounded matches from the repo skill registry."""
    if not debug:
        return emit_json(
            debug_trace_block(
                surface_id="skill_find",
                command="./repo-python kernel.py --skill-find",
                query=str(query or "").strip(),
            )
        )
    try:
        payload = build_skill_find_payload(query, limit=limit)
    except ValueError as exc:
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.skill_find",
                "query": str(query or ""),
                "error": str(exc),
            },
            2,
        )
    return emit_json(payload)


def build_skill_list_payload(
    *,
    surface: str = "all",
    fmt: str = "names",
    limit: int | None = None,
) -> dict[str, Any]:
    """Token-efficient enumeration of skills, grouped by surface.

    surface: agent-skills | doctrine | all
    fmt: names | table | json

    Backed by system.lib.skill_surfaces.published_agent_skill_rows so the AGENTS.md
    skill_catalog router header, the CLAUDE.md skill_router block, and this command
    are all driven by the same helper.
    """
    from system.lib import skill_surfaces  # local import keeps cold-path startup quiet

    registry = skill_surfaces.load_skill_registry()
    payload: dict[str, Any] = {
        "kind": "kernel.navigate.skill_list",
        "surface": surface,
        "format": fmt,
        "registry_path": "codex/doctrine/skills/skill_registry.json",
    }

    def _truncate(items: list[Any]) -> list[Any]:
        if limit is None or limit < 0:
            return items
        return items[:limit]

    def _row_summary(row: Mapping[str, Any]) -> dict[str, Any]:
        sp = row.get("surface_publication") if isinstance(row.get("surface_publication"), Mapping) else {}
        agent_surface = row.get("agent_surface") if isinstance(row.get("agent_surface"), Mapping) else {}
        return {
            "id": str(row.get("id") or ""),
            "name": str(sp.get("name") or row.get("id") or ""),
            "title": str(row.get("title") or ""),
            "projection_mode": str(sp.get("projection_mode") or ""),
            "one_liner": (
                str((row.get("holographic") or {}).get("one_liner") or "")
                or str(agent_surface.get("does") or "")
                or str(row.get("description") or "")[:120]
            ),
        }

    if surface in ("agent-skills", "all"):
        rows = skill_surfaces.published_agent_skill_rows(registry)
        groups: dict[str, list[Any]] = {}
        for mode, mode_rows in rows.items():
            if fmt == "names":
                groups[mode] = _truncate(
                    [str((r.get("surface_publication") or {}).get("name") or r.get("id") or "") for r in mode_rows]
                )
            else:
                groups[mode] = _truncate([_row_summary(r) for r in mode_rows])
        payload["agent_skills"] = groups

    if surface in ("doctrine", "all"):
        by_family: dict[str, list[Any]] = {}
        for family, skill in skill_surfaces.iter_active_skills(registry):
            fam_id = str(family.get("family_id") or "")
            entry: Any
            if fmt == "names":
                entry = str(skill.get("id") or "")
            else:
                entry = _row_summary(skill)
            by_family.setdefault(fam_id, []).append(entry)
        for fam_id in by_family:
            by_family[fam_id] = _truncate(by_family[fam_id])
        payload["doctrine"] = by_family

    return payload


def cmd_skill_list(*, surface: str = "all", fmt: str = "names", limit: int | None = None) -> int:
    """Emit registry-derived skill listing (no JSON read by callers)."""
    payload = build_skill_list_payload(surface=surface, fmt=fmt, limit=limit)
    if fmt == "names":
        # Token-efficient text output: one line per group.
        lines: list[str] = []
        if "agent_skills" in payload:
            lines.append("agent-skills:")
            for mode in ("generated_agent_skill", "hand_authored_agent_skill"):
                names = payload["agent_skills"].get(mode) or []
                lines.append(f"  {mode}: {', '.join(names) if names else '(none)'}")
        if "doctrine" in payload:
            lines.append("doctrine:")
            for fam_id in sorted(payload["doctrine"].keys()):
                names = payload["doctrine"][fam_id]
                lines.append(f"  {fam_id} ({len(names)}): {', '.join(names) if names else '(none)'}")
        sys.stdout.write("\n".join(lines) + "\n")
        return 0
    if fmt == "table":
        # Compact markdown table per surface group.
        lines = []
        if "agent_skills" in payload:
            lines.append("# Agent Skills (published)")
            lines.append("")
            lines.append("| name | mode | id | one-liner |")
            lines.append("|---|---|---|---|")
            for mode in ("generated_agent_skill", "hand_authored_agent_skill"):
                for row in payload["agent_skills"].get(mode) or []:
                    lines.append(
                        f"| `{row['name']}` | {mode} | `{row['id']}` | {row['one_liner']} |"
                    )
            lines.append("")
        if "doctrine" in payload:
            lines.append("# Doctrine skills")
            lines.append("")
            for fam_id in sorted(payload["doctrine"].keys()):
                rows_in_fam = payload["doctrine"][fam_id]
                lines.append(f"## {fam_id} ({len(rows_in_fam)})")
                lines.append("")
                lines.append("| id | title | one-liner |")
                lines.append("|---|---|---|")
                for r in rows_in_fam:
                    lines.append(f"| `{r['id']}` | {r['title']} | {r['one_liner']} |")
                lines.append("")
        sys.stdout.write("\n".join(lines) + "\n")
        return 0
    return emit_json(payload)


def cmd_terms(*, band: str = "card") -> int:
    return emit_json(list_system_terms(_repo_root_for_static_registry(), band=band))


def cmd_term(query: str, *, band: str = "card") -> int:
    payload = render_system_term(_repo_root_for_static_registry(), query=query, band=band)
    return emit_json_with_code(payload, 1 if payload.get("error") else 0)


def cmd_relational_context(node_ref: str, *, band: str = "card", radius: int = 1) -> int:
    """Emit a deterministic relational_context_v0 node-plus-edge packet.

    Wave 026 extractor + Wave 037 kernel re-wiring. Rebuilt after WIP-stash
    loss; the Python module under system/lib/relational_context.py carries
    the real logic, this is the kernel-layer command wrapper.
    """
    from system.lib.relational_context import extract_relational_context

    payload = extract_relational_context(
        str(node_ref or ""),
        band=band,
        radius=max(0, int(radius)),
        repo_root=_repo_root_for_static_registry(),
    )
    return emit_json(payload)


def cmd_kernel_surface_currentness(*, waves: str = "025-037") -> int:
    """Emit a living-system-posture audit of kernel command claims."""
    from system.lib.kernel_surface_currentness import build_kernel_surface_currentness_audit

    payload = build_kernel_surface_currentness_audit(
        _repo_root_for_static_registry(),
        waves=waves,
    )
    return emit_json(payload)


def cmd_command_card(query: str | None = None, *, limit: int = 6, debug: bool = False) -> int:
    """Emit typed command memory for repeated agent-movement command choices."""
    payload = build_command_card_payload(query, limit=limit, debug=debug)
    if payload.get("kind") == "kernel.route_policy":
        return emit_json(payload)
    code = 0 if payload.get("payload", {}).get("cards") else 1
    return emit_json_with_code(payload, code)


def cmd_validate_seed_heartbeat(path: str) -> int:
    """Emit a stale-wave reference check for a generated seed or synth heartbeat."""
    raw = str(path or "").strip()
    if not raw:
        return emit_json_with_code(
            {
                "kind": "kernel.validate.seed_heartbeat",
                "schema_version": "seed_heartbeat_validation_v1",
                "query": {"command": "validate-seed-heartbeat", "request": raw},
                "summary": {"status": "error", "stale_reference_count": 0},
                "errors": ["--validate-seed-heartbeat requires a seed or synth JSON path."],
                "warnings": [],
            },
            2,
        )
    target = Path(raw)
    if not target.is_absolute():
        target = state.REPO_ROOT / raw
    report = validate_seed_heartbeat_references(target, root=state.REPO_ROOT)
    report["query"] = {"command": "validate-seed-heartbeat", "request": raw}
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    status = str(summary.get("status") or "")
    if status == "unreadable":
        return emit_json_with_code(report, 2)
    return emit_json_with_code(report, 0 if status in {"ok", "warning"} else 1)


def cmd_session_diagnostics(
    *,
    lens: str = "all",
    store: str = "both",
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    project: str | None = None,
    limit: int = 20,
    write_path: str | None = None,
    write_route_miss_candidates_path: str | None = None,
    diagnostics_summary: bool = False,
) -> int:
    """Run the out-of-repo agent-session analyzer through the kernel ladder."""
    try:
        from tools.meta.observability.session_analyzer import (
            build_summary_report,
            build_report,
            summarize_report,
            write_report,
            write_route_miss_candidates,
        )

        if diagnostics_summary and lens == "all" and not write_route_miss_candidates_path:
            report = build_summary_report(
                store=store,
                last=last,
                after=after,
                before=before,
                project=project,
                limit=limit,
            )
            full_report = None
        else:
            full_report = build_report(
                lens=lens,
                store=store,
                last=last,
                after=after,
                before=before,
                project=project,
                limit=limit,
            )
            report = summarize_report(full_report) if diagnostics_summary else full_report
        if write_path:
            written = write_report(report, write_path)
            try:
                report["written_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                report["written_path"] = str(written)
        if write_route_miss_candidates_path:
            route_report = full_report if isinstance(full_report, dict) else {}
            if "route-misses" not in (route_report.get("lenses") or {}):
                route_report = build_report(
                    lens="route-misses",
                    store=store,
                    last=last,
                    after=after,
                    before=before,
                    project=project,
                    limit=limit,
                )
            written = write_route_miss_candidates(
                route_report,
                write_route_miss_candidates_path,
            )
            try:
                report["route_miss_candidates_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                report["route_miss_candidates_path"] = str(written)
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "agent_session_diagnostics",
                "error": str(exc),
            },
            2,
        )
    return emit_json(report)


def _load_trace_projection_previous(path_token: str | None) -> dict[str, Any] | None:
    if not path_token:
        return None
    path = Path(path_token).expanduser()
    if not path.is_absolute():
        path = state.REPO_ROOT / path
    payload = safe_load_json(path)
    return payload if isinstance(payload, dict) else None


def _load_work_ledger_active_claims_snapshot() -> dict[str, Any] | None:
    payload = safe_load_json(state.REPO_ROOT / "state" / "work_ledger" / "active_claims_snapshot.json")
    return payload if isinstance(payload, dict) else None


def cmd_trace_friction_board(
    *,
    last: int = 30,
    after: str | None = None,
    before: str | None = None,
    store: str = "both",
    project: str | None = None,
    limit: int = 20,
    force_live: bool = False,
    write_path: str | None = None,
) -> int:
    """Emit the generated Trace Friction Board over live and finished traces."""
    try:
        from system.lib.agent_execution_trace import build_process_summary_route_packet
        from tools.meta.observability.session_analyzer import (
            build_summary_report,
            build_trace_observatory_projection,
            write_report,
        )

        finished_summary = build_summary_report(
            store=store,
            last=last,
            after=after,
            before=before,
            project=project,
            limit=limit,
        )
        runtime_scope = store if str(store).lower() in {"codex", "claude"} else "both"
        process_summary_request = (
            f"{runtime_scope}:latest"
            if runtime_scope in {"codex", "claude"}
            else "latest"
        )
        _process_summary_code, process_summary = build_process_summary_route_packet(
            repo_root=state.REPO_ROOT,
            request=process_summary_request,
            since_ts=after,
            session_limit=limit,
            force_live=force_live,
        )
        process_bottlenecks = _build_process_bottlenecks_packet(
            since_ts=after,
            session_limit=limit,
            force_live=force_live,
        )
        projection = build_trace_observatory_projection(
            finished_summary=finished_summary,
            process_summary=process_summary,
            process_bottlenecks=process_bottlenecks,
            work_ledger_claims=_load_work_ledger_active_claims_snapshot(),
            previous_projection=_load_trace_projection_previous(write_path),
            runtime_scope=runtime_scope,
            last=last,
        )
        if write_path:
            written = write_report(projection, write_path)
            try:
                projection["written_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                projection["written_path"] = str(written)
            projection.setdefault("validation_receipts", []).append({
                "receipt": "trace_observatory_projection_written",
                "status": "written",
                "path": projection["written_path"],
            })
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "trace_observatory_projection",
                "schema_version": "trace_observatory_projection_v0",
                "error": f"{type(exc).__name__}: {exc}",
            },
            2,
        )
    return emit_json(projection)


def cmd_lean_diagnostics(
    *,
    lens: str = "all",
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    limit: int = 20,
    record_file: str | None = None,
    write_path: str | None = None,
    timeout_seconds: int = 180,
) -> int:
    """Run Lean timing diagnostics through the kernel ladder."""
    try:
        from tools.meta.observability.lean_analyzer import (
            build_report,
            record_file_profile,
            write_report,
        )

        recorded_run = None
        if record_file:
            recorded_run = record_file_profile(
                record_file,
                timeout_seconds=timeout_seconds,
            )
        report = build_report(
            lens=lens,
            last=last,
            after=after,
            before=before,
            limit=limit,
        )
        if recorded_run:
            execution_context = recorded_run.get("execution_context")
            context = execution_context if isinstance(execution_context, Mapping) else {}
            report["recorded_run"] = {
                "status": recorded_run.get("status"),
                "source_file": recorded_run.get("source_file"),
                "duration_ms": recorded_run.get("duration_ms"),
                "written_path": recorded_run.get("written_path"),
                "environment_status": recorded_run.get("environment_status"),
                "dependency_cache_status": recorded_run.get("dependency_cache_status"),
                "mode": context.get("mode"),
                "lake_root": context.get("lake_root"),
                "package_id": context.get("package_id"),
                "toolchain": context.get("lean_toolchain"),
                "command_form": context.get("command_form"),
                "cwd": context.get("cwd"),
                "target_file": context.get("target_file"),
                "target_module": context.get("target_module"),
                "recommended_dependency_commands": context.get("recommended_dependency_commands") or [],
                "diagnostic_lines": recorded_run.get("diagnostic_lines") or [],
            }
        if write_path:
            written = write_report(report, write_path)
            try:
                report["written_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                report["written_path"] = str(written)
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "lean_diagnostics",
                "error": str(exc),
            },
            2,
        )
    return emit_json(report)


def cmd_lean_bottlenecks(
    *,
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    limit: int = 20,
    write_path: str | None = None,
) -> int:
    """Emit the compact Lean long-tail phase/event packet."""
    try:
        from tools.meta.observability.lean_analyzer import (
            build_bottlenecks,
            write_report,
        )

        report = build_bottlenecks(
            last=last,
            after=after,
            before=before,
            limit=limit,
        )
        if write_path:
            written = write_report(report, write_path)
            try:
                report["written_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                report["written_path"] = str(written)
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "lean_bottlenecks",
                "error": str(exc),
            },
            2,
        )
    return emit_json(report)


def cmd_lean_pipeline_profile(
    *,
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    limit: int = 20,
    write_path: str | None = None,
    record_pipeline: bool = False,
    timeout_seconds: int = 360,
) -> int:
    """Emit or record the formal-math refresh-chain timing packet."""
    try:
        from tools.meta.observability.lean_analyzer import (
            build_pipeline_profile,
            record_formal_refresh_pipeline,
            write_report,
        )

        recorded_pipeline = None
        if record_pipeline:
            recorded_pipeline = record_formal_refresh_pipeline(
                timeout_seconds=timeout_seconds,
            )
        report = build_pipeline_profile(
            last=last,
            after=after,
            before=before,
            limit=limit,
        )
        if recorded_pipeline:
            report["recorded_pipeline"] = {
                "status": recorded_pipeline.get("status"),
                "duration_ms": recorded_pipeline.get("duration_ms"),
                "step_count": recorded_pipeline.get("step_count"),
                "written_path": recorded_pipeline.get("written_path"),
            }
        if write_path:
            written = write_report(report, write_path)
            try:
                report["written_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                report["written_path"] = str(written)
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "lean_pipeline_profile",
                "error": str(exc),
            },
            2,
        )
    return emit_json(report)


def cmd_lean_parallelism_plan(
    *,
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    limit: int = 20,
    write_path: str | None = None,
    max_workers: int | None = None,
    run_parallel_lane: str | None = None,
    parallel_dry_run: bool = False,
    timeout_seconds: int = 180,
) -> int:
    """Emit or execute the Lean timing/validation parallelism plan."""
    try:
        from tools.meta.observability.lean_analyzer import (
            build_parallelism_plan,
            execute_parallelism_plan,
            write_report,
        )

        report = build_parallelism_plan(
            last=last,
            after=after,
            before=before,
            limit=limit,
            max_workers=max_workers,
        )
        if run_parallel_lane:
            report["parallel_execution"] = execute_parallelism_plan(
                report,
                lane_id=run_parallel_lane,
                timeout_seconds=timeout_seconds,
                dry_run=parallel_dry_run,
            )
        if write_path:
            written = write_report(report, write_path)
            try:
                report["written_path"] = str(written.relative_to(state.REPO_ROOT))
            except ValueError:
                report["written_path"] = str(written)
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "lean_parallelism_plan",
                "error": str(exc),
            },
            2,
        )
    return emit_json(report)


_AGENT_WAKE_REPLACES_COMMANDS = [
    "./repo-python kernel.py --pulse",
    "./repo-python kernel.py --phase",
    "./repo-python kernel.py --view-graph-check",
    "codex/hologram/raw_seed_projection/summary.json (refresh with tools/meta/factory/build_raw_seed_projection_coverage.py)",
    "./repo-python tools/meta/factory/work_ledger.py session-status --overview --limit <N>",
]

_RAW_SEED_PROJECTION_DIR = Path("codex/hologram/raw_seed_projection")
_RAW_SEED_PROJECTION_REFRESH_COMMAND = (
    "./repo-python tools/meta/factory/build_raw_seed_projection_coverage.py "
    "--process-session-limit 10 --timeout-seconds 30"
)
_RAW_SEED_PROJECTION_CHECK_COMMAND = (
    "./repo-python tools/meta/factory/build_raw_seed_projection_coverage.py "
    "--check --process-session-limit 10 --timeout-seconds 30"
)
_AGENT_WAKE_RAW_SEED_PROJECTION_DIR = _RAW_SEED_PROJECTION_DIR
_AGENT_WAKE_RAW_SEED_REFRESH_COMMAND = _RAW_SEED_PROJECTION_REFRESH_COMMAND
_AGENT_WAKE_RAW_SEED_CHECK_COMMAND = _RAW_SEED_PROJECTION_CHECK_COMMAND


def _agent_wake_truncate(value: object, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _agent_wake_phase_id_from_text(value: object) -> str | None:
    text = str(value or "")
    for pattern in (
        r"(?:^|[/\s])(?P<num>\d{2})\.(?P<sub>\d+)\s+-\s+Phase",
        r"--phase\s+(?P<id>\d{2}[_\.]\d+)",
        r"\bphase\s+(?P<id>\d{2}[_\.]\d+)\b",
        r"\b(?P<id>\d{2}_\d+)\b",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        if "num" in match.groupdict() and match.group("num"):
            return f"{match.group('num')}_{match.group('sub')}"
        token = str(match.group("id") or "").replace(".", "_")
        if token:
            return token
    return None


def _agent_wake_warning_slice(items: object, *, limit: int = 4) -> list[str]:
    if not isinstance(items, list):
        return []
    warnings = [_agent_wake_truncate(item, 320) for item in items[:limit]]
    extra = len(items) - len(warnings)
    if extra > 0:
        warnings.append(f"+{extra} more warning(s)")
    return warnings


def _agent_wake_pulse_packet(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    frontier = snapshot.get("frontier_anchor") if isinstance(snapshot.get("frontier_anchor"), Mapping) else {}
    runtime = snapshot.get("latest_runtime") if isinstance(snapshot.get("latest_runtime"), Mapping) else {}
    routing = snapshot.get("routing_projection") if isinstance(snapshot.get("routing_projection"), Mapping) else {}
    closeout = snapshot.get("closeout_gap") if isinstance(snapshot.get("closeout_gap"), Mapping) else {}
    builder = snapshot.get("builder") if isinstance(snapshot.get("builder"), Mapping) else {}
    doctrine = snapshot.get("doctrine") if isinstance(snapshot.get("doctrine"), Mapping) else {}
    dp = snapshot.get("documentation_plane") if isinstance(snapshot.get("documentation_plane"), Mapping) else {}
    return {
        "generated_at": snapshot.get("generated_at"),
        "frontier": {
            "path": frontier.get("path"),
            "modified_at": frontier.get("modified_at"),
            "phase_id": _agent_wake_phase_id_from_text(frontier.get("path")),
        },
        "routing": {
            "stale": bool(routing.get("stale")),
            "drift_targets": list(routing.get("drift_targets") or [])[:4],
            "artifact_path": routing.get("artifact_path"),
        },
        "runtime": {
            "kind": runtime.get("kind"),
            "state": runtime.get("state"),
            "gate_reason": runtime.get("gate_reason"),
            "updated_at": runtime.get("updated_at"),
            "command": runtime.get("command"),
            "command_phase_id": _agent_wake_phase_id_from_text(runtime.get("command")),
        },
        "closeout_gap": {
            "pending": closeout.get("pending_closeout_count") or 0,
            "failed": closeout.get("failed_recovery_count") or 0,
            "failed_dispositioned": closeout.get("failed_dispositioned_count") or 0,
            "failed_unresolved": (
                closeout.get("failed_unresolved_count")
                if closeout.get("failed_unresolved_count") is not None
                else closeout.get("failed_recovery_count") or 0
            ),
            "failed_historic": closeout.get("failed_historic_count") or 0,
            "inflight": closeout.get("inflight_count") or 0,
            "orphaned": closeout.get("orphaned_count") or 0,
        },
        "docs_route_example": dp.get("docs_route_example"),
        "hologram": {
            "exists": bool(builder.get("exists")),
            "all_current": bool(builder.get("all_current")),
            "stale_phases": builder.get("stale_phases"),
            "stale_phase_names": list(builder.get("stale_phase_names") or [])[:6],
        },
        "doctrine": {
            "total_docs": doctrine.get("total_docs"),
            "drift_docs": doctrine.get("drift_docs"),
            "graph_docs": doctrine.get("graph_docs"),
        },
        "recommended_actions": list(snapshot.get("recommended_actions") or [])[:4],
        "decision_tree": list(snapshot.get("decision_tree") or [])[:6],
    }


def _agent_wake_phase_packet(phase_token: str | None) -> tuple[dict[str, Any], dict[str, list[str]], list[str]]:
    navigator = KernelNavigation(state.REPO_ROOT)
    # The wake packet is the compact reentry surface (analog of `band == "card"`),
    # so the transaction control plane is intentionally omitted to keep the
    # packet bounded. Setting this explicitly avoids a dangling `band` reference
    # that crashed wake-packet rendering with `name 'band' is not defined`.
    result = navigator.build_phase(
        phase_token,
        include_transaction_control_plane=False,
    )
    phase_dict = result.to_dict(state.KERNEL_VERSION, full=True)
    payload = phase_dict.get("payload") if isinstance(phase_dict.get("payload"), Mapping) else {}
    phase = payload.get("phase") if isinstance(payload.get("phase"), Mapping) else {}
    phase_card = payload.get("phase_card") if isinstance(payload.get("phase_card"), Mapping) else {}
    active_wave = phase_card.get("active_wave") if isinstance(phase_card.get("active_wave"), Mapping) else {}
    target_paths = list(active_wave.get("target_paths") or []) if isinstance(active_wave.get("target_paths"), list) else []
    family_anchor = phase_card.get("family_anchor") if isinstance(phase_card.get("family_anchor"), Mapping) else {}
    return (
        {
            "phase_id": phase.get("phase_id"),
            "phase_number": phase.get("phase_number"),
            "phase_title": phase.get("phase_title"),
            "status": phase.get("status"),
            "execution_mode": phase.get("execution_mode"),
            "canonical_entry": phase_dict.get("summary", {}).get("canonical_entry")
            if isinstance(phase_dict.get("summary"), Mapping)
            else None,
            "family_anchor": {
                "path": family_anchor.get("path"),
                "broad_goal": _agent_wake_truncate(family_anchor.get("broad_goal"), 220),
            },
            "active_wave": {
                "wave_id": active_wave.get("wave_id"),
                "mode": active_wave.get("mode"),
                "status": active_wave.get("status"),
                "objective": active_wave.get("objective"),
                "bounded_question": active_wave.get("bounded_question"),
                "target_path_count": len(target_paths),
                "target_paths": target_paths[:8],
            },
            "last_outcome": phase_card.get("last_outcome"),
            "next_step_posture": phase_card.get("next_step_posture"),
        },
        {
            "live": list((phase_dict.get("sources") or {}).get("live") or []),
            "derived": list((phase_dict.get("sources") or {}).get("derived") or []),
        },
        _agent_wake_warning_slice(phase_dict.get("warnings")),
    )


def _agent_wake_view_graph_check() -> tuple[dict[str, Any], list[str]]:
    script = state.REPO_ROOT / "tools" / "meta" / "observability" / "frontend_nav_graph.py"
    if not script.exists():
        return (
            {
                "ok": None,
                "error": f"Missing {state.rel(script)}",
                "counts": {},
            },
            [f"view graph check skipped because {state.rel(script)} is missing"],
        )
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=str(state.REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - this is a degraded read-only packet
        return (
            {
                "ok": False,
                "error": str(exc),
                "counts": {},
            },
            [f"view graph check failed: {exc}"],
        )
    parsed: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            raw = json.loads(proc.stdout)
            if isinstance(raw, dict):
                parsed = raw
        except json.JSONDecodeError:
            parsed = {}
    ok = bool(parsed.get("ok")) if parsed else proc.returncode == 0
    packet = {
        "ok": ok,
        "returncode": proc.returncode,
        "counts": dict(parsed.get("counts") or {}) if parsed else {},
    }
    warnings: list[str] = []
    if proc.returncode != 0:
        warnings.append(f"view graph check exited {proc.returncode}")
    if proc.stderr.strip():
        packet["stderr"] = _agent_wake_truncate(proc.stderr, 320)
    if not parsed and proc.stdout.strip():
        packet["stdout_preview"] = _agent_wake_truncate(proc.stdout, 320)
    return packet, warnings


def _agent_wake_projection_coverage() -> tuple[dict[str, Any], list[str]]:
    base_dir = state.REPO_ROOT / _AGENT_WAKE_RAW_SEED_PROJECTION_DIR
    summary_path = base_dir / "summary.json"
    ledger_path = base_dir / "ledger.json"
    expected_paths = [
        state.rel(base_dir / name)
        for name in ("summary.json", "ledger.json", "audit.json", "navigation_cache.json")
    ]

    payload: dict[str, Any] | None = None
    source_path: Path | None = None
    parse_errors: list[str] = []
    for candidate in (summary_path, ledger_path):
        if not candidate.exists():
            continue
        loaded, error = safe_load_json_with_error(candidate)
        if error:
            parse_errors.append(f"{state.rel(candidate)}: {error}")
            continue
        if loaded is not None:
            payload = loaded
            source_path = candidate
            break

    if payload is None:
        missing = [path for path in (summary_path, ledger_path) if not path.exists()]
        status = "missing_generated_projection" if missing else "malformed_generated_projection"
        reason = (
            "raw-seed projection summary/ledger is not materialized"
            if missing
            else "raw-seed projection summary/ledger could not be parsed"
        )
        return (
            {
                "status": status,
                "reason": reason,
                "summary": {},
                "themes": [],
                "expected_paths": expected_paths,
                "parse_errors": parse_errors,
                "refresh_command": _AGENT_WAKE_RAW_SEED_REFRESH_COMMAND,
                "check_command": _AGENT_WAKE_RAW_SEED_CHECK_COMMAND,
                "degraded": True,
            },
            [f"{reason}; run {_AGENT_WAKE_RAW_SEED_REFRESH_COMMAND}"],
        )

    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    if source_path == summary_path:
        theme_rows = payload.get("top_themes") if isinstance(payload.get("top_themes"), list) else []
        gap_rows = payload.get("top_gaps") if isinstance(payload.get("top_gaps"), list) else []
    else:
        theme_rows = payload.get("themes") if isinstance(payload.get("themes"), list) else []
        gap_rows = []

    themes = [
        {
            "theme_id": row.get("theme_id"),
            "gap_state": row.get("gap_state"),
            "recommended_next_action": row.get("recommended_next_action"),
            "gap_signals": list(row.get("gap_signals") or [])[:4],
        }
        for row in list(theme_rows or [])[:5]
        if isinstance(row, Mapping)
    ]
    top_gaps = [
        {
            "theme_id": row.get("theme_id"),
            "gap_state": row.get("gap_state"),
            "recommended_next_action": row.get("recommended_next_action"),
            "severity": row.get("severity"),
        }
        for row in list(gap_rows or [])[:5]
        if isinstance(row, Mapping)
    ]
    return {
        "status": "materialized",
        "source_path": state.rel(source_path),
        "generated_at": payload.get("generated_at"),
        "summary": dict(summary),
        "themes": themes,
        "top_gaps": top_gaps,
        "refresh_command": _AGENT_WAKE_RAW_SEED_REFRESH_COMMAND,
        "check_command": _AGENT_WAKE_RAW_SEED_CHECK_COMMAND,
        "degraded": False,
    }, []


def _agent_wake_compact_session(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = row.get("external_metadata") if isinstance(row.get("external_metadata"), Mapping) else {}
    return {
        "session_id": row.get("session_id"),
        "actor": row.get("actor"),
        "phase_id": row.get("phase_id"),
        "idle_seconds": row.get("idle_seconds"),
        "stale": bool(row.get("stale")),
        "orphaned_active": bool(row.get("orphaned_active")),
        "title": row.get("external_title") or metadata.get("external_title"),
        "touched_td_ids": list(row.get("touched_td_ids") or [])[:5],
        "active_claim_count": len(row.get("active_claims") or []),
    }


def _agent_wake_work_ledger(limit: int) -> tuple[dict[str, Any], list[str]]:
    try:
        from system.lib import work_ledger_runtime

        overview = work_ledger_runtime.build_session_cohort_overview(
            work_ledger_runtime.load_runtime_status(state.REPO_ROOT),
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 - keep wake packet usable when ledger is unavailable
        return {"error": str(exc), "counts": {}, "risk_level": None}, [f"work-ledger overview failed: {exc}"]
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    count_keys = (
        "sessions_total",
        "active_sessions",
        "effective_active_sessions",
        "orphaned_active_sessions",
        "stale_sessions",
        "active_claims",
        "claim_collisions",
        "unclaimed_touched_sessions",
    )
    return {
        "schema": overview.get("schema"),
        "generated_at": overview.get("generated_at"),
        "risk_level": contention.get("risk_level"),
        "signals": list(contention.get("signals") or []),
        "counts": {key: counts.get(key, 0) for key in count_keys},
        "effective_active_sessions": [
            _agent_wake_compact_session(row)
            for row in list(overview.get("effective_active_sessions") or [])[:limit]
            if isinstance(row, Mapping)
        ],
        "orphaned_active_sessions": [
            _agent_wake_compact_session(row)
            for row in list(overview.get("orphaned_active_sessions") or [])[: min(limit, 4)]
            if isinstance(row, Mapping)
        ],
        "recommended_actions": list(overview.get("recommended_actions") or [])[:4],
    }, []


def _agent_wake_phase_agreement(
    *,
    phase_id: str | None,
    pulse_packet: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    frontier = pulse_packet.get("frontier") if isinstance(pulse_packet.get("frontier"), Mapping) else {}
    runtime = pulse_packet.get("runtime") if isinstance(pulse_packet.get("runtime"), Mapping) else {}
    frontier_phase_id = frontier.get("phase_id")
    runtime_phase_id = runtime.get("command_phase_id")
    mismatches: list[dict[str, str]] = []
    if phase_id and frontier_phase_id and frontier_phase_id != phase_id:
        mismatches.append({"surface": "pulse.frontier", "expected": phase_id, "actual": str(frontier_phase_id)})
    if phase_id and runtime_phase_id and runtime_phase_id != phase_id:
        mismatches.append({"surface": "pulse.runtime.command", "expected": phase_id, "actual": str(runtime_phase_id)})
    warnings = [
        (
            f"phase/pulse disagreement: {item['surface']} points at {item['actual']} "
            f"while active phase packet is {item['expected']}"
        )
        for item in mismatches
    ]
    return {
        "status": "agree" if not mismatches else "warning",
        "phase_id": phase_id,
        "pulse_frontier_phase_id": frontier_phase_id,
        "pulse_runtime_command_phase_id": runtime_phase_id,
        "mismatches": mismatches,
    }, warnings


def _agent_wake_compact_workitem_entrypoint(
    workitem_entrypoint: Mapping[str, Any],
    *,
    backlog_health: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep the wake packet bounded while still carrying the WorkItem entrypoint."""
    task_ledger = (
        workitem_entrypoint.get("task_ledger")
        if isinstance(workitem_entrypoint.get("task_ledger"), Mapping)
        else {}
    )
    phase_freshness = (
        workitem_entrypoint.get("phase_freshness")
        if isinstance(workitem_entrypoint.get("phase_freshness"), Mapping)
        else {}
    )
    concurrency_attention = (
        workitem_entrypoint.get("concurrency_attention")
        if isinstance(workitem_entrypoint.get("concurrency_attention"), Mapping)
        else {}
    )
    subphase_runtime_attention = (
        workitem_entrypoint.get("subphase_runtime_attention")
        if isinstance(workitem_entrypoint.get("subphase_runtime_attention"), Mapping)
        else {}
    )
    strict_json_attention = (
        workitem_entrypoint.get("strict_json_artifact_attention")
        if isinstance(workitem_entrypoint.get("strict_json_artifact_attention"), Mapping)
        else {}
    )
    applicable_mechanisms = [
        item
        for item in (workitem_entrypoint.get("applicable_mechanisms") or [])
        if isinstance(item, Mapping)
    ]
    backlog_attention = (
        workitem_entrypoint.get("workitem_backlog_attention")
        if isinstance(workitem_entrypoint.get("workitem_backlog_attention"), Mapping)
        else {}
    )
    task_views = task_ledger.get("views") if isinstance(task_ledger.get("views"), Mapping) else {}
    work_ledger = (
        workitem_entrypoint.get("work_ledger")
        if isinstance(workitem_entrypoint.get("work_ledger"), Mapping)
        else {}
    )
    commit = (
        workitem_entrypoint.get("commit_readiness")
        if isinstance(workitem_entrypoint.get("commit_readiness"), Mapping)
        else {}
    )
    affordances = []
    for item in workitem_entrypoint.get("projection_affordances") or []:
        if not isinstance(item, Mapping):
            continue
        affordances.append(
            {
                "kind": item.get("kind"),
                "id": item.get("id"),
                "authority": item.get("authority"),
                "source_authority": item.get("source_authority"),
                "mutation_rule": item.get("mutation_rule"),
            }
        )
    return {
        "schema_version": workitem_entrypoint.get("schema_version"),
        "mode": workitem_entrypoint.get("mode"),
        "dirty_tree_allowed": workitem_entrypoint.get("dirty_tree_allowed"),
        "destructive_overwrite_allowed": workitem_entrypoint.get("destructive_overwrite_allowed"),
        "safe_to_continue": workitem_entrypoint.get("safe_to_continue"),
        "blocked_only_by": workitem_entrypoint.get("blocked_only_by") or [],
        "dirty_surface_classes": workitem_entrypoint.get("dirty_surface_classes") or {},
        "strict_validation_obligations": workitem_entrypoint.get("strict_validation_obligations") or {},
        "commit_readiness": {
            "safe_to_commit_scoped_progress": commit.get("safe_to_commit_scoped_progress"),
            "scoped_changed_paths": commit.get("scoped_changed_paths") or [],
            "commit_blockers": commit.get("commit_blockers") or [],
            "unrelated_dirty_path_count": commit.get("unrelated_dirty_path_count"),
            "recommended_commit_message": commit.get("recommended_commit_message"),
        },
        "task_ledger": {
            "authority": task_ledger.get("authority"),
            "counts": task_ledger.get("counts") or {},
            "views": {
                key: {
                    "path": value.get("path"),
                    "count": value.get("count"),
                    "projection_only": value.get("projection_only"),
                }
                for key, value in task_views.items()
                if isinstance(value, Mapping)
            },
        },
        "workitem_backlog_health": dict(backlog_health),
        "workitem_backlog_attention": {
            "authority": backlog_attention.get("authority"),
            "source_authority": backlog_attention.get("source_authority"),
            "capture_count": backlog_attention.get("capture_count"),
            "incomplete_count": backlog_attention.get("incomplete_count"),
            "blocked_count": backlog_attention.get("blocked_count"),
            "ready_by_rank_count": backlog_attention.get("ready_by_rank_count"),
            "capture_inbox_count": backlog_attention.get("capture_inbox_count"),
            "missing_satisfaction_contract_count": backlog_attention.get("missing_satisfaction_contract_count"),
            "missing_integration_contract_count": backlog_attention.get("missing_integration_contract_count"),
            "stale_review_count": backlog_attention.get("stale_review_count"),
            "unranked_capture_count": backlog_attention.get("unranked_capture_count"),
            "top_ready_workitem_ids": [
                item.get("id")
                for item in (backlog_attention.get("top_ready_workitems") or [])[:5]
                if isinstance(item, Mapping)
            ],
            "top_blocked_workitem_ids": [
                item.get("id")
                for item in (backlog_attention.get("top_blocked_workitems") or [])[:5]
                if isinstance(item, Mapping)
            ],
            "newest_capture_ids": [
                item.get("id")
                for item in (backlog_attention.get("newest_captures_sample") or [])[:5]
                if isinstance(item, Mapping)
            ],
            "note": backlog_attention.get("note"),
        },
        "phase_freshness": {
            "freshness_status": phase_freshness.get("freshness_status"),
            "requested_phase": phase_freshness.get("requested_phase"),
            "kernel_reported_phase": phase_freshness.get("kernel_reported_phase"),
            "explicit_active_phase": phase_freshness.get("explicit_active_phase"),
            "active_subphase": phase_freshness.get("active_subphase"),
            "focus_conflict_count": phase_freshness.get("focus_conflict_count"),
            "phase_staleness_reason": phase_freshness.get("phase_staleness_reason") or [],
            "recommended_actions": (phase_freshness.get("recommended_actions") or [])[:3],
        },
        "concurrency_attention": {
            "safe_parallelism_status": concurrency_attention.get("safe_parallelism_status"),
            "why_status": (concurrency_attention.get("why_status") or [])[:4],
            "active_sessions": concurrency_attention.get("active_sessions"),
            "effective_active_sessions": concurrency_attention.get("effective_active_sessions"),
            "active_claims": concurrency_attention.get("active_claims"),
            "claim_collisions": concurrency_attention.get("claim_collisions"),
            "requested_target_claim_collision_count": len(concurrency_attention.get("requested_target_claim_collisions") or []),
            "stale_sessions": concurrency_attention.get("stale_sessions"),
            "orphaned_active_sessions": concurrency_attention.get("orphaned_active_sessions"),
            "unknown_scope_active_sessions": concurrency_attention.get("unknown_scope_active_sessions"),
            "recommended_actions": (concurrency_attention.get("recommended_actions") or [])[:4],
        },
        "subphase_runtime_attention": {
            "runtime_status": subphase_runtime_attention.get("runtime_status"),
            "phase_id": subphase_runtime_attention.get("phase_id"),
            "subphase_id": subphase_runtime_attention.get("subphase_id"),
            "phase_freshness_status": subphase_runtime_attention.get("phase_freshness_status"),
            "safe_parallelism_status": subphase_runtime_attention.get("safe_parallelism_status"),
            "subphase_allocation_status": subphase_runtime_attention.get("subphase_allocation_status"),
            "execution_menu_ids": (subphase_runtime_attention.get("execution_menu_ids") or [])[:7],
            "selected_lane_hint": subphase_runtime_attention.get("selected_lane_hint") or {},
            "blocker_count": subphase_runtime_attention.get("blocker_count"),
            "warning_count": subphase_runtime_attention.get("warning_count"),
            "recommended_next_legal_actions": (
                subphase_runtime_attention.get("recommended_next_legal_actions") or []
            )[:4],
        },
        "applicable_mechanisms": [
            {
                "mechanism_id": item.get("mechanism_id"),
                "source_path": item.get("source_path"),
                "why_applicable_now": item.get("why_applicable_now"),
                "owner_tool": item.get("owner_tool"),
                "applicability": item.get("applicability"),
                "implementation_status": item.get("implementation_status"),
            }
            for item in applicable_mechanisms[:8]
        ],
        "strict_json_artifact_attention": {
            "status": strict_json_attention.get("status"),
            "strict_json_checked_count": strict_json_attention.get("strict_json_checked_count"),
            "blocker_count": len(strict_json_attention.get("missing_or_unknown_artifact_classes") or []),
            "scoped_obligation_count": len(strict_json_attention.get("scoped_target_obligations") or []),
            "standard_path": strict_json_attention.get("standard_path"),
            "strict_validation_commands": (strict_json_attention.get("strict_validation_commands") or [])[:3],
            "projection_check_commands": (strict_json_attention.get("projection_check_commands") or [])[:3],
            "failure_policy": (strict_json_attention.get("failure_policy") or [])[:4],
        },
        "work_ledger": {
            "authority": work_ledger.get("authority"),
            "risk_level": work_ledger.get("risk_level"),
            "counts": work_ledger.get("counts") or {},
            "claim_required_before_mutation": work_ledger.get("claim_required_before_mutation"),
            "closeout_before_finalize_required": work_ledger.get("closeout_before_finalize_required"),
        },
        "projection_affordances": affordances,
        "drilldown_command": "./repo-python kernel.py --workitem-entrypoint <phase>",
    }


def _agent_wake_fast_workitem_entrypoint(
    *,
    phase_packet: Mapping[str, Any],
    work_ledger: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Build the wake-packet WorkItem slice from materialized projections.

    The standalone --workitem-entrypoint route still replays Task Ledger
    authority. The wake packet is a bounded reentry card and should not spend
    its timeout rebuilding the full event projection when materialized views are
    already present.
    """
    try:
        from system.lib.workitem_runtime_entrypoint import (
            _strict_json_artifact_attention_packet,
            _task_ledger_materialized_projection_packet,
            _workitem_backlog_attention_packet,
            _workitem_backlog_health_packet,
        )
    except Exception as exc:  # noqa: BLE001 - wake packet should degrade instead of timing out
        return (
            {
                "kind": "kernel.workitem_runtime_entrypoint",
                "schema_version": "workitem_runtime_entrypoint_v1",
                "mode": "agent_wake_fast_projection",
                "safe_to_continue": False,
                "blocked_only_by": ["workitem_fast_projection_import_failed"],
                "error": str(exc),
            },
            [f"workitem fast projection import failed: {exc}"],
        )

    task_ledger, task_blockers = _task_ledger_materialized_projection_packet(state.REPO_ROOT)
    backlog_health = _workitem_backlog_health_packet(task_ledger, prompt_trace={})
    backlog_attention = _workitem_backlog_attention_packet(task_ledger, backlog_health=backlog_health)
    strict_json_attention = _strict_json_artifact_attention_packet(task_ledger, repo_root=state.REPO_ROOT, target_paths=[])

    counts = work_ledger.get("counts") if isinstance(work_ledger.get("counts"), Mapping) else {}
    risk_level = str(work_ledger.get("risk_level") or "unknown")
    if risk_level == "blocked" or int(counts.get("claim_collisions") or 0) > 0:
        parallelism_status = "blocked"
    elif (
        risk_level in {"watch", "unknown"}
        or int(counts.get("orphaned_active_sessions") or 0) > 0
        or int(counts.get("stale_sessions") or 0) > 0
        or int(counts.get("effective_active_sessions") or 0) > 1
    ):
        parallelism_status = "watch"
    else:
        parallelism_status = "safe"

    active_wave = phase_packet.get("active_wave") if isinstance(phase_packet.get("active_wave"), Mapping) else {}
    phase_id = str(phase_packet.get("phase_id") or "").strip() or None
    subphase_id = str(active_wave.get("wave_id") or "").strip() or None
    recommended_ids = [
        item.get("id")
        for item in (backlog_health.get("recommended_next_workitems") or [])
        if isinstance(item, Mapping) and item.get("id")
    ][:7]
    freshness_status = "current" if phase_id else "unknown"
    phase_freshness = {
        "freshness_status": freshness_status,
        "requested_phase": phase_id or "__active__",
        "kernel_reported_phase": phase_id,
        "explicit_active_phase": phase_id,
        "active_subphase": {
            "subphase_id": subphase_id,
            "status": active_wave.get("status"),
            "objective": active_wave.get("objective"),
        },
        "focus_conflict_count": 0,
        "phase_staleness_reason": [],
        "recommended_actions": [
            {
                "command": f"./repo-python kernel.py --phase-step {phase_id or '<phase>'}",
                "reason": "Preview the controller-owned next bounded wave action before mutation.",
            }
        ],
    }
    warning_count = 0 if parallelism_status == "safe" and freshness_status == "current" else 1
    blocker_count = 1 if parallelism_status == "blocked" else 0
    subphase_runtime_attention = {
        "runtime_status": "blocked" if blocker_count else ("watch" if warning_count else "ready"),
        "phase_id": phase_id,
        "subphase_id": subphase_id,
        "phase_freshness_status": freshness_status,
        "safe_parallelism_status": parallelism_status,
        "subphase_allocation_status": "agent_wake_projection_only",
        "execution_menu_ids": recommended_ids,
        "selected_lane_hint": {
            "work_item_id": recommended_ids[0] if recommended_ids else "<work_item_id>",
            "reason": "Use the first execution-menu WorkItem unless live blockers or operator direction select another proof.",
        },
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "recommended_next_legal_actions": [
            "choose implementation work from execution_menu_schedulable ids first, then schedulable_by_rank",
            "claim target paths through Work Ledger before mutation",
            "use the full --workitem-entrypoint route for target-aware commit readiness",
        ],
    }
    concurrency_attention = {
        "safe_parallelism_status": parallelism_status,
        "why_status": work_ledger.get("signals") or [],
        "active_sessions": counts.get("active_sessions"),
        "effective_active_sessions": counts.get("effective_active_sessions"),
        "active_claims": counts.get("active_claims"),
        "claim_collisions": counts.get("claim_collisions"),
        "stale_sessions": counts.get("stale_sessions"),
        "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
        "unknown_scope_active_sessions": None,
        "requested_target_claim_collisions": [],
        "recommended_actions": work_ledger.get("recommended_actions") or [],
    }
    blocked_only_by = [str(item.get("kind") or "unknown_blocker") for item in task_blockers if isinstance(item, Mapping)]
    return (
        {
            "kind": "kernel.workitem_runtime_entrypoint",
            "schema_version": "workitem_runtime_entrypoint_v1",
            "mode": "agent_wake_fast_projection",
            "dirty_tree_allowed": True,
            "destructive_overwrite_allowed": False,
            "safe_to_continue": not blocked_only_by and parallelism_status != "blocked",
            "blocked_only_by": blocked_only_by,
            "dirty_surface_classes": {},
            "strict_validation_obligations": {
                "paths": [],
                "rule": "wake packet uses materialized projection; run --workitem-entrypoint for target-aware validation",
            },
            "commit_readiness": {
                "safe_to_commit_scoped_progress": None,
                "scoped_changed_paths": [],
                "commit_blockers": ["target_scope_not_evaluated_in_agent_wake_packet"],
                "unrelated_dirty_path_count": None,
                "recommended_commit_message": "",
            },
            "task_ledger": task_ledger,
            "workitem_backlog_health": backlog_health,
            "workitem_backlog_attention": backlog_attention,
            "work_ledger": {
                "authority": "state/work_ledger/runtime_status.json",
                "risk_level": work_ledger.get("risk_level"),
                "counts": counts,
                "claim_required_before_mutation": True,
                "closeout_before_finalize_required": True,
            },
            "concurrency_attention": concurrency_attention,
            "strict_json_artifact_attention": strict_json_attention,
            "subphase_runtime_attention": subphase_runtime_attention,
            "phase_freshness": phase_freshness,
            "applicable_mechanisms": [],
            "projection_affordances": [
                {
                    "kind": "workitem_backlog_health_projection",
                    "id": "capture_inbox_execution_menu",
                    "authority": "projection_only",
                    "source_authority": "state/task_ledger/events.jsonl",
                    "mutation_rule": "append Task Ledger events; projections are read-only",
                },
                {
                    "kind": "work_ledger_concurrency_projection",
                    "id": "concurrency_attention",
                    "authority": "projection_only",
                    "source_authority": "state/work_ledger/runtime_status.json",
                    "mutation_rule": "claim/release/close through Work Ledger",
                },
            ],
        },
        [],
    )


def cmd_agent_wake_packet(phase_token: str | None = None, *, limit: int = 6) -> int:
    """Emit one bounded wake packet for Type A agent reentry and movement efficiency."""
    warnings: list[str] = []
    try:
        pulse_snapshot = _pulse_snapshot()
    except Exception as exc:  # noqa: BLE001 - kernel command should return JSON
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.agent_wake_packet",
                "query": {"command": "agent-wake-packet", "phase": phase_token or "__active__"},
                "error": f"failed to build pulse snapshot: {exc}",
            },
            2,
        )
    pulse_packet = _agent_wake_pulse_packet(pulse_snapshot)
    try:
        phase_packet, phase_sources, phase_warnings = _agent_wake_phase_packet(phase_token)
        warnings.extend(phase_warnings)
    except Exception as exc:  # noqa: BLE001 - degraded packet is more useful than a hard fail
        phase_packet = {"error": str(exc), "phase_id": None}
        phase_sources = {"live": [], "derived": []}
        warnings.append(f"phase packet failed: {exc}")
    view_graph, view_warnings = _agent_wake_view_graph_check()
    projection_coverage, projection_warnings = _agent_wake_projection_coverage()
    work_ledger, work_warnings = _agent_wake_work_ledger(limit)
    warnings.extend(view_warnings)
    warnings.extend(projection_warnings)
    warnings.extend(work_warnings)
    workitem_entrypoint, fast_workitem_warnings = _agent_wake_fast_workitem_entrypoint(
        phase_packet=phase_packet,
        work_ledger=work_ledger,
    )
    warnings.extend(fast_workitem_warnings)
    agreement, agreement_warnings = _agent_wake_phase_agreement(
        phase_id=phase_packet.get("phase_id") if isinstance(phase_packet, Mapping) else None,
        pulse_packet=pulse_packet,
    )
    warnings.extend(agreement_warnings)
    projection_summary = (
        projection_coverage.get("summary")
        if isinstance(projection_coverage.get("summary"), Mapping)
        else {}
    )
    work_counts = work_ledger.get("counts") if isinstance(work_ledger.get("counts"), Mapping) else {}
    workitem_blockers = workitem_entrypoint.get("blocked_only_by") if isinstance(workitem_entrypoint, Mapping) else []
    workitem_backlog = (
        workitem_entrypoint.get("workitem_backlog_health")
        if isinstance(workitem_entrypoint, Mapping) and isinstance(workitem_entrypoint.get("workitem_backlog_health"), Mapping)
        else {}
    )
    workitem_phase_freshness = (
        workitem_entrypoint.get("phase_freshness")
        if isinstance(workitem_entrypoint, Mapping) and isinstance(workitem_entrypoint.get("phase_freshness"), Mapping)
        else {}
    )
    workitem_concurrency = (
        workitem_entrypoint.get("concurrency_attention")
        if isinstance(workitem_entrypoint, Mapping) and isinstance(workitem_entrypoint.get("concurrency_attention"), Mapping)
        else {}
    )
    workitem_subphase_runtime = (
        workitem_entrypoint.get("subphase_runtime_attention")
        if isinstance(workitem_entrypoint, Mapping)
        and isinstance(workitem_entrypoint.get("subphase_runtime_attention"), Mapping)
        else {}
    )
    workitem_strict_json = (
        workitem_entrypoint.get("strict_json_artifact_attention")
        if isinstance(workitem_entrypoint, Mapping)
        and isinstance(workitem_entrypoint.get("strict_json_artifact_attention"), Mapping)
        else {}
    )
    recommended_next = [
        item.get("id")
        for item in (workitem_backlog.get("recommended_next_workitems") or [])
        if isinstance(item, Mapping) and item.get("id")
    ][:7]
    compact_backlog_health = {
        "capture_inbox_count": workitem_backlog.get("capture_inbox_count"),
        "incomplete_count": workitem_backlog.get("incomplete_count"),
        "shaped_ready_count": workitem_backlog.get("shaped_ready_count"),
        "blocked_count": workitem_backlog.get("blocked_count"),
        "missing_contract_count": workitem_backlog.get("missing_contract_count"),
        "duplicate_or_retire_candidate_count": workitem_backlog.get("duplicate_or_retire_candidate_count"),
        "prompt_linked_count": workitem_backlog.get("prompt_linked_count"),
        "work_ledger_linked_count": workitem_backlog.get("work_ledger_linked_count"),
        "execution_menu_count": workitem_backlog.get("execution_menu_count"),
        "recommended_next_workitem_ids": recommended_next,
        "why_these_next": (workitem_backlog.get("why_these_next") or [])[:5],
        "wip_policy": workitem_backlog.get("wip_policy"),
    }
    compact_phase_freshness = {
        "freshness_status": workitem_phase_freshness.get("freshness_status"),
        "requested_phase": workitem_phase_freshness.get("requested_phase"),
        "kernel_reported_phase": workitem_phase_freshness.get("kernel_reported_phase"),
        "explicit_active_phase": workitem_phase_freshness.get("explicit_active_phase"),
        "active_subphase": workitem_phase_freshness.get("active_subphase"),
        "focus_conflict_count": workitem_phase_freshness.get("focus_conflict_count"),
        "phase_staleness_reason": (workitem_phase_freshness.get("phase_staleness_reason") or [])[:5],
        "recommended_actions": (workitem_phase_freshness.get("recommended_actions") or [])[:3],
    }
    compact_concurrency_attention = {
        "safe_parallelism_status": workitem_concurrency.get("safe_parallelism_status"),
        "why_status": (workitem_concurrency.get("why_status") or [])[:4],
        "active_sessions": workitem_concurrency.get("active_sessions"),
        "effective_active_sessions": workitem_concurrency.get("effective_active_sessions"),
        "active_claims": workitem_concurrency.get("active_claims"),
        "claim_collisions": workitem_concurrency.get("claim_collisions"),
        "requested_target_claim_collision_count": len(workitem_concurrency.get("requested_target_claim_collisions") or []),
        "stale_sessions": workitem_concurrency.get("stale_sessions"),
        "orphaned_active_sessions": workitem_concurrency.get("orphaned_active_sessions"),
        "unknown_scope_active_sessions": workitem_concurrency.get("unknown_scope_active_sessions"),
        "recommended_actions": (workitem_concurrency.get("recommended_actions") or [])[:4],
    }
    compact_subphase_runtime_attention = {
        "runtime_status": workitem_subphase_runtime.get("runtime_status"),
        "phase_id": workitem_subphase_runtime.get("phase_id"),
        "subphase_id": workitem_subphase_runtime.get("subphase_id"),
        "phase_freshness_status": workitem_subphase_runtime.get("phase_freshness_status"),
        "focus_conflict_count": workitem_subphase_runtime.get("focus_conflict_count"),
        "safe_parallelism_status": workitem_subphase_runtime.get("safe_parallelism_status"),
        "subphase_allocation_status": workitem_subphase_runtime.get("subphase_allocation_status"),
        "execution_menu_ids": (workitem_subphase_runtime.get("execution_menu_ids") or [])[:7],
        "selected_lane_hint": workitem_subphase_runtime.get("selected_lane_hint") or {},
        "blocker_count": workitem_subphase_runtime.get("blocker_count"),
        "warning_count": workitem_subphase_runtime.get("warning_count"),
        "top_recommended_action": (workitem_subphase_runtime.get("recommended_next_legal_actions") or [None])[0],
    }
    compact_strict_json_attention = {
        "status": workitem_strict_json.get("status"),
        "checked_count": workitem_strict_json.get("strict_json_checked_count"),
        "blocker_count": len(workitem_strict_json.get("missing_or_unknown_artifact_classes") or []),
        "scoped_obligation_count": len(workitem_strict_json.get("scoped_target_obligations") or []),
        "top_commands": (workitem_strict_json.get("strict_validation_commands") or [])[:3],
    }
    compact_workitem_entrypoint = _agent_wake_compact_workitem_entrypoint(
        workitem_entrypoint if isinstance(workitem_entrypoint, Mapping) else {},
        backlog_health=compact_backlog_health,
    )
    return emit_json(
        {
            "kind": "kernel.navigate.agent_wake_packet",
            "schema_version": "agent_wake_packet_v1",
            "query": {
                "command": "agent-wake-packet",
                "phase": phase_token or "__active__",
                "limit": limit,
            },
            "summary": {
                "active_phase_id": agreement.get("phase_id"),
                "phase_agreement": agreement.get("status"),
                "view_graph_ok": view_graph.get("ok"),
                "projection_theme_count": projection_summary.get("theme_count"),
                "projection_gap_state_counts": projection_summary.get("gap_state_counts"),
                "work_ledger_risk_level": work_ledger.get("risk_level"),
                "effective_active_sessions": work_counts.get("effective_active_sessions"),
                "workitem_entrypoint_mode": workitem_entrypoint.get("mode") if isinstance(workitem_entrypoint, Mapping) else None,
                "workitem_safe_to_continue": workitem_entrypoint.get("safe_to_continue") if isinstance(workitem_entrypoint, Mapping) else None,
                "workitem_blocker_count": len(workitem_blockers) if isinstance(workitem_blockers, list) else None,
                "workitem_capture_inbox_count": workitem_backlog.get("capture_inbox_count"),
                "workitem_execution_menu_count": workitem_backlog.get("execution_menu_count"),
                "workitem_missing_contract_count": workitem_backlog.get("missing_contract_count"),
                "workitem_prompt_linked_count": workitem_backlog.get("prompt_linked_count"),
                "workitem_work_ledger_linked_count": workitem_backlog.get("work_ledger_linked_count"),
                "workitem_phase_freshness_status": workitem_phase_freshness.get("freshness_status"),
                "workitem_phase_focus_conflict_count": workitem_phase_freshness.get("focus_conflict_count"),
                "workitem_safe_parallelism_status": workitem_concurrency.get("safe_parallelism_status"),
                "workitem_active_claim_count": workitem_concurrency.get("active_claims"),
                "workitem_claim_collision_count": workitem_concurrency.get("claim_collisions"),
                "workitem_unknown_scope_active_session_count": workitem_concurrency.get("unknown_scope_active_sessions"),
                "workitem_subphase_runtime_status": workitem_subphase_runtime.get("runtime_status"),
                "workitem_subphase_id": workitem_subphase_runtime.get("subphase_id"),
                "workitem_subphase_blocker_count": workitem_subphase_runtime.get("blocker_count"),
                "workitem_subphase_top_action": (
                    workitem_subphase_runtime.get("recommended_next_legal_actions") or [None]
                )[0],
                "workitem_strict_json_status": workitem_strict_json.get("status"),
                "workitem_strict_json_checked_count": workitem_strict_json.get("strict_json_checked_count"),
                "workitem_strict_json_blocker_count": len(
                    workitem_strict_json.get("missing_or_unknown_artifact_classes") or []
                ),
                "workitem_strict_json_scoped_obligation_count": len(
                    workitem_strict_json.get("scoped_target_obligations") or []
                ),
                "warning_count": len(warnings),
            },
            "sources": {
                "live": [
                    "tools/meta/control/orchestration_state.json",
                    "codex/doctrine/routing_hologram.json",
                    "tools/meta/observability/frontend_nav_graph.py",
                    "codex/standards/observe_apply/std_raw_seed_projection_coverage.json",
                    "system/lib/work_ledger_runtime.py",
                    "system/lib/workitem_runtime_entrypoint.py",
                    "codex/standards/std_forward_integration_policy.json",
                    *phase_sources.get("live", []),
                ],
                "derived": [
                    "codex/hologram/raw_seed_projection/ledger.json",
                    "codex/hologram/raw_seed_projection/summary.json",
                    "codex/hologram/process/summary.json",
                    *phase_sources.get("derived", []),
                ],
            },
            "payload": {
                "command_budget": {
                    "purpose": "Replace repeated cold-start orientation calls with one compact, read-only reentry packet.",
                    "replaces_commands": _AGENT_WAKE_REPLACES_COMMANDS,
                    "usual_next_commands": [
                        "./repo-python kernel.py --phase-step <phase>",
                        "./repo-python kernel.py --workitem-entrypoint <phase>",
                        "./repo-python kernel.py --process-trace latest",
                        "./repo-python kernel.py --session-diagnostics --lens ladder-skip --last 10 --store both --json",
                    ],
                },
                "phase_agreement": agreement,
                "pulse": pulse_packet,
                "phase": phase_packet,
                "view_graph_check": view_graph,
                "raw_seed_projection_coverage": projection_coverage,
                "work_ledger_overview": work_ledger,
                "workitem_backlog_health": compact_backlog_health,
                "workitem_phase_freshness": compact_phase_freshness,
                "workitem_concurrency_attention": compact_concurrency_attention,
                "workitem_subphase_runtime_attention": compact_subphase_runtime_attention,
                "workitem_strict_json_artifact_attention": compact_strict_json_attention,
                "workitem_runtime_entrypoint": compact_workitem_entrypoint,
            },
            "next": [
                {
                    "command": "./repo-python kernel.py --workitem-entrypoint <phase>",
                    "reason": "Default WorkItem runtime policy packet: target-aware dirty tree classification, projection affordances, commit readiness, and closeout obligations.",
                },
                {
                    "command": "./repo-python kernel.py --phase-step <phase>",
                    "reason": "Advance only after the wake packet confirms the phase and surrounding surfaces.",
                },
                {
                    "command": "./repo-python kernel.py --process-trace latest",
                    "reason": "Use the process trace when optimizing the next movement-efficiency axis.",
                },
            ],
            "warnings": warnings,
        }
    )


def cmd_agent_recent_activity(
    *,
    limit: int = 100,
    session_id: str | None = None,
    source_runtime: str | None = None,
) -> int:
    """Emit a bounded live-agent self-read from recent AgentEvent rows."""
    from system.lib.agent_recent_activity import build_agent_recent_activity

    return emit_json(
        build_agent_recent_activity(
            state.REPO_ROOT,
            history_limit=limit,
            cwd=str(Path.cwd()),
            session_id=session_id,
            source_runtime=source_runtime,
        )
    )


def cmd_host_pressure(
    *,
    window_s: int = 900,
    write_path: str | None = None,
    activation_url: str | None = None,
) -> int:
    """Emit the host-aware progress-pressure packet for parallel agents."""
    try:
        from system.lib.agent_observability import AgentTraceStore
        from system.lib.host_pressure import build_progress_pressure_packet_from_store

        store = AgentTraceStore(state.REPO_ROOT)
        packet = build_progress_pressure_packet_from_store(
            store,
            state.REPO_ROOT,
            window_s=window_s,
            activation_url=activation_url,
        )
        if write_path:
            target = Path(write_path).expanduser()
            if not target.is_absolute():
                target = state.REPO_ROOT / target
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            try:
                packet["written_path"] = str(target.relative_to(state.REPO_ROOT))
            except ValueError:
                packet["written_path"] = str(target)
    except Exception as exc:  # noqa: BLE001 - kernel command must return JSON
        return emit_json_with_code(
            {
                "kind": "progress_pressure_ledger",
                "schema_version": "progress_pressure_packet_v0",
                "error": f"{type(exc).__name__}: {exc}",
            },
            2,
        )
    return emit_json(packet)


def cmd_agent_experience_diagnostics(
    *,
    last: int = 50,
    event_limit: int = 5000,
    closeout_limit: int = 100,
    since_ts: str | None = None,
    grand_rounds: bool = False,
) -> int:
    """Emit read-only Grand Rounds diagnostics over agent experience evidence."""
    from system.lib.agent_experience_diagnostics import build_agent_experience_diagnostics

    return emit_json(
        build_agent_experience_diagnostics(
            state.REPO_ROOT,
            last=last,
            event_limit=event_limit,
            closeout_limit=closeout_limit,
            since_ts=since_ts,
            grand_rounds=grand_rounds,
        )
    )


def cmd_workitem_entrypoint(
    phase_token: str | None = None,
    *,
    target_paths: Sequence[str] | None = None,
    write_profiles: Sequence[str] | None = None,
    session_id: str | None = None,
    require_exclusive: bool = False,
    limit: int = 6,
) -> int:
    """Emit the WorkItem runtime entrypoint with forward-integration policy."""
    from system.lib.workitem_runtime_entrypoint import build_workitem_runtime_entrypoint

    payload = build_workitem_runtime_entrypoint(
        state.REPO_ROOT,
        phase_token=phase_token,
        target_paths=target_paths,
        write_profiles=write_profiles,
        session_id=session_id,
        require_exclusive=require_exclusive,
        limit=limit,
    )
    return emit_json(payload)


def _paper_module_broad_query_block(*, request: str) -> dict[str, Any]:
    raw = str(request or "").strip()
    debug_command = (
        f"./repo-python kernel.py --paper-module {shlex.quote(raw)} --debug"
        if raw
        else "./repo-python kernel.py --paper-module <stable_slug> --debug"
    )
    return {
        "kind": "kernel.route_policy",
        "schema_version": "navigation_surface_contract_v0",
        "surface": "./repo-python kernel.py --paper-module",
        "surface_id": "paper_module",
        "surface_role": DRILLDOWN,
        "first_contact_allowed": False,
        "status": "blocked_for_broad_query",
        "query": raw,
        "replacement": ENTRY_REPLACEMENT,
        "safe_drilldown": "./repo-python kernel.py --paper-module <stable_slug>",
        "debug_command": debug_command,
        "why": (
            "Broad paper-module queries are route selection, not legal first-contact drilldown. "
            "Enter through a control packet or pass an exact stable slug."
        ),
        "surface_contract": surface_contract(
            surface_id="paper_module",
            command="./repo-python kernel.py --paper-module",
            surface_role=DRILLDOWN,
            authority_plane="drilldown",
            first_contact_allowed=False,
            replacement=ENTRY_REPLACEMENT,
            debug_command=debug_command,
            safe_drilldown_replacement="./repo-python kernel.py --paper-module <stable_slug>",
            allowed_callers=[
                "entry_packet.selected_lane",
                "selected_stable_slug_drilldown",
                "operator_debug",
            ],
            banned_callers=[
                "agent_first_contact",
                "broad_query_route_selection_without_entry_packet",
            ],
            default_output_policy={
                "stable_slug": "allowed",
                "broad_query": "blocked",
                "debug_fields": "hidden",
            },
            debug_output_policy={
                "requires_flag": "--debug",
                "field_names": "visible",
            },
        ),
    }


def _paper_module_surface_result(result: NavigationResult, *, request: str, debug: bool) -> NavigationResult:
    payload = json.loads(json.dumps(result.payload))
    if not debug:
        payload = _strip_default_debug_fields(payload)
    payload["surface_role"] = DRILLDOWN
    payload["first_contact_allowed"] = False
    payload["control_replacement"] = ENTRY_REPLACEMENT
    payload["debug_trace_command"] = (
        f"./repo-python kernel.py --paper-module {shlex.quote(str(request or '').strip())} --debug"
    )
    payload["debug_fields_visible"] = bool(debug)
    payload["surface_contract"] = surface_contract(
        surface_id="paper_module",
        command="./repo-python kernel.py --paper-module",
        surface_role=DRILLDOWN,
        authority_plane="drilldown",
        first_contact_allowed=False,
        replacement=ENTRY_REPLACEMENT,
        debug_command=payload["debug_trace_command"],
        safe_drilldown_replacement="./repo-python kernel.py --paper-module <stable_slug>",
        allowed_callers=[
            "entry_packet.selected_lane",
            "selected_stable_slug_drilldown",
            "operator_debug" if debug else "explicit_operator_browse",
        ],
        banned_callers=[
            "agent_first_contact",
            "broad_query_route_selection_without_entry_packet",
        ],
        default_output_policy={
            "selected_slug": "visible",
            "debug_fields": "hidden",
            "ranked_matches": "hidden",
        },
        debug_output_policy={
            "requires_flag": "--debug",
            "field_names": "visible",
        },
    )
    return NavigationResult(
        kind=result.kind,
        query=result.query,
        payload=payload,
        live_sources=result.live_sources,
        derived_sources=result.derived_sources,
        suggested_next=result.suggested_next,
        warnings=result.warnings,
        derived_required=result.derived_required,
        compact_hints=result.compact_hints,
    )


def cmd_paper_module(request: str, *, debug: bool = False) -> int:
    """[ACTION]
    - Teleology: Resolve a subsystem query to the best matching paper module or typed missing-module candidate.
    - Mechanism: Delegate to `KernelNavigation.build_paper_module_lookup` and emit the resulting lookup packet.
    - Guarantee: Returns 0 after emitting the paper-module navigation result.
    - Fails: Returns 1 when the navigator cannot resolve the subsystem query.
    - When-needed: Open when a task names an existing subsystem and the controller should prefer the paper-module ontology layer over reopening source files.
    - Escalates-to: system/lib/kernel_navigation.py; codex/doctrine/paper_modules/_index.json
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    raw = str(request or "").strip()
    stable_slugs = set(navigator._paper_module_entry_by_slug().keys())
    if not debug and raw not in stable_slugs:
        return emit_json(_paper_module_broad_query_block(request=raw))
    try:
        result = navigator.build_paper_module_lookup(request)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    result = _paper_module_surface_result(result, request=request, debug=debug)
    record_navigation_result(
        state.REPO_ROOT,
        event_kind="paper_module",
        query=request,
        command="kernel.py --paper-module",
        payload=result.payload,
    )
    return emit_navigation(result)


def cmd_paper_module_coverage() -> int:
    """[ACTION]
    - Teleology: Emit paper-module coverage grouped by metadata route targets instead of forcing agents to infer it from prose or queue tables.
    - Mechanism: Delegate to `KernelNavigation.build_paper_module_route_coverage` and emit the generated coverage lens.
    - Guarantee: Returns 0 after emitting the route-coverage navigation result.
    - Fails: Returns 1 when the navigator cannot load the paper-module runtime.
    - When-needed: Open when a task asks what paper modules cover, what their metadata routes to, or which routes are saturated/thin.
    - Escalates-to: system/lib/kernel_navigation.py; codex/doctrine/paper_modules/_route_coverage.json
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_paper_module_route_coverage()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_paper_module_route(request: str) -> int:
    """[ACTION]
    - Teleology: Resolve a paper-module metadata route key or target to its generated health and coverage packet.
    - Mechanism: Delegate to `KernelNavigation.build_paper_module_route_lookup` and emit the resulting route-target packet.
    - Guarantee: Returns 0 after emitting the paper-module route navigation result.
    - Fails: Returns 1 when the navigator cannot load route coverage or the query is empty.
    - When-needed: Open when a task asks what modules route to one metadata target or which modules a route-health row covers.
    - Escalates-to: system/lib/kernel_navigation.py; codex/doctrine/paper_modules/_route_coverage.json
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_paper_module_route_lookup(request)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def _annotate_option_surface_payload(payload: dict[str, Any], *, artifact_kind: str) -> dict[str, Any]:
    command = f"./repo-python kernel.py --option-surface {artifact_kind} --band {payload.get('band') or 'flag'}"
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
    boundary = payload.setdefault("navigation_boundary", {})
    if isinstance(boundary, dict):
        boundary.setdefault("surface_role", ATLAS_PROJECTION)
        boundary.setdefault("first_contact_allowed", False)
        boundary.setdefault("control_replacement", ENTRY_REPLACEMENT)
        boundary.setdefault("allowed_after", "entry_packet_selected_kind_or_explicit_operator_browse")
        boundary.setdefault("not_control_entry", True)
    return payload


def cmd_option_surface(
    artifact_kind: str,
    *,
    band: str = "flag",
    ids: str | None = None,
    attention_frame: str | None = None,
) -> int:
    """Emit a standard-owned option surface by artifact kind and band."""
    normalized_kind = str(artifact_kind or "").strip().lower().replace("-", "_").replace(" ", "_")

    def _option_surface_exit_code(payload: dict[str, Any]) -> int:
        if payload.get("profile_status") == "supported":
            return 0
        if payload.get("profile_gap_kind") == "route_affordance_alias":
            return 0
        return 2

    def _emit_option_surface(payload: dict[str, Any]) -> int:
        if attention_frame:
            command_parts = [
                "./repo-python",
                "kernel.py",
                "--option-surface",
                str(artifact_kind),
                "--band",
                str(payload.get("band") or band or "flag"),
            ]
            if ids:
                command_parts.extend(["--ids", ids])
            command_parts.extend(["--attention-frame", attention_frame])
            attention_event = record_attention_event(
                state.REPO_ROOT,
                frame_id=attention_frame,
                event_type="surface_seen",
                command=" ".join(shlex.quote(part) for part in command_parts),
                payload=payload,
                metadata={"surface_command": "option_surface"},
                return_error=True,
            )
            if attention_event:
                frame_id = attention_event.get("frame_id")
                payload["attention_event"] = {
                    "schema_version": attention_event.get("schema_version"),
                    "status": attention_event.get("status") or "unknown",
                    "event_id": attention_event.get("event_id"),
                    "frame_id": frame_id,
                    "frame_id_requested": attention_event.get("frame_id_requested"),
                    "surface_id": attention_event.get("surface_id"),
                    "event_type": attention_event.get("event_type"),
                    "error_class": attention_event.get("error_class"),
                    "error": attention_event.get("error"),
                    "attention_state_command": f"./repo-python kernel.py --attention-state {frame_id} --band flag" if frame_id else None,
                }
                payload["attention_delta"] = attention_event.get("attention_delta") or {}
        return emit_json_with_code(payload, _option_surface_exit_code(payload))

    if normalized_kind in {"standards", "standard", "std", "stds"} and band == "flag" and not ids:
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="standards")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "standards all-row flag is a high-cardinality standards-registry expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface standards --band flag --ids <standard_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all standard row flags.",
                }
            )
        return _emit_option_surface(payload)
    if (
        normalized_kind
        in {
            "task_ledger",
            "task_ledger",
            "work_items",
            "work_item",
            "workitems",
            "workitem",
            "tasks",
            "task_spine",
            "work_item_spine",
        }
        and band == "flag"
        and not ids
    ):
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="task_ledger")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "task_ledger all-row flag is a high-cardinality private-state expansion; browse view clusters before WorkItem row expansion.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface task_ledger --band flag --ids <work_item_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all Task Ledger WorkItem row flags.",
                }
            )
        return _emit_option_surface(payload)
    if (
        normalized_kind
        in {
            "frontend_components",
            "frontend_component",
            "components",
            "component",
            "tsx_components",
            "ui_components",
        }
        and band == "flag"
        and not ids
    ):
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="frontend_components")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "frontend_components all-row flag is a high-cardinality component-index expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface frontend_components --band flag --ids <component_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all frontend component row flags.",
                }
            )
        return _emit_option_surface(payload)
    if normalized_kind in {"principles", "principle", "pri", "pri_rows", "raw_seed_principles"} and band == "flag" and not ids:
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="principles")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "principles all-row flag is a high-cardinality raw-seed-principles expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface principles --band flag --ids <pri_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all principle row flags.",
                }
            )
        return _emit_option_surface(payload)
    if (
        normalized_kind
        in {
            "annex_patterns",
            "annex_pattern",
            "annex_notes",
            "annex_note",
            "annex_pattern_rows",
        }
        and band == "flag"
        and not ids
    ):
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="annex_patterns")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "annex_patterns all-row flag is a high-cardinality annex-note expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface annex_patterns --band flag --ids <slug>:<note_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all annex pattern row flags.",
                }
            )
        return _emit_option_surface(payload)
    if normalized_kind in {"paper_modules", "paper_module"} and band == "flag" and not ids:
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="paper_modules")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "paper_modules all-row flag is a known high-cardinality overflow surface; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface paper_modules --band flag --ids <slug1>,<slug2>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all paper-module row flags.",
                }
            )
        return _emit_option_surface(payload)
    if normalized_kind in {"skills", "skill", "agent_skills", "agent_skill"} and band == "flag" and not ids:
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="skills")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "skills all-row flag is a known high-cardinality overflow surface; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface skills --band flag --ids <skill_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all skill row flags.",
                }
            )
        return _emit_option_surface(payload)
    if normalized_kind in {"python_files", "python_file", "py_files", "py_file"} and band == "flag" and not ids:
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="python_files")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "python_files all-row flag is a high-cardinality scope-index expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface python_files --band flag --ids <path>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all Python file row flags.",
                }
            )
        return _emit_option_surface(payload)
    if normalized_kind in {"python_scopes", "python_scope", "py_scopes", "py_scope"} and band == "flag" and not ids:
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="python_scopes")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "python_scopes all-row flag is a high-cardinality scope-index expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface python_scopes --band flag --ids <symbol_id>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all Python scope row flags.",
                }
            )
        return _emit_option_surface(payload)
    if (
        normalized_kind
        in {
            "annex_distillation_patterns",
            "annex_distillation_pattern",
            "distillation_patterns",
            "distillation_pattern",
        }
        and band == "flag"
        and not ids
    ):
        payload = build_option_surface(state.REPO_ROOT, artifact_kind, band="cluster_flag", ids=ids)
        payload = _annotate_option_surface_payload(payload, artifact_kind="annex_distillation_patterns")
        payload["requested_band"] = "flag"
        payload["band_redirect"] = {
            "from": "flag",
            "to": "cluster_flag",
            "reason": "annex_distillation_patterns all-row flag is a high-cardinality distillation expansion; row-level flags require explicit --ids.",
            "explicit_row_flag_command": "./repo-python kernel.py --option-surface annex_distillation_patterns --band flag --ids <slug>:<pNNN>",
        }
        warnings = payload.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(
                {
                    "kind": "high_cardinality_flag_redirect",
                    "message": "Rendered cluster_flag instead of all annex distillation pattern row flags.",
                }
            )
        return _emit_option_surface(payload)
    payload = build_option_surface(state.REPO_ROOT, artifact_kind, band=band, ids=ids)
    payload = _annotate_option_surface_payload(payload, artifact_kind=str(payload.get("artifact_kind") or artifact_kind))
    return _emit_option_surface(payload)


def cmd_imagination_list() -> int:
    """Convenience alias for `--option-surface imaginations --band flag`."""
    payload = build_option_surface(state.REPO_ROOT, "imaginations", band="flag", ids=None)
    return emit_json_with_code(payload, 0 if payload.get("profile_status") == "supported" else 2)


def cmd_imagination(request: str) -> int:
    """Open one imagination by id or slug. Convenience alias for
    `--option-surface imaginations --band card --ids <id>` with id-or-slug
    resolution and migration lineage rendered inline.
    """
    if not isinstance(request, str) or not request.strip():
        print("ERROR: --imagination requires an imagination_id or slug.", file=__import__("sys").stderr)
        return 1
    request = request.strip()
    payload = build_option_surface(state.REPO_ROOT, "imaginations", band="card", ids=request)
    selection = payload.get("selection") or {}
    missing = list(selection.get("missing_ids") or [])
    rows = payload.get("rows") or []
    if missing and not rows:
        # Resolution failed; emit a structured not-found payload with hints.
        list_payload = build_option_surface(state.REPO_ROOT, "imaginations", band="flag", ids=None)
        candidates = [
            {
                "imagination_id": r.get("imagination_id"),
                "slug": r.get("slug"),
                "title": r.get("title"),
            }
            for r in (list_payload.get("rows") or [])
        ]
        not_found = {
            "kind": "imagination_not_found",
            "schema_version": "imagination_not_found_v0",
            "request": request,
            "missing_ids": missing,
            "available_imaginations": candidates,
            "hint_command": "./repo-python kernel.py --imagination-list",
            "find_command": f"./repo-python kernel.py --imagination-find \"{request}\" --debug",
        }
        return emit_json_with_code(not_found, 1)
    return emit_json_with_code(payload, 0 if payload.get("profile_status") == "supported" else 2)


def cmd_imagination_find(query: str, *, debug: bool = False) -> int:
    """Search the imagination index for matches across id, slug, title,
    voice_anchor_summary, primary_substrate_seam, migrated_from_axiom_candidate_ids,
    and migrated_from_deliverable_ids. Returns a ranked compact list with
    drilldown commands.
    """
    import sys as _sys
    if not isinstance(query, str) or not query.strip():
        print("ERROR: --imagination-find requires a query.", file=_sys.stderr)
        return 1
    if not debug:
        return emit_json(
            debug_trace_block(
                surface_id="imagination_find",
                command="./repo-python kernel.py --imagination-find",
                query=query.strip(),
            )
        )
    query_norm = query.strip().lower()
    surface = build_option_surface(state.REPO_ROOT, "imaginations", band="flag", ids=None)
    if surface.get("profile_status") != "supported":
        return emit_json_with_code(surface, 2)
    rows = surface.get("rows") or []

    def _row_search_text(row: dict) -> tuple[str, list[tuple[str, int]]]:
        haystacks: list[tuple[str, int]] = []
        # (field_name, weight)
        for field, weight in [
            ("imagination_id", 6),
            ("slug", 6),
            ("title", 5),
            ("voice_anchor_summary", 3),
            ("primary_substrate_seam", 3),
            ("retirement_trigger_summary", 2),
        ]:
            value = row.get(field) or ""
            if isinstance(value, str) and value:
                haystacks.append((value.lower(), weight))
        for field, weight in [
            ("migrated_from_axiom_candidate_ids", 4),
            ("migrated_from_deliverable_ids", 4),
        ]:
            values = row.get(field) or []
            if isinstance(values, list):
                for v in values:
                    if isinstance(v, str) and v:
                        haystacks.append((v.lower(), weight))
        combined = " | ".join(h[0] for h in haystacks)
        return combined, haystacks

    def _score(row: dict) -> int:
        _, haystacks = _row_search_text(row)
        score = 0
        for text, weight in haystacks:
            if query_norm in text:
                # bonus for exact-token match
                score += weight * 10
                if any(query_norm == token for token in text.split()):
                    score += weight * 5
        # also score by query word overlap
        query_words = [w for w in query_norm.split() if w]
        for word in query_words:
            for text, weight in haystacks:
                if word in text:
                    score += weight
        return score

    scored = [(row, _score(row)) for row in rows]
    scored = [(r, s) for r, s in scored if s > 0]
    scored.sort(key=lambda x: (-x[1], str(x[0].get("imagination_id") or "")))
    matches = [
        {
            "imagination_id": row.get("imagination_id"),
            "slug": row.get("slug"),
            "title": row.get("title"),
            "status": row.get("status"),
            "score": score,
            "voice_anchor_summary": row.get("voice_anchor_summary"),
            "primary_substrate_seam": row.get("primary_substrate_seam"),
            "migrated_from_axiom_candidate_ids": row.get("migrated_from_axiom_candidate_ids"),
            "drilldown_command": row.get("drilldown_command"),
            "convenience_command": row.get("convenience_command"),
        }
        for row, score in scored
    ]
    payload = {
        "kind": "imagination_find",
        "schema_version": "imagination_find_v0",
        "surface_role": DEBUG_TRACE,
        "first_contact_allowed": False,
        "debug": True,
        "query": query,
        "match_count": len(matches),
        "total_imaginations": len(rows),
        "matches": matches,
        "surface_contract": debug_trace_contract(
            surface_id="imagination_find",
            command="./repo-python kernel.py --imagination-find",
            query=query.strip(),
        ),
        "next": [
            {
                "command": "./repo-python kernel.py --imagination <id_or_slug>",
                "reason": "Open a matched imagination at card band.",
            },
            {
                "command": "./repo-python kernel.py --option-surface imaginations --band flag",
                "reason": "Browse all imaginations without a query.",
            },
        ],
    }
    return emit_json_with_code(payload, 0 if matches else 0)


def cmd_kind_atlas(*, band: str = "flag", query: str | None = None, ids: str | None = None) -> int:
    """Emit the rung-0 atlas of artifact kinds before keyword routing."""
    payload = build_kind_atlas(state.REPO_ROOT, band=band, query=query, ids=ids)
    payload.setdefault("surface_role", ATLAS_PROJECTION)
    payload.setdefault("first_contact_allowed", False)
    payload.setdefault("control_replacement", ENTRY_REPLACEMENT)
    payload.setdefault(
        "surface_contract",
        atlas_projection_contract(
            surface_id="kind_atlas",
            command="./repo-python kernel.py --kind-atlas",
        ),
    )
    return emit_json(payload)


def cmd_kind_band_contract_audit() -> int:
    """Emit a read-only audit of per-kind native navigation contracts."""
    payload = build_kind_band_contract_audit(state.REPO_ROOT)
    return emit_json(payload)


# =========================================================================
# Command-output projection (std_command_output_projection.json) — opt-in
# Default emission shapes for each command remain unchanged. The build_<cmd>_
# projection_envelope functions below wrap the existing payload computation in
# the canonical Rosetta-Stone envelope; they are invoked only when the caller
# passes --output-band <band> (or via --row KIND:ID --band BAND for kinds).
# =========================================================================

_COMMAND_OUTPUT_PROJECTION_BANDS = {
    "phase": ["card", "full"],
    "paper-module": ["flag", "card"],
    "info": ["flag", "card"],
    "frontier": ["flag", "card"],
    "docs-route": ["card"],
    "pulse": ["flag", "card"],
    "working-set": ["flag", "card"],
    "system-map": ["flag", "card"],
    "session-diagnostics": ["flag", "card"],
}


def _project_unsupported_band(*, command: str, band: str, supported: Sequence[str]) -> dict[str, Any]:
    """Structured refusal when a command does not support the requested output band."""
    return {
        "kind": "command_output_band_unavailable",
        "schema_version": "command_output_band_unavailable_v0",
        "governing_standard": "codex/standards/std_command_output_projection.json",
        "command": command,
        "requested_band": band,
        "supported_bands": list(supported),
        "reason": (
            f"--output-band {band!r} is not declared for {command!r}; supported bands are "
            f"{list(supported)!r}."
        ),
        "next_safe_commands": [
            f"./repo-python kernel.py {command} --output-band {b}" for b in supported
        ],
    }


def build_phase_projection_envelope(
    *,
    band: str = "card",
    phase_token: str | None = None,
) -> dict[str, Any]:
    """Wrap --phase output in the canonical Rosetta-Stone projection envelope.

    Default --phase emission is unchanged; this builder is invoked only when
    --output-band <band> opts in. Promotes the legacy nested ``omitted_sections``
    (inside payload) to the peer-level ``omission_receipt``.
    """
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["phase"]
    if band not in supported:
        return _project_unsupported_band(command="--phase", band=band, supported=supported)

    navigator = KernelNavigation(state.REPO_ROOT)
    result = navigator.build_phase(phase_token)
    output_mode = "summary" if band == "card" else "full"
    if band == "card":
        source_payload = result.payload if isinstance(result.payload, Mapping) else {}
        phase = source_payload.get("phase") if isinstance(source_payload.get("phase"), Mapping) else {}
        phase_card = (
            source_payload.get("phase_card")
            if isinstance(source_payload.get("phase_card"), Mapping)
            else {}
        )
        active_wave = (
            phase_card.get("active_wave")
            if isinstance(phase_card.get("active_wave"), Mapping)
            else {}
        )
        stage_guidance = (
            source_payload.get("stage_guidance")
            if isinstance(source_payload.get("stage_guidance"), Mapping)
            else {}
        )
        canonical_entry = (
            source_payload.get("canonical_entry")
            if isinstance(source_payload.get("canonical_entry"), Mapping)
            else {}
        )
        phase_id = str(phase.get("phase_id") or phase.get("phase_number") or "active") or "active"
        phase_command = "./repo-python kernel.py --phase {phase_id}"
        path_table: dict[str, str] = {}
        phase_dir = str(phase.get("phase_dir") or "").strip()
        if phase_dir:
            path_table["phase_dir"] = phase_dir
        def _phase_path_ref(path_value: object) -> str:
            raw_path = str(path_value or "").strip()
            if phase_dir and raw_path.startswith(f"{phase_dir}/"):
                return f"phase_dir/{raw_path[len(phase_dir) + 1:]}"
            return raw_path

        canonical_path = str(canonical_entry.get("path") or "").strip()
        if canonical_path:
            path_table["canonical_entry"] = _phase_path_ref(canonical_path)
        target_paths = (
            list(active_wave.get("target_paths") or [])
            if isinstance(active_wave.get("target_paths"), list)
            else []
        )
        target_path_limit = 20
        visible_target_paths = target_paths[:target_path_limit]
        omitted_target_paths = target_paths[target_path_limit:]
        full_command = phase_command.format(phase_id=phase_id) + " --full"
        summary_command = phase_command.format(phase_id=phase_id)
        compat_summary_command = f"{summary_command} --summary"
        warnings_command = f"{summary_command} --warnings-only"
        omitted_list = [
            "payload.phase_card",
            "payload.family",
            "payload.recovery_map",
            "payload.active_synth",
            "payload.derived_index.entry",
            "payload.plan_context|observe_authoring|manifest|closeout",
        ]
        compact_payload = {
            "view_profile": "phase_agent_control_packet_v0",
            "safe_decision_supported": (
                "Choose the active phase, current wave, next legal command, and whether to drill into full evidence."
            ),
            "source_payload_owner": {
                "owner_id": "kernel.phase.full_payload",
                "authority_plane": "source_payload",
                "primary_surface_ref": "phase_full",
                "owning_code": [
                    "system/lib/kernel_nav_phase.py::PhasePlanMixin.build_phase",
                    "system/lib/kernel_navigation.py::NavigationResult.to_dict",
                ],
                "facts_owned": [
                    "complete phase card",
                    "family members and archive members",
                    "recovery map",
                    "active synth normalization",
                    "derived index entry",
                    "plan, manifest, observe-authoring, and closeout details",
                ],
                "source_mutation_allowed_by_this_profile": False,
            },
            "view_owner": {
                "owner_id": "phase_agent_control_packet_v0",
                "authority_plane": "view_profile",
                "view_surface_ref": "phase_summary",
                "owning_code": [
                    "system/lib/kernel/commands/navigate.py::build_phase_projection_envelope",
                ],
                "omission_authority": [
                    "Default phase entry may omit evidence/debug sections when full_payload_hint names the drilldown.",
                    "Packet-scoped paths and commands are factored into path_table and command_templates.",
                    "Derived-index and normalized-synth internals remain source-owned by the full payload.",
                ],
                "view_mutation_allowed_by_this_profile": "phase_output_view_only",
            },
            "full_payload_hint": {
                "command_ref": "phase_full",
                "required_when": [
                    "debugging phase selection, recovery, or derived-index state",
                    "authoring an observe plan from detailed synth internals",
                    "auditing family/archive members or closeout records",
                    "checking omitted source authority before a mutation",
                ],
                "drilldown_sufficient_if": [
                    "the full payload resolves the same phase_id",
                    "the omitted sections listed by the omission_receipt are present in the full payload",
                ],
            },
            "phase": {
                "phase_id": phase.get("phase_id"),
                "phase_number": phase.get("phase_number"),
                "phase_title": phase.get("phase_title"),
                "phase_dir_ref": "phase_dir" if "phase_dir" in path_table else None,
                "status": phase.get("status"),
                "execution_mode": phase.get("execution_mode"),
                "current_wave_id": phase.get("current_wave_id"),
            },
            "canonical_entry": {
                **(_phase_output_note_stub(canonical_entry) or {}),
                "path": None,
                "path_ref": "canonical_entry" if "canonical_entry" in path_table else None,
            }
            if canonical_entry
            else None,
            "active_wave": {
                "wave_id": active_wave.get("wave_id"),
                "mode": active_wave.get("mode"),
                "status": active_wave.get("status"),
                "objective": active_wave.get("objective"),
                "bounded_question": active_wave.get("bounded_question"),
                "target_path_count": len(target_paths),
                "target_paths": visible_target_paths,
                "target_paths_limit": target_path_limit,
                "omitted_target_paths": omitted_target_paths,
                "omitted_target_path_count": len(omitted_target_paths),
            },
            "last_outcome": phase_card.get("last_outcome"),
            "next_step_posture": _agent_wake_truncate(phase_card.get("next_step_posture"), 420),
            "stage": {
                "stage": stage_guidance.get("stage"),
                "summary": _agent_wake_truncate(stage_guidance.get("summary"), 280),
            }
            if stage_guidance
            else None,
            "command_budget": {
                "purpose": "Bound phase reentry when the full phase card is unnecessary.",
                "summary_ref": "phase_summary",
                "compat_summary_ref": "phase_summary_compat",
                "full_ref": "phase_full",
                "warnings_ref": "phase_warnings",
            },
        }
        next_steps = [
            {
                "command_ref": "bootstrap_canonical_entry",
                "args": {"path_ref": "canonical_entry"},
                "reason": "Open the bounded task-entry packet for the canonical phase entry note.",
            }
        ]
        for item in list(result.suggested_next or [])[:3]:
            if not isinstance(item, Mapping):
                continue
            command = normalize_repo_kernel_command(str(item.get("command") or ""))
            reason = str(item.get("reason") or "").strip()
            if not command:
                continue
            if (
                ("canonical_entry" in path_table and path_table["canonical_entry"] in command)
                or (canonical_path and canonical_path in command)
            ):
                continue
            next_steps.append({"command": command, "reason": reason})
            if len(next_steps) >= 3:
                break
        omission = make_omission_receipt(
            omitted=omitted_list,
            reason=(
                "Card band is the agent control view: choose phase, wave, and next legal command. "
                "Full evidence/debug sections live behind --full."
            ),
            drilldown=full_command,
        )
        currentness = make_currentness(
            status="live_computed",
            recommended_action="trust",
        )
        validation = make_validation_contract(
            freshness_probe=f"./repo-python kernel.py --phase {phase_id}",
            failure_modes=[
                "phase token cannot be resolved",
                "active phase scaffold missing",
                "synth_seed.json normalization fails",
            ],
        )
        return command_projection(
            command="--phase",
            band="card",
            selector=phase_id,
            summary={
                "phase_id": phase.get("phase_id"),
                "status": phase.get("status"),
                "execution_mode": phase.get("execution_mode"),
                "current_wave_id": phase.get("current_wave_id"),
                "canonical_entry_ref": "canonical_entry" if "canonical_entry" in path_table else None,
                "warning_count": len(result.warnings or []),
            },
            payload=compact_payload,
            currentness=currentness,
            drilldown_command=full_command,
            evidence_command=full_command,
            omission_receipt=omission,
            validation_contract=validation,
            sources={
                "live_refs": [_phase_path_ref(path) for path in list(result.live_sources or [])[:6]],
                "derived_refs": [str(path) for path in list(result.derived_sources or [])[:4]],
                "derived_required": result.derived_required,
            },
            next_steps=next_steps,
            warnings=[{"message": str(w)} for w in result.warnings or []],
            extra_fields={
                "mode": output_mode,
                "packet_factoring_contract": {
                    "name": "payload_economy_via_packet_level_semantic_factoring",
                    "rule": (
                        "Packet-scoped facts are stated once and referenced by compact handles; "
                        "rows repeat only row-local discriminators, safety-critical identity, or copy-out affordances."
                    ),
                    "factored_fields": [
                        "phase.phase_dir",
                        "canonical_entry.path",
                        "phase command variants",
                    ],
                },
                "path_table": path_table,
                "command_templates": {
                    "phase_summary": phase_command,
                    "phase_summary_compat": phase_command + " --summary",
                    "phase_full": phase_command + " --full",
                    "phase_warnings": phase_command + " --warnings-only",
                    "bootstrap_canonical_entry": "./repo-python kernel.py --bootstrap-task {path}",
                },
                "command_args": {"phase_id": phase_id},
                "resolved_copy_out": {
                    "phase_summary": summary_command,
                    "phase_summary_compat": compat_summary_command,
                    "phase_full": full_command,
                    "phase_warnings": warnings_command,
                },
            },
        )

    # band == "full": project the navigation full payload with an empty omission receipt
    full_payload = result.payload
    phase_block = full_payload.get("phase") if isinstance(full_payload.get("phase"), Mapping) else {}
    phase_id = str(phase_block.get("phase_id") or phase_block.get("phase_number") or "active")
    drilldown = f"./repo-python kernel.py --phase {phase_id} --full"
    return command_projection(
        command="--phase",
        band="full",
        selector=phase_id,
        summary={
            "phase_id": phase_block.get("phase_id"),
            "phase_number": phase_block.get("phase_number"),
            "status": phase_block.get("status"),
            "current_wave_id": phase_block.get("current_wave_id"),
            "warning_count": len(result.warnings or []),
        },
        payload=dict(full_payload) if isinstance(full_payload, Mapping) else None,
        currentness=make_currentness(status="live_computed"),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=make_omission_receipt(
            omitted=[],
            reason="Full band emits the complete phase navigation payload; nothing is omitted.",
            drilldown=drilldown,
        ),
        validation_contract=make_validation_contract(
            freshness_probe=f"./repo-python kernel.py --phase {phase_id}",
            failure_modes=["phase token cannot be resolved"],
        ),
    )


def build_paper_module_projection_envelope(
    *,
    band: str = "card",
    slug: str | None = None,
) -> dict[str, Any]:
    """Wrap paper-module output in the canonical projection envelope (opt-in).

    Default --paper-module emission (full evidence markdown via
    ``KernelNavigation.build_paper_module_lookup``) remains unchanged. This
    builder delegates to the existing option-surface adapter so kind-native band
    semantics (declared in std_paper_module.json) are preserved.
    """
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["paper-module"]
    if band not in supported:
        return _project_unsupported_band(command="--paper-module", band=band, supported=supported)

    selector = slug or "_browse_"
    if band == "flag":
        selected_ids = [slug] if slug else None
        rendered_band = "flag" if slug else "cluster_flag"
        os_payload = build_option_surface(
            state.REPO_ROOT, "paper_modules", band=rendered_band, ids=selected_ids
        )
        drilldown = (
            f"./repo-python kernel.py --option-surface paper_modules --band card --ids {slug}"
            if slug
            else "./repo-python kernel.py --option-surface paper_modules --band cluster_flag"
        )
        evidence = (
            f"./repo-python kernel.py --paper-module {slug}"
            if slug
            else "./repo-python kernel.py --paper-module <slug>"
        )
        return command_projection(
            command="--paper-module",
            band="flag",
            selector=selector,
            summary={
                "requested_band": "flag",
                "rendered_band": rendered_band,
                "row_count": (os_payload.get("summary") or {}).get("row_count"),
                "total_available": (os_payload.get("summary") or {}).get("total_available"),
                "selection_method": (os_payload.get("summary") or {}).get("selection_method"),
            },
            payload={
                "rows": os_payload.get("rows", []),
                "band_redirect": None
                if slug
                else {
                    "from": "paper_modules.row_flag_all",
                    "to": "paper_modules.cluster_flag",
                    "reason": "all-row paper-module flag is a known high-cardinality overflow surface",
                },
            },
            currentness=make_currentness(
                status=(os_payload.get("currentness") or {}).get("status", "live_computed"),
            ),
            drilldown_command=drilldown,
            evidence_command=evidence,
            omission_receipt=make_omission_receipt(
                omitted=[
                    "all row-level flag rows" if not slug else "other paper-module flag rows",
                    "full markdown body",
                    "card band fields",
                    "evidence markdown",
                ],
                reason=(
                    "Flag projection must stay globally bounded; browse clusters first, then "
                    "request explicit row ids for row-level flags."
                    if not slug
                    else "Flag band carries one selected paper-module row so a reader can decide whether to open the card or evidence body."
                ),
                drilldown=drilldown,
            ),
            validation_contract=make_validation_contract(
                freshness_probe="./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
                failure_modes=[
                    "paper-module index stale vs authored markdown",
                    "missing required frontmatter / required sections",
                ],
            ),
            sources={"derived": ["codex/doctrine/paper_modules/_index.json"]},
        )

    # band == "card": delegate to option-surface card row for the selected slug
    if not slug:
        return row_band_unavailable(
            kind_id="paper_modules",
            row_id_value="<unspecified>",
            requested_band="card",
            reason=(
                "--paper-module --output-band card requires a slug; pass a paper-module slug "
                "as the positional argument."
            ),
            legal_bands=["flag", "card", "context", "evidence"],
            populated_bands=["flag", "card", "evidence"],
            next_safe_commands=[
                "./repo-python kernel.py --paper-module raw_seed_substrate --output-band card",
                "./repo-python kernel.py --paper-module --output-band flag",
                "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            ],
        )
    os_payload = build_option_surface(
        state.REPO_ROOT, "paper_modules", band="card", ids=[slug]
    )
    rows = os_payload.get("rows") or []
    if not rows:
        return row_band_unavailable(
            kind_id="paper_modules",
            row_id_value=str(slug),
            requested_band="card",
            reason=f"No paper-module row found for slug {slug!r}",
            legal_bands=["flag", "card", "context", "evidence"],
            populated_bands=["flag", "card", "evidence"],
            next_safe_commands=[
                "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            ],
        )
    row = rows[0] if isinstance(rows[0], dict) else {}
    drilldown = f"./repo-python kernel.py --paper-module {slug}"
    return command_projection(
        command="--paper-module",
        band="card",
        selector=str(slug),
        summary={
            "slug": row.get("slug"),
            "title": row.get("title"),
            "status": row.get("status"),
            "currentness_action": (row.get("currentness") or {}).get("recommended_action"),
        },
        payload={"row": row},
        currentness=row.get("currentness") if isinstance(row.get("currentness"), Mapping) else make_currentness(),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=make_omission_receipt(
            omitted=[
                "full markdown body",
                "full dependency transitive closure",
                "code loci body",
            ],
            reason=(
                "Card band supports selecting the next read; the full paper-module markdown "
                "is the evidence body."
            ),
            drilldown=drilldown,
        ),
        validation_contract=make_validation_contract(
            freshness_probe="./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
            failure_modes=[
                "paper-module index stale vs authored markdown",
                "slug renamed; row drops out of card band",
            ],
        ),
        sources={"derived": ["codex/doctrine/paper_modules/_index.json"]},
    )


def build_info_projection_envelope(*, band: str = "flag") -> dict[str, Any]:
    """Wrap --info output in the canonical projection envelope (opt-in)."""
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["info"]
    if band not in supported:
        return _project_unsupported_band(command="--info", band=band, supported=supported)

    drilldown = "./repo-python kernel.py --info --full"
    summary_block = {
        "kernel_version": state.KERNEL_VERSION,
        "repo_root": str(state.REPO_ROOT),
    }
    if band == "flag":
        omitted = [
            "command_groups.sample_flags",
            "essential_docs",
            "bootstrap_rules",
            "planning_loop",
            "observe_loop",
            "minimum_read_sets",
            "situation_routes",
        ]
        return command_projection(
            command="--info",
            band="flag",
            selector="bootstrap",
            summary=summary_block,
            payload={
                "next_command": "./repo-python kernel.py --info --output-band card",
            },
            currentness=make_currentness(status="live_computed"),
            drilldown_command=drilldown,
            evidence_command=drilldown,
            omission_receipt=make_omission_receipt(
                omitted=omitted,
                reason=(
                    "Flag band carries kernel identity only; the card band adds essential docs, "
                    "bootstrap sequence, and command-group counts."
                ),
                drilldown="./repo-python kernel.py --info --output-band card",
            ),
            validation_contract=make_validation_contract(
                freshness_probe="./repo-python kernel.py --info",
                failure_modes=["bootstrap config not loadable", "stale agent_bootstrap.json"],
            ),
        )

    # band == "card": include essentials but still shorter than --info --full
    return command_projection(
        command="--info",
        band="card",
        selector="bootstrap",
        summary=summary_block,
        payload={
            "essential_docs": {
                "codex": "codex/CODEX.md",
                "agents": "AGENTS.md",
                "claude": "CLAUDE.md",
                "agent_bootstrap": "codex/doctrine/agent_bootstrap.json",
                "kernel_quickstart": "codex/doctrine/operations/agent_quickstart.md",
            },
            "bootstrap_sequence_compact": [
                "./repo-python kernel.py --info",
                "./repo-python kernel.py --preflight",
                "./repo-python kernel.py --pulse",
                "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                WORK_LEDGER_SEED_SPEED_COMMAND,
                "./repo-python kernel.py --docs-route documentation",
            ],
            "live_work_first": {
                "rule": "Use WorkItems and Work Ledger claims before phase or markdown recency when choosing current work.",
                "phase_context_after": "./repo-python kernel.py --phase",
            },
        },
        currentness=make_currentness(status="live_computed"),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=make_omission_receipt(
            omitted=[
                "command_groups.sample_flags (per-group flag list)",
                "minimum_read_sets bodies",
                "situation_routes table",
                "runtime_control_plane",
            ],
            reason=(
                "Card band lists essential docs and the compact bootstrap sequence; the full "
                "manifest with per-group sample flags lives behind --info --full."
            ),
            drilldown=drilldown,
        ),
        validation_contract=make_validation_contract(
            freshness_probe="./repo-python kernel.py --info",
            failure_modes=["bootstrap config not loadable"],
        ),
    )


def build_frontier_projection_envelope(
    *,
    band: str = "flag",
    limit: int | None = None,
) -> dict[str, Any]:
    """Wrap --frontier output in the canonical projection envelope (opt-in)."""
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["frontier"]
    if band not in supported:
        return _project_unsupported_band(command="--frontier", band=band, supported=supported)

    requested_limit = int(limit) if limit is not None else state.MARKDOWN_FRONTIER_DEFAULT_LIMIT
    navigator = KernelNavigation(state.REPO_ROOT)
    result = navigator.build_frontier(requested_limit)
    payload = result.payload if isinstance(result.payload, Mapping) else {}
    rows = payload.get("recent_markdown") if isinstance(payload.get("recent_markdown"), list) else []
    drilldown = f"./repo-python kernel.py --frontier {requested_limit} --output-band card"

    if band == "flag":
        flag_rows = [
            {
                "path": str(row.get("path") or ""),
                "title": str(row.get("title") or ""),
                "mtime_epoch": row.get("mtime_epoch"),
            }
            for row in rows
            if isinstance(row, Mapping)
        ]
        return command_projection(
            command="--frontier",
            band="flag",
            selector=str(requested_limit),
            summary={"row_count": len(flag_rows), "limit": requested_limit},
            payload={"recent_markdown": flag_rows},
            currentness=make_currentness(status="live_computed"),
            drilldown_command=drilldown,
            evidence_command=f"./repo-python kernel.py --frontier {requested_limit}",
            omission_receipt=make_omission_receipt(
                omitted=["keywords", "signals", "size_bytes", "line_count"],
                reason="Flag band carries path/title/mtime only; deeper metadata lives at card band.",
                drilldown=drilldown,
            ),
            validation_contract=make_validation_contract(
                freshness_probe=f"./repo-python kernel.py --frontier {requested_limit}",
                failure_modes=["frontier scan path missing", "git mtime unreadable"],
            ),
        )

    # band == "card": include keywords / signals / size / line count
    card_rows = [
        {
            "path": str(row.get("path") or ""),
            "title": str(row.get("title") or ""),
            "mtime_epoch": row.get("mtime_epoch"),
            "size_bytes": row.get("size_bytes"),
            "line_count": row.get("line_count"),
            "keywords": row.get("keywords") or [],
            "signals": row.get("signals") or [],
        }
        for row in rows
        if isinstance(row, Mapping)
    ]
    full_command = f"./repo-python kernel.py --frontier {requested_limit}"
    return command_projection(
        command="--frontier",
        band="card",
        selector=str(requested_limit),
        summary={"row_count": len(card_rows), "limit": requested_limit},
        payload={"recent_markdown": card_rows},
        currentness=make_currentness(status="live_computed"),
        drilldown_command=full_command,
        evidence_command=full_command,
        omission_receipt=make_omission_receipt(
            omitted=["full payload-only fields beyond path/title/mtime/size/lines/keywords/signals"],
            reason=(
                "Card band carries selection-quality fields. Full frontier output adds nothing "
                "structural; the drilldown returns the same row schema."
            ),
            drilldown=full_command,
        ),
        validation_contract=make_validation_contract(
            freshness_probe=full_command,
            failure_modes=["frontier scan path missing", "git mtime unreadable"],
        ),
    )


def build_docs_route_projection_envelope(
    *,
    band: str = "card",
    request: str = "documentation",
) -> dict[str, Any]:
    """Wrap --docs-route output in the canonical projection envelope (opt-in)."""
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["docs-route"]
    if band not in supported:
        return _project_unsupported_band(command="--docs-route", band=band, supported=supported)

    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_docs_route(request)
    except ValueError as exc:
        return {
            "kind": "command_output_projection_error",
            "command": "--docs-route",
            "band": band,
            "request": str(request),
            "error": f"{type(exc).__name__}: {exc}",
        }
    payload = result.payload if isinstance(result.payload, Mapping) else {}
    compact_result = result.to_dict(state.KERNEL_VERSION, full=False)
    compact_payload = (
        compact_result.get("payload")
        if isinstance(compact_result, Mapping) and isinstance(compact_result.get("payload"), Mapping)
        else {}
    )
    route_card = (
        compact_payload.get("route_card")
        if isinstance(compact_payload.get("route_card"), Mapping)
        else {}
    )
    omitted_dup = []
    if isinstance(route_card.get("omitted_duplicate_fields"), list):
        omitted_dup = [str(item) for item in route_card.get("omitted_duplicate_fields") or []]
    drilldown = f"./repo-python kernel.py --docs-route {request!r}"

    path_table: dict[str, str] = {}
    message_table: dict[str, str] = {}

    def _path_ref(value: object) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        for ref, existing in path_table.items():
            if existing == text:
                return ref
        ref = f"p{len(path_table) + 1}"
        path_table[ref] = text
        return ref

    def _path_refs(values: object) -> list[str]:
        if not isinstance(values, list):
            return []
        refs: list[str] = []
        for value in values:
            ref = _path_ref(value)
            if ref and ref not in refs:
                refs.append(ref)
        return refs

    def _message_ref(value: object) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        for ref, existing in message_table.items():
            if existing == text:
                return ref
        ref = f"m{len(message_table) + 1}"
        message_table[ref] = text
        return ref

    focus = (
        payload.get("documentation_route_focus")
        if isinstance(payload.get("documentation_route_focus"), Mapping)
        else {}
    )
    resolution = (
        payload.get("resolution")
        if isinstance(payload.get("resolution"), Mapping)
        else {}
    )
    authority = (
        payload.get("authority")
        if isinstance(payload.get("authority"), Mapping)
        else {}
    )
    minimum_read_set = (
        payload.get("minimum_read_set")
        if isinstance(payload.get("minimum_read_set"), Mapping)
        else {}
    )
    runtime_surface = (
        payload.get("runtime_surface")
        if isinstance(payload.get("runtime_surface"), Mapping)
        else {}
    )
    entry_packet = (
        payload.get("entry_packet")
        if isinstance(payload.get("entry_packet"), Mapping)
        else {}
    )
    compact_entry_packet = (
        compact_payload.get("entry_packet")
        if isinstance(compact_payload.get("entry_packet"), Mapping)
        else {}
    )
    compact_resolution = (
        compact_payload.get("resolution")
        if isinstance(compact_payload.get("resolution"), Mapping)
        else {}
    )

    authority_surface_refs = _path_refs(authority.get("surfaces"))
    minimum_read_refs = _path_refs(minimum_read_set.get("paths"))
    local_artifacts = payload.get("local_artifacts") if isinstance(payload.get("local_artifacts"), list) else []
    local_artifact_refs = _path_refs(local_artifacts)
    runtime_authority_refs = _path_refs(runtime_surface.get("authority_paths"))
    entry_read_refs = _path_refs(entry_packet.get("read_this_first"))
    entry_runtime_refs = _path_refs(entry_packet.get("runtime_seam"))
    focus_path_ref = _path_ref(focus.get("path"))

    priority_why_ref = _message_ref(resolution.get("priority_why"))
    route_rationale_ref = _message_ref(payload.get("route_rationale"))
    focus_overlay_ref = _message_ref(focus.get("overlay_priority_why"))
    entry_summary_ref = _message_ref(entry_packet.get("summary"))
    route_card_why_ref = _message_ref(route_card.get("why"))

    factored_entry_packet: dict[str, Any] = {
        "title": entry_packet.get("title"),
        "summary_ref": entry_summary_ref,
        "read_this_first_refs": entry_read_refs,
        "first_moves": [
            {
                "command": str(item.get("command") or "").strip(),
                "reason": str(item.get("reason") or "").strip(),
            }
            for item in list(compact_entry_packet.get("first_moves") or [])[:5]
            if isinstance(item, Mapping) and str(item.get("command") or "").strip()
        ],
        "runtime_seam_refs": entry_runtime_refs,
        "why_layer_evidence": [
            {
                "ref": str(item.get("ref") or "").strip(),
                "gloss": str(item.get("gloss") or "").strip(),
                "command_template_ref": "raw_seed_paragraph",
            }
            for item in list(compact_entry_packet.get("why_layer_evidence") or [])[:3]
            if isinstance(item, Mapping) and str(item.get("ref") or "").strip()
        ],
    }
    resolution_factored = {
        key: value
        for key, value in dict(compact_resolution or resolution).items()
        if key != "priority_why" and value not in (None, [], {})
    }
    if priority_why_ref:
        resolution_factored["priority_why_ref"] = priority_why_ref
    if route_rationale_ref and route_rationale_ref != priority_why_ref:
        resolution_factored["route_rationale_ref"] = route_rationale_ref

    factored_payload: dict[str, Any] = {
        "view_profile": "docs_route_factored_card_v1",
        "route_card": {
            "route_id": route_card.get("route_id") or resolution.get("route_id"),
            "authority_layer": route_card.get("authority_layer") or authority.get("layer"),
            "why_ref": route_card_why_ref or priority_why_ref or route_rationale_ref or entry_summary_ref,
            "omitted_duplicate_fields": omitted_dup,
            "full_payload_ref": "docs_route_full",
        },
        "documentation_route_focus": {
            "path_ref": focus_path_ref,
            "active_preset_id": focus.get("active_preset_id"),
            "label": focus.get("label"),
            "overlay_priority_why_ref": focus_overlay_ref,
            "invalid_active_preset": focus.get("invalid_active_preset"),
        },
        "resolution": resolution_factored,
        "authority": {
            "layer": authority.get("layer"),
            "surface_refs": authority_surface_refs,
            "documentation_entries": [
                str(item).strip()
                for item in list(authority.get("documentation_entries") or [])
                if str(item).strip()
            ],
        },
        "minimum_read_set": {
            "id": minimum_read_set.get("id"),
            "path_refs": minimum_read_refs,
        },
        "local_artifact_refs": local_artifact_refs[:10],
        "runtime_surface": {
            "surface_id": runtime_surface.get("surface_id"),
            "primary_commands": [
                str(item).strip()
                for item in list(runtime_surface.get("primary_commands") or [])[:4]
                if str(item).strip()
            ],
            "authority_path_refs": runtime_authority_refs,
        }
        if runtime_surface
        else None,
        "entry_packet": factored_entry_packet,
        "paper_module_route_coverage": compact_payload.get("paper_module_route_coverage"),
        "matched_on": list(compact_payload.get("matched_on") or [])[:8],
    }
    if not factored_payload.get("paper_module_route_coverage"):
        factored_payload.pop("paper_module_route_coverage", None)

    return command_projection(
        command="--docs-route",
        band="card",
        selector=str(request),
        summary={
            "request": str(request),
            "matched_route": route_card.get("route_id") or resolution.get("route_id"),
            "minimum_read_set_count": len(minimum_read_refs),
        },
        payload=factored_payload,
        currentness=make_currentness(status="live_computed"),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=make_omission_receipt(
            omitted=omitted_dup
            + [
                "expanded paths (see path_table refs)",
                "raw-seed evidence commands (see command_templates.raw_seed_paragraph)",
                "duplicate route prose (see message_table refs)",
            ],
            reason=(
                "Card band factors packet-scoped paths, prose, and command forms into handle tables."
            ),
            drilldown=drilldown,
        ),
        validation_contract=make_validation_contract(
            freshness_probe=drilldown,
            failure_modes=[
                "no route matches the request token",
                "documentation_route_focus preset stale",
            ],
        ),
        sources={
            "live_refs": _path_refs(list(result.live_sources or [])[:8]),
            "derived_refs": _path_refs(list(result.derived_sources or [])[:4]),
            "derived_required": result.derived_required,
        },
        warnings=[{"message": str(w)} for w in result.warnings or []],
        extra_fields={
            "packet_factoring_contract": {
                "name": "payload_economy_via_packet_level_semantic_factoring",
                "factored_fields": [
                    "paths",
                    "route_prose",
                    "raw_seed_evidence_command",
                ],
            },
            "path_table": path_table,
            "message_table": message_table,
            "command_templates": {
                "docs_route": "./repo-python kernel.py --docs-route {request}",
                "docs_route_full": "./repo-python kernel.py --docs-route {request} --full",
                "raw_seed_paragraph": (
                    'python3 kernel.py --resolve-raw-seed-ref __active__ "paragraph:{ref}"'
                ),
            },
            "command_args": {"request": str(request)},
        },
    )


# ---------------------------------------------------------------------------
# Tranche 2 envelope builders: --pulse / --working-set / --system-map /
# --session-diagnostics. Default emission shape for each remains unchanged;
# these builders are only invoked when --output-band <band> opts in.
# ---------------------------------------------------------------------------

def build_pulse_projection_envelope(*, band: str = "flag") -> dict[str, Any]:
    """Wrap --pulse output in the canonical projection envelope (opt-in)."""
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["pulse"]
    if band not in supported:
        return _project_unsupported_band(command="--pulse", band=band, supported=supported)

    snapshot = _pulse_snapshot()
    frontier = snapshot.get("frontier_anchor") if isinstance(snapshot.get("frontier_anchor"), Mapping) else {}
    active_plan = snapshot.get("active_plan") if isinstance(snapshot.get("active_plan"), Mapping) else {}
    builder = snapshot.get("builder") if isinstance(snapshot.get("builder"), Mapping) else {}
    doctrine = snapshot.get("doctrine") if isinstance(snapshot.get("doctrine"), Mapping) else {}
    routing = snapshot.get("routing_projection") if isinstance(snapshot.get("routing_projection"), Mapping) else {}
    workspace = snapshot.get("workspace") if isinstance(snapshot.get("workspace"), Mapping) else {}
    closeout_git_state = snapshot.get("closeout_git_state") if isinstance(snapshot.get("closeout_git_state"), Mapping) else {}
    active_execution = (
        snapshot.get("active_execution_constellation")
        if isinstance(snapshot.get("active_execution_constellation"), Mapping)
        else {}
    )
    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    active_session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    live_campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    organisation_plane = (
        snapshot.get("organisation_control_plane")
        if isinstance(snapshot.get("organisation_control_plane"), Mapping)
        else {}
    )
    docfix = snapshot.get("latest_docfix_plan") if isinstance(snapshot.get("latest_docfix_plan"), Mapping) else {}
    recommended = snapshot.get("recommended_actions")
    recommended_count = len(recommended) if isinstance(recommended, list) else 0

    drilldown = "./repo-python kernel.py --pulse --full"

    if band == "flag":
        summary = {
            "frontier_path": frontier.get("path"),
            "active_plan_path": active_plan.get("path") if not active_plan.get("error") else None,
            "builder_stale": bool(builder.get("stale")) if builder else None,
            "routing_stale": bool(routing.get("stale")) if routing else None,
            "doctrine_drift_targets": len(doctrine.get("drift_targets") or []) if isinstance(doctrine.get("drift_targets"), list) else 0,
            "doctrine_hotspots_deferred": bool(doctrine.get("hotspots_deferred")) if doctrine else None,
            "git_dirty_total": closeout_git_state.get("dirty_total"),
            "git_ahead": closeout_git_state.get("ahead"),
            "git_closeout_ready": closeout_git_state.get("closeout_ready"),
            "hot_campaign_count": len(live_campaigns),
            "hot_active_claims": active_session_counts.get("active_claims"),
            "hot_effective_sessions": active_session_counts.get("effective_active_sessions"),
            "organisation_control_plane_command": organisation_plane.get("command"),
            "recommended_action_count": recommended_count,
        }
        omission = make_omission_receipt(
            omitted=[
                "frontier_anchor.full_metadata",
                "active_plan.runtime_details",
                "builder.per_phase_status",
                "doctrine.drift_targets_full_list",
                "workspace.full_counts",
                "latest_runtime",
                "latest_docfix_plan",
                "routing_projection.full_diagnostics",
                "closeout_git_state.conditions",
                "active_execution_constellation.live_campaigns_and_sessions",
                "recommended_actions.full_list",
            ],
            reason=(
                "Flag band carries one boolean/count per loop so the agent can decide "
                "which subsystem to open at card or full band."
            ),
            drilldown="./repo-python kernel.py --pulse --output-band card",
        )
    else:  # card
        summary = {
            "frontier_path": frontier.get("path"),
            "active_plan_path": active_plan.get("path") if not active_plan.get("error") else None,
            "builder_stale": bool(builder.get("stale")) if builder else None,
            "routing_stale": bool(routing.get("stale")) if routing else None,
            "doctrine_hotspots_deferred": bool(doctrine.get("hotspots_deferred")) if doctrine else None,
            "git_dirty_total": closeout_git_state.get("dirty_total"),
            "git_ahead": closeout_git_state.get("ahead"),
            "git_closeout_ready": closeout_git_state.get("closeout_ready"),
            "organisation_control_plane_command": organisation_plane.get("command"),
            "recommended_action_count": recommended_count,
        }
        omission = make_omission_receipt(
            omitted=[
                "frontier_anchor (full path metadata, mtime, signals)",
                "active_plan (runtime, group/file counts)",
                "builder (per-phase status)",
                "latest_runtime",
                "latest_docfix_plan (full prose)",
                "workspace (full counts)",
                "closeout_git_state (full condition rows)",
            ],
            reason=(
                "Card band exposes the active loops and recommended actions; the full "
                "pulse snapshot lives behind --pulse --full."
            ),
            drilldown=drilldown,
        )

    payload = {
        "frontier_anchor": dict(frontier) if frontier else None,
        "active_plan_summary": {
            "path": active_plan.get("path"),
            "runtime": active_plan.get("runtime"),
            "group_count": active_plan.get("group_count"),
            "total_files": active_plan.get("total_files"),
            "error": active_plan.get("error"),
        } if active_plan else None,
        "builder_summary": {
            "stale": builder.get("stale"),
            "stale_phases_count": len(builder.get("stale_phases") or []) if isinstance(builder.get("stale_phases"), list) else None,
        } if builder else None,
        "routing_summary": {
            "stale": routing.get("stale"),
            "drift_targets": routing.get("drift_targets"),
        } if routing else None,
        "doctrine_summary": {
            "drift_targets_count": len(doctrine.get("drift_targets") or []) if isinstance(doctrine.get("drift_targets"), list) else 0,
            "hotspots_deferred": bool(doctrine.get("hotspots_deferred")),
            "hotspot_command": doctrine.get("hotspot_command"),
        } if doctrine else None,
        "workspace_summary": dict(workspace) if isinstance(workspace, Mapping) else None,
        "closeout_git_state": dict(closeout_git_state) if isinstance(closeout_git_state, Mapping) else None,
        "organisation_control_plane": dict(organisation_plane) if isinstance(organisation_plane, Mapping) else None,
        "recommended_actions": recommended if isinstance(recommended, list) else None,
    }
    return command_projection(
        command="--pulse",
        band=band,
        selector="snapshot",
        summary=summary,
        payload=payload,
        currentness=make_currentness(
            generated_at=str(snapshot.get("generated_at") or "") or None,
        ),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=omission,
        validation_contract=make_validation_contract(
            freshness_probe="./repo-python kernel.py --pulse",
            failure_modes=[
                "frontier path missing",
                "active plan path missing",
                "builder/routing snapshot unavailable",
            ],
        ),
    )


def build_working_set_projection_envelope(
    *,
    band: str = "flag",
    limit: int | None = None,
    anchor: str | None = None,
) -> dict[str, Any]:
    """Wrap --working-set output in the canonical projection envelope (opt-in)."""
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["working-set"]
    if band not in supported:
        return _project_unsupported_band(command="--working-set", band=band, supported=supported)

    requested_limit = int(limit) if limit is not None else state.MARKDOWN_FRONTIER_DEFAULT_LIMIT
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_working_set(requested_limit, anchor=anchor)
    except ValueError as exc:
        return {
            "kind": "command_output_projection_error",
            "command": "--working-set",
            "band": band,
            "error": f"{type(exc).__name__}: {exc}",
        }
    payload_in = result.payload if isinstance(result.payload, Mapping) else {}
    anchor_block = payload_in.get("anchor") if isinstance(payload_in.get("anchor"), Mapping) else {}
    family = payload_in.get("family") if isinstance(payload_in.get("family"), Mapping) else {}
    phase_context = payload_in.get("phase_context") if isinstance(payload_in.get("phase_context"), Mapping) else {}
    stage_guidance = payload_in.get("stage_guidance") if isinstance(payload_in.get("stage_guidance"), Mapping) else {}
    plan_context = payload_in.get("plan_context") if isinstance(payload_in.get("plan_context"), Mapping) else {}
    observe_context = payload_in.get("observe_context") if isinstance(payload_in.get("observe_context"), Mapping) else {}

    members = family.get("member_paths") if isinstance(family.get("member_paths"), list) else []
    member_count = family.get("member_count") if family.get("member_count") is not None else len(members)

    selector = anchor or "auto"
    drilldown = f"./repo-python kernel.py --working-set {requested_limit}"
    if anchor:
        drilldown += f" --anchor {anchor!r}"

    if band == "flag":
        summary = {
            "anchor_path": anchor_block.get("path"),
            "family_member_count": member_count,
            "active_phase_id": phase_context.get("phase_id") if isinstance(phase_context, Mapping) else None,
            "limit": requested_limit,
        }
        omission = make_omission_receipt(
            omitted=[
                "family.member_paths",
                "plan_context",
                "observe_context",
                "stage_guidance",
                "active_phase_working_set",
                "anchor.full_metadata",
            ],
            reason=(
                "Flag band carries the anchor + family count + active phase id so the "
                "agent can decide whether to drill the working set."
            ),
            drilldown=f"{drilldown} --output-band card",
        )
        payload_out = {
            "anchor": {"path": anchor_block.get("path"), "title": anchor_block.get("title")} if anchor_block else None,
            "family_member_count": member_count,
            "phase_context": {"phase_id": phase_context.get("phase_id")} if phase_context else None,
        }
    else:  # card
        bounded_members = members[:10]
        summary = {
            "anchor_path": anchor_block.get("path"),
            "family_member_count": member_count,
            "active_phase_id": phase_context.get("phase_id") if isinstance(phase_context, Mapping) else None,
            "members_in_card": len(bounded_members),
            "limit": requested_limit,
        }
        omission = make_omission_receipt(
            omitted=[
                f"family.member_paths beyond first {len(bounded_members)}" if len(members) > len(bounded_members) else "(none beyond card)",
                "plan_context.full_payload",
                "observe_context.full_payload",
                "stage_guidance.full_prose",
            ],
            reason=(
                "Card band shows the anchor, top family rows, and active phase posture. "
                "Full continuity packet lives at default --working-set."
            ),
            drilldown=drilldown,
        )
        payload_out = {
            "anchor": dict(anchor_block) if anchor_block else None,
            "family": {
                "member_count": member_count,
                "member_paths_top": bounded_members,
            },
            "phase_context": dict(phase_context) if phase_context else None,
            "stage_guidance": dict(stage_guidance) if stage_guidance else None,
            "plan_context_summary": {
                "present": bool(plan_context),
                "key_count": len(plan_context) if isinstance(plan_context, Mapping) else 0,
            },
            "observe_context_summary": {
                "present": bool(observe_context),
                "key_count": len(observe_context) if isinstance(observe_context, Mapping) else 0,
            },
        }

    return command_projection(
        command="--working-set",
        band=band,
        selector=selector,
        summary=summary,
        payload=payload_out,
        currentness=make_currentness(),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=omission,
        validation_contract=make_validation_contract(
            freshness_probe=drilldown,
            failure_modes=[
                "no anchor resolved from recent markdown",
                "phase_family.json missing",
                "limit invalid",
            ],
        ),
    )


def build_system_map_projection_envelope(*, band: str = "flag") -> dict[str, Any]:
    """Wrap --system-map output in the canonical projection envelope (opt-in).

    Reads codex/doctrine/system_map.json directly (the same source cmd_system_map
    inspects when not delegating to the generator). Does not call the generator.
    """
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["system-map"]
    if band not in supported:
        return _project_unsupported_band(command="--system-map", band=band, supported=supported)

    map_path = state.REPO_ROOT / "codex" / "doctrine" / "system_map.json"
    exists = map_path.is_file()
    payload_in: dict[str, Any] = {}
    if exists:
        try:
            payload_in = json.loads(map_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload_in = {}
    identity = payload_in.get("identity") if isinstance(payload_in.get("identity"), Mapping) else {}
    active_context = payload_in.get("active_context") if isinstance(payload_in.get("active_context"), Mapping) else {}
    counts = payload_in.get("counts") if isinstance(payload_in.get("counts"), Mapping) else {}
    navigation = payload_in.get("navigation") if isinstance(payload_in.get("navigation"), Mapping) else {}
    documentation_routes = payload_in.get("documentation_routes") if isinstance(payload_in.get("documentation_routes"), Mapping) else {}
    standard_block = payload_in.get("standard") if isinstance(payload_in.get("standard"), Mapping) else {}
    drilldown = "./repo-python kernel.py --system-map --system-map-print"
    rel_path = "codex/doctrine/system_map.json"

    if band == "flag":
        summary = {
            "system_map_present": exists,
            "system_map_size_bytes": map_path.stat().st_size if exists else 0,
            "identity_repo": identity.get("repo") if isinstance(identity, Mapping) else None,
            "active_phase_id": active_context.get("phase_id") if isinstance(active_context, Mapping) else None,
            "doctrine_node_count": counts.get("doctrine_nodes") if isinstance(counts, Mapping) else None,
        }
        omission = make_omission_receipt(
            omitted=[
                "active_context.full_block",
                "navigation.entry_commands",
                "documentation_routes",
                "standard.registry_pointer",
                "counts.full_breakdown",
            ],
            reason=(
                "Flag band tells the agent whether the system map exists and what active "
                "phase it points at; deeper sections live at card / --system-map-print."
            ),
            drilldown="./repo-python kernel.py --system-map --output-band card",
        )
        payload_out = {
            "path": rel_path,
            "exists": exists,
            "identity": {"repo": identity.get("repo")} if identity else None,
            "active_phase_id": active_context.get("phase_id") if isinstance(active_context, Mapping) else None,
        }
    else:  # card
        summary = {
            "system_map_present": exists,
            "active_phase_id": active_context.get("phase_id") if isinstance(active_context, Mapping) else None,
            "doctrine_node_count": counts.get("doctrine_nodes") if isinstance(counts, Mapping) else None,
            "documentation_route_count": len(documentation_routes) if isinstance(documentation_routes, Mapping) else 0,
        }
        omission = make_omission_receipt(
            omitted=[
                "navigation.full_command_table",
                "documentation_routes.full_route_bodies",
                "any per-route prose beyond identity + count",
                "kernel_quickstart.full_block",
            ],
            reason=(
                "Card band exposes identity, active context, counts, navigation entry "
                "commands, and the registry pointer. Use --system-map-print for the "
                "full JSON payload."
            ),
            drilldown=drilldown,
        )
        payload_out = {
            "path": rel_path,
            "exists": exists,
            "identity": dict(identity) if identity else None,
            "active_context": dict(active_context) if active_context else None,
            "counts": dict(counts) if counts else None,
            "navigation_entry_commands": navigation.get("entry_commands") if isinstance(navigation.get("entry_commands"), list) else None,
            "kernel_quickstart": navigation.get("kernel_quickstart") if isinstance(navigation.get("kernel_quickstart"), Mapping) else None,
            "standard_pointer": dict(standard_block) if standard_block else None,
            "documentation_route_keys": sorted(documentation_routes.keys()) if isinstance(documentation_routes, Mapping) else None,
        }

    return command_projection(
        command="--system-map",
        band=band,
        selector=identity.get("repo") if isinstance(identity, Mapping) else "system_map",
        summary=summary,
        payload=payload_out,
        currentness=make_currentness(
            status="generated" if exists else "missing",
            recommended_action="trust" if exists else "repair",
            action_reason=None if exists else "system_map.json not present; regenerate via --system-map --system-map-dry-run / generator.",
        ),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=omission,
        validation_contract=make_validation_contract(
            freshness_probe=drilldown,
            failure_modes=[
                "system_map.json missing",
                "JSON decode error in generated map",
                "stale generated map vs source mtimes",
            ],
        ),
        sources={"derived": [rel_path]},
    )


def build_session_diagnostics_projection_envelope(
    *,
    band: str = "flag",
    lens: str = "all",
    last: int = 20,
) -> dict[str, Any]:
    """Wrap --session-diagnostics output in the canonical projection envelope (opt-in)."""
    supported = _COMMAND_OUTPUT_PROJECTION_BANDS["session-diagnostics"]
    if band not in supported:
        return _project_unsupported_band(command="--session-diagnostics", band=band, supported=supported)

    if lens == "latency":
        return _build_session_diagnostics_latency_projection_envelope(band=band, last=last)

    report_lens = "histogram" if lens == "all" else lens
    report_store = "claude" if report_lens == "histogram" else "both"
    try:
        from tools.meta.observability.session_analyzer import build_report
        report = build_report(lens=report_lens, store=report_store, last=last, limit=25)
    except Exception as exc:  # noqa: BLE001
        return {
            "kind": "command_output_projection_error",
            "command": "--session-diagnostics",
            "band": band,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if not isinstance(report, Mapping):
        report = {}
    summary_in = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    lenses = report.get("lenses") if isinstance(report.get("lenses"), Mapping) else {}
    histogram_payload = (
        lenses.get("histogram") if isinstance(lenses.get("histogram"), Mapping) else lenses
    )
    histogram = (
        histogram_payload.get("tool_histogram")
        if isinstance(histogram_payload, Mapping)
        and isinstance(histogram_payload.get("tool_histogram"), list)
        else []
    )
    total_events = (
        summary_in.get("event_count")
        or summary_in.get("total_events")
        or (
            histogram_payload.get("total_records")
            if isinstance(histogram_payload, Mapping)
            else None
        )
        or len(histogram)
    )

    drilldown = f"./repo-python kernel.py --session-diagnostics --lens {lens} --last {last}"

    if band == "flag":
        top_n = histogram[:5] if isinstance(histogram, list) else []
        summary = {
            "lens": lens,
            "last": last,
            "total_events": total_events,
            "top_tool_count": len(top_n),
        }
        omission = make_omission_receipt(
            omitted=[
                "tool_histogram beyond top 5",
                "per-session breakdowns",
                "warning detail",
                "additional lenses",
            ],
            reason=(
                "Flag band carries lens identity + total events + top tool count so the "
                "agent can decide whether to widen the diagnostic lens."
            ),
            drilldown=f"{drilldown} --output-band card",
        )
        payload_out = {
            "lens": lens,
            "last": last,
            "top_tools": top_n,
            "total_events": total_events,
        }
    else:  # card
        bounded_hist = histogram[:25] if isinstance(histogram, list) else []
        summary = {
            "lens": lens,
            "last": last,
            "total_events": total_events,
            "histogram_rows_in_card": len(bounded_hist),
            "histogram_total_rows": len(histogram) if isinstance(histogram, list) else 0,
        }
        omission = make_omission_receipt(
            omitted=[
                f"tool_histogram beyond first {len(bounded_hist)} rows" if len(histogram) > len(bounded_hist) else "(none beyond card)",
                "per-session full breakdown",
                "additional lenses not requested",
                "raw event log",
            ],
            reason=(
                "Card band carries the bounded histogram and lens identity. "
                "Full diagnostic report lives at default --session-diagnostics."
            ),
            drilldown=drilldown,
        )
        payload_out = {
            "lens": lens,
            "last": last,
            "tool_histogram_top": bounded_hist,
            "total_events": total_events,
            "summary": dict(summary_in) if summary_in else None,
        }

    return command_projection(
        command="--session-diagnostics",
        band=band,
        selector=f"{lens}:{last}",
        summary=summary,
        payload=payload_out,
        currentness=make_currentness(),
        drilldown_command=drilldown,
        evidence_command=drilldown,
        omission_receipt=omission,
        validation_contract=make_validation_contract(
            freshness_probe=drilldown,
            failure_modes=[
                "session_analyzer import error",
                "no recent sessions in store",
                "lens or limit invalid",
            ],
        ),
    )


def _session_diagnostics_latency_cache_currentness(
    *,
    cache_path: Path,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    try:
        rel_path = str(cache_path.relative_to(state.REPO_ROOT))
    except ValueError:
        rel_path = str(cache_path)
    try:
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        mtime = None
    generated_at = str(payload.get("generated_at") or "") if isinstance(payload, Mapping) else ""
    return make_currentness(
        status="cached_read_model" if payload else "missing_cache",
        generated_at=generated_at or None,
        source_refs_checked=[rel_path],
        source_mtimes={rel_path: mtime} if mtime else None,
        recommended_action="trust" if payload else "refresh",
        action_reason=None if payload else "process summary cache missing; refresh via process bottleneck builder",
    )


def _build_session_diagnostics_latency_projection_envelope(
    *,
    band: str,
    last: int,
) -> dict[str, Any]:
    """Build the latency output-band projection from the cached process summary."""
    cache = safe_load_json(PROCESS_SUMMARY_PATH) or {}
    summary_in = cache.get("summary") if isinstance(cache.get("summary"), Mapping) else {}
    bottlenecks = (
        cache.get("top_bottlenecks")
        if isinstance(cache.get("top_bottlenecks"), list)
        else []
    )
    try:
        cache_ref = str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT))
    except ValueError:
        cache_ref = str(PROCESS_SUMMARY_PATH)
    drilldown = f"./repo-python kernel.py --session-diagnostics --lens latency --last {last}"
    evidence = "./repo-python kernel.py --process-bottlenecks"
    top_limit = 3 if band == "flag" else 8
    top_rows = [dict(row) for row in bottlenecks[:top_limit] if isinstance(row, Mapping)]
    max_p95_ms = max(
        (int(row.get("p95_ms") or 0) for row in bottlenecks if isinstance(row, Mapping)),
        default=0,
    )
    summary = {
        "lens": "latency",
        "last": last,
        "source": "process_summary_cache",
        "session_count": summary_in.get("session_count"),
        "total_events": summary_in.get("total_span_count"),
        "bottleneck_rows": len(bottlenecks),
        "max_p95_ms": max_p95_ms,
    }
    if band == "flag":
        payload_out = {
            "lens": "latency",
            "last": last,
            "top_bottlenecks": top_rows,
            "total_events": summary_in.get("total_span_count"),
        }
        omitted = [
            "top_bottlenecks beyond first 3",
            "per-session latency rows",
            "Codex SQLite 7d log summary",
            "raw session files",
        ]
        reason = (
            "Flag band carries cached latency bottleneck shape from the process summary "
            "so agents can decide whether to pay the full session-diagnostics latency lens."
        )
    else:
        payload_out = {
            "lens": "latency",
            "last": last,
            "top_bottlenecks": top_rows,
            "process_summary": dict(summary_in),
            "cache_path": cache_ref,
        }
        omitted = [
            "top_bottlenecks beyond first 8",
            "per-session latency rows",
            "raw process ledger",
            "raw session files",
        ]
        reason = (
            "Card band carries the cached process-summary latency shape; full "
            "session-diagnostics remains the drilldown when per-session evidence is needed."
        )

    return command_projection(
        command="--session-diagnostics",
        band=band,
        selector=f"latency:{last}",
        summary=summary,
        payload=payload_out,
        currentness=_session_diagnostics_latency_cache_currentness(
            cache_path=PROCESS_SUMMARY_PATH,
            payload=cache,
        ),
        drilldown_command=drilldown,
        evidence_command=evidence,
        omission_receipt=make_omission_receipt(
            omitted=omitted,
            reason=reason,
            drilldown=drilldown,
        ),
        validation_contract=make_validation_contract(
            freshness_probe=evidence,
            failure_modes=[
                "process summary cache missing",
                "process summary cache malformed",
                "full latency lens required for per-session evidence",
            ],
        ),
        sources={
            "derived": [cache_ref],
            "live_drilldown": [drilldown],
        },
    )


def _row_kind_band_summary(kind_id: str) -> dict[str, Any]:
    """Resolve kind-native legal bands + adapter-populated bands for `cmd_row` refusal.

    Returns a dict with:
      - normalized_kind_id  the canonical kind_id after alias resolution (or the input)
      - legal_bands         declared kind-native bands per std_navigation_contract / kind-band-contract-audit
      - populated_bands     bands the option-surface adapter actually emits today
      - support_status      kind-atlas support_status (option_surface_supported / legacy_command_only / missing)
      - kind_known          True if the audit row exists for this kind

    Used by ``cmd_row`` so structured row_band_unavailable refusals carry
    accurate kind-native metadata, not just the option-surface adapter's flag/card/tape set.
    """
    info: dict[str, Any] = {
        "normalized_kind_id": kind_id,
        "legal_bands": [],
        "populated_bands": [],
        "support_status": "unknown",
        "kind_known": False,
    }
    try:
        audit = build_kind_band_contract_audit(state.REPO_ROOT)
    except Exception:
        audit = {}
    try:
        atlas = build_kind_atlas(state.REPO_ROOT, band="flag")
    except Exception:
        atlas = {}
    audit_rows = audit.get("rows") if isinstance(audit, Mapping) else None
    atlas_rows = atlas.get("rows") if isinstance(atlas, Mapping) else None
    audit_by_kind: dict[str, Mapping[str, Any]] = {}
    if isinstance(audit_rows, list):
        for row in audit_rows:
            if isinstance(row, Mapping):
                kid = str(row.get("kind_id") or "")
                if kid:
                    audit_by_kind[kid] = row
    atlas_by_kind: dict[str, Mapping[str, Any]] = {}
    if isinstance(atlas_rows, list):
        for row in atlas_rows:
            if isinstance(row, Mapping):
                kid = str(row.get("kind_id") or "")
                if kid:
                    atlas_by_kind[kid] = row
    # The option-surface adapter normalizes kind aliases; consult build_option_surface
    # at flag band with no ids to discover the canonical kind_id, but only when the
    # raw kind_id is unknown to the audit/atlas.
    if kind_id not in audit_by_kind and kind_id not in atlas_by_kind:
        try:
            probe = build_option_surface(state.REPO_ROOT, kind_id, band="flag", ids=None)
        except Exception:
            probe = {}
        canonical = str((probe or {}).get("artifact_kind") or "").strip()
        if canonical and canonical != kind_id:
            info["normalized_kind_id"] = canonical
            kind_id = canonical
    audit_row = audit_by_kind.get(kind_id) or {}
    atlas_row = atlas_by_kind.get(kind_id) or {}
    if audit_row:
        info["kind_known"] = True
    info["support_status"] = str(atlas_row.get("support_status") or "unknown")
    declared = audit_row.get("navigable_bands") if isinstance(audit_row, Mapping) else None
    if isinstance(declared, list):
        info["legal_bands"] = [str(b) for b in declared if str(b).strip()]
    populated = atlas_row.get("bands") if isinstance(atlas_row, Mapping) else None
    if isinstance(populated, list):
        info["populated_bands"] = [str(b) for b in populated if str(b).strip()]
    return info


def cmd_row(spec: str, *, band: str = "flag") -> int:
    """Generic --row KIND:ID --band BAND adapter over the option-surface machinery.

    Delegates to ``build_option_surface`` for the requested kind. Refuses
    requests for bands the option-surface adapter does not actually populate.
    Does not synthesize context/deep bands. Honors the Phase 09.45 routing-
    first reversal at the v0 safety level: if the band is not actually emitted
    by the existing adapter, refuse honestly with kind-native legal_bands and
    adapter-populated populated_bands sourced from the kind-band contract audit
    plus the kind atlas — not from the option-surface payload alone.
    """
    raw = str(spec or "").strip()
    if not raw or ":" not in raw:
        return emit_json_with_code(
            row_band_unavailable(
                kind_id="<unspecified>",
                row_id_value="<unspecified>",
                requested_band=str(band),
                reason=(
                    "--row expects KIND:ID (e.g., paper_modules:raw_seed_substrate). "
                    "Pass --band to select a kind-native or command-native band."
                ),
                legal_bands=[],
                populated_bands=[],
                next_safe_commands=[
                    "./repo-python kernel.py --kind-atlas",
                    "./repo-python kernel.py --option-surface paper_modules --band flag",
                ],
            ),
            2,
        )
    kind_id, _, row_id_value = raw.partition(":")
    kind_id = kind_id.strip()
    row_id_value = row_id_value.strip()
    if not kind_id or not row_id_value:
        return emit_json_with_code(
            row_band_unavailable(
                kind_id=kind_id or "<unspecified>",
                row_id_value=row_id_value or "<unspecified>",
                requested_band=str(band),
                reason="--row spec must be of the form KIND:ID with both parts non-empty.",
                legal_bands=[],
                populated_bands=[],
                next_safe_commands=[
                    "./repo-python kernel.py --kind-atlas",
                ],
            ),
            2,
        )

    band_str = str(band or "").strip().lower() or "flag"
    kind_info = _row_kind_band_summary(kind_id)
    canonical_kind = str(kind_info.get("normalized_kind_id") or kind_id)
    legal_bands = list(kind_info.get("legal_bands") or [])
    populated_bands = list(kind_info.get("populated_bands") or [])
    next_safe = [
        f"./repo-python kernel.py --option-surface {canonical_kind} --band flag",
        f"./repo-python kernel.py --option-surface {canonical_kind} --band card --ids {row_id_value}",
    ]

    # Refuse early when the requested band is declared kind-native but the
    # option-surface adapter does not populate it (Phase 09.45 v0 safety).
    if populated_bands and band_str not in populated_bands:
        if legal_bands and band_str in legal_bands:
            reason = (
                f"Band {band_str!r} is declared for kind {canonical_kind!r} per "
                "std_navigation_contract but is not yet populated by the option-surface "
                "adapter. Phase 09.45 routing-first safety: --row refuses unpopulated bands."
            )
        else:
            reason = (
                f"Band {band_str!r} is not in the option-surface adapter's populated band set "
                f"for kind {canonical_kind!r}. Use one of populated_bands."
            )
        return emit_json_with_code(
            row_band_unavailable(
                kind_id=canonical_kind,
                row_id_value=row_id_value,
                requested_band=band_str,
                reason=reason,
                legal_bands=legal_bands or populated_bands,
                populated_bands=populated_bands,
                next_safe_commands=next_safe,
            ),
            2,
        )

    payload = build_option_surface(state.REPO_ROOT, kind_id, band=band_str, ids=[row_id_value])
    if payload.get("profile_status") != "supported":
        # Adapter declined the band — emit a structured refusal, not the raw profile_gap.
        return emit_json_with_code(
            row_band_unavailable(
                kind_id=canonical_kind,
                row_id_value=row_id_value,
                requested_band=band_str,
                reason=(
                    f"Option-surface adapter for kind {canonical_kind!r} did not return a "
                    f"supported profile at band {band_str!r}; the adapter may not yet emit "
                    "this band."
                ),
                legal_bands=legal_bands or populated_bands,
                populated_bands=populated_bands,
                next_safe_commands=next_safe,
            ),
            2,
        )

    rows = payload.get("rows") or []
    selection = payload.get("selection") or {}
    missing_ids = list(selection.get("missing_ids") or []) if isinstance(selection, dict) else []

    if not rows or row_id_value in missing_ids:
        owned = (payload.get("governing_standard") or {}).get("owned_bands") or []
        return emit_json_with_code(
            row_band_unavailable(
                kind_id=canonical_kind,
                row_id_value=row_id_value,
                requested_band=band_str,
                reason=(
                    f"No row found for {row_id_value!r} in kind {canonical_kind!r} at band "
                    f"{band_str!r}. The id may not exist, or the band may be declared but "
                    "unpopulated."
                ),
                legal_bands=legal_bands or [str(b) for b in owned] or ["flag", "card"],
                populated_bands=populated_bands or [str(b) for b in owned] or ["flag", "card"],
                next_safe_commands=next_safe,
            ),
            2,
        )

    row = rows[0] if isinstance(rows[0], dict) else {}
    drilldown = (
        f"./repo-python kernel.py --option-surface {canonical_kind} --band card --ids {row_id_value}"
    )
    evidence = row.get("evidence_command") or drilldown
    envelope = command_projection(
        command="--row",
        band=band_str,
        selector=f"{canonical_kind}:{row_id_value}",
        summary={
            "kind_id": canonical_kind,
            "id": row_id_value,
            "band": band_str,
            "row_count": len(rows),
        },
        payload={"row": row},
        currentness=row.get("currentness") if isinstance(row.get("currentness"), Mapping) else make_currentness(),
        drilldown_command=drilldown,
        evidence_command=str(evidence),
        omission_receipt=make_omission_receipt(
            omitted=["non-selected option-surface fields", "full source body"],
            reason=(
                "--row is a thin adapter over --option-surface; deeper detail lives at the "
                "kind's evidence command."
            ),
            drilldown=drilldown,
        ),
        validation_contract=make_validation_contract(
            freshness_probe=drilldown,
            failure_modes=[
                "kind id alias not normalized",
                "row id missing or renamed",
                "band declared but unpopulated for this kind",
            ],
        ),
        sources=payload.get("source_refs") if isinstance(payload.get("source_refs"), Mapping) else None,
    )
    return emit_json(envelope)


def cmd_command_output_projection_audit() -> int:
    """Emit the command-output projection audit per std_command_output_projection.json."""
    payload = build_command_output_projection_audit()
    return emit_json(payload)


def cmd_command_output_duplication_audit() -> int:
    """Emit the report-only semantic duplication audit for projected packets."""
    payload = build_command_output_duplication_audit()
    return emit_json(payload)


# Thin wrappers used when --output-band is supplied on a retrofitted command.
# Default emission for each command remains unchanged; these wrappers are only
# invoked from kernel.py dispatch when args.output_band is set.

def cmd_phase_projection(*, band: str, phase_token: str | None = None) -> int:
    return emit_json(build_phase_projection_envelope(band=band, phase_token=phase_token))


def cmd_paper_module_projection(*, band: str, slug: str | None = None) -> int:
    return emit_json(build_paper_module_projection_envelope(band=band, slug=slug))


def cmd_info_projection(*, band: str) -> int:
    return emit_json(build_info_projection_envelope(band=band))


def cmd_frontier_projection(*, band: str, limit: int | None = None) -> int:
    return emit_json(build_frontier_projection_envelope(band=band, limit=limit))


def cmd_docs_route_projection(*, band: str, request: str) -> int:
    return emit_json(build_docs_route_projection_envelope(band=band, request=request))


def cmd_pulse_projection(*, band: str) -> int:
    return emit_json(build_pulse_projection_envelope(band=band))


def cmd_working_set_projection(*, band: str, limit: int | None = None, anchor: str | None = None) -> int:
    return emit_json(build_working_set_projection_envelope(band=band, limit=limit, anchor=anchor))


def cmd_system_map_projection(*, band: str) -> int:
    return emit_json(build_system_map_projection_envelope(band=band))


def cmd_session_diagnostics_projection(*, band: str, lens: str = "all", last: int = 20) -> int:
    return emit_json(build_session_diagnostics_projection_envelope(band=band, lens=lens, last=last))


def cmd_navigation_context_rosetta(*, context_budget: int = 1400) -> int:
    """Emit a read-only Rosetta packet for budgeted context compression."""
    payload = build_navigation_context_rosetta(state.REPO_ROOT, context_budget=context_budget)
    return emit_json(payload)


def cmd_agent_operating_packet(*, band: str = "summary") -> int:
    """Emit the generated principle/axiom operating packet in a bounded band."""
    from system.lib.agent_operating_packet import (
        build_agent_operating_packet_strip,
        build_agent_principle_lens,
        load_agent_operating_packet,
    )

    packet = load_agent_operating_packet(state.REPO_ROOT)
    normalized_band = str(band or "summary").strip().lower()
    strip = build_agent_operating_packet_strip(packet)
    if normalized_band in {"summary", "flag", "strip"}:
        return emit_json(strip)
    if normalized_band in {"agent_principles", "agent-principles", "lens"}:
        lens = build_agent_principle_lens(packet, max_rows=32)
        payload = {
            "kind": "agent_principles_card",
            "schema_version": packet.get("schema_version"),
            "authority_posture": packet.get("authority_posture"),
            "purpose": "Compact active agent-principle lens for Type A behavior, entry failures, proof binding, and substrate work.",
            "agent_principle_lens": lens,
            "selection_policy": (packet.get("selection_policy") or {}).get("agent_principles")
            if isinstance(packet.get("selection_policy"), Mapping)
            else None,
            "commands": {
                "entry_lens": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                "all_agent_principles": "./repo-python kernel.py --agent-principles --band card",
                "principle_cards": (packet.get("commands") or {}).get("agent_principle_cards")
                if isinstance(packet.get("commands"), Mapping)
                else None,
                "agent_operating_packet": "./repo-python kernel.py --agent-operating-packet --band card",
            },
            "source_refs": packet.get("source_refs"),
            "omission_receipt": {
                "omitted": ["always-global rows", "candidate axiom pressure", "full principle tape"],
                "reason": "This band is only the agent-principle behavior lens; use --agent-operating-packet --band card for the broader runtime doctrine frame.",
            },
        }
        return emit_json(payload)
    if normalized_band == "card":
        capsule = packet.get("global_runtime_capsule") if isinstance(packet.get("global_runtime_capsule"), Mapping) else {}
        axiom_pressure = packet.get("candidate_axiom_pressure") if isinstance(packet.get("candidate_axiom_pressure"), Mapping) else {}
        payload = {
            "kind": "agent_operating_packet_card",
            "schema_version": packet.get("schema_version"),
            "authority_posture": packet.get("authority_posture"),
            "purpose": packet.get("purpose"),
            "selection_policy": packet.get("selection_policy"),
            "global_runtime_capsule": capsule,
            "frequent_principles": packet.get("frequent_principles"),
            "candidate_axiom_pressure": {
                "authority_posture": axiom_pressure.get("authority_posture"),
                "non_law_warning": axiom_pressure.get("non_law_warning"),
                "rows": list(axiom_pressure.get("rows") or [])[:6],
                "omitted_count": max(0, len(axiom_pressure.get("rows") or []) - 6),
            },
            "classification_summary": packet.get("classification_summary"),
            "routing_matrix": packet.get("routing_matrix"),
            "budget_metrics": packet.get("budget_metrics"),
            "commands": packet.get("commands"),
            "source_refs": packet.get("source_refs"),
        }
        return emit_json(payload)
    return emit_json(packet)


def cmd_agent_principle_authoring(
    lesson: str | None = None,
    *,
    context_budget: int = 12000,
) -> int:
    """Emit the governed authoring packet for Type A agent principles."""
    from system.lib.agent_operating_packet import (
        build_agent_principle_authoring_packet,
        load_agent_operating_packet,
    )

    _ = context_budget
    packet = load_agent_operating_packet(state.REPO_ROOT)
    return emit_json(build_agent_principle_authoring_packet(packet, task_text=lesson or ""))


def cmd_navigation_context_pack(
    query: str,
    *,
    context_budget: int = 12000,
    include_transaction_control_plane: bool = False,
) -> int:
    """Emit a task-conditioned, mixed-band navigation context pack."""
    from system.lib.navigation_context_pack import build_navigation_context_pack

    payload = build_navigation_context_pack(
        state.REPO_ROOT,
        query,
        context_budget=context_budget,
        include_transaction_control_plane=include_transaction_control_plane,
    )
    return emit_json(payload)


def cmd_navigation_surface_audit(query: str | None = None, *, context_budget: int = 12000) -> int:
    """Emit read-only diagnostics for navigation route size and contract fit."""
    from system.lib.navigation_surface_audit import build_navigation_surface_audit

    payload = build_navigation_surface_audit(
        state.REPO_ROOT,
        query=query,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_clusterability_audit(*, context_budget: int = 12000) -> int:
    """Emit high-cardinality clusterability classification for option surfaces."""
    from system.lib.navigation_clusterability import build_navigation_clusterability_audit

    payload = build_navigation_clusterability_audit(
        state.REPO_ROOT,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_annex_routing_coverage(*, context_budget: int = 12000) -> int:
    """Emit annex pattern cluster-key routing coverage diagnostics."""
    from system.lib.annex_routing_coverage import build_annex_routing_coverage

    payload = build_annex_routing_coverage(
        state.REPO_ROOT,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_annex_currentness(*, context_budget: int = 12000) -> int:
    """Emit annex sync-digest currentness and upstream-movement diagnostics."""
    from system.lib.annex_currentness import build_annex_currentness

    payload = build_annex_currentness(
        state.REPO_ROOT,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_annex_movement_pressure_map(query: str | None = None, *, context_budget: int = 12000) -> int:
    """Emit read-only movement-pressure rows for mine_upstream_delta annex jobs."""
    from system.lib.annex_movement_pressure_map import build_annex_movement_pressure_map

    payload = build_annex_movement_pressure_map(
        state.REPO_ROOT,
        query=query,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_annex_navigation_dogfood(query: str | None = None, *, context_budget: int = 12000) -> int:
    """Emit annex navigation self-use diagnostics over compressed annex surfaces."""
    from system.lib.annex_navigation_dogfood import build_annex_navigation_dogfood

    payload = build_annex_navigation_dogfood(
        state.REPO_ROOT,
        query=query,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_surface_authoring_audit(*, context_budget: int = 12000) -> int:
    """Emit read-only authoring debt for compressed navigation rungs."""
    from system.lib.surface_authoring_audit import build_surface_authoring_audit

    payload = build_surface_authoring_audit(
        state.REPO_ROOT,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_latency_seed_digest(
    *,
    top_n: int = 5,
    include_git: bool = True,
    output_format: str = "json",
) -> int:
    """Emit the compact first-contact packet for latency seed coordination."""
    from system.lib.latency_seed_digest import build_latency_seed_digest, render_markdown

    payload = build_latency_seed_digest(
        state.REPO_ROOT,
        include_git=include_git,
        top_n=top_n,
    )
    if output_format == "markdown":
        print(render_markdown(payload), end="")
        return 0
    return emit_json(payload)


def _command_profile_payload_bytes(payload: Any) -> int:
    try:
        return len(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
    except TypeError:
        return len(json.dumps(str(payload), ensure_ascii=False).encode("utf-8"))


def _command_profile_output_shape(payload: Any, *, limit: int = 8) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "schema": "command_profile_output_shape_v0",
            "payload_type": type(payload).__name__,
            "output_bytes": _command_profile_payload_bytes(payload),
        }
    sections: list[dict[str, Any]] = []
    for key, value in payload.items():
        sections.append(
            {
                "section": str(key),
                "bytes": _command_profile_payload_bytes(value),
            }
        )
    sections.sort(key=lambda row: int(row.get("bytes") or 0), reverse=True)

    selected_rows = payload.get("selected_rows")
    selected_row_shapes: list[dict[str, Any]] = []
    if isinstance(selected_rows, Sequence) and not isinstance(selected_rows, (str, bytes, bytearray)):
        for index, row in enumerate(selected_rows):
            if not isinstance(row, Mapping):
                continue
            selected_row_shapes.append(
                {
                    "index": index,
                    "kind_id": row.get("kind_id"),
                    "row_id": row.get("row_id"),
                    "bytes": _command_profile_payload_bytes(row),
                }
            )
        selected_row_shapes.sort(key=lambda row: int(row.get("bytes") or 0), reverse=True)

    return {
        "schema": "command_profile_output_shape_v0",
        "output_bytes": _command_profile_payload_bytes(payload),
        "top_sections": sections[:limit],
        "section_count": len(sections),
        "selected_row_count": len(selected_rows) if isinstance(selected_rows, Sequence) else None,
        "top_selected_rows": selected_row_shapes[: min(limit, 6)] if selected_row_shapes else [],
    }


_COMMAND_PROFILE_SUPPORTED_SURFACES = [
    "info",
    "entry",
    "navigation-metabolism",
    "entrypoint-health",
    "pulse",
    "preflight",
    "phase",
    "context-pack",
    "process-summary",
    "process-bottlenecks",
    "latency-seed-digest",
    "latency-speedboard",
    "generated-state-drainer",
    "actor-receipt",
]


_COMMAND_PROFILE_ACTION_KIND_REDIRECTS = {
    "bash-grep": {
        "action_kind": "bash_grep",
        "owner_surface": "process_bottlenecks",
        "owner_check_command": "./repo-python kernel.py --process-bottlenecks",
        "force_live_command": "./repo-python kernel.py --process-bottlenecks --force",
        "reason": "bash_grep is a process-audit action kind, not a kernel command-profile surface.",
    },
    "grep-tool": {
        "action_kind": "grep_tool",
        "owner_surface": "process_bottlenecks",
        "owner_check_command": "./repo-python kernel.py --process-bottlenecks",
        "force_live_command": "./repo-python kernel.py --process-bottlenecks --force",
        "reason": "grep_tool is a process-audit action kind, not a kernel command-profile surface.",
    },
    "glob-tool": {
        "action_kind": "glob_tool",
        "owner_surface": "process_bottlenecks",
        "owner_check_command": "./repo-python kernel.py --process-bottlenecks",
        "force_live_command": "./repo-python kernel.py --process-bottlenecks --force",
        "reason": "glob_tool is a process-audit action kind, not a kernel command-profile surface.",
    },
}


def _infer_command_profile_surface(
    requested_surface: str | None,
    *,
    entry_task: str | None,
    navigation_metabolism_query: str | None,
    entrypoint_health: bool,
    pulse: bool,
    phase_token: str | None,
    context_pack_query: str | None,
) -> str:
    surface = str(requested_surface or "auto").strip().lower().replace("_", "-")
    if surface not in {"", "auto"}:
        return surface
    if entry_task is not None:
        return "entry"
    if navigation_metabolism_query is not None:
        return "navigation-metabolism"
    if entrypoint_health:
        return "entrypoint-health"
    if pulse:
        return "pulse"
    if phase_token is not None:
        return "phase"
    if context_pack_query is not None:
        return "context-pack"
    return "navigation-metabolism"


def cmd_command_profile(
    requested_surface: str | None = None,
    *,
    entry_task: str | None = None,
    navigation_metabolism_query: str | None = None,
    metabolism_profile: str = "quick",
    context_budget: int = 12000,
    entrypoint_health: bool = False,
    pulse: bool = False,
    phase_token: str | None = None,
    context_pack_query: str | None = None,
) -> int:
    """Emit a compact timing packet for first-contact command surfaces."""
    surface = _infer_command_profile_surface(
        requested_surface,
        entry_task=entry_task,
        navigation_metabolism_query=navigation_metabolism_query,
        entrypoint_health=entrypoint_health,
        pulse=pulse,
        phase_token=phase_token,
        context_pack_query=context_pack_query,
    )
    phases: list[dict[str, Any]] = []
    started = perf_counter()
    payload: Any
    if surface == "info":
        result = _info_compact_result(profile_sink=phases)
        payload = result.to_dict(state.KERNEL_VERSION, full=False)
    elif surface == "entry":
        from system.lib.kernel.commands.comprehension_snapshot import build_entry_packet

        entry_started = perf_counter()
        payload = build_entry_packet(
            state.REPO_ROOT,
            task=entry_task,
            context_budget=context_budget,
        )
        entry_ms = round((perf_counter() - entry_started) * 1000, 3)
        admission = payload.get("entry_payload_admission") if isinstance(payload, Mapping) else {}
        selected_lane = payload.get("selected_lane") if isinstance(payload, Mapping) else {}
        phases.append(
            {
                "phase": "entry_packet_build",
                "ms": entry_ms,
                "output_bytes": _command_profile_payload_bytes(payload),
                "recognized_situation": payload.get("recognized_situation")
                if isinstance(payload, Mapping)
                else None,
                "selected_lane_id": selected_lane.get("lane_id")
                if isinstance(selected_lane, Mapping)
                else None,
                "admission_status": admission.get("status")
                if isinstance(admission, Mapping)
                else None,
                "admission_saved_bytes": admission.get("saved_bytes")
                if isinstance(admission, Mapping)
                else None,
            }
        )
        phases.append(
            {
                "phase": "entry_packet_output_shape",
                "ms": 0.0,
                **_command_profile_output_shape(payload),
            }
        )
    elif surface in {"navigation-metabolism", "surface-ratchet"}:
        from system.lib.navigation_metabolism_ledger import (
            build_navigation_metabolism_ledger,
            compact_quick_navigation_metabolism_packet_for_cli,
        )

        payload = build_navigation_metabolism_ledger(
            state.REPO_ROOT,
            query=navigation_metabolism_query,
            context_budget=context_budget,
            metabolism_profile=metabolism_profile,
            profile_sink=phases,
        )
        if str(metabolism_profile or "").strip().lower() == "quick":
            payload = compact_quick_navigation_metabolism_packet_for_cli(
                payload,
                context_budget=context_budget,
            )
        surface = "navigation-metabolism"
    elif surface == "entrypoint-health":
        from system.lib.entrypoint_health import build_entrypoint_health

        payload = build_entrypoint_health(state.REPO_ROOT)
    elif surface == "pulse":
        payload = _pulse_snapshot(profile_sink=phases)
    elif surface == "preflight":
        payload = _preflight_card(profile_sink=phases)
    elif surface == "phase":
        navigator = KernelNavigation(state.REPO_ROOT)
        result = navigator.build_phase(
            phase_token,
            include_transaction_control_plane=False,
        )
        payload = _phase_output_mode_packet(result, output_mode="summary")
    elif surface == "context-pack":
        from system.lib.navigation_context_pack import build_navigation_context_pack

        context_pack_started = perf_counter()
        payload = build_navigation_context_pack(
            state.REPO_ROOT,
            query=context_pack_query or "",
            context_budget=context_budget,
        )
        context_pack_ms = round((perf_counter() - context_pack_started) * 1000, 3)
        budget = payload.get("budget") if isinstance(payload, Mapping) else {}
        phases.append(
            {
                "phase": "context_pack_build",
                "ms": context_pack_ms,
                "output_bytes": _command_profile_payload_bytes(payload),
                "contract_status": budget.get("contract_status")
                if isinstance(budget, Mapping)
                else None,
                "estimated_tokens": budget.get("estimated_tokens")
                if isinstance(budget, Mapping)
                else None,
            }
        )
        strategy = payload.get("strategy") if isinstance(payload, Mapping) else {}
        stage_timings = (
            strategy.get("stage_timings_ms") if isinstance(strategy, Mapping) else None
        )
        if isinstance(stage_timings, Mapping):
            for stage_name, stage_ms in stage_timings.items():
                phases.append(
                    {
                        "phase": f"context_pack.{stage_name}",
                        "ms": round(float(stage_ms or 0), 3),
                    }
                )
        phases.append(
            {
                "phase": "context_pack_output_shape",
                "ms": 0.0,
                **_command_profile_output_shape(payload),
            }
        )
    elif surface in {"process-bottlenecks", "process_bottlenecks"}:
        process_bottleneck_started = perf_counter()
        payload = _build_process_bottlenecks_packet()
        phases.append(
            {
                "phase": "process_bottlenecks_status_packet",
                "ms": round((perf_counter() - process_bottleneck_started) * 1000, 3),
                "output_bytes": _command_profile_payload_bytes(payload),
                "source_mode": (
                    payload.get("source_freshness", {}).get("mode")
                    if isinstance(payload, Mapping)
                    else None
                ),
                "decision_authority": (
                    payload.get("decision_authority", {}).get("status")
                    if isinstance(payload, Mapping)
                    else None
                ),
            }
        )
        surface = "process-bottlenecks"
    elif surface in {"process-summary", "process_summary"}:
        from system.lib.agent_execution_trace import build_process_summary_route_packet

        process_summary_started = perf_counter()
        code, payload = build_process_summary_route_packet(
            repo_root=_repo_root_for_static_registry(),
            request="codex:latest",
        )
        phases.append(
            {
                "phase": "process_summary_status_packet",
                "ms": round((perf_counter() - process_summary_started) * 1000, 3),
                "output_bytes": _command_profile_payload_bytes(payload),
                "request": "codex:latest",
                "return_code": code,
                "source_mode": (
                    payload.get("source_freshness", {}).get("mode")
                    if isinstance(payload, Mapping)
                    else None
                ),
                "source_status": (
                    payload.get("source_freshness", {}).get("status")
                    if isinstance(payload, Mapping)
                    else None
                ),
                "selected_session_id": (
                    payload.get("summary", {}).get("session_id")
                    if isinstance(payload, Mapping)
                    else None
                ),
            }
        )
        surface = "process-summary"
    elif surface in {"latency-seed-digest", "latency_seed_digest"}:
        from system.lib.latency_seed_digest import build_latency_seed_digest

        payload = build_latency_seed_digest(state.REPO_ROOT, profile_sink=phases)
        surface = "latency-seed-digest"
    elif surface in {"latency-speedboard", "latency_speedboard"}:
        from system.lib import latency_speedboard

        repo_root = _repo_root_for_static_registry()
        materialized_started = perf_counter()
        written_speedboard = latency_speedboard.load_written_speedboard(repo_root)
        materialized_read_model_source = "written_speedboard" if written_speedboard else "rebuilt_in_memory"
        materialized_board = written_speedboard or latency_speedboard.build_speedboard(repo_root)
        materialized_summary = latency_speedboard.summarize_speedboard(
            materialized_board,
            preview_limit=3,
        )
        materialized_source = (
            materialized_summary.get("remaining_bottlenecks_source", {})
            if isinstance(materialized_summary, Mapping)
            else {}
        )
        phases.append(
            {
                "phase": "latency_speedboard_materialized_summary",
                "ms": round((perf_counter() - materialized_started) * 1000, 3),
                "output_bytes": _command_profile_payload_bytes(materialized_summary),
                "source_mode": (
                    materialized_source.get("mode")
                    if isinstance(materialized_source, Mapping)
                    else None
                ),
                "source_status": (
                    materialized_source.get("status")
                    if isinstance(materialized_source, Mapping)
                    else None
                ),
                "remaining_bottleneck_count": (
                    len(materialized_summary.get("remaining_bottlenecks", []))
                    if isinstance(materialized_summary, Mapping)
                    else 0
                ),
                "read_model_source": materialized_read_model_source,
            }
        )
        live_started = perf_counter()
        materialized_remaining_count = (
            len(materialized_summary.get("remaining_bottlenecks", []))
            if isinstance(materialized_summary, Mapping)
            else 0
        )
        materialized_source_status = (
            str(materialized_source.get("status") or "")
            if isinstance(materialized_source, Mapping)
            else ""
        )
        if materialized_remaining_count and materialized_source_status not in {"missing", "unavailable"}:
            live_summary = {
                "remaining_bottlenecks": [],
                "remaining_bottlenecks_source": {
                    "mode": "deferred",
                    "status": "deferred_materialized_summary_available",
                    "reason": "materialized_speedboard_remaining_bottlenecks_available",
                    "refresh_command": (
                        "./repo-python tools/meta/observability/latency_speedboard.py "
                        "show --live-process --process-limit 3 --limit 3"
                    ),
                },
            }
            live_source = live_summary["remaining_bottlenecks_source"]
            live_skipped = True
        else:
            live_board = latency_speedboard.build_speedboard(
                repo_root,
                live_process=True,
                process_limit=3,
            )
            live_summary = latency_speedboard.summarize_speedboard(
                live_board,
                preview_limit=3,
            )
            live_source = (
                live_summary.get("remaining_bottlenecks_source", {})
                if isinstance(live_summary, Mapping)
                else {}
            )
            live_skipped = False
        phases.append(
            {
                "phase": "latency_speedboard_live_process_summary",
                "ms": round((perf_counter() - live_started) * 1000, 3),
                "output_bytes": _command_profile_payload_bytes(live_summary),
                "source_mode": (
                    live_source.get("mode")
                    if isinstance(live_source, Mapping)
                    else None
                ),
                "source_status": (
                    live_source.get("status")
                    if isinstance(live_source, Mapping)
                    else None
                ),
                "process_limit": 3,
                "session_count": (
                    live_source.get("session_count")
                    if isinstance(live_source, Mapping)
                    else None
                ),
                "remaining_bottleneck_count": (
                    len(live_summary.get("remaining_bottlenecks", []))
                    if isinstance(live_summary, Mapping)
                    else 0
                ),
                "skipped": live_skipped,
            }
        )
        payload = {
            "schema": "latency_speedboard_command_profile_payload_v0",
            "surface": "latency-speedboard",
            "profiled_commands": [
                "./repo-python tools/meta/observability/latency_speedboard.py --json --limit 3",
                (
                    "./repo-python tools/meta/observability/latency_speedboard.py "
                    "show --live-process --process-limit 3 --limit 3"
                ),
            ],
            "materialized": {
                "source_status": materialized_source.get("status")
                if isinstance(materialized_source, Mapping)
                else None,
                "source_mode": materialized_source.get("mode")
                if isinstance(materialized_source, Mapping)
                else None,
                "remaining_bottleneck_count": (
                    len(materialized_summary.get("remaining_bottlenecks", []))
                    if isinstance(materialized_summary, Mapping)
                    else 0
                ),
                "read_model_source": materialized_read_model_source,
            },
            "live_process": {
                "source_status": live_source.get("status")
                if isinstance(live_source, Mapping)
                else None,
                "source_mode": live_source.get("mode")
                if isinstance(live_source, Mapping)
                else None,
                "process_limit": 3,
                "session_count": live_source.get("session_count")
                if isinstance(live_source, Mapping)
                else None,
                "remaining_bottleneck_count": (
                    len(live_summary.get("remaining_bottlenecks", []))
                    if isinstance(live_summary, Mapping)
                    else 0
                ),
                "skipped": live_skipped,
            },
            "privacy_boundary": "speedboard summaries emit timing/count/path metadata only; no raw stdout or stderr bodies",
        }
        surface = "latency-speedboard"
    elif surface == "generated-state-drainer":
        from system.lib.generated_state_drainer import build_generated_projection_settlement_fast_plan

        fast_plan_started = perf_counter()
        fast_plan_payload = build_generated_projection_settlement_fast_plan(state.REPO_ROOT)
        phases.append(
            {
                "phase": "settlement_fast_plan",
                "ms": round((perf_counter() - fast_plan_started) * 1000, 3),
                "output_bytes": _command_profile_payload_bytes(fast_plan_payload),
            }
        )
        payload = {
            "schema": "generated_state_drainer_command_profile_payload_v0",
            "surface": "generated-state-drainer",
            "profiled_commands": [
                "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --fast",
            ],
            "fast_plan_summary": {
                "status": fast_plan_payload.get("status") if isinstance(fast_plan_payload, Mapping) else None,
                "dirty_owner_count": fast_plan_payload.get("dirty_owner_count")
                if isinstance(fast_plan_payload, Mapping)
                else None,
                "refresh_required_owner_count": fast_plan_payload.get("refresh_required_owner_count")
                if isinstance(fast_plan_payload, Mapping)
                else None,
                "blocked_owner_count": fast_plan_payload.get("blocked_owner_count")
                if isinstance(fast_plan_payload, Mapping)
                else None,
                "required_next_command": fast_plan_payload.get("required_next_command")
                if isinstance(fast_plan_payload, Mapping)
                else None,
            },
            "status_drilldown_command": "./repo-python tools/meta/control/generated_state_drainer.py status",
            "full_authority_command": "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --full-diff-stat",
            "privacy_boundary": "path/status/count metadata only; does not run settle, commit, or store stdout/stderr bodies",
        }
    elif surface in {"actor-receipt", "actor_delivery_receipt"}:
        from tools.meta.factory import check_agent_bootstrap_projection as checker

        previous_root = checker.REPO_ROOT
        checker.REPO_ROOT = state.REPO_ROOT
        try:
            cfg = checker.load_agent_bootstrap_config(state.REPO_ROOT)
            context = checker.build_actor_receipt_context(state.REPO_ROOT, cfg)
            payload = checker.build_actor_receipt(context, run_smokes=False)
        finally:
            checker.REPO_ROOT = previous_root
        surface = "actor-receipt"
    else:
        action_kind_redirect = _COMMAND_PROFILE_ACTION_KIND_REDIRECTS.get(surface)
        if action_kind_redirect is not None:
            owner_check_command = action_kind_redirect["owner_check_command"]
            force_live_command = action_kind_redirect["force_live_command"]
            return emit_json(
                {
                    "kind": "command_profile",
                    "schema_version": "command_profile_action_kind_redirect_v0",
                    "status": "action_kind_redirect",
                    "surface": surface,
                    "action_kind": action_kind_redirect["action_kind"],
                    "owner_surface": action_kind_redirect["owner_surface"],
                    "reason": action_kind_redirect["reason"],
                    "owner_check_command": owner_check_command,
                    "force_live_command": force_live_command,
                    "suggested_command": owner_check_command,
                    "next_commands": [
                        owner_check_command,
                        force_live_command,
                        (
                            './repo-python kernel.py --navigation-metabolism "slow bash grep owner route" '
                            "--metabolism-profile quick --context-budget 12000"
                        ),
                    ],
                    "source_projection_boundary": {
                        "action_kind_policy": "process_audit_action_kind_not_kernel_command_surface",
                        "cached_summary_policy": "advisory_only_for_candidate_ranking",
                        "patch_selection_policy": "force_live_before_source_patch",
                        "default_status_route": owner_check_command,
                        "authoritative_decision_route": force_live_command,
                    },
                    "supported_surfaces": list(_COMMAND_PROFILE_SUPPORTED_SURFACES),
                }
            )
        return emit_json_with_code(
            {
                "kind": "command_profile",
                "status": "unsupported_surface",
                "surface": surface,
                "supported_surfaces": list(_COMMAND_PROFILE_SUPPORTED_SURFACES),
            },
            2,
        )
    total_ms = round((perf_counter() - started) * 1000, 3)
    cache_nodes = payload.get("command_node_cache") if isinstance(payload, Mapping) else None
    profile = {
        "kind": "command_profile",
        "schema_version": "command_profile_v0",
        "surface": surface,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile_scope": "in_process_after_dispatch",
        "profile_scope_caveat": (
            "Excludes wrapper startup, Python import, argparse dispatch, and stdout"
            " serialization seen by the agent's tool host. Use --entry-ladder for the"
            " end-to-end ladder shape; CLI wall time can exceed total_ms when a surface"
            " starts subprocess probes or the tool host waits on process teardown."
        ),
        "total_ms": total_ms,
        "output_bytes": _command_profile_payload_bytes(payload),
        "context_budget": context_budget,
        "metabolism_profile": metabolism_profile if surface == "navigation-metabolism" else None,
        "phases": phases,
        "cache_nodes": cache_nodes if isinstance(cache_nodes, Mapping) else {},
        "cache_controls": {
            "disable": "AIW_COMMAND_CACHE=0",
            "refresh": "AIW_COMMAND_CACHE_REFRESH=1",
        },
    }
    return emit_json(profile)


def _classify_entry_next_action(command: str) -> dict[str, Any]:
    """Parse the entry packet's next_action.command into a (surface, query) handle."""
    import shlex

    if not command:
        return {"surface": "unknown", "raw_command": ""}
    try:
        tokens = shlex.split(command)
    except ValueError:
        return {"surface": "unparseable", "raw_command": command}
    surface_tokens = {
        "--context-pack",
        "--navigation-metabolism",
        "--paper-module",
        "--kind-atlas",
        "--option-surface",
        "--row",
        "--docs-route",
    }
    surface = "unknown"
    arg: str | None = None
    metabolism_profile: str | None = None
    for index, token in enumerate(tokens):
        if token in surface_tokens and surface == "unknown":
            surface = token.lstrip("-")
            if index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
                arg = tokens[index + 1]
        elif token == "--metabolism-profile" and index + 1 < len(tokens):
            metabolism_profile = tokens[index + 1]
    classified: dict[str, Any] = {"surface": surface, "raw_command": command}
    if arg is not None:
        classified["query"] = arg
    if metabolism_profile is not None:
        classified["metabolism_profile"] = metabolism_profile
    return classified


def cmd_entry_ladder(
    task: str | None = None,
    *,
    context_budget: int = 12000,
    metabolism_profile: str = "quick",
) -> int:
    """Profile the actual entry ladder: --entry plus the first follow-up command it routes to.

    A cheap entry packet that routes immediately to an expensive follow-up still
    reproduces the original command-substrate stampede. This surface measures
    both steps in one in-process run.
    """
    from system.lib.kernel.commands.comprehension_snapshot import build_entry_packet

    overall_started = perf_counter()
    steps: list[dict[str, Any]] = []
    aggregate_cache_nodes: dict[str, Any] = {}

    step_started = perf_counter()
    entry_payload = build_entry_packet(state.REPO_ROOT, task=task or "", context_budget=context_budget)
    entry_ms = round((perf_counter() - step_started) * 1000, 3)
    entry_bytes = _command_profile_payload_bytes(entry_payload)
    next_action_block = entry_payload.get("next_action") if isinstance(entry_payload, Mapping) else {}
    next_action = next_action_block if isinstance(next_action_block, Mapping) else {}
    next_command = str(next_action.get("command") or "")
    steps.append(
        {
            "step_index": 0,
            "surface": "entry",
            "ms": entry_ms,
            "output_bytes": entry_bytes,
            "selected_lane": entry_payload.get("selected_lane") if isinstance(entry_payload, Mapping) else None,
            "next_action_command": next_command,
        }
    )

    classified = _classify_entry_next_action(next_command)
    next_surface = classified.get("surface", "unknown")
    follow_up_step: dict[str, Any] = {
        "step_index": 1,
        "surface": next_surface,
        "raw_command": next_command,
    }
    follow_up_payload: Any = None
    follow_step_started = perf_counter()
    if next_surface == "context-pack":
        from system.lib.navigation_context_pack import build_navigation_context_pack

        follow_up_payload = build_navigation_context_pack(
            state.REPO_ROOT,
            query=str(classified.get("query") or task or ""),
            context_budget=context_budget,
        )
    elif next_surface == "kind-atlas":
        follow_up_payload = build_kind_atlas(state.REPO_ROOT, band="flag")
    elif next_surface == "navigation-metabolism":
        from system.lib.navigation_metabolism_ledger import build_navigation_metabolism_ledger

        ladder_phases: list[dict[str, Any]] = []
        follow_up_payload = build_navigation_metabolism_ledger(
            state.REPO_ROOT,
            query=str(classified.get("query") or task or ""),
            context_budget=context_budget,
            metabolism_profile=str(classified.get("metabolism_profile") or metabolism_profile),
            profile_sink=ladder_phases,
        )
        follow_up_step["phases"] = ladder_phases
    else:
        follow_up_step["status"] = "unsupported_step_in_ladder_profile"

    if follow_up_payload is not None:
        follow_up_step["ms"] = round((perf_counter() - follow_step_started) * 1000, 3)
        follow_up_step["output_bytes"] = _command_profile_payload_bytes(follow_up_payload)
        if isinstance(follow_up_payload, Mapping):
            cache_nodes_block = follow_up_payload.get("command_node_cache")
            if isinstance(cache_nodes_block, Mapping):
                aggregate_cache_nodes.update(cache_nodes_block)
                follow_up_step["cache_nodes"] = dict(cache_nodes_block)
    steps.append(follow_up_step)

    total_ms = round((perf_counter() - overall_started) * 1000, 3)
    total_output_bytes = sum(int(step.get("output_bytes") or 0) for step in steps)
    profile = {
        "kind": "command_profile",
        "schema_version": "command_profile_v0",
        "surface": "entry_ladder",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile_scope": "in_process_after_dispatch",
        "profile_scope_caveat": (
            "Two-step in-process ladder: --entry then the first command the entry packet"
            " routed to. Excludes wrapper/import/dispatch overhead and stdout serialization."
        ),
        "task": task,
        "context_budget": context_budget,
        "metabolism_profile_default": metabolism_profile,
        "total_ms": total_ms,
        "total_output_bytes": total_output_bytes,
        "steps": steps,
        "cache_nodes": aggregate_cache_nodes,
        "cache_controls": {
            "disable": "AIW_COMMAND_CACHE=0",
            "refresh": "AIW_COMMAND_CACHE_REFRESH=1",
        },
    }
    return emit_json(profile)


def cmd_command_output_read(rel_path: str, *, band: str = "summary") -> int:
    """Read a sidecar payload from `state/command_outputs/` bounded to a band.

    The sidecar receipt advertises this surface so concurrent agents can drill
    in without dumping the full payload through their tool host buffer. Path
    is restricted to `state/command_outputs/` to keep the read surface small.
    """
    if not rel_path:
        return emit_json_with_code(
            {
                "kind": "command_output_read_error",
                "schema_version": "command_output_read_v0",
                "status": "missing_path",
            },
            2,
        )
    repo_root = state.REPO_ROOT.resolve()
    expected_root = (repo_root / "state" / "command_outputs").resolve()
    raw_path = Path(rel_path)
    if not raw_path.is_absolute():
        raw_path = repo_root / raw_path
    target = raw_path.resolve()
    try:
        target.relative_to(expected_root)
    except ValueError:
        return emit_json_with_code(
            {
                "kind": "command_output_read_error",
                "schema_version": "command_output_read_v0",
                "status": "path_outside_command_outputs",
                "path": rel_path,
                "expected_root": str(expected_root.relative_to(repo_root)),
            },
            2,
        )
    if not target.is_file():
        return emit_json_with_code(
            {
                "kind": "command_output_read_error",
                "schema_version": "command_output_read_v0",
                "status": "not_found",
                "path": rel_path,
            },
            2,
        )
    band_choice = band.strip().lower() if isinstance(band, str) else "summary"
    if band_choice not in {"summary", "card", "full"}:
        return emit_json_with_code(
            {
                "kind": "command_output_read_error",
                "schema_version": "command_output_read_v0",
                "status": "unsupported_band",
                "supported_bands": ["summary", "card", "full"],
                "band": band_choice,
            },
            2,
        )
    text = target.read_text(encoding="utf-8")
    payload_bytes = len(text.encode("utf-8"))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return emit_json_with_code(
            {
                "kind": "command_output_read_error",
                "schema_version": "command_output_read_v0",
                "status": "invalid_json",
                "path": rel_path,
                "error": f"{type(exc).__name__}: {exc}",
            },
            2,
        )
    rel = target.relative_to(repo_root).as_posix()
    base_envelope: dict[str, Any] = {
        "kind": "command_output_read",
        "schema_version": "command_output_read_v0",
        "band": band_choice,
        "source_path": rel,
        "source_bytes": payload_bytes,
    }
    if isinstance(payload, Mapping):
        base_envelope["payload_kind"] = payload.get("kind")
        base_envelope["payload_schema_version"] = payload.get("schema_version")
    if band_choice == "summary":
        envelope = dict(base_envelope)
        if isinstance(payload, Mapping):
            summary_block = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else None
            envelope["payload_summary"] = dict(summary_block) if summary_block is not None else None
            envelope["top_keys"] = sorted(str(k) for k in payload.keys())[:24]
        else:
            envelope["payload_summary"] = None
            envelope["top_keys"] = None
        return emit_json(envelope)
    if band_choice == "card":
        envelope = dict(base_envelope)
        if isinstance(payload, Mapping):
            keys = list(payload.keys())[:8]
            envelope["payload"] = {str(k): payload[k] for k in keys}
            envelope["truncated_keys"] = [str(k) for k in list(payload.keys())[8:]]
        else:
            envelope["payload"] = payload
            envelope["truncated_keys"] = []
        return emit_json(envelope)
    envelope = dict(base_envelope)
    envelope["payload"] = payload
    return emit_json(envelope)


class _NavigationMetabolismTimeout(BaseException):
    """Raised when the navigation-metabolism command exceeds its budget."""


def _navigation_metabolism_timeout_ms(profile: str) -> int:
    raw = os.environ.get(NAVIGATION_METABOLISM_TIMEOUT_ENV)
    if raw is not None:
        try:
            return max(0, int(float(raw)))
        except ValueError:
            return NAVIGATION_METABOLISM_QUICK_TIMEOUT_MS if profile == "quick" else 0
    if profile == "quick":
        return NAVIGATION_METABOLISM_QUICK_TIMEOUT_MS
    return 0


def _navigation_metabolism_timeout_packet(
    *,
    query: str | None,
    context_budget: int,
    metabolism_profile: str,
    timeout_ms: int,
    elapsed_ms: int,
) -> dict[str, Any]:
    budget = int(context_budget or 0)
    task_query = str(query or "navigation metabolism timeout").strip() or "navigation metabolism timeout"
    full_profile_command = (
        "./repo-python kernel.py --navigation-metabolism "
        f"{shlex.quote(task_query)} --metabolism-profile full --context-budget {budget}"
    )
    budget_manifest_query = "navigation_metabolism timeout breaker budget_manifest"
    budget_manifest_command = f"./repo-python kernel.py --kind-atlas {shlex.quote(budget_manifest_query)}"
    return {
        "kind": "navigation_metabolism_timeout_packet",
        "schema_version": "navigation_metabolism_timeout_packet_v0",
        "error": "navigation_metabolism_timeout",
        "failure_kind": "navigation_metabolism_timeout",
        "query": query,
        "metabolism_profile": metabolism_profile,
        "context_budget": budget,
        "elapsed_ms": elapsed_ms,
        "timeout_ms": timeout_ms,
        "surface": f"navigation_metabolism.{metabolism_profile}",
        "work_item_ref": NAVIGATION_METABOLISM_TIMEOUT_WORK_ITEM_ID,
        "task_ledger_binding": {
            "work_item_id": NAVIGATION_METABOLISM_TIMEOUT_WORK_ITEM_ID,
            "card_command": (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                f"{NAVIGATION_METABOLISM_TIMEOUT_WORK_ITEM_ID}"
            ),
            "mutation_rule": "append Task Ledger events; never edit projection views",
        },
        "owner_surfaces": [
            "system/lib/kernel/commands/navigate.py",
            "system/lib/navigation_metabolism_ledger.py",
            "codex/standards/std_agent_entry_surface.json",
            "state/task_ledger/events.jsonl",
        ],
        "validation_contract": {
            "purpose": "prove quick navigation-metabolism degrades into an action-bearing JSON packet before agents stall",
            "acceptance_command": (
                "AIW_NAVIGATION_METABOLISM_TIMEOUT_MS=1 ./repo-python kernel.py "
                "--navigation-metabolism \"timeout budget\" --metabolism-profile quick --context-budget 12000"
            ),
            "expected_payload": {
                "kind": "navigation_metabolism_timeout_packet",
                "failure_kind": "navigation_metabolism_timeout",
                "task_ledger_binding.work_item_id": NAVIGATION_METABOLISM_TIMEOUT_WORK_ITEM_ID,
            },
        },
        "degrade_behavior": "emit_timeout_packet",
        "next_drilldown_contract": "commands_are_task_bound_and_shell_parseable",
        "next_drilldowns": [
            (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                f"{NAVIGATION_METABOLISM_TIMEOUT_WORK_ITEM_ID}"
            ),
            full_profile_command,
            budget_manifest_command,
        ],
    }


def cmd_navigation_metabolism(
    query: str | None = None,
    *,
    context_budget: int = 12000,
    metabolism_profile: str = "quick",
) -> int:
    """Emit the unified navigation/compression ratchet ledger.

    The command-surface default is `quick` to keep concurrent agents off the
    expensive full ledger. Callers that explicitly want the rich audit shape
    must pass `metabolism_profile="full"`. The library builder
    `build_navigation_metabolism_ledger` keeps its own legacy default for
    direct internal callers.
    """
    profile = str(metabolism_profile or "quick").strip().lower() or "quick"
    timeout_ms = _navigation_metabolism_timeout_ms(profile)
    started = perf_counter()
    previous_handler: Any = None
    timeout_armed = timeout_ms > 0 and threading.current_thread() is threading.main_thread()

    from system.lib.navigation_metabolism_ledger import (
        build_navigation_metabolism_ledger,
        compact_quick_navigation_metabolism_packet_for_cli,
    )
    from system.lib.command_output_sidecar import maybe_route_to_sidecar

    def _raise_timeout(_signum: int, _frame: Any) -> None:
        raise _NavigationMetabolismTimeout()

    try:
        if timeout_armed:
            previous_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, _raise_timeout)
            signal.setitimer(signal.ITIMER_REAL, timeout_ms / 1000.0)
        payload = build_navigation_metabolism_ledger(
            state.REPO_ROOT,
            query=query,
            context_budget=context_budget,
            metabolism_profile=profile,
        )
        receipt = maybe_route_to_sidecar(
            payload,
            surface=f"navigation_metabolism.{profile}",
            repo_root=state.REPO_ROOT,
        )
        if receipt is not None:
            return emit_json(receipt)
        if profile == "quick":
            payload = compact_quick_navigation_metabolism_packet_for_cli(
                payload,
                context_budget=context_budget,
            )
        return emit_json(payload)
    except _NavigationMetabolismTimeout:
        payload = _navigation_metabolism_timeout_packet(
            query=query,
            context_budget=context_budget,
            metabolism_profile=profile,
            timeout_ms=timeout_ms,
            elapsed_ms=int((perf_counter() - started) * 1000),
        )
        return emit_json_with_code(payload, 2)
    finally:
        if timeout_armed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)


def cmd_coverage_enforcement_matrix(
    query: str | None = None,
    *,
    context_budget: int = 12000,
) -> int:
    """Emit per-kind coverage-first enforcement status and process pressure."""
    from system.lib.navigation_coverage_matrix import build_coverage_enforcement_matrix

    payload = build_coverage_enforcement_matrix(
        state.REPO_ROOT,
        query=query,
        context_budget=context_budget,
    )
    return emit_json(payload)


def cmd_organisation_control_plane(
    *,
    context_budget: int = 12000,
    next_slice: int = 5,
    band: str = "full",
) -> int:
    """Emit lane-level organisation state and ranked next actions."""
    from system.lib.organisation_control_plane import (
        build_organisation_control_plane,
        build_organisation_control_plane_card,
    )

    payload = build_organisation_control_plane(
        state.REPO_ROOT,
        next_slice=next_slice,
    )
    payload["context_budget"] = context_budget
    if band in {"card", "compact"}:
        return emit_json(build_organisation_control_plane_card(payload))
    if band not in {"full", "flag"}:
        return emit_json(
            {
                "kind": "organisation_control_plane_band_unavailable",
                "requested_band": band,
                "supported_bands": ["full", "card", "compact"],
                "drilldown_command": "./repo-python kernel.py --organisation-control-plane --band card --context-budget 12000",
            }
        )
    return emit_json(payload)


def cmd_entrypoint_health() -> int:
    """Emit the compact entrypoint budget and first-contact health scanner."""
    from system.lib.entrypoint_health import build_entrypoint_health

    return emit_json(build_entrypoint_health(state.REPO_ROOT))


def cmd_navigation_fitness(
    query_or_suite: str | None = None,
    *,
    context_budget: int = 12000,
    fitness_mode: str = "library",
) -> int:
    """Emit cold-task navigation sufficiency and latency fitness metrics."""
    from system.lib.navigation_fitness import build_navigation_fitness

    payload = build_navigation_fitness(
        state.REPO_ROOT,
        query_or_suite=query_or_suite,
        context_budget=context_budget,
        fitness_mode=fitness_mode,
    )
    return emit_json(payload)


def cmd_dynamic_paper_lattice(
    slug: str | None = None,
    *,
    band: str = "card",
    scope: str | None = None,
    facet: str | None = None,
    edge_neighborhood: int = 1,
    context_budget: int = 12000,
) -> int:
    """Emit a live source-derived dynamic paper lattice exemplar."""
    from system.lib.dynamic_paper_lattice import DEFAULT_SLUG, build_dynamic_paper_lattice

    payload = build_dynamic_paper_lattice(
        state.REPO_ROOT,
        slug=slug or DEFAULT_SLUG,
        band=band,
        scope=scope,
        facet=facet,
        edge_neighborhood=edge_neighborhood,
        context_budget=context_budget,
    )
    return emit_json_with_code(payload, 2 if payload.get("error") else 0)


def _fact_sources() -> dict[str, list[str]]:
    return {
        "live": ["codex/doctrine/facts/fact_registry.json", "codex/standards/std_derived_fact.json"],
        "derived": [
            str(FACT_LEDGER_PATH.relative_to(state.REPO_ROOT)),
            str(FACT_AUDIT_PATH.relative_to(state.REPO_ROOT)),
            str(FACT_NAVIGATION_CACHE_PATH.relative_to(state.REPO_ROOT)),
        ],
    }


def _fact_cluster_rows(navigation_cache: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index_name in (
        "tag_index",
        "facet_index",
        "value_index",
        "subject_kind_index",
        "fact_family_index",
        "mechanism_ref_index",
    ):
        for row in navigation_cache.get(index_name) or []:
            if not isinstance(row, Mapping):
                continue
            rows.append({"index": index_name, **dict(row)})
    return rows


def _fact_navigation_boundary(*, band: str) -> dict[str, Any]:
    command = f"./repo-python kernel.py --facts --band {band or 'flag'}"
    return {
        "surface_role": ATLAS_PROJECTION,
        "first_contact_allowed": False,
        "control_replacement": ENTRY_REPLACEMENT,
        "navigation_boundary": {
            "not_keyword_search": True,
            "artifact_kind_first": True,
            "generated_artifact_projection": True,
            "cluster_first_for_high_cardinality": True,
            "surface_role": ATLAS_PROJECTION,
            "first_contact_allowed": False,
            "control_replacement": ENTRY_REPLACEMENT,
            "allowed_after": "entry_packet_selected_kind_or_explicit_operator_browse",
            "not_control_entry": True,
        },
        "surface_contract": atlas_projection_contract(
            surface_id="facts:derived_facts",
            command=command,
        ),
    }


def cmd_facts(
    query: str | None = None,
    *,
    tag: str | None = None,
    facet: str | None = None,
    value: str | None = None,
    filters: Sequence[str] | None = None,
    band: str = "flag",
    ambiguous_tag: str | None = None,
) -> int:
    """Emit derived facts through the generated state-axis artifact."""
    if ambiguous_tag:
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.facts",
                "query": {"command": "facts", "request": query},
                "error": "--tag is owned by apply/inject_tag, not the facts command.",
                "suggested_command": f"./repo-python kernel.py --facts --facts-tag {ambiguous_tag}",
                "warnings": [
                    {
                        "rule": "facts_tag_parser_ambiguous",
                        "message": "Use --facts-tag or --facts-filter tag:<tag> so state-axis filtering is parsed by the facts command.",
                    }
                ],
            },
            2,
        )
    payload = build_fact_hologram(repo_root=state.REPO_ROOT)
    ledger = payload["ledger"]
    navigation_cache = payload["navigation_cache"]
    band_choice = str(band or "flag").strip().lower()
    matched_rows = filter_facts(
        ledger=ledger,
        query=query,
        tag=tag,
        facet=facet,
        value=value,
        filters=filters,
        limit=None,
    )
    rows = matched_rows[:40]
    cluster_rows = _fact_cluster_rows(navigation_cache)
    emit_rows = cluster_rows if band_choice == "cluster_flag" else rows
    omitted_fact_count = max(0, len(matched_rows) - len(rows))
    omission_receipt = (
        {
            "reason": "result_limit",
            "matched_fact_count": len(matched_rows),
            "emitted_fact_count": len(rows),
            "omitted_fact_count": omitted_fact_count,
            "limit": 40,
            "message": "Fact rows are truncated for first-contact output; use narrower tag/facet/filter drilldowns for the omitted rows.",
        }
        if omitted_fact_count
        else None
    )
    sources = _fact_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.facts",
            "schema_version": "kernel_facts_navigation_v0",
            **_fact_navigation_boundary(band=band_choice),
            "query": {
                "command": "facts",
                "request": query,
                "tag": tag,
                "facet": facet,
                "value": value,
                "filters": list(filters or []),
                "band": band_choice,
            },
            "summary": {
                "fact_count": len(rows),
                "matched_fact_count": len(matched_rows),
                "emitted_fact_count": len(rows),
                "emitted_row_count": len(emit_rows),
                "omitted_fact_count": omitted_fact_count,
                "total_fact_count": int((ledger.get("summary") or {}).get("fact_count") or 0),
                "error_count": int((ledger.get("summary") or {}).get("error_count") or 0),
                "artifact_role": navigation_cache.get("artifact_role"),
                "cluster_row_count": len(cluster_rows),
            },
            "sources": sources,
            "payload": {
                "ledger_summary": dict(ledger.get("summary") or {}),
                "navigation_summary": dict(navigation_cache.get("summary") or {}),
                "state_axis_indexes": {
                    "tag_index": navigation_cache.get("tag_index") or [],
                    "facet_index": navigation_cache.get("facet_index") or [],
                    "value_index": navigation_cache.get("value_index") or [],
                    "subject_kind_index": navigation_cache.get("subject_kind_index") or [],
                    "fact_family_index": navigation_cache.get("fact_family_index") or [],
                    "mechanism_ref_index": navigation_cache.get("mechanism_ref_index") or [],
                }
                if band_choice == "cluster_flag"
                else {},
                "facts": emit_rows,
                "omission_receipt": omission_receipt,
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --fact <fact_id>",
                    "reason": "Open one derived fact with provider details.",
                },
                {
                    "command": "python3 kernel.py --facts --band cluster_flag",
                    "reason": "Open the compressed state-axis artifact indexes.",
                },
                {
                    "command": "python3 kernel.py --fact-audit",
                    "reason": "Inspect provider errors and paper-module fact-audit status.",
                },
            ],
            "warnings": []
            if band_choice in {"flag", "card", "cluster_flag", ""}
            else [{"rule": "facts_band_unrecognized", "message": f"Facts band {band_choice!r} uses flag rows."}],
        }
    )


def cmd_fact(fact_id: str) -> int:
    """Emit one derived fact by id."""
    payload = build_fact_hologram(repo_root=state.REPO_ROOT)
    ledger = payload["ledger"]
    facts = fact_by_id(ledger)
    raw = str(fact_id or "").strip()
    if raw not in facts:
        matches = search_facts(raw, ledger=ledger, limit=12)
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.fact",
                "query": {"command": "fact", "request": raw},
                "error": f"Unknown fact id: {raw}",
                "alternatives": matches,
            },
            1,
        )
    sources = _fact_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.fact",
            "query": {"command": "fact", "request": raw},
            "summary": {"fact_id": raw, "status": facts[raw].get("status")},
            "sources": sources,
            "payload": {
                "fact": facts[raw],
                "ledger_summary": dict(ledger.get("summary") or {}),
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": f"python3 kernel.py --facts {shlex.quote(raw.rsplit('.', 1)[0])}",
                    "reason": "Browse nearby facts by namespace.",
                }
            ],
            "warnings": [],
        }
    )


def cmd_fact_audit() -> int:
    """Emit provider audit plus paper-module assertion summary."""
    payload = build_fact_hologram(repo_root=state.REPO_ROOT)
    navigator = KernelNavigation(state.REPO_ROOT)
    report = navigator.paper_module_validation_report
    fact_summary = dict(((report.get("summary") or {}).get("fact_audit") or {}))
    modules_with_findings = [
        {
            "slug": item.get("slug"),
            "file": item.get("file"),
            "fact_audit": item.get("fact_audit"),
            "findings": [
                dict(finding)
                for finding in (item.get("findings") or [])
                if isinstance(finding, Mapping)
                and (
                    str(finding.get("rule") or "").startswith("fact")
                    or str(finding.get("rule") or "") == "unbound_numeric_claim"
                )
            ],
        }
        for item in (report.get("modules") or [])
        if isinstance(item, Mapping)
        and (
            ((item.get("fact_audit") or {}).get("summary") or {}).get("finding_count")
            or any(
                isinstance(finding, Mapping)
                and str(finding.get("rule") or "") == "unbound_numeric_claim"
                for finding in (item.get("findings") or [])
            )
        )
    ]
    sources = _fact_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.fact_audit",
            "query": {"command": "fact-audit"},
            "summary": {
                "provider_error_count": int(((payload["audit"].get("summary") or {}).get("provider_error_count")) or 0),
                "paper_module_fact_finding_count": int(fact_summary.get("finding_count") or 0),
                "modules_with_fact_findings": len(modules_with_findings),
            },
            "sources": sources,
            "payload": {
                "provider_audit": payload["audit"],
                "paper_module_fact_audit": fact_summary,
                "modules": modules_with_findings[:50],
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --paper-module-facts <slug>",
                    "reason": "Inspect fact assertions and warnings for one paper module.",
                }
            ],
            "warnings": [],
        }
    )


def cmd_paper_module_facts(slug: str) -> int:
    """Emit fact assertions and fact findings for one paper module."""
    raw = str(slug or "").strip()
    navigator = KernelNavigation(state.REPO_ROOT)
    report = navigator.paper_module_validation_report
    rows = [
        dict(item)
        for item in (report.get("modules") or [])
        if isinstance(item, Mapping) and str(item.get("slug") or "") == raw
    ]
    if not rows:
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.paper_module_facts",
                "query": {"command": "paper-module-facts", "request": raw},
                "error": f"Unknown paper module slug: {raw}",
            },
            1,
        )
    row = rows[0]
    sources = _fact_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.paper_module_facts",
            "query": {"command": "paper-module-facts", "request": raw},
            "summary": {
                "slug": raw,
                "assertion_count": int((((row.get("fact_audit") or {}).get("summary") or {}).get("assertion_count")) or 0),
                "finding_count": int((((row.get("fact_audit") or {}).get("summary") or {}).get("finding_count")) or 0),
            },
            "sources": {
                "live": [str(row.get("file") or ""), *sources["live"]],
                "derived": sources["derived"],
            },
            "payload": {
                "module": {
                    "slug": raw,
                    "file": row.get("file"),
                    "status": row.get("status"),
                    "recommended_action": row.get("recommended_action"),
                },
                "fact_audit": row.get("fact_audit"),
                "fact_findings": [
                    dict(finding)
                    for finding in (row.get("findings") or [])
                    if isinstance(finding, Mapping)
                    and (
                        str(finding.get("rule") or "").startswith("fact")
                        or str(finding.get("rule") or "") == "unbound_numeric_claim"
                    )
                ],
            },
            "next": [
                {
                    "command": f"python3 kernel.py --paper-module {shlex.quote(raw)}",
                    "reason": "Open the full paper-module lookup packet.",
                }
            ],
            "warnings": [],
        }
    )


def _agent_entrypoint_sources() -> dict[str, list[str]]:
    return {
        "live": [
            "codex/standards/std_agent_entrypoint_audit.json",
            str(AGENT_ENTRYPOINT_AXIS_REGISTRY_PATH.relative_to(state.REPO_ROOT)),
            str(AGENT_ENTRYPOINT_REGISTRY_PATH.relative_to(state.REPO_ROOT)),
            "codex/doctrine/agent_bootstrap.json",
            "codex/doctrine/paper_modules/_index.json",
        ],
        "derived": [
            str(AGENT_ENTRYPOINT_AUDIT_PATH.relative_to(state.REPO_ROOT)),
            str(AGENT_ENTRYPOINT_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
            str(AGENT_ENTRYPOINT_PER_ENTRYPOINT_PATH.relative_to(state.REPO_ROOT)),
        ],
    }


def cmd_agent_entrypoints() -> int:
    """[ACTION]
    - Teleology: List every authored agent entrypoint surface (CLAUDE.md / CODEX.md / AGENTS.md) with its per-axis comprehension coverage tiles.
    - Mechanism: Build the entrypoint audit in memory and emit the compact per-entrypoint summary plus recommended next commands.
    - Guarantee: Returns 0 after emitting the JSON navigation packet.
    - Fails: Never fails on a present registry; missing registries are returned as empty entrypoint arrays.
    - When-needed: Open at cold start or after editing CLAUDE.md / CODEX.md / AGENTS.md to see whether every required comprehension axis is still reachable.
    - Escalates-to: tools/meta/factory/build_agent_entrypoint_audit.py; codex/doctrine/agent_entrypoints/axis_registry.json
    - Navigation-group: kernel_lib
    """
    payload = build_agent_entrypoint_audit(repo_root=state.REPO_ROOT)
    audit = payload["audit"]
    rollup = summarize_entrypoints(audit)
    sources = _agent_entrypoint_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.agent_entrypoints",
            "query": {"command": "agent-entrypoints"},
            "summary": {
                "entrypoint_count": int((audit.get("summary") or {}).get("entrypoint_count") or 0),
                "axis_count": int((audit.get("summary") or {}).get("axis_count") or 0),
                "error_count": int((audit.get("summary") or {}).get("error_count") or 0),
                "warning_count": int((audit.get("summary") or {}).get("warning_count") or 0),
                "recommended_action": (audit.get("summary") or {}).get("recommended_action"),
            },
            "sources": sources,
            "payload": {
                "entrypoints": rollup["entrypoints"],
                "axes": [{"id": axis.get("id"), "title": axis.get("title"), "severity_if_missing": axis.get("severity_if_missing")} for axis in audit.get("axes") or []],
                "finding_count": int((audit.get("summary") or {}).get("finding_count") or 0),
                "repair_plan": dict(audit.get("repair_plan") or {}),
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --agent-entrypoint-audit",
                    "reason": "Open the full audit with every finding and recommended fix.",
                },
                {
                    "command": "python3 kernel.py --agent-entrypoint claude",
                    "reason": "Inspect one entrypoint's axis matrix and uncovered axes.",
                },
                {
                    "command": "./repo-python tools/meta/factory/build_agent_entrypoint_audit.py --check",
                    "reason": "Refresh and CI-gate the audit; exits non-zero on error-severity findings.",
                },
            ],
            "warnings": [],
        }
    )


def cmd_agent_entrypoint_audit() -> int:
    """[ACTION]
    - Teleology: Emit the full agent-entrypoint comprehension audit record (findings + axis matrix + dotfile inventory).
    - Mechanism: Build the audit in memory and return the full payload with rule-aggregated finding counts.
    - Guarantee: Returns 0 after emitting the JSON packet; the CI builder variant exits non-zero on error-severity findings.
    - Fails: Never; a broken registry returns an empty audit rather than raising.
    - When-needed: Open before landing changes to CLAUDE.md / CODEX.md / AGENTS.md or the authored axis registry to see whether the change closed or opened a drift.
    - Escalates-to: system/lib/agent_entrypoint_audit.py; tools/meta/factory/build_agent_entrypoint_audit.py
    - Navigation-group: kernel_lib
    """
    payload = build_agent_entrypoint_audit(repo_root=state.REPO_ROOT)
    audit = payload["audit"]
    sources = _agent_entrypoint_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.agent_entrypoint_audit",
            "query": {"command": "agent-entrypoint-audit"},
            "summary": dict(audit.get("summary") or {}),
            "sources": sources,
            "payload": {
                "findings": list(audit.get("findings") or []),
                "repair_plan": dict(audit.get("repair_plan") or {}),
                "entrypoints": [
                    {
                        "id": record.get("id"),
                        "role": record.get("role"),
                        "actor_id": record.get("actor_id"),
                        "status": record.get("status"),
                        "covered_axis_count": record.get("covered_axis_count"),
                        "required_axis_count": record.get("required_axis_count"),
                        "uncovered_axes": list(record.get("uncovered_axes") or []),
                    }
                    for record in audit.get("entrypoints") or []
                    if isinstance(record, Mapping)
                ],
                "dotfile_tree_inventory": dict(audit.get("dotfile_tree_inventory") or {}),
                "entry_surface_budget_ledger": dict(audit.get("entry_surface_budget_ledger") or {}),
                "entry_surface_topology": dict(audit.get("entry_surface_topology") or {}),
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --agent-entrypoint <claude|codex|shared>",
                    "reason": "Open one entrypoint's full axis matrix and uncovered axes.",
                },
                {
                    "command": "python3 kernel.py --paper-module host_agent_dotfile_surfaces",
                    "reason": "Open the host-agent dotfile plane paper module if dotfile findings surfaced.",
                },
            ],
            "warnings": [],
        }
    )


def cmd_agent_entrypoint(request: str) -> int:
    """[ACTION]
    - Teleology: Return one authored entrypoint surface (claude / codex / shared, or a full id) with its full axis-coverage matrix.
    - Mechanism: Build the audit in memory, resolve the requested entrypoint id / actor alias, and emit its per-axis probe results.
    - Guarantee: Returns 0 after emitting the JSON packet when the entrypoint resolves.
    - Fails: Returns 1 with an alternatives list when the request matches no registered entrypoint.
    - When-needed: Open after landing a CLAUDE.md / CODEX.md / AGENTS.md edit to see exactly which resolution method covered each axis.
    - Escalates-to: system/lib/agent_entrypoint_audit.py; codex/doctrine/agent_entrypoints/entrypoint_registry.json
    - Navigation-group: kernel_lib
    """
    raw = str(request or "").strip()
    payload = build_agent_entrypoint_audit(repo_root=state.REPO_ROOT)
    audit = payload["audit"]
    record = select_entrypoint(audit, raw)
    sources = _agent_entrypoint_sources()
    if record is None:
        alternatives = [
            {"id": str(item.get("id") or ""), "actor_id": item.get("actor_id"), "role": item.get("role")}
            for item in audit.get("entrypoints") or []
            if isinstance(item, Mapping)
        ]
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.agent_entrypoint",
                "query": {"command": "agent-entrypoint", "request": raw},
                "error": f"Unknown entrypoint: {raw!r}",
                "alternatives": alternatives,
            },
            1,
        )
    findings = [
        dict(finding)
        for finding in audit.get("findings") or []
        if isinstance(finding, Mapping)
        and (
            not finding.get("entrypoint_id")
            or str(finding.get("entrypoint_id") or "") == str(record.get("id") or "")
        )
    ]
    return emit_json(
        {
            "kind": "kernel.navigate.agent_entrypoint",
            "query": {"command": "agent-entrypoint", "request": raw},
            "summary": {
                "id": record.get("id"),
                "role": record.get("role"),
                "actor_id": record.get("actor_id"),
                "status": record.get("status"),
                "covered_axis_count": record.get("covered_axis_count"),
                "required_axis_count": record.get("required_axis_count"),
            },
            "sources": sources,
            "payload": {
                "entrypoint": record,
                "findings": findings,
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --agent-entrypoint-audit",
                    "reason": "Open the full audit with every entrypoint's findings.",
                },
                {
                    "command": "./repo-python tools/meta/factory/build_agent_entrypoint_audit.py --check",
                    "reason": "Refresh and CI-gate the audit; exits non-zero on error-severity findings.",
                },
            ],
            "warnings": [],
        }
    )


def _process_trace_sources() -> dict[str, list[str]]:
    return {
        "live": [
            "codex/standards/std_agent_execution_trace.json",
            str(PROCESS_TRACE_RULES_PATH.relative_to(state.REPO_ROOT)),
        ],
        "derived": [
            str(PROCESS_LEDGER_PATH.relative_to(state.REPO_ROOT)),
            str(PROCESS_AUDIT_PATH.relative_to(state.REPO_ROOT)),
            str(PROCESS_NAVIGATION_CACHE_PATH.relative_to(state.REPO_ROOT)),
            str(PROCESS_PATTERNS_PATH.relative_to(state.REPO_ROOT)),
            str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
        ],
    }


def _process_build(*, since_ts: str | None = None, session_limit: int | None = None) -> dict[str, Any]:
    return build_agent_execution_trace(
        repo_root=state.REPO_ROOT,
        since_ts=since_ts,
        session_limit=session_limit,
    )


PROCESS_BOTTLENECK_STALE_AFTER_SECONDS = 600.0


def _process_bottleneck_decision_authority(cache_status: Mapping[str, Any]) -> dict[str, Any]:
    mode = str(cache_status.get("mode") or "")
    status = str(cache_status.get("status") or "")
    window_status = str(cache_status.get("window_status") or "")
    age_seconds = cache_status.get("age_seconds", cache_status.get("age_s"))
    stale_after = cache_status.get("stale_after_seconds", cache_status.get("stale_after_s"))
    try:
        age_value = float(age_seconds)
    except (TypeError, ValueError):
        age_value = None
    try:
        stale_after_value = float(stale_after)
    except (TypeError, ValueError):
        stale_after_value = None
    is_stale = status == "stale" or (
        age_value is not None
        and stale_after_value is not None
        and age_value > stale_after_value
    )
    if is_stale:
        return {
            "status": "advisory_only_stale_read_model",
            "use_for": [
                "cheap triage",
                "historical command-family shape",
                "candidate ranking seed",
            ],
            "not_for": [
                "selecting a new source patch target",
                "declaring a recently fixed command lane still hot",
            ],
            "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
            "reason": "cached process bottleneck rows can outlive command-lane repairs; force a live rebuild before patch selection",
        }
    if window_status == "compatible_superset_window":
        return {
            "status": "advisory_only_superset_window",
            "use_for": [
                "cheap triage",
                "candidate ranking seed",
                "avoiding a live rebuild when a narrower requested window is covered by a wider cache",
            ],
            "not_for": [
                "exact narrower-window ranking",
                "declaring a recently fixed command lane still hot",
            ],
            "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
            "reason": "requested window is narrower than the cached read model; force a live rebuild for exact rankings",
        }
    if mode == "live_in_memory" and status in {"fresh", "forced"}:
        return {
            "status": "authoritative_live_process_window",
            "use_for": ["patch target selection", "current bottleneck ranking"],
            "not_for": [],
            "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
        }
    return {
        "status": "current_cached_triage",
        "use_for": ["cheap triage", "candidate ranking seed"],
        "not_for": ["final authority when a stale/fixed lane would change the decision"],
        "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
    }


def _process_summary_cache_status(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    generated_at = str((summary or {}).get("generated_at") or "")
    generated_dt = parse_iso_datetime(generated_at)
    age_seconds = None
    if generated_dt is not None:
        if generated_dt.tzinfo is None:
            generated_dt = generated_dt.replace(tzinfo=timezone.utc)
        age_seconds = round((datetime.now(timezone.utc) - generated_dt).total_seconds(), 3)
    status = "hit"
    if age_seconds is not None and age_seconds > PROCESS_BOTTLENECK_STALE_AFTER_SECONDS:
        status = "stale"
    return {
        "mode": "cached_summary",
        "status": status,
        "cache_path": str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
        "generated_at": generated_at or None,
        "age_seconds": age_seconds,
        "stale_after_seconds": PROCESS_BOTTLENECK_STALE_AFTER_SECONDS,
        "refresh_command": "./repo-python tools/meta/factory/build_agent_execution_trace.py",
        "force_live_command": "./repo-python kernel.py --process-bottlenecks --force",
        "staleness_policy": (
            "default route is cached snapshot for cheap triage; narrower non-force --limit windows may reuse "
            "a wider cached read model as advisory, while --force gives exact live rankings"
        ),
    }


def _process_bottleneck_speedboard_path(repo_root: Path | None = None) -> Path:
    return (repo_root or state.REPO_ROOT) / "state/performance/latency_speedboard.json"


PROCESS_BOTTLENECK_DEFAULT_SESSION_LIMIT = 20
PROCESS_BOTTLENECK_STATUS_ROW_LIMIT = 6
PROCESS_BOTTLENECK_OUTPUT_ROW_LIMIT = 5
PROCESS_BOTTLENECK_CONTEXT_ROW_LIMIT = 4
PROCESS_BOTTLENECK_DEFAULT_EXAMPLE_LIMIT = 2
PROCESS_BOTTLENECK_FORCE_EXAMPLE_LIMIT = 1
PROCESS_BOTTLENECK_FORCE_TARGET_BYTES = 30_000


def _process_bottleneck_cached_window_status(
    *,
    cached_since: Any,
    cached_limit_raw: Any,
    since_ts: str | None,
    session_limit: int | None,
) -> dict[str, Any]:
    cached_limit = _int_value(cached_limit_raw)
    requested_limit = _int_value(session_limit)
    cached_window = {
        "since": cached_since,
        "session_limit": cached_limit_raw,
    }
    requested_window = {
        "since": since_ts,
        "session_limit": session_limit,
    }
    base = {
        "cached_window": cached_window,
        "requested_window": requested_window,
    }
    if cached_since != since_ts:
        return {
            **base,
            "status": "window_mismatch",
            "reason": "cached and requested --after windows differ",
        }
    if cached_limit == requested_limit:
        return {
            **base,
            "status": "exact_window",
            "served_window": dict(cached_window),
        }
    if cached_limit > requested_limit > 0:
        return {
            **base,
            "status": "compatible_superset_window",
            "served_window": dict(cached_window),
            "reason": (
                "requested non-force session window is narrower than the cached read model; "
                "serving the wider cache avoids live trace rebuild for triage"
            ),
        }
    return {
        **base,
        "status": "window_mismatch",
        "reason": "requested session window is wider or incompatible with cached read model",
    }


def _load_process_bottleneck_speedboard_fallback(
    *,
    since_ts: str | None = None,
    session_limit: int | None = None,
    repo_root: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    repo_root = repo_root or state.REPO_ROOT
    speedboard_path = _process_bottleneck_speedboard_path(repo_root)
    board = safe_load_json(speedboard_path)
    rel_speedboard = str(speedboard_path.relative_to(repo_root))
    if not isinstance(board, Mapping):
        return None, {
            "mode": "speedboard_embedded_summary",
            "status": "missing_or_invalid",
            "speedboard_path": rel_speedboard,
        }
    source = board.get("remaining_bottlenecks_source")
    rows = board.get("remaining_bottlenecks")
    if not isinstance(source, Mapping) or not isinstance(rows, list):
        return None, {
            "mode": "speedboard_embedded_summary",
            "status": "missing_remaining_bottleneck_read_model",
            "speedboard_path": rel_speedboard,
        }
    cached_since = source.get("live_process_since")
    cached_limit_raw = source.get("live_process_limit")
    cached_limit = _int_value(source.get("live_process_limit"))
    requested_limit = _int_value(session_limit)
    default_window_match = (
        since_ts is None
        and cached_since is None
        and cached_limit_raw is None
        and requested_limit == PROCESS_BOTTLENECK_DEFAULT_SESSION_LIMIT
    )
    if not default_window_match and (cached_since != since_ts or cached_limit != requested_limit):
        return None, {
            "mode": "speedboard_embedded_summary",
            "status": "window_mismatch",
            "speedboard_path": rel_speedboard,
            "cached_window": {
                "since": cached_since,
                "session_limit": cached_limit_raw,
            },
            "requested_window": {
                "since": since_ts,
                "session_limit": session_limit,
            },
        }
    effective_session_limit = (
        session_limit if default_window_match else cached_limit_raw
    )
    top_bottlenecks: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        first_example = row.get("first_example")
        example_spans = row.get("example_spans")
        if not isinstance(example_spans, list):
            example_spans = [dict(first_example)] if isinstance(first_example, Mapping) else []
        top_bottlenecks.append(
            _drop_none(
                {
                    "action_kind": row.get("action_kind"),
                    "span_count": row.get("span_count") or row.get("count"),
                    "count": row.get("count"),
                    "p50_ms": row.get("p50_ms"),
                    "p95_ms": row.get("p95_ms"),
                    "max_ms": row.get("max_ms"),
                    "total_duration_ms": row.get("total_duration_ms"),
                    "slow_count": row.get("slow_count"),
                    "threshold_ms": row.get("threshold_ms"),
                    "example_spans": example_spans,
                    "repair_hints": list(row.get("repair_hints") or []),
                }
            )
        )
    if not top_bottlenecks:
        return None, {
            "mode": "speedboard_embedded_summary",
            "status": "empty_remaining_bottleneck_read_model",
            "speedboard_path": rel_speedboard,
            "remaining_bottlenecks_source": dict(source),
        }
    source_status = str(source.get("status") or "unknown")
    summary = {
        "kind": "agent_execution_trace_summary",
        "generated_at": source.get("generated_at"),
        "summary": {
            "session_count": _int_value(source.get("session_count")),
            "window": {
                "since": cached_since,
                "session_limit": effective_session_limit,
            },
            "source": "latency_speedboard.remaining_bottlenecks",
            "source_status": source_status,
            "row_count": len(top_bottlenecks),
        },
        "top_bottlenecks": top_bottlenecks,
    }
    return summary, {
        "mode": "speedboard_embedded_summary",
        "status": source_status,
        "speedboard_path": rel_speedboard,
        "fallback_source": "latency_speedboard.remaining_bottlenecks",
        "summary_path": source.get("summary_path"),
        "generated_at": source.get("generated_at"),
        "age_seconds": source.get("age_s"),
        "stale_after_seconds": source.get("stale_after_s"),
        "refresh_command": source.get("refresh_command")
        or "./repo-python tools/meta/observability/latency_speedboard.py show --live-process",
        "force_live_command": "./repo-python kernel.py --process-bottlenecks --force",
        "authority_posture": "cached_speedboard_read_model_not_authoritative_process_trace",
        "mutation_status": "read_only_no_speedboard_write",
        "staleness_policy": "default route may use speedboard-embedded bottleneck shape for cheap triage when the standalone process summary is absent; use --force for authoritative live rebuild",
    }


def _load_process_bottleneck_summary_cache(
    *,
    since_ts: str | None = None,
    session_limit: int | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    summary = safe_load_json(PROCESS_SUMMARY_PATH)
    if not isinstance(summary, Mapping):
        return None, {
            "mode": "cached_summary",
            "status": "missing_or_invalid",
            "cache_path": str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
        }
    payload_summary = summary.get("summary")
    if not isinstance(payload_summary, Mapping) or not isinstance(summary.get("top_bottlenecks"), list):
        return None, {
            "mode": "cached_summary",
            "status": "invalid_shape",
            "cache_path": str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
        }
    window = payload_summary.get("window")
    if not isinstance(window, Mapping):
        return None, {
            "mode": "cached_summary",
            "status": "window_missing",
            "cache_path": str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
        }
    cached_since = window.get("since")
    window_status = _process_bottleneck_cached_window_status(
        cached_since=cached_since,
        cached_limit_raw=window.get("session_limit"),
        since_ts=since_ts,
        session_limit=session_limit,
    )
    if window_status["status"] == "window_mismatch":
        return None, {
            "mode": "cached_summary",
            "status": "window_mismatch",
            "cache_path": str(PROCESS_SUMMARY_PATH.relative_to(state.REPO_ROOT)),
            "cached_window": window_status["cached_window"],
            "requested_window": window_status["requested_window"],
            "reason": window_status.get("reason"),
        }
    cache_status = _process_summary_cache_status(summary)
    if window_status["status"] == "compatible_superset_window":
        cache_status = {
            **cache_status,
            "window_status": window_status["status"],
            "cached_window": window_status["cached_window"],
            "requested_window": window_status["requested_window"],
            "served_window": window_status["served_window"],
            "authority_posture": "cached_superset_window_advisory_not_exact_requested_window",
            "reason": window_status.get("reason"),
        }
    return dict(summary), cache_status


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _drop_none(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items() if value is not None}


def _top_mapping_items(value: Mapping[str, Any] | None, *, limit: int = 10) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    items = sorted(value.items(), key=lambda item: (-_int_value(item[1]), str(item[0])))
    return {str(key): count for key, count in items[:limit]}


def _compact_command_rows(rows: Sequence[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _drop_none(
                {
                "command": row.get("command") or row.get("normalized_command"),
                "count": row.get("count"),
                "total_duration_ms": row.get("total_duration_ms"),
                "p95_ms": row.get("p95_ms"),
                "exit_code": row.get("exit_code"),
                }
            )
        )
    return compact


def _compact_bottleneck_preview(rows: Sequence[Any], *, limit: int = 6) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        target_paths = row.get("target_paths")
        if target_paths is None and row.get("target_path"):
            target_paths = [row.get("target_path")]
        compact.append(
            _drop_none(
                {
                "action_kind": row.get("action_kind"),
                "duration_ms": row.get("duration_ms"),
                "outcome": row.get("outcome"),
                "normalized_command": _agent_wake_truncate(row.get("normalized_command"), 220)
                if row.get("normalized_command")
                else None,
                "target_paths": list(target_paths or [])[:2],
                "command_shape_tags": list(row.get("command_shape_tags") or [])[:6],
                }
            )
        )
    return compact


def _compact_pattern_rows(rows: Sequence[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _drop_none(
                {
                "pattern_id": row.get("pattern_id"),
                "severity": row.get("severity"),
                "instances": row.get("instances"),
                "session_hits": len(row.get("session_id_hits") or []),
                }
            )
        )
    return compact


def _compact_audit_findings(rows: Sequence[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _drop_none(
                {
                "rule": row.get("rule"),
                "severity": row.get("severity"),
                "subject": row.get("subject"),
                "message": row.get("message"),
                }
            )
        )
    return compact


def _compact_process_bottlenecks(value: Mapping[str, Any] | None, *, limit: int = 8) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    items = sorted(
        value.items(),
        key=lambda item: (-_int_value((item[1] or {}).get("p95_ms") if isinstance(item[1], Mapping) else 0), str(item[0])),
    )
    compact: dict[str, Any] = {}
    for key, row in items[:limit]:
        if not isinstance(row, Mapping):
            continue
        row_out: dict[str, Any] = {
            "span_count": row.get("span_count"),
            "count": row.get("count"),
            "p50_ms": row.get("p50_ms"),
            "p95_ms": row.get("p95_ms"),
            "max_ms": row.get("max_ms"),
            "total_duration_ms": row.get("total_duration_ms"),
            "slow_count": row.get("slow_count"),
            "threshold_ms": row.get("threshold_ms"),
            "example_spans": _compact_bottleneck_preview(list(row.get("example_spans") or []), limit=3),
            "repair_hints": list(row.get("repair_hints") or [])[:3],
        }
        by_flag = list(row.get("by_kernel_flag") or [])
        if by_flag:
            row_out["by_kernel_flag"] = by_flag[:5]
        compact[str(key)] = row_out
    return compact


def _compact_process_bottleneck_rows(
    rows: Sequence[Any],
    *,
    limit: int = 8,
    example_limit: int = PROCESS_BOTTLENECK_DEFAULT_EXAMPLE_LIMIT,
) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in list(rows)[:limit]:
        if not isinstance(row, Mapping):
            continue
        hints = row.get("repair_hints")
        by_flag = list(row.get("by_kernel_flag") or [])
        compact.append(
            _drop_none(
                {
                    "action_kind": row.get("action_kind"),
                    "count": row.get("count") or row.get("span_count"),
                    "p50_ms": row.get("p50_ms"),
                    "p95_ms": row.get("p95_ms"),
                    "max_ms": row.get("max_ms"),
                    "total_duration_ms": row.get("total_duration_ms"),
                    "slow_count": row.get("slow_count"),
                    "threshold_ms": row.get("threshold_ms"),
                    "total_output_bytes": row.get("total_output_bytes"),
                    "max_output_bytes": row.get("max_output_bytes"),
                    "p95_output_bytes": row.get("p95_output_bytes"),
                    "example_spans": _compact_bottleneck_preview(
                        list(row.get("example_spans") or []),
                        limit=example_limit,
                    ),
                    "repair_hints": list(hints or [])[:2],
                    "by_kernel_flag": (by_flag[:5] if by_flag else None),
                }
            )
        )
    return compact


def _compact_process_output_producers(rows: Sequence[Any], *, limit: int = 5) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in list(rows)[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _drop_none(
                {
                    "action_kind": row.get("action_kind"),
                    "span_count": row.get("span_count") or row.get("count"),
                    "total_output_bytes": row.get("total_output_bytes"),
                    "max_output_bytes": row.get("max_output_bytes"),
                    "p95_output_bytes": row.get("p95_output_bytes"),
                }
            )
        )
    return compact


def _compact_context_yield_example(row: Mapping[str, Any]) -> dict[str, Any]:
    target_paths = row.get("target_paths")
    return _drop_none(
        {
            "session_id": row.get("session_id"),
            "span_id": row.get("span_id"),
            "action_kind": row.get("action_kind"),
            "output_byte_count": row.get("output_byte_count"),
            "governance_status": row.get("governance_status"),
            "command_shape_tags": list(row.get("command_shape_tags") or [])[:6],
            "target_paths": list(target_paths or [])[:2],
            "normalized_command_preview": _agent_wake_truncate(
                row.get("normalized_command_preview") or row.get("normalized_command"),
                180,
            )
            if row.get("normalized_command_preview") or row.get("normalized_command")
            else None,
        }
    )


def _compact_context_yield_steering(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    clusters = value.get("command_shape_clusters")
    compact_clusters = None
    if isinstance(clusters, Mapping):
        compact_clusters = _drop_none(
            {
                "status": clusters.get("status"),
                "tag_counts": _top_mapping_items(clusters.get("tag_counts"), limit=6),
                "action_kind_counts": _top_mapping_items(clusters.get("action_kind_counts"), limit=6),
            }
        )
    return _drop_none(
        {
            "replacement_route": value.get("replacement_route"),
            "applies_to_status": value.get("applies_to_status"),
            "applies_to_count": value.get("applies_to_count"),
            "accepted_case_guard": _agent_wake_truncate(value.get("accepted_case_guard"), 220)
            if value.get("accepted_case_guard")
            else None,
            "command_shape_clusters": compact_clusters,
        }
    )


def _compact_context_yield_attribution(
    value: Mapping[str, Any] | None,
    *,
    row_limit: int = 8,
    example_limit: int = 1,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    rows = [row for row in list(value.get("rows") or []) if isinstance(row, Mapping)]
    actionable_statuses = {
        "ungoverned",
        "governed_route_available_but_not_used",
        "needs_owner_patch",
    }
    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        active_bytes = int(row.get("active_bytes") or 0)
        span_count = int(row.get("span_count") or 0)
        status_counts = dict(row.get("governance_status_counts") or {})
        status_bytes = dict(row.get("governance_status_bytes") or {})
        actionable_span_count = row.get("actionable_span_count")
        if actionable_span_count is None:
            actionable_span_count = sum(int(status_counts.get(status) or 0) for status in actionable_statuses)
        actionable_active_bytes = row.get("actionable_active_bytes")
        if actionable_active_bytes is None:
            if status_bytes:
                actionable_active_bytes = sum(int(status_bytes.get(status) or 0) for status in actionable_statuses)
            elif int(actionable_span_count or 0) and span_count:
                actionable_active_bytes = round(active_bytes * (int(actionable_span_count or 0) / span_count))
            elif int(actionable_span_count or 0):
                actionable_active_bytes = active_bytes
            else:
                actionable_active_bytes = 0
        non_actionable_active_bytes = row.get("non_actionable_active_bytes")
        if non_actionable_active_bytes is None:
            non_actionable_active_bytes = max(active_bytes - int(actionable_active_bytes or 0), 0)
        enriched["_compact_active_bytes"] = active_bytes
        enriched["_compact_span_count"] = span_count
        enriched["_compact_actionable_active_bytes"] = int(actionable_active_bytes or 0)
        enriched["_compact_non_actionable_active_bytes"] = int(non_actionable_active_bytes or 0)
        enriched["_compact_actionable_span_count"] = int(actionable_span_count or 0)
        enriched_rows.append(enriched)
    enriched_rows.sort(
        key=lambda row: (
            int(row.get("_compact_actionable_active_bytes") or 0),
            int(row.get("_compact_active_bytes") or 0),
            int(row.get("_compact_span_count") or 0),
        ),
        reverse=True,
    )
    compact_rows: list[dict[str, Any]] = []
    for row in enriched_rows[:row_limit]:
        examples = [example for example in list(row.get("examples") or []) if isinstance(example, Mapping)]
        compact_examples = [
            _compact_context_yield_example(example)
            for example in examples[:example_limit]
        ]
        active_bytes = int(row.get("_compact_active_bytes") or 0)
        span_count = int(row.get("_compact_span_count") or 0)
        actionable_active_bytes = int(row.get("_compact_actionable_active_bytes") or 0)
        non_actionable_active_bytes = int(row.get("_compact_non_actionable_active_bytes") or 0)
        actionable_span_count = int(row.get("_compact_actionable_span_count") or 0)
        owner_coverage = row.get("owner_coverage")
        if isinstance(owner_coverage, Mapping):
            owner_coverage = _drop_none(
                {
                    "route_available": owner_coverage.get("route_available"),
                    "route_used": owner_coverage.get("route_used"),
                    "route_gap": owner_coverage.get("route_gap"),
                }
            )
        else:
            owner_coverage = None
        compact_rows.append(
            _drop_none(
                {
                    "motif": row.get("motif"),
                    "active_bytes": active_bytes,
                    "actionable_active_bytes": actionable_active_bytes,
                    "non_actionable_active_bytes": non_actionable_active_bytes,
                    "span_count": span_count,
                    "actionable_span_count": actionable_span_count,
                    "session_count": row.get("session_count"),
                    "repetition_count": row.get("repetition_count"),
                    "next_wave_score": row.get("next_wave_score"),
                    "owner_surface": row.get("owner_surface"),
                    "existing_route": row.get("existing_route"),
                    "candidate_patch": row.get("candidate_patch"),
                    "safety_gate": row.get("safety_gate"),
                    "governance_status_counts": dict(row.get("governance_status_counts") or {}),
                    "owner_coverage": owner_coverage,
                    "steering": _compact_context_yield_steering(row.get("steering")),
                    "examples": compact_examples if compact_examples else None,
                    "example_count": len(examples),
                    "examples_omitted": max(0, len(examples) - len(compact_examples)),
                }
            )
        )
    top_actionable_row = next(
        (row for row in enriched_rows if int(row.get("_compact_actionable_active_bytes") or 0) > 0),
        None,
    )
    top_total_row = enriched_rows[0] if enriched_rows else None
    summary = dict(value.get("summary") or {})
    summary.update(
        {
            "top_motif": top_actionable_row.get("motif") if top_actionable_row else None,
            "top_active_bytes": int(top_actionable_row.get("_compact_active_bytes") or 0)
            if top_actionable_row
            else 0,
            "top_actionable_bytes": int(top_actionable_row.get("_compact_actionable_active_bytes") or 0)
            if top_actionable_row
            else 0,
            "top_total_motif": top_total_row.get("motif") if top_total_row else None,
            "top_total_active_bytes": int(top_total_row.get("_compact_active_bytes") or 0)
            if top_total_row
            else 0,
            "rank_basis": "actionable_active_bytes_then_total_active_bytes_then_span_count",
        }
    )
    return {
        "kind": value.get("kind"),
        "schema_version": value.get("schema_version"),
        "generated_at": value.get("generated_at"),
        "output_profile": "compact_context_yield_status",
        "summary": summary,
        "rows": compact_rows,
        "rows_returned": len(compact_rows),
        "rows_available": len(enriched_rows),
        "rows_omitted": max(0, len(enriched_rows) - len(compact_rows)),
        "privacy_boundary": value.get("privacy_boundary"),
        "full_payload_routes": [
            "./repo-python kernel.py --process-audit",
        ],
        "omission_receipt": {
            "omitted": [
                "raw command output bodies",
                "raw context-yield example bodies",
                "context-yield rows beyond the compact owner-status limit",
            ],
            "drilldown": "./repo-python kernel.py --process-audit",
        },
    }


def _compact_process_session(session: Mapping[str, Any]) -> dict[str, Any]:
    compliance = session.get("route_compliance") if isinstance(session.get("route_compliance"), Mapping) else {}
    return {
        "session_id": session.get("session_id"),
        "agent": session.get("agent"),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "duration_ms": session.get("duration_ms"),
        "span_count": session.get("span_count"),
        "turn_count": session.get("turn_count"),
        "action_kind_counts": _top_mapping_items(session.get("action_kind_counts"), limit=10),
        "kernel_flag_counts": _top_mapping_items(session.get("kernel_flag_counts"), limit=12),
        "top_normalized_commands": _compact_command_rows(list(session.get("top_normalized_commands") or []), limit=8),
        "target_path_hot_list": list(session.get("target_path_hot_list") or [])[:8],
        "route_compliance": {
            "score": compliance.get("score"),
            "ladder_position": compliance.get("ladder_position"),
            "deviation_count": compliance.get("deviation_count"),
            "ladder_rungs_hit": list(compliance.get("ladder_rungs_hit") or [])[:12],
        },
        "anti_patterns": _compact_pattern_rows(list(session.get("anti_patterns") or []), limit=6),
        "bottleneck_preview": _compact_bottleneck_preview(list(session.get("bottleneck_preview") or []), limit=6),
        "summary_thought_trace": dict(session.get("summary_thought_trace") or {}),
    }


def _compact_process_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    summary = dict(audit.get("summary") or {})
    return {
        "summary": summary,
        "slow_action_shapes": _compact_audit_findings(
            [
                row
                for row in list(audit.get("findings") or [])
                if isinstance(row, Mapping) and row.get("rule") == "slow_action_shape"
            ],
            limit=8,
        ),
        "pattern_counts": dict(summary.get("pattern_counts") or {}),
        "top_patterns": _compact_pattern_rows(list(audit.get("patterns") or []), limit=8),
        "top_bottlenecks": _compact_process_bottlenecks(audit.get("bottlenecks"), limit=8),
        "parse_failure_count": len(audit.get("parse_failures") or []),
    }


def _process_summary_identity_scope(raw: str, session: Mapping[str, Any]) -> dict[str, Any]:
    request = str(raw or "latest").strip().lower()
    selected_session_id = session.get("session_id")
    selected_agent = session.get("agent")
    if request in {"", "latest"}:
        selection_basis = "latest_ended_session"
        current_session_claim = "not_claimed"
        concurrency_posture = "not_self_identity_safe"
        warning_reason = (
            "`latest` selects the newest completed process trace; concurrent sibling "
            "seeds can make that a different agent's session."
        )
    elif request in {"codex", "codex:latest", "claude", "claude:latest"}:
        selection_basis = "agent_latest_ended_session"
        current_session_claim = "not_claimed"
        concurrency_posture = "agent_scoped_not_self_identity_safe"
        warning_reason = (
            f"`{raw}` selects the newest completed trace for that agent family, "
            "not necessarily this live wake."
        )
    else:
        selection_basis = "explicit_session_id"
        current_session_claim = "explicit_user_or_callsite_selection"
        concurrency_posture = "explicit_trace_selection"
        warning_reason = ""
    warnings = []
    if warning_reason:
        warnings.append({
            "warning_id": "process_summary_latest_alias_not_self_identity",
            "reason": warning_reason,
            "safe_action": "Treat the selected session as evidence only after checking selected_session_id/selected_agent, or rerun with an explicit session id.",
        })
    return {
        "schema_version": "process_summary_identity_scope_v1",
        "request_alias": raw or "latest",
        "selection_basis": selection_basis,
        "selected_session_id": selected_session_id,
        "selected_agent": selected_agent,
        "current_session_claim": current_session_claim,
        "concurrency_posture": concurrency_posture,
        "safe_trace_command": f"./repo-python kernel.py --process-trace {selected_session_id}",
        "warnings": warnings,
    }


def cmd_process_summary(request: str | None = None) -> int:
    """[ACTION]
    - Teleology: Inspect the latest process trace and cross-session audit as one compact packet before opening verbose payloads.
    - Mechanism: Build the process trace once, resolve the requested session alias, and emit bounded summaries of the selected session plus audit.
    - Guarantee: Returns 0 after emitting the JSON navigation packet when the session resolves.
    - Fails: Returns 1 with alternatives when no session matches the request.
    - When-needed: Open first during autonomous self-inspection when context pressure or repeated trace/audit reads are the bottleneck.
    - Escalates-to: cmd_process_trace; cmd_process_audit; system/lib/agent_execution_trace.py
    - Navigation-group: kernel_lib
    """
    payload = _process_build()
    ledger = payload["ledger"]
    audit = payload["audit"]
    raw = (request or "latest").strip()
    session = select_session(ledger, raw)
    sources = _process_trace_sources()
    if session is None:
        alt = [
            {"session_id": row.get("session_id"), "agent": row.get("agent"), "ended_at": row.get("ended_at")}
            for row in (ledger.get("sessions") or [])[:10]
            if isinstance(row, Mapping)
        ]
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.process_summary",
                "query": {"command": "process-summary", "request": raw},
                "error": f"No session matches {raw!r}. Run `./repo-python tools/meta/factory/build_agent_execution_trace.py` to refresh the ledger.",
                "alternatives": alt,
            },
            1,
        )
    audit_summary = dict((audit.get("summary") or {}))
    identity_scope = _process_summary_identity_scope(raw, session)
    return emit_json(
        {
            "kind": "kernel.navigate.process_summary",
            "schema_version": "process_summary_v1",
            "query": {"command": "process-summary", "request": raw},
            "identity_scope": identity_scope,
            "summary": {
                "session_id": session.get("session_id"),
                "agent": session.get("agent"),
                "span_count": session.get("span_count"),
                "duration_ms": session.get("duration_ms"),
                "route_compliance_score": (session.get("route_compliance") or {}).get("score"),
                "ladder_position": (session.get("route_compliance") or {}).get("ladder_position"),
                "audit_warning_count": audit_summary.get("warning_count"),
                "audit_error_count": audit_summary.get("error_count"),
                "audit_finding_count": audit_summary.get("finding_count"),
            },
            "sources": sources,
            "payload": {
                "session": _compact_process_session(session),
                "audit_summary": _compact_process_audit(audit),
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": f"python3 kernel.py --process-trace {session.get('session_id')}",
                    "reason": "Drill into the full selected session only after the compact packet identifies the need.",
                },
                {
                    "command": "python3 kernel.py --process-audit",
                    "reason": "Open the full cross-session audit only when findings need raw rows.",
                },
                {
                    "command": "python3 kernel.py --process-bottlenecks",
                    "reason": "Browse the bounded bottleneck packet if latency shapes are the chosen axis.",
                },
                {
                    "command": "python3 kernel.py --process-patterns",
                    "reason": "Browse recurring anti-patterns when process repetition is the chosen axis.",
                },
            ],
            "warnings": list(identity_scope.get("warnings") or []),
        }
    )


def cmd_process_trace(
    request: str | None = None,
    trace_level: str = "tape",
    *,
    include_tape: bool = False,
    tape_max_chars: int = 10000,
    include_raw_sidecar: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Open one session's observed-action process trace.
    - Mechanism: Build the trace ledger in memory; resolve the requested session alias (`latest` | `claude:latest` | `codex:latest` | session_id) and emit the tape/sidecar packet.
    - Guarantee: Returns 0 after emitting the navigation packet when the session resolves.
    - Fails: Returns 1 with alternatives when no session matches the request.
    - When-needed: Open when the operator asks 'what did this session actually do / where did it spend its time / did it climb the ladder'.
    - Escalates-to: system/lib/agent_execution_trace.py; tools/meta/factory/build_agent_execution_trace.py
    - Navigation-group: kernel_lib
    """
    code, payload = build_process_trace_route_packet(
        repo_root=state.REPO_ROOT,
        request=request,
        trace_level=trace_level,
        include_tape=include_tape,
        tape_max_chars=tape_max_chars,
        include_raw_sidecar=include_raw_sidecar,
    )
    return emit_json_with_code(payload, code)


def cmd_process_audit(*, since_ts: str | None = None, session_limit: int | None = None) -> int:
    """[ACTION]
    - Teleology: Emit the full execution-trace audit record (findings + aggregate bottlenecks + pattern counts).
    - Mechanism: Build the ledger + audit in memory and emit the full audit JSON. Use since_ts/session_limit for follow-up observation windows.
    - Guarantee: Returns 0 after emitting the packet.
    - When-needed: Open before optimizing agent throughput; every warning is a concrete optimization target.
    - Escalates-to: system/lib/agent_execution_trace.py; codex/standards/std_agent_execution_trace.json
    - Navigation-group: kernel_lib
    """
    payload = _process_build(since_ts=since_ts, session_limit=session_limit)
    audit = payload["audit"]
    sources = _process_trace_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.process_audit",
            "query": {
                "command": "process-audit",
                "after": since_ts,
                "limit": session_limit,
            },
            "summary": dict(audit.get("summary") or {}),
            "sources": sources,
            "payload": {
                "findings": list(audit.get("findings") or []),
                "bottlenecks": dict(audit.get("bottlenecks") or {}),
                "patterns": list(audit.get("patterns") or []),
                "context_yield_attribution": dict(audit.get("context_yield_attribution") or {}),
                "mode_control": dict(audit.get("mode_control") or {}),
                "parse_failures": list(audit.get("parse_failures") or []),
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --process-bottlenecks",
                    "reason": "Browse the top N slowest action shapes and longest spans.",
                },
                {
                    "command": "python3 kernel.py --process-patterns",
                    "reason": "Browse recurring process patterns and session hit lists.",
                },
            ],
            "warnings": [],
        }
    )


def _build_process_bottlenecks_packet(
    *,
    since_ts: str | None = None,
    session_limit: int | None = None,
    force_live: bool = False,
) -> dict[str, Any]:
    cache_status: dict[str, Any] = {
        "mode": "live_in_memory",
        "status": "forced" if force_live else "cache_unavailable",
    }
    effective_session_limit = (
        session_limit if session_limit is not None else PROCESS_BOTTLENECK_DEFAULT_SESSION_LIMIT
    )
    summary = None
    if not force_live:
        summary, cache_status = _load_process_bottleneck_summary_cache(
            since_ts=since_ts,
            session_limit=effective_session_limit,
        )
        if summary is None:
            canonical_cache_status = dict(cache_status)
            summary, cache_status = _load_process_bottleneck_speedboard_fallback(
                since_ts=since_ts,
                session_limit=effective_session_limit,
            )
            if summary is not None:
                cache_status["canonical_process_summary"] = canonical_cache_status
            else:
                canonical_cache_status["speedboard_fallback"] = cache_status
                cache_status = canonical_cache_status
    if summary is None:
        payload = _process_build(since_ts=since_ts, session_limit=effective_session_limit)
        summary = payload["summary"]
        cache_status = {
            "mode": "live_in_memory",
            "status": "fresh",
            "cache_fallback": cache_status,
        }
    sources = _process_trace_sources()
    decision_authority = _process_bottleneck_decision_authority(cache_status)
    cache_status = dict(cache_status)
    cache_status["decision_authority"] = decision_authority
    warnings = []
    if decision_authority.get("status") == "advisory_only_stale_read_model":
        warnings.append(
            {
                "warning_id": "stale_process_bottleneck_read_model_advisory_only",
                "reason": decision_authority.get("reason"),
                "safe_action": "./repo-python kernel.py --process-bottlenecks --force",
            }
        )
    top_bottlenecks_all = list(summary.get("top_bottlenecks") or [])
    top_output_producers_all = list(summary.get("top_output_producers") or [])
    compact_default = not force_live
    if compact_default:
        top_bottlenecks = _compact_process_bottleneck_rows(
            top_bottlenecks_all,
            limit=PROCESS_BOTTLENECK_STATUS_ROW_LIMIT,
            example_limit=PROCESS_BOTTLENECK_DEFAULT_EXAMPLE_LIMIT,
        )
        top_output_producers = _compact_process_output_producers(
            top_output_producers_all,
            limit=PROCESS_BOTTLENECK_OUTPUT_ROW_LIMIT,
        )
        output_economy = {
            "profile": "compact_owner_status",
            "reason": (
                "Default process-bottlenecks is a first-triage owner status route; "
                "full per-span evidence remains behind force-live and process-audit drilldowns."
            ),
            "top_bottlenecks_emitted": len(top_bottlenecks),
            "top_bottlenecks_available": len(top_bottlenecks_all),
            "top_output_producers_emitted": len(top_output_producers),
            "top_output_producers_available": len(top_output_producers_all),
            "row_limits": {
                "top_bottlenecks": PROCESS_BOTTLENECK_STATUS_ROW_LIMIT,
                "top_output_producers": PROCESS_BOTTLENECK_OUTPUT_ROW_LIMIT,
                "context_yield_rows": PROCESS_BOTTLENECK_CONTEXT_ROW_LIMIT,
                "examples_per_bottleneck": PROCESS_BOTTLENECK_DEFAULT_EXAMPLE_LIMIT,
            },
            "omitted_fields": [
                "full example span normalized_command bodies",
                "example spans beyond two per action kind",
                "top bottleneck rows beyond first six",
                "top output-producer rows beyond first five",
                "full context-yield attribution examples and drilldown rows",
            ],
            "full_payload_routes": [
                "./repo-python kernel.py --process-bottlenecks --force",
                "./repo-python kernel.py --process-audit",
            ],
        }
    else:
        top_bottlenecks = _compact_process_bottleneck_rows(
            top_bottlenecks_all,
            limit=PROCESS_BOTTLENECK_STATUS_ROW_LIMIT,
            example_limit=PROCESS_BOTTLENECK_FORCE_EXAMPLE_LIMIT,
        )
        top_output_producers = _compact_process_output_producers(
            top_output_producers_all,
            limit=PROCESS_BOTTLENECK_OUTPUT_ROW_LIMIT,
        )
        output_economy = {
            "profile": "force_live_authoritative_rankings_compact_context_yield",
            "reason": (
                "--force requested a live in-memory rebuild for ranking rows; "
                "the emitted owner packet keeps the same row budget as the cheap status route "
                "because raw examples belong behind process-audit."
            ),
            "target_bytes": PROCESS_BOTTLENECK_FORCE_TARGET_BYTES,
            "top_bottlenecks_emitted": len(top_bottlenecks),
            "top_bottlenecks_available": len(top_bottlenecks_all),
            "top_output_producers_emitted": len(top_output_producers),
            "top_output_producers_available": len(top_output_producers_all),
            "row_limits": {
                "top_bottlenecks": PROCESS_BOTTLENECK_STATUS_ROW_LIMIT,
                "top_output_producers": PROCESS_BOTTLENECK_OUTPUT_ROW_LIMIT,
                "context_yield_rows": PROCESS_BOTTLENECK_CONTEXT_ROW_LIMIT,
                "examples_per_bottleneck": PROCESS_BOTTLENECK_FORCE_EXAMPLE_LIMIT,
            },
            "omitted_fields": [
                "raw top-bottleneck example rows",
                "raw top output-producer rows",
                "full context-yield attribution examples and drilldown rows",
            ],
            "full_payload_routes": [
                "./repo-python kernel.py --process-audit",
            ],
        }
    context_yield_attribution = _compact_context_yield_attribution(
        summary.get("context_yield_attribution"),
        row_limit=PROCESS_BOTTLENECK_CONTEXT_ROW_LIMIT,
        example_limit=0,
    )
    return {
        "kind": "kernel.navigate.process_bottlenecks",
        "schema_version": "process_bottlenecks_v1",
        "query": {
            "command": "process-bottlenecks",
            "after": since_ts,
            "limit": effective_session_limit,
            "force_live": force_live,
        },
        "summary": {
            "action_kind_count": len(summary.get("top_bottlenecks") or []),
            "output_producer_count": len(summary.get("top_output_producers") or []),
            "session_count": int((summary.get("summary") or {}).get("session_count") or 0),
        },
        "source_freshness": cache_status,
        "decision_authority": decision_authority,
        "sources": sources,
        "payload": {
            "top_bottlenecks": top_bottlenecks,
            "top_output_producers": top_output_producers,
            "context_yield_attribution": context_yield_attribution,
            "summary": dict(summary.get("summary") or {}),
            "next_reads": sources["derived"],
            "output_economy": output_economy,
        },
        "next": [
            {
                "command": "python3 kernel.py --process-audit",
                "reason": "Open the full audit with findings and per-session preview.",
            },
            {
                "command": "python3 kernel.py --process-bottlenecks --force",
                "reason": "Force a live in-memory rebuild when the cached summary is not fresh enough for the decision.",
            },
        ],
        "warnings": warnings,
    }


def cmd_process_bottlenecks(
    *,
    since_ts: str | None = None,
    session_limit: int | None = None,
    force_live: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Emit the top-N slowest action shapes with percentiles and a longest-span preview.
    - Mechanism: Read the generated summary snapshot for the default window; narrower non-force session windows may reuse a wider cached read model as advisory, and --force gives exact live rankings.
    - Guarantee: Returns 0 after emitting the packet.
    - When-needed: Open when the task is to identify which action shapes dominate agent latency.
    - Escalates-to: system/lib/agent_execution_trace.py; tools/meta/agent_telemetry/extract.py (command-shape context)
    - Navigation-group: kernel_lib
    """
    return emit_json(
        _build_process_bottlenecks_packet(
            since_ts=since_ts,
            session_limit=session_limit,
            force_live=force_live,
        )
    )


def cmd_process_patterns(*, since_ts: str | None = None, session_limit: int | None = None) -> int:
    """[ACTION]
    - Teleology: Emit recurring process patterns (anti-patterns and positive patterns) with per-session hit lists.
    - Mechanism: Build the trace in memory; return the patterns hologram artifact. Use since_ts/session_limit for follow-up observation windows.
    - Guarantee: Returns 0 after emitting the packet.
    - When-needed: Open when the task is to correlate process patterns with outcomes or to triage which patterns fire most often.
    - Escalates-to: codex/doctrine/process/trace_rules.json; codex/doctrine/skills/kernel/navigation_seed.md
    - Navigation-group: kernel_lib
    """
    payload = _process_build(since_ts=since_ts, session_limit=session_limit)
    patterns = payload["patterns"]
    sources = _process_trace_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.process_patterns",
            "query": {
                "command": "process-patterns",
                "after": since_ts,
                "limit": session_limit,
            },
            "summary": {
                "pattern_count": len(patterns.get("patterns") or []),
            },
            "sources": sources,
            "payload": {
                "patterns": list(patterns.get("patterns") or []),
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --process-trace <session_id>",
                    "reason": "Drill into one session where the pattern fired.",
                }
            ],
            "warnings": [],
        }
    )


def cmd_process_compare() -> int:
    """[ACTION]
    - Teleology: Emit Claude-vs-Codex process divergence: ladder climb rates, grep shares, kernel shares, anti-pattern counts.
    - Mechanism: Build the ledger in memory; partition per agent; compute means and distributions.
    - Guarantee: Returns 0 after emitting the packet.
    - When-needed: Open when the task is 'how do Claude and Codex differ in actual navigation behavior'.
    - Escalates-to: system/lib/agent_execution_trace.py; docs/agent_telemetry.md
    - Navigation-group: kernel_lib
    """
    payload = _process_build()
    ledger = payload["ledger"]
    buckets = compare_agents(ledger)
    sources = _process_trace_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.process_compare",
            "query": {"command": "process-compare"},
            "summary": {
                "claude_sessions": buckets.get("claude_code", {}).get("sessions"),
                "codex_sessions": buckets.get("codex", {}).get("sessions"),
                "claude_avg_route_compliance": buckets.get("claude_code", {}).get("avg_route_compliance"),
                "codex_avg_route_compliance": buckets.get("codex", {}).get("avg_route_compliance"),
            },
            "sources": sources,
            "payload": {
                "agents": buckets,
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --process-patterns",
                    "reason": "Inspect which anti-patterns account for the divergence.",
                }
            ],
            "warnings": [],
        }
    )


def cmd_navigation_mechanism_factory(*, limit: int | None = 200) -> int:
    """[ACTION]
    - Teleology: Emit the read-only Navigation Mechanism Metabolism candidate ledger.
    - Mechanism: Normalize observable process spans into navigation_trace_event_v0 rows, convert route-training emissions into candidate mechanism projection claims, and expose replay/provider receipt skeletons.
    - Guarantee: Does not mutate mechanisms, standards, skills, WorkItems, entrypoints, prompt ledgers, or raw seed.
    - When-needed: Use when trace-derived route behavior should become safely learnable through mechanism facets and replay tests.
    - Escalates-to: system/lib/navigation_mechanism_factory.py; codex/standards/std_mechanism_projection_ledger.json
    - Navigation-group: kernel_lib
    """
    from system.lib.navigation_mechanism_factory import build_navigation_mechanism_projection

    payload = build_navigation_mechanism_projection(state.REPO_ROOT, event_limit=limit)
    return emit_json(
        {
            "kind": "kernel.navigate.navigation_mechanism_factory",
            "query": {"command": "navigation-mechanism-factory", "limit": limit},
            "summary": dict(payload.get("summary") or {}),
            "sources": {
                "live": [
                    "codex/standards/std_agent_execution_trace.json",
                    "codex/standards/std_navigation_trace_event.json",
                    "codex/standards/std_navigation_trace_case.json",
                    "codex/standards/std_navigation_route_replay_result.json",
                    "codex/standards/std_navigation_mechanism_acceptance.json",
                    "codex/standards/std_mechanism_facet_manifest.json",
                    "codex/standards/std_mechanism_projection_ledger.json",
                    "codex/standards/std_provider_navigation_transform_receipt.json",
                    "system/lib/navigation_mechanism_factory.py",
                ],
                "evidence": [
                    "./repo-python kernel.py --process-audit",
                    "./repo-python kernel.py --option-surface navigation_training_emissions --band flag",
                    "./repo-python kernel.py --option-surface navigation_mechanism_candidates --band flag",
                ],
            },
            "payload": payload,
            "next": [
                {
                    "command": "./repo-python kernel.py --option-surface navigation_mechanism_candidates --band flag",
                    "reason": "Browse candidate projection claims by stable claim id.",
                },
                {
                    "command": "./repo-python kernel.py --navigation-fitness smoke --fitness-mode library --context-budget 12000",
                    "reason": "Run route replay/fitness before accepting any mechanism affordance.",
                },
            ],
            "warnings": [],
        }
    )


def cmd_navigation_mechanism_replay(case_ids: Sequence[str] | None = None) -> int:
    """[ACTION]
    - Teleology: Emit machine-readable replay results for Navigation Mechanism Metabolism route-repair cases.
    - Mechanism: Consumes deterministic replay case ids and returns navigation_route_replay_result_v0 rows that can be used as validation evidence, not owner acceptance.
    - Guarantee: Does not mutate mechanisms, standards, skills, WorkItems, entrypoints, prompt ledgers, or raw seed.
    - When-needed: Use before accepting a navigation mechanism projection claim.
    - Escalates-to: system/lib/navigation_mechanism_factory.py; codex/standards/std_navigation_route_replay_result.json
    - Navigation-group: kernel_lib
    """
    from system.lib.navigation_mechanism_factory import build_navigation_route_replay_results

    results = build_navigation_route_replay_results(case_ids=case_ids)
    return emit_json(
        {
            "kind": "kernel.navigate.navigation_mechanism_replay",
            "query": {"command": "navigation-mechanism-replay", "case_ids": list(case_ids or [])},
            "summary": {
                "result_count": len(results),
                "passed_count": sum(1 for row in results if row.get("passed") is True),
                "failed_count": sum(1 for row in results if row.get("passed") is not True),
                "authority_posture": "fitness_probe_not_acceptance",
            },
            "sources": {
                "live": [
                    "codex/standards/std_navigation_route_replay_result.json",
                    "system/lib/navigation_mechanism_factory.py",
                ],
                "evidence": [
                    "./repo-python kernel.py --navigation-mechanism-factory",
                    "./repo-python tools/meta/factory/validate_navigation_mechanism_facets.py --json",
                ],
            },
            "payload": {
                "schema_version": "navigation_route_replay_results_v0",
                "route_replay_results": results,
            },
            "next": [
                {
                    "command": "./repo-python tools/meta/factory/validate_navigation_mechanism_facets.py --json",
                    "reason": "Validate candidate claims, replay results, and provider authority before owner acceptance.",
                }
            ],
            "warnings": [],
        }
    )


def _raw_seed_projection_sources() -> dict[str, list[str]]:
    return {
        "live": [
            "codex/standards/observe_apply/std_raw_seed_projection_coverage.json",
            "obsidian/**/raw_seed.json",
            "obsidian/**/extracted_shards.json",
            "obsidian/**/raw_seed/raw_seed_coverage.json",
            "obsidian/**/raw_seed/raw_seed_coverage_enriched.json",
            "codex/doctrine/paper_modules/*.md",
            "codex/doctrine/facts/fact_registry.json",
            "codex/doctrine/agent_entrypoints/axis_registry.json",
            "codex/doctrine/process/trace_rules.json",
        ],
        "derived": [
            "codex/hologram/raw_seed_projection/ledger.json",
            "codex/hologram/raw_seed_projection/audit.json",
            "codex/hologram/raw_seed_projection/navigation_cache.json",
            "codex/hologram/raw_seed_projection/summary.json",
        ],
    }


def _raw_seed_projection_expected_paths() -> list[str]:
    base_dir = state.REPO_ROOT / _RAW_SEED_PROJECTION_DIR
    return [
        state.rel(base_dir / name)
        for name in ("summary.json", "ledger.json", "audit.json", "navigation_cache.json")
    ]


def _load_raw_seed_projection_generated(
    filenames: Sequence[str],
) -> tuple[dict[str, Any] | None, Path | None, list[str]]:
    base_dir = state.REPO_ROOT / _RAW_SEED_PROJECTION_DIR
    parse_errors: list[str] = []
    for filename in filenames:
        candidate = base_dir / filename
        if not candidate.exists():
            continue
        loaded, error = safe_load_json_with_error(candidate)
        if error:
            parse_errors.append(f"{state.rel(candidate)}: {error}")
            continue
        if not isinstance(loaded, Mapping):
            parse_errors.append(f"{state.rel(candidate)}: expected JSON object")
            continue
        return dict(loaded), candidate, parse_errors
    return None, None, parse_errors


def _raw_seed_projection_degraded_packet(
    *,
    command: str,
    required_files: Sequence[str],
    parse_errors: Sequence[str],
) -> dict[str, Any]:
    base_dir = state.REPO_ROOT / _RAW_SEED_PROJECTION_DIR
    required_paths = [state.rel(base_dir / name) for name in required_files]
    missing_paths = [path for path in required_paths if not (state.REPO_ROOT / path).exists()]
    status = "missing_generated_projection" if missing_paths else "malformed_generated_projection"
    reason = (
        "raw-seed projection generated files are not materialized"
        if missing_paths
        else "raw-seed projection generated files could not be parsed"
    )
    sources = _raw_seed_projection_sources()
    return {
        "kind": f"kernel.navigate.{command.replace('-', '_')}",
        "query": {"command": command},
        "status": status,
        "summary": {
            "status": status,
            "degraded": True,
            "reason": reason,
            "missing_path_count": len(missing_paths),
            "parse_error_count": len(parse_errors),
        },
        "sources": sources,
        "payload": {
            "themes": [],
            "findings": [],
            "highest_value_gap": None,
            "entrypoint_projection_worklist": {},
            "raw_seed_backlog_worklist": {},
            "process_summary_trace_worklist": {},
            "metabolism_reaction_worklist": {},
            "expected_paths": _raw_seed_projection_expected_paths(),
            "required_paths": required_paths,
            "missing_paths": missing_paths,
            "parse_errors": list(parse_errors),
            "refresh_command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
            "check_command": _RAW_SEED_PROJECTION_CHECK_COMMAND,
            "next_reads": sources["derived"],
        },
        "next": [
            {
                "command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
                "reason": "Materialize the generated raw-seed projection summary before route drilldown.",
            },
            {
                "command": _RAW_SEED_PROJECTION_CHECK_COMMAND,
                "reason": "Run the generated-plane check with an explicit timeout budget.",
            },
        ],
        "warnings": [f"{reason}; run {_RAW_SEED_PROJECTION_REFRESH_COMMAND}"],
    }


def _raw_seed_projection_worklists(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "entrypoint_projection_worklist": dict(payload.get("entrypoint_projection_worklist") or {}),
        "raw_seed_backlog_worklist": dict(payload.get("raw_seed_backlog_worklist") or {}),
        "process_summary_trace_worklist": dict(payload.get("process_summary_trace_worklist") or {}),
        "metabolism_reaction_worklist": dict(payload.get("metabolism_reaction_worklist") or {}),
    }


def _compact_raw_seed_projection_theme(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "theme_id": row.get("theme_id"),
        "query": row.get("query"),
        "gap_state": row.get("gap_state"),
        "gap_signals": list(row.get("gap_signals") or []),
        "recommended_next_action": row.get("recommended_next_action"),
        "paragraph_hit_count": len((((row.get("seed_evidence") or {}).get("paragraphs")) or [])),
        "shard_hit_count": len((((row.get("seed_evidence") or {}).get("shards")) or [])),
        "paper_module_slugs": [
            module.get("slug")
            for module in ((((row.get("projection_coverage") or {}).get("paper_modules")) or []))
            if isinstance(module, Mapping)
        ],
    }


def cmd_raw_seed_projection_theme(query: str) -> int:
    """Emit one raw-seed-first projection coverage theme packet."""
    raw = str(query or "").strip()
    if not raw:
        return emit_json_with_code(
            {
                "kind": "kernel.navigate.raw_seed_projection_theme",
                "query": {"command": "raw-seed-projection-theme", "request": raw},
                "error": "--raw-seed-projection-theme requires a non-empty query.",
            },
            2,
        )
    ledger, source_path, parse_errors = _load_raw_seed_projection_generated(("ledger.json",))
    if ledger is None:
        packet = _raw_seed_projection_degraded_packet(
            command="raw-seed-projection-theme",
            required_files=("ledger.json",),
            parse_errors=parse_errors,
        )
        packet["query"]["request"] = raw
        packet["payload"]["theme"] = None
        return emit_json(packet)

    theme = select_theme(raw, ledger) or {}
    sources = _raw_seed_projection_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.raw_seed_projection_theme",
            "status": "materialized" if theme else "theme_not_found",
            "query": {"command": "raw-seed-projection-theme", "request": raw},
            "summary": {
                "theme_id": theme.get("theme_id"),
                "gap_state": theme.get("gap_state"),
                "recommended_next_action": theme.get("recommended_next_action"),
                "paragraph_hit_count": len((((theme.get("seed_evidence") or {}).get("paragraphs")) or [])),
                "shard_hit_count": len((((theme.get("seed_evidence") or {}).get("shards")) or [])),
                "paper_module_hit_count": len((((theme.get("projection_coverage") or {}).get("paper_modules")) or [])),
                "fact_hit_count": len((((theme.get("fact_linkage") or {}).get("facts")) or [])),
            },
            "sources": sources,
            "payload": {
                "theme": theme,
                "source_path": state.rel(source_path) if source_path else None,
                "generated_at": ledger.get("generated_at"),
                "ledger_summary": dict(ledger.get("summary") or {}),
                "next_reads": sources["derived"],
                "refresh_command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
                "check_command": _RAW_SEED_PROJECTION_CHECK_COMMAND,
            },
            "next": [
                {
                    "command": "python3 kernel.py --raw-seed-projection-gap-audit",
                    "reason": "Inspect all weak, missing, or drifting raw-seed projection themes.",
                },
                {
                    "command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
                    "reason": "Refresh the generated raw-seed projection coverage hologram.",
                },
            ],
            "warnings": [] if theme else [f"No materialized raw-seed projection theme matched query: {raw}"],
        }
    )


def cmd_raw_seed_projection_coverage() -> int:
    """Emit compact raw-seed projection coverage summary and top theme rows."""
    payload, source_path, parse_errors = _load_raw_seed_projection_generated(("summary.json", "ledger.json"))
    if payload is None:
        return emit_json(
            _raw_seed_projection_degraded_packet(
                command="raw-seed-projection-coverage",
                required_files=("summary.json", "ledger.json"),
                parse_errors=parse_errors,
            )
        )

    if source_path and source_path.name == "summary.json":
        theme_rows = payload.get("top_themes") if isinstance(payload.get("top_themes"), list) else []
    else:
        theme_rows = payload.get("themes") if isinstance(payload.get("themes"), list) else []
    worklists = _raw_seed_projection_worklists(payload)
    sources = _raw_seed_projection_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.raw_seed_projection_coverage",
            "status": "materialized",
            "query": {"command": "raw-seed-projection-coverage"},
            "summary": dict(payload.get("summary") or {}),
            "sources": sources,
            "payload": {
                "themes": [
                    _compact_raw_seed_projection_theme(row)
                    for row in list(theme_rows or [])[:12]
                    if isinstance(row, Mapping)
                ],
                "top_gaps": list(payload.get("top_gaps") or [])[:10],
                "source_path": state.rel(source_path) if source_path else None,
                "generated_at": payload.get("generated_at"),
                "refresh_command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
                "check_command": _RAW_SEED_PROJECTION_CHECK_COMMAND,
                **worklists,
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --raw-seed-projection-theme <theme>",
                    "reason": "Open one theme as a full bounded packet.",
                },
                {
                    "command": "python3 kernel.py --raw-seed-projection-gap-audit",
                    "reason": "Open repair-oriented gap findings.",
                },
                {
                    "command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
                    "reason": "Refresh the generated raw-seed projection coverage hologram.",
                },
            ],
            "warnings": [],
        }
    )


def cmd_raw_seed_projection_gap_audit() -> int:
    """Emit sorted raw-seed projection coverage gaps."""
    payload, source_path, parse_errors = _load_raw_seed_projection_generated(("audit.json", "summary.json", "ledger.json"))
    if payload is None:
        return emit_json(
            _raw_seed_projection_degraded_packet(
                command="raw-seed-projection-gap-audit",
                required_files=("audit.json", "summary.json", "ledger.json"),
                parse_errors=parse_errors,
            )
        )

    if source_path and source_path.name == "audit.json":
        findings = list(payload.get("findings") or [])
        highest_value_gap = payload.get("highest_value_gap")
    elif source_path and source_path.name == "summary.json":
        findings = list(payload.get("top_gaps") or [])
        highest_value_gap = findings[0] if findings else None
    else:
        theme_rows = payload.get("themes") if isinstance(payload.get("themes"), list) else []
        findings = [
            {
                "theme_id": row.get("theme_id"),
                "gap_state": row.get("gap_state"),
                "recommended_next_action": row.get("recommended_next_action"),
                "gap_signals": list(row.get("gap_signals") or []),
            }
            for row in theme_rows
            if isinstance(row, Mapping) and row.get("gap_state") not in (None, "covered")
        ]
        highest_value_gap = findings[0] if findings else None
    worklists = _raw_seed_projection_worklists(payload)
    sources = _raw_seed_projection_sources()
    return emit_json(
        {
            "kind": "kernel.navigate.raw_seed_projection_gap_audit",
            "status": "materialized",
            "query": {"command": "raw-seed-projection-gap-audit"},
            "summary": dict(payload.get("summary") or {}),
            "sources": sources,
            "payload": {
                "highest_value_gap": highest_value_gap,
                "findings": findings,
                "source_path": state.rel(source_path) if source_path else None,
                "generated_at": payload.get("generated_at"),
                "refresh_command": _RAW_SEED_PROJECTION_REFRESH_COMMAND,
                "check_command": _RAW_SEED_PROJECTION_CHECK_COMMAND,
                **worklists,
                "next_reads": sources["derived"],
            },
            "next": [
                {
                    "command": "python3 kernel.py --raw-seed-projection-theme <theme>",
                    "reason": "Open one gap as a source-to-repair packet.",
                },
                {
                    "command": _RAW_SEED_PROJECTION_CHECK_COMMAND,
                    "reason": "Run the generated-plane check without treating warning-grade gaps as failures.",
                },
            ],
            "warnings": [],
        }
    )


def cmd_doctrine_triple(request: str) -> int:
    """[ACTION]
    - Teleology: Resolve a doctrine triple bundle from raw-seed alchemy review state, doctrine nodes, and governing paper modules.
    - Mechanism: Delegate to `KernelNavigation.build_doctrine_triple` and emit the resulting unified packet.
    - Guarantee: Returns 0 after emitting the doctrine-triple navigation result.
    - Fails: Returns 1 when no alchemy bundle matches the doctrine id or free-text query.
    - When-needed: Open when an operator wants the linked principle/concept/mechanism bundle plus the backing shards and governing paper modules in one surface.
    - Escalates-to: system/lib/kernel_navigation.py; raw_seed/raw_seed_alchemy_review.json
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_doctrine_triple(request)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_system_view(phase_token: str | None = None) -> int:
    """
    [ACTION]
    - Teleology: Emit a multi-surface system view for the active or specified phase.
    - Guarantee: Returns 0 after emitting the system-view navigation result.
    - Fails: Returns 1 when the phase token cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_system_view(phase_token)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_list_docs_route_focus() -> int:
    """
    [ACTION]
    - Teleology: Emit all available docs-route focus presets and the currently active preset.
    - Guarantee: Returns 0 after printing the preset listing as JSON.
    - Fails: None.
    """
    import json

    from system.control.documentation_route_focus import list_presets, load_documentation_route_focus

    doc = load_documentation_route_focus(state.REPO_ROOT)
    payload = {
        "active_preset_id": doc.get("active_preset_id"),
        "set_by": doc.get("set_by"),
        "updated_at": doc.get("updated_at"),
        "presets": list_presets(doc),
    }
    inv = str(doc.get("_invalid_active_preset") or "").strip()
    if inv:
        payload["invalid_active_preset_fallback"] = inv
    print(json.dumps(payload, indent=2))
    return 0


def cmd_set_docs_route_focus(preset_id: str) -> int:
    """[ACTION]
    - Teleology: Change the active docs-route focus preset and refresh orchestration artifacts.
    - Mechanism: Persist the preset via `set_active_preset`, trigger orchestration artifact refresh, and print the resulting preset list.
    - Guarantee: Returns 0 after the preset is applied and the updated focus payload is printed.
    - Fails: Returns 1 when the requested preset id is invalid.
    - When-needed: Open when route ranking needs to be biased toward a documentation, runtime-control, or standards focus preset.
    - Escalates-to: system/control/documentation_route_focus.py; kernel.py
    """
    from system.control.documentation_route_focus import set_active_preset
    from system.control.orchestration import write_orchestration_artifacts

    try:
        set_active_preset(state.REPO_ROOT, preset_id, set_by="kernel_cli")
        write_orchestration_artifacts(repo_root=state.REPO_ROOT)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return cmd_list_docs_route_focus()


def cmd_orient_task(task: str) -> int:
    """[ACTION]
    - Teleology: Turn a vague task description into a bounded kernel-local working set.
    - Mechanism: Delegate to `KernelNavigation.build_orient_task` and emit the resulting orientation payload.
    - Guarantee: Returns 0 after emitting the orient-task packet.
    - Fails: Returns 1 when the navigator cannot resolve the task.
    - When-needed: Open when the problem statement names a topic but not the files, notes, or subsystems you should read first.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_lens.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_orient_task(task)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_context(node_id: str, view: str = "summary") -> int:
    """
    [ACTION]
    - Teleology: Emit the doctrine or codex context card for a named node.
    - Guarantee: Returns 0 after emitting the context navigation result.
    - Fails: Returns 1 when the node id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_context(node_id, view=view)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_trace(node_id: str, direction: str, collapsed: bool = False) -> int:
    """
    [ACTION]
    - Teleology: Emit the upstream or downstream dependency trace for a doctrine or codex node.
    - Guarantee: Returns 0 after emitting the trace navigation result.
    - Fails: Returns 1 when the node id or direction cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_trace(node_id, direction)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if collapsed:
        d = result.to_dict(state.KERNEL_VERSION, full=navigation_output_full(result.kind))
        # Strip verbose paths arrays, keep only summary + edges
        payload = d.get("payload", d)
        if isinstance(payload, dict):
            for direction_key in ("upstream", "downstream"):
                section = payload.get(direction_key)
                if isinstance(section, dict) and "paths" in section:
                    del section["paths"]
        return emit_json(d)
    return emit_navigation(result)


def cmd_doctrine(doc_id: str) -> int:
    """
    [ACTION]
    - Teleology: Emit the full doctrine entry for a named skill, concept, or principle doc.
    - Guarantee: Returns 0 after emitting the doctrine navigation result.
    - Fails: Returns 1 when the doc id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_doctrine(doc_id)
    except ValueError as exc:
        normalized = str(doc_id or "").strip().casefold()
        if normalized == "principles":
            print(
                "ERROR: Doctrine doc not found: principles. "
                "Did you mean `python3 kernel.py --docs-route raw_seed_principles` for the family principles graph, "
                "or `python3 kernel.py --doctrine principles_curation` for the curation skill?",
                file=sys.stderr,
            )
            return 1
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_doctrine_runtime() -> int:
    """
    [ACTION]
    - Teleology: Emit the doctrine runtime spec containing the control-plane, scaling policy, and runtime contract.
    - Guarantee: Returns 0 after emitting the parsed doctrine_runtime.json content.
    - Fails: None — emits an error payload when the file is missing or invalid rather than returning 1.
    """
    path = state.DOCTRINE_RUNTIME_SPEC
    if not path.is_file():
        return emit_json(
            {
                "error": "missing",
                "path": state.rel(path),
                "hint": "Add codex/doctrine/doctrine_runtime.json or sync from doctrine_registry surfaces.",
            }
        )
    payload = safe_load_json(path)
    if not isinstance(payload, dict):
        return emit_json({"error": "invalid_or_empty", "path": state.rel(path)})
    merged = dict(payload)
    merged["_kernel"] = {"repo_relative_path": state.rel(path), "exists": True}
    return emit_json(merged)


def cmd_locate(token: str) -> int:
    """
    [ACTION]
    - Teleology: Locate the canonical file or node for an arbitrary token using the graph navigation layer.
    - Guarantee: Returns 0 after emitting the locate navigation result.
    - Fails: Returns 1 when the token cannot be resolved to any known location.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_locate(token)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    record_navigation_result(
        state.REPO_ROOT,
        event_kind="locate",
        query=token,
        command="kernel.py --locate",
        payload=result.to_dict(state.KERNEL_VERSION, full=True),
    )
    return emit_navigation(result)


def cmd_run_context(run_id: str) -> int:
    """
    [ACTION]
    - Teleology: Emit the runtime context and lineage card for a specific run id.
    - Guarantee: Returns 0 after emitting the run-context navigation result.
    - Fails: Returns 1 when the run id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_run_context(run_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_data_roots() -> int:
    """
    [ACTION]
    - Teleology: Emit grouped data-root summaries for browsing reusable source-data snapshots.
    - Guarantee: Returns 0 after emitting the data-roots navigation result.
    - Fails: None.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    return emit_navigation(navigator.build_data_roots())


def cmd_lens(target: str) -> int:
    """[ACTION]
    - Teleology: Emit a focused holographic lens view for one semantic target.
    - Mechanism: Delegate to `KernelNavigation.build_lens` and emit the resulting boundary payload.
    - Guarantee: Returns 0 after emitting the lens result.
    - Fails: Returns 1 when the target cannot be resolved.
    - When-needed: Open when the task already has a semantic target and needs the focused boundary view instead of the whole atlas.
    - Escalates-to: system/lib/kernel_nav_lens.py; system/lib/kernel_navigation.py
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_lens(target)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_plan_phase(plan_id: str | None = None) -> int:
    """[ACTION]
    - Teleology: Emit the active implementation plan plus its current manifest batch context.
    - Mechanism: Delegate to `KernelNavigation.build_plan_phase` and emit the resulting plan payload.
    - Guarantee: Returns 0 after emitting the plan-phase packet.
    - Fails: Returns 1 when the plan cannot be resolved.
    - When-needed: Open when implementation work needs the active plan and batch context before touching code.
    - Escalates-to: system/lib/kernel_nav_phase.py; kernel.py
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_plan_phase(plan_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def _phase_output_note_stub(note: object) -> dict[str, Any] | None:
    if not isinstance(note, Mapping):
        return None
    return {
        "path": note.get("path"),
        "title": note.get("title"),
        "role": note.get("role"),
        "status": note.get("status"),
        "focus_badges": list(note.get("focus_badges") or []),
    }


def _phase_active_execution_overlay(phase: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    try:
        from system.lib.active_execution_constellation import build_active_execution_constellation

        active_execution = build_active_execution_constellation(
            state.REPO_ROOT,
            active_phase={
                "active_phase_id": phase.get("phase_id"),
                "active_phase_title": phase.get("phase_title"),
                "active_phase_dir": phase.get("phase_dir"),
            },
            campaign_limit=3,
            claim_limit=0,
            session_limit=3,
        )
    except Exception:
        return {}, []
    if not _pulse_has_hot_execution(active_execution):
        return {}, []

    anchor = (
        active_execution.get("declared_anchor")
        if isinstance(active_execution.get("declared_anchor"), Mapping)
        else {}
    )
    campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    compact_campaigns: list[dict[str, Any]] = []
    for campaign in campaigns[:3]:
        if not isinstance(campaign, Mapping):
            continue
        compact_campaigns.append(
            {
                key: campaign.get(key)
                for key in ("workitem_id", "rank", "state", "title")
                if campaign.get(key) not in (None, "", [], {})
            }
        )
    stale_pointers = (
        active_execution.get("stale_decorative_pointers")
        if isinstance(active_execution.get("stale_decorative_pointers"), list)
        else []
    )
    stale_pointer = stale_pointers[0] if stale_pointers and isinstance(stale_pointers[0], Mapping) else {}
    compact: dict[str, Any] = {
        "kind": active_execution.get("kind") or "active_execution_constellation",
        "view_profile": "phase_liveness_overlay",
        "declared_anchor": {
            key: anchor.get(key)
            for key in ("phase_id", "status", "runtime_state", "runtime_gate_reason")
            if anchor.get(key) not in (None, "", [], {})
        },
        "live_campaigns": compact_campaigns,
        "live_sessions": {
            "counts": {
                key: session_counts.get(key)
                for key in ("active_claims", "effective_active_sessions", "orphaned_active_sessions")
                if session_counts.get(key) not in (None, "", [], {})
            },
        },
    }
    if stale_pointer:
        compact["stale_decorative_pointer"] = {
            key: stale_pointer.get(key)
            for key in ("pointer", "replacement_surface")
            if stale_pointer.get(key) not in (None, "", [], {})
        }
    compact["projection_freshness"] = {
        "status": (
            (active_execution.get("projection_freshness") or {}).get("status")
            if isinstance(active_execution.get("projection_freshness"), Mapping)
            else None
        )
    }
    compact["liveness_summary"] = (
        "Declared phase is contextual/dormant; current execution routes through WorkItems/claims."
        if str(anchor.get("status") or "") == "declared_anchor_runtime_dormant"
        else "Verify phase context against WorkItems/claims before mutating."
    )
    compact["authority_order"] = ["Task Ledger WorkItems", "Work Ledger claims", "phase context"]
    return compact, _phase_active_execution_next_actions(active_execution)


def _phase_active_execution_next_actions(active_execution: Mapping[str, Any]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    campaigns = (
        active_execution.get("live_campaigns")
        if isinstance(active_execution.get("live_campaigns"), list)
        else []
    )
    campaign_rows = [item for item in campaigns if isinstance(item, Mapping)]
    if campaign_rows:
        first_campaign = campaign_rows[0]
        command = str(first_campaign.get("drilldown_command") or "").strip()
        workitem_id = str(first_campaign.get("workitem_id") or first_campaign.get("id") or "").strip()
        if command:
            actions.append(
                {
                    "command": command,
                    "reason": (
                        "Open the hot Task Ledger WorkItem before treating the phase wave "
                        f"as current{f' ({workitem_id})' if workitem_id else ''}."
                    ),
                }
            )

    live_sessions = (
        active_execution.get("live_sessions")
        if isinstance(active_execution.get("live_sessions"), Mapping)
        else {}
    )
    session_counts = (
        live_sessions.get("counts")
        if isinstance(live_sessions.get("counts"), Mapping)
        else {}
    )
    session_rows = (
        live_sessions.get("sessions")
        if isinstance(live_sessions.get("sessions"), list)
        else []
    )
    if int(session_counts.get("active_claims") or 0) or session_rows:
        drilldowns = (
            live_sessions.get("drilldown_commands")
            if isinstance(live_sessions.get("drilldown_commands"), Mapping)
            else {}
        )
        command = str(drilldowns.get("cards") or "").strip()
        if command:
            actions.append(
                {
                    "command": command,
                    "reason": "Open the compact active-seed session packet before using phase target paths as a write set.",
                }
            )

    for item in active_execution.get("next_actions") or []:
        if not isinstance(item, Mapping):
            continue
        command = str(item.get("command") or "").strip()
        if not command or any(existing["command"] == command for existing in actions):
            continue
        actions.append(
            {
                "command": command,
                "reason": str(item.get("reason") or "").strip(),
            }
        )
        if len(actions) >= 4:
            break
    return actions[:4]


def _merge_unique_next_actions(*groups: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if not isinstance(item, Mapping):
                continue
            command = normalize_repo_kernel_command(str(item.get("command") or "").strip())
            if not command or command in seen:
                continue
            seen.add(command)
            actions.append(
                {
                    "command": command,
                    "reason": str(item.get("reason") or "").strip(),
                }
            )
            if len(actions) >= 4:
                return actions
    return actions


def _phase_output_mode_packet(
    result: NavigationResult,
    *,
    output_mode: str,
    task_query: str | None = None,
) -> dict[str, Any]:
    payload = result.payload
    phase = payload.get("phase") if isinstance(payload.get("phase"), Mapping) else {}
    phase_card = payload.get("phase_card") if isinstance(payload.get("phase_card"), Mapping) else {}
    active_wave = phase_card.get("active_wave") if isinstance(phase_card.get("active_wave"), Mapping) else {}
    target_paths = list(active_wave.get("target_paths") or []) if isinstance(active_wave.get("target_paths"), list) else []
    target_path_limit = 20
    visible_target_paths = target_paths[:target_path_limit]
    omitted_target_paths = target_paths[target_path_limit:]
    stage_guidance = payload.get("stage_guidance") if isinstance(payload.get("stage_guidance"), Mapping) else {}
    transaction_control_plane = (
        payload.get("transaction_control_plane")
        if isinstance(payload.get("transaction_control_plane"), Mapping)
        else None
    )
    transaction_control_plane_hint = (
        payload.get("transaction_control_plane_hint")
        if isinstance(payload.get("transaction_control_plane_hint"), Mapping)
        else None
    )
    phase_ref = str(phase.get("phase_id") or phase.get("phase_number") or "<phase>").strip() or "<phase>"
    phase_command = f"./repo-python kernel.py --phase {phase_ref}"
    task_phase_alignment = (
        build_phase_task_alignment(
            phase_ref,
            task_query,
            phase_title=str(phase.get("phase_title") or ""),
            active_wave=active_wave,
        )
        if task_query is not None
        else None
    )
    summary_command = phase_command
    task_summary_command = f"{phase_command} --task {shlex.quote(str(task_query))}" if task_query is not None else None
    compat_summary_command = f"{phase_command} --summary"
    full_command = f"{phase_command} --full"
    omitted_sections = [
        {
            "section": "payload.phase_card",
            "preserved_fields": ["active_wave", "last_outcome", "next_step_posture", "stage"],
            "why_omitted": "summary view; full phase card is evidence/debug context",
        },
        {
            "section": "payload.family",
            "why_omitted": "family/archive lists repeat long paths",
        },
        {
            "section": "payload.recovery_map",
            "why_omitted": "repair diagnostics belong in full evidence",
        },
        {
            "section": "payload.active_synth",
            "why_omitted": "synth internals are authoring/debug evidence",
        },
        {
            "section": "payload.derived_index.entry",
            "why_omitted": "derived-index internals duplicate phase identity",
        },
        {
            "section": "payload.plan_context|observe_authoring|manifest|closeout",
            "why_omitted": "detailed task state is drilldown context",
        },
        {
            "section": "payload.transaction_control_plane",
            "why_omitted": "transaction probes stay behind full drilldown",
        },
    ]
    alignment_next: list[dict[str, str]] = []
    if isinstance(task_phase_alignment, Mapping):
        for command in list(task_phase_alignment.get("legal_owner_commands") or [])[:3]:
            text = str(command or "").strip()
            if text:
                alignment_next.append(
                    {
                        "command": text,
                        "reason": "Legal owner surface for the selected phase task lane.",
                    }
                )
    active_execution_overlay, active_execution_next = _phase_active_execution_overlay(phase)
    if active_execution_overlay and target_path_limit > 3:
        target_path_limit = 3
        visible_target_paths = target_paths[:target_path_limit]
        omitted_target_paths = target_paths[target_path_limit:]
    omitted_target_path_count = len(omitted_target_paths)
    if active_execution_overlay:
        omitted_target_paths = []
    phase_next = [
        {
            "command": normalize_repo_kernel_command(str(item.get("command") or "")),
            "reason": str(item.get("reason") or "").strip(),
        }
        for item in list(result.suggested_next or [])[:3]
        if isinstance(item, Mapping) and str(item.get("command") or "").strip()
    ]
    packet: dict[str, Any] = {
        "kind": result.kind,
        "kernel_version": state.KERNEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": output_mode,
        "query": {**result.query, "output_mode": output_mode},
        "summary": {
            "phase_id": phase.get("phase_id"),
            "status": phase.get("status"),
            "execution_mode": phase.get("execution_mode"),
            "current_wave_id": phase.get("current_wave_id"),
            "task_alignment_status": (
                task_phase_alignment.get("status") if isinstance(task_phase_alignment, Mapping) else None
            ),
            "selected_lane": (
                task_phase_alignment.get("selected_lane") if isinstance(task_phase_alignment, Mapping) else None
            ),
            "canonical_entry": (
                (payload.get("canonical_entry") or {}).get("path")
                if isinstance(payload.get("canonical_entry"), Mapping)
                else None
            ),
            "warning_count": len(result.warnings or []),
            "active_execution_status": (
                ((active_execution_overlay.get("declared_anchor") or {}).get("status"))
                if isinstance(active_execution_overlay.get("declared_anchor"), Mapping)
                else None
            ),
        },
        "sources": {
            "live": list(result.live_sources or [])[:6],
            "derived": list(result.derived_sources or [])[:4],
            "derived_required": result.derived_required,
        },
        "payload": {
            "view_profile": "phase_agent_control_packet_v0",
            "safe_decision_supported": (
                "Use the phase as context; choose current execution from Task Ledger/Work Ledger when the active-execution overlay is present."
            ),
            "source_payload_owner": {
                "owner_id": "kernel.phase.full_payload",
                "authority_plane": "source_payload",
                "primary_surface": full_command,
                "owning_code": [
                    "system/lib/kernel_nav_phase.py::PhasePlanMixin.build_phase",
                    "system/lib/kernel_navigation.py::NavigationResult.to_dict",
                ],
                "facts_owned": [
                    "complete phase card",
                    "family members and archive members",
                    "recovery map",
                    "active synth normalization",
                    "derived index entry",
                    "plan, manifest, observe-authoring, and closeout details",
                    "transaction control-plane rollup when present",
                ],
                "source_mutation_allowed_by_this_profile": False,
            },
            "view_owner": {
                "owner_id": "phase_agent_control_packet_v0",
                "authority_plane": "view_profile",
                "view_surface": summary_command,
                "owning_code": [
                    "system/lib/kernel/commands/navigate.py::_phase_output_mode_packet",
                ],
                "omission_authority": [
                    "Default phase entry may omit evidence/debug sections when full_payload_hint names the drilldown.",
                    "Repeated long paths may be represented by bounded active-wave targets and source counts.",
                    "Derived-index and normalized-synth internals remain source-owned by the full payload.",
                ],
                "view_mutation_allowed_by_this_profile": "phase_output_view_only",
            },
            "full_payload_hint": {
                "command": full_command,
                "required_when": [
                    "debugging phase selection, recovery, or derived-index state",
                    "authoring an observe plan from detailed synth internals",
                    "auditing family/archive members or closeout records",
                    "checking omitted source authority before a mutation",
                ],
                "drilldown_sufficient_if": [
                    "the full payload resolves the same phase_id",
                    "the omitted sections listed by the control packet are present in the full payload",
                ],
            },
            "omitted_sections": omitted_sections,
            "phase": {
                "phase_id": phase.get("phase_id"),
                "phase_number": phase.get("phase_number"),
                "phase_title": phase.get("phase_title"),
                "phase_dir": phase.get("phase_dir"),
                "status": phase.get("status"),
                "execution_mode": phase.get("execution_mode"),
                "current_wave_id": phase.get("current_wave_id"),
            },
            "active_execution_overlay": active_execution_overlay or None,
            "canonical_entry": _phase_output_note_stub(payload.get("canonical_entry")),
            "active_wave": {
                "wave_id": active_wave.get("wave_id"),
                "mode": active_wave.get("mode"),
                "status": active_wave.get("status"),
                "objective": active_wave.get("objective"),
                "bounded_question": active_wave.get("bounded_question"),
                "selected_for_current_task": (
                    None
                    if not isinstance(task_phase_alignment, Mapping)
                    else bool((task_phase_alignment.get("write_guard") or {}).get("primary_wave_write_allowed"))
                ),
                "target_paths_write_status": (
                    ((task_phase_alignment.get("write_guard") or {}).get("primary_wave_target_paths_write_status"))
                    if isinstance(task_phase_alignment, Mapping)
                    else "unknown_until_task_alignment"
                ),
                "target_path_count": len(target_paths),
                "target_paths": visible_target_paths,
                "target_paths_limit": target_path_limit,
                "omitted_target_paths": omitted_target_paths,
                "omitted_target_path_count": omitted_target_path_count,
            },
            "last_outcome": phase_card.get("last_outcome"),
            "next_step_posture": _agent_wake_truncate(phase_card.get("next_step_posture"), 420),
            "stage": {
                "stage": stage_guidance.get("stage"),
                "summary": _agent_wake_truncate(stage_guidance.get("summary"), 280),
            }
            if stage_guidance
            else None,
            "task_phase_alignment": task_phase_alignment,
            "available_residual_lanes": phase_residual_lane_catalog(),
            "command_budget": {
                "purpose": "Bound phase reentry when the full phase card is unnecessary.",
                "summary_command": summary_command,
                "task_summary_command": task_summary_command,
                "compat_summary_command": compat_summary_command,
                "full_command": full_command,
                "warnings_command": f"{phase_command} --warnings-only",
            },
        },
        "next": _merge_unique_next_actions(
            alignment_next,
            active_execution_next,
            phase_next,
        ),
        "warnings": list(result.warnings or []),
    }
    if transaction_control_plane is not None:
        packet["payload"]["transaction_control_plane"] = transaction_control_plane
    elif transaction_control_plane_hint is not None:
        packet["payload"]["transaction_control_plane_hint"] = transaction_control_plane_hint
    if output_mode == "warnings_only":
        # Preserve focus-drift WorkItem context so warnings_only callers see the
        # actionable Task Ledger surface, not just the bare drift string.
        lifecycle_enforcement = (
            result.payload.get("phase_lifecycle_enforcement")
            if isinstance(result.payload.get("phase_lifecycle_enforcement"), Mapping)
            else {}
        )
        focus_drift_actions = (
            list(lifecycle_enforcement.get("focus_drift_actions") or [])
            if isinstance(lifecycle_enforcement, Mapping)
            else []
        )
        focus_conflicts_payload = (
            list(lifecycle_enforcement.get("focus_conflicts") or [])
            if isinstance(lifecycle_enforcement, Mapping)
            else []
        )
        recommended_commands_payload = (
            list(lifecycle_enforcement.get("recommended_commands") or [])
            if isinstance(lifecycle_enforcement, Mapping)
            else []
        )
        packet["payload"] = {
            "phase": packet["payload"]["phase"],
            "canonical_entry": packet["payload"]["canonical_entry"],
            "warning_count": len(result.warnings or []),
            "warnings": list(result.warnings or []),
            "command_budget": packet["payload"]["command_budget"],
        }
        if focus_conflicts_payload:
            packet["payload"]["focus_conflicts"] = focus_conflicts_payload
        if focus_drift_actions:
            packet["payload"]["focus_drift_actions"] = focus_drift_actions
        if recommended_commands_payload:
            packet["payload"]["recommended_commands"] = recommended_commands_payload
        if task_phase_alignment is not None:
            packet["payload"]["task_phase_alignment"] = task_phase_alignment
        packet["next"] = [
            {
                "command": "./repo-python kernel.py --phase <phase> --summary",
                "reason": "Open the bounded phase summary if the warnings-only packet is clean but more context is needed.",
            }
        ]
    return packet


def cmd_phase(
    phase_token: str | None = None,
    *,
    summary: bool = False,
    warnings_only: bool = False,
    task_query: str | None = None,
) -> int:
    """[ACTION]
    - Teleology: Emit the phase control packet derived from self-describing phase-family metadata.
    - Mechanism: Delegate to `KernelNavigation.build_phase`; emit the bounded agent-control view by default and the full evidence/debug envelope only when global --full is active.
    - Guarantee: Returns 0 after emitting the phase packet.
    - Fails: Returns 1 when the phase token cannot be resolved.
    - When-needed: Open when the task is phase-scoped and you need the current phase packet rather than reading phase artifacts individually.
    - Escalates-to: system/lib/kernel_nav_phase.py; kernel.py
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_phase(
            phase_token,
            include_transaction_control_plane=bool(
                state.NAVIGATION_FULL_OUTPUT and not summary and not warnings_only
            ),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if warnings_only:
        return emit_json(_phase_output_mode_packet(result, output_mode="warnings_only", task_query=task_query))
    if summary or not state.NAVIGATION_FULL_OUTPUT:
        return emit_json(_phase_output_mode_packet(result, output_mode="summary", task_query=task_query))
    return emit_navigation(result, full=True)


def cmd_campaign(
    phase_token: str | None = None,
    *,
    task_query: str | None = None,
) -> int:
    """Emit the read-only integration campaign packet above phase/lane routing."""
    try:
        packet = build_campaign_packet(
            state.REPO_ROOT,
            phase_token=phase_token,
            task_query=task_query,
            pulse_snapshot=_pulse_snapshot(),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(packet)


def cmd_campaign_state_sync(campaign_id: str, *, receipt_id: str | None = None) -> int:
    """Assimilate one Work Ledger receipt into persisted campaign state."""
    if not receipt_id:
        print("ERROR: --campaign-state-sync requires --receipt td_<id>", file=sys.stderr)
        return 1
    try:
        payload = sync_campaign_state_from_receipt(
            state.REPO_ROOT,
            campaign_id=campaign_id,
            receipt_id=receipt_id,
        )
    except CampaignTransitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(payload)


def cmd_campaign_dispatch_register(
    campaign_id: str,
    *,
    mission_id: str | None = None,
    lane_id: str | None = None,
    objective: str | None = None,
    source_refs: Sequence[str] | None = None,
    write_scope: Sequence[str] | None = None,
) -> int:
    """Register a candidate campaign dispatch through the transition event log."""
    if not mission_id:
        print("ERROR: --campaign-dispatch-register requires --mission <mission_id>", file=sys.stderr)
        return 1
    if not lane_id:
        print("ERROR: --campaign-dispatch-register requires --lane <lane_id>", file=sys.stderr)
        return 1
    if not objective:
        print("ERROR: --campaign-dispatch-register requires --objective <text>", file=sys.stderr)
        return 1
    try:
        payload = register_campaign_dispatch(
            state.REPO_ROOT,
            campaign_id=campaign_id,
            mission_id=mission_id,
            lane_id=lane_id,
            objective=objective,
            source_refs=source_refs or [],
            write_scope=write_scope or [],
        )
    except CampaignTransitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(payload)


def cmd_hidden_substrate_reconciliation(*, live: bool = False) -> int:
    """Emit or write the hidden-substrate local-affordance reconciliation report."""
    try:
        payload = (
            write_hidden_substrate_affordance_reconciliation(state.REPO_ROOT)
            if live
            else build_hidden_substrate_affordance_reconciliation(state.REPO_ROOT)
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json(payload)


def cmd_phase_step(
    phase_token: str | None = None,
    *,
    live: bool = False,
    force: bool = False,
    task_query: str | None = None,
) -> int:
    """[ACTION]
    - Teleology: Compile the next wave-native subphase action from the active synth and phase-native controller state without inventing a second controller root.
    - Mechanism: Resolve the phase packet, materialize family autonomous seed continuity when needed, ask the phase-native controller whether the wave is dispatchable or resumable, and then either write `observe_plan.json` or derive `continuation_summary.json` plus `synth_seed_delta.json`.
    - Guarantee: Returns a preview or live payload describing the next bounded action, written artifacts, and follow-up commands.
    - Fails: Returns 1 when the phase or synth cannot be resolved, the observe-plan payload is invalid, or a completed wave lacks the typed checkpoint receipt needed for resume.
    - When-needed: Open when a subphase should advance one bounded step through the shared wave/checkpoint contract rather than hand-editing synth or continuation artifacts.
    - Escalates-to: system.lib.seed_pipeline_controller.py; tools/meta/apply/run_observe_plan.py; system/lib/kernel/commands/navigate.py::cmd_phase_assimilate
    - Navigation-group: kernel_lib
    """
    try:
        _navigator, phase_entry = _resolve_phase_entry_for_lifecycle(phase_token)
        scaffold_path = _phase_scaffold_path_for_entry(phase_entry)
        scaffold_payload = safe_load_json(scaffold_path)
        if not isinstance(scaffold_payload, dict):
            raise ValueError(f"Invalid phase_scaffold.json: {state.rel(scaffold_path)}")
        synth_path = _phase_file_from_entry(phase_entry, "synth_seed.json")
        synth_payload = safe_load_json(synth_path)
        if not isinstance(synth_payload, dict):
            raise ValueError(f"Invalid synth_seed.json: {state.rel(synth_path)}")
        autonomous_seed = _ensure_phase_family_autonomous_seed(phase_entry)
        normalized = normalize_synth_payload(synth_payload, phase_scaffold=scaffold_payload)
        if not isinstance(normalized, dict):
            raise ValueError("Could not normalize synth_seed.json")
        preview = phase_step_controller.phase_step_preview(
            phase_entry,
            normalized,
            repo_root=state.REPO_ROOT,
            force=force,
        )
        history_state = phase_step_controller.phase_step_history_state(
            repo_root=state.REPO_ROOT,
            observe_history_entry=preview.get("observe_history_entry"),
            stage_kind=str(preview.get("stage_kind") or "problem_space"),
        )
        actual_action = str(preview.get("action") or "dispatch").strip()
        if force and history_state.get("checkpoint_ready"):
            actual_action = "resume"
        if actual_action == "resume":
            writes = [
                {"path": str(preview.get("continuation_summary_path") or "").strip(), "kind": "continuation_summary"},
                {"path": str(preview.get("synth_delta_path") or "").strip(), "kind": "synth_seed_delta"},
            ]
        elif actual_action == "dispatch":
            writes = [
                {"path": str(preview.get("observe_plan_path") or "").strip(), "kind": "observe_plan"},
            ]
        else:
            writes = []
        follow_up_commands: list[dict[str, Any]] = []
        if actual_action == "dispatch":
            launch_parts = [
                "python3 kernel.py --launch-observe",
                f"--plan {shlex.quote(str(preview.get('observe_plan_path') or ''))}",
            ]
            if str(normalized.get("execution_mode") or normalized.get("current_wave", {}).get("mode") or "").strip() in BRIDGE_COMPILABLE_EXECUTION_MODES:
                launch_parts.extend(["--bridge", "--provider chatgpt", "--bridge-workers 3"])
            follow_up_commands.append(
                {
                    "command": " ".join(launch_parts),
                    "reason": "Run the compiled grouped-observe stage for the active wave.",
                }
            )
        elif actual_action == "resume":
            follow_up_commands.append(
                {
                    "command": f"python3 kernel.py --phase-assimilate {shlex.quote(str(phase_entry.get('phase_id') or phase_entry.get('phase_number') or ''))} --live",
                    "reason": "Assimilate the compiled checkpoint summary and synth delta into the next wave.",
                }
            )
        elif actual_action == "assimilate_ready":
            follow_up_commands.append(
                {
                    "command": f"python3 kernel.py --phase-assimilate {shlex.quote(str(phase_entry.get('phase_id') or phase_entry.get('phase_number') or ''))} --live",
                    "reason": "Checkpoint artifacts already exist; assimilate them into the next wave.",
                }
            )
        payload = {
            "kind": "kernel.phase_step",
            "mode": "live" if live else "preview",
            "status": "preview_ready",
            "phase": {
                "phase_id": phase_entry.get("phase_id"),
                "phase_number": phase_entry.get("phase_number"),
                "phase_title": phase_entry.get("phase_title"),
                "phase_dir": phase_entry.get("phase_dir"),
                "family_dir": _phase_step_family_dir(phase_entry) or None,
            },
            "autonomous_seed": {
                "materialized": bool(autonomous_seed.get("autonomous_seed_path")),
                "path": autonomous_seed.get("autonomous_seed_path"),
                "markdown_path": autonomous_seed.get("autonomous_seed_markdown_path"),
            },
            "preview": preview,
            "action": actual_action,
            "writes": writes,
            "suggested_next": follow_up_commands,
        }
        task_phase_alignment: dict[str, Any] | None = None
        campaign_write_guard: dict[str, Any] | None = None
        if task_query is not None:
            task_phase_alignment = build_phase_task_alignment(
                phase_entry.get("phase_id") or phase_entry.get("phase_number"),
                task_query,
                phase_title=str(phase_entry.get("phase_title") or ""),
                active_wave=normalized.get("current_wave") if isinstance(normalized.get("current_wave"), Mapping) else {},
            )
            campaign_selected_lane = classify_campaign_lane(task_query, task_phase_alignment)
            campaign_write_guard = build_campaign_write_guard(
                selected_lane=campaign_selected_lane,
                phase_alignment=task_phase_alignment,
                primary_wave_id=str(task_phase_alignment.get("primary_wave") or PROVIDER_METABOLISM_LANE_ID),
            )
            phase_write_guard = task_phase_alignment.get("write_guard")
            payload["task_phase_alignment"] = task_phase_alignment
            payload["phase_write_guard"] = phase_write_guard
            payload["write_guard"] = phase_write_guard
            payload["campaign_write_guard"] = campaign_write_guard
            payload["effective_authority"] = {
                "selected_layer": campaign_write_guard.get("selected_layer"),
                "selected_lane": campaign_write_guard.get("selected_campaign_lane"),
                "effective_write_authority": campaign_write_guard.get("effective_write_authority"),
                "phase_step_live_allowed": bool(campaign_write_guard.get("phase_step_live_allowed")),
                "phase_primary_writes_allowed": bool(campaign_write_guard.get("phase_primary_writes_allowed")),
                "residual_owner_required": bool(campaign_write_guard.get("residual_owner_required")),
                "type_a_dispatch_required": bool(campaign_write_guard.get("type_a_dispatch_required")),
            }
            payload["next"] = [
                {"command": str(command), "reason": "Legal owner surface for the selected phase task lane."}
                for command in list(task_phase_alignment.get("legal_owner_commands") or [])[:3]
                if str(command or "").strip()
            ]
            if campaign_selected_lane in CAMPAIGN_ONLY_LANE_IDS:
                payload["write_guard"] = campaign_write_guard
                payload["next"] = [
                    {
                        "command": f"./repo-python kernel.py --campaign --task {shlex.quote(task_query)}",
                        "reason": "Campaign selected a non-phase lane; use the campaign packet and Type A dispatch contract.",
                    }
                ]
        if not live:
            return emit_json(payload)

        if (
            isinstance(campaign_write_guard, Mapping)
            and str(campaign_write_guard.get("effective_write_authority") or "") == "campaign"
            and not bool(campaign_write_guard.get("phase_step_live_allowed"))
        ):
            blocked_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"preview", "action", "suggested_next"}
            }
            return emit_json(
                {
                    **blocked_payload,
                    "mode": "live_blocked",
                    "status": "campaign_lane_write_blocked",
                    "reason": campaign_write_guard.get("reason"),
                    "writes": [],
                    "blocked_primary_wave_preview": {
                        "would_have_action": actual_action,
                        "preview": preview,
                        "suppressed_writes": writes,
                        "suppressed_next": follow_up_commands,
                    },
                }
            )

        if (
            isinstance(task_phase_alignment, Mapping)
            and str(task_phase_alignment.get("status") or "") == "residual_lane"
            and not bool((task_phase_alignment.get("write_guard") or {}).get("live_phase_step_allowed"))
        ):
            blocked_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"preview", "action", "suggested_next"}
            }
            return emit_json(
                {
                    **blocked_payload,
                    "mode": "live_blocked",
                    "status": "residual_lane_write_blocked",
                    "reason": (task_phase_alignment.get("write_guard") or {}).get("reason"),
                    "writes": [],
                    "blocked_primary_wave_preview": {
                        "would_have_action": actual_action,
                        "preview": preview,
                        "suppressed_writes": writes,
                        "suppressed_next": follow_up_commands,
                    },
                }
            )

        if actual_action == "dispatch":
            observe_plan = _compile_phase_step_observe_plan(
                phase_entry=phase_entry,
                scaffold_payload=scaffold_payload,
                synth_payload=normalized,
                autonomous_seed_path=str(autonomous_seed.get("autonomous_seed_path") or "").strip() or None,
                preview=preview,
            )
            errors, warnings = _kernel_validate_observe_payload(observe_plan)
            if errors:
                return emit_json_with_code(
                    {
                        **payload,
                        "status": "invalid_phase_step_plan",
                        "errors": errors,
                        "warnings": warnings,
                        "observe_plan": observe_plan,
                    },
                    1,
                )
            observe_plan_path = state.REPO_ROOT / str(preview.get("observe_plan_path") or "")
            observe_plan_path.parent.mkdir(parents=True, exist_ok=True)
            observe_plan_path.write_text(json.dumps(observe_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return emit_json(
                {
                    **payload,
                    "status": "observe_plan_written",
                    "observe_plan_path": state.rel(observe_plan_path),
                    "warnings": warnings,
                }
            )

        if actual_action == "resume":
            checkpoint_payload = history_state.get("checkpoint_payload")
            if not isinstance(checkpoint_payload, Mapping):
                raise ValueError("phase-step resume requires a completed checkpoint receipt in grouped observe history.")
            probe_payloads = [
                dict(item)
                for item in (history_state.get("probe_payloads") or [])
                if isinstance(item, Mapping)
            ]
            transition = phase_step_controller.phase_step_transition(
                normalized,
                checkpoint_payload,
                probe_payloads=probe_payloads,
                force=force,
            )
            files_touched = sorted(
                {
                    canonicalize_write_path(str(item).strip()) or str(item).strip()
                    for item in (
                        list(normalized.get("current_wave", {}).get("target_paths") or [])
                        + [
                            path
                            for row in probe_payloads
                            for path in ((row.get("receipt") or {}).get("files_examined") or [])
                        ]
                    )
                    if str(item).strip()
                }
            )
            artifact_paths = sorted(
                {
                    canonicalize_write_path(str(item).strip()) or str(item).strip()
                    for item in (
                        [
                            str(preview.get("observe_plan_path") or "").strip(),
                            str(history_state.get("history_entry") or "").strip(),
                        ]
                        + list(history_state.get("artifact_paths") or [])
                    )
                    if str(item).strip()
                }
            )
            continuation_payload = phase_step_controller.build_phase_step_continuation_summary(
                phase_entry=phase_entry,
                synth=normalized,
                checkpoint_payload=checkpoint_payload,
                transition=transition,
                files_touched=files_touched,
                artifact_paths=artifact_paths,
                probe_payloads=probe_payloads,
                legacy_cycle_index=int(preview.get("legacy_cycle_index") or 0),
            )
            continuation_path = state.REPO_ROOT / str(preview.get("continuation_summary_path") or "")
            continuation_path.parent.mkdir(parents=True, exist_ok=True)
            continuation_path.write_text(canonical_json_text(continuation_payload), encoding="utf-8")
            delta_payload = {
                "schema_version": "synth_seed_delta_v0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "target_phase_dir": str(phase_entry.get("phase_dir") or "").strip(),
                "patches": list(transition.get("delta_patches") or []),
            }
            delta_path = state.REPO_ROOT / str(preview.get("synth_delta_path") or "")
            delta_path.parent.mkdir(parents=True, exist_ok=True)
            delta_path.write_text(canonical_json_text(delta_payload), encoding="utf-8")
            return emit_json(
                {
                    **payload,
                    "status": "checkpoint_compiled",
                    "continuation_summary_path": state.rel(continuation_path),
                    "synth_delta_path": state.rel(delta_path),
                    "transition": transition,
                }
            )

        return emit_json(
            {
                **payload,
                "status": "no_op",
                "reason": preview.get("no_op_reason") or "phase_step_noop",
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_phase_assimilate(phase_token: str | None = None, *, live: bool = False) -> int:
    """[ACTION]
    - Teleology: Close the active wave for one phase by archiving the prior synth, applying an optional typed delta, appending a wave-history ledger row, and regenerating the synth markdown.
    - Mechanism: Resolve the phase, normalize the active synth, derive assimilation targets, preview or write the archive path, optionally apply synth_seed_delta.json, update cycle metadata, append a ledger entry, and rewrite synth_seed.md.
    - Guarantee: Returns a preview/live payload with the archive path, ledger entry, and touched artifact list.
    - Fails: Returns 1 when the phase, scaffold, synth, or ledger artifacts are invalid or when a typed synth delta fails validation.
    - When-needed: Open when a completed direct, hybrid, bridge, or subagent wave needs to be rolled back into the active synth packet.
    - Escalates-to: system/lib/synth_seed_delta_merge.py; system/lib/observe_apply_contracts.py
    - Navigation-group: kernel_lib
    """
    try:
        _navigator, phase_entry = _resolve_phase_entry_for_lifecycle(phase_token)
        scaffold_path = _phase_scaffold_path_for_entry(phase_entry)
        scaffold_payload = safe_load_json(scaffold_path)
        if not isinstance(scaffold_payload, dict):
            raise ValueError(f"Invalid phase_scaffold.json: {state.rel(scaffold_path)}")
        synth_json_path = _phase_file_from_entry(phase_entry, "synth_seed.json")
        synth_markdown_path = _phase_file_from_entry(phase_entry, "synth_seed.md")
        meta_ledger_path = _phase_file_from_entry(phase_entry, "meta_ledger.json")
        current_payload = safe_load_json(synth_json_path)
        if not isinstance(current_payload, dict):
            raise ValueError(f"Invalid synth_seed.json: {state.rel(synth_json_path)}")
        meta_ledger = safe_load_json(meta_ledger_path)
        if not isinstance(meta_ledger, dict):
            raise ValueError(f"Invalid meta_ledger.json: {state.rel(meta_ledger_path)}")
        ledger_entries = meta_ledger.get("entries")
        if not isinstance(ledger_entries, list):
            raise ValueError(f"meta_ledger.json is missing an entries list: {state.rel(meta_ledger_path)}")

        normalized = normalize_synth_payload(current_payload, phase_scaffold=scaffold_payload)
        if not isinstance(normalized, dict):
            raise ValueError("Could not normalize synth_seed.json")
        current_wave = dict(normalized.get("current_wave") or {})
        assimilation_targets = normalize_assimilation_targets(
            normalized.get("assimilation_targets"),
            phase_scaffold=scaffold_payload,
        )
        archive_root_rel = canonicalize_write_path(str(assimilation_targets.get("archive_root") or "").strip()) or ""
        if not archive_root_rel:
            raise ValueError("assimilation_targets.archive_root is required.")
        wave_id = str(current_wave.get("wave_id") or "wave_001").strip()
        archive_rel = canonicalize_write_path(
            f"{archive_root_rel.rstrip('/')}/synth_seed__{wave_id}__{_timestamp_slug()}.json"
        ) or ""
        if not archive_rel:
            raise ValueError("Could not resolve synth archive path.")
        delta_rel = canonicalize_write_path(str(assimilation_targets.get("delta_path") or "").strip()) or ""
        continuation_rel = canonicalize_write_path(str(assimilation_targets.get("continuation_summary_path") or "").strip()) or ""
        delta_path = state.REPO_ROOT / delta_rel if delta_rel else None
        continuation_path = state.REPO_ROOT / continuation_rel if continuation_rel else None
        files_touched = sorted(
            {
                canonicalize_write_path(str(item.get("path") or "").strip()) or str(item.get("path") or "").strip()
                for item in (normalized.get("working_set") or [])
                if isinstance(item, Mapping) and str(item.get("path") or "").strip()
            }
            | {
                canonicalize_write_path(str(item).strip()) or str(item).strip()
                for item in (current_wave.get("target_paths") or [])
                if str(item).strip()
            }
        )
        preview_entry = _wave_ledger_entry(
            phase_entry=phase_entry,
            wave=current_wave,
            normalized_synth=normalized,
            archived_synth_path=archive_rel,
            delta_path=delta_rel,
            continuation_summary_path=continuation_rel,
            files_touched=files_touched,
            legacy_cycle_index=int((normalized.get("meta") or {}).get("current_cycle") or 0),
        )
        payload = {
            "kind": "kernel.phase_assimilate",
            "mode": "live" if live else "preview",
            "status": "applied" if live else "preview_ready",
            "phase": {
                "phase_id": phase_entry.get("phase_id"),
                "phase_number": phase_entry.get("phase_number"),
                "phase_title": phase_entry.get("phase_title"),
                "phase_dir": phase_entry.get("phase_dir"),
            },
            "wave": {
                "wave_id": wave_id,
                "mode": normalized.get("execution_mode"),
                "status": current_wave.get("status"),
            },
            "assimilation": {
                "archive_path": archive_rel,
                "delta_path": delta_rel or None,
                "delta_exists": bool(delta_path and delta_path.exists()),
                "continuation_summary_path": continuation_rel or None,
                "continuation_summary_exists": bool(continuation_path and continuation_path.exists()),
                "ledger_path": state.rel(meta_ledger_path),
            },
            "ledger_entry": preview_entry,
            "writes": [
                {"path": archive_rel, "kind": "synth_seed_archive"},
                {"path": state.rel(meta_ledger_path), "kind": "meta_ledger"},
                {"path": state.rel(synth_json_path), "kind": "synth_seed"},
                {"path": state.rel(synth_markdown_path), "kind": "synth_seed_note"},
                {"path": state.rel(scaffold_path), "kind": "phase_scaffold_spec"},
            ],
        }
        if not live:
            return emit_json(payload)

        archive_path = state.REPO_ROOT / archive_rel
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_text(canonical_json_text(normalized), encoding="utf-8")

        if delta_path and delta_path.exists():
            delta_payload = safe_load_json(delta_path)
            if not isinstance(delta_payload, Mapping):
                raise ValueError(f"Invalid synth_seed delta: {state.rel(delta_path)}")
            ok, messages = apply_synth_seed_delta(
                state.REPO_ROOT,
                delta_payload,
                allow_pending_validation=True,
            )
            if not ok:
                return emit_json_with_code(
                    {
                        **payload,
                        "status": "delta_failed",
                        "errors": messages,
                    },
                    1,
                )

        updated_payload = safe_load_json(synth_json_path)
        if not isinstance(updated_payload, dict):
            raise ValueError(f"Invalid synth_seed.json after assimilation update: {state.rel(synth_json_path)}")
        updated = normalize_synth_payload(updated_payload, phase_scaffold=scaffold_payload)
        if not isinstance(updated, dict):
            raise ValueError("Could not normalize updated synth_seed.json")
        now_iso = datetime.now(timezone.utc).isoformat()
        updated_meta = dict(updated.get("meta") or {})
        next_cycle = int(updated_meta.get("current_cycle") or scaffold_payload.get("current_cycle") or 0) + 1
        updated_meta["current_cycle"] = next_cycle
        updated_meta["updated_at"] = now_iso
        updated["meta"] = updated_meta
        if str(updated.get("authoring_status") or "").strip() == PENDING_SYNTH_AUTHORING:
            updated["authoring_status"] = "authored"
        updated_wave = dict(updated.get("current_wave") or {})
        continuation_payload_cache = safe_load_json(continuation_path) if continuation_path and continuation_path.exists() else None
        continuation_applied_status = False
        if continuation_path and continuation_path.exists():
            continuation_payload = continuation_payload_cache
            if isinstance(continuation_payload, Mapping):
                progress_state = dict(updated.get("progress_state") or {})
                last_outcome = str(
                    continuation_payload.get("routing_outcome")
                    or continuation_payload.get("last_wave_outcome")
                    or continuation_payload.get("status")
                    or ""
                ).strip()
                if last_outcome:
                    progress_state["last_wave_outcome"] = last_outcome
                current_focus = str(
                    continuation_payload.get("current_focus")
                    or continuation_payload.get("next_focus")
                    or ""
                ).strip()
                if current_focus:
                    progress_state["current_focus"] = current_focus
                if progress_state:
                    updated["progress_state"] = progress_state
                next_step_posture = str(
                    continuation_payload.get("next_step_posture")
                    or continuation_payload.get("summary")
                    or ""
                ).strip()
                if next_step_posture:
                    updated["next_step_posture"] = next_step_posture
                recommended_next_wave = (
                    continuation_payload.get("recommended_next_wave")
                    if isinstance(continuation_payload.get("recommended_next_wave"), Mapping)
                    else None
                )
                if recommended_next_wave:
                    normalized_next = normalize_synth_payload(
                        {
                            **updated,
                            "current_wave": recommended_next_wave,
                        },
                        phase_scaffold=scaffold_payload,
                    )
                    if not isinstance(normalized_next, dict) or not isinstance(normalized_next.get("current_wave"), Mapping):
                        raise ValueError("Could not normalize recommended_next_wave during assimilation.")
                    updated["current_wave"] = dict(normalized_next.get("current_wave") or {})
                    continuation_applied_status = True
                elif updated_wave:
                    decision = str(continuation_payload.get("decision") or "").strip()
                    if decision:
                        updated_wave["status"] = decision
                        updated["current_wave"] = updated_wave
                        continuation_applied_status = True
        if (
            isinstance(updated.get("current_wave"), Mapping)
            and (not isinstance(continuation_payload_cache, Mapping) or not continuation_applied_status)
        ):
            updated_wave = dict(updated.get("current_wave") or {})
            if str(updated_wave.get("status") or "").strip() in {"", str(current_wave.get("status") or "").strip(), "planned", "in_progress"}:
                updated_wave["status"] = "assimilated"
                updated["current_wave"] = updated_wave

        errors = validate_synth_seed_payload(updated, phase_scaffold=scaffold_payload, allow_pending=True)
        if errors:
            return emit_json_with_code(
                {
                    **payload,
                    "status": "validation_failed",
                    "errors": errors,
                },
                1,
            )

        synth_markdown = render_synth_seed_markdown(
            updated,
            phase_scaffold_path=state.rel(scaffold_path),
            synth_seed_json_path=state.rel(synth_json_path),
        )
        updated_scaffold = dict(scaffold_payload)
        updated_scaffold["current_cycle"] = next_cycle
        updated_scaffold["updated_at"] = now_iso
        if str(updated_scaffold.get("authoring_status") or "").strip() == PENDING_SYNTH_AUTHORING:
            updated_scaffold["authoring_status"] = SYNCED_SYNTH_AUTHORING
        updated_ledger = dict(meta_ledger)
        final_entry = _wave_ledger_entry(
            phase_entry=phase_entry,
            wave=updated.get("current_wave") if isinstance(updated.get("current_wave"), Mapping) else current_wave,
            normalized_synth=updated,
            archived_synth_path=archive_rel,
            delta_path=delta_rel,
            continuation_summary_path=continuation_rel,
            files_touched=files_touched,
            legacy_cycle_index=int((normalized.get("meta") or {}).get("current_cycle") or 0),
        )
        updated_ledger["entries"] = [*ledger_entries, final_entry]

        synth_json_path.write_text(canonical_json_text(updated), encoding="utf-8")
        synth_markdown_path.write_text(synth_markdown, encoding="utf-8")
        meta_ledger_path.write_text(canonical_json_text(updated_ledger), encoding="utf-8")
        scaffold_path.write_text(canonical_json_text(updated_scaffold), encoding="utf-8")
        resume_writes = _write_phase_resume_bundle(_build_phase_resume_bundle(phase_entry))

        return emit_json(
            {
                **payload,
                "status": "assimilated",
                "wave": {
                    **dict(payload.get("wave") or {}),
                    "status": updated.get("current_wave", {}).get("status") if isinstance(updated.get("current_wave"), Mapping) else "assimilated",
                },
                "ledger_entry": final_entry,
                "resume_writes": resume_writes,
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_phase_resume(
    phase_token: str | None = None,
    *,
    live: bool = False,
    advance: bool = False,
    force: bool = False,
) -> int:
    """[ACTION]
    - Teleology: Materialize one phase-native controller resume surface for a synth-first subphase so unfinished waves can be resumed from disk instead of recovered ad hoc from chat.
    - Mechanism: Resolve the phase, classify its latest closeout/runtime state, compile a controller bootstrap packet plus pipeline resume/attention artifacts, optionally persist them beside the phase, and optionally execute the recommended next lifecycle edge.
    - Guarantee: Returns a preview/live payload with the lifecycle stage, next action, compression summary, write targets, and optional downstream lifecycle result.
    - Fails: Returns 1 when the phase or its synth/scaffold/meta-ledger artifacts are invalid.
    - When-needed: Open when a subphase is unfinished, has a detached observe gap, or needs a deterministic closeout-aware resume packet similar to mission launch.
    - Escalates-to: system/lib/continuation_packet.py; system/lib/kernel/commands/navigate.py::cmd_phase_assimilate; system/lib/kernel/commands/navigate.py::cmd_close_phase
    - Navigation-group: kernel_lib
    """
    try:
        if advance and not live:
            raise ValueError("--phase-resume --advance requires --live.")
        _navigator, phase_entry = _resolve_phase_entry_for_lifecycle(phase_token)
        bundle = _build_phase_resume_bundle(phase_entry)
        payload = dict(bundle.get("public_payload") or {})
        if not live:
            return emit_json(payload)

        writes = _write_phase_resume_bundle(bundle)
        if advance:
            next_action = dict(payload.get("next_action") or {})
            action_code, action_payload, action_stdout = _run_phase_resume_next_action(
                phase_token=phase_token,
                next_action=next_action,
                force=force,
            )
            response = {
                **payload,
                "mode": "live",
                "status": "advance_completed" if action_code == 0 else "advance_failed",
                "writes": writes,
                "advanced_action": next_action,
                "advance_result": action_payload,
            }
            if action_code != 0 and action_payload is None and action_stdout:
                response["advance_stdout"] = action_stdout
            return emit_json_with_code(response, action_code)
        return emit_json(
            {
                **payload,
                "mode": "live",
                "status": "resume_artifacts_written",
                "writes": writes,
            }
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_closeout_audit(limit: int = 10) -> int:
    """[ACTION]
    - Teleology: Audit detached observe-session closeout state across phases so finished sessions that still need synth evolution, assimilation, or recovery stop being invisible.
    - Mechanism: Rank the latest session candidate per phase, compare its lifecycle stage to the phase's current wave and assimilation surfaces, and emit per-phase closeout recommendations.
    - Guarantee: Returns 0 after emitting a deterministic audit payload.
    - Fails: Returns 1 only when the requested limit is invalid.
    - When-needed: Open when detached subphase runs may have completed or failed but phase cards still look active or unclosed.
    - Escalates-to: system/lib/observe_sessions.py; system/lib/phase_harbor.py; system/lib/kernel/commands/navigate.py::cmd_phase_assimilate
    """
    if limit < 0:
        print("ERROR: --closeout-audit limit must be >= 0", file=sys.stderr)
        return 1
    payload = _build_closeout_audit_payload(limit=limit)
    try:
        _, cache_status = _refresh_pulse_closeout_audit_cache(force_refresh=True)
        payload["command_node_cache"] = {"pulse_closeout_audit_quick": cache_status}
    except Exception as exc:  # pragma: no cover - audit output should survive cache skew
        payload["command_node_cache"] = {
            "pulse_closeout_audit_quick": {
                "status": "refresh_failed",
                "reason": "pulse_closeout_audit_cache_refresh_failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:240],
            }
        }
    return emit_json(payload)


def cmd_phase_harbor(phase_token: str | None = None, *, live: bool = False) -> int:
    """
    [ACTION]
    - Teleology: Inspect or bootstrap the JSON-first phase harbor artifacts for a given phase.
    - Guarantee: Returns 0 after emitting the harbor navigation result; with `--live` also writes missing harbor artifacts to disk.
    - Fails: Returns 1 when the phase token cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_phase_harbor(phase_token)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not live:
        return emit_navigation(result)

    phase_payload = result.payload.get("phase") if isinstance(result.payload.get("phase"), dict) else {}
    phase_ref = (
        phase_payload.get("phase_id")
        or phase_payload.get("phase_number")
        or phase_payload.get("phase_dir")
        or ""
    )
    try:
        phase_entry = navigator._resolve_phase_entry(str(phase_ref or phase_token or "").strip() or None)
        bootstrap = bootstrap_phase_harbor(state.REPO_ROOT, phase_entry, phase_entries=navigator.phase_entries, live=True)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    updated_payload = dict(result.payload)
    updated_payload["bootstrap"] = {
        **(
            result.payload.get("bootstrap")
            if isinstance(result.payload.get("bootstrap"), dict)
            else {}
        ),
        "status": bootstrap.get("status"),
        "writes": bootstrap.get("writes"),
    }
    updated_result = NavigationResult(
        kind=result.kind,
        query=result.query,
        payload=updated_payload,
        live_sources=result.live_sources,
        derived_sources=result.derived_sources,
        suggested_next=[
            {
                "command": f"python3 kernel.py --phase-deposit {shlex.quote(str(phase_ref))}",
                "reason": "Compile the first typed deposit packet now that the harbor artifacts exist on disk.",
            },
            *result.suggested_next,
        ],
        warnings=result.warnings,
        compact_hints=result.compact_hints,
        derived_required=result.derived_required,
    )
    return emit_navigation(updated_result)


def cmd_phase_deposit(phase_token: str | None = None, *, write_packet_to: str | None = None) -> int:
    """
    [ACTION]
    - Teleology: Compile and write the typed deposit packet from the active phase's raw_seed and synth_seed surfaces.
    - Guarantee: Returns 0 after writing the deposit packet to disk and emitting the updated navigation result.
    - Fails: Returns 1 when the phase token is unresolvable, the write path escapes the repo, or the builder returns no packet.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_phase_deposit(phase_token, write_packet_to=write_packet_to)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    write_info = result.payload.get("write_packet") if isinstance(result.payload.get("write_packet"), dict) else {}
    default_path = str(write_info.get("path") or "").strip()
    try:
        target_path = _resolve_write_packet_path(write_packet_to or default_path)
    except ValueError:
        print(f"ERROR: write path must remain inside repo: {write_packet_to or default_path}", file=sys.stderr)
        return 1

    packet = result.payload.get("deposit_packet")
    if not isinstance(packet, dict):
        print("ERROR: phase deposit builder did not return a valid packet payload", file=sys.stderr)
        return 1

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    updated_payload = dict(result.payload)
    updated_payload["write_packet"] = {
        **write_info,
        "path": state.rel(target_path),
        "written": True,
    }
    response_path = str(write_info.get("default_response_path") or "").strip()
    updated_result = NavigationResult(
        kind=result.kind,
        query=result.query,
        payload=updated_payload,
        live_sources=result.live_sources,
        derived_sources=result.derived_sources,
        suggested_next=[
            {
                "command": f"python3 kernel.py --ingest-phase-deposit {shlex.quote(response_path)}",
                "reason": "Preview how the typed deposit response would land on synth_seed/reference_ledger/meta_ledger.",
            },
            *result.suggested_next,
        ],
        warnings=result.warnings,
        compact_hints=result.compact_hints,
        derived_required=result.derived_required,
    )
    return emit_navigation(updated_result)


def cmd_phase_dock(
    phase_token: str | None = None,
    *,
    operation: str = "extract_subphase_seed",
    session_ref: str | None = None,
    consumer: str = "bridge",
    bridge_provider: str | None = None,
    bridge_route: str | None = None,
    bridge_timeout_s: float = 0.0,
    live: bool = False,
    write_packet_to: str | None = None,
    write_dock_to: str | None = None,
    resume: bool = True,
) -> int:
    """
    [ACTION]
    - Teleology: Compile a bridge-ready dock packet for a phase, optionally dispatch it to the bridge, and land the typed response.
    - Guarantee: Returns 0 after emitting the dock payload.
    - Fails: Returns 1 when the phase token is unresolvable or the session manifest is missing for evolve operations.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        phase_entry = navigator._resolve_phase_entry(phase_token)
        session_manifest: str | None = None
        if operation == "evolve_subphase_seed":
            manifest_path = _resolve_phase_session_manifest(phase_entry, ref=session_ref)
            if manifest_path is None or not manifest_path.exists():
                print(
                    f"ERROR: Observe session manifest not found for {session_ref or 'latest'} and phase {phase_token or phase_entry.get('phase_id')}.",
                    file=sys.stderr,
                )
                return 1
            session_manifest = state.rel(manifest_path)
        payload = run_phase_dock(
            state.REPO_ROOT,
            phase_entry,
            phase_entries=navigator.phase_entries,
            operation=operation,
            session_manifest=session_manifest,
            consumer=consumer,
            bridge_provider=bridge_provider,
            bridge_route=bridge_route,
            bridge_timeout_s=bridge_timeout_s,
            live=live,
            write_packet_to=write_packet_to,
            write_dock_to=write_dock_to,
            resume=resume,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json_with_code(payload, 0)


def cmd_phase_begin(
    phase_token: str | None = None,
    *,
    operation: str = "extract_subphase_seed",
    session_ref: str | None = None,
    consumer: str = "bridge",
    bridge_provider: str | None = None,
    bridge_route: str | None = None,
    bridge_timeout_s: float = 0.0,
    live: bool = False,
    write_packet_to: str | None = None,
    write_dock_to: str | None = None,
    resume: bool = True,
    run_bridge_preflight: bool = False,
) -> int:
    """
    [ACTION]
    - Teleology: Preflight the next dock/evolve loop by rebuilding packets, inspecting reuse, and reporting readiness without dispatching.
    - Guarantee: Returns 0 when status is ready or warning; returns 1 when status is blocked.
    - Fails: Returns 1 when the phase token is unresolvable or the session manifest is missing for evolve operations.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        phase_entry = navigator._resolve_phase_entry(phase_token)
        session_manifest: str | None = None
        if operation == "evolve_subphase_seed":
            manifest_path = _resolve_phase_session_manifest(phase_entry, ref=session_ref)
            if manifest_path is None or not manifest_path.exists():
                print(
                    f"ERROR: Observe session manifest not found for {session_ref or 'latest'} and phase {phase_token or phase_entry.get('phase_id')}.",
                    file=sys.stderr,
                )
                return 1
            session_manifest = state.rel(manifest_path)

        payload = preflight_phase_dock(
            state.REPO_ROOT,
            phase_entry,
            phase_entries=navigator.phase_entries,
            operation=operation,
            session_manifest=session_manifest,
            consumer=consumer,
            bridge_provider=bridge_provider,
            bridge_route=bridge_route,
            bridge_timeout_s=bridge_timeout_s,
            live=live,
            write_packet_to=write_packet_to,
            write_dock_to=write_dock_to,
            resume=resume,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    recommended = [dict(item) for item in payload.get("recommended", []) if isinstance(item, Mapping)]
    git_scope = _git_scope_summary(state.REPO_ROOT)
    recommended.append(
        {
            "id": "git_scope",
            "status": git_scope.get("status") or "warning",
            "detail": git_scope.get("detail"),
            "summary": git_scope.get("summary"),
            "sample_paths": git_scope.get("sample_paths"),
            "error": git_scope.get("error"),
            "exit_code": git_scope.get("exit_code"),
        }
    )

    bridge_preflight_item: dict[str, Any]
    bridge_preflight_payload: dict[str, Any] | None = None
    resolved_provider = str(bridge_provider or "").strip() or "chatgpt"
    if consumer != "bridge":
        bridge_preflight_item = {
            "id": "bridge_preflight",
            "status": "not_applicable",
            "detail": "Bridge preflight is not relevant when the selected consumer is manual.",
        }
    elif run_bridge_preflight:
        bridge_preflight_payload = _kernel_run_bridge_preflight(bridge_provider, fast=True)
        exit_code = int(bridge_preflight_payload.get("exit_code") or 0)
        bridge_preflight_item = {
            "id": "bridge_preflight",
            "status": "ready" if exit_code == 0 else "warning",
            "detail": (
                f"Fast bridge preflight passed for {bridge_preflight_payload.get('provider') or resolved_provider}."
                if exit_code == 0
                else f"Fast bridge preflight failed for {bridge_preflight_payload.get('provider') or resolved_provider}."
            ),
            "provider": bridge_preflight_payload.get("provider"),
            "exit_code": exit_code,
            "command": str(bridge_preflight_payload.get("command") or "").strip() or None,
        }
    else:
        bridge_preflight_item = {
            "id": "bridge_preflight",
            "status": "not_run",
            "detail": "Bridge preflight did not run in this begin pass.",
            "command": f"python3 kernel.py --bridge-preflight --provider {resolved_provider}",
        }
    recommended.append(bridge_preflight_item)

    phase_ref = _phase_command_token(phase_entry, phase_token)
    follow_up = [
        {
            "command": _phase_dock_command(
                phase_ref,
                operation=operation,
                session_ref=session_ref,
                consumer=consumer,
                bridge_provider=bridge_provider,
                bridge_route=bridge_route,
                bridge_timeout_s=bridge_timeout_s,
                live=live,
                resume=resume,
                write_packet_to=write_packet_to,
                write_dock_to=write_dock_to,
            ),
            "reason": "Run the exact dock/evolve loop this begin preflight just validated.",
        }
    ]
    if consumer == "bridge":
        follow_up.append(
            {
                "command": _phase_dock_command(
                    phase_ref,
                    operation=operation,
                    session_ref=session_ref,
                    consumer=consumer,
                    bridge_provider=bridge_provider,
                    bridge_route=bridge_route,
                    bridge_timeout_s=bridge_timeout_s,
                    live=live,
                    resume=False,
                    write_packet_to=write_packet_to,
                    write_dock_to=write_dock_to,
                ),
                "reason": "Force a fresh bridge answer and ignore any reusable response artifacts from prior runs.",
            }
        )
    follow_up.append(
        {
            "command": "./venv/bin/python -m pytest system/server/tests/test_phase_harbor.py -q",
            "reason": "Smoke the harbor ingest path before a new live landing if that seam changed recently.",
        }
    )
    if consumer == "bridge":
        follow_up.append(
            {
                "command": f"python3 kernel.py --bridge-preflight --provider {resolved_provider}",
                "reason": "Warm the selected provider tab and verify bridge selectors before live dispatch.",
            }
        )

    payload["recommended"] = recommended
    payload["bridge_preflight"] = bridge_preflight_payload
    payload["git_scope"] = git_scope
    payload["follow_up"] = follow_up
    status_items = [dict(item) for item in payload.get("must_have", []) if isinstance(item, Mapping)]
    if run_bridge_preflight:
        status_items.append(dict(bridge_preflight_item))
    payload["status"] = _phase_begin_status(status_items)
    return emit_json_with_code(payload, 0 if payload["status"] != "blocked" else 1)


def cmd_ingest_phase_deposit(response_path: str, *, live: bool = False) -> int:
    """
    [ACTION]
    - Teleology: Preview or apply a typed phase deposit response onto synth_seed, reference_ledger, and meta_ledger.
    - Guarantee: Returns 0 after emitting the ingest result payload.
    - Fails: Returns 1 when the response path is invalid or the ingest operation fails.
    """
    try:
        payload = ingest_phase_deposit_response(state.REPO_ROOT, response_path, live=live)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_json_with_code(payload, 0)


def cmd_phase_observe(
    phase_token: str | None = None,
    *,
    write_plan_to: str | None = None,
    shard_packet_request: Mapping[str, Any] | None = None,
) -> int:
    """[ACTION]
    - Teleology: Compile the active seed surface into a runnable grouped observe plan and optionally materialize shard-selected packet context into that plan in one move.
    - Mechanism: Delegate to exact token `build_phase_observe` via `KernelNavigation.build_phase_observe`, validate the returned plan, write it to disk, and emit launch-oriented follow-up commands.
    - Guarantee: Returns 0 after writing and emitting a valid observe plan.
    - Fails: Returns 1 when the phase token or write path is invalid, the builder returns no plan, or validation fails.
    - When-needed: Open when a phase-scoped task needs exact token `build_phase_observe` resolved to the canonical observe-plan compiler rather than drafting the JSON by hand.
    - Escalates-to: system/lib/kernel_nav_phase.py; system/lib/kernel/commands/observe.py::cmd_launch_observe
    - Navigation-group: kernel_lib
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_phase_observe(
            phase_token,
            write_plan_to=write_plan_to,
            shard_packet_request=shard_packet_request,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        target_path = _kernel_resolve_write_plan_path(write_plan_to)
    except ValueError:
        print(f"ERROR: write path must remain inside repo: {write_plan_to}", file=sys.stderr)
        return 1

    observe_plan = result.payload.get("observe_plan")
    if not isinstance(observe_plan, dict):
        print("ERROR: phase observe builder did not return a valid observe plan payload", file=sys.stderr)
        return 1

    errors, warnings = _kernel_validate_observe_payload(observe_plan)
    if errors:
        return emit_json_with_code(
            {
                "status": "invalid_phase_observe_plan",
                "path": state.rel(target_path),
                "errors": errors,
                "warnings": warnings,
                "plan": observe_plan,
            },
            1,
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(observe_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_payload = result.payload.get("write_plan") if isinstance(result.payload.get("write_plan"), dict) else {}
    updated_payload = dict(result.payload)
    updated_payload["write_plan"] = {
        **write_payload,
        "path": state.rel(target_path),
        "written": True,
        "warning_count": len(warnings),
        "warnings": warnings,
    }
    updated_result = NavigationResult(
        kind=result.kind,
        query=result.query,
        payload=updated_payload,
        live_sources=result.live_sources,
        derived_sources=result.derived_sources,
        suggested_next=[
            {
                "command": f"python3 kernel.py --launch-observe --plan {shlex.quote(state.rel(target_path))} --bridge --provider gemini --bridge-workers auto --launch-profile {_kernel_observe_launch_profile_default()} --detach --no-sticky-dump-dir",
                "reason": "Dispatch the grouped observe plan compiled from the active seed surface.",
            },
            {
                "command": "python3 kernel.py --read-observe latest",
                "reason": "Recover the typed result note, synthesis artifact, and next-step contract after dispatch.",
            },
        ],
        warnings=result.warnings,
        compact_hints=result.compact_hints,
        derived_required=result.derived_required,
    )
    return emit_navigation(updated_result)


def cmd_campaign_loop(
    phase_token: str | None,
    *,
    rounds: int = 1,
    bridge_enabled: bool,
    bridge_provider: str | None,
    bridge_max_chars: int,
    bridge_timeout_s: float,
    bridge_workers: Any,
    launch_profile: str | None = None,
    bootstrap_via_bridge: bool = False,
    live: bool = False,
) -> int:
    """
    [ACTION]
    - Teleology: Run one or more observe-plan compile-and-dispatch rounds for a phase in a tight campaign loop.
    - Guarantee: Returns 0 after completing all rounds or emitting a dry-run summary; returns 1 on unrecoverable errors.
    - Fails: Returns 1 when the phase token is unresolvable or the observe plan is invalid.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        phase_entry = navigator._resolve_phase_entry(phase_token)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rounds = max(1, int(rounds or 1))
    harbor_preview = bootstrap_phase_harbor(state.REPO_ROOT, phase_entry, phase_entries=navigator.phase_entries, live=live)
    if not live:
        try:
            observe_plan, plan_path, plan_meta = _compile_phase_observe_plan_payload(phase_token)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        phase_ref = str(phase_entry.get("phase_id") or phase_entry.get("phase_number") or phase_token or "").strip()
        synth_artifact = harbor_preview.get("harbor", {}).get("artifacts", {}).get("synth_seed", {}) if isinstance(harbor_preview.get("harbor"), dict) else {}
        synth_missing = not bool(synth_artifact.get("exists"))
        synth_is_bootstrap = str(synth_artifact.get("version") or "").strip() in {"", "synth_C0"} and int(synth_artifact.get("idea_count") or 0) == 0
        return emit_json(
            {
                "status": "preview_ready",
                "phase": {
                    "phase_id": phase_entry.get("phase_id"),
                    "phase_number": phase_entry.get("phase_number"),
                    "phase_title": phase_entry.get("phase_title"),
                    "phase_dir": phase_entry.get("phase_dir"),
                },
                "harbor_bootstrap": harbor_preview,
                "first_plan_path": state.rel(plan_path),
                "first_plan_runtime": _kernel_observe_runtime_kind(observe_plan),
                "first_plan_warning_count": len(plan_meta.get("warnings") or []),
                "rounds": rounds,
                "bootstrap_via_bridge": bootstrap_via_bridge or synth_missing or synth_is_bootstrap,
                "bridge_required": bool(bridge_enabled),
                "suggested_sequence": [
                    item
                    for item in [
                        (
                            f"python3 kernel.py --phase-dock {shlex.quote(phase_ref)} --dock-operation extract_subphase_seed --live"
                            if (bootstrap_via_bridge or synth_missing or synth_is_bootstrap)
                            else None
                        ),
                        f"python3 kernel.py --phase-observe {shlex.quote(phase_ref)}",
                        f"python3 kernel.py --launch-observe --plan {state.rel(plan_path)} --bridge --provider {bridge_provider or 'gemini'}",
                        "python3 kernel.py --read-session latest",
                        f"python3 kernel.py --phase-dock {shlex.quote(phase_ref)} --dock-operation evolve_subphase_seed --dock-session latest --live",
                    ]
                    if item
                ],
            }
        )

    if bridge_timeout_s <= 0:
        print("ERROR: --bridge-timeout-s must be > 0", file=sys.stderr)
        return 1

    synth_artifact = harbor_preview.get("harbor", {}).get("artifacts", {}).get("synth_seed", {}) if isinstance(harbor_preview.get("harbor"), dict) else {}
    synth_missing = not bool(synth_artifact.get("exists"))
    synth_is_bootstrap = str(synth_artifact.get("version") or "").strip() in {"", "synth_C0"} and int(synth_artifact.get("idea_count") or 0) == 0
    seed_bootstrap_requested = bootstrap_via_bridge or synth_missing or synth_is_bootstrap
    if seed_bootstrap_requested and not bridge_enabled:
        print("ERROR: --campaign-loop needs --bridge when synth bootstrap is requested or the synth seed is still empty.", file=sys.stderr)
        return 1

    phase_ref = str(phase_entry.get("phase_id") or phase_entry.get("phase_number") or phase_token or "").strip()
    seed_bootstrap_receipt: dict[str, Any] | None = None
    if seed_bootstrap_requested:
        try:
            seed_bootstrap_receipt = run_phase_dock(
                state.REPO_ROOT,
                phase_entry,
                phase_entries=navigator.phase_entries,
                operation="extract_subphase_seed",
                consumer="bridge",
                bridge_provider=bridge_provider,
                bridge_timeout_s=bridge_timeout_s,
                live=True,
            )
        except ValueError as exc:
            print(f"ERROR: initial synth bootstrap failed: {exc}", file=sys.stderr)
            return 1

    round_receipts: list[dict[str, Any]] = []
    current_manifest_path: Path | None = None
    current_plan_path: Path | None = None
    current_plan_payload: dict[str, Any] | None = None
    for round_offset in range(rounds):
        try:
            if round_offset == 0:
                current_plan_payload, current_plan_path, plan_meta = _compile_phase_observe_plan_payload(
                    phase_token,
                    write_plan_to=PHASE_OBSERVE_DEFAULT_PLAN_PATH.as_posix(),
                )
            else:
                if current_manifest_path is None or not current_manifest_path.exists():
                    raise ValueError("campaign loop could not locate the prior session manifest for drafting the next pass")
                manifest_payload = _kernel_load_session_manifest_payload(current_manifest_path)
                if not isinstance(manifest_payload, dict):
                    raise ValueError(f"failed to read session manifest: {state.rel(current_manifest_path)}")
                target_path = PHASE_OBSERVE_DEFAULT_PLAN_PATH.with_name(f"{PHASE_OBSERVE_DEFAULT_PLAN_PATH.stem}_round_{round_offset + 1}.json")
                current_plan_payload, plan_meta = _write_next_pass_plan_payload(
                    current_manifest_path,
                    manifest_payload,
                    target_path=target_path,
                )
                current_plan_path = target_path
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        runtime_kind, summary = _run_observe_plan_sync(
            plan_path=current_plan_path,
            plan_payload=current_plan_payload,
            bridge_enabled=bridge_enabled,
            bridge_provider=bridge_provider,
            bridge_max_chars=bridge_max_chars,
            bridge_timeout_s=bridge_timeout_s,
            bridge_workers=bridge_workers,
            launch_profile=launch_profile,
        )
        manifest_rel = str(summary.get("session_manifest") or "").strip() if isinstance(summary, dict) else ""
        current_manifest_path = (state.REPO_ROOT / manifest_rel).resolve() if manifest_rel else None
        synth_evolution_receipt: dict[str, Any] | None = None
        if runtime_kind == "observe_session" and current_manifest_path is not None and current_manifest_path.exists() and bridge_enabled:
            try:
                synth_evolution_receipt = run_phase_dock(
                    state.REPO_ROOT,
                    phase_entry,
                    phase_entries=navigator.phase_entries,
                    operation="evolve_subphase_seed",
                    session_manifest=state.rel(current_manifest_path),
                    consumer="bridge",
                    bridge_provider=bridge_provider,
                    bridge_timeout_s=bridge_timeout_s,
                    live=True,
                )
            except ValueError as exc:
                synth_evolution_receipt = {
                    "status": "failure",
                    "reason": str(exc),
                    "phase": phase_ref,
                    "session_manifest": state.rel(current_manifest_path),
                }
        round_receipts.append(
            {
                "round": round_offset + 1,
                "plan_path": state.rel(current_plan_path) if current_plan_path else None,
                "runtime_kind": runtime_kind,
                "plan_warning_count": len(plan_meta.get("warnings") or []),
                "summary": summary,
                "synth_evolution": synth_evolution_receipt or {
                    "status": "skipped",
                    "reason": "bridge_disabled_or_non_session_runtime",
                },
            }
        )
        if runtime_kind != "observe_session" and rounds > 1:
            print("ERROR: campaign loop can only draft follow-on rounds from observe-session runs.", file=sys.stderr)
            return 1
        if current_manifest_path is None and round_offset + 1 < rounds:
            print("ERROR: campaign loop expected a session manifest for the next round but none was produced.", file=sys.stderr)
            return 1

    return emit_json(
        {
            "status": "success",
            "phase": {
                "phase_id": phase_entry.get("phase_id"),
                "phase_number": phase_entry.get("phase_number"),
                "phase_title": phase_entry.get("phase_title"),
                "phase_dir": phase_entry.get("phase_dir"),
            },
            "harbor_bootstrap": harbor_preview,
            "seed_bootstrap": seed_bootstrap_receipt or {
                "status": "skipped",
                "reason": "synth_seed_already_materialized",
            },
            "rounds_requested": rounds,
            "rounds_completed": len(round_receipts),
            "rounds": round_receipts,
        }
    )


def cmd_plan_batch(batch_id: str, plan_id: str | None = None) -> int:
    """
    [ACTION]
    - Teleology: Emit one manifest batch with its file targets, dependencies, and acceptance commands.
    - Guarantee: Returns 0 after emitting the plan-batch navigation result.
    - Fails: Returns 1 when the batch id or plan id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_plan_batch(batch_id, plan_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_plan_sync(plan_id: str | None = None) -> int:
    """
    [ACTION]
    - Teleology: Emit drift checks between the active plan note and its companion manifest.
    - Guarantee: Returns 0 after emitting the plan-sync navigation result.
    - Fails: Returns 1 when the plan id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_plan_sync(plan_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_impact(file_token: str, plan_id: str | None = None) -> int:
    """
    [ACTION]
    - Teleology: Emit plan ownership, doctrine claims, and node touchpoints for a given file token.
    - Guarantee: Returns 0 after emitting the impact navigation result.
    - Fails: Returns 1 when the file token or plan id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_impact(file_token, plan_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_compile_batch(batch_id: str, plan_id: str | None = None) -> int:
    """
    [ACTION]
    - Teleology: Emit semantic compilation for one manifest batch without including raw file bodies.
    - Guarantee: Returns 0 after emitting the compile-batch navigation result.
    - Fails: Returns 1 when the batch id or plan id cannot be resolved.
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_compile_batch(batch_id, plan_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return emit_navigation(result)


def cmd_compile(paths: Sequence[str]) -> int:
    """[ACTION]
    - Teleology: Emit semantic compilation for one or more repo files or tokens.
    - Mechanism: Delegate to `KernelNavigation.build_compile_files` and emit the resulting compiled payload.
    - Guarantee: Returns 0 after emitting the compilation result.
    - Fails: Returns 1 when one of the requested paths or tokens cannot be compiled.
    - When-needed: Open when you know which files matter and need the semantic card instead of raw source reading.
    - Escalates-to: system/lib/kernel_navigation.py; system/lib/kernel_nav_lens.py
    """
    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        result = navigator.build_compile_files(list(paths))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    record_navigation_result(
        state.REPO_ROOT,
        event_kind="compile",
        query=" ".join(str(path) for path in paths),
        command="kernel.py --compile",
        payload=result.to_dict(state.KERNEL_VERSION, full=True),
    )
    return emit_navigation(result)


def cmd_verify(batch_id: str, plan_id: str | None = None) -> int:
    """[ACTION]
    - Teleology: Run the acceptance commands for one manifest batch.
    - Mechanism: Resolve the batch via `build_plan_batch`, execute its acceptance commands, and emit pass/fail JSON.
    - Guarantee: Returns 0 only when the batch verification passes.
    - Fails: Returns 1 when the batch cannot be resolved or one of its acceptance commands fails.
    - When-needed: Open when implementation work needs the canonical batch acceptance runner before claiming completion.
    - Escalates-to: system/lib/kernel_nav_phase.py; codex/doctrine/skills/kernel/apply.md
    """
    import subprocess

    navigator = KernelNavigation(state.REPO_ROOT)
    try:
        batch_result = navigator.build_plan_batch(batch_id, plan_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = batch_result.payload
    plan = payload.get("plan", {}) if isinstance(payload, dict) else {}
    batch = payload.get("batch", {}) if isinstance(payload, dict) else {}
    commands = batch.get("acceptance_commands", []) if isinstance(batch, dict) else []
    if not isinstance(commands, list):
        commands = []

    command_results: list[dict[str, object]] = []
    overall_passed = True
    for command in commands:
        executed_command = _rewrite_verify_command(str(command))
        proc = subprocess.run(
            executed_command,
            cwd=state.REPO_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        passed = proc.returncode == 0
        overall_passed = overall_passed and passed
        command_results.append(
            {
                "command": str(command),
                "executed_command": executed_command,
                "returncode": proc.returncode,
                "passed": passed,
                "stdout": _kernel_truncate_text(proc.stdout or ""),
                "stderr": _kernel_truncate_text(proc.stderr or ""),
            }
        )

    warnings: list[str] = []
    if not commands:
        warnings.append("No acceptance commands declared for this batch.")
        overall_passed = False

    verify_payload = {
        "kind": "kernel.plan.verify",
        "kernel_version": state.KERNEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query": {
            "command": "verify",
            "plan_id": plan.get("plan_id"),
            "batch_id": batch.get("id"),
        },
        "payload": {
            "plan": plan,
            "batch": {
                "id": batch.get("id"),
                "name": batch.get("name"),
                "status": batch.get("status"),
            },
            "passed": overall_passed,
            "command_count": len(commands),
            "commands": command_results,
        },
        "warnings": warnings,
    }
    emit_json(verify_payload)
    return 0 if overall_passed else 1
