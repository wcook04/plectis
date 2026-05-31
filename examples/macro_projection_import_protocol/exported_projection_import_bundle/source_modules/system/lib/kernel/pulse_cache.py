"""Shared cache IDs and producers for kernel pulse hot-read sidecars."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


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


ProviderPlaneBuilder = Callable[..., dict[str, Any]]


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


__all__ = [
    "PULSE_CLOSEOUT_AUDIT_FRESHNESS_POLICY",
    "PULSE_CLOSEOUT_AUDIT_INPUT_PATHS",
    "PULSE_CLOSEOUT_AUDIT_KEY",
    "PULSE_CLOSEOUT_AUDIT_NODE_ID",
    "PULSE_PROVIDER_PLANE_LIVENESS_FRESHNESS_POLICY",
    "PULSE_PROVIDER_PLANE_LIVENESS_INPUT_PATHS",
    "PULSE_PROVIDER_PLANE_LIVENESS_KEY",
    "PULSE_PROVIDER_PLANE_LIVENESS_NODE_ID",
    "refresh_provider_plane_liveness_cache",
]
