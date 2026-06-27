"""
WorkItem runtime entrypoint packet.

This composes forward-integration policy, Task Ledger state, Work Ledger cohort
state, phase context, projection affordances, and closeout obligations into one
read-only orientation packet for Type A runtime entry.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib import strict_json, task_ledger_events, uppropagation_intake, work_ledger_runtime
from system.lib.forward_integration_policy import (
    build_forward_integration_policy,
    normalize_repo_path,
    owner_tool_entries_for_path,
    path_scope_overlaps,
)
from system.lib.kernel_navigation import KernelNavigation
from system.lib.work_ledger_commands import WORK_LEDGER_SEED_SPEED_COMMAND

try:  # Reuse the live write-profile registry without making it authority here.
    from tools.meta.factory.work_ledger import WRITE_PROFILE_PATHS
except Exception:  # pragma: no cover - defensive fallback for packaged use
    WRITE_PROFILE_PATHS = {}  # type: ignore[assignment]


SCHEMA_VERSION = "workitem_runtime_entrypoint_v1"
PHASE_INDEX_REL = Path("codex/derived/phase_index.json")
TASK_LEDGER_SOURCE_AUTO = "auto"
TASK_LEDGER_SOURCE_AUTHORITY = "authority"
TASK_LEDGER_SOURCE_MATERIALIZED = "materialized_projection"


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _expand_write_profiles(profile_names: Sequence[str] | None) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    profiles: list[dict[str, Any]] = []
    paths: list[str] = []
    warnings: list[str] = []
    for raw in profile_names or []:
        name = str(raw or "").strip()
        if not name:
            continue
        profile_paths = list(WRITE_PROFILE_PATHS.get(name) or ())
        if not profile_paths:
            warnings.append(f"unknown write profile: {name}")
        profiles.append({"profile": name, "paths": profile_paths, "known": bool(profile_paths)})
        paths.extend(profile_paths)
    return profiles, paths, warnings


def _task_ledger_view_rows(views: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    view_rows: dict[str, dict[str, Any]] = {}
    for name, payload in sorted(views.items()):
        if not isinstance(payload, Mapping):
            continue
        row = {
            "path": str(task_ledger_events.VIEWS_REL / f"{name}.json"),
            "count": payload.get("count"),
            "projection_only": True,
        }
        if name in {
            "blocked",
            "capture_inbox",
            "capture_triage",
            "dependency_anomalies",
            "dependency_blocked",
            "dependency_graph",
            "execution_menu",
            "execution_menu_schedulable",
            "merge_or_retire_candidates",
            "missing_contracts_ranked",
            "ready_by_rank",
            "schedulable_by_rank",
            "unlocks_by_rank",
        }:
            for field in (
                "counts_by_status",
                "category_counts",
                "linkage_counts",
                "stale_capture_count",
                "count_semantics",
                "projection_semantics",
                "total_capture_count",
                "raw_capture_inbox_count",
                "active_raw_capture_count",
                "closed_or_signed_off_count",
                "why_execution_menu_is_small",
                "why_these_next",
                "wip_policy",
            ):
                if field in payload:
                    row[field] = payload.get(field)
            if isinstance(payload.get("items"), list):
                row["items_preview"] = list(payload.get("items") or [])[:8]
        view_rows[str(name)] = row
    return view_rows


def _task_ledger_projection_payload(
    *,
    validation: Mapping[str, Any],
    event_count: int | None,
    ledger: Mapping[str, Any],
    signoffs: Mapping[str, Any],
    views: Mapping[str, Any],
) -> dict[str, Any]:
    view_rows = _task_ledger_view_rows(views)
    capture_statuses = view_rows.get("capture_triage", {}).get("counts_by_status") or {}
    capture_categories = view_rows.get("capture_triage", {}).get("category_counts") or {}
    shaped_ready_count = 0
    if isinstance(capture_statuses, Mapping):
        shaped_ready_count = int(capture_statuses.get("shaped_ready") or 0) + int(
            capture_statuses.get("shaped_needs_completion_contract") or 0
        )
    raw_capture_inbox_count = view_rows.get("capture_inbox", {}).get("raw_capture_inbox_count")
    if raw_capture_inbox_count is None and isinstance(capture_categories, Mapping):
        raw_capture_inbox_count = capture_categories.get("raw_capture_inbox")
    closed_capture_count = view_rows.get("capture_inbox", {}).get("closed_or_signed_off_count")
    if closed_capture_count is None and isinstance(capture_statuses, Mapping):
        closed_capture_count = capture_statuses.get("closed_or_signed_off")
    return {
        "ok": True,
        "authority": str(task_ledger_events.EVENTS_REL),
        "projection": str(task_ledger_events.LEDGER_REL),
        "sign_off_projection": str(task_ledger_events.SIGNOFFS_REL),
        "validation": dict(validation),
        "counts": {
            "event_count": event_count if event_count is not None else ledger.get("event_count"),
            "work_item_count": len(ledger.get("work_items") or []),
            "task_count": len(ledger.get("tasks") or []),
            "capture_count": view_rows.get("capture_inbox", {}).get("count"),
            "total_capture_count": view_rows.get("capture_inbox", {}).get("count"),
            "raw_capture_inbox_count": raw_capture_inbox_count,
            "active_capture_inbox_count": raw_capture_inbox_count,
            "closed_capture_count": closed_capture_count,
            "sign_off_count": len(signoffs.get("sign_offs") or []),
            "incomplete_count": view_rows.get("incomplete_work_items", {}).get("count"),
            "blocked_count": view_rows.get("blocked", {}).get("count"),
            "capture_triage_count": view_rows.get("capture_triage", {}).get("count"),
            "shaped_ready_count": shaped_ready_count,
            "stale_capture_count": view_rows.get("capture_triage", {}).get("stale_capture_count"),
            "duplicate_or_retire_candidate_count": view_rows.get("merge_or_retire_candidates", {}).get("count"),
            "execution_menu_count": view_rows.get("execution_menu", {}).get("count"),
            "execution_menu_schedulable_count": view_rows.get("execution_menu_schedulable", {}).get("count"),
            "schedulable_by_rank_count": view_rows.get("schedulable_by_rank", {}).get("count"),
            "dependency_blocked_count": view_rows.get("dependency_blocked", {}).get("count"),
            "dependency_anomaly_count": view_rows.get("dependency_anomalies", {}).get("count"),
            "missing_contracts_ranked_count": view_rows.get("missing_contracts_ranked", {}).get("count"),
            "missing_contract_count": view_rows.get("missing_contracts_ranked", {}).get("count"),
            "task_ledger_prompt_ref_count": (
                view_rows.get("capture_triage", {}).get("linkage_counts") or {}
            ).get("prompt_trace_linked"),
            "task_ledger_work_ledger_ref_count": (
                view_rows.get("capture_triage", {}).get("linkage_counts") or {}
            ).get("work_ledger_linked"),
        },
        "views": view_rows,
    }


def _task_ledger_materialized_projection_packet(
    repo_root: Path,
    *,
    view_names: Sequence[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ledger = _safe_read_json(repo_root / task_ledger_events.LEDGER_REL)
    signoffs = _safe_read_json(repo_root / task_ledger_events.SIGNOFFS_REL)
    views: dict[str, Any] = {}
    requested_views = {str(name) for name in (view_names or []) if str(name or "").strip()}
    views_root = repo_root / task_ledger_events.VIEWS_REL
    if views_root.exists():
        view_paths = (
            [views_root / f"{name}.json" for name in sorted(requested_views)]
            if requested_views
            else sorted(views_root.glob("*.json"))
        )
        for path in view_paths:
            payload = _safe_read_json(path)
            if payload:
                views[path.stem] = payload
    if not ledger and not views:
        return (
            {
                "ok": False,
                "validation_error": "Task Ledger materialized projections are missing",
                "authority": str(task_ledger_events.EVENTS_REL),
                "projection": str(task_ledger_events.LEDGER_REL),
            },
            [
                {
                    "kind": "projection_missing",
                    "surface": str(task_ledger_events.LEDGER_REL),
                    "reason": "agent-wake fast path needs materialized Task Ledger projections",
                }
            ],
        )
    validation = {
        "source_mode": "materialized_projection",
        "authority_validation": "skipped_for_fast_agent_wake_packet",
        "projection": str(task_ledger_events.LEDGER_REL),
        "projection_mtime": _safe_mtime_iso(repo_root / task_ledger_events.LEDGER_REL),
        "view_filter": sorted(requested_views) if requested_views else None,
    }
    return (
        _task_ledger_projection_payload(
            validation=validation,
            event_count=ledger.get("event_count") if isinstance(ledger, Mapping) else None,
            ledger=ledger,
            signoffs=signoffs,
            views=views,
        ),
        [],
    )


def _task_ledger_packet(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    try:
        validation = task_ledger_events.validate_event_log(repo_root)
        events = task_ledger_events.load_and_validate_events(repo_root)
        projection = task_ledger_events.build_projection(events)
    except Exception as exc:  # noqa: BLE001 - entrypoint should degrade with a blocker
        blockers.append(
            {
                "kind": "authority_validation_failed",
                "surface": "state/task_ledger/events.jsonl",
                "reason": str(exc),
            }
        )
        return (
            {
                "ok": False,
                "validation_error": str(exc),
                "authority": "state/task_ledger/events.jsonl",
            },
            blockers,
        )

    ledger = projection.get("ledger") if isinstance(projection.get("ledger"), Mapping) else {}
    signoffs = projection.get("sign_offs") if isinstance(projection.get("sign_offs"), Mapping) else {}
    views = projection.get("views") if isinstance(projection.get("views"), Mapping) else {}
    return (
        _task_ledger_projection_payload(
            validation=validation,
            event_count=len(events),
            ledger=ledger,
            signoffs=signoffs,
            views=views,
        ),
        blockers,
    )


def _work_ledger_packet(repo_root: Path, *, limit: int) -> dict[str, Any]:
    try:
        status = work_ledger_runtime.load_runtime_status(repo_root)
        overview = work_ledger_runtime.build_session_cohort_overview(status, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(exc),
            "authority": "state/work_ledger/runtime_status.json",
            "claim_required_before_mutation": True,
            "closeout_before_finalize_required": True,
        }
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    stale_rows = overview.get("stale_sessions") if isinstance(overview.get("stale_sessions"), list) else []
    repaired = _forward_repaired_stale_sessions(repo_root, stale_rows=stale_rows)
    return {
        "ok": True,
        "authority": "state/work_ledger/runtime_status.json",
        "risk_level": overview.get("risk_level"),
        "signals": overview.get("signals") or [],
        "counts": counts,
        "active_claims": overview.get("active_claims") or [],
        "contention": overview.get("contention") or {},
        "stale_sessions": repaired,
        "recommended_actions": overview.get("recommended_actions") or [],
        "claim_required_before_mutation": True,
        "closeout_before_finalize_required": True,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _forward_repaired_stale_sessions(repo_root: Path, *, stale_rows: Sequence[Any]) -> dict[str, Any]:
    repairs_by_source: dict[str, dict[str, Any]] = {}
    for jsonl_path in sorted((repo_root / "codex/ledger").glob("*/work_ledger.jsonl")):
        for row in _read_jsonl(jsonl_path):
            metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
            source_session = str(metadata.get("source_work_ledger_session") or "").strip()
            if not source_session:
                continue
            repairs_by_source[source_session] = {
                "stale_session_id": source_session,
                "repair_session_id": row.get("actor_session_id"),
                "repair_td_id": row.get("td_id"),
                "repair_event_id": row.get("event_id"),
                "phase_id": row.get("phase_id"),
                "ledger_path": normalize_repo_path(repo_root, jsonl_path),
                "repair_reason": metadata.get("repair_reason"),
            }
    stale_ids = {
        str(row.get("session_id") or "")
        for row in stale_rows
        if isinstance(row, Mapping)
    }
    repaired = [
        repair
        for source_id, repair in sorted(repairs_by_source.items())
        if not stale_ids or source_id in stale_ids
    ]
    repaired_ids = {str(item.get("stale_session_id") or "") for item in repaired}
    unresolved = [
        row
        for row in stale_rows
        if isinstance(row, Mapping) and str(row.get("session_id") or "") not in repaired_ids
    ]
    return {
        "unresolved_count": len(unresolved),
        "unresolved_sample": unresolved[:10],
        "forward_repaired_count": len(repaired),
        "forward_repaired": repaired[:25],
    }


def _phase_packet(repo_root: Path, phase_token: str | None) -> dict[str, Any]:
    try:
        nav = KernelNavigation(repo_root)
        result = nav.build_phase(phase_token)
        payload = result.payload if hasattr(result, "payload") else dict(result)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "phase_id": phase_token}
    phase_payload = payload if isinstance(payload, Mapping) else {}
    phase = phase_payload.get("phase") if isinstance(phase_payload.get("phase"), Mapping) else {}
    active_wave = (
        phase_payload.get("active_wave")
        if isinstance(phase_payload.get("active_wave"), Mapping)
        else (phase_payload.get("phase_card") or {}).get("current_wave")
        if isinstance((phase_payload.get("phase_card") or {}).get("current_wave"), Mapping)
        else {}
    )
    lifecycle = (
        phase_payload.get("phase_lifecycle_enforcement")
        if isinstance(phase_payload.get("phase_lifecycle_enforcement"), Mapping)
        else {}
    )
    closeout = phase_payload.get("closeout") if isinstance(phase_payload.get("closeout"), Mapping) else {}
    derived_index = phase_payload.get("derived_index") if isinstance(phase_payload.get("derived_index"), Mapping) else {}
    subphase_id = active_wave.get("wave_id") or active_wave.get("id") or phase.get("current_wave_id")
    return {
        "ok": True,
        "phase_id": phase.get("phase_id") or phase_payload.get("phase_id"),
        "requested_phase": phase_token or "__active__",
        "phase": phase,
        "subphase": {
            "subphase_id": subphase_id,
            "source": "kernel.py --phase active_wave",
            "work_item_streams": active_wave.get("work_item_streams") or [],
            "status": active_wave.get("status"),
            "objective": active_wave.get("objective"),
            "closeout_policy": {
                "task_ledger_signoff_or_residual_required": True,
                "work_ledger_closeout_before_finalize_required": True,
            },
        },
        "phase_lifecycle_enforcement": lifecycle,
        "closeout": {
            "path": closeout.get("path"),
            "exists": closeout.get("exists"),
            "status": closeout.get("status"),
            "closed_at": closeout.get("closed_at"),
        },
        "derived_index": {
            "path": derived_index.get("path"),
            "exists": derived_index.get("exists"),
            "entry": derived_index.get("entry") if isinstance(derived_index.get("entry"), Mapping) else None,
        },
        "warnings": list(getattr(result, "warnings", []) or []),
        "suggested_next": list(getattr(result, "suggested_next", []) or []),
        "sources": {
            "live": list(getattr(result, "live_sources", []) or []),
            "derived": list(getattr(result, "derived_sources", []) or []),
        },
    }


def _phase_freshness_packet(repo_root: Path, *, phase: Mapping[str, Any]) -> dict[str, Any]:
    if not phase.get("ok"):
        return {
            "authority": "projection_only",
            "source_authority": "kernel.py --phase",
            "freshness_status": "unknown",
            "phase_staleness_reason": [str(phase.get("error") or "kernel phase packet unavailable")],
            "requested_phase": phase.get("phase_id"),
            "kernel_reported_phase": None,
            "recommended_actions": [
                {
                    "command": "./repo-python kernel.py --phase <phase>",
                    "reason": "Recover phase truth before mutating phase-scoped surfaces.",
                }
            ],
        }

    phase_row = phase.get("phase") if isinstance(phase.get("phase"), Mapping) else {}
    subphase = phase.get("subphase") if isinstance(phase.get("subphase"), Mapping) else {}
    lifecycle = (
        phase.get("phase_lifecycle_enforcement")
        if isinstance(phase.get("phase_lifecycle_enforcement"), Mapping)
        else {}
    )
    explicit = (
        lifecycle.get("explicit_active_phase")
        if isinstance(lifecycle.get("explicit_active_phase"), Mapping)
        else {}
    )
    focus_conflicts = lifecycle.get("focus_conflicts") if isinstance(lifecycle.get("focus_conflicts"), list) else []
    closeout = phase.get("closeout") if isinstance(phase.get("closeout"), Mapping) else {}
    sources = phase.get("sources") if isinstance(phase.get("sources"), Mapping) else {}
    source_paths = [
        str(path)
        for path in [
            *((sources.get("live") or []) if isinstance(sources.get("live"), list) else []),
            *((sources.get("derived") or []) if isinstance(sources.get("derived"), list) else []),
            explicit.get("family_marker_path"),
            closeout.get("path"),
            str(PHASE_INDEX_REL),
        ]
        if str(path or "").strip()
    ]
    derived_phase_index = _safe_read_json(repo_root / PHASE_INDEX_REL)
    derived_active_phase = str(derived_phase_index.get("active_phase_id") or "").strip() or None
    kernel_phase = str(phase_row.get("phase_id") or phase.get("phase_id") or "").strip() or None
    explicit_active = str(explicit.get("phase_id") or "").strip() or None
    selected_matches = lifecycle.get("selected_matches_explicit_active")
    reasons: list[str] = []
    if selected_matches is False:
        reasons.append("requested phase does not match explicit active phase marker")
    if focus_conflicts:
        reasons.append("non-active phase notes still claim active/default focus")
    if derived_active_phase and kernel_phase and derived_active_phase != kernel_phase:
        reasons.append(
            f"derived phase index active_phase_id={derived_active_phase} differs from kernel_reported_phase={kernel_phase}"
        )
    if closeout.get("exists") is True:
        reasons.append("phase has a closeout artifact; verify before treating it as active")
    if not kernel_phase:
        reasons.append("kernel phase id absent")

    if not kernel_phase:
        freshness_status = "unknown"
    elif selected_matches is False or focus_conflicts:
        freshness_status = "conflicting"
    elif derived_active_phase and derived_active_phase != kernel_phase:
        freshness_status = "stale"
    else:
        freshness_status = "current"

    recommended_actions = [
        item
        for item in phase.get("suggested_next") or []
        if isinstance(item, Mapping)
        and (
            "phase-demote-stale-focus" in str(item.get("command") or "")
            or "phase-step" in str(item.get("command") or "")
            or "phase-assimilate" in str(item.get("command") or "")
        )
    ][:5]
    if not recommended_actions:
        recommended_actions = [
            {
                "command": f"./repo-python kernel.py --phase-step {kernel_phase or '<phase>'}",
                "reason": "Preview the controller-owned next bounded wave action before mutating phase-scoped surfaces.",
            }
        ]

    return {
        "authority": "projection_only",
        "source_authority": "kernel.py --phase",
        "requested_phase": phase.get("requested_phase"),
        "kernel_reported_phase": kernel_phase,
        "explicit_active_phase": explicit_active,
        "explicit_active_phase_source": explicit.get("family_marker_path"),
        "explicit_active_changed_at": explicit.get("changed_at"),
        "active_subphase": {
            "subphase_id": subphase.get("subphase_id"),
            "status": subphase.get("status"),
            "objective": subphase.get("objective"),
            "source": subphase.get("source"),
        },
        "freshness_status": freshness_status,
        "phase_staleness_reason": reasons,
        "focus_conflict_count": len(focus_conflicts),
        "focus_conflicts": focus_conflicts[:5],
        "derived_phase_index": {
            "path": str(PHASE_INDEX_REL),
            "exists": (repo_root / PHASE_INDEX_REL).exists(),
            "generated_at": derived_phase_index.get("generated_at"),
            "active_phase_id": derived_active_phase,
            "mtime": _safe_mtime_iso(repo_root / PHASE_INDEX_REL),
        },
        "phase_closeout": closeout,
        "evidence_paths": sorted(set(source_paths)),
        "recommended_actions": recommended_actions,
        "mutation_rule": "do not mutate phase files through this packet; use phase owner tooling or append WorkItems for ambiguity",
    }


def _prompt_trace_packet(repo_root: Path) -> dict[str, Any]:
    candidates = {
        "uppropagation_index": "state/prompt_shelf/uppropagation_index.json",
        "runs_index": "state/prompt_shelf/prompt_shelf_runs_index.json",
        "prompt_ledger_events": "state/prompt_ledger/events.jsonl",
        "workitem_prompt_links": "state/prompt_ledger/views/workitem_prompt_links.json",
        "unlinked_prompt_traces": "state/prompt_ledger/views/unlinked_prompt_traces.json",
        "source_stream_cursors": "state/prompt_ledger/views/source_stream_cursors.json",
        "source_idempotency_keys": "state/prompt_ledger/views/source_idempotency_keys.json",
        "source_drift": "state/prompt_ledger/views/source_drift.json",
    }
    rows: dict[str, dict[str, Any]] = {}
    for key, rel in candidates.items():
        path = repo_root / rel
        rows[key] = {"path": rel, "exists": path.exists(), "projection_only": key != "prompt_ledger_events"}
        if path.suffix == ".json":
            payload = _safe_read_json(path)
            if payload:
                for count_key in ("count", "run_count", "event_count", "trace_count"):
                    if count_key in payload:
                        rows[key]["count"] = payload.get(count_key)
                        break
    return {
        "authority": "trace_only_until_adopted",
        "surfaces": rows,
        "blocking": False,
    }


def _provider_packet(repo_root: Path) -> dict[str, Any]:
    surfaces = {
        "compute_receipts": "state/compute_workers/receipts",
        "compute_row_patches": "state/compute_workers/row_patches",
        "compute_transform_jobs": "state/compute_workers/transform_jobs",
        "compute_cache": "state/compute_workers/cache",
        "compute_run_fingerprints": "state/compute_workers/run_fingerprints",
        "provider_model_catalog_signal": "system/lib/provider_metabolism_signal.py",
        "provider_reaction_ledger": "tools/meta/control/reactions_ledger.jsonl",
    }
    projected: dict[str, dict[str, Any]] = {}
    for key, rel in surfaces.items():
        path = repo_root / rel
        row = {
            "path": rel,
            "exists": path.exists(),
            "projection_only": key
            not in {
                "compute_receipts",
                "compute_row_patches",
                "compute_transform_jobs",
                "compute_cache",
                "compute_run_fingerprints",
            },
        }
        if path.is_dir():
            row["json_count"] = len(list(path.glob("**/*.json")))
        projected[key] = row
    return {
        "authority": "compute_worker_receipt_only_until_adopted",
        "source_authority": "state/compute_workers receipts, row_patches, transform_jobs, cache, and run_fingerprints",
        "surfaces": projected,
        "candidate_feed_surface": "system.lib.provider_metabolism_signal.derive_provider_model_catalog_candidate_feed",
        "mutation_rule": "provider output may create compute-worker receipts and row patches; WorkItems adopt only after review or explicit promotion",
        "blocking": False,
    }


def _claim_collisions_for_targets(
    active_claims: Sequence[Mapping[str, Any]],
    target_paths: Sequence[str],
    *,
    session_id: str | None,
) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    for claim in active_claims:
        claim_path = str(claim.get("path") or claim.get("scope_id") or "").strip()
        if not claim_path:
            continue
        if session_id and str(claim.get("session_id") or "") == session_id:
            continue
        for target in target_paths:
            if path_scope_overlaps(claim_path, target):
                collisions.append(
                    {
                        "path": claim_path,
                        "target_path": target,
                        "session_id": claim.get("session_id"),
                        "actor": claim.get("actor"),
                        "claim_id": claim.get("claim_id"),
                    }
                )
    return collisions


def _git_status_rows(repo_root: Path, *, dirty_paths: Sequence[str] | None = None) -> list[dict[str, Any]]:
    if dirty_paths is not None:
        return [
            {"path": normalize_repo_path(repo_root, path), "status": "dirty_override"}
            for path in dirty_paths
            if str(path or "").strip()
        ]
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1", "-z"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    entries = proc.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:].strip()
        if status.strip().startswith(("R", "C")) and index < len(entries) and entries[index]:
            path = entries[index].strip()
            index += 1
        if path:
            rows.append({"path": path, "status": status})
    return rows


def _recommended_commit_message(scoped_paths: Sequence[str]) -> str:
    if not scoped_paths:
        return ""
    if any("strict_json" in path or "std_strict_json_artifact" in path for path in scoped_paths):
        return "runtime: add strict JSON artifact standard"
    if any("task_ledger_events.py" in path or "capture_triage" in path or "execution_menu" in path for path in scoped_paths):
        return "task-ledger: add capture execution menu"
    if any("prompt_ledger" in path for path in scoped_paths):
        return "prompt-ledger: add stream idempotency and cursors"
    if any("uppropagation" in path or "uppropagate" in path for path in scoped_paths):
        return "runtime: add up-propagation intake lane"
    if any("forward_integration" in path or "workitem_runtime_entrypoint" in path for path in scoped_paths):
        return "runtime: harden forward integration entrypoint"
    if any(path.startswith("state/task_ledger/") for path in scoped_paths):
        return "task-ledger: update WorkItem runtime receipts"
    return "runtime: update WorkItem scoped surfaces"


def _commit_readiness(
    repo_root: Path,
    *,
    forward_policy: Mapping[str, Any],
    target_paths: Sequence[str],
    blockers: Sequence[Mapping[str, Any]],
    safe_to_continue: bool,
    dirty_paths: Sequence[str] | None,
) -> dict[str, Any]:
    status_rows = _git_status_rows(repo_root, dirty_paths=dirty_paths)
    dirty_path_rows = [
        {"path": normalize_repo_path(repo_root, row["path"]), "status": row.get("status")}
        for row in status_rows
        if str(row.get("path") or "").strip()
    ]
    targets = [normalize_repo_path(repo_root, path) for path in target_paths if str(path or "").strip()]
    scoped = [
        row
        for row in dirty_path_rows
        if any(path_scope_overlaps(str(row["path"]), target) or path_scope_overlaps(target, str(row["path"])) for target in targets)
    ]
    scoped_paths = sorted({str(row["path"]) for row in scoped})
    unrelated = [
        row
        for row in dirty_path_rows
        if str(row["path"]) not in scoped_paths
    ]
    target_policy = forward_policy.get("target_path_policy") if isinstance(forward_policy.get("target_path_policy"), Mapping) else {}
    generated_receipt_paths = [
        path
        for path, policy in target_policy.items()
        if isinstance(policy, Mapping) and policy.get("owner_tool_or_adoption_receipt_required")
    ]
    authority_paths = [
        path
        for path in forward_policy.get("strict_validation_required_paths") or []
        if path in scoped_paths or path in targets
    ]
    commit_blockers = [str(item.get("kind") or "unknown_blocker") for item in blockers]
    if not targets:
        commit_blockers.append("no_target_commit_scope")
    elif not scoped_paths:
        commit_blockers.append("no_scoped_changed_paths")
    commit_blockers.extend(
        f"generated_projection_requires_owner_tool_or_adoption_receipt:{path}"
        for path in generated_receipt_paths
    )
    commit_blockers = sorted(set(commit_blockers))
    safe_to_commit = bool(safe_to_continue and scoped_paths and not commit_blockers)
    return {
        "mode": "forward_integration",
        "safe_to_commit_scoped_progress": safe_to_commit,
        "scoped_changed_paths": scoped_paths,
        "authority_paths_requiring_validation": sorted(set(authority_paths)),
        "generated_paths_requiring_owner_tool_or_receipt": sorted(set(generated_receipt_paths)),
        "unrelated_dirty_path_count": len(unrelated),
        "unrelated_dirty_paths_excluded": unrelated[:80],
        "commit_blockers": commit_blockers,
        "owner_tool_hints": {
            path: owner_tool_entries_for_path(path)
            for path in scoped_paths
            if owner_tool_entries_for_path(path)
        },
        "recommended_commit_message": _recommended_commit_message(scoped_paths),
    }


def _projection_affordances(
    task_ledger: Mapping[str, Any],
    live_work_runtime_attention: Mapping[str, Any],
    concurrency_attention: Mapping[str, Any],
    strict_json_attention: Mapping[str, Any],
    phase_runtime_context: Mapping[str, Any],
    subphase_runtime_attention: Mapping[str, Any],
    applicable_mechanisms: Sequence[Mapping[str, Any]],
    prompt_trace: Mapping[str, Any],
    provider: Mapping[str, Any],
    uppropagation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    views = task_ledger.get("views") if isinstance(task_ledger.get("views"), Mapping) else {}
    return [
        {
            "kind": "kanban_projection",
            "id": "task_ledger_kanban",
            "authority": "projection_only",
            "source_authority": "state/task_ledger/events.jsonl",
            "views": [
                views.get(name, {"path": f"state/task_ledger/views/{name}.json"})
                for name in (
                    "capture_inbox",
                    "capture_triage",
                    "execution_menu",
                    "ready_by_rank",
                    "active_wip",
                    "blocked",
                    "needs_signoff",
                )
            ],
            "use_when": ["choose next work", "inspect WIP", "find review/signoff/blockers"],
            "mutation_rule": "append Task Ledger events; never mutate board rows",
        },
        {
            "kind": "workitem_backlog_health_projection",
            "id": "capture_inbox_execution_menu",
            "authority": "projection_only",
            "source_authority": "state/task_ledger/events.jsonl",
            "views": [
                views.get(name, {"path": f"state/task_ledger/views/{name}.json"})
                for name in (
                    "capture_triage",
                    "execution_menu",
                    "merge_or_retire_candidates",
                    "missing_contracts_ranked",
                )
            ],
            "use_when": [
                "turn capture inbox into next bounded proof",
                "find duplicate or already-closed captures",
                "shape missing WorkItem contracts before implementation",
            ],
            "mutation_rule": "append Task Ledger shape/promote/retire/signoff events; projections are read-only",
        },
        {
            "kind": "live_work_runtime_attention_projection",
            "id": "live_work_runtime_attention",
            "authority": "projection_only",
            "source_authority": live_work_runtime_attention.get("source_authority"),
            "use_when": [
                "choose current work without reopening phase/subphase files",
                "inspect Task Ledger WorkItems and Work Ledger claim pressure before mutation",
                "keep phase/subphase identity as context rather than liveness authority",
            ],
            "recommended_workitem_ids": live_work_runtime_attention.get("recommended_workitem_ids") or [],
            "safe_parallelism_status": live_work_runtime_attention.get("safe_parallelism_status"),
            "mutation_rule": live_work_runtime_attention.get("mutation_rule"),
        },
        {
            "kind": "hud_projection",
            "id": "workitem_hud",
            "authority": "projection_only",
            "source_authority": "Task Ledger + Work Ledger",
            "use_when": ["runtime orientation", "contention scan", "closeout readiness"],
        },
        {
            "kind": "work_ledger_concurrency_projection",
            "id": "concurrency_attention",
            "authority": "projection_only",
            "source_authority": "state/work_ledger/runtime_status.json",
            "use_when": ["choose safe parallel work", "inspect claim collisions", "route around stale or unknown-scope sessions"],
            "safe_parallelism_status": concurrency_attention.get("safe_parallelism_status"),
            "mutation_rule": "claim/release/close through Work Ledger; do not edit this projection",
        },
        {
            "kind": "phase_runtime_context_projection",
            "id": "phase_runtime_context",
            "authority": "projection_only",
            "source_authority": phase_runtime_context.get("source_authority"),
            "use_when": [
                "explain phase/wave context after live WorkItems have been selected",
                "separate phase freshness warnings from Work Ledger claim blockers",
                "avoid treating legacy subphase naming as current-work authority",
            ],
            "context_role": phase_runtime_context.get("context_role"),
            "legacy_projection_id": phase_runtime_context.get("legacy_projection_id"),
            "mutation_rule": phase_runtime_context.get("mutation_rule"),
        },
        {
            "kind": "subphase_runtime_attention_projection",
            "id": "subphase_runtime_attention",
            "authority": "projection_only",
            "source_authority": subphase_runtime_attention.get("source_authority"),
            "compatibility_status": "legacy_alias_of_phase_runtime_context",
            "use_when": [
                "support older consumers that still read subphase_runtime_attention",
                "prefer phase_runtime_context for new WorkItem-first routing",
            ],
            "safe_parallelism_status": subphase_runtime_attention.get("safe_parallelism_status"),
            "mutation_rule": subphase_runtime_attention.get("mutation_rule"),
        },
        {
            "kind": "mechanism_affordance_projection",
            "id": "applicable_mechanisms",
            "authority": "projection_only",
            "source_authority": [
                "codex/standards",
                "codex/doctrine/skills",
                "system/lib",
                "tools/meta/factory",
            ],
            "use_when": [
                "find code-grounded recipes that apply to this WorkItem/runtime posture",
                "avoid decorative mechanism theory disconnected from owner tools",
            ],
            "mechanism_count": len(applicable_mechanisms),
            "mutation_rule": "mechanisms are discoverable recipes; mutate through their listed authority and owner tools",
        },
        {
            "kind": "strict_json_artifact_validation_projection",
            "id": "strict_json_artifact_attention",
            "authority": "projection_only",
            "source_authority": strict_json_attention.get("standard_path"),
            "use_when": [
                "classify JSON/JSONL authority versus projection surfaces",
                "find owner-tool rebuild/check commands before commit",
                "avoid hand-editing generated projections",
            ],
            "strict_json_status": strict_json_attention.get("status"),
            "mutation_rule": "validate through owning tools; standards define contracts but do not mutate ledger state",
        },
        {
            "kind": "station_projection",
            "id": "station",
            "authority": "projection_only",
            "source_authority": "registered ledgers and generated views",
            "use_when": ["operator cockpit", "cross-surface scanning"],
        },
        {
            "kind": "prompt_trace_projection",
            "id": "prompt_trace",
            "authority": prompt_trace.get("authority"),
            "source_authority": "Prompt Ledger events when present; prompt shelf traces otherwise",
            "surfaces": prompt_trace.get("surfaces"),
            "mutation_rule": "record provenance; derived work mutates through Task Ledger",
        },
        {
            "kind": "uppropagation_intake_projection",
            "id": "uppropagation_intake",
            "authority": "projection_only",
            "source_authority": uppropagation.get("source_authority"),
            "surfaces": uppropagation.get("surfaces"),
            "use_when": [
                "adopt local lessons",
                "link prompt/work/provider evidence to WorkItems",
                "inspect repeated intake idempotency and drift",
            ],
            "mutation_rule": uppropagation.get("mutation_rule"),
        },
        {
            "kind": "provider_queue_projection",
            "id": "provider_queue",
            "authority": provider.get("authority"),
            "source_authority": "provider receipt events when present",
            "surfaces": provider.get("surfaces"),
            "mutation_rule": "provider outputs become strict only when adopted into receipts or WorkItems",
        },
    ]


def _strict_json_artifact_attention_packet(
    task_ledger: Mapping[str, Any],
    *,
    repo_root: Path,
    target_paths: Sequence[str],
) -> dict[str, Any]:
    validation = task_ledger.get("validation") if isinstance(task_ledger.get("validation"), Mapping) else {}
    strict = validation.get("strict_json") if isinstance(validation.get("strict_json"), Mapping) else {}
    checked_paths = [str(path) for path in strict.get("paths") or []]
    known_paths = [
        "codex/standards/std_strict_json_artifact.json",
        "state/task_ledger/events.jsonl",
        "state/task_ledger/ledger.json",
        "state/task_ledger/sign_offs.json",
        "state/task_ledger/views/*.json",
        "state/prompt_ledger/events.jsonl",
        "state/prompt_ledger/ledger.json",
        "state/prompt_ledger/views/*.json",
        "codex/ledger/*/work_ledger.jsonl",
        "codex/ledger/*/work_ledger_index.json",
    ]
    scoped_paths = [normalize_repo_path(repo_root, path) for path in target_paths if str(path or "").strip()]
    scoped_report = strict_json.strict_json_artifact_report(scoped_paths)
    blocker_count = len(scoped_report.get("unknown_paths") or [])
    return {
        "authority": "projection_only",
        "source_authority": "codex/standards/std_strict_json_artifact.json",
        "standard_path": "codex/standards/std_strict_json_artifact.json",
        "status": "ok" if blocker_count == 0 else "inspection_required",
        "strict_json_checked_count": strict.get("checked_count", 0),
        "checked_scope": "task_ledger_strict_surfaces_from_current_entrypoint_validation",
        "additional_strict_surfaces_require_commands": [
            "./repo-python tools/meta/observability/prompt_ledger.py validate",
            "./repo-python tools/meta/factory/work_ledger.py session-status --overview --limit 20",
        ],
        "strict_json_authority_paths": [
            "state/task_ledger/events.jsonl",
            "state/prompt_ledger/events.jsonl",
            "codex/ledger/*/work_ledger.jsonl",
            "codex/standards/*.json",
        ],
        "strict_json_projection_paths": [
            "state/task_ledger/ledger.json",
            "state/task_ledger/sign_offs.json",
            "state/task_ledger/views/*.json",
            "state/prompt_ledger/ledger.json",
            "state/prompt_ledger/views/*.json",
            "codex/ledger/*/work_ledger_index.json",
        ],
        "event_log_paths": [
            "state/task_ledger/events.jsonl",
            "state/prompt_ledger/events.jsonl",
            "codex/ledger/*/work_ledger.jsonl",
        ],
        "generated_projection_paths": [
            "state/task_ledger/ledger.json",
            "state/task_ledger/sign_offs.json",
            "state/task_ledger/views/*.json",
            "state/prompt_ledger/ledger.json",
            "state/prompt_ledger/views/*.json",
            "codex/ledger/*/work_ledger_index.json",
        ],
        "owner_tool_required_paths": [
            "state/task_ledger/views/*.json",
            "state/prompt_ledger/views/*.json",
            "codex/ledger/*/work_ledger_index.json",
        ],
        "strict_validation_commands": [
            "./repo-python tools/meta/factory/task_ledger_apply.py validate",
            "./repo-python tools/meta/observability/prompt_ledger.py validate",
            "./repo-python -m py_compile system/lib/strict_json.py",
        ],
        "projection_check_commands": [
            "./repo-python tools/meta/factory/task_ledger_project.py rebuild --check",
            "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
        ],
        "relevant_standards": [
            "codex/standards/std_strict_json_artifact.json",
            "codex/standards/std_task_ledger.json",
            "codex/standards/std_prompt_ledger.json",
        ],
        "failure_policy": [
            "duplicate_keys_fail_before_schema_or_replay_validation",
            "event_logs_validate_hash_chains_when_chain_fields_exist",
            "generated_projections_require_owner_tool_or_adoption_receipt_if_targeted",
            "unrelated_dirty_surfaces_do_not_block_scoped_forward_progress",
        ],
        "scoped_target_obligations": scoped_report.get("items") or [],
        "missing_or_unknown_artifact_classes": scoped_report.get("unknown_paths") or [],
        "known_artifact_rules": strict_json.artifact_rules_payload(),
        "checked_paths_preview": checked_paths[:12],
        "known_paths_preview": known_paths,
        "next_legal_actions": [
            "classify target JSON/JSONL paths before mutation",
            "run strict validation commands for touched authority surfaces",
            "run owner-tool rebuild/check for touched projections",
            "capture residuals instead of hand-editing generated views",
        ],
    }


def _uppropagation_intake_packet(repo_root: Path) -> dict[str, Any]:
    candidates = {
        "ledger": str(uppropagation_intake.LEDGER_REL),
        "pending_adoption": str(uppropagation_intake.PENDING_ADOPTION_REL),
        "linked_sources": str(uppropagation_intake.LINKED_SOURCES_REL),
        "source_drift": str(uppropagation_intake.SOURCE_DRIFT_REL),
    }
    rows: dict[str, dict[str, Any]] = {}
    for key, rel in candidates.items():
        path = repo_root / rel
        rows[key] = {"path": rel, "exists": path.exists(), "projection_only": True}
        payload = _safe_read_json(path)
        if payload:
            for count_key in ("count", "intake_count", "pending_count", "drift_count"):
                if count_key in payload:
                    rows[key]["count"] = payload.get(count_key)
                    break
    return {
        "authority": "projection_only",
        "source_authority": [
            str(task_ledger_events.EVENTS_REL),
            "state/prompt_ledger/events.jsonl",
        ],
        "surfaces": rows,
        "blocking": False,
        "mutation_rule": "intake appends Task Ledger captures and Prompt Ledger links; projections are rebuilt",
        "next_legal_actions": [
            "./repo-python tools/meta/factory/uppropagate.py intake --source-kind prompt_ledger --source-ref <event_id> --dry-run",
            "./repo-python tools/meta/factory/uppropagate.py intake --source-kind final_report --source-ref <ref> --payload-file <file> --dry-run",
        ],
    }


def _surface_count(packet: Mapping[str, Any], surface_id: str) -> int | None:
    surfaces = packet.get("surfaces") if isinstance(packet.get("surfaces"), Mapping) else {}
    surface = surfaces.get(surface_id) if isinstance(surfaces.get(surface_id), Mapping) else {}
    value = surface.get("count")
    return int(value) if isinstance(value, int) else None


def _workitem_backlog_health_packet(
    task_ledger: Mapping[str, Any],
    *,
    prompt_trace: Mapping[str, Any],
) -> dict[str, Any]:
    views = task_ledger.get("views") if isinstance(task_ledger.get("views"), Mapping) else {}
    counts = task_ledger.get("counts") if isinstance(task_ledger.get("counts"), Mapping) else {}
    execution_menu = views.get("execution_menu") if isinstance(views.get("execution_menu"), Mapping) else {}
    capture_triage = views.get("capture_triage") if isinstance(views.get("capture_triage"), Mapping) else {}
    linkage_counts = capture_triage.get("linkage_counts") if isinstance(capture_triage.get("linkage_counts"), Mapping) else {}
    prompt_linked_count = _surface_count(prompt_trace, "workitem_prompt_links")
    prompt_unlinked_count = _surface_count(prompt_trace, "unlinked_prompt_traces")
    return {
        "authority": "projection_only",
        "source_authority": str(task_ledger_events.EVENTS_REL),
        "capture_inbox_count": counts.get("capture_count"),
        "capture_inbox_count_semantics": "total_capture_log_including_closed_shaped_and_raw_rows",
        "total_capture_count": counts.get("total_capture_count"),
        "raw_capture_inbox_count": counts.get("raw_capture_inbox_count"),
        "active_capture_inbox_count": counts.get("active_capture_inbox_count"),
        "closed_capture_count": counts.get("closed_capture_count"),
        "capture_triage_count": counts.get("capture_triage_count"),
        "incomplete_count": counts.get("incomplete_count"),
        "shaped_ready_count": counts.get("shaped_ready_count"),
        "blocked_count": counts.get("blocked_count"),
        "stale_capture_count": counts.get("stale_capture_count"),
        "duplicate_or_retire_candidate_count": counts.get("duplicate_or_retire_candidate_count"),
        "missing_contract_count": counts.get("missing_contract_count"),
        "missing_contracts_ranked_count": counts.get("missing_contracts_ranked_count"),
        "prompt_linked_count": prompt_linked_count if prompt_linked_count is not None else linkage_counts.get("prompt_trace_linked"),
        "prompt_unlinked_trace_count": prompt_unlinked_count,
        "task_ledger_prompt_ref_count": counts.get("task_ledger_prompt_ref_count"),
        "work_ledger_linked_count": counts.get("task_ledger_work_ledger_ref_count"),
        "execution_menu_count": counts.get("execution_menu_count"),
        "capture_status_counts": capture_triage.get("counts_by_status") or {},
        "capture_category_counts": capture_triage.get("category_counts") or {},
        "capture_linkage_counts": linkage_counts,
        "recommended_next_workitems": (
            (views.get("execution_menu_schedulable") or {}).get("items_preview")
            if isinstance(views.get("execution_menu_schedulable"), Mapping)
            else None
        ) or _view_items(views, "schedulable_by_rank") or execution_menu.get("items_preview") or [],
        "why_these_next": execution_menu.get("why_these_next") or [],
        "wip_policy": execution_menu.get("wip_policy") or "keep active implementation WIP small; capture inbox may be large",
        "views": {
            "capture_triage": views.get("capture_triage"),
            "execution_menu": views.get("execution_menu"),
            "merge_or_retire_candidates": views.get("merge_or_retire_candidates"),
            "missing_contracts_ranked": views.get("missing_contracts_ranked"),
        },
        "next_legal_actions": [
            "choose from state/task_ledger/views/execution_menu_schedulable.json first, then schedulable_by_rank.json, with legacy execution_menu.json / ready_by_rank.json fallback",
            "append work_item.shaped for captures missing completion or contracts",
            "append work_item.promoted only for a capture selected into active WIP",
            "append work_item.retired for duplicates or obsolete captures; never delete history",
        ],
    }


def _view_items(views: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    view = views.get(name) if isinstance(views.get(name), Mapping) else {}
    return [item for item in (view.get("items_preview") or []) if isinstance(item, dict)]


def _workitem_backlog_attention_packet(
    task_ledger: Mapping[str, Any],
    *,
    backlog_health: Mapping[str, Any],
) -> dict[str, Any]:
    views = task_ledger.get("views") if isinstance(task_ledger.get("views"), Mapping) else {}
    counts = task_ledger.get("counts") if isinstance(task_ledger.get("counts"), Mapping) else {}
    capture_count = int(counts.get("capture_count") or 0)
    execution_menu_count = int(counts.get("execution_menu_count") or 0)
    return {
        "authority": "projection_only",
        "source_authority": str(task_ledger_events.EVENTS_REL),
        "event_count": counts.get("event_count"),
        "work_item_count": counts.get("work_item_count"),
        "capture_count": counts.get("capture_count"),
        "total_capture_count": counts.get("total_capture_count"),
        "raw_capture_inbox_count": counts.get("raw_capture_inbox_count"),
        "active_capture_inbox_count": counts.get("active_capture_inbox_count"),
        "closed_capture_count": counts.get("closed_capture_count"),
        "sign_off_count": counts.get("sign_off_count"),
        "incomplete_count": counts.get("incomplete_count"),
        "blocked_count": counts.get("blocked_count"),
        "ready_by_rank_count": (views.get("ready_by_rank") or {}).get("count") if isinstance(views.get("ready_by_rank"), Mapping) else None,
        "schedulable_by_rank_count": (views.get("schedulable_by_rank") or {}).get("count") if isinstance(views.get("schedulable_by_rank"), Mapping) else None,
        "execution_menu_schedulable_count": (
            (views.get("execution_menu_schedulable") or {}).get("count")
            if isinstance(views.get("execution_menu_schedulable"), Mapping)
            else None
        ),
        "dependency_blocked_count": (views.get("dependency_blocked") or {}).get("count") if isinstance(views.get("dependency_blocked"), Mapping) else None,
        "dependency_anomaly_count": (views.get("dependency_anomalies") or {}).get("count") if isinstance(views.get("dependency_anomalies"), Mapping) else None,
        "capture_inbox_count": counts.get("capture_count"),
        "capture_inbox_count_semantics": "total_capture_log_including_closed_shaped_and_raw_rows",
        "missing_satisfaction_contract_count": (
            (views.get("missing_satisfaction_contract") or {}).get("count")
            if isinstance(views.get("missing_satisfaction_contract"), Mapping)
            else None
        ),
        "missing_integration_contract_count": (
            (views.get("missing_integration_contract") or {}).get("count")
            if isinstance(views.get("missing_integration_contract"), Mapping)
            else None
        ),
        "stale_review_count": (views.get("stale_review") or {}).get("count") if isinstance(views.get("stale_review"), Mapping) else None,
        "prompt_trace_unlinked_count": (
            (views.get("prompt_trace_unlinked") or {}).get("count")
            if isinstance(views.get("prompt_trace_unlinked"), Mapping)
            else None
        ),
        "work_ledger_unlinked_count": (
            (views.get("work_ledger_unlinked") or {}).get("count")
            if isinstance(views.get("work_ledger_unlinked"), Mapping)
            else None
        ),
        "top_schedulable_workitems": (
            _view_items(views, "execution_menu_schedulable")
            or _view_items(views, "schedulable_by_rank")
        )[:5],
        "top_ready_workitems": (
            _view_items(views, "execution_menu_schedulable")
            or _view_items(views, "schedulable_by_rank")
            or _view_items(views, "execution_menu")
            or _view_items(views, "ready_by_rank")
        )[:5],
        "top_blocked_workitems": _view_items(views, "blocked")[:5],
        "newest_captures_sample": _view_items(views, "capture_inbox")[:5],
        "unranked_capture_count": max(capture_count - execution_menu_count, 0),
        "recommended_next_workitems": list(backlog_health.get("recommended_next_workitems") or [])[:7],
        "note": "capture inbox is append-only raw material, not the execution queue; choose active work from execution_menu_schedulable/schedulable_by_rank with legacy execution_menu/ready fallback",
        "source_projection_paths": {
            name: (view.get("path") if isinstance(view, Mapping) else None)
            for name, view in views.items()
            if name
            in {
                "capture_inbox",
                "capture_triage",
                "execution_menu",
                "execution_menu_schedulable",
                "ready_by_rank",
                "schedulable_by_rank",
                "dependency_blocked",
                "dependency_anomalies",
                "blocked",
                "missing_satisfaction_contract",
                "missing_integration_contract",
                "stale_review",
                "prompt_trace_unlinked",
                "work_ledger_unlinked",
            }
        },
        "next_legal_task_ledger_commands": [
            "./repo-python tools/meta/factory/task_ledger_apply.py shape --subject-id <cap_id> --payload-json <json>",
            "./repo-python tools/meta/factory/task_ledger_apply.py promote --subject-id <cap_id> --payload-json <json>",
            "./repo-python tools/meta/factory/task_ledger_apply.py block --subject-id <cap_id> --payload-json <json>",
            "./repo-python tools/meta/factory/task_ledger_apply.py retire --subject-id <cap_id> --payload-json <json>",
            "./repo-python tools/meta/factory/task_ledger_apply.py closeout-slice --work-item-id <cap_id> ...",
        ],
    }


def _active_mission_row(repo_root: Path, *, phase_id: str | None, subphase_id: str | None) -> dict[str, Any]:
    board = _safe_read_json(repo_root / "state/mission_blackboard/board.json")
    rows = board.get("rows") if isinstance(board.get("rows"), list) else []
    active_row_id = str(board.get("active_row_id") or "").strip()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if active_row_id and str(row.get("row_id") or "") == active_row_id:
            return dict(row)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if phase_id and str(row.get("phase_id") or "") != phase_id:
            continue
        if subphase_id and str(row.get("wave_id") or "") != subphase_id:
            continue
        return dict(row)
    return {}


def _top_recommended_workitem_ids(backlog_health: Mapping[str, Any], *, limit: int = 7) -> list[str]:
    ids: list[str] = []
    for item in backlog_health.get("recommended_next_workitems") or []:
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("id") or "").strip()
        if item_id:
            ids.append(item_id)
    return ids[:limit]


def _compact_live_workitem_card(item: Mapping[str, Any]) -> dict[str, Any]:
    dependency_status = item.get("dependency_status") if isinstance(item.get("dependency_status"), Mapping) else {}
    pressure = item.get("pressure") if isinstance(item.get("pressure"), Mapping) else {}
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "state": item.get("state"),
        "rank": item.get("rank"),
        "work_item_type": item.get("work_item_type"),
        "required_next_event": item.get("required_next_event"),
        "why_this_next": list(item.get("why_this_next") or [])[:4],
        "dependency_status": {
            "schedulable": dependency_status.get("schedulable"),
            "hard_dep_count": dependency_status.get("hard_dep_count"),
            "unsatisfied_dep_count": len(dependency_status.get("unsatisfied_dep_ids") or []),
            "downstream_unlock_count": len(dependency_status.get("downstream_unlock_ids") or []),
        },
        "pressure": {
            "score": pressure.get("score"),
            "waiting": pressure.get("waiting"),
            "downstream_unsatisfied": pressure.get("downstream_unsatisfied"),
        },
    }


def _compact_live_workitem_cards(items: Sequence[Any], *, limit: int) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        cards.append(_compact_live_workitem_card(item))
        if len(cards) >= limit:
            break
    return cards


def _subphase_runtime_attention_packet(
    repo_root: Path,
    *,
    phase: Mapping[str, Any],
    phase_freshness: Mapping[str, Any],
    backlog_health: Mapping[str, Any],
    concurrency_attention: Mapping[str, Any],
    strict_json_attention: Mapping[str, Any],
) -> dict[str, Any]:
    phase_row = phase.get("phase") if isinstance(phase.get("phase"), Mapping) else {}
    subphase = phase.get("subphase") if isinstance(phase.get("subphase"), Mapping) else {}
    phase_id = str(phase_row.get("phase_id") or phase.get("phase_id") or "").strip() or None
    subphase_id = str(subphase.get("subphase_id") or "").strip() or None
    active_row = _active_mission_row(repo_root, phase_id=phase_id, subphase_id=subphase_id)
    focus_conflict_count = int(phase_freshness.get("focus_conflict_count") or 0)
    freshness_status = str(phase_freshness.get("freshness_status") or "unknown")
    safe_parallelism_status = str(concurrency_attention.get("safe_parallelism_status") or "unknown")
    strict_status = str(strict_json_attention.get("status") or "unknown")
    execution_menu_ids = _top_recommended_workitem_ids(backlog_health)

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if safe_parallelism_status == "blocked":
        blockers.append(
            {
                "kind": "claim_collision",
                "reason": "Work Ledger reports a requested target or active claim collision.",
            }
        )
    if strict_status not in {"ok", ""}:
        warnings.append(
            {
                "kind": "strict_json_artifact_attention",
                "reason": f"Strict JSON artifact attention status is {strict_status}.",
            }
        )
    if freshness_status in {"conflicting", "stale", "unknown"}:
        warnings.append(
            {
                "kind": "phase_freshness",
                "status": freshness_status,
                "reason": "Phase/subphase identity is not enough; use evidence and owner tooling before editing phase files.",
            }
        )
    if focus_conflict_count:
        warnings.append(
            {
                "kind": "focus_conflict",
                "count": focus_conflict_count,
                "reason": "Another phase surface still claims active/default focus.",
            }
        )
    if safe_parallelism_status in {"watch", "unknown"}:
        warnings.append(
            {
                "kind": "parallelism_watch",
                "status": safe_parallelism_status,
                "reason": "Claim exact paths before mutation; stale/orphan sessions are attention, not global blockers.",
            }
        )

    if blockers:
        runtime_status = "blocked"
    elif warnings:
        runtime_status = "watch"
    else:
        runtime_status = "ready"

    active_rows = []
    board = _safe_read_json(repo_root / "state/mission_blackboard/board.json")
    for row in board.get("rows") if isinstance(board.get("rows"), list) else []:
        if isinstance(row, Mapping) and str(row.get("status") or "") == "active":
            active_rows.append(row)
    if len(active_rows) > 1:
        subphase_allocation_status = "multi_active_projected"
    elif len(active_rows) == 1:
        subphase_allocation_status = "single_active"
    else:
        subphase_allocation_status = "unknown"

    selected_workitem = execution_menu_ids[0] if execution_menu_ids else "<work_item_id>"
    return {
        "authority": "projection_only",
        "view_profile": "legacy_subphase_runtime_attention_v0",
        "successor_projection": "phase_runtime_context",
        "context_role": "phase_wave_context_only_not_liveness_authority",
        "liveness_authority": False,
        "source_authority": [
            str(task_ledger_events.EVENTS_REL),
            "state/work_ledger/runtime_status.json",
            "kernel.py --phase",
            "state/mission_blackboard/board.json",
        ],
        "runtime_status": runtime_status,
        "phase_id": phase_id,
        "requested_phase": phase.get("requested_phase"),
        "subphase_id": subphase_id or active_row.get("wave_id"),
        "active_wave_id": subphase_id or active_row.get("wave_id"),
        "active_wave_objective": subphase.get("objective") or active_row.get("focus_summary"),
        "phase_freshness_status": freshness_status,
        "focus_conflict_count": focus_conflict_count,
        "phase_staleness_reason": phase_freshness.get("phase_staleness_reason") or [],
        "phase_source_paths": phase_freshness.get("evidence_paths") or [],
        "mission_blackboard": {
            "path": "state/mission_blackboard/board.json",
            "active_phase_id": board.get("active_phase_id"),
            "active_row_id": board.get("active_row_id"),
            "active_row_wave_id": active_row.get("wave_id"),
            "active_row_status": active_row.get("status"),
            "updated_at": active_row.get("updated_at") or board.get("updated_at"),
        },
        "subphase_allocation_status": subphase_allocation_status,
        "execution_menu_ids": execution_menu_ids,
        "selected_lane_hint": {
            "work_item_id": selected_workitem,
            "reason": "Use the first execution-menu WorkItem unless live blockers or operator direction select a different bounded proof.",
        },
        "concurrency_lane_candidates": [
            {
                "work_item_id": work_item_id,
                "lane": f"{phase_id or 'phase_unknown'}::{subphase_id or 'subphase_unknown'}::{work_item_id}",
                "claim_rule": "safe if target paths do not overlap active Work Ledger claims",
            }
            for work_item_id in execution_menu_ids[:5]
        ],
        "active_claim_count": concurrency_attention.get("active_claims"),
        "claim_collision_count": concurrency_attention.get("claim_collisions"),
        "unknown_scope_active_session_count": concurrency_attention.get("unknown_scope_active_sessions"),
        "safe_parallelism_status": safe_parallelism_status,
        "blocking_claims": concurrency_attention.get("requested_target_claim_collisions") or [],
        "advisory_sessions": {
            "active_sessions": concurrency_attention.get("active_sessions"),
            "effective_active_sessions": concurrency_attention.get("effective_active_sessions"),
            "stale_sessions": concurrency_attention.get("stale_sessions"),
            "orphaned_active_sessions": concurrency_attention.get("orphaned_active_sessions"),
            "unknown_scope_active_sessions": concurrency_attention.get("unknown_scope_active_sessions"),
        },
        "blockers": blockers,
        "warnings": warnings,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "owner_tool_commands": [
            "./repo-python kernel.py --phase <phase>",
            "./repo-python kernel.py --phase-step <phase>",
            "./repo-python tools/meta/factory/task_ledger_project.py rebuild --check",
            "./repo-python tools/meta/factory/work_ledger.py session-status --overview --limit 20",
        ],
        "recommended_claim_shape": {
            "command": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                f"--phase-id {phase_id or '<phase>'} --td-id {selected_workitem} "
                "--path <target-path> --require-exclusive"
            ),
            "rule": "claim exact authority/projection/code paths for the selected WorkItem before mutation",
        },
        "recommended_next_legal_actions": [
            "choose implementation work from execution_menu_schedulable ids first, then schedulable_by_rank, unless a blocker selects a different WorkItem",
            "claim target paths through Work Ledger before mutation",
            "treat stale/orphan sessions as watch-level unless they collide with target paths",
            "use phase owner tooling for phase/subphase files; append a Task Ledger capture for unresolved phase ambiguity",
        ],
        "authority_boundary": {
            "task_ledger": "Task Ledger WorkItem/cap/task/signoff authority",
            "work_ledger": "execution session, claim, and closeout authority",
            "kernel_phase": "read model over phase-family/seed/runtime surfaces",
            "mission_blackboard": "projection/readiness surface",
            "phase_runtime_context": "preferred projection name for phase/wave context",
            "subphase_runtime_attention": "legacy compatibility alias; projection only",
        },
        "mutation_rule": "read-only coordination surface; do not create scheduler state here",
    }


def _phase_runtime_context_packet(subphase_runtime_attention: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": "projection_only",
        "view_profile": "phase_runtime_context_v0",
        "legacy_projection_id": "subphase_runtime_attention",
        "context_role": "phase_wave_context_only_not_liveness_authority",
        "liveness_authority": False,
        "source_authority": subphase_runtime_attention.get("source_authority") or [],
        "runtime_status": subphase_runtime_attention.get("runtime_status"),
        "phase_id": subphase_runtime_attention.get("phase_id"),
        "requested_phase": subphase_runtime_attention.get("requested_phase"),
        "wave_id": subphase_runtime_attention.get("active_wave_id")
        or subphase_runtime_attention.get("subphase_id"),
        "phase_freshness_status": subphase_runtime_attention.get("phase_freshness_status"),
        "focus_conflict_count": subphase_runtime_attention.get("focus_conflict_count"),
        "phase_staleness_reason": subphase_runtime_attention.get("phase_staleness_reason") or [],
        "mission_blackboard": subphase_runtime_attention.get("mission_blackboard") or {},
        "execution_menu_ids": subphase_runtime_attention.get("execution_menu_ids") or [],
        "selected_workitem_hint": subphase_runtime_attention.get("selected_lane_hint") or {},
        "safe_parallelism_status": subphase_runtime_attention.get("safe_parallelism_status"),
        "active_claim_count": subphase_runtime_attention.get("active_claim_count"),
        "claim_collision_count": subphase_runtime_attention.get("claim_collision_count"),
        "advisory_sessions": subphase_runtime_attention.get("advisory_sessions") or {},
        "blockers": subphase_runtime_attention.get("blockers") or [],
        "warnings": subphase_runtime_attention.get("warnings") or [],
        "blocker_count": subphase_runtime_attention.get("blocker_count"),
        "warning_count": subphase_runtime_attention.get("warning_count"),
        "preferred_authority_order": [
            "Task Ledger WorkItems",
            "Work Ledger claims",
            "phase runtime context",
        ],
        "recommended_next_legal_actions": [
            "choose implementation work from live WorkItem projections before phase/wave files",
            "claim target paths through Work Ledger before mutation",
            "use phase owner tooling only for phase-context repair",
        ],
        "compatibility_note": (
            "subphase_runtime_attention remains for older consumers; new routing should read "
            "phase_runtime_context and treat it as context, not liveness authority."
        ),
        "mutation_rule": "read-only context projection; mutate work through Task Ledger and Work Ledger owner tools",
    }


def _live_work_runtime_attention_packet(
    *,
    task_ledger_source: str,
    backlog_health: Mapping[str, Any],
    backlog_attention: Mapping[str, Any],
    concurrency_attention: Mapping[str, Any],
    phase_freshness: Mapping[str, Any],
    subphase_runtime_attention: Mapping[str, Any],
) -> dict[str, Any]:
    raw_recommended_workitems = [
        item
        for item in backlog_attention.get("recommended_next_workitems")
        or backlog_health.get("recommended_next_workitems")
        or []
        if isinstance(item, Mapping)
    ][:7]
    recommended_ids = [
        str(item.get("id") or "").strip()
        for item in raw_recommended_workitems
        if str(item.get("id") or "").strip()
    ]
    recommended_workitems = _compact_live_workitem_cards(raw_recommended_workitems, limit=7)
    top_schedulable = _compact_live_workitem_cards(
        list(backlog_attention.get("top_schedulable_workitems") or []),
        limit=5,
    )
    top_ready = _compact_live_workitem_cards(
        list(backlog_attention.get("top_ready_workitems") or []),
        limit=5,
    )
    safe_parallelism_status = str(concurrency_attention.get("safe_parallelism_status") or "unknown")
    runtime_status = str(subphase_runtime_attention.get("runtime_status") or "unknown")
    phase_status = str(phase_freshness.get("freshness_status") or "unknown")
    if safe_parallelism_status == "blocked" or runtime_status == "blocked":
        selection_status = "blocked"
    elif recommended_ids:
        selection_status = "ready_with_watch" if safe_parallelism_status in {"watch", "unknown"} else "ready"
    else:
        selection_status = "needs_workitem_selection"
    return {
        "authority": "projection_only",
        "source_authority": [
            str(task_ledger_events.EVENTS_REL),
            "state/task_ledger/views/execution_menu_schedulable.json",
            "state/task_ledger/views/schedulable_by_rank.json",
            "state/work_ledger/runtime_status.json",
        ],
        "task_ledger_source": task_ledger_source,
        "authority_order": [
            "Task Ledger WorkItems",
            "Work Ledger claims",
            "phase runtime context",
        ],
        "selection_status": selection_status,
        "runtime_status": runtime_status,
        "safe_parallelism_status": safe_parallelism_status,
        "phase_freshness_status": phase_status,
        "phase_context_role": "context_only_not_liveness_authority",
        "subphase_context_role": "context_only_not_liveness_authority",
        "recommended_workitem_ids": recommended_ids,
        "recommended_workitems": recommended_workitems,
        "recommended_workitems_projection": {
            "row_shape": "compact_live_workitem_card",
            "omitted": [
                "source_event_ids",
                "source_event_types",
                "dependency edge lists",
                "downstream unlock detail",
            ],
            "full_detail_sources": [
                "state/task_ledger/views/execution_menu_schedulable.json",
                "state/task_ledger/views/schedulable_by_rank.json",
            ],
        },
        "top_schedulable_workitems": top_schedulable,
        "top_ready_workitems": top_ready,
        "blocked_workitem_count": backlog_attention.get("blocked_count"),
        "dependency_blocked_count": backlog_attention.get("dependency_blocked_count"),
        "live_claim_counts": {
            "active_claims": concurrency_attention.get("active_claims"),
            "effective_active_sessions": concurrency_attention.get("effective_active_sessions"),
            "orphaned_active_sessions": concurrency_attention.get("orphaned_active_sessions"),
            "claim_collisions": concurrency_attention.get("claim_collisions"),
        },
        "phase_context": {
            "phase_freshness_status": phase_status,
            "focus_conflict_count": phase_freshness.get("focus_conflict_count"),
            "active_wave_id": subphase_runtime_attention.get("active_wave_id")
            or subphase_runtime_attention.get("subphase_id"),
            "context_projection": "phase_runtime_context",
            "legacy_projection": "subphase_runtime_attention",
        },
        "next_legal_actions": [
            "choose from execution_menu_schedulable/schedulable_by_rank before phase or wave files",
            "inspect Work Ledger claims and claim exact target paths before mutation",
            "use phase owner tooling only for phase-context repair",
        ],
        "drilldown_commands": {
            "task_ledger_cluster": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "work_ledger_claims": WORK_LEDGER_SEED_SPEED_COMMAND,
            "phase_runtime_context": "./repo-python kernel.py --workitem-entrypoint <phase>",
            "phase_context": "./repo-python kernel.py --phase <phase>",
        },
        "mutation_rule": "read-only live-work selector; mutate work through Task Ledger events and execution state through Work Ledger claims",
    }


def _applicable_mechanisms_packet(
    repo_root: Path,
    *,
    phase_freshness: Mapping[str, Any],
    concurrency_attention: Mapping[str, Any],
    strict_json_attention: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = [
        {
            "mechanism_id": "forward_integration_dirty_surface_classification",
            "source_path": "codex/standards/std_forward_integration_policy.json",
            "implementation_path": "system/lib/forward_integration_policy.py",
            "why_applicable_now": "dirty tree is present and target-aware mutation policy is required before edits",
            "authority_surface": "codex/standards/std_forward_integration_policy.json",
            "mutation_surface": "target paths only",
            "projection_surface": "workitem_runtime_entrypoint_v1.forward_integration",
            "owner_tool": "./repo-python kernel.py --workitem-entrypoint <phase>",
            "validation_commands": ["./repo-pytest system/server/tests/test_forward_integration_policy.py"],
            "concurrency_policy": "classify dirty unrelated surfaces as warnings; block destructive overwrite risk",
            "closeout_policy": "capture residuals and do not restore/clean unrelated dirt",
            "related_standard": "codex/standards/std_forward_integration_policy.json",
            "applicability": "required",
            "implementation_status": "code_grounded",
        },
        {
            "mechanism_id": "work_ledger_claim_closeout_validation",
            "source_path": "codex/standards/std_work_ledger.json",
            "implementation_path": "tools/meta/factory/work_ledger.py",
            "why_applicable_now": "multiple active/stale sessions exist and path claims define safe Type A parallelism",
            "authority_surface": "codex/ledger/*/work_ledger.jsonl",
            "mutation_surface": "Work Ledger CLI append/release/finalize commands",
            "projection_surface": "state/work_ledger/runtime_status.json",
            "owner_tool": "./repo-python tools/meta/factory/work_ledger.py",
            "validation_commands": ["./repo-pytest system/server/tests/test_work_ledger_core.py"],
            "concurrency_policy": str(concurrency_attention.get("safe_parallelism_status") or "unknown"),
            "closeout_policy": "Task Ledger signoff/residual before Work Ledger closeout; finalize last",
            "related_standard": "codex/standards/std_work_ledger.json",
            "applicability": "required",
            "implementation_status": "code_grounded",
        },
        {
            "mechanism_id": "strict_json_artifact_validation",
            "source_path": "codex/standards/std_strict_json_artifact.json",
            "implementation_path": "system/lib/strict_json.py",
            "why_applicable_now": "authority and projection JSON/JSONL surfaces are touched or validated during closeout",
            "authority_surface": "strict JSON standard plus ledger event logs",
            "mutation_surface": "owning ledger/projector tools",
            "projection_surface": "workitem_runtime_entrypoint_v1.strict_json_artifact_attention",
            "owner_tool": "./repo-python tools/meta/factory/task_ledger_apply.py validate",
            "validation_commands": [
                "./repo-python tools/meta/factory/task_ledger_apply.py validate",
                "./repo-python tools/meta/observability/prompt_ledger.py validate",
            ],
            "concurrency_policy": "strict validation is local to touched authority/projection surfaces",
            "closeout_policy": str(strict_json_attention.get("status") or "unknown"),
            "related_standard": "codex/standards/std_strict_json_artifact.json",
            "applicability": "required",
            "implementation_status": "code_grounded",
        },
        {
            "mechanism_id": "phase_runtime_context",
            "source_path": "system/lib/workitem_runtime_entrypoint.py",
            "implementation_path": "system/lib/workitem_runtime_entrypoint.py",
            "why_applicable_now": "phase freshness is not fully current and Type A needs a lane-level read model before mutation",
            "authority_surface": "Task Ledger + Work Ledger + kernel phase packet",
            "mutation_surface": "none in this read model",
            "projection_surface": "workitem_runtime_entrypoint_v1.phase_runtime_context",
            "owner_tool": "./repo-python kernel.py --workitem-entrypoint <phase>",
            "validation_commands": ["./repo-pytest system/server/tests/test_workitem_runtime_entrypoint.py"],
            "concurrency_policy": str(concurrency_attention.get("safe_parallelism_status") or "unknown"),
            "closeout_policy": "capture unresolved phase ambiguity through Task Ledger",
            "related_standard": "candidate: codex/standards/std_phase_subphase_runtime.json",
            "applicability": "recommended",
            "implementation_status": "code_grounded",
        },
        {
            "mechanism_id": "subphase_runtime_attention",
            "source_path": "system/lib/workitem_runtime_entrypoint.py",
            "implementation_path": "system/lib/workitem_runtime_entrypoint.py",
            "why_applicable_now": "legacy consumer compatibility only; prefer phase_runtime_context for new WorkItem-first routing",
            "authority_surface": "Task Ledger + Work Ledger + kernel phase packet",
            "mutation_surface": "none in this read model",
            "projection_surface": "workitem_runtime_entrypoint_v1.subphase_runtime_attention",
            "owner_tool": "./repo-python kernel.py --workitem-entrypoint <phase>",
            "validation_commands": ["./repo-pytest system/server/tests/test_workitem_runtime_entrypoint.py"],
            "concurrency_policy": str(concurrency_attention.get("safe_parallelism_status") or "unknown"),
            "closeout_policy": "capture unresolved phase ambiguity through Task Ledger",
            "related_standard": "candidate: codex/standards/std_phase_subphase_runtime.json",
            "applicability": "compatibility",
            "implementation_status": "legacy_alias",
        },
    ]
    if str(phase_freshness.get("freshness_status") or "") in {"conflicting", "stale", "unknown"}:
        rows.append(
            {
                "mechanism_id": "kernel_phase_freshness_reconciliation",
                "source_path": "system/lib/workitem_runtime_entrypoint.py",
                "implementation_path": "system/lib/kernel/commands/navigate.py",
                "why_applicable_now": "phase freshness status requires owner-tool reconciliation or an absence/blocker receipt",
                "authority_surface": "phase-family seed/runtime surfaces",
                "mutation_surface": "phase owner tooling only",
                "projection_surface": "workitem_runtime_entrypoint_v1.phase_freshness",
                "owner_tool": "./repo-python kernel.py --phase-step <phase>",
                "validation_commands": ["./repo-python kernel.py --phase <phase>"],
                "concurrency_policy": "advisory until target phase files are claimed",
                "closeout_policy": "capture phase ambiguity if not repaired in this slice",
                "related_standard": "candidate: codex/standards/std_phase_subphase_runtime.json",
                "applicability": "recommended",
                "implementation_status": "code_grounded",
            }
        )
    for row in rows:
        source_path = str(row.get("source_path") or "")
        implementation_path = str(row.get("implementation_path") or "")
        row["source_exists"] = bool(source_path and (repo_root / source_path).exists())
        row["implementation_exists"] = bool(implementation_path and (repo_root / implementation_path).exists())
    return rows


def _annex_concurrency_pattern_candidates(repo_root: Path) -> list[dict[str, Any]]:
    candidates = [
        {
            "pattern_id": "annex_nano_claude_background_task_polling",
            "annex_path": "annexes/nano-claude-code/annex_notes.json",
            "source_refs": ["annexes/nano-claude-code/annex_notes.json::n010", "annexes/nano-claude-code/repo/multi_agent/subagent.py"],
            "problem_solved": "background subagent status becomes visible at the next prompt/render boundary",
            "repo_mapping": "poll Work Ledger at Type A wake and expose session/claim pressure before mutation",
            "what_not_to_import": "do not copy ThreadPoolExecutor or worktree spawning into the WorkItem spine",
            "readiness": "implemented_now_as_entrypoint_read_model",
        },
        {
            "pattern_id": "annex_agent_orchestrator_file_lock_stale_timeout",
            "annex_path": "annexes/agent-orchestrator/repo/packages/core/src/file-lock.ts",
            "source_refs": ["annexes/agent-orchestrator/repo/packages/core/src/file-lock.ts"],
            "problem_solved": "lock acquisition uses bounded wait, stale detection, and cleanup",
            "repo_mapping": "keep Work Ledger claims as authority; surface stale/collision pressure as decision status",
            "what_not_to_import": "do not replace Work Ledger claims with ad hoc file locks",
            "readiness": "capture_only",
        },
        {
            "pattern_id": "annex_agent_flow_dual_session_visibility",
            "annex_path": "annexes/agent-flow/annex_notes.json",
            "source_refs": ["annexes/agent-flow/annex_notes.json::n001", "annexes/agent-flow/annex_notes.json::n003", "annexes/agent-flow/annex_notes.json::n004"],
            "problem_solved": "concurrent Claude/Codex sessions are visible from authoritative event streams",
            "repo_mapping": "future Station/HUD can render this packet; kernel entrypoint owns only read-model affordance",
            "what_not_to_import": "do not wedge frontend visualization in this slice",
            "readiness": "capture_only",
        },
    ]
    for candidate in candidates:
        candidate["source_exists"] = all((repo_root / ref.split("::", 1)[0]).exists() for ref in candidate["source_refs"])
    return candidates


def _concurrency_attention_packet(
    work_ledger: Mapping[str, Any],
    *,
    claim_collisions: Sequence[Mapping[str, Any]],
    target_paths: Sequence[str],
    require_exclusive: bool,
    repo_root: Path,
) -> dict[str, Any]:
    counts = work_ledger.get("counts") if isinstance(work_ledger.get("counts"), Mapping) else {}
    contention = work_ledger.get("contention") if isinstance(work_ledger.get("contention"), Mapping) else {}
    stale = work_ledger.get("stale_sessions") if isinstance(work_ledger.get("stale_sessions"), Mapping) else {}
    active_claims = work_ledger.get("active_claims") if isinstance(work_ledger.get("active_claims"), list) else []
    unknown_scope = contention.get("unknown_scope_active_sessions") if isinstance(contention.get("unknown_scope_active_sessions"), list) else []
    orphaned = contention.get("orphaned_active_sessions") if isinstance(contention.get("orphaned_active_sessions"), list) else []
    unclaimed_touched = contention.get("unclaimed_touched_sessions") if isinstance(contention.get("unclaimed_touched_sessions"), list) else []
    reasons: list[str] = []
    if not work_ledger.get("ok", True):
        status = "unknown"
        reasons.append(str(work_ledger.get("error") or "Work Ledger overview unavailable"))
    elif claim_collisions or int(counts.get("claim_collisions") or 0) > 0:
        status = "blocked"
        reasons.append("claim collision exists for requested target path or active Work Ledger scope")
    elif unknown_scope or orphaned or int(counts.get("stale_sessions") or 0) > 0:
        status = "watch"
        reasons.append("active/stale session pressure exists; claim target paths before mutation")
    elif active_claims or int(counts.get("effective_active_sessions") or 0) > 1:
        status = "watch"
        reasons.append("parallel work is present but no target collision was detected")
    else:
        status = "safe"
        reasons.append("no active claims, claim collisions, or unresolved session pressure reported")

    recommended_actions = ["claim target paths before mutation"]
    if claim_collisions:
        recommended_actions.append("do not mutate contested paths; route around or wait for claim release")
    if unknown_scope:
        recommended_actions.append("inspect unknown-scope active sessions before assuming safe parallelism")
    if orphaned or int(counts.get("stale_sessions") or 0) > 0:
        recommended_actions.append("run Work Ledger session-status/session-sweep or capture stale-session residuals")
    if not target_paths:
        recommended_actions.append("supply --workitem-path/--workitem-write-profile to get target-aware collision checks")

    return {
        "authority": "projection_only",
        "source_authority": "state/work_ledger/runtime_status.json",
        "safe_parallelism_status": status,
        "why_status": reasons,
        "active_sessions": counts.get("active_sessions"),
        "effective_active_sessions": counts.get("effective_active_sessions"),
        "active_claims": counts.get("active_claims"),
        "claim_collisions": counts.get("claim_collisions"),
        "stale_sessions": counts.get("stale_sessions"),
        "forward_repaired_stale_sessions": stale.get("forward_repaired_count"),
        "unresolved_stale_sessions": stale.get("unresolved_count"),
        "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
        "unknown_scope_active_sessions": len(unknown_scope),
        "unclaimed_touched_sessions": counts.get("unclaimed_touched_sessions"),
        "requested_target_claim_collisions": list(claim_collisions),
        "path_claim_collisions": list(claim_collisions),
        "workitem_claim_collisions": [],
        "workitem_claim_collision_absence_receipt": "Work Ledger models session/path/td claims; WorkItem-id claim collision is not a separate authority surface yet.",
        "target_paths_checked": list(target_paths),
        "require_exclusive": bool(require_exclusive),
        "active_claims_sample": active_claims[:8],
        "unknown_scope_active_sessions_sample": unknown_scope[:5],
        "orphaned_active_sessions_sample": orphaned[:5],
        "unclaimed_touched_sessions_sample": unclaimed_touched[:5],
        "recommended_actions": recommended_actions,
        "annex_pattern_candidates": _annex_concurrency_pattern_candidates(repo_root),
        "mutation_rule": "read-only decision surface; mutate execution state through Work Ledger claims/closeout and work state through Task Ledger events",
    }


def build_workitem_runtime_entrypoint(
    repo_root: Path,
    *,
    phase_token: str | None = None,
    target_paths: Sequence[str] | None = None,
    write_profiles: Sequence[str] | None = None,
    session_id: str | None = None,
    require_exclusive: bool = False,
    dirty_paths: Sequence[str] | None = None,
    attempted_action: str | None = None,
    limit: int = 6,
    task_ledger_source: str = TASK_LEDGER_SOURCE_AUTO,
) -> dict[str, Any]:
    root = repo_root.resolve()
    profile_rows, profile_paths, profile_warnings = _expand_write_profiles(write_profiles)
    explicit_targets = [
        normalize_repo_path(root, path)
        for path in (target_paths or [])
        if str(path or "").strip()
    ]
    target_set = sorted({*explicit_targets, *[normalize_repo_path(root, path) for path in profile_paths]})
    requested_task_ledger_source = str(task_ledger_source or TASK_LEDGER_SOURCE_AUTO).strip() or TASK_LEDGER_SOURCE_AUTO
    source_warnings: list[str] = []
    if requested_task_ledger_source not in {
        TASK_LEDGER_SOURCE_AUTO,
        TASK_LEDGER_SOURCE_AUTHORITY,
        TASK_LEDGER_SOURCE_MATERIALIZED,
    }:
        source_warnings.append(f"unknown task ledger source: {requested_task_ledger_source}")
        requested_task_ledger_source = TASK_LEDGER_SOURCE_AUTO
    target_aware_validation = bool(target_set or require_exclusive or attempted_action)
    selected_task_ledger_source = (
        TASK_LEDGER_SOURCE_AUTHORITY
        if requested_task_ledger_source == TASK_LEDGER_SOURCE_AUTO and target_aware_validation
        else TASK_LEDGER_SOURCE_MATERIALIZED
        if requested_task_ledger_source == TASK_LEDGER_SOURCE_AUTO
        else requested_task_ledger_source
    )

    work_ledger = _work_ledger_packet(root, limit=limit)
    active_claims = work_ledger.get("active_claims") if isinstance(work_ledger.get("active_claims"), list) else []
    claim_collisions = _claim_collisions_for_targets(
        [claim for claim in active_claims if isinstance(claim, Mapping)],
        target_set,
        session_id=session_id,
    )
    forward_policy = build_forward_integration_policy(
        root,
        target_paths=target_set,
        owner_tool_paths=profile_paths,
        dirty_paths=dirty_paths,
        attempted_action=attempted_action,
        claim_collisions=claim_collisions,
        require_exclusive=require_exclusive,
    )
    if selected_task_ledger_source == TASK_LEDGER_SOURCE_MATERIALIZED:
        task_ledger, task_blockers = _task_ledger_materialized_projection_packet(root)
    else:
        task_ledger, task_blockers = _task_ledger_packet(root)
    phase = _phase_packet(root, phase_token)
    phase_freshness = _phase_freshness_packet(root, phase=phase)
    prompt_trace = _prompt_trace_packet(root)
    provider = _provider_packet(root)
    uppropagation = _uppropagation_intake_packet(root)
    backlog_health = _workitem_backlog_health_packet(task_ledger, prompt_trace=prompt_trace)
    backlog_attention = _workitem_backlog_attention_packet(task_ledger, backlog_health=backlog_health)
    concurrency_attention = _concurrency_attention_packet(
        work_ledger,
        claim_collisions=[item for item in claim_collisions if isinstance(item, Mapping)],
        target_paths=target_set,
        require_exclusive=require_exclusive,
        repo_root=root,
    )
    strict_json_attention = _strict_json_artifact_attention_packet(
        task_ledger,
        repo_root=root,
        target_paths=target_set,
    )
    subphase_runtime_attention = _subphase_runtime_attention_packet(
        root,
        phase=phase,
        phase_freshness=phase_freshness,
        backlog_health=backlog_health,
        concurrency_attention=concurrency_attention,
        strict_json_attention=strict_json_attention,
    )
    phase_runtime_context = _phase_runtime_context_packet(subphase_runtime_attention)
    live_work_runtime_attention = _live_work_runtime_attention_packet(
        task_ledger_source=selected_task_ledger_source,
        backlog_health=backlog_health,
        backlog_attention=backlog_attention,
        concurrency_attention=concurrency_attention,
        phase_freshness=phase_freshness,
        subphase_runtime_attention=subphase_runtime_attention,
    )
    applicable_mechanisms = _applicable_mechanisms_packet(
        root,
        phase_freshness=phase_freshness,
        concurrency_attention=concurrency_attention,
        strict_json_attention=strict_json_attention,
    )

    blockers = list(forward_policy.get("blockers") or []) + task_blockers
    warnings = list(forward_policy.get("warnings") or []) + profile_warnings + source_warnings
    safe_to_continue = bool(forward_policy.get("safe_to_continue")) and not task_blockers
    commit_readiness = _commit_readiness(
        root,
        forward_policy=forward_policy,
        target_paths=target_set,
        blockers=[item for item in blockers if isinstance(item, Mapping)],
        safe_to_continue=safe_to_continue,
        dirty_paths=dirty_paths,
    )

    return {
        "kind": "kernel.workitem_runtime_entrypoint",
        "schema_version": SCHEMA_VERSION,
        "mode": "forward_integration",
        "dirty_tree_allowed": True,
        "destructive_overwrite_allowed": False,
        "destructive_override_required": any(
            str(item.get("mode") or "") == "destructive_override_required" for item in blockers
        ),
        "safe_to_continue": safe_to_continue,
        "blocked_only_by": [str(item.get("kind") or "unknown_blocker") for item in blockers],
        "blockers": blockers,
        "warnings": warnings,
        "query": {
            "phase": phase_token or "__active__",
            "target_paths": target_set,
            "write_profiles": profile_rows,
            "session_id": session_id,
            "require_exclusive": bool(require_exclusive),
            "task_ledger_source": selected_task_ledger_source,
            "requested_task_ledger_source": requested_task_ledger_source,
            "task_ledger_source_policy": {
                "default": "plain entrypoint uses materialized WorkItem projections for live-work selection",
                "authority_replay_when": [
                    "--workitem-path is supplied",
                    "--workitem-write-profile is supplied",
                    "--workitem-require-exclusive is supplied",
                    "attempted_action is supplied by an internal caller",
                ],
            },
        },
        "live_work_runtime_attention": live_work_runtime_attention,
        "authority_order": live_work_runtime_attention.get("authority_order"),
        "forward_integration": forward_policy,
        "dirty_surface_classes": forward_policy.get("dirty_surface_classes") or {},
        "strict_validation_obligations": {
            "paths": forward_policy.get("strict_validation_required_paths") or [],
            "rule": "strict validation applies to touched authority-bearing surfaces; unrelated dirty authority is not a clean-tree blocker",
        },
        "inspection_required_paths": forward_policy.get("inspection_required_paths") or [],
        "target_path_policy": forward_policy.get("target_path_policy") or {},
        "commit_readiness": commit_readiness,
        "task_ledger": task_ledger,
        "workitem_backlog_health": backlog_health,
        "workitem_backlog_attention": backlog_attention,
        "work_ledger": work_ledger,
        "concurrency_attention": concurrency_attention,
        "strict_json_artifact_attention": strict_json_attention,
        "phase_runtime_context": phase_runtime_context,
        "subphase_runtime_attention": subphase_runtime_attention,
        "applicable_mechanisms": applicable_mechanisms,
        "phase": phase.get("phase"),
        "subphase": phase.get("subphase"),
        "phase_freshness": phase_freshness,
        "projection_affordances": _projection_affordances(
            task_ledger,
            live_work_runtime_attention,
            concurrency_attention,
            strict_json_attention,
            phase_runtime_context,
            subphase_runtime_attention,
            applicable_mechanisms,
            prompt_trace,
            provider,
            uppropagation,
        ),
        "prompt_trace": prompt_trace,
        "uppropagation_intake": uppropagation,
        "provider": provider,
        "hook_obligations": {
            "before_mutation": [
                "classify dirty target paths",
                "claim or no-claim receipt for authority/high-risk surfaces",
                "link WorkItem or no-link receipt",
            ],
            "before_commit": [
                "strict validation for touched authority files",
                "projection check for touched projections",
            ],
            "before_finalize": [
                "Task Ledger signoff or residual capture",
                "Work Ledger closeout while read receipt is live",
                "release claims",
                "session-finalize last",
            ],
        },
        "next_legal_actions": [
            "continue scoped edits that do not overwrite unrelated dirty work",
            "select active implementation from workitem_backlog_health.recommended_next_workitems when possible",
            "append Task Ledger captures for unresolved integration debt",
            "use projection affordances for selection; mutate through authoritative event logs",
        ],
        "sources": {
            "forward_policy_standard": "codex/standards/std_forward_integration_policy.json",
            "task_ledger_authority": "state/task_ledger/events.jsonl",
            "work_ledger_authority": "state/work_ledger/runtime_status.json",
            "work_ledger_write_profiles": "tools/meta/factory/work_ledger.py::WRITE_PROFILE_PATHS",
            "owner_tool_registry": "system/lib/forward_integration_policy.py::OWNER_TOOL_REGISTRY",
            "uppropagation_intake_standard": "codex/standards/std_uppropagation_intake.json",
        },
    }
