"""Shared work-creation admission helpers.

This module lifts host-pressure admission from quoted commands to proposed
work starts. It does not schedule work; it gives launchers and planners one
small typed contract for allow, queue, summary-first, or explicit override.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORK_ADMISSION_SCHEMA = "work_creation_admission_decision_v0"
WORK_ADMISSION_COVERAGE_SCHEMA = "work_creation_admission_coverage_v0"
HELPER_LEASE_ADMISSION_SCHEMA = "helper_lease_admission_receipt_v1"
HELPER_OWNER_RELEASE_REQUEST_SCHEMA = "helper_owner_release_request_v1"
OWNER_RELEASE_RESULT_SCHEMA = "owner_release_result_receipt_v1"
BACKGROUND_LOOP_DOWNSHIFT_SCHEMA = "background_loop_downshift_receipt_v1"
RESIDENT_PRESSURE_RELIEF_WINDOW_SCHEMA = "resident_pressure_relief_window_v1"
RESIDENT_RELIEF_EFFECT_SCHEMA = "resident_relief_effect_receipt_v1"
RESIDENT_RELIEF_LADDER_SCHEMA = "resident_relief_ladder_state_v1"
SESSION_PRESSURE_RANK_SCHEMA = "session_pressure_rank_v1"
SESSION_YIELD_REQUEST_SCHEMA = "session_yield_request_receipt_v1"
OWNER_YIELD_RESULT_SCHEMA = "owner_yield_result_receipt_v1"
SESSION_YIELD_CONTROL_SURFACE_SCHEMA = "session_yield_control_surface_v1"
RESIDENT_RELIEF_ESCALATION_WINDOW_SCHEMA = "resident_relief_escalation_window_v1"
ACCEPTED_RESIDENT_RELIEF_WINDOW_SCHEMA = "accepted_resident_relief_window_v1"
PRESSURE_BUDGET_RELIEF_SCHEMA = "pressure_budget_relief_decision_v1"
ADMISSION_POLICY_VALUES = ("auto", "warn", "off")
ADMISSION_TEMPFAIL = 75

CHEAP_READ = "cheap_read"
ATTACH_EXISTING = "attach_existing"
EDIT_LIGHT_PATCH = "edit_light_patch"
SUMMARY_FIRST_DIAGNOSTIC = "summary_first_diagnostic"
FORCE_LIVE_DIAGNOSTIC = "force_live_diagnostic"
VALIDATION_OR_BUILD = "validation_or_build"
RENDER_CAPTURE = "render_capture"
PROJECTION_REBUILD = "projection_rebuild"
AUTOMATION_RESUME = "automation_resume"
TRANCHE_SUBPHASE_WAVE = "tranche_subphase_wave"
UNCATALOGUED_HEAVY_WORK = "uncatalogued_heavy_work"

PLAYWRIGHT_MCP = "playwright_mcp"
CODEX_STDIO_APP_SERVER = "codex_stdio_app_server"
CHROME_DEVTOOLS_MCP = "chrome_devtools_mcp"
VITE_DEV_SERVER = "vite_dev_server"
OTHER_TOOL_BRIDGE = "other_tool_bridge"

HELPER_LEASE_KINDS = (
    PLAYWRIGHT_MCP,
    CODEX_STDIO_APP_SERVER,
    CHROME_DEVTOOLS_MCP,
    VITE_DEV_SERVER,
    OTHER_TOOL_BRIDGE,
)

AGENT_OBSERVABILITY_SAMPLER = "agent_observability_sampler"
STATION_POLLING = "station_polling"
PROJECTION_REBUILD_LOOP = "projection_rebuild_loop"
VITE_DEV_SERVER_WATCHER = "vite_dev_server_watcher"
MCP_HELPER_KEEPALIVE = "mcp_helper_keepalive"
TRACE_IMPORT_REFRESH = "trace_import_refresh"
OTHER_BACKGROUND_LOOP = "other_background_loop"

BACKGROUND_LOOP_KINDS = (
    AGENT_OBSERVABILITY_SAMPLER,
    STATION_POLLING,
    PROJECTION_REBUILD_LOOP,
    VITE_DEV_SERVER_WATCHER,
    MCP_HELPER_KEEPALIVE,
    TRACE_IMPORT_REFRESH,
    OTHER_BACKGROUND_LOOP,
)

OWNER_RELEASE_RESULT_VALUES = (
    "accepted",
    "declined",
    "unsupported",
    "unreachable",
    "owner_unresolved",
    "not_supported",
)

BACKGROUND_DOWNSHIFT_RESULTS = (
    "applied",
    "unsupported",
    "blocked_by_owner",
    "not_applicable",
)

SESSION_YIELD_ACTIONS = (
    "yield",
    "hibernate",
    "release_tool_lease",
    "lower_poll_rate",
)

SESSION_YIELD_RESULTS = (
    "requested",
    "accepted",
    "declined",
    "unsupported",
    "unreachable",
    "owner_unresolved",
)

OWNER_YIELD_RESULT_VALUES = (
    "accepted",
    "declined",
    "unsupported",
    "unreachable",
    "owner_unresolved",
)

OWNER_YIELD_DELIVERY_VALUES = (
    "visible_to_owner",
    "queued_for_owner",
    "unreachable",
    "unsupported",
)

OWNER_YIELD_APPLIED_ACTIONS = (
    "none",
    "yielded",
    "hibernated",
    "released_tool_lease",
    "lowered_poll_rate",
)

PRESSURE_SENSITIVE_HELPER_LEASES = frozenset(
    {
        PLAYWRIGHT_MCP,
        CODEX_STDIO_APP_SERVER,
        CHROME_DEVTOOLS_MCP,
        VITE_DEV_SERVER,
        OTHER_TOOL_BRIDGE,
    }
)

DEGRADED_HELPER_LEASE_BUDGETS = {
    PLAYWRIGHT_MCP: 0,
    CODEX_STDIO_APP_SERVER: 1,
    CHROME_DEVTOOLS_MCP: 0,
    VITE_DEV_SERVER: 1,
    OTHER_TOOL_BRIDGE: 0,
}

NORMAL_HELPER_LEASE_BUDGETS = {
    PLAYWRIGHT_MCP: 2,
    CODEX_STDIO_APP_SERVER: 4,
    CHROME_DEVTOOLS_MCP: 2,
    VITE_DEV_SERVER: 1,
    OTHER_TOOL_BRIDGE: 2,
}

HEAVY_WORK_CLASSES = frozenset(
    {
        FORCE_LIVE_DIAGNOSTIC,
        VALIDATION_OR_BUILD,
        RENDER_CAPTURE,
        PROJECTION_REBUILD,
        AUTOMATION_RESUME,
        TRANCHE_SUBPHASE_WAVE,
        UNCATALOGUED_HEAVY_WORK,
    }
)

HOST_PRESSURE_WORKLOAD_BY_CLASS = {
    CHEAP_READ: "read_only_survey",
    ATTACH_EXISTING: "read_only_survey",
    EDIT_LIGHT_PATCH: "edit_light_patch",
    SUMMARY_FIRST_DIAGNOSTIC: "read_only_survey",
    FORCE_LIVE_DIAGNOSTIC: "repo_wide_search",
    VALIDATION_OR_BUILD: "test_build",
    RENDER_CAPTURE: "test_build",
    PROJECTION_REBUILD: "background_projection",
    AUTOMATION_RESUME: "mixed_realistic",
    TRANCHE_SUBPHASE_WAVE: "mixed_realistic",
    UNCATALOGUED_HEAVY_WORK: "mixed_realistic",
}

PROJECTION_WRITE_PROFILES = frozenset(
    {
        "agent_bootstrap_projection",
        "paper_module_index",
        "skill_catalog_projection",
        "annex_catalog_projection",
        "raw_seed_family_projection",
        "navigation_hologram_projection",
    }
)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_work_admission_policy(policy: str | None) -> str:
    value = str(policy or "auto").strip().lower()
    if value not in ADMISSION_POLICY_VALUES:
        expected = ", ".join(ADMISSION_POLICY_VALUES)
        raise ValueError(f"work admission policy must be one of: {expected}")
    return value


def is_heavy_work_class(work_class: str | None) -> bool:
    return str(work_class or "").strip() in HEAVY_WORK_CLASSES


def normalize_helper_lease_kind(lease_kind: str | None) -> str:
    value = str(lease_kind or "").strip().lower()
    if value not in HELPER_LEASE_KINDS:
        expected = ", ".join(HELPER_LEASE_KINDS)
        raise ValueError(f"helper lease kind must be one of: {expected}")
    return value


def normalize_background_loop_kind(loop_kind: str | None) -> str:
    value = str(loop_kind or "").strip().lower()
    if value not in BACKGROUND_LOOP_KINDS:
        expected = ", ".join(BACKGROUND_LOOP_KINDS)
        raise ValueError(f"background loop kind must be one of: {expected}")
    return value


def _profile_names(write_profiles: Sequence[Any]) -> list[str]:
    rows: list[str] = []
    for profile in write_profiles or []:
        if isinstance(profile, Mapping):
            value = profile.get("profile")
        else:
            value = profile
        token = str(value or "").strip()
        if token:
            rows.append(token)
    return rows


def classify_work_creation_request(
    *,
    paths: Sequence[str] = (),
    write_profiles: Sequence[Any] = (),
    recommended_lane: str | None = None,
    plane_home: str | None = None,
    requested_class: str | None = None,
) -> dict[str, Any]:
    """Classify a proposed work start into the admission vocabulary."""
    if requested_class:
        work_class = str(requested_class).strip()
        return {
            "schema": "work_creation_classification_v0",
            "work_class": work_class,
            "source": "requested_class",
            "heavy": is_heavy_work_class(work_class),
        }

    profile_names = _profile_names(write_profiles)
    path_rows = [str(path or "").strip() for path in paths or [] if str(path or "").strip()]
    lane = str(recommended_lane or "").strip()
    plane = str(plane_home or "").strip()
    lowered_paths = " ".join(path_rows).lower()

    if lane == "task_ledger_batch_event" or plane == "note_only":
        work_class = CHEAP_READ
        reason = "Task Ledger note-only or batch-event preview is cheap metadata work."
    elif lane == "subphase_wave":
        work_class = TRANCHE_SUBPHASE_WAVE
        reason = "Starting a subphase tranche can create new parallel work."
    elif any(profile in PROJECTION_WRITE_PROFILES for profile in profile_names):
        work_class = PROJECTION_REBUILD
        reason = "Write profile expands to generated projection rebuild outputs."
    elif plane in {"projection", "paper_module"}:
        work_class = PROJECTION_REBUILD
        reason = "Projection or paper-module work usually triggers builder refresh."
    elif plane == "test":
        work_class = VALIDATION_OR_BUILD
        reason = "Explicit test plane declares validation work."
    elif "station_render" in lowered_paths or "state/observability/renders" in lowered_paths:
        work_class = RENDER_CAPTURE
        reason = "Render capture creates browser/screenshot work."
    elif plane == "unknown" and lane in {"manual", ""}:
        work_class = EDIT_LIGHT_PATCH
        reason = "Manual-classification planning row; explicit launcher gaps must request uncatalogued_heavy_work."
    elif not path_rows and not profile_names:
        work_class = CHEAP_READ
        reason = "No write scope was proposed."
    else:
        work_class = EDIT_LIGHT_PATCH
        if any(
            token in lowered_paths
            for token in ("test_", "_test.", ".test.", "package.json", "vitest", "pytest")
        ):
            reason = (
                "Scoped edits to test/build-named files are not validation launches; "
                "heavy validation remains separately gated."
            )
        else:
            reason = "Ordinary scoped edit start; heavy validation remains separately gated."

    return {
        "schema": "work_creation_classification_v0",
        "work_class": work_class,
        "source": "heuristic",
        "reason": reason,
        "heavy": is_heavy_work_class(work_class),
        "path_count": len(path_rows),
        "write_profile_count": len(profile_names),
        "write_profiles": profile_names,
        "recommended_lane": lane or None,
        "plane_home": plane or None,
    }


def load_admission_consumer_coverage(repo_root: Path) -> dict[str, Any]:
    try:
        from system.lib.action_quote import _admission_consumer_coverage

        return _admission_consumer_coverage(repo_root)
    except Exception as exc:  # pragma: no cover - defensive read-model boundary.
        return {
            "schema": WORK_ADMISSION_COVERAGE_SCHEMA,
            "status": "unavailable",
            "error_class": type(exc).__name__,
            "summary": {
                "coverage_closure_status": "unknown",
                "blocking_gap_count": None,
            },
            "rows": [],
        }


def build_host_pressure_admission(
    repo_root: Path,
    *,
    workload_class: str,
    host_pressure_packet: Mapping[str, Any] | None = None,
    include_processes: bool = True,
) -> dict[str, Any]:
    trace_path = repo_root / "state/observability/agent_trace/events.jsonl"
    base: dict[str, Any] = {
        "schema": "work_creation_host_pressure_admission_v0",
        "status": "missing_trace_store" if not trace_path.is_file() else "available",
        "requested_workload_class": workload_class,
        "source": {
            "trace_path": str(trace_path.relative_to(repo_root))
            if trace_path.is_relative_to(repo_root)
            else str(trace_path),
            "event_limit": 500,
            "include_processes": include_processes,
            "process_rows_policy": (
                "sampled_for_launch_gate" if include_processes else "omitted_by_default"
            ),
        },
    }
    if host_pressure_packet is not None:
        packet = dict(host_pressure_packet)
        base["status"] = "available"
        base["source"]["packet_source"] = "supplied_fixture"
    elif not trace_path.is_file():
        base["should_block_run"] = False
        base["recommendation_effect"] = "no_admission_change"
        return base
    else:
        try:
            from system.lib.agent_observability import AgentTraceStore
            from system.lib.host_pressure import build_progress_pressure_packet_from_store

            store = AgentTraceStore(repo_root, max_history=500)
            packet = build_progress_pressure_packet_from_store(
                store,
                repo_root,
                event_limit=500,
                include_processes=include_processes,
                requested_workload_class=workload_class,
            )
        except Exception as exc:  # pragma: no cover - host adapters must degrade.
            base.update(
                {
                    "status": "unavailable",
                    "error_class": type(exc).__name__,
                    "should_block_run": False,
                    "recommendation_effect": "no_admission_change",
                }
            )
            return base

    summary = _as_mapping(packet.get("summary"))
    governor = _as_mapping(packet.get("mac_throttle_relief_governor"))
    admission = _as_mapping(governor.get("admission"))
    decision = str(admission.get("decision") or summary.get("admission_default_decision") or "unknown")
    load_shed_recommended = bool(
        summary.get("load_shed_recommended")
        or admission.get("local_load_shed_recommended")
        or _as_list(packet.get("load_shed_action_receipts"))
    )
    if decision == "queue_until_pressure_clears":
        effect = "defer_or_use_cheaper_summary"
    elif decision == "require_operator_override":
        effect = "operator_override_required"
    elif load_shed_recommended:
        effect = "prefer_cheaper_summary"
    else:
        effect = "allow"
    base.update(
        {
            "status": "available",
            "decision": decision,
            "recommendation_effect": effect,
            "should_block_run": decision in {"queue_until_pressure_clears", "require_operator_override"},
            "summary": {
                "active_agents": summary.get("active_agents"),
                "pressure_index": summary.get("pressure_index"),
                "bottleneck_class": summary.get("bottleneck_class"),
                "admission_default_decision": summary.get("admission_default_decision"),
                "load_shed_recommended": summary.get("load_shed_recommended"),
            },
            "admission": {
                "requested_workload_class": admission.get("requested_workload_class") or workload_class,
                "decision": decision,
                "reason": admission.get("reason"),
                "active_agents": admission.get("active_agents"),
                "heuristic_cap": admission.get("heuristic_cap"),
                "operator_override_required": admission.get("operator_override_required"),
            },
        }
    )
    return base


def build_work_admission_decision(
    repo_root: Path,
    *,
    work_class: str,
    policy: str = "auto",
    request_id: str | None = None,
    host_pressure_packet: Mapping[str, Any] | None = None,
    admission_consumer_coverage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_policy = normalize_work_admission_policy(policy)
    work = str(work_class or CHEAP_READ).strip() or CHEAP_READ
    heavy = is_heavy_work_class(work)
    workload_class = HOST_PRESSURE_WORKLOAD_BY_CLASS.get(work, "mixed_realistic")
    cheap_or_attach = work in {CHEAP_READ, ATTACH_EXISTING, EDIT_LIGHT_PATCH, SUMMARY_FIRST_DIAGNOSTIC}
    coverage_summary: Mapping[str, Any] = {}
    admission: Mapping[str, Any] = {
        "schema": "work_creation_host_pressure_admission_v0",
        "status": "not_consulted_for_cheap_work" if cheap_or_attach else "not_consulted",
        "requested_workload_class": workload_class,
        "should_block_run": False,
    }
    if not cheap_or_attach:
        coverage = dict(admission_consumer_coverage or load_admission_consumer_coverage(repo_root))
        coverage_summary = _as_mapping(coverage.get("summary"))
        admission = build_host_pressure_admission(
            repo_root,
            workload_class=workload_class,
            host_pressure_packet=host_pressure_packet,
        )
    base = {
        "schema": WORK_ADMISSION_SCHEMA,
        "request_id": request_id,
        "work_class": work,
        "host_pressure_workload_class": workload_class,
        "policy": normalized_policy,
        "heavy": heavy,
        "host_pressure_status": admission.get("status"),
        "host_pressure_decision": admission.get("decision"),
        "host_pressure_reason": _as_mapping(admission.get("admission")).get("reason"),
        "coverage_closure_status": coverage_summary.get("coverage_closure_status"),
        "coverage_blocking_gap_count": coverage_summary.get("blocking_gap_count"),
        "override_hint": "--host-pressure-policy=warn or --host-pressure-policy=off",
        "host_pressure_admission": admission,
        "admission_consumer_coverage_summary": dict(coverage_summary),
    }
    if normalized_policy == "off":
        return {
            **base,
            "result": "allow",
            "status": "skipped_by_policy",
            "allow": True,
            "new_heavy_work_launched": None,
        }
    if cheap_or_attach:
        return {
            **base,
            "result": "allow",
            "status": "cheap_or_attach_allowed",
            "allow": True,
            "new_heavy_work_launched": None,
        }
    if work == UNCATALOGUED_HEAVY_WORK:
        blocked_result = "explicit_override_required"
        if normalized_policy == "warn":
            return {
                **base,
                "result": "allow",
                "blocked_result": blocked_result,
                "status": "warn_only_uncatalogued_heavy_work",
                "allow": True,
                "new_heavy_work_launched": None,
            }
        return {
            **base,
            "result": blocked_result,
            "status": "blocked_uncatalogued_heavy_work",
            "allow": False,
            "new_heavy_work_launched": False,
            "reason": "Uncatalogued heavy work must be bound to quote coverage or explicitly overridden.",
        }
    should_block = heavy and bool(admission.get("should_block_run"))
    if not should_block:
        return {
            **base,
            "result": "allow",
            "status": "allowed_by_admission",
            "allow": True,
            "new_heavy_work_launched": None,
        }
    decision = str(admission.get("decision") or "")
    blocked_result = (
        "explicit_override_required"
        if decision == "require_operator_override"
        else "queue_until_pressure_clears"
    )
    if normalized_policy == "warn":
        return {
            **base,
            "result": "allow",
            "blocked_result": blocked_result,
            "status": "warn_only",
            "allow": True,
            "new_heavy_work_launched": None,
        }
    return {
        **base,
        "result": blocked_result,
        "status": "blocked",
        "allow": False,
        "new_heavy_work_launched": False,
    }


def _pressure_mode_from_admission(admission: Mapping[str, Any]) -> str:
    if admission.get("status") not in {None, "available"}:
        return "unknown"
    summary = _as_mapping(admission.get("summary"))
    body = _as_mapping(admission.get("admission"))
    decision = str(admission.get("decision") or body.get("decision") or "")
    bottleneck = str(summary.get("bottleneck_class") or "")
    memory_class = str(summary.get("memory_class") or "")
    if (
        bottleneck == "memory_pressure_swap_churn"
        or memory_class == "swap_rising"
        or decision in {"queue_until_pressure_clears", "require_operator_override"}
        or bool(summary.get("load_shed_recommended"))
    ):
        return "degraded"
    return "normal"


def _inventory_summary_from(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _as_mapping(value)
    if "summary" in payload:
        return _as_mapping(payload.get("summary"))
    before = _as_mapping(payload.get("before"))
    if before:
        return _as_mapping(before.get("inventory_summary"))
    return payload


def build_helper_lease_admission_decision(
    repo_root: Path,
    *,
    lease_kind: str,
    policy: str = "auto",
    request_id: str | None = None,
    requested_by: str | None = None,
    owner_status: str | None = None,
    host_pressure_packet: Mapping[str, Any] | None = None,
    inventory_summary: Mapping[str, Any] | None = None,
    current_lease_count: int | None = None,
) -> dict[str, Any]:
    """Gate persistent helper/tool leases under pressure-budget mode.

    This is the helper-lease sibling of work creation admission: callers should
    ask before allocating another Playwright/MCP/Codex helper when the resident
    helper set is already over budget or host pressure is degraded. It never
    signals or terminates a process.
    """
    normalized_policy = normalize_work_admission_policy(policy)
    lease = normalize_helper_lease_kind(lease_kind)
    admission = build_host_pressure_admission(
        repo_root,
        workload_class="mixed_realistic",
        host_pressure_packet=host_pressure_packet,
    )
    pressure_mode = _pressure_mode_from_admission(admission)
    summary = _inventory_summary_from(inventory_summary)
    kind_counts = _as_mapping(summary.get("kind_counts"))
    observed_count = (
        _as_int(current_lease_count)
        if current_lease_count is not None
        else _as_int(kind_counts.get(lease), 0)
    )
    degraded_budget = DEGRADED_HELPER_LEASE_BUDGETS.get(lease)
    normal_budget = NORMAL_HELPER_LEASE_BUDGETS.get(lease)
    budget = degraded_budget if pressure_mode == "degraded" else normal_budget
    budget_exhausted = budget is not None and observed_count >= budget
    degraded_budget_exhausted = (
        pressure_mode == "degraded"
        and degraded_budget is not None
        and observed_count >= degraded_budget
    )
    resident_budget_exhausted = (
        pressure_mode != "degraded"
        and normal_budget is not None
        and observed_count >= normal_budget
    )
    owner = str(owner_status or "unknown").strip() or "unknown"
    owner_unknown = owner in {"unknown", "unknown_parent", "unknown_parent_process", "parent_unknown"}
    sensitive = lease in PRESSURE_SENSITIVE_HELPER_LEASES
    should_block = sensitive and (
        degraded_budget_exhausted
        or resident_budget_exhausted
        or (pressure_mode == "degraded" and owner_unknown)
    )
    host_body = _as_mapping(admission.get("admission"))
    base: dict[str, Any] = {
        "schema": HELPER_LEASE_ADMISSION_SCHEMA,
        "request_id": request_id,
        "requested_lease_kind": lease,
        "requested_by": requested_by,
        "owner_status": owner,
        "policy": normalized_policy,
        "pressure_mode": pressure_mode,
        "host_pressure_status": admission.get("status"),
        "host_pressure_decision": admission.get("decision"),
        "host_pressure_reason": host_body.get("reason"),
        "helper_lease_budget": {
            "schema": "helper_lease_budget_v1",
            "mode": pressure_mode,
            "lease_kind": lease,
            "budget": budget,
            "normal_budget": normal_budget,
            "degraded_budget": degraded_budget,
            "current_count": observed_count,
            "budget_exhausted": budget_exhausted,
            "resident_budget_exhausted": resident_budget_exhausted,
            "degraded_budget_exhausted": degraded_budget_exhausted,
            "source": "tool_server_pressure_inventory_v1_summary_or_supplied_count",
        },
        "hygiene_summary": {
            "safe_close_candidate_count": _as_int(summary.get("candidate_safe_close_count"), 0),
            "requires_owner_check_count": _as_int(summary.get("requires_owner_check_count"), 0),
            "requires_owner_check_rss_mb": _as_float(summary.get("requires_owner_check_rss_mb"), 0.0),
            "active_owner_release_request_count": _as_int(
                summary.get("active_owner_release_request_count"),
                0,
            ),
            "active_owner_release_rss_mb": _as_float(
                summary.get("active_owner_release_rss_mb"),
                0.0,
            ),
        },
        "override_hint": "--host-pressure-policy=warn or --host-pressure-policy=off",
        "safety": {
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
            "no_active_session_terminated": True,
        },
    }
    if normalized_policy == "off":
        return {
            **base,
            "result": "allow",
            "status": "skipped_by_policy",
            "allow": True,
            "new_helper_lease_started": None,
            "next_action": "allow",
        }
    if not should_block:
        return {
            **base,
            "result": "allow",
            "status": "allowed_by_pressure_budget",
            "allow": True,
            "new_helper_lease_started": None,
            "next_action": "allow",
        }
    blocked_result = (
        "require_owner_override"
        if pressure_mode == "degraded" and owner_unknown
        else "queue_until_pressure_clears"
    )
    next_action = (
        "resolve_owner_before_helper_lease"
        if pressure_mode == "degraded" and owner_unknown
        else (
            "reuse_existing_or_release_helper_before_start"
            if resident_budget_exhausted
            else "queue_helper_lease_until_pressure_clears"
        )
    )
    status = "blocked_resident_helper_budget_exhausted" if resident_budget_exhausted else "blocked"
    if normalized_policy == "warn":
        return {
            **base,
            "result": "allow",
            "blocked_result": blocked_result,
            "status": "warn_only",
            "allow": True,
            "new_helper_lease_started": None,
            "next_action": next_action,
        }
    return {
        **base,
        "result": blocked_result,
        "status": status,
        "allow": False,
        "new_helper_lease_started": False,
        "next_action": next_action,
    }


def build_helper_owner_release_request(
    *,
    process_kind: str,
    owner_status: str,
    rss_mb_total: float | int | None = None,
    target_owner: str | None = None,
    pressure_mode: str = "degraded",
) -> dict[str, Any]:
    """Build the non-destructive owner-release receipt for resident helpers."""
    owner = str(owner_status or "unknown").strip() or "unknown"
    active_owner = owner in {"active_session", "active_codex_parent_chain", "active_claude_parent_chain"}
    unknown_owner = owner in {"unknown", "unknown_parent", "unknown_parent_process", "parent_unknown"}
    launchd_detached = owner == "launchd_detached"
    if active_owner:
        permitted_action = "ask_owner_to_release"
        requested_action = "release_tool_lease"
        result = "requested"
    elif unknown_owner:
        permitted_action = "resolve_owner"
        requested_action = "resolve_owner_before_release"
        result = "owner_unresolved"
    elif launchd_detached:
        permitted_action = "defer_to_strict_orphan_reaper"
        requested_action = "use_safe_close_predicate_if_candidate"
        result = "not_sent"
    else:
        permitted_action = "keep"
        requested_action = "keep"
        result = "not_supported"
    return {
        "schema": HELPER_OWNER_RELEASE_REQUEST_SCHEMA,
        "process_kind": process_kind,
        "owner_status": owner,
        "target_owner": target_owner,
        "pressure_mode": pressure_mode,
        "rss_mb_total": _as_float(rss_mb_total),
        "permitted_action": permitted_action,
        "requested_action": requested_action,
        "result": result,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def build_owner_release_result_receipt(
    *,
    release_request: Mapping[str, Any],
    result: str,
    result_note: str | None = None,
) -> dict[str, Any]:
    """Bind an owner-release request to a non-destructive result state."""
    request = _as_mapping(release_request)
    requested_result = str(result or "").strip().lower()
    if requested_result not in OWNER_RELEASE_RESULT_VALUES:
        expected = ", ".join(OWNER_RELEASE_RESULT_VALUES)
        raise ValueError(f"owner release result must be one of: {expected}")
    owner_status = str(request.get("owner_status") or "unknown").strip() or "unknown"
    owner_unresolved = owner_status in {
        "unknown",
        "unknown_parent",
        "unknown_parent_process",
        "parent_unknown",
    }
    effective_result = "owner_unresolved" if owner_unresolved and requested_result == "accepted" else requested_result
    release_confirmed = effective_result == "accepted"
    return {
        "schema": OWNER_RELEASE_RESULT_SCHEMA,
        "request_schema": request.get("schema"),
        "process_kind": request.get("process_kind"),
        "owner_status": owner_status,
        "target_owner": request.get("target_owner"),
        "requested_action": request.get("requested_action"),
        "result": effective_result,
        "requested_result": requested_result,
        "release_confirmed": release_confirmed,
        "result_note": result_note,
        "status": "release_confirmed" if release_confirmed else effective_result,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def _default_downshift_action(loop: str) -> str:
    if loop == PROJECTION_REBUILD_LOOP:
        return "defer_index_rebuild"
    if loop == TRACE_IMPORT_REFRESH:
        return "skip_optional_refresh"
    return "lower_poll_rate"


def build_background_loop_downshift_receipt(
    *,
    loop_kind: str,
    owner_surface: str,
    pressure_mode: str = "degraded",
    result: str = "unsupported",
    action: str | None = None,
    duration_s: int | None = 600,
    effective_interval_s: float | int | None = None,
    restore_condition: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Record a reversible resident-pressure downshift attempt for a loop."""
    loop = normalize_background_loop_kind(loop_kind)
    normalized_result = str(result or "").strip().lower()
    if normalized_result not in BACKGROUND_DOWNSHIFT_RESULTS:
        expected = ", ".join(BACKGROUND_DOWNSHIFT_RESULTS)
        raise ValueError(f"background downshift result must be one of: {expected}")
    mode = str(pressure_mode or "unknown").strip() or "unknown"
    selected_action = action or _default_downshift_action(loop)
    applied = normalized_result == "applied"
    return {
        "schema": BACKGROUND_LOOP_DOWNSHIFT_SCHEMA,
        "issued_at": _now_iso(),
        "loop_kind": loop,
        "owner_surface": str(owner_surface or ""),
        "pressure_mode": mode,
        "action": selected_action,
        "duration_s": _as_int(duration_s, 600),
        "effective_interval_s": _as_float(effective_interval_s, 15.0)
        if effective_interval_s is not None
        else None,
        "result": normalized_result,
        "applied": applied,
        "restore_condition": list(
            restore_condition
            or [
                "memory_pressure_not_swap_rising",
                "swap_delta_falls",
                "operator_override",
            ]
        ),
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def _packet_metrics(packet: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _as_mapping(packet)
    summary = _as_mapping(payload.get("summary"))
    host = _as_mapping(payload.get("host"))
    memory = _as_mapping(host.get("memory"))
    swap = _as_mapping(memory.get("swap"))
    return {
        "active_agents": summary.get("active_agents"),
        "pressure_index": _as_float(summary.get("pressure_index"), 0.0),
        "progress_per_pressure": _as_float(summary.get("progress_per_pressure"), 0.0),
        "bottleneck_class": summary.get("bottleneck_class"),
        "memory_class": memory.get("memory_class"),
        "swap_used_mb": _as_float(swap.get("used_mb"), 0.0),
    }


def _strict_safe_close_count(rows: Sequence[Any]) -> int:
    count = 0
    for row in rows or []:
        if isinstance(row, Mapping):
            result = str(row.get("result") or row.get("status") or "")
            if result in {"closed", "terminated", "success"}:
                count += 1
        elif row:
            count += 1
    return count


def _owner_status_unresolved(owner_status: str | None) -> bool:
    owner = str(owner_status or "unknown").strip() or "unknown"
    return owner in {
        "unknown",
        "unknown_parent",
        "unknown_parent_process",
        "parent_unknown",
    }


def build_session_yield_request_receipt(
    *,
    target_id: str | None,
    request_id: str | None = None,
    target_class: str = "idle_session",
    requested_action: str = "yield",
    owner_status: str = "active_session",
    pressure_mode: str = "degraded",
    result: str = "requested",
    helper_rss_mb: float | int | None = None,
    recent_progress_units: float | int | None = None,
    result_note: str | None = None,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Record a non-destructive owner-visible session/tool yield request."""
    action = str(requested_action or "yield").strip().lower()
    if action not in SESSION_YIELD_ACTIONS:
        expected = ", ".join(SESSION_YIELD_ACTIONS)
        raise ValueError(f"session yield action must be one of: {expected}")
    requested_result = str(result or "requested").strip().lower()
    if requested_result not in SESSION_YIELD_RESULTS:
        expected = ", ".join(SESSION_YIELD_RESULTS)
        raise ValueError(f"session yield result must be one of: {expected}")
    owner = str(owner_status or "unknown").strip() or "unknown"
    unresolved = _owner_status_unresolved(owner)
    effective_result = "owner_unresolved" if unresolved and requested_result == "accepted" else requested_result
    accepted = effective_result == "accepted"
    return {
        "schema": SESSION_YIELD_REQUEST_SCHEMA,
        "request_id": request_id,
        "issued_at": issued_at or _now_iso(),
        "pressure_mode": str(pressure_mode or "unknown").strip() or "unknown",
        "target_id": str(target_id or "unknown"),
        "target_class": str(target_class or "unknown").strip() or "unknown",
        "owner_status": owner,
        "requested_action": action,
        "result": effective_result,
        "requested_result": requested_result,
        "accepted": accepted,
        "helper_rss_mb": _as_float(helper_rss_mb),
        "recent_progress_units": _as_float(recent_progress_units),
        "result_note": result_note,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def _session_yield_request_payload(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _as_mapping(value)
    nested = _as_mapping(payload.get("session_yield_request"))
    return nested or payload


def build_owner_yield_result_receipt(
    *,
    yield_request: Mapping[str, Any],
    result: str = "accepted",
    applied_action: str = "none",
    delivery: str = "visible_to_owner",
    result_note: str | None = None,
) -> dict[str, Any]:
    """Close a session-yield request with the owner's visible result."""
    request = _session_yield_request_payload(yield_request)
    owner = str(request.get("owner_status") or "unknown").strip() or "unknown"
    requested_result = str(result or "accepted").strip().lower()
    if requested_result not in OWNER_YIELD_RESULT_VALUES:
        expected = ", ".join(OWNER_YIELD_RESULT_VALUES)
        raise ValueError(f"owner yield result must be one of: {expected}")
    delivery_state = str(delivery or "visible_to_owner").strip().lower()
    if delivery_state not in OWNER_YIELD_DELIVERY_VALUES:
        expected = ", ".join(OWNER_YIELD_DELIVERY_VALUES)
        raise ValueError(f"owner yield delivery must be one of: {expected}")
    requested_applied_action = str(applied_action or "none").strip().lower()
    if requested_applied_action not in OWNER_YIELD_APPLIED_ACTIONS:
        expected = ", ".join(OWNER_YIELD_APPLIED_ACTIONS)
        raise ValueError(f"owner yield applied action must be one of: {expected}")
    unresolved = _owner_status_unresolved(owner)
    effective_result = "owner_unresolved" if unresolved and requested_result == "accepted" else requested_result
    accepted = effective_result == "accepted"
    effective_applied_action = requested_applied_action if accepted else "none"
    applied = accepted and effective_applied_action != "none"
    if effective_result == "owner_unresolved":
        status = "owner_unresolved"
    elif accepted and applied:
        status = "accepted_and_applied"
    elif accepted:
        status = "accepted_not_applied"
    else:
        status = effective_result
    return {
        "schema": OWNER_YIELD_RESULT_SCHEMA,
        "request_id": request.get("request_id"),
        "target_id": request.get("target_id"),
        "target_class": request.get("target_class"),
        "requested_action": request.get("requested_action"),
        "owner_status": owner,
        "pressure_mode": request.get("pressure_mode"),
        "delivery": delivery_state,
        "result": effective_result,
        "requested_result": requested_result,
        "accepted": accepted,
        "applied": applied,
        "applied_action": effective_applied_action,
        "requested_applied_action": requested_applied_action,
        "result_note": result_note,
        "status": status,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def build_session_yield_control_surface(
    *,
    request_events: Sequence[Mapping[str, Any]] = (),
    result_events: Sequence[Mapping[str, Any]] = (),
    background_loop_downshift: Mapping[str, Any] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Summarize pending, accepted, and applied resident-yield control state."""
    requests = [_session_yield_request_payload(row) for row in request_events or []]
    results = []
    for row in result_events or []:
        payload = _as_mapping(row)
        result = _as_mapping(payload.get("owner_yield_result")) or payload
        if result:
            results.append(result)
    latest_result_by_request: dict[str, Mapping[str, Any]] = {}
    latest_result_by_target: dict[str, Mapping[str, Any]] = {}
    for result in results:
        request_id = str(result.get("request_id") or "")
        target_id = str(result.get("target_id") or "")
        if request_id:
            latest_result_by_request[request_id] = result
        if target_id:
            latest_result_by_target[target_id] = result
    pending: list[Mapping[str, Any]] = []
    resolved: list[Mapping[str, Any]] = []
    for request in requests:
        request_id = str(request.get("request_id") or "")
        target_id = str(request.get("target_id") or "")
        result = latest_result_by_request.get(request_id) or latest_result_by_target.get(target_id)
        if result:
            resolved.append(request)
        elif request.get("result") == "requested":
            pending.append(request)
    accepted_results = [row for row in results if row.get("result") == "accepted"]
    applied_results = [row for row in accepted_results if row.get("applied") is True]
    unsupported_results = [row for row in results if row.get("result") in {"unsupported", "unreachable", "owner_unresolved"}]
    owner_unresolved_results = [row for row in results if row.get("result") == "owner_unresolved"]
    bounded_limit = max(1, int(limit or 1))
    downshift = _as_mapping(background_loop_downshift)
    downshift_active = downshift.get("result") == "applied" and downshift.get("applied") is True
    station_downshift_active = bool(downshift_active and downshift.get("loop_kind") == "station_polling")
    applied_result_count = len(applied_results)
    accepted_actuator_count = applied_result_count + (1 if station_downshift_active else 0)
    if accepted_actuator_count:
        recovery_verdict = "accepted_actuator_available"
    elif pending:
        recovery_verdict = "no_accepted_actuator"
    elif unsupported_results:
        recovery_verdict = "owner_release_unsupported"
    elif downshift_active:
        recovery_verdict = "prior_downshift_only"
    else:
        recovery_verdict = "no_pending_request"
    return {
        "schema": SESSION_YIELD_CONTROL_SURFACE_SCHEMA,
        "latest_requests": list(reversed(requests))[:bounded_limit],
        "latest_results": list(reversed(results))[:bounded_limit],
        "pending_requests": list(reversed(pending))[:bounded_limit],
        "resolved_requests": list(reversed(resolved))[:bounded_limit],
        "accepted_results": list(reversed(accepted_results))[:bounded_limit],
        "applied_results": list(reversed(applied_results))[:bounded_limit],
        "unsupported_results": list(reversed(unsupported_results))[:bounded_limit],
        "owner_unresolved_results": list(reversed(owner_unresolved_results))[:bounded_limit],
        "background_loop_downshift": dict(downshift) if downshift else None,
        "station_downshift_active": station_downshift_active,
        "accepted_actuator_count": accepted_actuator_count,
        "recovery_verdict": recovery_verdict,
        "counts": {
            "requests": len(requests),
            "request_count": len(requests),
            "results": len(results),
            "result_count": len(results),
            "pending_requests": len(pending),
            "pending_request_count": len(pending),
            "accepted_results": len(accepted_results),
            "accepted_result_count": len(accepted_results),
            "applied_results": len(applied_results),
            "applied_result_count": applied_result_count,
            "unsupported_results": len(unsupported_results),
            "unsupported_result_count": len(unsupported_results),
            "owner_unresolved_count": len(owner_unresolved_results),
        },
        "policy": {
            "requested_is_not_accepted": True,
            "accepted_without_applied_action_is_not_relief": True,
            "unsupported_is_not_relief": True,
            "owner_unresolved_cannot_accept": True,
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def build_session_pressure_rank(
    sessions: Sequence[Mapping[str, Any]],
    *,
    limit: int = 12,
) -> dict[str, Any]:
    """Rank session/tool owners for safe yield requests under host pressure."""
    rows: list[dict[str, Any]] = []
    for row in sessions or []:
        session = _as_mapping(row)
        owner_status = str(session.get("owner_status") or "unknown").strip() or "unknown"
        helper_rss = _as_float(session.get("helper_rss_mb") or session.get("rss_mb"), 0.0)
        progress = _as_float(session.get("recent_progress_units"), 0.0)
        idle_age_s = _as_float(session.get("idle_age_s"), 0.0)
        heartbeat_age_s = _as_float(session.get("last_heartbeat_age_s"), 0.0)
        active_claims = _as_int(session.get("active_claim_count"), 0)
        priority_hint = str(session.get("operator_priority_hint") or "").strip().lower()
        unresolved = _owner_status_unresolved(owner_status)
        productive = progress >= 10.0 or active_claims >= 3 or priority_hint in {"critical", "operator_critical"}
        score = helper_rss + min(idle_age_s / 10.0, 120.0) + min(heartbeat_age_s / 20.0, 60.0)
        score -= min(progress * 8.0, 160.0)
        score -= min(active_claims * 12.0, 120.0)
        if unresolved:
            candidate_action = "owner_unresolved"
        elif productive:
            candidate_action = "keep"
        elif helper_rss >= 256.0 and progress < 5.0:
            candidate_action = "ask_release_tool_lease"
        elif idle_age_s >= 600.0 and progress < 5.0:
            candidate_action = "ask_yield"
        elif helper_rss >= 512.0:
            candidate_action = "ask_release_tool_lease"
        else:
            candidate_action = "keep"
        rows.append(
            {
                "session_id": session.get("session_id") or session.get("target_id") or "unknown",
                "owner_status": owner_status,
                "helper_rss_mb": helper_rss,
                "recent_progress_units": progress,
                "idle_age_s": idle_age_s,
                "last_heartbeat_age_s": heartbeat_age_s,
                "active_claim_count": active_claims,
                "operator_priority_hint": priority_hint or None,
                "pressure_score": round(score, 3),
                "candidate_action": candidate_action,
                "safety": {
                    "no_process_signal_sent": True,
                    "no_unknown_owner_killed": True,
                    "no_active_session_terminated": True,
                },
            }
        )
    rows.sort(key=lambda item: item["pressure_score"], reverse=True)
    bounded = rows[: max(1, int(limit or 1))]
    for index, row in enumerate(bounded, start=1):
        row["rank"] = index
    return {
        "schema": SESSION_PRESSURE_RANK_SCHEMA,
        "row_count": len(rows),
        "returned_count": len(bounded),
        "rows": bounded,
        "policy": {
            "reduce_low_progress_resident_pressure_first": True,
            "productive_active_sessions_are_not_penalized_for_activity_alone": True,
            "unknown_owner_requires_resolution_not_termination": True,
        },
    }


def build_resident_pressure_relief_window(
    *,
    before_packet: Mapping[str, Any],
    after_packet: Mapping[str, Any] | None = None,
    owner_release_results: Sequence[Mapping[str, Any]] = (),
    background_downshifts: Sequence[Mapping[str, Any]] = (),
    strict_safe_closes: Sequence[Mapping[str, Any]] = (),
    blocked_work_starts: int = 0,
    blocked_helper_leases: int = 0,
    workload_mix_changed: bool = False,
) -> dict[str, Any]:
    """Summarize whether resident-pressure actuators produced recovery."""
    release_results = [_as_mapping(row) for row in owner_release_results or []]
    downshift_rows = [_as_mapping(row) for row in background_downshifts or []]
    accepted_releases = sum(1 for row in release_results if row.get("result") == "accepted")
    applied_downshifts = sum(1 for row in downshift_rows if row.get("result") == "applied")
    safe_close_count = _strict_safe_close_count(strict_safe_closes)
    resident_actuator_count = accepted_releases + applied_downshifts + safe_close_count
    before = _packet_metrics(before_packet)
    after = _packet_metrics(after_packet)
    if resident_actuator_count == 0:
        verdict = "no_resident_actuator"
        status = "resident_relief_not_applied"
    elif after_packet is None:
        verdict = "pending_recheck"
        status = "resident_relief_recheck_pending"
    elif workload_mix_changed:
        verdict = "inconclusive_workload_mix_changed"
        status = "inconclusive"
    else:
        pressure_delta = after["pressure_index"] - before["pressure_index"]
        swap_delta = after["swap_used_mb"] - before["swap_used_mb"]
        progress_delta = after["progress_per_pressure"] - before["progress_per_pressure"]
        bottleneck_cleared = (
            before.get("bottleneck_class") == "memory_pressure_swap_churn"
            and after.get("bottleneck_class") != "memory_pressure_swap_churn"
        )
        pressure_improved = pressure_delta <= -0.1 or swap_delta <= -64.0 or bottleneck_cleared
        partial_pressure_improved = (
            swap_delta <= -8.0
            or progress_delta >= max(before["progress_per_pressure"] * 0.02, 1.0)
        )
        progress_held = after["progress_per_pressure"] >= before["progress_per_pressure"] * 0.9
        pressure_worse = pressure_delta >= 0.1 or swap_delta >= 64.0
        progress_collapsed = after["progress_per_pressure"] < before["progress_per_pressure"] * 0.8
        if pressure_improved and progress_held:
            verdict = "improved"
        elif pressure_worse or progress_collapsed:
            verdict = "worse"
        elif partial_pressure_improved and progress_held:
            verdict = "partial_improved"
        else:
            verdict = "unchanged"
        status = verdict
    return {
        "schema": RESIDENT_PRESSURE_RELIEF_WINDOW_SCHEMA,
        "status": status,
        "verdict": verdict,
        "front_door_blocks_not_counted_as_resident_relief": True,
        "actuators": {
            "blocked_work_starts": _as_int(blocked_work_starts),
            "blocked_helper_leases": _as_int(blocked_helper_leases),
            "owner_release_results": len(release_results),
            "accepted_owner_releases": accepted_releases,
            "background_downshifts": len(downshift_rows),
            "applied_background_downshifts": applied_downshifts,
            "strict_safe_closes": safe_close_count,
            "resident_actuator_count": resident_actuator_count,
        },
        "before": before,
        "after": after if after_packet is not None else None,
        "workload_mix_changed": bool(workload_mix_changed),
        "effect_deltas": {
            "pressure_index": round(after["pressure_index"] - before["pressure_index"], 3)
            if after_packet is not None
            else None,
            "swap_used_mb": round(after["swap_used_mb"] - before["swap_used_mb"], 3)
            if after_packet is not None
            else None,
            "progress_per_pressure": round(
                after["progress_per_pressure"] - before["progress_per_pressure"],
                3,
            )
            if after_packet is not None
            else None,
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def build_resident_relief_effect_receipt(
    *,
    relief_window: Mapping[str, Any],
    actuator_class: str = "background_loop_downshift",
    actuator_id: str | None = None,
    baseline_receipt_id: str | None = None,
) -> dict[str, Any]:
    """Convert one relief window into an escalation-ready effect data point."""
    window = _as_mapping(relief_window)
    verdict = str(window.get("verdict") or "unknown")
    before = _as_mapping(window.get("before"))
    after = _as_mapping(window.get("after"))
    residual_bottleneck = after.get("bottleneck_class") or before.get("bottleneck_class")
    if verdict in {"improved", "recovered"} and residual_bottleneck != "memory_pressure_swap_churn":
        effect = "recovered"
    elif verdict in {"improved", "partial_improved", "partial_not_recovered"}:
        effect = "partial"
    elif verdict == "worse":
        effect = "worse"
    elif verdict in {"no_resident_actuator", "no_second_resident_actuator"}:
        effect = "not_applied"
    else:
        effect = "unchanged"
    next_escalation_required = effect != "recovered" and residual_bottleneck == "memory_pressure_swap_churn"
    return {
        "schema": RESIDENT_RELIEF_EFFECT_SCHEMA,
        "baseline_receipt_id": baseline_receipt_id,
        "actuator_class": str(actuator_class or "unknown"),
        "actuator_id": actuator_id,
        "window_schema": window.get("schema"),
        "window_verdict": verdict,
        "effect": effect,
        "residual_bottleneck": residual_bottleneck,
        "next_escalation_required": next_escalation_required,
        "deltas": _as_mapping(window.get("effect_deltas")),
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def build_resident_relief_ladder_state(
    *,
    host_pressure_packet: Mapping[str, Any],
    effect_receipts: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Choose the next reversible resident actuator after measured relief."""
    summary = _as_mapping(_as_mapping(host_pressure_packet).get("summary"))
    bottleneck = str(summary.get("bottleneck_class") or "unknown")
    pressure_active = bottleneck == "memory_pressure_swap_churn"
    effects = [_as_mapping(row) for row in effect_receipts or []]
    latest_effect = effects[-1] if effects else {}
    latest_status = str(latest_effect.get("effect") or "none")
    if not pressure_active:
        next_action = "record_normalized_no_action"
        selected_level = "none"
    elif latest_effect.get("next_escalation_required"):
        next_action = "select_next_resident_actuator"
        selected_level = "level_2"
    else:
        next_action = "apply_first_resident_actuator"
        selected_level = "level_1"
    return {
        "schema": RESIDENT_RELIEF_LADDER_SCHEMA,
        "pressure_active": pressure_active,
        "bottleneck_class": bottleneck,
        "latest_effect": latest_status,
        "selected_level": selected_level,
        "next_action": next_action,
        "levels": [
            {
                "level": "level_0",
                "actuator": "front_door_gates",
                "status": "already_landed",
            },
            {
                "level": "level_1",
                "actuator": "agent_observability_sampler_downshift",
                "status": "spent" if latest_effect else "available",
            },
            {
                "level": "level_2",
                "actuator": "station_polling_or_projection_refresh_downshift",
                "status": "next_candidate" if selected_level == "level_2" else "available",
            },
            {
                "level": "level_3",
                "actuator": "owner_visible_session_yield_or_helper_release",
                "status": "requires_owner_yield_bus",
            },
            {
                "level": "level_4",
                "actuator": "strict_safe_close_predicate_only",
                "status": "last_resort_existing_reaper_only",
            },
        ],
        "safety": {
            "session_yield_not_process_kill": True,
            "no_unknown_owner_killed": True,
        },
    }


def build_resident_relief_escalation_window(
    *,
    previous_effect_receipt: Mapping[str, Any] | None,
    before_packet: Mapping[str, Any],
    after_packet: Mapping[str, Any] | None = None,
    session_yield_results: Sequence[Mapping[str, Any]] = (),
    owner_release_results: Sequence[Mapping[str, Any]] = (),
    background_downshifts: Sequence[Mapping[str, Any]] = (),
    strict_safe_closes: Sequence[Mapping[str, Any]] = (),
    workload_mix_changed: bool = False,
) -> dict[str, Any]:
    """Measure escalation after a second resident actuator, not old gates."""
    yield_rows = [_as_mapping(row) for row in session_yield_results or []]
    release_rows = [_as_mapping(row) for row in owner_release_results or []]
    downshift_rows = [_as_mapping(row) for row in background_downshifts or []]
    accepted_yields = sum(1 for row in yield_rows if row.get("result") == "accepted")
    applied_yields = sum(1 for row in yield_rows if row.get("result") == "accepted" and row.get("applied") is True)
    accepted_releases = sum(1 for row in release_rows if row.get("result") == "accepted")
    applied_downshifts = sum(1 for row in downshift_rows if row.get("result") == "applied")
    safe_close_count = _strict_safe_close_count(strict_safe_closes)
    second_actuator_count = applied_yields + accepted_releases + applied_downshifts + safe_close_count
    before = _packet_metrics(before_packet)
    after = _packet_metrics(after_packet)
    if second_actuator_count == 0:
        verdict = "no_accepted_actuator"
        status = "resident_relief_escalation_not_applied"
    elif after_packet is None:
        verdict = "pending_recheck"
        status = "resident_relief_escalation_recheck_pending"
    elif workload_mix_changed:
        verdict = "inconclusive_workload_mix_changed"
        status = "inconclusive"
    else:
        pressure_delta = after["pressure_index"] - before["pressure_index"]
        swap_delta = after["swap_used_mb"] - before["swap_used_mb"]
        progress_delta = after["progress_per_pressure"] - before["progress_per_pressure"]
        bottleneck_cleared = (
            before.get("bottleneck_class") == "memory_pressure_swap_churn"
            and after.get("bottleneck_class") != "memory_pressure_swap_churn"
        )
        progress_held = after["progress_per_pressure"] >= before["progress_per_pressure"] * 0.9
        if bottleneck_cleared and progress_held:
            verdict = "recovered"
        elif (pressure_delta <= -0.1 or swap_delta <= -64.0) and progress_held:
            verdict = "partial_improved"
        elif (
            swap_delta <= -8.0
            or progress_delta >= max(before["progress_per_pressure"] * 0.02, 1.0)
        ) and progress_held:
            verdict = "partial_improved"
        elif pressure_delta >= 0.1 or swap_delta >= 64.0 or after["progress_per_pressure"] < before["progress_per_pressure"] * 0.8:
            verdict = "worse"
        else:
            verdict = "unchanged"
        status = verdict
    return {
        "schema": RESIDENT_RELIEF_ESCALATION_WINDOW_SCHEMA,
        "status": status,
        "verdict": verdict,
        "previous_effect": _as_mapping(previous_effect_receipt),
        "second_actuators": {
            "session_yield_results": len(yield_rows),
            "accepted_session_yields": accepted_yields,
            "applied_session_yields": applied_yields,
            "owner_release_results": len(release_rows),
            "accepted_owner_releases": accepted_releases,
            "background_downshifts": len(downshift_rows),
            "applied_background_downshifts": applied_downshifts,
            "strict_safe_closes": safe_close_count,
            "second_resident_actuator_count": second_actuator_count,
        },
        "before": before,
        "after": after if after_packet is not None else None,
        "workload_mix_changed": bool(workload_mix_changed),
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def build_accepted_resident_relief_window(
    *,
    previous_effect_receipt: Mapping[str, Any] | None,
    before_packet: Mapping[str, Any],
    after_packet: Mapping[str, Any] | None = None,
    owner_yield_results: Sequence[Mapping[str, Any]] = (),
    owner_release_results: Sequence[Mapping[str, Any]] = (),
    background_downshifts: Sequence[Mapping[str, Any]] = (),
    strict_safe_closes: Sequence[Mapping[str, Any]] = (),
    workload_mix_changed: bool = False,
) -> dict[str, Any]:
    """Alias the escalation window as the accepted-actuator proof surface."""
    window = build_resident_relief_escalation_window(
        previous_effect_receipt=previous_effect_receipt,
        before_packet=before_packet,
        after_packet=after_packet,
        session_yield_results=owner_yield_results,
        owner_release_results=owner_release_results,
        background_downshifts=background_downshifts,
        strict_safe_closes=strict_safe_closes,
        workload_mix_changed=workload_mix_changed,
    )
    return {
        **window,
        "schema": ACCEPTED_RESIDENT_RELIEF_WINDOW_SCHEMA,
        "accepted_actuator_required": True,
    }


def build_pressure_budget_relief_decision(
    *,
    host_pressure_packet: Mapping[str, Any],
    hygiene_receipt: Mapping[str, Any] | None = None,
    admission_coverage_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the next pressure-budget actuator after cleanup/admission checks."""
    host_admission = build_host_pressure_admission(
        Path("."),
        workload_class="mixed_realistic",
        host_pressure_packet=host_pressure_packet,
    )
    pressure_mode = _pressure_mode_from_admission(host_admission)
    hygiene_summary = _inventory_summary_from(hygiene_receipt)
    coverage = _as_mapping(admission_coverage_summary)
    safe_close_count = _as_int(hygiene_summary.get("candidate_safe_close_count"), 0)
    owner_check_count = _as_int(hygiene_summary.get("requires_owner_check_count"), 0)
    coverage_closed = coverage.get("coverage_closure_status") == "closed" and _as_int(
        coverage.get("blocking_gap_count"),
        0,
    ) == 0
    if pressure_mode == "normal":
        next_action = "record_normalized_no_action"
        status = "pressure_normalized"
    elif safe_close_count > 0:
        next_action = "run_strict_safe_close_then_remeasure"
        status = "safe_cleanup_available"
    elif owner_check_count > 0 and coverage_closed:
        next_action = "resident_pressure_relief_owner_release_or_downshift"
        status = "pressure_active_start_gate_working_no_safe_cleanup"
    elif owner_check_count > 0:
        next_action = "close_admission_coverage_then_helper_budget"
        status = "pressure_active_coverage_not_closed"
    else:
        next_action = "no_safe_action"
        status = "pressure_active_no_helper_pressure_rows"
    return {
        "schema": PRESSURE_BUDGET_RELIEF_SCHEMA,
        "pressure_mode": pressure_mode,
        "status": status,
        "next_action": next_action,
        "safe_close_candidate_count": safe_close_count,
        "requires_owner_check_count": owner_check_count,
        "coverage_closure_status": coverage.get("coverage_closure_status"),
        "coverage_blocking_gap_count": coverage.get("blocking_gap_count"),
        "front_door_gate_sufficient_for_recovery": False,
        "resident_relief_required": status == "pressure_active_start_gate_working_no_safe_cleanup",
        "safety": {
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }
