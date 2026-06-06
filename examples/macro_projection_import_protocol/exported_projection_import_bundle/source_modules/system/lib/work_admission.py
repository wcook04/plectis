"""Shared work-creation admission helpers.

This module lifts host-pressure admission from quoted commands to proposed
work starts. It does not schedule work; it gives launchers and planners one
small typed contract for allow, queue, summary-first, or explicit override.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORK_ADMISSION_SCHEMA = "work_creation_admission_decision_v0"
WORK_ADMISSION_COVERAGE_SCHEMA = "work_creation_admission_coverage_v0"
HELPER_LEASE_ADMISSION_SCHEMA = "helper_lease_admission_receipt_v1"
DEV_RESOURCE_LEASE_SCHEMA = "dev_resource_lease_v1"
DEV_RESOURCE_LEASE_ADMISSION_SCHEMA = "dev_resource_lease_admission_receipt_v1"
HELPER_OWNER_RELEASE_REQUEST_SCHEMA = "helper_owner_release_request_v1"
OWNER_RELEASE_RESULT_SCHEMA = "owner_release_result_receipt_v1"
BACKGROUND_LOOP_DOWNSHIFT_SCHEMA = "background_loop_downshift_receipt_v1"
RESIDENT_PRESSURE_RELIEF_WINDOW_SCHEMA = "resident_pressure_relief_window_v1"
RESIDENT_RELIEF_EFFECT_SCHEMA = "resident_relief_effect_receipt_v1"
RESIDENT_RELIEF_LADDER_SCHEMA = "resident_relief_ladder_state_v1"
SESSION_PRESSURE_RANK_SCHEMA = "session_pressure_rank_v1"
SESSION_YIELD_REQUEST_SCHEMA = "session_yield_request_receipt_v1"
SESSION_YIELD_COORDINATION_REQUEST_SCHEMA = "session_yield_coordination_request_v1"
OWNER_YIELD_RESULT_SCHEMA = "owner_yield_result_receipt_v1"
SESSION_YIELD_CONTROL_SURFACE_SCHEMA = "session_yield_control_surface_v1"
SESSION_YIELD_INBOX_SURFACE_SCHEMA = "session_yield_inbox_surface_v1"
RESIDENT_RELIEF_SETTLEMENT_WINDOW_SCHEMA = "resident_relief_settlement_window_v1"
RESIDENT_RELIEF_ESCALATION_WINDOW_SCHEMA = "resident_relief_escalation_window_v1"
ACCEPTED_RESIDENT_RELIEF_WINDOW_SCHEMA = "accepted_resident_relief_window_v1"
PRESSURE_BUDGET_RELIEF_SCHEMA = "pressure_budget_relief_decision_v1"
RESIDENT_RELIEF_PENDING_TTL_S = 30 * 60
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
PROJECTION_SETTLEMENT = "projection_settlement"
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

FRONTEND_DEV_SERVER = "frontend_dev_server"
BACKEND_API_SERVER = "backend_api_server"
BROWSER_HARNESS = "browser_harness"
VITE_PREVIEW_SERVER = "vite_preview_server"
PLAYWRIGHT_WEBSERVER = "playwright_webserver"
TEST_DATABASE = "test_database"
BUILD_CACHE = "build_cache"
PROJECT_GRAPH_DAEMON = "project_graph_daemon"
LONG_RUNNING_WATCHER = "long_running_watcher"
WATCHER = "watcher"
GENERATED_PROJECTION_BUILDER = "generated_projection_builder"
EXACT_COPY_REPAIR_RUNNER = "exact_copy_repair_runner"

DEV_RESOURCE_KINDS = (
    FRONTEND_DEV_SERVER,
    BACKEND_API_SERVER,
    BROWSER_HARNESS,
    VITE_DEV_SERVER,
    VITE_PREVIEW_SERVER,
    PLAYWRIGHT_WEBSERVER,
    TEST_DATABASE,
    BUILD_CACHE,
    PROJECT_GRAPH_DAEMON,
    LONG_RUNNING_WATCHER,
    WATCHER,
    GENERATED_PROJECTION_BUILDER,
    EXACT_COPY_REPAIR_RUNNER,
)

REUSABLE_DEV_RESOURCE_STATES = frozenset(
    {
        "running",
        "ready",
        "warm",
        "reusable",
        "attached",
        "shared",
    }
)

SHARED_DEV_RESOURCE_KINDS = frozenset(
    {
        FRONTEND_DEV_SERVER,
        BACKEND_API_SERVER,
        BROWSER_HARNESS,
        VITE_DEV_SERVER,
        VITE_PREVIEW_SERVER,
        PLAYWRIGHT_WEBSERVER,
        TEST_DATABASE,
        BUILD_CACHE,
        PROJECT_GRAPH_DAEMON,
        LONG_RUNNING_WATCHER,
        WATCHER,
        GENERATED_PROJECTION_BUILDER,
        EXACT_COPY_REPAIR_RUNNER,
    }
)

DEV_RESOURCE_CONFLICT_KEYS = (
    "port",
    "host",
    "base_url",
    "url",
    "workspace_root",
    "cwd",
    "repo",
    "repo_root",
    "worktree",
    "transaction_id",
    "command",
    "package_lock_hash",
    "env_hash",
    "route",
    "backend",
    "dirty_scope_hash",
    "service_name",
    "project",
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
    "release_after_landing",
    "cede_path",
    "claim_projection_refresh",
    "accept_settlement_group",
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
    "landed_or_released_paths",
    "ceded_path",
    "claimed_projection_refresh",
    "accepted_settlement_group",
)
RESIDENT_OWNER_YIELD_APPLIED_ACTIONS = (
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
    PROJECTION_SETTLEMENT: "edit_light_patch",
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


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return _as_int(value)


def _dedupe_strings(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _host_pressure_load_shed_target_classes(
    packet: Mapping[str, Any],
    governor: Mapping[str, Any],
) -> list[str]:
    targets: list[Any] = []
    compact_load_shed = _as_mapping(packet.get("load_shed"))
    targets.extend(_as_list(compact_load_shed.get("target_classes")))
    for action in _as_list(packet.get("load_shed_action_receipts")):
        action_body = _as_mapping(action)
        if action_body.get("target_class"):
            targets.append(action_body.get("target_class"))
    for action in _as_list(governor.get("load_shed_actions")):
        action_body = _as_mapping(action)
        if action_body.get("target_class"):
            targets.append(action_body.get("target_class"))
    return _dedupe_strings(targets)


def _host_pressure_resident_projection(
    packet: Mapping[str, Any],
    summary: Mapping[str, Any],
    load_shed_target_classes: Sequence[str],
) -> dict[str, Any]:
    resident_threads = _as_mapping(packet.get("resident_threads"))
    counts = _as_mapping(resident_threads.get("counts"))
    safe_to_nap = _as_optional_int(
        _first_present(summary.get("resident_safe_to_nap"), counts.get("safe_to_nap"))
    )
    safe_to_terminate = _as_optional_int(
        _first_present(
            summary.get("resident_safe_to_terminate_after_grace"),
            counts.get("safe_to_terminate_after_grace"),
        )
    )
    warm_claim_quiet = _as_optional_int(
        _first_present(summary.get("resident_warm_claim_quiet"), counts.get("warm_claim_quiet"))
    )
    safe_relief_count = sum(
        value
        for value in (safe_to_nap, safe_to_terminate, warm_claim_quiet)
        if isinstance(value, int)
    )
    resident_relief_recommended = "resident_work_ledger_threads" in load_shed_target_classes
    return {
        "schema_version": resident_threads.get("schema_version"),
        "status": _first_present(
            summary.get("resident_projection_status"),
            resident_threads.get("status"),
        ),
        "pressure_mode": _first_present(
            summary.get("resident_pressure_mode"),
            resident_threads.get("pressure_mode"),
        ),
        "resident_thread_count": _as_optional_int(
            _first_present(summary.get("resident_thread_count"), counts.get("resident_threads"))
        ),
        "hot_active_claims": _as_optional_int(
            _first_present(
                summary.get("resident_hot_active_claims"),
                counts.get("hot_active_claims"),
            )
        ),
        "warm_claim_quiet": warm_claim_quiet,
        "idle_unclaimed_over_10m": _as_optional_int(
            _first_present(
                summary.get("resident_idle_unclaimed_over_10m"),
                counts.get("idle_unclaimed_over_10m"),
            )
        ),
        "idle_unclaimed_over_30m": _as_optional_int(
            _first_present(
                summary.get("resident_idle_unclaimed_over_30m"),
                counts.get("idle_unclaimed_over_30m"),
            )
        ),
        "safe_to_nap": safe_to_nap,
        "safe_to_terminate_after_grace": safe_to_terminate,
        "safe_relief_count": safe_relief_count,
        "relief_recommended": resident_relief_recommended,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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


def normalize_dev_resource_kind(resource_kind: str | None) -> str:
    value = str(resource_kind or "").strip().lower()
    if value not in DEV_RESOURCE_KINDS:
        expected = ", ".join(DEV_RESOURCE_KINDS)
        raise ValueError(f"dev resource kind must be one of: {expected}")
    return value


def dev_resource_work_class(resource_kind: str | None) -> str:
    kind = normalize_dev_resource_kind(resource_kind)
    if kind == GENERATED_PROJECTION_BUILDER:
        return PROJECTION_REBUILD
    if kind == BROWSER_HARNESS:
        return RENDER_CAPTURE
    return VALIDATION_OR_BUILD


def _dev_resource_work_class_from_fingerprint(
    *,
    resource_kind: str,
    fingerprint: Mapping[str, Any],
) -> tuple[str, str]:
    default = dev_resource_work_class(resource_kind)
    override = str(fingerprint.get("admission_work_class") or "").strip()
    if not override:
        return default, "resource_kind"
    if override not in HOST_PRESSURE_WORKLOAD_BY_CLASS:
        expected = ", ".join(sorted(HOST_PRESSURE_WORKLOAD_BY_CLASS))
        raise ValueError(f"admission_work_class must be one of: {expected}")
    return override, "fingerprint.admission_work_class"


def _normalize_fingerprint_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_fingerprint_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
            if nested is not None
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_fingerprint_value(nested) for nested in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    token = str(value).strip()
    return token


def _dev_resource_fingerprint_hash(resource_kind: str, fingerprint: Mapping[str, Any]) -> str:
    body = {
        "resource_kind": resource_kind,
        "fingerprint": _normalize_fingerprint_value(fingerprint),
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "drl_" + hashlib.sha256(encoded).hexdigest()[:16]


def _dev_resource_lease_id(resource_kind: str, fingerprint_hash: str) -> str:
    token = str(fingerprint_hash or "").strip() or _dev_resource_fingerprint_hash(resource_kind, {})
    return "lease_" + token.removeprefix("drl_")[:16]


def _existing_dev_resource_rows(existing_leases: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in existing_leases or []:
        if not isinstance(raw, Mapping):
            continue
        try:
            kind = normalize_dev_resource_kind(str(raw.get("resource_kind") or raw.get("kind") or ""))
        except ValueError:
            continue
        fingerprint = _as_mapping(raw.get("fingerprint"))
        fingerprint_hash = str(raw.get("fingerprint_hash") or "").strip()
        if not fingerprint_hash:
            fingerprint_hash = _dev_resource_fingerprint_hash(kind, fingerprint)
        state = str(raw.get("state") or raw.get("status") or "unknown").strip().lower()
        rows.append(
            {
                **dict(raw),
                "resource_kind": kind,
                "fingerprint": dict(fingerprint),
                "fingerprint_hash": fingerprint_hash,
                "state": state,
                "lease_id": str(raw.get("lease_id") or raw.get("id") or _dev_resource_lease_id(kind, fingerprint_hash)),
            }
        )
    return rows


def _dev_resource_shared_safety(
    *,
    resource_kind: str,
    fingerprint: Mapping[str, Any],
    user_facing: bool,
    exclusive_required: bool,
    unsafe_host_or_proxy: bool,
) -> dict[str, Any]:
    host = str(fingerprint.get("host") or fingerprint.get("bind_host") or "").strip().lower()
    proxy = str(fingerprint.get("proxy") or fingerprint.get("proxy_url") or "").strip()
    user_visible = user_facing or bool(fingerprint.get("user_facing"))
    local_host = host in {"", "localhost", "127.0.0.1", "::1"}
    proxy_declared_safe = bool(fingerprint.get("proxy_is_agent_local") or fingerprint.get("proxy_is_safe"))
    unsafe = bool(unsafe_host_or_proxy or (host and not local_host and not user_visible) or (proxy and not proxy_declared_safe))
    shareable = (
        resource_kind in SHARED_DEV_RESOURCE_KINDS
        and not user_visible
        and not exclusive_required
        and not unsafe
    )
    return {
        "schema": "dev_resource_safety_v1",
        "agent_only": not user_visible,
        "user_facing": user_visible,
        "exclusive_required": bool(exclusive_required),
        "unsafe_host_or_proxy": unsafe,
        "host": host or None,
        "proxy_present": bool(proxy),
        "shareable": shareable,
        "safe_to_reuse": shareable,
        "safe_to_start": not unsafe,
        "policy": "reuse_agent_only_compatible_resources_isolate_user_facing_or_conflicting_resources",
    }


def _dev_resource_conflict_reasons(
    *,
    resource_kind: str,
    fingerprint: Mapping[str, Any],
    fingerprint_hash: str,
    existing_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for row in existing_rows:
        if str(row.get("resource_kind") or "") != resource_kind:
            continue
        if str(row.get("fingerprint_hash") or "") == fingerprint_hash:
            continue
        row_fingerprint = _as_mapping(row.get("fingerprint"))
        matched_keys = [
            key
            for key in DEV_RESOURCE_CONFLICT_KEYS
            if str(fingerprint.get(key) or "").strip()
            and str(fingerprint.get(key) or "").strip() == str(row_fingerprint.get(key) or "").strip()
        ]
        if matched_keys:
            conflicts.append(
                {
                    "lease_id": str(row.get("lease_id") or ""),
                    "state": str(row.get("state") or "unknown"),
                    "fingerprint_hash": str(row.get("fingerprint_hash") or ""),
                    "matched_keys": matched_keys,
                }
            )
    return conflicts


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
    load_shed_target_classes = _host_pressure_load_shed_target_classes(packet, governor)
    resident_projection = _host_pressure_resident_projection(
        packet,
        summary,
        load_shed_target_classes,
    )
    decision = str(admission.get("decision") or summary.get("admission_default_decision") or "unknown")
    load_shed_recommended = bool(
        summary.get("load_shed_recommended")
        or admission.get("local_load_shed_recommended")
        or _as_list(packet.get("load_shed_action_receipts"))
        or load_shed_target_classes
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
            "load_shed_target_classes": load_shed_target_classes,
            "resident_relief_recommended": resident_projection["relief_recommended"],
            "resident_threads": resident_projection,
            "summary": {
                "active_agents": summary.get("active_agents"),
                "pressure_index": summary.get("pressure_index"),
                "bottleneck_class": summary.get("bottleneck_class"),
                "admission_default_decision": summary.get("admission_default_decision"),
                "load_shed_recommended": summary.get("load_shed_recommended"),
                "load_shed_target_classes": load_shed_target_classes,
                "resident_thread_count": resident_projection["resident_thread_count"],
                "resident_hot_active_claims": resident_projection["hot_active_claims"],
                "resident_warm_claim_quiet": resident_projection["warm_claim_quiet"],
                "resident_idle_unclaimed_over_10m": resident_projection["idle_unclaimed_over_10m"],
                "resident_idle_unclaimed_over_30m": resident_projection["idle_unclaimed_over_30m"],
                "resident_safe_to_nap": resident_projection["safe_to_nap"],
                "resident_safe_to_terminate_after_grace": (
                    resident_projection["safe_to_terminate_after_grace"]
                ),
                "resident_safe_relief_count": resident_projection["safe_relief_count"],
                "resident_pressure_mode": resident_projection["pressure_mode"],
                "resident_projection_status": resident_projection["status"],
                "resident_relief_recommended": resident_projection["relief_recommended"],
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


def build_dev_resource_lease_decision(
    repo_root: Path,
    *,
    resource_kind: str,
    fingerprint: Mapping[str, Any] | None = None,
    existing_leases: Sequence[Mapping[str, Any]] | None = None,
    policy: str = "auto",
    request_id: str | None = None,
    requested_by: str | None = None,
    user_facing: bool = False,
    exclusive_required: bool = False,
    unsafe_host_or_proxy: bool = False,
    host_pressure_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide whether a dev resource should be reused, isolated, queued, or refused.

    The broker is intentionally admission-only: it never starts, signals, or
    stops a process. Callers use the returned lease fingerprint and action to
    attach to an existing server/daemon or to start an isolated one through
    their own launcher.
    """
    normalized_policy = normalize_work_admission_policy(policy)
    kind = normalize_dev_resource_kind(resource_kind)
    normalized_fingerprint = _normalize_fingerprint_value(_as_mapping(fingerprint))
    if not isinstance(normalized_fingerprint, Mapping):
        normalized_fingerprint = {}
    resource_work_class, resource_work_class_source = _dev_resource_work_class_from_fingerprint(
        resource_kind=kind,
        fingerprint=normalized_fingerprint,
    )
    fingerprint_hash = _dev_resource_fingerprint_hash(kind, normalized_fingerprint)
    lease_id = _dev_resource_lease_id(kind, fingerprint_hash)
    existing_rows = _existing_dev_resource_rows(existing_leases)
    safety = _dev_resource_shared_safety(
        resource_kind=kind,
        fingerprint=normalized_fingerprint,
        user_facing=user_facing,
        exclusive_required=exclusive_required,
        unsafe_host_or_proxy=unsafe_host_or_proxy,
    )
    compatible = [
        row
        for row in existing_rows
        if str(row.get("resource_kind") or "") == kind
        and str(row.get("fingerprint_hash") or "") == fingerprint_hash
        and str(row.get("state") or "") in REUSABLE_DEV_RESOURCE_STATES
    ]
    conflicts = _dev_resource_conflict_reasons(
        resource_kind=kind,
        fingerprint=normalized_fingerprint,
        fingerprint_hash=fingerprint_hash,
        existing_rows=existing_rows,
    )
    lease = {
        "schema": DEV_RESOURCE_LEASE_SCHEMA,
        "lease_id": lease_id,
        "resource_kind": kind,
        "fingerprint": dict(normalized_fingerprint),
        "fingerprint_hash": fingerprint_hash,
        "state": "proposed",
        "requested_by": requested_by,
        "request_id": request_id,
        "created_at": _now_iso(),
        "safety": safety,
    }
    base: dict[str, Any] = {
        "schema": DEV_RESOURCE_LEASE_ADMISSION_SCHEMA,
        "request_id": request_id,
        "requested_by": requested_by,
        "requested_resource_kind": kind,
        "policy": normalized_policy,
        "lease": lease,
        "existing_lease_count": len(existing_rows),
        "compatible_lease_count": len(compatible),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "resource_work_class": resource_work_class,
        "resource_work_class_source": resource_work_class_source,
        "safety": safety,
        "broker_contract": {
            "schema": "dev_resource_broker_contract_v1",
            "reuse_compatible_agent_only_resource": True,
            "isolate_conflicting_or_user_facing_resource": True,
            "refuse_unsafe_host_or_proxy": True,
            "host_pressure_gates_new_resource_start": True,
            "starts_or_stops_processes": False,
        },
    }
    if compatible and safety.get("safe_to_reuse"):
        row = compatible[0]
        return {
            **base,
            "result": "reuse_existing",
            "status": "reusable_compatible_resource_found",
            "allow": True,
            "resource_action": "attach_existing_compatible_resource",
            "new_resource_started": False,
            "new_resource_permitted": False,
            "lease_ref": str(row.get("lease_id") or ""),
            "reentry_condition": None,
        }
    if safety.get("unsafe_host_or_proxy"):
        return {
            **base,
            "result": "refuse_unsafe_host_or_proxy",
            "status": "blocked_unsafe_resource_binding",
            "allow": False,
            "resource_action": "refuse_until_allowed_hosts_or_proxy_are_explicit",
            "new_resource_started": False,
            "new_resource_permitted": False,
            "lease_ref": None,
            "reentry_condition": "declare localhost-only binding or mark the proxy as safe before requesting a shared dev resource",
        }
    admission = build_work_admission_decision(
        repo_root,
        work_class=resource_work_class,
        policy=normalized_policy,
        request_id=request_id,
        host_pressure_packet=host_pressure_packet,
    )
    host_blocked = not bool(admission.get("allow", True))
    if host_blocked:
        return {
            **base,
            "result": "queue_until_pressure_clears",
            "status": "blocked_by_host_pressure",
            "allow": False,
            "resource_action": "queue_new_resource_start",
            "new_resource_started": False,
            "new_resource_permitted": False,
            "lease_ref": None,
            "host_pressure_admission": admission,
            "resource_queue_item": {
                "schema": "dev_resource_queue_item_v1",
                "resource_kind": kind,
                "fingerprint_hash": fingerprint_hash,
                "work_class": resource_work_class,
                "queue_reason": "host_pressure_blocks_new_dev_resource",
                "reentry_condition": (
                    f"retry after host pressure admission allows {resource_work_class} starts"
                ),
            },
        }
    isolated = bool(conflicts or user_facing or exclusive_required)
    action = "start_isolated_resource" if isolated else "start_shared_resource"
    status = "isolated_resource_permitted" if isolated else "shared_resource_permitted"
    return {
        **base,
        "result": "allow",
        "status": status,
        "allow": True,
        "resource_action": action,
        "new_resource_started": False,
        "new_resource_permitted": True,
        "lease_ref": None,
        "host_pressure_admission": admission,
        "reentry_condition": None,
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


def _background_loop_downshift_status(downshift: Mapping[str, Any]) -> dict[str, Any]:
    if not downshift:
        return {
            "present": False,
            "active": False,
            "expired": False,
        }
    applied = downshift.get("result") == "applied" and downshift.get("applied") is True
    issued_at = _parse_iso_datetime(downshift.get("issued_at"))
    duration_s = _as_float(downshift.get("duration_s"), 0.0)
    age_s: float | None = None
    expires_at: str | None = None
    expired = False
    if issued_at is not None:
        now = datetime.now(timezone.utc)
        age_s = round(max((now - issued_at).total_seconds(), 0.0), 3)
        if duration_s > 0:
            expires_at_dt = datetime.fromtimestamp(issued_at.timestamp() + duration_s, timezone.utc)
            expires_at = expires_at_dt.isoformat(timespec="seconds")
            expired = age_s > duration_s
    active = bool(applied and not expired)
    return {
        "present": True,
        "loop_kind": downshift.get("loop_kind"),
        "result": downshift.get("result"),
        "applied": downshift.get("applied"),
        "active": active,
        "expired": expired,
        "age_s": age_s,
        "duration_s": duration_s,
        "expires_at": expires_at,
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


def _session_yield_result_payload(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _as_mapping(value)
    nested = _as_mapping(payload.get("owner_yield_result"))
    return nested or payload


def _session_yield_short_text(value: Any, *, max_chars: int = 160) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _bounded_text_items(values: Sequence[Any] | str | None, *, limit: int = 12) -> list[str]:
    if values is None:
        return []
    source: Sequence[Any]
    if isinstance(values, str):
        source = [values]
    else:
        source = values
    items: list[str] = []
    seen: set[str] = set()
    for value in source:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if len(items) >= limit:
            break
    return items


def _inline_items(items: Sequence[str], *, empty: str = "the requested shared surfaces") -> str:
    if not items:
        return empty
    return ", ".join(f"`{item}`" for item in items)


def _session_yield_request_card(row: Mapping[str, Any]) -> dict[str, Any]:
    request = _session_yield_request_payload(row)
    coordination = _as_mapping(request.get("coordination_request"))
    held_paths = _bounded_text_items(coordination.get("held_paths"), limit=3)
    avoid_paths = _bounded_text_items(coordination.get("avoid_paths"), limit=3)
    avoid_sessions = _bounded_text_items(coordination.get("avoid_session_ids"), limit=3)
    body_omitted = any(
        bool(coordination.get(field))
        for field in ("message", "acknowledgement_template", "requested_action_note")
    )
    return {
        "schema": "session_yield_request_card_v1",
        "request_id": request.get("request_id") or coordination.get("request_id"),
        "issued_at": request.get("issued_at") or coordination.get("issued_at"),
        "target_id": coordination.get("target_session_id") or request.get("target_id"),
        "target_class": request.get("target_class") or coordination.get("target_class"),
        "requested_action": request.get("requested_action") or coordination.get("requested_action"),
        "result": request.get("result"),
        "accepted": bool(request.get("accepted")),
        "owner_status": request.get("owner_status"),
        "pressure_mode": request.get("pressure_mode"),
        "requester_label": coordination.get("requester_label"),
        "requester_session_id": coordination.get("requester_session_id"),
        "held_path_count": len(_as_list(coordination.get("held_paths"))),
        "held_paths_preview": held_paths,
        "avoid_paths_preview": avoid_paths,
        "avoid_session_ids_preview": avoid_sessions,
        "blocked_on_preview": _session_yield_short_text(coordination.get("blocked_on")),
        "validation_status_preview": _session_yield_short_text(coordination.get("validation_status")),
        "inbox_command": coordination.get("inbox_command"),
        "result_command": coordination.get("result_command"),
        "coordination_body_omitted": body_omitted,
    }


def _session_yield_result_card(row: Mapping[str, Any]) -> dict[str, Any]:
    result = _session_yield_result_payload(row)
    return {
        "schema": "owner_yield_result_card_v1",
        "request_id": result.get("request_id"),
        "target_id": result.get("target_id"),
        "target_class": result.get("target_class"),
        "requested_action": result.get("requested_action"),
        "owner_status": result.get("owner_status"),
        "pressure_mode": result.get("pressure_mode"),
        "delivery": result.get("delivery"),
        "result": result.get("result"),
        "accepted": bool(result.get("accepted")),
        "applied": bool(result.get("applied")),
        "applied_action": result.get("applied_action"),
        "status": result.get("status"),
        "result_note_preview": _session_yield_short_text(result.get("result_note")),
        "result_note_omitted": bool(result.get("result_note")),
    }


def _background_downshift_card(downshift: Mapping[str, Any], downshift_status: Mapping[str, Any]) -> dict[str, Any] | None:
    if not downshift:
        return None
    return {
        "schema": "background_loop_downshift_card_v1",
        "loop_kind": downshift.get("loop_kind") or downshift_status.get("loop_kind"),
        "owner_surface": downshift.get("owner_surface"),
        "result": downshift.get("result"),
        "applied": bool(downshift.get("applied")),
        "active": bool(downshift_status.get("active")),
        "expired": bool(downshift_status.get("expired")),
        "age_s": downshift_status.get("age_s"),
        "expires_at": downshift_status.get("expires_at"),
        "effective_interval_s": downshift.get("effective_interval_s"),
    }


def _resident_relief_runtime_sessions(
    runtime_status: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    payload = _as_mapping(runtime_status)
    sessions = _as_mapping(payload.get("sessions"))
    return sessions or payload


def _latest_session_activity(
    session: Mapping[str, Any],
) -> tuple[datetime | None, str | None]:
    candidates: list[tuple[datetime, str]] = []
    field_sources = {
        "last_activity_at": "last_activity",
        "last_append_at": "ledger_append",
        "last_query_at": "ledger_query",
    }
    for field, source in field_sources.items():
        parsed = _parse_iso_datetime(session.get(field))
        if parsed is not None:
            candidates.append((parsed, source))
    heartbeat = _as_mapping(session.get("pass_heartbeat"))
    heartbeat_fields = {
        "updated_at": "pass_heartbeat",
        "current_pass_updated_at": "pass_heartbeat_current_pass",
        "last_pass_completed_at": "pass_heartbeat_completed_pass",
    }
    for field, source in heartbeat_fields.items():
        parsed = _parse_iso_datetime(heartbeat.get(field))
        if parsed is not None:
            candidates.append((parsed, source))
    if not candidates:
        return None, None
    latest = max(candidates, key=lambda item: item[0])
    return latest


def _resident_relief_target_claim_count(session: Mapping[str, Any]) -> int:
    claims = _as_list(session.get("claims"))
    return _as_int(session.get("active_claim_count"), len(claims))


def _resident_relief_settlement_card(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "resident_relief_settlement_card_v1",
        "request_id": row.get("request_id"),
        "target_id": row.get("target_id"),
        "target_class": row.get("target_class"),
        "requested_action": row.get("requested_action"),
        "verdict": row.get("verdict"),
        "evidence_type": row.get("evidence_type"),
        "issued_at": row.get("issued_at"),
        "age_s": row.get("age_s"),
        "stale_pending": bool(row.get("stale_pending")),
        "result": row.get("result"),
        "applied_action": row.get("applied_action"),
        "target_last_activity_at": row.get("target_last_activity_at"),
        "target_ended_at": row.get("target_ended_at"),
        "reentry_condition": row.get("reentry_condition"),
    }


def _resident_relief_settlement_status(counts: Mapping[str, Any]) -> str:
    if _as_int(counts.get("stale_pending_count")) > 0:
        return "stale_pending_recheck_required"
    if _as_int(counts.get("pending_count")) > 0:
        return "request_pending"
    if _as_int(counts.get("superseded_by_fresh_activity_count")) > 0:
        return "owner_activity_observed"
    if _as_int(counts.get("settled_effective_count")) > 0:
        return "relief_effective"
    if (
        _as_int(counts.get("owner_refused_count")) > 0
        or _as_int(counts.get("owner_unreachable_count")) > 0
        or _as_int(counts.get("owner_unresolved_count")) > 0
    ):
        return "owner_response_no_relief"
    if _as_int(counts.get("request_count")) > 0:
        return "settled_no_effective_relief"
    return "not_requested"


def build_resident_relief_settlement_window(
    *,
    request_events: Sequence[Mapping[str, Any]] = (),
    result_events: Sequence[Mapping[str, Any]] = (),
    runtime_status: Mapping[str, Any] | None = None,
    resident_thread_rows: Sequence[Mapping[str, Any]] = (),
    pending_ttl_s: int | float | None = RESIDENT_RELIEF_PENDING_TTL_S,
    now: datetime | None = None,
    limit: int = 20,
    output_profile: str = "compact",
) -> dict[str, Any]:
    """Classify resident relief requests after owner activity and recheck evidence.

    Settlement is observation-only. It correlates request/result receipts with
    live runtime activity and never signals or terminates a session.
    """
    profile = str(output_profile or "compact").strip().lower()
    if profile not in {"compact", "full"}:
        raise ValueError("output_profile must be 'compact' or 'full'")
    bounded_limit = max(1, int(limit or 1))
    ttl_s = max(1.0, _as_float(pending_ttl_s, RESIDENT_RELIEF_PENDING_TTL_S))
    now_dt = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    requests = [_session_yield_request_payload(row) for row in request_events or []]
    results = [_session_yield_result_payload(row) for row in result_events or []]
    runtime_sessions = _resident_relief_runtime_sessions(runtime_status)

    latest_result_by_request: dict[str, Mapping[str, Any]] = {}
    latest_result_by_target: dict[str, Mapping[str, Any]] = {}
    for result in results:
        request_id = str(result.get("request_id") or "").strip()
        target_id = str(result.get("target_id") or "").strip()
        if request_id:
            latest_result_by_request[request_id] = result
        if target_id:
            latest_result_by_target[target_id] = result

    settlement_rows: list[dict[str, Any]] = []
    for request in requests:
        request_id = str(request.get("request_id") or "").strip()
        target_id = str(request.get("target_id") or "").strip()
        result = latest_result_by_request.get(request_id) or latest_result_by_target.get(target_id)
        if not result and str(request.get("result") or "") != "requested":
            result = request
        issued_at = _parse_iso_datetime(request.get("issued_at"))
        age_s = None
        if issued_at is not None:
            age_s = round(max((now_dt - issued_at).total_seconds(), 0.0), 3)
        session = _as_mapping(runtime_sessions.get(target_id))
        ended_at = _parse_iso_datetime(session.get("ended_at"))
        latest_activity_at, latest_activity_source = _latest_session_activity(session)
        target_claim_count = _resident_relief_target_claim_count(session)
        verdict = "request_pending"
        evidence_type = "pending_request"
        stale_pending = False
        reentry_condition: str | None = None
        result_value = str(_as_mapping(result).get("result") or "").strip().lower()
        applied = bool(_as_mapping(result).get("applied"))
        applied_action = str(_as_mapping(result).get("applied_action") or "none")

        if result:
            if (
                result_value == "accepted"
                and applied
                and applied_action in RESIDENT_OWNER_YIELD_APPLIED_ACTIONS
            ):
                verdict = "relief_effective"
                evidence_type = "owner_result_applied"
            elif result_value == "accepted":
                verdict = "accepted_without_applied_relief"
                evidence_type = "owner_result_not_applied"
                reentry_condition = "owner accepted request but no resident relief action was applied"
            elif result_value == "unreachable":
                verdict = "owner_unreachable"
                evidence_type = "owner_result_unreachable"
                reentry_condition = "retry after owner surface becomes reachable"
            elif result_value == "owner_unresolved":
                verdict = "owner_unresolved"
                evidence_type = "owner_unresolved"
                reentry_condition = "resolve owner before treating resident relief as available"
            else:
                verdict = "owner_refused"
                evidence_type = "owner_result_no_relief"
                reentry_condition = "choose a different relief actuator or wait for pressure to clear"
        elif ended_at is not None and (issued_at is None or ended_at >= issued_at):
            verdict = "relief_effective"
            evidence_type = "session_finalized"
        elif (
            latest_activity_at is not None
            and issued_at is not None
            and latest_activity_at > issued_at
        ):
            verdict = "superseded_by_fresh_activity"
            evidence_type = latest_activity_source or "fresh_owner_activity"
            reentry_condition = "recheck host pressure after fresh owner activity"
        elif age_s is not None and age_s >= ttl_s:
            stale_pending = True
            if target_claim_count > 0:
                verdict = "stale_claim_needs_demote"
                evidence_type = "stale_pending_active_claim"
                reentry_condition = "demote stale active claim or request owner refresh"
            else:
                verdict = "still_degraded"
                evidence_type = "stale_pending_no_owner_result"
                reentry_condition = "run resident pressure recheck or escalate to another relief actuator"

        settlement_rows.append(
            {
                "schema": "resident_relief_settlement_row_v1",
                "request_id": request_id or None,
                "target_id": target_id or None,
                "target_class": request.get("target_class"),
                "owner_status": request.get("owner_status"),
                "requested_action": request.get("requested_action"),
                "issued_at": request.get("issued_at"),
                "age_s": age_s,
                "pending_ttl_s": ttl_s,
                "verdict": verdict,
                "evidence_type": evidence_type,
                "stale_pending": stale_pending,
                "result": result_value or None,
                "applied": applied,
                "applied_action": applied_action if applied_action != "none" else None,
                "target_last_activity_at": latest_activity_at.isoformat()
                if latest_activity_at is not None
                else None,
                "target_last_activity_source": latest_activity_source,
                "target_ended_at": ended_at.isoformat() if ended_at is not None else None,
                "target_active_claim_count": target_claim_count,
                "reentry_condition": reentry_condition,
            }
        )

    terminate_grace_rows = [
        row
        for row in resident_thread_rows or []
        if isinstance(row, Mapping)
        and str(row.get("recommended_action") or row.get("action") or "") == "terminate_grace"
    ]
    counts = {
        "request_count": len(requests),
        "result_count": len(results),
        "settlement_row_count": len(settlement_rows),
        "settled_effective_count": sum(
            1 for row in settlement_rows if row["verdict"] == "relief_effective"
        ),
        "pending_count": sum(1 for row in settlement_rows if row["verdict"] == "request_pending"),
        "request_pending_count": sum(
            1 for row in settlement_rows if row["verdict"] == "request_pending"
        ),
        "stale_pending_count": sum(1 for row in settlement_rows if row["stale_pending"]),
        "stale_claim_needs_demote_count": sum(
            1 for row in settlement_rows if row["verdict"] == "stale_claim_needs_demote"
        ),
        "still_degraded_count": sum(
            1 for row in settlement_rows if row["verdict"] == "still_degraded"
        ),
        "owner_refused_count": sum(
            1 for row in settlement_rows if row["verdict"] == "owner_refused"
        ),
        "owner_unreachable_count": sum(
            1 for row in settlement_rows if row["verdict"] == "owner_unreachable"
        ),
        "owner_unresolved_count": sum(
            1 for row in settlement_rows if row["verdict"] == "owner_unresolved"
        ),
        "accepted_without_applied_relief_count": sum(
            1
            for row in settlement_rows
            if row["verdict"] == "accepted_without_applied_relief"
        ),
        "superseded_by_fresh_activity_count": sum(
            1
            for row in settlement_rows
            if row["verdict"] == "superseded_by_fresh_activity"
        ),
        "terminate_grace_escrow_candidate_count": len(terminate_grace_rows),
    }
    counts["outstanding_pending_count"] = (
        counts["request_pending_count"] + counts["stale_pending_count"]
    )
    latest_cards = [
        _resident_relief_settlement_card(row)
        for row in list(reversed(settlement_rows))[:bounded_limit]
    ]
    digest_body = {
        "counts": counts,
        "rows": [
            {
                "request_id": row.get("request_id"),
                "target_id": row.get("target_id"),
                "verdict": row.get("verdict"),
                "evidence_type": row.get("evidence_type"),
                "stale_pending": row.get("stale_pending"),
            }
            for row in settlement_rows
        ],
    }
    digest = hashlib.sha256(
        json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    payload = {
        "schema": RESIDENT_RELIEF_SETTLEMENT_WINDOW_SCHEMA,
        "output_profile": "full",
        "generated_at": now_dt.isoformat(timespec="seconds"),
        "receipt_id": f"rrs_{digest}",
        "receipt_hash": digest,
        "status": _resident_relief_settlement_status(counts),
        "pending_ttl_s": ttl_s,
        "settlement_rows": settlement_rows[:bounded_limit],
        "latest_settlement_cards": latest_cards,
        "terminate_grace_escrow_candidates": [
            {
                "session_id": row.get("session_id"),
                "recommended_action": row.get("recommended_action") or row.get("action"),
                "state": row.get("state"),
                "quiet_for_s": row.get("quiet_for_s"),
            }
            for row in terminate_grace_rows[:bounded_limit]
        ],
        "counts": counts,
        "policy": {
            "pending_request_is_not_effective_relief": True,
            "fresh_owner_activity_settles_request_but_requires_recheck": True,
            "stale_pending_routes_to_recheck_or_demote_not_kill": True,
            "terminate_grace_rows_are_escrow_candidates_not_signals": True,
            "pending_ttl_s": ttl_s,
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
            "terminate_grace_is_not_actuated": True,
        },
    }
    if profile == "full":
        return payload
    return {
        **payload,
        "output_profile": "compact",
        "settlement_rows": [],
        "rows_omitted": max(0, len(settlement_rows) - len(latest_cards)),
        "omission_receipt": {
            "omitted": ["full resident relief settlement rows"],
            "reason": "compact settlement keeps resident relief observation cheap",
            "drilldown": "./repo-python tools/meta/factory/work_ledger.py session-yield-control --full --limit 20",
        },
    }


def _session_yield_action_sentence(action: str, override: str | None = None) -> str:
    explicit = str(override or "").strip()
    if explicit:
        return explicit
    if action == "release_after_landing":
        return "Please prioritize finishing validation, then land or release the shared paths you own."
    if action == "cede_path":
        return "Please cede or release the requested paths when safe."
    if action == "claim_projection_refresh":
        return "Please claim or hand off the projection refresh so the blocked lane can continue."
    if action == "accept_settlement_group":
        return "Please accept or respond to the settlement group so the sibling lane can close cleanly."
    if action == "release_tool_lease":
        return "Please release the tool lease if it is no longer needed."
    if action == "lower_poll_rate":
        return "Please lower the polling rate if the background loop can safely downshift."
    if action == "hibernate":
        return "Please hibernate the session if it is no longer actively advancing the shared lane."
    return "Please yield, land, or respond with the smallest action that clears the sibling blocker."


def _session_yield_applied_action(action: str) -> str:
    if action == "release_after_landing":
        return "landed_or_released_paths"
    if action == "cede_path":
        return "ceded_path"
    if action == "claim_projection_refresh":
        return "claimed_projection_refresh"
    if action == "accept_settlement_group":
        return "accepted_settlement_group"
    if action == "release_tool_lease":
        return "released_tool_lease"
    if action == "lower_poll_rate":
        return "lowered_poll_rate"
    if action == "hibernate":
        return "hibernated"
    if action == "yield":
        return "yielded"
    return "none"


def build_session_yield_coordination_request(
    *,
    yield_request: Mapping[str, Any],
    requester_label: str | None = None,
    requester_session_id: str | None = None,
    blocked_on: str | None = None,
    validation_status: str | None = None,
    held_paths: Sequence[Any] | str | None = (),
    avoid_paths: Sequence[Any] | str | None = (),
    avoid_session_ids: Sequence[Any] | str | None = (),
    requested_action_note: str | None = None,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Build a paste-ready sibling-thread coordination brief from a yield request."""
    request = _session_yield_request_payload(yield_request)
    request_id = str(request.get("request_id") or "unknown").strip() or "unknown"
    target_id = str(request.get("target_id") or "unknown").strip() or "unknown"
    requested_action = str(request.get("requested_action") or "yield").strip().lower()
    target_class = str(request.get("target_class") or "unknown").strip() or "unknown"
    requester = (
        str(requester_label or "").strip()
        or str(requester_session_id or "").strip()
        or "a sibling Type A thread"
    )
    held = _bounded_text_items(held_paths)
    avoid = _bounded_text_items(avoid_paths)
    avoid_sessions = _bounded_text_items(avoid_session_ids)
    blocked_text = str(blocked_on or "").strip()
    validation_text = str(validation_status or "").strip()

    lines = [f"Coordination request from {requester}."]
    if held:
        lines.append(
            f"Your Work Ledger session `{target_id}` currently holds or has dirty "
            f"these shared surfaces: {_inline_items(held)}."
        )
    else:
        lines.append(
            f"Your Work Ledger session `{target_id}` is the current owner visible "
            "on the Work Ledger yield bus."
        )
    if validation_text and blocked_text:
        lines.append(
            f"{validation_text}, but sibling scoped landing is blocked by "
            f"`{blocked_text}` until this yield request is handled."
        )
    elif blocked_text:
        lines.append(
            f"Sibling scoped landing is blocked by `{blocked_text}` until this "
            "yield request is handled."
        )
    elif validation_text:
        lines.append(f"Current sibling validation/status: {validation_text}.")
    lines.append(_session_yield_action_sentence(requested_action, requested_action_note))
    if avoid or avoid_sessions:
        avoid_parts: list[str] = []
        if avoid:
            avoid_parts.append(f"paths {_inline_items(avoid)}")
        if avoid_sessions:
            avoid_parts.append(f"sessions {_inline_items(avoid_sessions)}")
        lines.append(f"Do not touch the sibling-owned {'; '.join(avoid_parts)}.")
    lines.append(f"A Work Ledger yield request was recorded as `{request_id}`.")

    if requested_action == "release_after_landing":
        ack_action = "finish focused validation, then land or release the shared paths I claimed"
    elif requested_action == "cede_path":
        ack_action = "cede or release the requested paths when safe"
    else:
        ack_action = f"handle `{requested_action}` and record the result"
    ack = (
        "Received. I am prioritizing the requested coordination now: "
        f"{ack_action}."
    )
    if avoid or avoid_sessions:
        ack += " I will leave the named sibling-owned paths/sessions alone."

    return {
        "schema": SESSION_YIELD_COORDINATION_REQUEST_SCHEMA,
        "request_id": request_id,
        "target_session_id": target_id,
        "target_class": target_class,
        "requested_action": requested_action,
        "requester_label": requester,
        "requester_session_id": str(requester_session_id or "").strip() or None,
        "blocked_on": blocked_text or None,
        "validation_status": validation_text or None,
        "held_paths": held,
        "avoid_paths": avoid,
        "avoid_session_ids": avoid_sessions,
        "message": " ".join(lines),
        "acknowledgement_template": ack,
        "result_command": (
            "./repo-python tools/meta/factory/work_ledger.py session-yield-result "
            f"--request-id {request_id} --result accepted "
            f"--applied-action {_session_yield_applied_action(requested_action)}"
        ),
        "inbox_command": (
            "./repo-python tools/meta/factory/work_ledger.py session-yield-inbox "
            f"--session-id {target_id} --limit 12"
        ),
        "control_command": "./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit 20",
        "issued_at": issued_at or _now_iso(),
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


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
    output_profile: str = "compact",
) -> dict[str, Any]:
    """Summarize pending, accepted, and applied resident-yield control state."""
    profile = str(output_profile or "compact").strip().lower()
    if profile not in {"compact", "full"}:
        raise ValueError("output_profile must be 'compact' or 'full'")
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
    resident_applied_results = [
        row
        for row in applied_results
        if row.get("applied_action") in RESIDENT_OWNER_YIELD_APPLIED_ACTIONS
    ]
    unsupported_results = [row for row in results if row.get("result") in {"unsupported", "unreachable", "owner_unresolved"}]
    owner_unresolved_results = [row for row in results if row.get("result") == "owner_unresolved"]
    bounded_limit = max(1, int(limit or 1))
    downshift = _as_mapping(background_loop_downshift)
    downshift_status = _background_loop_downshift_status(downshift)
    downshift_active = bool(downshift_status.get("active"))
    station_downshift_active = bool(downshift_active and downshift.get("loop_kind") == "station_polling")
    applied_result_count = len(applied_results)
    accepted_actuator_count = len(resident_applied_results) + (1 if downshift_active else 0)
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
    payload = {
        "schema": SESSION_YIELD_CONTROL_SURFACE_SCHEMA,
        "output_profile": "full",
        "latest_requests": list(reversed(requests))[:bounded_limit],
        "latest_results": list(reversed(results))[:bounded_limit],
        "pending_requests": list(reversed(pending))[:bounded_limit],
        "resolved_requests": list(reversed(resolved))[:bounded_limit],
        "accepted_results": list(reversed(accepted_results))[:bounded_limit],
        "applied_results": list(reversed(applied_results))[:bounded_limit],
        "unsupported_results": list(reversed(unsupported_results))[:bounded_limit],
        "owner_unresolved_results": list(reversed(owner_unresolved_results))[:bounded_limit],
        "background_loop_downshift": dict(downshift) if downshift else None,
        "background_downshift_status": downshift_status,
        "background_downshift_active": downshift_active,
        "background_downshift_expired": bool(downshift_status.get("expired")),
        "background_downshift_loop_kind": downshift_status.get("loop_kind"),
        "background_downshift_age_s": downshift_status.get("age_s"),
        "background_downshift_expires_at": downshift_status.get("expires_at"),
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
            "resident_applied_result_count": len(resident_applied_results),
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
    if profile == "full":
        payload["compact_command"] = f"./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit {bounded_limit}"
        return payload

    compact_card_limit = min(5, bounded_limit)
    compact_payload = {
        "schema": SESSION_YIELD_CONTROL_SURFACE_SCHEMA,
        "output_profile": "compact",
        "card_limit": compact_card_limit,
        "latest_request_cards": [
            _session_yield_request_card(row) for row in list(reversed(requests))[:compact_card_limit]
        ],
        "latest_result_cards": [
            _session_yield_result_card(row) for row in list(reversed(results))[:compact_card_limit]
        ],
        "unsupported_result_cards": [
            _session_yield_result_card(row) for row in list(reversed(unsupported_results))[:compact_card_limit]
        ],
        "background_loop_downshift": _background_downshift_card(downshift, downshift_status),
        "background_downshift_status": downshift_status,
        "background_downshift_active": downshift_active,
        "background_downshift_expired": bool(downshift_status.get("expired")),
        "background_downshift_loop_kind": downshift_status.get("loop_kind"),
        "background_downshift_age_s": downshift_status.get("age_s"),
        "background_downshift_expires_at": downshift_status.get("expires_at"),
        "station_downshift_active": station_downshift_active,
        "accepted_actuator_count": accepted_actuator_count,
        "recovery_verdict": recovery_verdict,
        "counts": payload["counts"],
        "policy": payload["policy"],
        "safety": payload["safety"],
        "full_payload_command": f"./repo-python tools/meta/factory/work_ledger.py session-yield-control --full --limit {bounded_limit}",
        "omission_receipt": {
            "omitted": [
                "full yield request rows",
                "coordination_request.message bodies",
                "coordination acknowledgement templates",
                "full owner result rows",
                "full background downshift receipt",
                "per-category compact arrays beyond latest request/result cards",
            ],
            "reason": "session-yield-control defaults to compact coordination cards so routine polling cannot dump sibling-thread message bodies.",
            "drilldown": f"./repo-python tools/meta/factory/work_ledger.py session-yield-control --full --limit {bounded_limit}",
        },
    }
    return compact_payload


def build_session_yield_inbox_surface(
    *,
    session_id: str,
    request_events: Sequence[Mapping[str, Any]] = (),
    result_events: Sequence[Mapping[str, Any]] = (),
    limit: int = 12,
) -> dict[str, Any]:
    """Return a target-owner inbox over the disk-backed session yield bus."""
    target_session_id = str(session_id or "").strip() or "unknown"
    bounded_limit = max(1, int(limit or 1))
    requests = [_session_yield_request_payload(row) for row in request_events or []]
    results = [_session_yield_result_payload(row) for row in result_events or []]

    latest_result_by_request: dict[str, Mapping[str, Any]] = {}
    latest_result_by_target: dict[str, Mapping[str, Any]] = {}
    for result in results:
        request_id = str(result.get("request_id") or "").strip()
        target_id = str(result.get("target_id") or "").strip()
        if request_id:
            latest_result_by_request[request_id] = result
        if target_id:
            latest_result_by_target[target_id] = result

    inbox_rows: list[dict[str, Any]] = []
    pending_rows: list[dict[str, Any]] = []
    resolved_rows: list[dict[str, Any]] = []
    for request in requests:
        coordination = _as_mapping(request.get("coordination_request"))
        target_id = (
            str(coordination.get("target_session_id") or "").strip()
            or str(request.get("target_id") or "").strip()
        )
        if target_id != target_session_id:
            continue
        request_id = str(request.get("request_id") or coordination.get("request_id") or "").strip()
        if request_id:
            result = latest_result_by_request.get(request_id)
        else:
            result = latest_result_by_target.get(target_id)
        requested_action = (
            str(request.get("requested_action") or coordination.get("requested_action") or "yield")
            .strip()
            .lower()
        )
        result_command = str(coordination.get("result_command") or "").strip()
        if not result_command and request_id:
            result_command = (
                "./repo-python tools/meta/factory/work_ledger.py session-yield-result "
                f"--request-id {request_id} --result accepted "
                f"--applied-action {_session_yield_applied_action(requested_action)}"
            )
        row = {
            "schema": "session_yield_inbox_row_v1",
            "request_id": request_id or None,
            "target_session_id": target_id,
            "target_class": request.get("target_class") or coordination.get("target_class"),
            "requested_action": requested_action,
            "issued_at": request.get("issued_at") or coordination.get("issued_at"),
            "requester_label": coordination.get("requester_label"),
            "requester_session_id": coordination.get("requester_session_id"),
            "owner_status": request.get("owner_status"),
            "pressure_mode": request.get("pressure_mode"),
            "held_paths": _bounded_text_items(coordination.get("held_paths")),
            "avoid_paths": _bounded_text_items(coordination.get("avoid_paths")),
            "avoid_session_ids": _bounded_text_items(coordination.get("avoid_session_ids")),
            "blocked_on": coordination.get("blocked_on"),
            "validation_status": coordination.get("validation_status"),
            "message": coordination.get("message") or request.get("result_note"),
            "acknowledgement_template": coordination.get("acknowledgement_template"),
            "result_command": result_command or None,
            "inbox_command": (
                coordination.get("inbox_command")
                or "./repo-python tools/meta/factory/work_ledger.py "
                f"session-yield-inbox --session-id {target_session_id} --limit {bounded_limit}"
            ),
            "control_command": (
                coordination.get("control_command")
                or "./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit 20"
            ),
            "pending": not bool(result) and request.get("result") == "requested",
            "resolved": bool(result),
            "latest_result_status": result.get("status") if result else None,
            "latest_result": dict(result) if result else None,
            "safety": request.get("safety") or coordination.get("safety"),
        }
        inbox_rows.append(row)
        if row["pending"]:
            pending_rows.append(row)
        elif row["resolved"]:
            resolved_rows.append(row)

    latest_rows = list(reversed(inbox_rows))
    latest_pending = list(reversed(pending_rows))
    latest_resolved = list(reversed(resolved_rows))
    first_pending_command = latest_pending[0]["result_command"] if latest_pending else None
    return {
        "schema": SESSION_YIELD_INBOX_SURFACE_SCHEMA,
        "session_id": target_session_id,
        "latest_requests": latest_rows[:bounded_limit],
        "pending_requests": latest_pending[:bounded_limit],
        "resolved_requests": latest_resolved[:bounded_limit],
        "counts": {
            "inbox_request_count": len(inbox_rows),
            "pending_request_count": len(pending_rows),
            "resolved_request_count": len(resolved_rows),
            "result_event_count": len(results),
        },
        "recommended_commands": {
            "poll_inbox": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-yield-inbox --session-id {target_session_id} --limit {bounded_limit}"
            ),
            "global_control": "./repo-python tools/meta/factory/work_ledger.py session-yield-control --limit 20",
            "record_first_pending_result": first_pending_command,
        },
        "transport_boundary": {
            "authority": (
                "state/performance/session_yield_requests.jsonl plus "
                "state/performance/session_yield_results.jsonl"
            ),
            "codex_thread_interrupts": "optional_convenience_not_authority",
            "claude_code_delivery": "poll_disk_backed_inbox_or_shell_command",
            "no_process_signal_sent": True,
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
