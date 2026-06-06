"""Coverage enforcement matrix for first-contact navigation.

This is a read-only composer over existing surfaces. It does not define new
artifact authority; it makes the current coverage-first invariant measurable
per artifact kind by joining Kind Atlas rows with quick Navigation Metabolism
behavior/debt pressure, then names any additional standard type-plane route
surfaces that resolve outside the matrix row set.
"""
from __future__ import annotations

import json
import shlex
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.kind_atlas import build_kind_atlas
from system.lib.navigation_metabolism_ledger import build_navigation_metabolism_ledger
from system.lib.navigation_surface_contracts import ATLAS_PROJECTION, CONTROL_ENTRY, DRILLDOWN, ENTRY_REPLACEMENT


DEFAULT_QUERY = "coverage-first navigation enforcement"
STANDARD_TYPE_PLANE = Path("codex/standards/std_standard_type_plane.json")
SLOW_PHASE_WARN_MS = 2500
HIGH_CARDINALITY_THRESHOLD = 80

_PROCESS_KIND_MAP: dict[str, tuple[str, ...]] = {
    "keyword_search_before_cluster_surface": ("skills",),
    "skill_find_first_contact": ("skills",),
    "paper_module_skip": ("paper_modules",),
    "grep_before_kernel": ("*global*",),
    "deep_without_ladder": ("*global*",),
    "cold_boot_missing_info": ("*entrypoint*",),
    "command_loop": ("*global*",),
    "agent_stalled_mid_session": ("*global*",),
    "slow_action_shape": ("*global*",),
}

_EXACT_LOOKUP_ROUTE_BY_KIND: dict[str, str] = {
    "skills": "skill_find",
    "paper_modules": "paper_lattice",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any) -> int:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except TypeError:
        text = json.dumps(str(value), ensure_ascii=False)
    return len(text.encode("utf-8"))


def _elapsed_ms(start: float) -> int:
    return max(0, int(round((time.perf_counter() - start) * 1000)))


def _latency_profile(stage_timings_ms: Mapping[str, int], total_ms: int) -> dict[str, Any]:
    slow_phases = [
        {"phase": phase, "ms": int(ms)}
        for phase, ms in stage_timings_ms.items()
        if int(ms) >= SLOW_PHASE_WARN_MS
    ]
    return {
        "schema_version": "coverage_matrix_latency_profile_v0",
        "status": "slow_phase_detected" if slow_phases else "ok",
        "total_ms": int(total_ms),
        "phase_count": len(stage_timings_ms),
        "slow_phase_count": len(slow_phases),
        "slow_phase_warn_ms": SLOW_PHASE_WARN_MS,
        "slow_phases": slow_phases[:8],
        "privacy": "phase_names_wall_time_only_no_command_output_bodies",
        "authority": "in_process_wall_clock_for_this_read_only_invocation",
    }


def _compact_debt(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "debt_id",
        "debt_class",
        "priority",
        "title",
        "repair_class",
        "source_surface",
        "route_id",
        "artifact_kind",
        "anti_pattern",
        "better_first_surface",
        "safe_alternative",
        "library_reference_only",
        "compatibility_behavior",
        "retired_by_navigation_mechanism_observation",
        "navigation_mechanism_claim_id",
        "preferred_next",
        "process_bottleneck_drilldown",
    )
    compact = {key: row.get(key) for key in keys if row.get(key) not in (None, "", [], {})}
    if row.get("repair_hints"):
        compact["repair_hints"] = [
            dict(item)
            for item in list(row.get("repair_hints") or [])[:2]
            if isinstance(item, Mapping)
        ]
    active_debt = _debt_is_active(row)
    compact["active_debt"] = active_debt
    compact["debt_lifecycle_state"] = _debt_lifecycle_state(row)
    if row.get("advisory_only") is True or not active_debt:
        compact["advisory_only"] = True
    return compact


def _debt_is_active(row: Mapping[str, Any]) -> bool:
    return row.get("active_debt") is not False and row.get("advisory_only") is not True


def _debt_lifecycle_state(row: Mapping[str, Any]) -> str:
    if row.get("retired_by_navigation_mechanism_observation") is True:
        return "retired_observed"
    if not _debt_is_active(row):
        return "advisory"
    return "active"


def _behavior_lifecycle_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    active_rows = [row for row in rows if _debt_lifecycle_state(row) == "active"]
    advisory_rows = [row for row in rows if _debt_lifecycle_state(row) != "active"]
    retired_rows = [
        row
        for row in rows
        if row.get("retired_by_navigation_mechanism_observation") is True
    ]
    return {
        "active_behavior_debt_count": len(active_rows),
        "advisory_behavior_debt_count": len(advisory_rows),
        "retired_by_navigation_mechanism_count": len(retired_rows),
        "active_behavior_debt_ids": [str(row.get("debt_id") or "") for row in active_rows[:5]],
        "advisory_behavior_debt_ids": [str(row.get("debt_id") or "") for row in advisory_rows[:5]],
        "retired_behavior_debt_ids": [str(row.get("debt_id") or "") for row in retired_rows],
        "rule": (
            "Observed navigation-mechanism repairs remain visible as advisory evidence, "
            "but active behavior routing should prefer rows where active_debt is true."
        ),
    }


def _behavior_rows_for_routing(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            0 if _debt_lifecycle_state(row) == "active" else 1,
            -int(row.get("priority") or 0),
            str(row.get("debt_id") or ""),
        ),
    )


def _row_matches_query(row: Mapping[str, Any], query: str) -> bool:
    query_text = str(query or "").lower()
    if not query_text:
        return False
    haystack = " ".join(
        str(row.get(key) or "").lower()
        for key in ("debt_id", "title", "repair_class", "source_surface", "anti_pattern", "route_id")
    )
    if not haystack:
        return False
    for value in (
        str(row.get("debt_id") or "").lower(),
        str(row.get("anti_pattern") or "").lower(),
    ):
        if value and value in query_text:
            return True
    terms = [
        term.strip()
        for term in query_text.replace(":", " ").replace("/", " ").replace("-", " ").split()
        if len(term.strip()) > 2 and term.strip() not in {"the", "and", "for", "with", "owner", "route"}
    ]
    return bool(terms) and all(term in haystack for term in terms)


def _query_names_specific_process_debt(query: str) -> bool:
    query_text = str(query or "").lower()
    return any(
        marker in query_text
        for marker in (
            "anti_pattern_",
            "slow_action_shape",
            "bash_",
            "behavior:process_audit:",
        )
    )


def _row_is_throughput_debt(row: Mapping[str, Any]) -> bool:
    return (
        str(row.get("repair_class") or "") == "action_kind_throughput_repair"
        or str(row.get("anti_pattern") or "") == "slow_action_shape"
        or str(row.get("owner_surface") or "") == "process_bottlenecks"
    )


def _throughput_action_kind(row: Mapping[str, Any]) -> str:
    action_kind = str(row.get("action_kind") or "").strip()
    if action_kind:
        return action_kind
    debt_id = str(row.get("debt_id") or "").strip()
    prefix = "behavior:process_audit:slow_action_shape:"
    if debt_id.startswith(prefix):
        return debt_id.removeprefix(prefix).strip()
    return ""


def _query_prefers_throughput_debt(query: str) -> bool:
    query_text = str(query or "").lower()
    if not query_text:
        return False
    markers = {
        "action kind",
        "action_kind",
        "bash_grep",
        "bottleneck",
        "command profile",
        "command-profile",
        "command_profile",
        "context economy",
        "latency",
        "p95",
        "performance",
        "process audit",
        "process-audit",
        "process_audit",
        "process bottleneck",
        "process-bottleneck",
        "process_bottleneck",
        "route cost",
        "slow",
        "slow_action_shape",
        "speed",
        "throughput",
        "validation economy",
    }
    return any(marker in query_text for marker in markers)


def _query_prefers_doctrine_routing_weave(query: str) -> bool:
    query_text = str(query or "").lower()
    if not query_text:
        return False
    markers = {
        "axiom",
        "bidirectional",
        "cognitive operator",
        "concept",
        "doctrine route",
        "doctrine routing",
        "doctrine weave",
        "mechanism",
        "paper module",
        "principle",
        "route graph",
        "routing weave",
        "substrate route",
        "weave",
    }
    return any(marker in query_text for marker in markers)


def _process_audit_source_freshness(metabolism: Mapping[str, Any]) -> dict[str, Any]:
    quality_signal = metabolism.get("quality_signal")
    if not isinstance(quality_signal, Mapping):
        return {}
    source_freshness = quality_signal.get("source_freshness")
    if not isinstance(source_freshness, Mapping):
        return {}
    process_cache = source_freshness.get("process_audit_cache")
    if not isinstance(process_cache, Mapping):
        return {}
    return {
        str(key): value
        for key, value in process_cache.items()
        if key and value not in (None, "", [], {})
    }


def _process_audit_fast_path(
    rows: Sequence[Mapping[str, Any]],
    *,
    query: str = "",
    source_freshness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    freshness = dict(source_freshness or {})
    active_rows = [row for row in rows if _debt_lifecycle_state(row) == "active"]
    if not active_rows:
        return {
            "status": "no_active_behavior_debt",
            "rule": (
                "No active process-audit behavior debt is present; use top_behavior_rows as "
                "advisory evidence and keep the matrix rows as the audit surface."
            ),
            "next_commands": [],
        }

    matching_rows = [row for row in active_rows if _row_matches_query(row, query)]
    throughput_rows = [row for row in active_rows if _row_is_throughput_debt(row)]
    selection_reason = "query_matched_active_debt"
    if matching_rows:
        top = matching_rows[0]
    elif _query_names_specific_process_debt(query):
        inactive_matches = [
            row
            for row in rows
            if _debt_lifecycle_state(row) != "active" and _row_matches_query(row, query)
        ]
        return {
            "status": "matched_behavior_debt_not_active",
            "debt": _compact_debt(inactive_matches[0]) if inactive_matches else None,
            "rule": (
                "The query names a specific process-audit debt, but no active matching "
                "behavior debt is present; keep the matrix rows visible instead of "
                "routing to an unrelated active fast path."
            ),
            "next_commands": [],
        }
    elif throughput_rows and _query_prefers_throughput_debt(query):
        top = throughput_rows[0]
        selection_reason = "throughput_query_preferred_action_kind_debt"
    else:
        top = active_rows[0]
        selection_reason = "top_active_behavior_debt"
    alternate_active_debt_ids = [
        str(row.get("debt_id") or "")
        for row in active_rows
        if row is not top and row.get("debt_id")
    ]
    if not freshness and isinstance(top.get("source_freshness"), Mapping):
        freshness = dict(top.get("source_freshness") or {})
    boundary = top.get("source_projection_boundary") or {}
    if not isinstance(boundary, Mapping):
        boundary = {}
    owner_card_command = str(boundary.get("owner_card_route") or "").strip()
    owner_status_command = str(top.get("owner_status_command") or boundary.get("owner_status_route") or "").strip()
    authoritative_command = str(
        top.get("authoritative_decision_command") or boundary.get("authoritative_decision_route") or ""
    ).strip()
    action_kind_quote_command = ""
    if _row_is_throughput_debt(top):
        action_kind = _throughput_action_kind(top)
        action_kind_quote_command = "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage"
        if action_kind:
            action_kind_quote_command += f" --action-kind {shlex.quote(action_kind)}"
    next_commands: list[dict[str, str]] = []
    if owner_card_command:
        next_commands.append(
            {
                "command": owner_card_command,
                "surface_role": ATLAS_PROJECTION,
                "reason": "Open the stable owner card before scanning source or broad matrix rows.",
            }
        )
    if action_kind_quote_command:
        next_commands.append(
            {
                "command": action_kind_quote_command,
                "surface_role": CONTROL_ENTRY,
                "reason": "Use the cheap quote plane before paying a force-live process bottleneck refresh.",
            }
        )
    if authoritative_command:
        next_commands.append(
            {
                "command": authoritative_command,
                "surface_role": CONTROL_ENTRY,
                "reason": "Refresh the authoritative behavior-debt decision if the owner card is insufficient.",
            }
        )
    if owner_status_command and owner_status_command not in {item["command"] for item in next_commands}:
        next_commands.append(
            {
                "command": owner_status_command,
                "surface_role": CONTROL_ENTRY,
                "reason": "Re-run the status audit after selecting the owner route.",
            }
        )
    return {
        "status": "active_behavior_debt",
        "debt": _compact_debt(top),
        "selection_reason": selection_reason,
        "active_behavior_debt_count": len(active_rows),
        "alternate_active_debt_count": len(alternate_active_debt_ids),
        "alternate_active_debt_ids": alternate_active_debt_ids[:5],
        "owner_card_command": owner_card_command or None,
        "owner_status_command": owner_status_command or None,
        "authoritative_decision_command": authoritative_command or None,
        "process_bottleneck_quote_command": action_kind_quote_command or None,
        "source_freshness": freshness or None,
        "target_files": list(top.get("target_files") or []),
        "source_projection_boundary": {
            key: value
            for key, value in boundary.items()
            if key
            in {
                "process_audit_policy",
                "patch_selection_policy",
                "owner_status_route",
                "authoritative_decision_route",
                "owner_card_route",
            }
            and value not in (None, "", [], {})
        },
        "rule": (
            "When active behavior debt exists, follow this fast path before reading the full "
            "coverage matrix rows; the rows remain evidence, not the first action surface."
        ),
        "next_commands": next_commands,
    }


def _fast_path_row_omission_requested(
    query: str,
    fast_path: Mapping[str, Any],
    *,
    context_budget: int,
) -> bool:
    if fast_path.get("status") != "active_behavior_debt":
        return False
    if int(context_budget or 0) > 12000:
        return False
    query_text = str(query or "").lower()
    debt = fast_path.get("debt")
    debt_id = str(debt.get("debt_id") or "").lower() if isinstance(debt, Mapping) else ""
    anti_pattern = str(debt.get("anti_pattern") or "").lower() if isinstance(debt, Mapping) else ""
    markers = {
        "anti_pattern_",
        "owner route",
        "owner_route",
        "deep_without_ladder",
        "slow_action_shape",
        "bash_grep",
        "action kind",
        "action_kind",
        "process-audit",
        "process audit",
    }
    return any(marker in query_text for marker in markers) or (
        bool(anti_pattern) and anti_pattern in query_text
    ) or (bool(debt_id) and debt_id in query_text)


def _compact_first_contact_row_omission_requested(
    query: str,
    fast_path: Mapping[str, Any],
    *,
    context_budget: int,
) -> bool:
    if fast_path.get("status") != "no_active_behavior_debt":
        return False
    if int(context_budget or 0) > 12000:
        return False
    query_text = str(query or "").lower()
    if not query_text:
        return False
    control_plane_markers = {
        "control plane",
        "control-plane",
        "microcosm",
    }
    economy_markers = {
        "efficiency",
        "latency",
        "optimisation",
        "optimization",
        "route cost",
        "speed",
        "throughput",
    }
    return any(marker in query_text for marker in control_plane_markers) and any(
        marker in query_text for marker in economy_markers
    )


def _omit_rows_for_fast_path(packet: dict[str, Any], *, query: str, budget: int) -> dict[str, Any]:
    rows = packet.get("rows")
    if not isinstance(rows, list) or not rows:
        return packet
    packet = dict(packet)
    omitted_count = len(rows)
    full_budget = max(40000, int(budget or 12000) * 3)
    full_matrix_command = (
        f"./repo-python kernel.py --coverage-enforcement-matrix "
        f"{json.dumps(str(query or DEFAULT_QUERY))} --context-budget {full_budget}"
    )
    packet["rows"] = []
    summary = dict(packet.get("summary") or {})
    summary["rows_emitted_count"] = 0
    summary["matrix_rows_omitted_count"] = omitted_count
    packet["summary"] = summary
    budget_section = dict(packet.get("budget") or {})
    budget_section["fast_path_row_omission"] = True
    budget_section["row_compaction_contract"] = (
        "active process-audit fast-path packets omit full matrix rows at routine budget; "
        "the owner route, summary counts, and full_matrix_command preserve drilldown access"
    )
    packet["budget"] = budget_section
    packet["matrix_rows_omission_receipt"] = {
        "status": "omitted_for_process_audit_fast_path",
        "omitted_row_count": omitted_count,
        "reason": (
            "The query names an active process-audit anti-pattern or owner route, so the "
            "first useful action is the process_audit_fast_path owner card rather than "
            "re-reading every Kind Atlas row."
        ),
        "preserved_fields": [
            "summary.kind_count",
            "summary.coverage_status_counts",
            "process_audit_fast_path",
            "process_audit_regression_pressure",
            "type_plane_resolution",
            "next_commands",
        ],
        "full_matrix_command": full_matrix_command,
    }
    next_commands = list(packet.get("next_commands") or [])
    next_commands.append(
        {
            "command": full_matrix_command,
            "surface_role": DRILLDOWN,
            "reason": "Open full per-kind matrix rows only when the fast-path owner route is insufficient.",
        }
    )
    packet["next_commands"] = _dedupe_next_commands(next_commands)
    return packet


def _omit_rows_for_compact_first_contact(packet: dict[str, Any], *, query: str, budget: int) -> dict[str, Any]:
    rows = packet.get("rows")
    if not isinstance(rows, list) or not rows:
        return packet
    packet = dict(packet)
    omitted_count = len(rows)
    kind_ids = [str(row.get("kind_id") or "") for row in rows if isinstance(row, Mapping) and row.get("kind_id")]
    full_budget = max(40000, int(budget or 12000) * 3)
    full_matrix_command = (
        f"./repo-python kernel.py --coverage-enforcement-matrix "
        f"{json.dumps(str(query or DEFAULT_QUERY))} --context-budget {full_budget}"
    )
    packet["rows"] = []
    summary = dict(packet.get("summary") or {})
    summary["rows_emitted_count"] = 0
    summary["matrix_rows_omitted_count"] = omitted_count
    summary["compact_first_contact_status"] = "rows_omitted_no_active_behavior_debt"
    packet["summary"] = summary
    budget_section = dict(packet.get("budget") or {})
    budget_section["compact_first_contact_omission"] = True
    budget_section["row_compaction_contract"] = (
        "broad microcosm/control-plane speed packets with no active process debt omit full "
        "matrix rows at routine budget; summary counts, source freshness, and "
        "full_matrix_command preserve drilldown access"
    )
    packet["budget"] = budget_section
    packet["compact_first_contact_omission_receipt"] = {
        "status": "omitted_for_compact_first_contact_no_active_behavior_debt",
        "omitted_row_count": omitted_count,
        "reason": (
            "The query asks for speed/context/control-plane optimization and the process "
            "audit fast path reports no active behavior debt, so the first-contact packet "
            "keeps the health summary and routes full per-kind rows behind an explicit drilldown."
        ),
        "trigger_policy": (
            "Requires a context-management, control-plane, or microcosm marker plus a "
            "speed, efficiency, throughput, latency, or route-cost marker."
        ),
        "kind_id_preview": kind_ids[:16],
        "kind_id_omitted": max(0, len(kind_ids) - 16),
        "preserved_fields": [
            "summary.kind_count",
            "summary.coverage_status_counts",
            "process_audit_fast_path",
            "process_audit_regression_pressure",
            "type_plane_resolution",
            "next_commands",
        ],
        "full_matrix_command": full_matrix_command,
    }
    next_commands = list(packet.get("next_commands") or [])
    next_commands.append(
        {
            "command": full_matrix_command,
            "surface_role": DRILLDOWN,
            "reason": "Open full per-kind matrix rows only when the compact first-contact packet is insufficient.",
        }
    )
    packet["next_commands"] = _dedupe_next_commands(next_commands)
    return packet


def _dedupe_next_commands(commands: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for command in commands:
        if not isinstance(command, Mapping):
            continue
        text = str(command.get("command") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(dict(command))
    return deduped


def _lifecycle_summary(route: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not route:
        return None
    out: dict[str, Any] = {
        "route_id": route.get("route_id"),
        "status": route.get("status"),
    }
    for key in ("superseded_by", "compatibility_behavior", "removal_condition", "entry_condition"):
        value = route.get(key)
        if value not in (None, "", [], {}):
            out[key] = value
    return out


def _compact_trimmed_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Keep routeable row facts while dropping repeated default-zero detail."""
    out: dict[str, Any] = {}
    for key in (
        "kind_id",
        "row_count",
        "coverage_status",
        "coverage_surface_available",
        "atlas_projection_available",
        "control_entry_allowed",
        "coverage_surface",
        "surface_role",
        "entry_replacement",
        "cluster_flag_available",
        "fallback_surface",
    ):
        value = row.get(key)
        if value not in (None, "", [], {}):
            out[key] = value

    process = row.get("process_audit_violations")
    if isinstance(process, Mapping):
        direct_count = int(process.get("direct_count") or 0)
        blocking_count = int(process.get("blocking_count") or 0)
        accepted_projected_count = int(process.get("accepted_projected_count") or 0)
        observation_pending_count = int(process.get("observation_pending_count") or 0)
        direct_patterns = list(process.get("direct_anti_patterns") or [])
        direct_debt_ids = list(process.get("top_direct_debt_ids") or [])
        accepted_claim_ids = list(process.get("accepted_projected_claim_ids") or [])
        if direct_count or blocking_count or accepted_projected_count or direct_patterns or direct_debt_ids:
            out["process_audit_violations"] = {
                key: value
                for key, value in {
                    "direct_count": direct_count,
                    "blocking_count": blocking_count,
                    "accepted_projected_count": accepted_projected_count,
                    "observation_pending_count": observation_pending_count,
                    "direct_anti_patterns": direct_patterns,
                    "top_direct_debt_ids": direct_debt_ids,
                    "accepted_projected_claim_ids": accepted_claim_ids,
                }.items()
                if value not in (None, "", [], {})
            }

    hooks = row.get("runtime_hook_coverage")
    if isinstance(hooks, Mapping):
        matched = list(hooks.get("matched_anti_patterns") or [])
        status = hooks.get("status")
        if matched or status not in (None, "", "available"):
            out["runtime_hook_coverage"] = {
                key: value
                for key, value in {
                    "status": status,
                    "matched_anti_patterns": matched,
                }.items()
                if value not in (None, "", [], {})
            }

    lifecycle = row.get("route_lifecycle_status")
    if isinstance(lifecycle, Mapping):
        compact_lifecycle = {
            key: value
            for key, value in lifecycle.items()
            if value not in (None, "", [], {})
        }
        if compact_lifecycle:
            out["route_lifecycle_status"] = compact_lifecycle

    debt = row.get("debt_pressure")
    if isinstance(debt, Mapping):
        total = int(debt.get("total") or 0)
        if total:
            out["debt_pressure"] = {
                key: value
                for key, value in debt.items()
                if value not in (None, "", [], {}, 0)
            }
    return out


def _compact_profile_preview_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Tiny per-kind row preview for command-profile packets."""
    out: dict[str, Any] = {}
    for key in (
        "kind_id",
        "row_count",
        "coverage_status",
        "coverage_surface_available",
        "coverage_surface",
        "cluster_flag_available",
    ):
        value = row.get(key)
        if value not in (None, "", [], {}):
            out[key] = value

    process = row.get("process_audit_violations")
    if isinstance(process, Mapping):
        counts = {
            "blocking_count": int(process.get("blocking_count") or 0),
            "direct_count": int(process.get("direct_count") or 0),
            "accepted_projected_count": int(process.get("accepted_projected_count") or 0),
        }
        nonzero_counts = {key: value for key, value in counts.items() if value}
        if nonzero_counts:
            out["process_audit_counts"] = nonzero_counts

    debt = row.get("debt_pressure")
    if isinstance(debt, Mapping):
        total = int(debt.get("total") or 0)
        if total:
            out["debt_pressure_total"] = total
    return out


def _compact_profile_process_pressure(section: Any) -> Any:
    if not isinstance(section, Mapping):
        return section
    freshness = section.get("source_freshness")
    freshness = freshness if isinstance(freshness, Mapping) else {}
    lifecycle = section.get("behavior_lifecycle_summary")
    lifecycle = lifecycle if isinstance(lifecycle, Mapping) else {}
    hook_shadow = section.get("hook_shadow_coverage")
    hook_shadow = hook_shadow if isinstance(hook_shadow, Mapping) else {}
    return {
        key: value
        for key, value in {
            "status": section.get("status"),
            "source_freshness": {
                key: value
                for key, value in {
                    "status": freshness.get("status"),
                    "cache_status": freshness.get("cache_status"),
                    "patch_selection_policy": freshness.get("patch_selection_policy"),
                    "authoritative_decision_command": freshness.get("authoritative_decision_command"),
                }.items()
                if value not in (None, "", [], {})
            },
            "observed_session_count": section.get("observed_session_count"),
            "behavior_row_count": section.get("behavior_row_count"),
            "pattern_class_count": len(section.get("pattern_classes") or []),
            "pattern_classes_preview": list(section.get("pattern_classes") or [])[:4],
            "behavior_lifecycle_summary": {
                key: value
                for key, value in {
                    "active_behavior_debt_count": lifecycle.get("active_behavior_debt_count"),
                    "advisory_behavior_debt_count": lifecycle.get("advisory_behavior_debt_count"),
                    "retired_by_navigation_mechanism_count": lifecycle.get(
                        "retired_by_navigation_mechanism_count"
                    ),
                    "active_behavior_debt_ids": lifecycle.get("active_behavior_debt_ids"),
                }.items()
                if value not in (None, "", [], {})
            },
            "hook_shadow_coverage": {
                key: value
                for key, value in {
                    "status": hook_shadow.get("status"),
                    "hook_shadow_coverage_top_patterns": hook_shadow.get(
                        "hook_shadow_coverage_top_patterns"
                    ),
                    "would_intervene_on_recent_route_failures": hook_shadow.get(
                        "would_intervene_on_recent_route_failures"
                    ),
                }.items()
                if value not in (None, "", [], {})
            },
        }.items()
        if value not in (None, "", [], {})
    }


def _compact_profile_type_plane_resolution(section: Any) -> Any:
    if not isinstance(section, Mapping):
        return section
    routes = [row for row in section.get("extra_resolved_routes") or [] if isinstance(row, Mapping)]
    return {
        key: value
        for key, value in {
            "schema_version": section.get("schema_version"),
            "status": section.get("status"),
            "coverage_matrix_scope": section.get("coverage_matrix_scope"),
            "authority_ref": section.get("authority_ref"),
            "kind_atlas_kind_count": section.get("kind_atlas_kind_count"),
            "extra_resolved_surface_count": section.get("extra_resolved_surface_count"),
            "extra_resolved_type_ids": [str(row.get("type_id") or "") for row in routes if row.get("type_id")],
            "first_extra_route_command": (
                str(routes[0].get("option_surface_command") or "") if routes else None
            ),
        }.items()
        if value not in (None, "", [], {})
    }


def _compact_profile_strategy(section: Any) -> Any:
    if not isinstance(section, Mapping):
        return section
    latency = section.get("latency_profile")
    latency = latency if isinstance(latency, Mapping) else {}
    source_surfaces = section.get("source_surfaces_reused") or []
    return {
        key: value
        for key, value in {
            "read_only_composer": section.get("read_only_composer"),
            "coverage_before_invocation": section.get("coverage_before_invocation"),
            "coverage_is_not_permission": section.get("coverage_is_not_permission"),
            "control_entry_required": section.get("control_entry_required"),
            "kind_atlas_projection_profile": section.get("kind_atlas_projection_profile"),
            "kind_atlas_fast_path": section.get("kind_atlas_fast_path"),
            "source_surface_count": len(source_surfaces),
            "stage_timings_ms": section.get("stage_timings_ms"),
            "latency_profile": {
                key: value
                for key, value in {
                    "status": latency.get("status"),
                    "total_ms": latency.get("total_ms"),
                    "slow_phase_count": latency.get("slow_phase_count"),
                    "slow_phases": latency.get("slow_phases"),
                }.items()
                if value not in (None, "", [], {})
            },
        }.items()
        if value not in (None, "", [], {})
    }


def _compact_profile_next_commands(commands: Any, *, full_matrix_command: str) -> list[dict[str, Any]]:
    if not isinstance(commands, Sequence) or isinstance(commands, (str, bytes, bytearray)):
        commands = []
    selected: list[Mapping[str, Any]] = []
    for command in commands:
        if not isinstance(command, Mapping):
            continue
        text = str(command.get("command") or "")
        if text == full_matrix_command or "--entry" in text:
            selected.append(command)
    if not any(str(command.get("command") or "") == full_matrix_command for command in selected):
        selected.append(
            {
                "command": full_matrix_command,
                "surface_role": DRILLDOWN,
                "reason": "Open full per-kind matrix rows when command-profile shape is insufficient.",
            }
        )
    return _dedupe_next_commands(selected)


def _debt_matches_kind(row: Mapping[str, Any], kind_id: str) -> bool:
    debt_id = str(row.get("debt_id") or "")
    route_id = str(row.get("route_id") or "")
    artifact_kind = str(row.get("artifact_kind") or "")
    if artifact_kind == kind_id:
        return True
    if route_id.startswith(f"{kind_id}."):
        return True
    if f":{kind_id}" in debt_id or f":{kind_id}." in debt_id:
        return True
    if kind_id == "skills" and ("skill_find" in debt_id or "skill_find" in route_id):
        return True
    if kind_id == "skill_compression_debt" and "skill_compression" in debt_id:
        return True
    return False


def _debt_is_coverage_watch(row: Mapping[str, Any]) -> bool:
    if row.get("active_debt") is False or row.get("advisory_only") is True:
        return False
    if row.get("debt_class") == "layer_sprawl_debt":
        return False
    return True


def _process_kinds(row: Mapping[str, Any]) -> tuple[str, ...]:
    anti_pattern = str(row.get("anti_pattern") or row.get("anti_pattern_id") or "")
    debt_id = str(row.get("debt_id") or "")
    if "skill_find" in debt_id:
        return ("skills",)
    if "paper_module" in debt_id:
        return ("paper_modules",)
    return _PROCESS_KIND_MAP.get(anti_pattern, ())


def _process_anti_pattern_id(row: Mapping[str, Any]) -> str:
    anti_pattern_id = str(row.get("anti_pattern_id") or "")
    if anti_pattern_id.startswith("anti_pattern_"):
        return anti_pattern_id
    debt_id = str(row.get("debt_id") or "")
    marker = "anti_pattern_"
    if marker in debt_id:
        return f"{marker}{debt_id.split(marker, 1)[1]}"
    anti_pattern = str(row.get("anti_pattern") or "")
    if not anti_pattern:
        return ""
    if anti_pattern.startswith("anti_pattern_"):
        return anti_pattern
    return f"anti_pattern_{anti_pattern}"


def _accepted_mechanism_projections(metabolism: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    mechanism = metabolism.get("navigation_mechanism_metabolism") or {}
    if not isinstance(mechanism, Mapping):
        return {}
    projections: dict[str, Mapping[str, Any]] = {}
    claim_rows = list(mechanism.get("observed_claim_refs") or [])
    claim_rows.extend(list(mechanism.get("top_candidate_claims") or []))
    for row in claim_rows:
        if not isinstance(row, Mapping):
            continue
        anti_pattern_id = str(row.get("anti_pattern_id") or "")
        if not anti_pattern_id:
            continue
        state = str(row.get("state") or "")
        accepted = row.get("owner_acceptance_status") == "accepted" or row.get("acceptance_eligibility") == "accepted"
        future_status = ""
        future_observation = row.get("future_observation")
        if isinstance(future_observation, Mapping):
            future_status = str(future_observation.get("status") or "")
        projected = (
            state in {"accepted", "projected", "observed", "superseded"}
            or row.get("latest_acceptance_event_type") in {"projection.recorded", "observation.recorded", "claim.superseded"}
            or future_status == "observed"
        )
        if accepted and projected:
            projections[anti_pattern_id] = row
    return projections


def _process_projection_for_row(
    row: Mapping[str, Any],
    projections: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    anti_pattern_id = _process_anti_pattern_id(row)
    if not anti_pattern_id:
        return None
    return projections.get(anti_pattern_id)


def _compact_process_projection(row: Mapping[str, Any], projection: Mapping[str, Any]) -> dict[str, Any]:
    future_observation = projection.get("future_observation") or {}
    if not isinstance(future_observation, Mapping):
        future_observation = {}
    return {
        key: value
        for key, value in {
            "anti_pattern_id": _process_anti_pattern_id(row),
            "debt_id": row.get("debt_id"),
            "claim_id": projection.get("claim_id"),
            "state": projection.get("state"),
            "owner_acceptance_status": projection.get("owner_acceptance_status"),
            "latest_acceptance_event_type": projection.get("latest_acceptance_event_type"),
            "future_observation_status": future_observation.get("status"),
            "future_observation_window_status": future_observation.get("future_observation_window_status"),
        }.items()
        if value not in (None, "", [], {})
    }


def _hook_matches_kind(row: Mapping[str, Any], kind_id: str) -> bool:
    text_parts: list[str] = [
        str(row.get("suggested_route") or ""),
        str(row.get("fallback_surface") or ""),
        " ".join(str(item) for item in row.get("expected_artifacts") or []),
    ]
    haystack = " ".join(text_parts)
    return (
        f"--option-surface {kind_id}" in haystack
        or f"option_surface:{kind_id}" in haystack
        or f"{kind_id}:" in haystack
        or (kind_id == "skills" and "skill" in haystack)
        or (kind_id == "paper_modules" and "paper-module" in haystack)
    )


def _coverage_surface_command(kind_id: str, atlas_row: Mapping[str, Any], high_cardinality: bool) -> str:
    command = str(atlas_row.get("option_surface_command") or "").strip()
    bands = {str(item) for item in atlas_row.get("bands") or []}
    if command:
        if (
            not high_cardinality
            and "flag" in bands
            and command.endswith("--band cluster_flag")
        ):
            return f"./repo-python kernel.py --option-surface {kind_id} --band flag"
        return command
    cluster_command = str(atlas_row.get("cluster_command") or "").strip()
    if cluster_command and (high_cardinality or "cluster_flag" in bands):
        return cluster_command
    band = "cluster_flag" if high_cardinality else "flag"
    return f"./repo-python kernel.py --option-surface {kind_id} --band {band}"


def _standard_type_plane_resolution(
    repo_root: Path,
    *,
    kind_ids: set[str],
) -> dict[str, Any]:
    try:
        payload = json.loads((repo_root / STANDARD_TYPE_PLANE).read_text())
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": "coverage_matrix_type_plane_resolution_v0",
            "status": "standard_type_plane_unavailable",
            "coverage_matrix_scope": "kind_atlas_rows",
            "authority_ref": str(STANDARD_TYPE_PLANE),
            "extra_resolved_surface_count": 0,
            "extra_resolved_routes": [],
        }
    rows = payload.get("type_plane_rows") if isinstance(payload, Mapping) else []
    extra_routes: list[dict[str, Any]] = []
    type_plane_rows = rows if isinstance(rows, list) else []
    for row in type_plane_rows:
        if not isinstance(row, Mapping):
            continue
        type_id = str(row.get("type_id") or "").strip()
        command = str(row.get("option_surface_command") or "").strip()
        if not type_id or not command or type_id in kind_ids:
            continue
        passport = row.get("compression_passport")
        passport = passport if isinstance(passport, Mapping) else {}
        type_plane_card_command = str(passport.get("safe_drilldown") or "").strip()
        if not type_plane_card_command:
            type_plane_card_command = (
                "./repo-python kernel.py --option-surface navigation_type_plane "
                f"--band card --ids {shlex.quote(type_id)}"
            )
        extra_routes.append(
            {
                "type_id": type_id,
                "canonical_type_id": str(row.get("canonical_type_id") or "").strip() or None,
                "title": str(row.get("title") or type_id),
                "option_surface_command": command,
                "type_plane_card_command": type_plane_card_command,
                "coverage_relationship": "resolved_by_standard_type_plane_not_matrix_kind_row",
            }
        )
    extra_routes.sort(key=lambda item: str(item.get("type_id") or ""))
    return {
        "schema_version": "coverage_matrix_type_plane_resolution_v0",
        "status": "extra_standard_type_plane_routes_present" if extra_routes else "kind_atlas_scope_aligned",
        "coverage_matrix_scope": "kind_atlas_rows",
        "authority_ref": str(STANDARD_TYPE_PLANE),
        "entry_index_spine_field": "navigation_index_spine.coverage_closure.coverage_surface_resolution_sources",
        "kind_atlas_kind_count": len(kind_ids),
        "extra_resolved_surface_count": len(extra_routes),
        "extra_resolved_routes": extra_routes,
        "policy": (
            "The coverage matrix audits behavior and debt over Kind Atlas rows; standard type-plane "
            "rows outside Kind Atlas are surfaced here as resolved drilldowns, not as additional "
            "matrix rows or control-entry permissions."
        ),
    }


def _declared_coverage_surface_available(atlas_row: Mapping[str, Any], high_cardinality: bool) -> bool:
    if str(atlas_row.get("option_surface_command") or "").strip():
        return True
    cluster_command = str(atlas_row.get("cluster_command") or "").strip()
    bands = {str(item) for item in atlas_row.get("bands") or []}
    return bool(cluster_command and (high_cardinality or "cluster_flag" in bands))


def _trim_packet(packet: dict[str, Any], *, context_budget: int) -> dict[str, Any]:
    budget_bytes = max(1000, int(context_budget or 12000)) * 4 - 2048
    if _json_bytes(packet) <= budget_bytes:
        packet["budget"]["estimated_tokens"] = max(1, (_json_bytes(packet) + 3) // 4)
        return packet
    packet = dict(packet)
    packet["rows"] = [
        _compact_trimmed_row(row)
        for row in packet.get("rows", [])
        if isinstance(row, Mapping)
    ]
    packet["budget"]["trimmed_for_budget"] = True
    packet["budget"]["trim_note"] = (
        "Matrix rows omit repeated default-zero detail; rerun with a larger --context-budget "
        "for owner standards, lifecycle nulls, ambient-only process pressure, and full debt ids."
    )
    packet["budget"]["row_compaction_contract"] = (
        "all kind rows remain routeable; covered rows may omit zero/default nested diagnostics"
    )
    fast_path = packet.get("process_audit_fast_path")
    if isinstance(fast_path, dict) and fast_path.get("status") == "active_behavior_debt":
        compact_fast_path = dict(fast_path)
        compact_fast_path.pop("source_projection_boundary", None)
        compact_fast_path.pop("next_commands", None)
        packet["process_audit_fast_path"] = compact_fast_path
    process_pressure = packet.get("process_audit_regression_pressure")
    if isinstance(process_pressure, dict):
        process_pressure = dict(process_pressure)
        top_behavior_rows = process_pressure.get("top_behavior_rows")
        if isinstance(top_behavior_rows, list):
            process_pressure["top_behavior_rows"] = top_behavior_rows[:3]
        packet["process_audit_regression_pressure"] = process_pressure
    if _json_bytes(packet) > budget_bytes:
        process_pressure = packet.get("process_audit_regression_pressure")
        if isinstance(process_pressure, dict):
            process_pressure = dict(process_pressure)
            top_behavior_rows = process_pressure.get("top_behavior_rows")
            if isinstance(top_behavior_rows, list):
                process_pressure["top_behavior_rows"] = top_behavior_rows[:1]
            hook_shadow = process_pressure.get("hook_shadow_coverage")
            if isinstance(hook_shadow, dict):
                hook_shadow = dict(hook_shadow)
                rows = hook_shadow.get("rows")
                if isinstance(rows, list):
                    hook_shadow["rows"] = rows[:3]
                process_pressure["hook_shadow_coverage"] = hook_shadow
            packet["process_audit_regression_pressure"] = process_pressure
    packet["budget"]["estimated_tokens"] = max(1, (_json_bytes(packet) + 3) // 4)
    return packet


def compact_coverage_enforcement_matrix_for_profile(
    packet: Mapping[str, Any],
    *,
    query: str | None = None,
    context_budget: int = 12000,
    row_preview_limit: int = 3,
) -> dict[str, Any]:
    """Keep command-profile output bounded while preserving the full matrix drilldown."""
    rows = [dict(row) for row in packet.get("rows", []) if isinstance(row, Mapping)]
    if not rows:
        return dict(packet)

    def pressure_key(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
        process = row.get("process_audit_violations")
        process = process if isinstance(process, Mapping) else {}
        debt = row.get("debt_pressure")
        debt = debt if isinstance(debt, Mapping) else {}
        return (
            int(debt.get("total") or 0),
            int(process.get("blocking_count") or 0),
            int(process.get("direct_count") or 0),
            int(row.get("row_count") or 0),
        )

    task_query = str(query or packet.get("query") or DEFAULT_QUERY)
    full_budget = max(40000, int(context_budget or 12000) * 3)
    full_matrix_command = (
        f"./repo-python kernel.py --coverage-enforcement-matrix "
        f"{json.dumps(task_query)} --context-budget {full_budget}"
    )
    pressure_rows = sorted(rows, key=pressure_key, reverse=True)[: max(0, row_preview_limit)]

    compact = dict(packet)
    summary = dict(compact.get("summary") if isinstance(compact.get("summary"), Mapping) else {})
    summary.update(
        {
            "rows_emitted_count": 0,
            "matrix_rows_omitted_count": len(rows),
            "row_pressure_preview_count": len(pressure_rows),
            "compact_profile_status": "rows_omitted_for_command_profile",
        }
    )
    budget = dict(compact.get("budget") if isinstance(compact.get("budget"), Mapping) else {})
    budget["command_profile_compaction"] = True
    budget["row_compaction_contract"] = (
        "command-profile packets emit timing and bounded row-pressure preview only; "
        "the full matrix route preserves per-kind evidence"
    )

    compact["output_profile"] = "coverage_enforcement_matrix_command_profile_compact_v0"
    compact["summary"] = summary
    compact["budget"] = budget
    compact["rows"] = []
    compact["row_pressure_preview"] = [_compact_profile_preview_row(row) for row in pressure_rows]
    compact["process_audit_regression_pressure"] = _compact_profile_process_pressure(
        compact.get("process_audit_regression_pressure")
    )
    compact["type_plane_resolution"] = _compact_profile_type_plane_resolution(
        compact.get("type_plane_resolution")
    )
    compact["strategy"] = _compact_profile_strategy(compact.get("strategy"))
    compact["command_profile_omission_receipt"] = {
        "status": "matrix_rows_omitted_for_command_profile",
        "omitted_row_count": len(rows),
        "reason": (
            "Command-profile output is a timing/shape packet; full per-kind coverage rows "
            "belong behind the explicit coverage-enforcement matrix drilldown."
        ),
        "preserved_fields": [
            "summary",
            "row_pressure_preview",
            "process_audit_fast_path",
            "process_audit_regression_pressure",
            "type_plane_resolution",
            "next_commands",
        ],
        "full_matrix_command": full_matrix_command,
        "context_budget_tokens": context_budget,
    }
    compact["next_commands"] = _compact_profile_next_commands(
        compact.get("next_commands"),
        full_matrix_command=full_matrix_command,
    )
    compact["budget"]["estimated_tokens"] = max(1, (_json_bytes(compact) + 3) // 4)
    return compact


def build_coverage_enforcement_matrix(
    repo_root: Path | str,
    *,
    query: str | None = None,
    context_budget: int = 12000,
) -> dict[str, Any]:
    """Build a per-kind coverage matrix from existing atlas surfaces."""
    total_started = time.perf_counter()
    stage_timings_ms: dict[str, int] = {}
    root = Path(repo_root)
    budget = max(1000, int(context_budget or 12000))
    task_query = str(query or DEFAULT_QUERY)

    stage_started = time.perf_counter()
    atlas = build_kind_atlas(root, band="flag", fast=True)
    stage_timings_ms["kind_atlas"] = _elapsed_ms(stage_started)

    stage_started = time.perf_counter()
    metabolism = build_navigation_metabolism_ledger(
        root,
        query=task_query,
        context_budget=budget,
        include_session_summary=False,
        include_fitness=False,
        metabolism_profile="quick",
    )
    stage_timings_ms["navigation_metabolism"] = _elapsed_ms(stage_started)

    stage_started = time.perf_counter()
    debt_rows = [row for row in metabolism.get("debt_rows") or [] if isinstance(row, Mapping)]
    route_lifecycle = {
        str(row.get("route_id") or ""): row
        for row in metabolism.get("route_lifecycle") or []
        if isinstance(row, Mapping)
    }
    hook_rows = [
        row
        for row in ((metabolism.get("hook_shadow_coverage") or {}).get("rows") or [])
        if isinstance(row, Mapping)
    ]
    cluster_rows = {
        str(row.get("kind_id") or ""): row
        for row in ((metabolism.get("clusterability") or {}).get("rows") or [])
        if isinstance(row, Mapping)
    }

    behavior_rows = [row for row in debt_rows if row.get("debt_class") == "behavior_debt"]
    behavior_rows_for_routing = _behavior_rows_for_routing(behavior_rows)
    process_audit_source_freshness = _process_audit_source_freshness(metabolism)
    process_audit_fast_path = _process_audit_fast_path(
        behavior_rows_for_routing,
        query=task_query,
        source_freshness=process_audit_source_freshness,
    )
    global_process_rows = [
        row for row in behavior_rows if "*global*" in _process_kinds(row) or "*entrypoint*" in _process_kinds(row)
    ]
    accepted_mechanisms = _accepted_mechanism_projections(metabolism)

    matrix_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    coverage_surface_available_count = 0
    control_entry_allowed_count = 0
    high_cardinality_count = 0
    high_cardinality_clustered_count = 0
    matrix_kind_ids: set[str] = set()

    atlas_rows = [
        row
        for row in atlas.get("rows") or []
        if isinstance(row, Mapping) and any(str(item).strip() for item in row.get("bands") or [])
    ]
    for atlas_row in atlas_rows:
        if not isinstance(atlas_row, Mapping):
            continue
        kind_id = str(atlas_row.get("kind_id") or "")
        if not kind_id:
            continue
        matrix_kind_ids.add(kind_id)
        row_count = int(atlas_row.get("row_count") or 0)
        bands = [str(item) for item in atlas_row.get("bands") or []]
        high_cardinality = row_count >= HIGH_CARDINALITY_THRESHOLD
        if high_cardinality:
            high_cardinality_count += 1
        has_cluster = "cluster_flag" in bands
        if high_cardinality and has_cluster:
            high_cardinality_clustered_count += 1
        has_flag = "flag" in bands
        has_card = "card" in bands
        support_status = atlas_row.get("support_status")
        profile_supported = support_status == "option_surface_supported"
        legacy_command_supported = support_status == "legacy_command_only" and _declared_coverage_surface_available(
            atlas_row, high_cardinality
        )
        source_drilldown = bool(atlas_row.get("evidence_command") or atlas_row.get("card_command"))
        coverage_surface_available = bool(
            (profile_supported or legacy_command_supported)
            and has_flag
            and (has_cluster if high_cardinality else True)
        )
        if coverage_surface_available:
            coverage_surface_available_count += 1

        kind_debts = [row for row in debt_rows if _debt_matches_kind(row, kind_id)]
        coverage_watch_debts = [row for row in kind_debts if _debt_is_coverage_watch(row)]
        direct_process_rows = [
            row
            for row in behavior_rows
            if kind_id in _process_kinds(row) or _debt_matches_kind(row, kind_id)
        ]
        projected_process_rows = [
            row
            for row in direct_process_rows
            if _process_projection_for_row(row, accepted_mechanisms) is not None
        ]
        blocking_process_rows = [
            row
            for row in direct_process_rows
            if _process_projection_for_row(row, accepted_mechanisms) is None
        ]
        process_projection_rows = [
            _compact_process_projection(row, projection)
            for row in projected_process_rows
            if (projection := _process_projection_for_row(row, accepted_mechanisms)) is not None
        ]
        hook_matches = [row for row in hook_rows if _hook_matches_kind(row, kind_id)]
        lifecycle_all_row = route_lifecycle.get(f"{kind_id}.row_flag_all")
        exact_route = _EXACT_LOOKUP_ROUTE_BY_KIND.get(kind_id)
        exact_lifecycle = route_lifecycle.get(exact_route or "")
        clusterability_row = cluster_rows.get(kind_id)

        if not coverage_surface_available and not (profile_supported or legacy_command_supported):
            coverage_status = "blocked_no_option_surface"
        elif high_cardinality and not has_cluster:
            coverage_status = "blocked_missing_cluster_flag"
        elif blocking_process_rows or coverage_watch_debts:
            coverage_status = "watch_behavior_or_debt"
        else:
            coverage_status = "covered"
        status_counts[coverage_status] += 1

        matrix_rows.append(
            {
                "kind_id": kind_id,
                "title": atlas_row.get("title"),
                "row_count": row_count,
                "atlas_visible": True,
                "high_cardinality": high_cardinality,
                "cluster_flag_available": has_cluster,
                "flag_available": has_flag,
                "card_available": has_card,
                "source_drilldown_available": source_drilldown,
                "owner_standard": list(atlas_row.get("governing_standard_refs") or []),
                "projection_refs": list(atlas_row.get("projection_refs") or []),
                "surface_role": ATLAS_PROJECTION,
                "coverage_surface_available": coverage_surface_available,
                "atlas_projection_available": coverage_surface_available,
                "control_entry_allowed": False,
                "first_contact_policy": "entry_packet_required",
                "entry_replacement": ENTRY_REPLACEMENT,
                "coverage_surface": _coverage_surface_command(kind_id, atlas_row, high_cardinality),
                "fallback_surface": (
                    atlas_row.get("option_surface_command")
                    or atlas_row.get("cluster_command")
                    or atlas_row.get("card_command")
                    or f"./repo-python kernel.py --option-surface {kind_id} --band flag"
                ),
                "coverage_status": coverage_status,
                "route_lifecycle_status": {
                    "all_row_flag": _lifecycle_summary(lifecycle_all_row),
                    "exact_lookup": _lifecycle_summary(exact_lifecycle),
                },
                "clusterability": {
                    "status": (clusterability_row or {}).get("cluster_flag_status")
                    if isinstance(clusterability_row, Mapping)
                    else ("implemented" if has_cluster else "not_required" if not high_cardinality else "missing"),
                    "grouping_keys_available": (clusterability_row or {}).get("grouping_keys_available")
                    if isinstance(clusterability_row, Mapping)
                    else [],
                    "repair_class": (clusterability_row or {}).get("repair_class")
                    if isinstance(clusterability_row, Mapping)
                    else None,
                },
                "debt_pressure": {
                    "total": len(kind_debts),
                    "coverage_watch_debt_count": len(coverage_watch_debts),
                    "compression_debt": sum(
                        1
                        for row in kind_debts
                        if row.get("debt_class") in {"authoring_debt", "clusterability_debt", "layer_sprawl_debt"}
                    ),
                    "projection_debt": sum(1 for row in kind_debts if row.get("debt_class") == "projection_debt"),
                    "top_coverage_watch_debt_ids": [str(row.get("debt_id")) for row in coverage_watch_debts[:5]],
                    "top_debt_ids": [str(row.get("debt_id")) for row in kind_debts[:5]],
                    "top_debt_rows": [_compact_debt(row) for row in kind_debts[:3]],
                },
                "runtime_hook_coverage": {
                    "status": "direct" if hook_matches else (metabolism.get("hook_shadow_coverage") or {}).get("status"),
                    "matched_anti_patterns": [str(row.get("anti_pattern_id") or "") for row in hook_matches],
                    "shadow_top_patterns": (metabolism.get("hook_shadow_coverage") or {}).get(
                        "hook_shadow_coverage_top_patterns"
                    ),
                },
                "process_audit_violations": {
                    "direct_count": len(direct_process_rows),
                    "blocking_count": len(blocking_process_rows),
                    "accepted_projected_count": len(projected_process_rows),
                    "observation_pending_count": sum(
                        1
                        for row in process_projection_rows
                        if row.get("future_observation_status") == "awaiting_observation"
                    ),
                    "ambient_process_pressure_count": len(global_process_rows),
                    "direct_anti_patterns": sorted(
                        {
                            str(row.get("anti_pattern") or row.get("debt_id") or "")
                            for row in direct_process_rows
                            if str(row.get("anti_pattern") or row.get("debt_id") or "")
                        }
                    ),
                    "top_direct_debt_ids": [str(row.get("debt_id") or "") for row in direct_process_rows[:5]],
                    "top_blocking_debt_ids": [str(row.get("debt_id") or "") for row in blocking_process_rows[:5]],
                    "accepted_projected_claim_ids": [
                        str(row.get("claim_id") or "")
                        for row in process_projection_rows[:5]
                        if str(row.get("claim_id") or "")
                    ],
                    "accepted_projected_repairs": process_projection_rows[:3],
                },
            }
        )
    stage_timings_ms["matrix_rows"] = _elapsed_ms(stage_started)

    stage_started = time.perf_counter()
    type_plane_resolution = _standard_type_plane_resolution(root, kind_ids=matrix_kind_ids)
    standard_type_plane_resolved_count = int(type_plane_resolution.get("extra_resolved_surface_count") or 0)
    coverage_surface_resolution_sources = {
        "kind_atlas": coverage_surface_available_count,
    }
    if standard_type_plane_resolved_count:
        coverage_surface_resolution_sources["standard_type_plane"] = standard_type_plane_resolved_count
    stage_timings_ms["standard_type_plane"] = _elapsed_ms(stage_started)

    stage_started = time.perf_counter()
    process_source = (metabolism.get("observation_sources") or {}).get("agent_path_events") or {}
    packet: dict[str, Any] = {
        "kind": "coverage_enforcement_matrix",
        "schema_version": "coverage_enforcement_matrix_v0",
        "generated_at": _utc_now(),
        "query": task_query,
        "budget": {
            "context_budget_tokens": budget,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "invariant": "Coverage is not permission: atlas affordances may be discoverable without being legal first-contact control.",
        "strategy": {
            "read_only_composer": True,
            "new_registry_created": False,
            "coverage_before_invocation": True,
            "coverage_is_not_permission": True,
            "control_entry_required": True,
            "kind_atlas_projection_profile": atlas.get("projection_profile")
            if isinstance(atlas, Mapping)
            else None,
            "kind_atlas_fast_path": (
                (atlas.get("summary") or {}).get("fast_path")
                if isinstance(atlas.get("summary"), Mapping)
                else None
            )
            if isinstance(atlas, Mapping)
            else None,
            "kind_atlas_filtered_no_band_row_count": max(
                0,
                len(atlas.get("rows") or []) - len(atlas_rows),
            )
            if isinstance(atlas, Mapping)
            else 0,
            "source_surfaces_reused": [
                "system/lib/kind_atlas.py",
                "system/lib/navigation_metabolism_ledger.py",
                "system/lib/navigation_clusterability.py",
                "system/lib/navigation_route_intervention.py",
                "system/lib/agent_execution_trace.py",
                "codex/standards/std_standard_type_plane.json",
            ],
        },
        "summary": {
            "kind_count": len(matrix_rows),
            "coverage_matrix_scope": "kind_atlas_rows",
            "coverage_surface_available_count": coverage_surface_available_count,
            "kind_atlas_coverage_surface_available_count": coverage_surface_available_count,
            "standard_type_plane_resolved_surface_count": standard_type_plane_resolved_count,
            "resolved_route_surface_count": coverage_surface_available_count + standard_type_plane_resolved_count,
            "coverage_surface_resolution_sources": coverage_surface_resolution_sources,
            "coverage_count_policy": (
                "coverage_surface_available_count counts matrix Kind Atlas rows only; "
                "resolved_route_surface_count adds standard type-plane fallback routes so this packet "
                "aligns with the entry index spine without turning fallback routes into matrix rows."
            ),
            "coverage_surface_blocked_count": len(matrix_rows) - coverage_surface_available_count,
            "control_entry_allowed_count": control_entry_allowed_count,
            "control_entry_blocked_count": len(matrix_rows) - control_entry_allowed_count,
            "high_cardinality_kind_count": high_cardinality_count,
            "high_cardinality_clustered_count": high_cardinality_clustered_count,
            "coverage_status_counts": dict(status_counts),
            "process_audit_status": process_source.get("process_audit_status") or process_source.get("status"),
            "process_audit_session_count": process_source.get("process_audit_session_count"),
            "process_audit_behavior_row_count": process_source.get("process_audit_behavior_row_count"),
            "process_audit_source_freshness_status": process_audit_source_freshness.get("status"),
            "runtime_hook_shadow_coverage": (metabolism.get("hook_shadow_coverage") or {}).get(
                "hook_shadow_coverage_top_patterns"
            ),
        },
        "process_audit_regression_pressure": {
            "status": process_source.get("process_audit_status") or process_source.get("status"),
            "source_freshness": process_audit_source_freshness or None,
            "observed_session_count": process_source.get("process_audit_observed_session_count"),
            "behavior_row_count": process_source.get("process_audit_behavior_row_count"),
            "pattern_classes": process_source.get("process_audit_pattern_classes") or [],
            "behavior_lifecycle_summary": _behavior_lifecycle_summary(behavior_rows),
            "top_behavior_rows": [_compact_debt(row) for row in behavior_rows_for_routing[:8]],
            "hook_shadow_coverage": metabolism.get("hook_shadow_coverage"),
        },
        "process_audit_fast_path": process_audit_fast_path,
        "type_plane_resolution": type_plane_resolution,
        "rows": matrix_rows,
        "next_commands": _dedupe_next_commands(
            list(process_audit_fast_path.get("next_commands") or [])
            + (
                [
                    {
                        "command": (
                            f"./repo-python kernel.py --doctrine-routing-weave "
                            f"{json.dumps(task_query)} --context-budget {budget}"
                        ),
                        "surface_role": CONTROL_ENTRY,
                        "reason": "Compose the bidirectional doctrine-to-substrate route read model for this coverage lane.",
                    }
                ]
                if _query_prefers_doctrine_routing_weave(task_query)
                else []
            )
            + [
                {
                    "command": (
                        f"./repo-python kernel.py --coverage-enforcement-matrix "
                        f"{json.dumps(task_query)} --context-budget {budget}"
                    ),
                    "surface_role": CONTROL_ENTRY,
                    "reason": "Re-run this read-only audit with the same task query.",
                },
                {
                    "command": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                    "surface_role": CONTROL_ENTRY,
                    "reason": "Compile a fresh task into one legal control packet.",
                },
                {
                    "command": "./repo-python kernel.py --kind-atlas",
                    "surface_role": ATLAS_PROJECTION,
                    "reason": (
                        "Browse artifact kinds only after entry selects atlas orientation or the "
                        "operator explicitly browses."
                    ),
                },
                {
                    "command": "./repo-python kernel.py --option-surface <kind> --band cluster_flag",
                    "surface_role": ATLAS_PROJECTION,
                    "reason": "Browse one kind contents page only after entry selects that kind.",
                },
                {
                    "command": (
                        "./repo-python kernel.py --navigation-metabolism \"<task>\" "
                        "--metabolism-profile quick --context-budget 12000"
                    ),
                    "surface_role": CONTROL_ENTRY,
                    "reason": "Use the metabolism ledger for navigation/process/surface complaints.",
                },
                {
                    "command": "./repo-python kernel.py --process-audit",
                    "surface_role": DRILLDOWN,
                    "reason": "Open behavior evidence after a navigation-control packet selects process audit.",
                },
            ]
        ),
        "source_surfaces": [
            "system/lib/navigation_coverage_matrix.py",
            "system/lib/kind_atlas.py",
            "system/lib/navigation_metabolism_ledger.py",
            "system/lib/navigation_clusterability.py",
            "system/lib/navigation_route_intervention.py",
            "system/lib/agent_execution_trace.py",
            "codex/standards/std_standard_type_plane.json",
        ],
    }
    if _fast_path_row_omission_requested(
        task_query,
        process_audit_fast_path,
        context_budget=budget,
    ):
        packet = _omit_rows_for_fast_path(packet, query=task_query, budget=budget)
    elif _compact_first_contact_row_omission_requested(
        task_query,
        process_audit_fast_path,
        context_budget=budget,
    ):
        packet = _omit_rows_for_compact_first_contact(packet, query=task_query, budget=budget)
    stage_timings_ms["packet_assembly"] = _elapsed_ms(stage_started)

    stage_started = time.perf_counter()
    packet = _trim_packet(packet, context_budget=budget)
    stage_timings_ms["budget_trim"] = _elapsed_ms(stage_started)
    total_ms = _elapsed_ms(total_started)

    strategy = packet.setdefault("strategy", {})
    strategy["stage_timings_ms"] = dict(stage_timings_ms)
    strategy["latency_profile"] = _latency_profile(stage_timings_ms, total_ms)
    packet["budget"]["estimated_tokens"] = max(1, (_json_bytes(packet) + 3) // 4)
    return packet
