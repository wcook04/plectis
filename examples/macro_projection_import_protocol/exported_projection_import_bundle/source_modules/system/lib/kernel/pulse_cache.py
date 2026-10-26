"""Shared cache IDs and producers for kernel pulse hot-read sidecars."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping


PULSE_PROVIDER_PLANE_LIVENESS_NODE_ID = "kernel.pulse.provider_plane_liveness.quick"
PULSE_PROVIDER_PLANE_LIVENESS_KEY = {"version": 1}
PULSE_PROVIDER_PLANE_LIVENESS_INPUT_PATHS = (
    "system/lib/provider_plane_liveness.py",
    "state/compute_workers/transform_jobs",
    "state/compute_workers/receipts",
    "state/compute_workers/row_patches",
    "state/compute_workers/row_patch_reviews",
    "state/task_ledger/views",
)
PULSE_PROVIDER_PLANE_LIVENESS_FRESHNESS_POLICY = (
    "stale_ok_hot_pulse_read_provider_plane_exact_route_refreshes"
)

PULSE_CLOSEOUT_AUDIT_NODE_ID = "kernel.pulse.closeout_audit.quick"
PULSE_CLOSEOUT_AUDIT_KEY = {"version": 1, "limit": 5, "candidate_scan_limit": 120}
PULSE_CLOSEOUT_AUDIT_INPUT_PATHS = (
    "system/lib/kernel/commands/navigate.py",
    "system/lib/observe_sessions.py",
    "system/lib/phase_harbor.py",
    "tools/meta/control/orchestration_events.jsonl",
    "obsidian",
)
PULSE_CLOSEOUT_AUDIT_FRESHNESS_POLICY = (
    "stale_ok_hot_pulse_read_closeout_audit_exact_route_refreshes"
)

PULSE_CLOSEOUT_GIT_STATE_NODE_ID = "kernel.pulse.closeout_git_state.quick"
PULSE_CLOSEOUT_GIT_STATE_KEY = {"version": 1}
PULSE_CLOSEOUT_GIT_STATE_INPUT_PATHS = (
    "system/lib/git_state_snapshot.py",
)
PULSE_CLOSEOUT_GIT_STATE_FRESHNESS_POLICY = (
    "stale_ok_hot_pulse_read_git_state_exact_route_refreshes"
)
PULSE_CLOSEOUT_GIT_STATE_CACHE_TTL_S = 30.0

PULSE_TASK_LEDGER_PRIORITY_NODE_ID = "kernel.pulse.task_ledger_priority.quick"
PULSE_TASK_LEDGER_PRIORITY_KEY = {"version": 1}
PULSE_TASK_LEDGER_PRIORITY_INPUT_PATHS = (
    "system/lib/task_ledger_priority.py",
    "state/task_ledger/views/execution_menu_schedulable.json",
    "state/task_ledger/views/schedulable_by_rank.json",
    "state/task_ledger/views/ready_by_rank.json",
    "state/task_ledger/views/dependency_blocked.json",
    "state/task_ledger/views/unlocks_by_rank.json",
)
PULSE_TASK_LEDGER_PRIORITY_FRESHNESS_POLICY = (
    "manifest_validated_task_ledger_priority_projection_exact_route_refreshes"
)

PULSE_ANNEX_LANDING_NODE_ID = "kernel.pulse.annex_landing.quick"
PULSE_ANNEX_LANDING_KEY = {"version": 1}
PULSE_ANNEX_LANDING_INPUT_PATHS = (
    "system/lib/kernel/commands/navigate.py",
    "annexes/annex_distillation_index.json",
)
PULSE_ANNEX_LANDING_FRESHNESS_POLICY = (
    "manifest_validated_annex_landing_summary_exact_route_refreshes"
)

PULSE_DOCTRINE_SUMMARY_NODE_ID = "kernel.pulse.doctrine_summary.quick"
PULSE_DOCTRINE_SUMMARY_KEY = {"version": 1}
PULSE_DOCTRINE_SUMMARY_INPUT_PATHS = (
    "system/lib/kernel/commands/navigate.py",
    "codex/derived/map.json",
)
PULSE_DOCTRINE_SUMMARY_FRESHNESS_POLICY = (
    "manifest_validated_doctrine_summary_projection_exact_route_refreshes"
)


ProviderPlaneBuilder = Callable[..., dict[str, Any]]
CloseoutGitStateBuilder = Callable[..., dict[str, Any]]


def _closeout_git_state_failure_payload(reason: str, exc: Exception) -> tuple[dict[str, Any], dict[str, Any]]:
    return {
        "schema": "closeout_git_state_summary_v0",
        "status": "unknown",
        "reason": reason,
        "error": str(exc)[:240],
        "drilldowns": {
            "closeout_conditions": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions"
        },
    }, {
        "status": "error",
        "reason": reason,
        "error_type": type(exc).__name__,
        "error": str(exc)[:240],
    }


def refresh_closeout_git_state_cache(
    repo_root: Path | str,
    *,
    ttl_s: float = PULSE_CLOSEOUT_GIT_STATE_CACHE_TTL_S,
    force_refresh: bool = False,
    builder: CloseoutGitStateBuilder | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refresh or reuse the compact closeout git summary consumed by hot entry/pulse."""
    try:
        from system.lib.command_node_cache import cached_command_node

        root = Path(repo_root)
        if builder is None:
            from system.lib.git_state_snapshot import build_closeout_git_state_summary_fast as builder

        def _build() -> dict[str, Any]:
            payload = builder(root, path_limit=5)
            return json.loads(json.dumps(payload, default=str))

        payload, cache_status = cached_command_node(
            root,
            node_id=PULSE_CLOSEOUT_GIT_STATE_NODE_ID,
            key=PULSE_CLOSEOUT_GIT_STATE_KEY,
            input_paths=PULSE_CLOSEOUT_GIT_STATE_INPUT_PATHS,
            ttl_s=ttl_s,
            builder=_build,
            freshness_policy=PULSE_CLOSEOUT_GIT_STATE_FRESHNESS_POLICY,
            dynamic_inputs_manifested=False,
            force_refresh=force_refresh,
        )
        return dict(payload), cache_status
    except Exception as exc:
        return _closeout_git_state_failure_payload("pulse_closeout_git_state_failed", exc)


def closeout_git_state_cache_or_refresh(
    repo_root: Path | str,
    *,
    exact: bool = False,
    ttl_s: float = PULSE_CLOSEOUT_GIT_STATE_CACHE_TTL_S,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a stale-ok cached closeout summary, refreshing when no cache exists."""
    if exact:
        return refresh_closeout_git_state_cache(repo_root, ttl_s=ttl_s, force_refresh=True)
    try:
        from system.lib.command_node_cache import peek_cached_command_node

        root = Path(repo_root)
        payload, cache_status = peek_cached_command_node(
            root,
            node_id=PULSE_CLOSEOUT_GIT_STATE_NODE_ID,
            key=PULSE_CLOSEOUT_GIT_STATE_KEY,
            input_paths=PULSE_CLOSEOUT_GIT_STATE_INPUT_PATHS,
            ttl_s=ttl_s,
            freshness_policy=PULSE_CLOSEOUT_GIT_STATE_FRESHNESS_POLICY,
            dynamic_inputs_manifested=False,
        )
        if isinstance(payload, Mapping):
            return dict(payload), cache_status
        return refresh_closeout_git_state_cache(root, ttl_s=ttl_s, force_refresh=False)
    except Exception as exc:
        return _closeout_git_state_failure_payload("pulse_closeout_git_state_cache_peek_failed", exc)


def refresh_provider_plane_liveness_cache(
    repo_root: Path | str,
    *,
    ttl_s: float,
    force_refresh: bool = True,
    builder: ProviderPlaneBuilder | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refresh the bounded provider-plane payload consumed by quick pulse."""
    from system.lib.command_node_cache import cached_command_node

    root = Path(repo_root)
    if builder is None:
        from system.lib.provider_plane_liveness import build_provider_plane_liveness as builder

    def _build() -> dict[str, Any]:
        payload = builder(root, scan_mode="bounded_scan")
        return json.loads(json.dumps(payload, default=str))

    payload, cache_status = cached_command_node(
        root,
        node_id=PULSE_PROVIDER_PLANE_LIVENESS_NODE_ID,
        key=PULSE_PROVIDER_PLANE_LIVENESS_KEY,
        input_paths=PULSE_PROVIDER_PLANE_LIVENESS_INPUT_PATHS,
        ttl_s=ttl_s,
        builder=_build,
        freshness_policy=PULSE_PROVIDER_PLANE_LIVENESS_FRESHNESS_POLICY,
        dynamic_inputs_manifested=False,
        force_refresh=force_refresh,
    )
    return dict(payload), cache_status


TaskLedgerPriorityBuilder = Callable[[Path], dict[str, Any]]


def refresh_task_ledger_priority_cache(
    repo_root: Path | str,
    *,
    force_refresh: bool = False,
    builder: TaskLedgerPriorityBuilder | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refresh or reuse the compact Task Ledger priority payload for pulse."""
    from system.lib.command_node_cache import cached_command_node

    root = Path(repo_root)
    if builder is None:
        from system.lib.task_ledger_priority import priority_constellation as builder

    def _build() -> dict[str, Any]:
        payload = builder(root)
        return json.loads(json.dumps(payload, default=str))

    payload, cache_status = cached_command_node(
        root,
        node_id=PULSE_TASK_LEDGER_PRIORITY_NODE_ID,
        key=PULSE_TASK_LEDGER_PRIORITY_KEY,
        input_paths=PULSE_TASK_LEDGER_PRIORITY_INPUT_PATHS,
        ttl_s=0.0,
        builder=_build,
        freshness_policy=PULSE_TASK_LEDGER_PRIORITY_FRESHNESS_POLICY,
        dynamic_inputs_manifested=True,
        force_refresh=force_refresh,
    )
    return dict(payload), cache_status


__all__ = [
    "PULSE_CLOSEOUT_AUDIT_FRESHNESS_POLICY",
    "PULSE_CLOSEOUT_AUDIT_INPUT_PATHS",
    "PULSE_CLOSEOUT_AUDIT_KEY",
    "PULSE_CLOSEOUT_AUDIT_NODE_ID",
    "PULSE_ANNEX_LANDING_FRESHNESS_POLICY",
    "PULSE_ANNEX_LANDING_INPUT_PATHS",
    "PULSE_ANNEX_LANDING_KEY",
    "PULSE_ANNEX_LANDING_NODE_ID",
    "PULSE_CLOSEOUT_GIT_STATE_FRESHNESS_POLICY",
    "PULSE_CLOSEOUT_GIT_STATE_INPUT_PATHS",
    "PULSE_CLOSEOUT_GIT_STATE_KEY",
    "PULSE_CLOSEOUT_GIT_STATE_NODE_ID",
    "PULSE_CLOSEOUT_GIT_STATE_CACHE_TTL_S",
    "PULSE_DOCTRINE_SUMMARY_FRESHNESS_POLICY",
    "PULSE_DOCTRINE_SUMMARY_INPUT_PATHS",
    "PULSE_DOCTRINE_SUMMARY_KEY",
    "PULSE_DOCTRINE_SUMMARY_NODE_ID",
    "PULSE_PROVIDER_PLANE_LIVENESS_FRESHNESS_POLICY",
    "PULSE_PROVIDER_PLANE_LIVENESS_INPUT_PATHS",
    "PULSE_PROVIDER_PLANE_LIVENESS_KEY",
    "PULSE_PROVIDER_PLANE_LIVENESS_NODE_ID",
    "PULSE_TASK_LEDGER_PRIORITY_FRESHNESS_POLICY",
    "PULSE_TASK_LEDGER_PRIORITY_INPUT_PATHS",
    "PULSE_TASK_LEDGER_PRIORITY_KEY",
    "PULSE_TASK_LEDGER_PRIORITY_NODE_ID",
    "closeout_git_state_cache_or_refresh",
    "refresh_provider_plane_liveness_cache",
    "refresh_closeout_git_state_cache",
    "refresh_task_ledger_priority_cache",
]
