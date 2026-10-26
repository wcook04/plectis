#!/usr/bin/env python3
"""
Always-on metabolic kernel for ai_workflow.

[PURPOSE]
- Teleology: Keep the repo's maintenance surfaces alive in the background by
  owning the durable queue, blackboard, provider budgets, launch-agent install,
  and safe dispatch of small upkeep jobs.
- Mechanism: Read events from SQLite + inbox spool files, scan deterministic
  substrate surfaces, derive launchable-operation jobs, enforce provider
  budgets/cooldowns, and project runtime status to JSON/Markdown.
"""
from __future__ import annotations

import argparse
import errno
import gzip
import hashlib
import json
import os
import plistlib
import shutil
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]


def _safe_type_a_recovery_summary(
    family_token: str = "09",
) -> dict[str, Any] | None:
    """Best-effort projection of Type A attempt-recovery state for the
    blackboard. Catches every error so blackboard rendering never breaks."""
    try:
        family_dir = _resolve_family_dir_for_recovery(REPO_ROOT, family_token)
        if not family_dir:
            return None
        return raw_seed_attempt_recovery.type_a_recovery_summary(REPO_ROOT, family_dir)
    except Exception:
        return None
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.repo_env import maybe_reexec_into_repo_python

if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)

from system.lib import metabolism_blackboard as blackboard  # noqa: E402
from system.lib import metabolism_governor as governor  # noqa: E402
from system.lib import metabolism_hooks  # noqa: E402
from system.lib import metabolism_market_clock as market_clock  # noqa: E402
from system.lib import metabolism_policy as policy  # noqa: E402
from system.lib import provider_metabolism_signal as provider_signal  # noqa: E402
from system.lib import metabolism_raw_seed_intake as raw_seed_intake  # noqa: E402
from system.lib import metabolism_reconciliation as reconciliation  # noqa: E402
from system.lib import metabolism_scheduler as scheduler  # noqa: E402
from system.lib import metabolism_store as store  # noqa: E402
from system.lib import type_a_worker_harness  # noqa: E402
from system.lib.metabolism_row_jobs import build_metabolism_row_jobs  # noqa: E402
from system.lib import raw_seed_attempt_recovery  # noqa: E402
from system.lib.raw_seed_atomization import _resolve_family_dir as _resolve_family_dir_for_recovery  # noqa: E402
from tools.meta.control import market_snapshot as market_snapshot_tool  # noqa: E402


STATUS_SCHEMA = "metabolism_status_v2"
STATUS_SCHEMA_PREVIOUS = "metabolism_status_v1"
PROCESS_NAME = "metabolismd"
ONCE_PROCESS_NAME = "metabolismd_once"
HEARTBEAT_STALE_AFTER_SECONDS = 120.0
LAUNCH_AGENT_LABEL = "com.aiworkflow.metabolismd"
LAUNCH_AGENT_SOURCE = REPO_ROOT / "launchd" / f"{LAUNCH_AGENT_LABEL}.plist"

# Loop-phase state machine: foreground tick phases for the resident daemon.
# Observer commands read the most-recent phase from the runtime ticks sidecar so
# a stalled foreground loop cannot masquerade as "healthy" behind a fresh
# background heartbeat.
LOOP_PHASE_STARTUP = "startup"
LOOP_PHASE_REAP = "reap"
LOOP_PHASE_POLL = "poll"
LOOP_PHASE_DISPATCH = "dispatch"
LOOP_PHASE_SCAN = "scan"
LOOP_PHASE_APPLY_POLICIES = "apply_policies"
LOOP_PHASE_PROJECT = "project"
LOOP_PHASE_SLEEP = "sleep"
LOOP_PHASE_SHUTDOWN = "shutdown"
LOOP_PHASES: tuple[str, ...] = (
    LOOP_PHASE_STARTUP,
    LOOP_PHASE_REAP,
    LOOP_PHASE_POLL,
    LOOP_PHASE_DISPATCH,
    LOOP_PHASE_SCAN,
    LOOP_PHASE_APPLY_POLICIES,
    LOOP_PHASE_PROJECT,
    LOOP_PHASE_SLEEP,
    LOOP_PHASE_SHUTDOWN,
)

# Foreground tick staleness thresholds (3x the default 10s poll cadence).
LOOP_TICK_STALE_AFTER_SECONDS = 90.0
JOB_POLL_STALE_AFTER_SECONDS = 90.0
CHILD_REAP_STALE_AFTER_SECONDS = 90.0

DAEMON_HEALTH_HEALTHY = "healthy"
DAEMON_HEALTH_DEGRADED = "degraded"
DAEMON_HEALTH_STALLED = "stalled"
DAEMON_HEALTH_NOT_RUNNING = "not_running"
SELECTOR_TICK_SCHEMA = "metabolism_selector_tick_v0"
SELECTOR_TICK_KIND = "metabolism_selector_tick"
SELECTOR_TICK_SETTING_KEY = "selector_tick_latest"
SELECTOR_MATERIALIZED_SETTING_KEY = "selector_tick_materialized"

LAUNCHABLE_OPERATION_CONTRACT_STATUS_SCHEMA = "launchable_operation_contract_status_v1"
LAUNCHABLE_OPERATION_CONTRACT_OVERLAY_REF = "codex/contracts/launchable_operation_contracts.json"
LAUNCHABLE_OPERATION_STANDARD_REF = "codex/standards/std_launchable_operation_contract.json"


def _import_launch_contracts_module():
    from system.lib import launchable_operation_contracts as launch_contracts

    return launch_contracts


def _import_launchable_operations_module():
    from system.lib import launchable_operations as launch_ops

    return launch_ops


def prepare_launch_operation(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().prepare_launch_operation(*args, **kwargs)


def parse_operation_output_payload(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().parse_operation_output_payload(*args, **kwargs)


def artifact_refs_from_operation_payload(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().artifact_refs_from_operation_payload(*args, **kwargs)


def start_meta_mission_run(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().start_meta_mission_run(*args, **kwargs)


def finalize_meta_mission_run(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().finalize_meta_mission_run(*args, **kwargs)


def launcher_meta_mission_env(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().launcher_meta_mission_env(*args, **kwargs)


def artifact_refs_from_operation_output(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().artifact_refs_from_operation_output(*args, **kwargs)


def operation_event_fields_from_operation_payload(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().operation_event_fields_from_operation_payload(*args, **kwargs)


def operation_event_fields_from_operation_output(*args: Any, **kwargs: Any) -> Any:
    return _import_launchable_operations_module().operation_event_fields_from_operation_output(*args, **kwargs)


def _safe_launchable_operation_contract_status(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    try:
        launch_contracts = _import_launch_contracts_module()
        return launch_contracts.build_status_projection(repo_root)
    except Exception as exc:  # noqa: BLE001 - status/doctor must not fail on contract projection.
        return {
            "schema_version": LAUNCHABLE_OPERATION_CONTRACT_STATUS_SCHEMA,
            "posture": "report_only_warn",
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "contract_overlay_ref": LAUNCHABLE_OPERATION_CONTRACT_OVERLAY_REF,
            "standard_ref": LAUNCHABLE_OPERATION_STANDARD_REF,
            "next_action": "inspect launchable-operation contract resolver error or install the repo server dependencies",
        }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _utc_now() -> str:
    return store.utc_now()


def _runtime_ticks_path(repo_root: Path) -> Path:
    return repo_root / "state" / "metabolism" / "runtime_ticks.json"


def _read_runtime_ticks(repo_root: Path) -> dict[str, Any]:
    path = _runtime_ticks_path(repo_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _tick_is_stale(tick_value: Any, *, now: datetime, threshold_seconds: float) -> bool:
    parsed = _parse_dt(tick_value)
    if parsed is None:
        return True
    return (now - parsed).total_seconds() > threshold_seconds


def _launch_argv_for_prepared_command(command: str) -> list[str]:
    argv = shlex.split(str(command or ""))
    if not argv:
        raise ValueError("prepared command is empty")
    launcher = argv[0]
    launcher_name = Path(launcher).name
    if launcher in {"./repo-python", "repo-python"} or launcher_name == "repo-python":
        return [sys.executable, *argv[1:]]
    if launcher in {"python3", "python"}:
        return [sys.executable, *argv[1:]]
    return argv


def _background_policy_argv_for_operation(
    operation_id: str,
    operation_parameters: Mapping[str, Any],
    argv: list[str],
) -> tuple[list[str], dict[str, Any]]:
    local_cost_class = governor.operation_local_cost_class(operation_id, operation_parameters)
    policy = {
        "local_cost_class": local_cost_class,
        "background_policy": "none",
        "taskpolicy_applied": False,
    }
    if not governor.should_launch_with_background_policy(local_cost_class):
        return argv, policy
    policy["background_policy"] = "taskpolicy_background_throttle"
    taskpolicy = shutil.which("taskpolicy")
    if sys.platform != "darwin" or not taskpolicy:
        policy["background_policy"] = "taskpolicy_unavailable"
        return argv, policy
    wrapped = [taskpolicy, "-b", "-c", "background", "-d", "throttle", *argv]
    policy["taskpolicy_applied"] = True
    return wrapped, policy


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _heartbeat_fresh(row: Mapping[str, Any], *, now: datetime | None = None) -> bool:
    seen = _parse_dt(row.get("last_seen_at"))
    if seen is None:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - seen).total_seconds() <= HEARTBEAT_STALE_AFTER_SECONDS


def _heartbeat_age_seconds(row: Mapping[str, Any], *, now: datetime | None = None) -> float | None:
    seen = _parse_dt(row.get("last_seen_at"))
    if seen is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max((now - seen).total_seconds(), 0.0)


def _pid_running(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError as exc:
        if exc.errno == errno.EPERM:
            return True
        return False
    return True


def _tail_text(path: Path, *, limit: int = 8000) -> str:
    if not path.exists():
        return ""
    if limit <= 0:
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(size - limit, 0), os.SEEK_SET)
        data = handle.read(limit)
    return data.decode("utf-8", errors="replace")


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _live_daemon_heartbeats(conn) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    candidates = [
        dict(row)
        for row in store.list_heartbeats(conn)
        if row.get("process_name") == PROCESS_NAME
        and (row.get("payload") or {}).get("mode") != "once"
        and _heartbeat_fresh(row, now=now)
    ]
    candidates.sort(
        key=lambda row: (
            str(row.get("started_at") or ""),
            str(row.get("last_seen_at") or ""),
        ),
        reverse=True,
    )
    live: list[dict[str, Any]] = []
    for row in candidates:
        if _pid_running(row.get("pid")):
            live.append(row)
    return live


def _live_daemon_heartbeat(conn) -> dict[str, Any] | None:
    live = _live_daemon_heartbeats(conn)
    return live[0] if live else None


def _latest_alive_daemon_heartbeat(conn) -> dict[str, Any] | None:
    candidates = [
        dict(row)
        for row in store.list_heartbeats(conn)
        if row.get("process_name") == PROCESS_NAME
        and (row.get("payload") or {}).get("mode") != "once"
        and _pid_running(row.get("pid"))
    ]
    candidates.sort(
        key=lambda row: (
            str(row.get("started_at") or ""),
            str(row.get("last_seen_at") or ""),
        ),
        reverse=True,
    )
    return candidates[0] if candidates else None


def build_daemon_start_guard_report(conn, *, current_pid: int | None = None) -> dict[str, Any]:
    current_pid = int(current_pid or os.getpid())
    live = [
        row
        for row in _live_daemon_heartbeats(conn)
        if int(row.get("pid") or 0) != current_pid
    ]
    active_owner_jobs: list[dict[str, Any]] = []
    for job in store.fetch_jobs(
        conn,
        states=[store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING],
    ):
        owner_liveness = _job_owner_liveness(job)
        owner = str(owner_liveness.get("owner") or "")
        owner_pid = owner_liveness.get("pid")
        if (
            owner.startswith(f"{PROCESS_NAME}:")
            and isinstance(owner_pid, int)
            and owner_pid != current_pid
            and owner_liveness.get("pid_running")
        ):
            active_owner_jobs.append(
                {
                    "id": job.get("id"),
                    "kind": job.get("kind"),
                    "provider": job.get("provider"),
                    "state": job.get("state"),
                    "claim_owner": job.get("claim_owner"),
                    "owner_liveness": owner_liveness,
                }
            )
    recovery_commands = [
        "./repo-python -m tools.meta.control.metabolismd status --json",
        "./repo-python -m tools.meta.control.metabolismd doctor --json",
    ]
    if live or active_owner_jobs:
        recovery_commands.extend(
            [
                "Use scoped drains instead of starting a second resident loop: ./repo-python -m tools.meta.control.metabolismd run --once --job-id <job_id> --require-dispatch --once-drain-timeout-seconds 300",
                "Stop the existing foreground metabolismd process or let launchd own the resident loop before starting another daemon.",
            ]
        )
    if live:
        status = "daemon_already_running"
    elif active_owner_jobs:
        status = "active_metabolism_owner_without_fresh_heartbeat"
    else:
        status = "clear"
    return {
        "schema": "metabolism_daemon_start_guard_v1",
        "generated_at": _utc_now(),
        "ok": not bool(live or active_owner_jobs),
        "current_pid": current_pid,
        "status": status,
        "live_daemon_count": len(live),
        "live_daemons": [
            {
                "pid": row.get("pid"),
                "owner": (row.get("payload") or {}).get("owner"),
                "started_at": row.get("started_at"),
                "last_seen_at": row.get("last_seen_at"),
                "heartbeat_age_seconds": _heartbeat_age_seconds(row),
            }
            for row in live
        ],
        "active_owner_job_count": len(active_owner_jobs),
        "active_owner_jobs": active_owner_jobs,
        "recovery_commands": recovery_commands,
    }


def _owner_pid(owner: str | None) -> int | None:
    token = str(owner or "").strip()
    if ":" not in token:
        return None
    _, pid_text = token.rsplit(":", 1)
    try:
        pid = int(pid_text)
    except ValueError:
        return None
    return pid if pid > 0 else None


def _job_owner_liveness(job: Mapping[str, Any]) -> dict[str, Any]:
    owner = str(job.get("claim_owner") or "").strip()
    if not owner:
        return {
            "owner": None,
            "pid": None,
            "pid_running": False,
            "state": "missing_owner",
            "recoverable": True,
        }
    pid = _owner_pid(owner)
    if pid is None:
        return {
            "owner": owner,
            "pid": None,
            "pid_running": False,
            "state": "unparseable_owner",
            "recoverable": False,
        }
    running = _pid_running(pid)
    return {
        "owner": owner,
        "pid": pid,
        "pid_running": running,
        "state": "owner_alive" if running else "owner_dead",
        "recoverable": not running,
    }


def build_queue_liveness_report(conn, *, live_heartbeat: Mapping[str, Any] | None = None) -> dict[str, Any]:
    live_daemon_rows = _live_daemon_heartbeats(conn)
    if live_heartbeat:
        live_heartbeat_row = dict(live_heartbeat)
        if not any(row.get("pid") == live_heartbeat_row.get("pid") for row in live_daemon_rows):
            live_daemon_rows = [live_heartbeat_row, *live_daemon_rows]
    else:
        live_heartbeat_row = dict(live_daemon_rows[0] if live_daemon_rows else {})
    duplicate_daemon_rows = live_daemon_rows[1:] if len(live_daemon_rows) > 1 else []
    now = datetime.now(timezone.utc)
    heartbeat_age_seconds = (
        _heartbeat_age_seconds(live_heartbeat_row, now=now) if live_heartbeat_row else None
    )
    scheduler_settings = store.get_setting(conn, "scheduler", {}) or {}
    poll_seconds = float(scheduler_settings.get("poll_seconds") or 10)
    daemon_stall_threshold_seconds = max(poll_seconds * 3.0, 30.0)
    active_jobs = store.fetch_jobs(
        conn,
        states=[store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING],
    )
    queued_jobs = store.fetch_jobs(
        conn,
        states=[store.JOB_STATE_QUEUED, store.JOB_STATE_RECOVERABLE],
    )
    orphaned: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    live_active: list[dict[str, Any]] = []
    provider_holds: dict[str, int] = {}
    live_owner_job_count = 0
    for job in active_jobs:
        provider = str(job.get("provider") or "local")
        provider_holds[provider] = provider_holds.get(provider, 0) + 1
        owner_liveness = _job_owner_liveness(job)
        if owner_liveness.get("pid_running"):
            live_owner_job_count += 1
        live_pid = live_heartbeat_row.get("pid")
        owner = str(owner_liveness.get("owner") or "")
        owner_pid = owner_liveness.get("pid")
        if (
            owner.startswith(f"{PROCESS_NAME}:")
            and isinstance(live_pid, int)
            and live_pid > 0
            and isinstance(owner_pid, int)
            and owner_pid != live_pid
        ):
            owner_state = "stale_daemon_owner_dead"
            recoverable = True
            if owner_liveness.get("pid_running"):
                owner_state = "stale_daemon_owner_alive"
                recoverable = False
            owner_liveness = {
                **owner_liveness,
                "state": owner_state,
                "recoverable": recoverable,
                "live_daemon_pid": live_pid,
                "live_daemon_owner": (live_heartbeat_row.get("payload") or {}).get("owner"),
            }
        item = {
            "id": job.get("id"),
            "kind": job.get("kind"),
            "provider": provider,
            "state": job.get("state"),
            "priority": job.get("priority"),
            "updated_at": job.get("updated_at"),
            "claim_owner": job.get("claim_owner"),
            "claim_expires_at": job.get("claim_expires_at"),
            "owner_liveness": owner_liveness,
        }
        if owner_liveness.get("recoverable"):
            orphaned.append(item)
        elif not live_heartbeat_row or str(owner_liveness.get("state") or "").startswith("stale_daemon_owner"):
            ambiguous.append(item)
        else:
            live_active.append(item)
    daemon_heartbeat_stalled = bool(
        live_heartbeat_row
        and heartbeat_age_seconds is not None
        and heartbeat_age_seconds > daemon_stall_threshold_seconds
    )
    if orphaned:
        status = "orphaned_active_jobs"
    elif ambiguous and live_heartbeat_row:
        status = "active_jobs_ambiguous_owner"
    elif active_jobs and not live_heartbeat_row:
        if live_owner_job_count == len(active_jobs):
            status = "active_jobs_owned_by_live_runner_without_registered_daemon"
        else:
            status = "active_jobs_without_live_daemon"
    elif active_jobs and daemon_heartbeat_stalled:
        status = "active_jobs_live_daemon_stalled"
    elif active_jobs:
        status = "active_jobs_live"
    elif duplicate_daemon_rows:
        status = "duplicate_daemon_heartbeat"
    elif (
        queued_jobs
        and live_heartbeat_row
        and heartbeat_age_seconds is not None
        and heartbeat_age_seconds > daemon_stall_threshold_seconds
    ):
        status = "queued_work_ready_for_daemon_stalled"
    elif queued_jobs:
        status = "queued_work_ready_for_daemon"
    else:
        status = "idle"
    recovery_commands = []
    if orphaned:
        recovery_commands.append(
            "./repo-python -m tools.meta.control.metabolismd repair --live"
        )
    if not live_heartbeat_row and status != "active_jobs_owned_by_live_runner_without_registered_daemon":
        recovery_commands.append(
            "./repo-python -m tools.meta.control.metabolismd run"
        )
    if status == "active_jobs_owned_by_live_runner_without_registered_daemon":
        recovery_commands.extend(
            [
                "./repo-python -m tools.meta.control.metabolismd status --json",
                "./repo-python -m tools.meta.control.metabolismd doctor --json",
            ]
        )
    if status == "active_jobs_ambiguous_owner":
        recovery_commands.extend(
            [
                "./repo-python -m tools.meta.control.metabolismd jobs --state running",
                "./repo-python -m tools.meta.control.metabolismd doctor --json",
                "Stop duplicate foreground metabolismd processes or wait for the stale owner to exit; do not repair while owner_liveness.state is stale_daemon_owner_alive.",
                "./repo-python -m tools.meta.control.metabolismd run --once --job-id <job_id> --require-dispatch --once-drain-timeout-seconds 300",
            ]
        )
    if status == "queued_work_ready_for_daemon_stalled":
        recovery_commands.extend(
            [
                "./repo-python -m tools.meta.control.metabolismd run --once --once-drain-timeout-seconds 300",
                "Grant Full Disk Access for the launchd runner or move the repo out of Desktop/Documents, then reinstall the LaunchAgent.",
                "./repo-python -m tools.meta.control.metabolismd install-launch-agent",
            ]
        )
    if status == "duplicate_daemon_heartbeat":
        recovery_commands.extend(
            [
                "./repo-python -m tools.meta.control.metabolismd doctor --json",
                "Stop duplicate foreground metabolismd processes or let launchd own exactly one resident loop.",
                "./repo-python -m tools.meta.control.metabolismd run --once --job-id <job_id> --require-dispatch --once-drain-timeout-seconds 300",
            ]
        )
    if status == "active_jobs_live_daemon_stalled":
        recovery_commands.extend(
            [
                "./repo-python -m tools.meta.control.metabolismd jobs --state running",
                "./repo-python -m tools.meta.control.metabolismd jobs --state queued",
                "./repo-python -m tools.meta.control.metabolismd run --once --job-id <job_id> --require-dispatch --once-drain-timeout-seconds 300",
            ]
        )
    return {
        "schema": "metabolism_queue_liveness_v1",
        "generated_at": _utc_now(),
        "status": status,
        "daemon_running": bool(live_heartbeat_row),
        "daemon_pid": live_heartbeat_row.get("pid") if live_heartbeat_row else None,
        "live_daemon_count": len(live_daemon_rows),
        "duplicate_daemon_count": len(duplicate_daemon_rows),
        "duplicate_daemon_heartbeats": [
            {
                "pid": row.get("pid"),
                "owner": (row.get("payload") or {}).get("owner"),
                "started_at": row.get("started_at"),
                "last_seen_at": row.get("last_seen_at"),
                "heartbeat_age_seconds": _heartbeat_age_seconds(row),
            }
            for row in duplicate_daemon_rows
        ],
        "daemon_heartbeat_age_seconds": heartbeat_age_seconds,
        "daemon_stall_threshold_seconds": daemon_stall_threshold_seconds,
        "daemon_heartbeat_stalled": daemon_heartbeat_stalled,
        "active_job_count": len(active_jobs),
        "live_owner_job_count": live_owner_job_count,
        "queued_or_recoverable_job_count": len(queued_jobs),
        "provider_active_job_holds": [
            {"provider": provider, "active_job_count": count}
            for provider, count in sorted(provider_holds.items())
        ],
        "live_active_jobs": live_active,
        "orphaned_jobs": orphaned,
        "ambiguous_active_jobs": ambiguous,
        "recovery_commands": recovery_commands,
    }


def repair_orphaned_active_jobs(conn, *, live: bool = False) -> dict[str, Any]:
    before = build_queue_liveness_report(conn)
    orphaned = list(before.get("orphaned_jobs") or [])
    repaired: list[dict[str, Any]] = []
    if live and orphaned:
        grace_seconds = max(scheduler.orphan_recovery_grace_seconds(conn), 0)
        not_before = (
            (store.now_dt() + timedelta(seconds=grace_seconds)).isoformat()
            if grace_seconds
            else None
        )
        with store.transaction(conn):
            for item in orphaned:
                job_id = str(item.get("id") or "").strip()
                if not job_id:
                    continue
                live_job = store.fetch_job(conn, job_id)
                if live_job.get("state") not in {store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING}:
                    continue
                owner_liveness = _job_owner_liveness(live_job)
                item_liveness = item.get("owner_liveness") if isinstance(item.get("owner_liveness"), Mapping) else {}
                if str(item_liveness.get("state") or "").startswith("stale_daemon_owner"):
                    owner_liveness = dict(item_liveness)
                if not owner_liveness.get("recoverable"):
                    continue
                store.update_job(
                    conn,
                    job_id,
                    state=store.JOB_STATE_RECOVERABLE,
                    claim_owner=None,
                    claim_expires_at=None,
                    not_before=not_before,
                    last_error=(
                        "orphaned active job recovered by metabolismd repair "
                        f"({owner_liveness.get('state')})"
                    ),
                )
                repaired.append(
                    {
                        "id": job_id,
                        "previous_state": live_job.get("state"),
                        "provider": live_job.get("provider"),
                        "not_before": not_before,
                    }
                )
    after = build_queue_liveness_report(conn)
    return {
        "schema": "metabolism_repair_v1",
        "generated_at": _utc_now(),
        "live": bool(live),
        "candidate_count": len(orphaned),
        "repaired_count": len(repaired),
        "repaired_jobs": repaired,
        "before": before,
        "after": after,
    }


def run_reconciliation_pass(
    conn,
    *,
    repo_root: Path,
    scope: str,
    runtime_owner: str | None = None,
    apply_safe_repairs: bool = False,
    log_freshness_threshold_seconds: float | None = None,
    emit_event: bool = True,
) -> reconciliation.ReconciliationSnapshot:
    """Build queue liveness, then delegate to the reconciliation lib.

    Single entry point used by cmd_run boot, cmd_reconcile, and
    cmd_doctor so all three call sites share the same dependency wiring
    (queue_liveness, pid liveness probe, safe-repair callback). The
    reconciliation lib itself is dependency-injected and stays free of
    metabolismd-specific imports — see system/lib/metabolism_reconciliation.py.
    """
    queue_liveness = build_queue_liveness_report(conn)
    threshold = (
        float(log_freshness_threshold_seconds)
        if log_freshness_threshold_seconds is not None
        else 600.0
    )
    safe_repair_callback = (
        (lambda c: repair_orphaned_active_jobs(c, live=True))
        if apply_safe_repairs
        else None
    )
    return reconciliation.reconcile(
        conn,
        repo_root,
        queue_liveness_report=queue_liveness,
        scope=scope,
        runtime_owner=runtime_owner,
        apply_safe_repairs=apply_safe_repairs,
        safe_repair_callback=safe_repair_callback,
        pid_running=_pid_running,
        log_freshness_threshold_seconds=threshold,
        emit_event=emit_event,
    )


def _compact_provider_pressure(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    compact: list[dict[str, Any]] = []
    for row in rows[:8]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            {
                "provider": row.get("provider"),
                "blocked": bool(row.get("blocked")),
                "active_total": row.get("active_total"),
                "max_concurrent": row.get("max_concurrent"),
                "reason": row.get("reason"),
            }
        )
    return compact


def _compact_selector_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    candidate_feed = snapshot.get("candidate_feed") if isinstance(snapshot.get("candidate_feed"), Mapping) else {}
    candidates = candidate_feed.get("candidates") if isinstance(candidate_feed, Mapping) else []
    return {
        "schema_version": snapshot.get("schema_version"),
        "kind": snapshot.get("kind"),
        "generated_at": snapshot.get("generated_at"),
        "source": snapshot.get("source"),
        "mode": snapshot.get("mode"),
        "dispatch_enabled": bool(snapshot.get("dispatch_enabled")),
        "dispatch_block_reason": snapshot.get("dispatch_block_reason"),
        "cpu_gate_state": snapshot.get("cpu_gate_state"),
        "provider_pressure": _compact_provider_pressure(snapshot.get("provider_pressure")),
        "candidate_count": int(snapshot.get("candidate_count") or 0),
        "claimable_count": int(snapshot.get("claimable_count") or 0),
        "next_candidate_id": snapshot.get("next_candidate_id"),
        "next_candidate": snapshot.get("next_candidate"),
        "next_claimable_by_provider": snapshot.get("next_claimable_by_provider") or {},
        "skip_reason_ledger": list(snapshot.get("skip_reason_ledger") or [])[:20],
        "hard_veto_summary": dict(snapshot.get("hard_veto_summary") or {}),
        "why_nothing_ran": snapshot.get("why_nothing_ran"),
        "stale_receipt_count": int(snapshot.get("stale_receipt_count") or 0),
        "provider_scorecard": snapshot.get("provider_scorecard") or {},
        "candidate_feed": {
            "source": candidate_feed.get("source") if isinstance(candidate_feed, Mapping) else None,
            "candidate_count": len(candidates) if isinstance(candidates, list) else 0,
            "claimable_count": snapshot.get("claimable_count") or 0,
            "next_candidate_id": snapshot.get("next_candidate_id") or "",
        },
    }


def _selector_receipt_candidates(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    feed = snapshot.get("candidate_feed") if isinstance(snapshot.get("candidate_feed"), Mapping) else {}
    candidates = feed.get("candidates") if isinstance(feed, Mapping) else []
    rows: list[dict[str, Any]] = []
    for candidate in candidates or []:
        if not isinstance(candidate, Mapping):
            continue
        vetoes = [
            str(reason)
            for reason in (
                list(candidate.get("hard_vetoes") or [])
                + list(candidate.get("skip_reasons") or [])
            )
            if str(reason).strip()
        ]
        if vetoes and not bool(candidate.get("selector_claimable_now")):
            rows.append(dict(candidate))
    return rows


def _row_job_for_candidate(repo_root: Path, candidate: Mapping[str, Any], *, limit: int) -> dict[str, Any] | None:
    target_row_id = str(candidate.get("target_row_id") or "").strip()
    if not target_row_id:
        return None
    payload = build_metabolism_row_jobs(
        repo_root=repo_root,
        source="provider-model-catalog",
        limit=max(int(limit or 1), 1),
    )
    for row in payload.get("row_jobs") or []:
        if isinstance(row, Mapping) and str(row.get("target_row_id") or "").strip() == target_row_id:
            return dict(row)
    return None


def _select_next_candidate(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    next_candidate = snapshot.get("next_candidate")
    if isinstance(next_candidate, Mapping) and next_candidate.get("candidate_id"):
        return dict(next_candidate)
    feed = snapshot.get("candidate_feed") if isinstance(snapshot.get("candidate_feed"), Mapping) else {}
    candidates = feed.get("candidates") if isinstance(feed, Mapping) else []
    claimable = [
        dict(row)
        for row in candidates or []
        if isinstance(row, Mapping) and bool(row.get("selector_claimable_now"))
    ]
    return max(
        claimable,
        key=lambda row: (float(row.get("score") or 0.0), -int(row.get("selection_index") or 0)),
        default=None,
    )


def run_selector_tick(
    conn,
    repo_root: Path,
    *,
    apply: bool = True,
    limit: int = 20,
    receipt_limit: int = 5,
    candidate_feed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one low-heat selector tick.

    The tick builds the canonical selector snapshot, writes bounded deduped
    skip/veto receipts, and materializes at most one transform-job draft.  It
    never calls a provider and never promotes doctrine/source authority.
    """
    feed = dict(
        candidate_feed
        or provider_signal.derive_candidate_job_feed(
            repo_root,
            source="all",
            limit=limit,
        )
    )
    snapshot = scheduler.build_selector_snapshot(
        conn,
        repo_root=repo_root,
        limit=limit,
        candidate_feed=feed,
    )
    compact_snapshot = _compact_selector_snapshot(snapshot)
    skip_written = 0
    skip_deduped = 0
    skip_dry_run = 0
    skip_samples: list[dict[str, Any]] = []
    mode = str(snapshot.get("mode") or "")
    for candidate in _selector_receipt_candidates(snapshot)[: max(int(receipt_limit or 0), 0)]:
        vetoes = [
            str(reason)
            for reason in (
                list(candidate.get("hard_vetoes") or [])
                + list(candidate.get("skip_reasons") or [])
            )
            if str(reason).strip()
        ]
        if not vetoes:
            continue
        original_skip_reasons = {
            str(reason)
            for reason in (candidate.get("skip_reasons") or [])
            if str(reason).strip()
        }
        hard_veto_values = [
            str(reason)
            for reason in (candidate.get("hard_vetoes") or [])
            if str(reason).strip()
        ]
        receipt_kind = (
            "veto"
            if any(reason not in original_skip_reasons for reason in hard_veto_values)
            else "skip"
        )
        receipt_candidate = (
            {**candidate, "hard_vetoes": []}
            if receipt_kind == "skip"
            else candidate
        )
        if not apply:
            skip_dry_run += 1
            skip_samples.append(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "receipt": None,
                    "receipt_kind": receipt_kind,
                    "deduped": False,
                    "dry_run": True,
                    "reason": vetoes[0],
                }
            )
            continue
        result = type_a_worker_harness.write_candidate_skip_receipt(
            repo_root,
            candidate=receipt_candidate,
            receipt_kind=receipt_kind,
            skip_reason=vetoes[0],
            hard_vetoes=vetoes if receipt_kind == "veto" else [],
            governor_mode=mode,
            cpu_gate_state=(
                candidate.get("cpu_gate_state")
                if isinstance(candidate.get("cpu_gate_state"), Mapping)
                else {}
            ),
        )
        deduped = bool(result.artifact_refs.get("deduped"))
        if deduped:
            skip_deduped += 1
        else:
            skip_written += 1
        skip_samples.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "receipt": result.artifact_refs.get("receipt"),
                "receipt_kind": receipt_kind,
                "deduped": deduped,
                "reason": vetoes[0],
            }
        )

    selected = _select_next_candidate(snapshot)
    selected_candidate_id = str((selected or {}).get("candidate_id") or "")
    selected_action = "none"
    selected_action_status = str(snapshot.get("why_nothing_ran") or "no queued work")
    materialized_artifact_path = None
    materialized_deduped = False
    selected_error = None
    if selected:
        selected_action = "materialize_transform_job_draft"
        if not apply:
            selected_action_status = "dry_run"
        elif str(selected.get("candidate_kind") or "") != "provider_model_catalog_row_job_candidate":
            selected_action_status = "unsupported_candidate_kind"
        else:
            materialized_index = store.get_setting(conn, SELECTOR_MATERIALIZED_SETTING_KEY, {}) or {}
            if not isinstance(materialized_index, dict):
                materialized_index = {}
            materialization_key = policy.stable_digest(
                {
                    "schema": SELECTOR_TICK_SCHEMA,
                    "candidate_id": selected_candidate_id,
                    "source_fingerprint": selected.get("source_fingerprint"),
                    "target_row_id": selected.get("target_row_id"),
                    "action": selected_action,
                }
            )
            previous = materialized_index.get(materialization_key)
            previous_path = str((previous or {}).get("artifact_path") or "") if isinstance(previous, Mapping) else ""
            if previous_path and (repo_root / previous_path).exists():
                materialized_artifact_path = previous_path
                materialized_deduped = True
                selected_action_status = "deduped_materialized"
            else:
                row_job = _row_job_for_candidate(repo_root, selected, limit=limit)
                if row_job is None:
                    selected_action_status = "blocked_missing_row_job"
                else:
                    try:
                        result = type_a_worker_harness.materialize_provider_transform_job_from_row_job(
                            repo_root,
                            row_job,
                            write=True,
                            created_by="metabolism_selector_tick",
                        )
                        materialized_artifact_path = result.get("artifact_path")
                        materialized_index[materialization_key] = {
                            "candidate_id": selected_candidate_id,
                            "source_fingerprint": selected.get("source_fingerprint"),
                            "target_row_id": selected.get("target_row_id"),
                            "artifact_path": materialized_artifact_path,
                            "provider_id": result.get("provider_id"),
                            "runtime_token": result.get("runtime_token"),
                            "created_at": _utc_now(),
                        }
                        store.set_setting(conn, SELECTOR_MATERIALIZED_SETTING_KEY, materialized_index)
                        selected_action_status = "materialized_transform_job_draft"
                    except Exception as exc:  # noqa: BLE001 - selector tick must stay observable.
                        selected_error = f"{type(exc).__name__}: {exc}"
                        selected_action_status = "materialization_blocked"

    report = {
        "schema_version": SELECTOR_TICK_SCHEMA,
        "kind": SELECTOR_TICK_KIND,
        "generated_at": _utc_now(),
        "apply": bool(apply),
        "mode": compact_snapshot.get("mode"),
        "candidate_count": compact_snapshot.get("candidate_count"),
        "claimable_count": compact_snapshot.get("claimable_count"),
        "skip_receipts_written": skip_written,
        "skip_receipts_deduped": skip_deduped,
        "skip_receipts_dry_run": skip_dry_run,
        "skip_receipts": skip_samples,
        "selected_candidate_id": selected_candidate_id,
        "selected_action": selected_action,
        "selected_action_status": selected_action_status,
        "selected_error": selected_error,
        "materialized_artifact_path": materialized_artifact_path,
        "materialized_deduped": materialized_deduped,
        "why_nothing_ran": compact_snapshot.get("why_nothing_ran"),
        "hard_veto_summary": compact_snapshot.get("hard_veto_summary") or {},
        "provider_pressure_summary": compact_snapshot.get("provider_pressure") or [],
        "stale_receipt_count": compact_snapshot.get("stale_receipt_count") or 0,
        "provider_scorecard": compact_snapshot.get("provider_scorecard") or {},
        "selector_snapshot": compact_snapshot,
        "receipt_summary": {
            "skip_receipts_written": skip_written,
            "skip_receipts_deduped": skip_deduped,
            "skip_receipts_dry_run": skip_dry_run,
        },
    }
    if apply:
        store.set_setting(conn, SELECTOR_TICK_SETTING_KEY, report)
    return report


def _selector_tick_skipped_report(reason: str) -> dict[str, Any]:
    reason = str(reason or "dispatch disabled").strip() or "dispatch disabled"
    selector_snapshot = {
        "schema_version": provider_signal.SELECTOR_SNAPSHOT_SCHEMA_VERSION,
        "kind": provider_signal.SELECTOR_SNAPSHOT_KIND,
        "candidate_count": 0,
        "claimable_count": 0,
        "why_nothing_ran": reason,
    }
    return {
        "schema_version": SELECTOR_TICK_SCHEMA,
        "kind": SELECTOR_TICK_KIND,
        "generated_at": _utc_now(),
        "apply": False,
        "candidate_count": 0,
        "claimable_count": 0,
        "skip_receipts_written": 0,
        "skip_receipts_deduped": 0,
        "skip_receipts_dry_run": 0,
        "skip_receipts": [],
        "selected_candidate_id": "",
        "selected_action": "none",
        "selected_action_status": "skipped_dispatch_disabled",
        "selected_error": None,
        "materialized_artifact_path": None,
        "materialized_deduped": False,
        "why_nothing_ran": reason,
        "selector_snapshot": selector_snapshot,
        "receipt_summary": {
            "skip_receipts_written": 0,
            "skip_receipts_deduped": 0,
            "skip_receipts_dry_run": 0,
        },
    }


def _launchctl_state(label: str) -> tuple[bool, str]:
    domain = f"gui/{os.getuid()}/{label}"
    proc = subprocess.run(
        ["launchctl", "print", domain],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, (proc.stderr or proc.stdout).strip()


def _plist_program_argument(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = plistlib.loads(path.read_bytes())
    except Exception:
        return None
    args = payload.get("ProgramArguments") if isinstance(payload, dict) else None
    if not isinstance(args, list) or not args:
        return None
    return str(args[0] or "").strip() or None


def _launchctl_last_exit_code(details: str) -> int | None:
    for line in str(details or "").splitlines():
        if "last exit code" not in line:
            continue
        _, _, value = line.partition("=")
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _yfinance_status() -> dict[str, Any]:
    try:
        import yfinance as yf
    except Exception as exc:
        return {
            "available": False,
            "version": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "available": True,
        "version": str(getattr(yf, "__version__", "")) or None,
        "error": None,
    }


def _pmset_status() -> dict[str, Any]:
    advisory = (
        "LaunchAgent survives terminal close but not system sleep. Keep the machine plugged in, "
        "keep network available, and enable Prevent automatic sleep when the display is off."
    )
    proc = subprocess.run(
        ["pmset", "-g"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {
            "available": False,
            "excerpt": "",
            "error": (proc.stderr or proc.stdout).strip(),
            "advisory": advisory,
        }
    excerpt = "\n".join((proc.stdout or "").splitlines()[:12]).strip()
    return {
        "available": True,
        "excerpt": excerpt,
        "error": None,
        "advisory": advisory,
    }


def _effective_market_config(conn) -> dict[str, Any]:
    raw_universe = store.get_setting(conn, "market_clock_universe", None)
    return {
        "schema": "market_clock_config_v1",
        "generated_at": _utc_now(),
        "clock": market_clock.load_config(conn),
        "universe_source": "custom" if isinstance(raw_universe, list) and bool(raw_universe) else "default",
        "universe": market_snapshot_tool._clean_universe(raw_universe),
        "timeline_path": str(market_clock.TIMELINE_PATH_REL),
    }


def _load_universe_file(path_text: str) -> list[dict[str, str]]:
    path = Path(path_text).expanduser()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("--universe-file must decode to a JSON array of {ticker,label} objects")
    cleaned = market_snapshot_tool._clean_universe(payload)
    if not cleaned:
        raise SystemExit("--universe-file did not yield any valid ticker entries")
    return cleaned


def render_launch_agent_plist(repo_root: Path, *, home: Path | None = None) -> str:
    user_home = home or Path.home()
    logs_dir = repo_root / "state" / "metabolism" / "logs"
    repo_env = repo_root / "repo-env"
    repo_python = repo_root / "repo-python"
    venv_python = repo_root / "venv" / "bin" / "python"
    if repo_env.exists() and repo_python.exists():
        program_arguments = [
            repo_env,
            repo_python,
            "-m",
            "tools.meta.control.metabolismd",
            "run",
        ]
    else:
        launcher = venv_python if venv_python.exists() else repo_python
        program_arguments = [
            launcher,
            "-m",
            "tools.meta.control.metabolismd",
            "run",
        ]
    rendered_arguments = "\n".join(f"    <string>{arg}</string>" for arg in program_arguments)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LAUNCH_AGENT_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
{rendered_arguments}
  </array>
  <key>WorkingDirectory</key>
  <string>{repo_root}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ProcessType</key>
  <string>Background</string>
  <key>LowPriorityIO</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{logs_dir / 'metabolismd.out.log'}</string>
  <key>StandardErrorPath</key>
  <string>{logs_dir / 'metabolismd.err.log'}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key>
    <string>{user_home}</string>
  </dict>
</dict>
</plist>
"""


class MetabolismRuntime:
    def __init__(
        self,
        repo_root: Path,
        *,
        enable_watchers: bool = False,
        runtime_mode: str = "daemon",
    ) -> None:
        self.repo_root = repo_root
        self.paths = store.metabolism_paths(repo_root)
        self.conn = store.connect(repo_root)
        requested_mode = str(runtime_mode or "").strip()
        if requested_mode == "once":
            self.runtime_mode = "once"
        elif requested_mode == "observer":
            self.runtime_mode = "observer"
        else:
            self.runtime_mode = "daemon"
        owner_prefix = ONCE_PROCESS_NAME if self.runtime_mode == "once" else PROCESS_NAME
        self.process_name = owner_prefix
        self.owner = f"{owner_prefix}:{os.getpid()}"
        self.started_at = _utc_now()
        self.processes: dict[str, dict[str, Any]] = {}
        self.last_scan_monotonic: float | None = None
        self._current_phase: str = LOOP_PHASE_STARTUP
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self.raw_seed_intake = raw_seed_intake.RawSeedIntakeCoordinator(
            repo_root,
            self.conn,
            enable_watchers=enable_watchers,
        )

    def close(self) -> None:
        self.stop_background_heartbeat()
        self.raw_seed_intake.close()
        self.conn.close()

    def touch_heartbeat(self) -> None:
        if self.runtime_mode == "observer":
            return
        store.touch_heartbeat(
            self.conn,
            process_name=self.process_name,
            pid=os.getpid(),
            payload={
                "repo_root": str(self.repo_root),
                "owner": self.owner,
                "mode": self.runtime_mode,
            },
            started_at=self.started_at,
        )

    def enter_phase(
        self,
        phase: str,
        *,
        next_scan_at: str | None = None,
        active_children: int | None = None,
    ) -> None:
        """Record a foreground loop phase transition into the runtime-ticks sidecar.

        Observer commands (status, doctor) read this file to distinguish a
        healthy daemon from one whose foreground loop is stuck behind a fresh
        background heartbeat.
        """
        if self.runtime_mode == "observer":
            return
        if phase not in LOOP_PHASES:
            raise ValueError(f"unknown loop phase: {phase!r}")
        self._current_phase = phase
        now = _utc_now()
        payload = _read_runtime_ticks(self.repo_root)
        payload["schema"] = "metabolism_runtime_ticks_v1"
        payload["owner"] = self.owner
        payload["pid"] = os.getpid()
        payload["mode"] = self.runtime_mode
        payload["current_phase"] = phase
        payload["loop_tick_at"] = now
        if phase == LOOP_PHASE_POLL:
            payload["last_job_poll_at"] = now
        if phase == LOOP_PHASE_REAP:
            payload["last_child_reap_at"] = now
        if phase == LOOP_PHASE_SCAN:
            payload["last_scan_at"] = now
        if next_scan_at is not None:
            payload["next_scan_at"] = next_scan_at
        if active_children is not None:
            payload["active_children"] = int(active_children)
        else:
            payload["active_children"] = len(self.processes)
        _atomic_write(
            _runtime_ticks_path(self.repo_root),
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        )

    def start_background_heartbeat(self, *, interval_seconds: float = 5.0) -> None:
        if self.runtime_mode != "daemon" or self._heartbeat_thread is not None:
            return
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._background_heartbeat_loop,
            kwargs={"interval_seconds": max(float(interval_seconds), 1.0)},
            name="metabolismd-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def stop_background_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        thread = self._heartbeat_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._heartbeat_thread = None

    def _background_heartbeat_loop(self, *, interval_seconds: float) -> None:
        while not self._heartbeat_stop.wait(interval_seconds):
            try:
                conn = store.connect(self.repo_root)
                try:
                    store.touch_heartbeat(
                        conn,
                        process_name=self.process_name,
                        pid=os.getpid(),
                        payload={
                            "repo_root": str(self.repo_root),
                            "owner": self.owner,
                            "mode": self.runtime_mode,
                            "heartbeat_source": "background",
                        },
                        started_at=self.started_at,
                    )
                finally:
                    conn.close()
            except Exception:
                # The foreground loop also heartbeats; this thread is an observability backstop.
                continue

    def ingest_inbox(self) -> int:
        count = 0
        self.paths.inbox_archive_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.paths.inbox_dir.glob("*.jsonl")):
            if path.is_dir():
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                store.enqueue_event(
                    self.conn,
                    source=str(payload.get("source") or "inbox"),
                    kind=str(payload.get("kind") or "unknown"),
                    payload=dict(payload.get("payload") or {}),
                    stable_digest=str(payload.get("stable_digest") or policy.stable_digest(payload)),
                )
                count += 1
            archived = self.paths.inbox_archive_dir / f"{path.stem}_{int(time.time())}.jsonl"
            path.replace(archived)
        return count

    def scan(self) -> dict[str, Any]:
        previous_state = store.get_setting(self.conn, "scan_state", {}) or {}
        file_events, next_state = policy.collect_scan_events(self.repo_root, previous_state)
        runtime_events = policy.build_runtime_signal_events(self.repo_root)
        inserted = 0
        for event in [*file_events, *runtime_events]:
            _row, created = store.enqueue_event(
                self.conn,
                source=event["source"],
                kind=event["kind"],
                payload=event["payload"],
                stable_digest=event["stable_digest"],
            )
            if created:
                inserted += 1
        store.set_setting(self.conn, "scan_state", next_state)
        return {
            "file_events": len(file_events),
            "runtime_events": len(runtime_events),
            "inserted": inserted,
        }

    def ingest_raw_seed_watch_events(self) -> int:
        inserted = 0
        for rel_path in self.raw_seed_intake.drain_watch_paths():
            root = self.raw_seed_intake.family_root_for_path(rel_path)
            if root is None:
                continue
            absolute_path = self.repo_root / rel_path
            try:
                fingerprint = policy._fingerprint_file(absolute_path)  # noqa: SLF001 - daemon uses policy's canonical fingerprinting.
            except OSError:
                continue
            _row, created = store.enqueue_event(
                self.conn,
                source="watchfiles",
                kind="raw_seed_edit_observed",
                payload={
                    "path": rel_path,
                    "category": "raw_seed",
                    "fingerprint": fingerprint,
                    "family": root.family_number,
                    "family_dir": root.family_dir,
                    "raw_seed_path": root.raw_seed_path,
                },
                stable_digest=policy.stable_digest(
                    {
                        "kind": "raw_seed_edit_observed",
                        "path": rel_path,
                        "fingerprint": fingerprint,
                    }
                ),
            )
            if created:
                inserted += 1
        return inserted

    def _apply_provider_interrupt(self, event: dict[str, Any]) -> None:
        payload = dict(event.get("payload") or {})
        provider = str(payload.get("provider") or "local").strip() or "local"
        reason = str(payload.get("reason") or "provider interrupt").strip()
        cooldown_seconds = int(payload.get("cooldown_seconds") or 300)
        current = store.get_provider_row(self.conn, provider)
        store.set_provider_row(
            self.conn,
            provider=provider,
            state="cooldown",
            cooldown_until=(store.now_dt() + timedelta(seconds=cooldown_seconds)).isoformat(),
            budget=current.get("budget") or {},
            last_interrupt={
                "reason": reason,
                "payload": payload.get("payload") or {},
                "updated_at": _utc_now(),
            },
        )

    def _apply_raw_seed_edit_observed(self, event: dict[str, Any]) -> bool:
        payload = dict(event.get("payload") or {})
        rel_path = str(payload.get("path") or "").strip()
        session = self.raw_seed_intake.observe_path(
            rel_path,
            source=str(event.get("source") or "metabolismd"),
            observed_at=str(event.get("created_at") or _utc_now()),
        )
        return bool(session)

    def _apply_auto_sync_completion(self, event: dict[str, Any]) -> int:
        payload = dict(event.get("payload") or {})
        operation_id = str(payload.get("operation_id") or "").strip()
        returncode = int(payload.get("returncode") or 0)
        if operation_id != "kernel_sync_raw_seed_auto" or returncode != 0:
            return 0
        params = dict(payload.get("resolved_parameters") or {})
        family = str(params.get("family") or "").strip()
        if not family:
            return 0
        synced = self.raw_seed_intake.mark_family_synced(
            family,
            synced_at=str(event.get("created_at") or _utc_now()),
        )
        return len(synced)

    def _apply_event_policies(self) -> dict[str, int]:
        processed = 0
        queued = 0
        observed = 0
        settled = 0
        synced = 0
        while True:
            self.touch_heartbeat()
            events = store.fetch_unprocessed_events(self.conn, limit=500)
            if not events:
                settle_events = self.raw_seed_intake.settle_due_sessions()
                if not settle_events:
                    break
                settled += len(settle_events)
                for event in settle_events:
                    store.enqueue_event(
                        self.conn,
                        source=str(event["source"]),
                        kind=str(event["kind"]),
                        payload=dict(event["payload"]),
                        stable_digest=str(event["stable_digest"]),
                    )
                continue
            for event in events:
                kind = str(event.get("kind") or "").strip()
                if kind == "provider_interrupt":
                    self._apply_provider_interrupt(event)
                    store.mark_event_processed(self.conn, int(event["id"]))
                    processed += 1
                    if processed % 50 == 0:
                        self.touch_heartbeat()
                    continue
                if kind == "raw_seed_edit_observed":
                    observed += 1 if self._apply_raw_seed_edit_observed(event) else 0
                    store.mark_event_processed(self.conn, int(event["id"]))
                    processed += 1
                    if processed % 50 == 0:
                        self.touch_heartbeat()
                    continue
                if kind == "operation_completed":
                    synced += self._apply_auto_sync_completion(event)
                for job in policy.derive_jobs_for_event(event):
                    _row, created = store.create_job(
                        self.conn,
                        kind=str(job["kind"]),
                        provider=str(job.get("provider") or "local"),
                        params=dict(job.get("params") or {}),
                        idempotency_key=str(job["idempotency_key"]),
                        priority=int(job.get("priority") or 20),
                        source_event_digest=str(event.get("stable_digest") or ""),
                        summary=dict(job.get("summary") or {}),
                    )
                    if created:
                        queued += 1
                store.mark_event_processed(self.conn, int(event["id"]))
                processed += 1
                if processed % 50 == 0:
                    self.touch_heartbeat()
        self.touch_heartbeat()
        for job in policy.derive_reaction_jobs(self.repo_root):
            idempotency_key = str(job["idempotency_key"])
            if store.fetch_job_by_idempotency(self.conn, idempotency_key):
                continue
            _row, created = store.create_job(
                self.conn,
                kind=str(job["kind"]),
                provider=str(job.get("provider") or "local"),
                params=dict(job.get("params") or {}),
                idempotency_key=idempotency_key,
                priority=int(job.get("priority") or 20),
                summary=dict(job.get("summary") or {}),
            )
            if created:
                queued += 1
        return {
            "processed_events": processed,
            "queued_jobs": queued,
            "raw_seed_observations": observed,
            "raw_seed_settled_events": settled,
            "raw_seed_synced_sessions": synced,
        }

    def _launch_job(self, job: dict[str, Any]) -> None:
        params = dict(job.get("params") or {})
        operation_id = str(params.get("operation_id") or job.get("kind") or "").strip()
        operation_parameters = dict(params.get("operation_parameters") or {})
        prepared = prepare_launch_operation(
            self.repo_root,
            operation_id=operation_id,
            parameters=operation_parameters,
        )
        log_path = self.paths.logs_dir / f"{job['id']}.log"
        meta_run_id = start_meta_mission_run(
            self.repo_root,
            prepared=prepared,
            operation_id=operation_id,
            parameters=operation_parameters,
            trigger="metabolismd",
        )
        env = os.environ.copy()
        if meta_run_id:
            env.update(
                launcher_meta_mission_env(
                    meta_mission_id=str(prepared.operation.get("meta_mission_id") or ""),
                    meta_mission_run_id=meta_run_id,
                    execution_mode=prepared.execution_mode,
                    base_env=env,
                )
            )
        handle = log_path.open("w", encoding="utf-8")
        base_argv = _launch_argv_for_prepared_command(prepared.command)
        launch_argv, launch_policy = _background_policy_argv_for_operation(
            operation_id,
            operation_parameters,
            base_argv,
        )
        run = store.insert_run(
            self.conn,
            job_id=job["id"],
            log_path=str(log_path.relative_to(self.repo_root)),
            summary={
                "operation_id": operation_id,
                "resolved_parameters": prepared.resolved_parameters,
                "command": prepared.command,
                "meta_mission_run_id": meta_run_id,
                "launch_policy": launch_policy,
            },
        )
        launch_record = {
            "kind": "metabolism_job_launch",
            "job_id": job["id"],
            "run_id": run["id"],
            "owner": self.owner,
            "operation_id": operation_id,
            "command": prepared.command,
            "argv": launch_argv,
            "base_argv": base_argv,
            "launch_policy": launch_policy,
            "resolved_parameters": prepared.resolved_parameters,
            "meta_mission_run_id": meta_run_id,
            "started_at": _utc_now(),
        }
        handle.write(json.dumps(launch_record, ensure_ascii=False) + "\n")
        handle.flush()
        proc = subprocess.Popen(
            launch_record["argv"],
            cwd=self.repo_root,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            start_new_session=True,
        )
        attempts = int(job.get("attempts") or 0) + 1
        running = scheduler.mark_running(self.conn, job["id"], owner=self.owner, attempts=attempts)
        self.processes[job["id"]] = {
            "proc": proc,
            "handle": handle,
            "prepared": prepared,
            "run_id": run["id"],
            "meta_mission_run_id": meta_run_id,
            "log_path": log_path,
            "job": running,
        }

    def _provider_backoff_seconds(self, provider: str) -> int:
        row = store.get_provider_row(self.conn, provider)
        budget = dict(row.get("budget") or {})
        backoff = list(budget.get("backoff_seconds") or [300])
        interrupt = dict(row.get("last_interrupt") or {})
        count = int(interrupt.get("count") or 0)
        index = min(count, max(len(backoff) - 1, 0))
        return int(backoff[index] or 300)

    def _looks_like_provider_interrupt(self, provider: str, log_text: str) -> bool:
        if provider not in {"chatgpt", "claude", "codex", "nvidia", "openrouter_free"}:
            return False
        lowered = log_text.lower()
        needles = [
            '"status": "429"',
            '"status": "timeout"',
            "read timed out",
            "rate limit",
            "rate-limited",
            "too many requests",
            "temporarily unavailable",
            "try again later",
            "response was empty",
            "not idle",
            "busy",
            "cooldown",
            "occupied",
        ]
        return any(token in lowered for token in needles)

    def retire_legacy_raw_seed_auto_jobs(self) -> int:
        count = 0
        for job in store.fetch_jobs(
            self.conn,
            states=[
                store.JOB_STATE_QUEUED,
                store.JOB_STATE_RECOVERABLE,
                store.JOB_STATE_BLOCKED,
                store.JOB_STATE_PAUSED,
            ],
            limit=500,
        ):
            if str(job.get("kind") or "") != "kernel_sync_raw_seed":
                continue
            summary = dict(job.get("summary") or {})
            params = dict(job.get("params") or {})
            if summary.get("category") != "raw_seed":
                continue
            if str(params.get("source") or "") not in {"", "metabolism_policy"}:
                continue
            store.update_job(
                self.conn,
                str(job["id"]),
                state=store.JOB_STATE_COMPLETED,
                last_error="retired legacy raw-seed auto sync job after intake tracker migration",
                summary={
                    **summary,
                    "retired_reason": "superseded_by_raw_seed_entry_settled",
                    "retired_at": _utc_now(),
                },
            )
            count += 1
        return count

    def retire_superseded_reaction_jobs(self) -> int:
        candidates: list[dict[str, Any]] = []
        for job in store.fetch_jobs(
            self.conn,
            states=[
                store.JOB_STATE_QUEUED,
                store.JOB_STATE_RECOVERABLE,
                store.JOB_STATE_PAUSED,
            ],
            limit=1000,
        ):
            params = dict(job.get("params") or {})
            if str(params.get("source") or "").strip() != "reactions_yaml":
                continue
            reaction_id = str(params.get("reaction_id") or "").strip()
            operation_id = str(params.get("operation_id") or job.get("kind") or "").strip()
            if not reaction_id or not operation_id:
                continue
            candidates.append(job)
        newest_by_lane: dict[tuple[str, str, str], dict[str, Any]] = {}
        for job in candidates:
            params = dict(job.get("params") or {})
            key = (
                str(params.get("reaction_id") or "").strip(),
                str(params.get("operation_id") or job.get("kind") or "").strip(),
                str(job.get("provider") or "local").strip(),
            )
            current = newest_by_lane.get(key)
            if current is None or str(job.get("created_at") or "") > str(current.get("created_at") or ""):
                newest_by_lane[key] = job
        count = 0
        newest_ids = {str(job.get("id") or "") for job in newest_by_lane.values()}
        for job in candidates:
            job_id = str(job.get("id") or "")
            if not job_id or job_id in newest_ids:
                continue
            summary = dict(job.get("summary") or {})
            store.update_job(
                self.conn,
                job_id,
                state=store.JOB_STATE_COMPLETED,
                claim_owner=None,
                claim_expires_at=None,
                last_error="retired superseded queued reaction job",
                summary={
                    **summary,
                    "retired_reason": "superseded_by_newer_reaction_signal",
                    "retired_at": _utc_now(),
                },
            )
            count += 1
        return count

    def poll_running_jobs(self) -> dict[str, int]:
        completed = 0
        retried = 0
        failed = 0
        for job_id, info in list(self.processes.items()):
            proc = info["proc"]
            returncode = proc.poll()
            if returncode is None:
                store.update_job(
                    self.conn,
                    job_id,
                    claim_expires_at=store.bump_claim_expiry(scheduler.claim_ttl_seconds(self.conn)),
                )
                continue
            info["handle"].close()
            prepared = info["prepared"]
            log_path = info["log_path"]
            log_text = _tail_text(log_path)
            operation_payload = parse_operation_output_payload(log_text)
            artifact_refs = artifact_refs_from_operation_payload(operation_payload)
            operation_fields = operation_event_fields_from_operation_payload(operation_payload)
            run_summary = {
                "operation_id": prepared.operation.get("operation_id"),
                "resolved_parameters": prepared.resolved_parameters,
                "artifact_refs": artifact_refs,
                "operation_fields": operation_fields,
                "pid": proc.pid,
            }
            store.complete_run(
                self.conn,
                info["run_id"],
                returncode=int(returncode),
                summary=run_summary,
            )
            meta_run_id = info.get("meta_mission_run_id")
            if meta_run_id:
                finalize_meta_mission_run(
                    self.repo_root,
                    prepared=prepared,
                    run_id=meta_run_id,
                    status="completed" if returncode == 0 else "failed",
                    error=None if returncode == 0 else log_text[-400:],
                    artifact_refs=artifact_refs,
                    extra={"returncode": returncode, **operation_fields},
                )
            provider = str(info["job"].get("provider") or "local")
            if returncode == 0:
                scheduler.mark_completed(self.conn, job_id)
                store.enqueue_event(
                    self.conn,
                    source="metabolismd",
                    kind="operation_completed",
                    payload={
                        "job_id": job_id,
                        "run_id": info["run_id"],
                        "operation_id": prepared.operation.get("operation_id"),
                        "resolved_parameters": prepared.resolved_parameters,
                        "returncode": returncode,
                        "artifact_refs": artifact_refs,
                        **operation_fields,
                    },
                    stable_digest=policy.stable_digest(
                        {
                            "job_id": job_id,
                            "run_id": info["run_id"],
                            "returncode": returncode,
                        }
                    ),
                )
                completed += 1
            else:
                if self._looks_like_provider_interrupt(provider, log_text):
                    delay = self._provider_backoff_seconds(provider)
                    scheduler.schedule_retry(
                        self.conn,
                        job_id,
                        delay_seconds=delay,
                        error=f"provider interrupt: {prepared.operation.get('operation_id')}",
                        provider=provider,
                    )
                    metabolism_hooks.emit_provider_interrupt(
                        self.repo_root,
                        provider=provider,
                        reason=f"{prepared.operation.get('operation_id')} interrupted",
                        cooldown_seconds=delay,
                        payload={
                            "job_id": job_id,
                            "returncode": returncode,
                        },
                    )
                    retried += 1
                else:
                    scheduler.mark_failed(
                        self.conn,
                        job_id,
                        error=f"{prepared.operation.get('operation_id')} failed with {returncode}",
                    )
                    failed += 1
            del self.processes[job_id]
        return {"completed": completed, "retried": retried, "failed": failed}

    def dispatch_jobs(
        self,
        *,
        ignore_pause: bool = False,
        only_ids: set[str] | None = None,
        only_kinds: set[str] | None = None,
    ) -> dict[str, Any]:
        ready_jobs, blocked_reasons = scheduler.claimable_jobs(
            self.conn,
            ignore_pause=ignore_pause,
            only_ids=only_ids,
            only_kinds=only_kinds,
        )
        launched = 0
        for job in ready_jobs:
            claimed = scheduler.claim_job(self.conn, job["id"], owner=self.owner)
            try:
                self._launch_job(claimed)
            except Exception as exc:
                scheduler.mark_failed(self.conn, claimed["id"], error=str(exc))
            else:
                launched += 1
        return {"launched": launched, "blocked_reasons": blocked_reasons}

    def _pause_reason(self, *, ignore_pause: bool = False) -> str | None:
        if ignore_pause:
            return None
        paused, reason = scheduler.is_paused(self.conn)
        return str(reason or "paused") if paused else None

    def _manual_pause_remaining_seconds(self) -> float | None:
        pause_state = store.get_setting(self.conn, "pause", {}) or {}
        if not isinstance(pause_state, Mapping) or not bool(pause_state.get("paused")):
            return None
        paused_until = _parse_dt(pause_state.get("paused_until"))
        if paused_until is None:
            return None
        return max((paused_until - datetime.now(timezone.utc)).total_seconds(), 0.0)

    def _paused_tick_result(self, *, paused_reason: str, do_scan: bool) -> dict[str, Any]:
        self.enter_phase(LOOP_PHASE_POLL)
        poll_summary = self.poll_running_jobs()
        selector_summary = _selector_tick_skipped_report(paused_reason)
        store.set_setting(self.conn, SELECTOR_TICK_SETTING_KEY, selector_summary)
        self.enter_phase(LOOP_PHASE_PROJECT)
        status = self.write_projections(blocked_reasons={"global": paused_reason})
        skipped = {"skipped": "paused", "reason": paused_reason}
        return {
            "watch_events": dict(skipped),
            "retired_legacy_raw_seed_jobs": 0,
            "retired_superseded_reaction_jobs": 0,
            "reclaimed": 0,
            "ingested": dict(skipped),
            "market": dict(skipped),
            "scan": {**skipped, "requested": bool(do_scan), "file_events": 0, "runtime_events": 0, "inserted": 0},
            "events": {"queued_jobs": 0, **skipped},
            "selector_tick": selector_summary,
            "poll": poll_summary,
            "dispatch": {"launched": 0, "blocked_reasons": {"global": paused_reason}},
            "status": status,
        }

    def build_status_snapshot(
        self,
        *,
        blocked_reasons: Mapping[str, str] | None = None,
        board: Mapping[str, Any] | None = None,
        live_heartbeat: Mapping[str, Any] | None = None,
        market: Mapping[str, Any] | None = None,
        intake: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        live_heartbeat_row = dict(
            live_heartbeat
            or _live_daemon_heartbeat(self.conn)
            or _latest_alive_daemon_heartbeat(self.conn)
            or {}
        )
        market = dict(
            market
            or market_clock.build_market_projection(
                self.conn,
                daemon_running=bool(live_heartbeat_row),
            )
        )
        intake = dict(intake or self.raw_seed_intake.write_projection())
        board = dict(
            board
            or blackboard.build_blackboard_projection(
                self.conn,
                market=market,
                raw_seed_intake=intake,
                type_a_recovery=_safe_type_a_recovery_summary(),
            )
        )
        daemon_payload = dict(live_heartbeat_row.get("payload") or {})
        ready_jobs, ready_reasons = scheduler.claimable_jobs(self.conn)
        if ready_jobs and not board.get("paused"):
            idle_reason = f"{len(ready_jobs)} ready job(s) queued"
        else:
            idle_reason = scheduler.explain_idle_reason(self.conn, blocked_reasons or ready_reasons or {})
        if not live_heartbeat_row and ready_jobs and not board.get("paused"):
            idle_reason = f"daemon not running; {len(ready_jobs)} ready job(s) queued"
        queue_liveness = build_queue_liveness_report(self.conn, live_heartbeat=live_heartbeat_row)

        ticks = _read_runtime_ticks(self.repo_root)
        current_phase = str(ticks.get("current_phase") or LOOP_PHASE_STARTUP)
        loop_tick_at = ticks.get("loop_tick_at")
        last_job_poll_at = ticks.get("last_job_poll_at")
        last_child_reap_at = ticks.get("last_child_reap_at")
        last_scan_at = ticks.get("last_scan_at")
        next_scan_at = ticks.get("next_scan_at")
        active_children = (
            int(ticks.get("active_children"))
            if isinstance(ticks.get("active_children"), (int, float))
            else len(self.processes)
        )

        running_jobs_list = board.get("running_jobs") or []
        waiting_jobs_list = board.get("waiting_jobs") or []
        recoverable_jobs_list = store.fetch_jobs(
            self.conn, states=[store.JOB_STATE_RECOVERABLE]
        )
        event_backlog = store.count_unprocessed_events(self.conn)
        claim_ttl = int(scheduler.claim_ttl_seconds(self.conn))
        now_dt = datetime.now(timezone.utc)
        oldest_running_job_age_seconds: float | None = None
        for job in running_jobs_list:
            claim_expires = _parse_dt(job.get("claim_expires_at"))
            updated_at_dt = _parse_dt(job.get("updated_at"))
            if claim_expires is not None:
                # claim_expires_at = claim_start + claim_ttl; age = now - claim_start.
                age = (now_dt - claim_expires).total_seconds() + claim_ttl
            elif updated_at_dt is not None:
                # Blackboard projections strip claim_expires_at. updated_at is the
                # last mutation timestamp, which for state=running equals the claim
                # start — age is simply the elapsed time since.
                age = (now_dt - updated_at_dt).total_seconds()
            else:
                continue
            if oldest_running_job_age_seconds is None or age > oldest_running_job_age_seconds:
                oldest_running_job_age_seconds = max(age, 0.0)

        health_reasons: list[str] = []
        daemon_health = DAEMON_HEALTH_NOT_RUNNING
        if not live_heartbeat_row:
            daemon_health = DAEMON_HEALTH_NOT_RUNNING
            health_reasons.append("no_live_daemon_heartbeat")
        else:
            loop_stale = _tick_is_stale(
                loop_tick_at, now=now_dt, threshold_seconds=LOOP_TICK_STALE_AFTER_SECONDS
            )
            poll_stale = _tick_is_stale(
                last_job_poll_at, now=now_dt, threshold_seconds=JOB_POLL_STALE_AFTER_SECONDS
            )
            reap_stale = _tick_is_stale(
                last_child_reap_at, now=now_dt, threshold_seconds=CHILD_REAP_STALE_AFTER_SECONDS
            )
            if loop_stale or poll_stale or reap_stale:
                daemon_health = DAEMON_HEALTH_STALLED
                if loop_stale:
                    health_reasons.append("loop_tick_stale")
                if poll_stale:
                    health_reasons.append("job_poll_stale")
                if reap_stale:
                    health_reasons.append("child_reap_stale")
            elif (
                oldest_running_job_age_seconds is not None
                and oldest_running_job_age_seconds > claim_ttl
            ):
                daemon_health = DAEMON_HEALTH_DEGRADED
                health_reasons.append("oldest_running_job_beyond_claim_ttl")
            elif queue_liveness.get("orphaned_jobs"):
                daemon_health = DAEMON_HEALTH_DEGRADED
                health_reasons.append("orphaned_active_jobs_present")
            elif queue_liveness.get("ambiguous_active_jobs"):
                daemon_health = DAEMON_HEALTH_DEGRADED
                health_reasons.append("ambiguous_active_jobs_present")
            else:
                daemon_health = DAEMON_HEALTH_HEALTHY

        selector_tick = store.get_setting(self.conn, SELECTOR_TICK_SETTING_KEY, {}) or {}
        if not isinstance(selector_tick, Mapping):
            selector_tick = {}
        selector_snapshot = selector_tick.get("selector_snapshot") if isinstance(selector_tick, Mapping) else {}
        if not isinstance(selector_snapshot, Mapping):
            selector_snapshot = {}
        if board.get("paused"):
            selector_tick = _selector_tick_skipped_report(str(board.get("pause_reason") or "paused"))
            selector_snapshot = selector_tick.get("selector_snapshot") or {}
        elif not selector_snapshot:
            try:
                selector_snapshot = _compact_selector_snapshot(
                    scheduler.build_selector_snapshot(
                        self.conn,
                        repo_root=self.repo_root,
                        limit=20,
                        candidate_feed=provider_signal.derive_candidate_job_feed(
                            self.repo_root,
                            source="all",
                            limit=20,
                        ),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - status must not fail on selector projection.
                selector_snapshot = {
                    "schema_version": provider_signal.SELECTOR_SNAPSHOT_SCHEMA_VERSION,
                    "kind": provider_signal.SELECTOR_SNAPSHOT_KIND,
                    "error": f"{type(exc).__name__}: {exc}",
                }

        launch_contract_status = _safe_launchable_operation_contract_status(self.repo_root)

        return {
            "schema": STATUS_SCHEMA,
            "compat": {"previous": STATUS_SCHEMA_PREVIOUS},
            "generated_at": _utc_now(),
            "daemon": {
                "process_name": PROCESS_NAME,
                "running": bool(live_heartbeat_row),
                "pid": live_heartbeat_row.get("pid") if live_heartbeat_row else None,
                "owner": daemon_payload.get("owner") if live_heartbeat_row else None,
                "started_at": live_heartbeat_row.get("started_at") if live_heartbeat_row else None,
                "heartbeat": live_heartbeat_row or None,
                "health": daemon_health,
                "health_reasons": list(health_reasons),
                "current_phase": current_phase,
                "loop_tick_at": loop_tick_at,
                "last_job_poll_at": last_job_poll_at,
                "last_child_reap_at": last_child_reap_at,
                "last_scan_at": last_scan_at,
                "next_scan_at": next_scan_at,
                "active_children": active_children,
                "oldest_running_job_age_seconds": oldest_running_job_age_seconds,
                "claim_ttl_seconds": claim_ttl,
            },
            "daemon_health": daemon_health,
            "health_reasons": list(health_reasons),
            "current_phase": current_phase,
            "loop_tick_at": loop_tick_at,
            "last_job_poll_at": last_job_poll_at,
            "last_child_reap_at": last_child_reap_at,
            "last_scan_at": last_scan_at,
            "next_scan_at": next_scan_at,
            "active_children": active_children,
            "oldest_running_job_age_seconds": oldest_running_job_age_seconds,
            "claim_ttl_seconds": claim_ttl,
            "event_backlog": event_backlog,
            "waiting_jobs": len(waiting_jobs_list),
            "recoverable_jobs": len(recoverable_jobs_list),
            "paused": board.get("paused"),
            "pause_reason": board.get("pause_reason"),
            "idle_reason": idle_reason,
            "counts": {
                "unprocessed_events": event_backlog,
                "running_jobs": len(running_jobs_list),
                "waiting_jobs": len(waiting_jobs_list),
                "active_agents": len(board.get("active_agents") or []),
                "active_provider_claims": sum(
                    int(row.get("active_runtime_claim_count") or 0)
                    for row in (board.get("provider_pressure") or [])
                ),
                "collisions": len(board.get("collisions") or []),
                "raw_seed_active_sessions": len((intake or {}).get("active_draft_sessions") or []),
            },
            "running_jobs": running_jobs_list,
            "waiting_jobs": waiting_jobs_list,
            "provider_pressure": board.get("provider_pressure") or [],
            "provider_cooldowns": board.get("provider_cooldowns") or [],
            "active_agents": board.get("active_agents") or [],
            "latest_changed_substrate": board.get("latest_changed_substrate") or [],
            "collisions": board.get("collisions") or [],
            "blocked_reasons": dict(blocked_reasons or {}),
            "queue_liveness": queue_liveness,
            "governor": governor.build_status(self.conn),
            "market": market,
            "raw_seed_intake": intake,
            "selector_snapshot": dict(selector_snapshot),
            "selector_tick": dict(selector_tick),
            "skip_receipt_count": int((selector_tick.get("receipt_summary") or {}).get("skip_receipts_written") or 0)
            + int((selector_tick.get("receipt_summary") or {}).get("skip_receipts_deduped") or 0),
            "last_selector_tick_at": selector_tick.get("generated_at"),
            "selected_candidate_id": selector_tick.get("selected_candidate_id"),
            "selected_action_status": selector_tick.get("selected_action_status"),
            "receipt_summary": selector_tick.get("receipt_summary") or {},
            "launchable_operation_contracts": launch_contract_status,
        }

    def write_projections(self, *, blocked_reasons: Mapping[str, str] | None = None) -> dict[str, Any]:
        self.touch_heartbeat()
        live_heartbeat = _live_daemon_heartbeat(self.conn) or _latest_alive_daemon_heartbeat(self.conn)
        market = market_clock.build_market_projection(
            self.conn,
            daemon_running=live_heartbeat is not None,
        )
        self.touch_heartbeat()
        intake = self.raw_seed_intake.write_projection()
        self.touch_heartbeat()
        board = blackboard.build_blackboard_projection(
            self.conn,
            market=market,
            raw_seed_intake=intake,
            type_a_recovery=_safe_type_a_recovery_summary(),
        )
        self.touch_heartbeat()
        status = self.build_status_snapshot(
            blocked_reasons=blocked_reasons,
            board=board,
            live_heartbeat=live_heartbeat,
            market=market,
            intake=intake,
        )
        self.touch_heartbeat()
        _atomic_write(
            self.paths.blackboard_json,
            json.dumps(board, indent=2, ensure_ascii=False) + "\n",
        )
        _atomic_write(self.paths.blackboard_md, blackboard.render_blackboard_markdown(board))
        _atomic_write(
            self.paths.status_json,
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        )
        return status

    def check_market_clock(self) -> dict[str, Any]:
        try:
            emitted = market_clock.compute_and_emit_fires(self.conn)
        except Exception as exc:
            return {"emitted": 0, "error": f"{type(exc).__name__}: {exc}"}
        return {
            "emitted": len(emitted),
            "fire_points": [
                dict(event.get("payload") or {}) for event in emitted
            ],
        }

    def process_once(
        self,
        *,
        do_scan: bool = False,
        allow_dispatch: bool = True,
        ignore_pause: bool = False,
        only_ids: set[str] | None = None,
        only_kinds: set[str] | None = None,
    ) -> dict[str, Any]:
        self.enter_phase(LOOP_PHASE_REAP)
        self.touch_heartbeat()
        paused_reason = self._pause_reason(ignore_pause=ignore_pause)
        if paused_reason:
            return self._paused_tick_result(paused_reason=paused_reason, do_scan=do_scan)
        watch_events = self.ingest_raw_seed_watch_events()
        retired = self.retire_legacy_raw_seed_auto_jobs()
        retired_reaction_jobs = self.retire_superseded_reaction_jobs()
        reclaimed = scheduler.maybe_requeue_expired(self.conn)
        ingested = self.ingest_inbox()
        self.enter_phase(LOOP_PHASE_POLL)
        poll_summary = self.poll_running_jobs()
        market_summary = self.check_market_clock()
        self.enter_phase(LOOP_PHASE_DISPATCH)
        early_dispatch_summary = (
            self.dispatch_jobs(
                ignore_pause=ignore_pause,
                only_ids=only_ids,
                only_kinds=only_kinds,
            )
            if allow_dispatch
            else {"launched": 0, "blocked_reasons": {}}
        )
        self.touch_heartbeat()
        if do_scan:
            self.enter_phase(LOOP_PHASE_SCAN)
        scan_summary = self.scan() if do_scan else {"file_events": 0, "runtime_events": 0, "inserted": 0}
        if do_scan:
            self.last_scan_monotonic = time.monotonic()
        self.touch_heartbeat()
        self.enter_phase(LOOP_PHASE_APPLY_POLICIES)
        event_summary = self._apply_event_policies()
        self.enter_phase(LOOP_PHASE_DISPATCH)
        late_dispatch_summary = (
            self.dispatch_jobs(
                ignore_pause=ignore_pause,
                only_ids=only_ids,
                only_kinds=only_kinds,
            )
            if allow_dispatch
            else {"launched": 0, "blocked_reasons": {}}
        )
        dispatch_summary = {
            "launched": int(early_dispatch_summary.get("launched") or 0)
            + int(late_dispatch_summary.get("launched") or 0),
            "blocked_reasons": {
                **dict(early_dispatch_summary.get("blocked_reasons") or {}),
                **dict(late_dispatch_summary.get("blocked_reasons") or {}),
            },
            "early_launched": int(early_dispatch_summary.get("launched") or 0),
            "late_launched": int(late_dispatch_summary.get("launched") or 0),
        }
        self.touch_heartbeat()
        selector_allowed, selector_block_reason = governor.dispatch_enabled(self.conn)
        if selector_allowed or ignore_pause:
            try:
                selector_summary = run_selector_tick(
                    self.conn,
                    self.repo_root,
                    apply=True,
                    limit=20,
                    receipt_limit=5,
                )
            except Exception as exc:  # noqa: BLE001 - selector observability must not stop the daemon loop.
                selector_summary = {
                    "schema_version": SELECTOR_TICK_SCHEMA,
                    "kind": SELECTOR_TICK_KIND,
                    "generated_at": _utc_now(),
                    "selected_action_status": "selector_tick_error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
                store.set_setting(self.conn, SELECTOR_TICK_SETTING_KEY, selector_summary)
        else:
            selector_summary = _selector_tick_skipped_report(selector_block_reason)
            store.set_setting(self.conn, SELECTOR_TICK_SETTING_KEY, selector_summary)
        self.touch_heartbeat()
        self.enter_phase(LOOP_PHASE_PROJECT)
        status = self.write_projections(blocked_reasons=dispatch_summary.get("blocked_reasons") or {})
        return {
            "watch_events": watch_events,
            "retired_legacy_raw_seed_jobs": retired,
            "retired_superseded_reaction_jobs": retired_reaction_jobs,
            "reclaimed": reclaimed,
            "ingested": ingested,
            "market": market_summary,
            "scan": scan_summary,
            "events": event_summary,
            "selector_tick": selector_summary,
            "poll": poll_summary,
            "dispatch": dispatch_summary,
            "status": status,
        }

    def process_scoped_once(
        self,
        *,
        ignore_pause: bool = False,
        only_ids: set[str] | None = None,
        only_kinds: set[str] | None = None,
    ) -> dict[str, Any]:
        self.enter_phase(LOOP_PHASE_REAP)
        self.touch_heartbeat()
        reclaimed = scheduler.maybe_requeue_expired(self.conn)
        self.enter_phase(LOOP_PHASE_POLL)
        poll_summary = self.poll_running_jobs()
        self.enter_phase(LOOP_PHASE_DISPATCH)
        dispatch_summary = self.dispatch_jobs(
            ignore_pause=ignore_pause,
            only_ids=only_ids,
            only_kinds=only_kinds,
        )
        self.enter_phase(LOOP_PHASE_PROJECT)
        status = self.write_projections(blocked_reasons=dispatch_summary.get("blocked_reasons") or {})
        return {
            "watch_events": {"skipped": "scoped_once"},
            "retired_legacy_raw_seed_jobs": 0,
            "reclaimed": reclaimed,
            "ingested": {"skipped": "scoped_once"},
            "market": {"emitted": 0, "skipped": "scoped_once"},
            "scan": {"file_events": 0, "runtime_events": 0, "inserted": 0, "skipped": "scoped_once"},
            "events": {"queued_jobs": 0, "skipped": "scoped_once"},
            "poll": poll_summary,
            "dispatch": dispatch_summary,
            "status": status,
        }

    def next_wake_seconds(self, *, default_poll_seconds: float, scan_interval_seconds: float) -> float:
        paused_reason = self._pause_reason()
        if paused_reason:
            remaining = self._manual_pause_remaining_seconds()
            if remaining is not None:
                return max(min(max(remaining, default_poll_seconds), 60.0), 1.0)
            return max(float(default_poll_seconds), 30.0)
        candidates = [max(default_poll_seconds, 0.25)]
        next_due = self.raw_seed_intake.next_due_in_seconds()
        if next_due is not None:
            candidates.append(max(min(next_due, default_poll_seconds), 0.25))
        if self.last_scan_monotonic is not None:
            elapsed = time.monotonic() - self.last_scan_monotonic
            until_scan = max(scan_interval_seconds - elapsed, 0.0)
            candidates.append(max(min(until_scan, default_poll_seconds), 0.25))
        return max(min(candidates), 0.25)


def _runtime(*, enable_watchers: bool = False, runtime_mode: str = "observer") -> MetabolismRuntime:
    """Return a MetabolismRuntime. Default is observer mode — only ``cmd_run``
    is allowed to construct a resident daemon runtime.

    Observer mode disables heartbeat writes and phase-tick persistence so
    side-channel commands (status, doctor, jobs, blackboard, market, governor,
    repair, maintenance, scan, enqueue, pause, resume, raw_seed_*) cannot
    masquerade as a live daemon.
    """
    return MetabolismRuntime(
        REPO_ROOT,
        enable_watchers=enable_watchers,
        runtime_mode=runtime_mode,
    )


def cmd_run(args: argparse.Namespace) -> int:
    ignore_pause = bool(getattr(args, "ignore_pause", False))
    if ignore_pause and not args.once:
        raise SystemExit("--ignore-pause is only supported with --once")
    require_dispatch = bool(getattr(args, "require_dispatch", False))
    if require_dispatch and not args.once:
        raise SystemExit("--require-dispatch is only supported with --once")
    only_ids = {
        str(value).strip()
        for value in (getattr(args, "job_id", None) or [])
        if str(value).strip()
    }
    only_kinds = {
        str(value).strip()
        for value in (getattr(args, "only_kind", None) or [])
        if str(value).strip()
    }
    if (only_ids or only_kinds) and not args.once:
        raise SystemExit("--job-id/--only-kind are only supported with --once")
    if not args.once and not bool(getattr(args, "allow_duplicate_daemon", False)):
        guard_conn = store.connect(REPO_ROOT)
        try:
            guard = build_daemon_start_guard_report(guard_conn)
        finally:
            guard_conn.close()
        if not guard.get("ok"):
            print(json.dumps(guard, indent=2, ensure_ascii=False))
            return 4
    runtime = _runtime(
        enable_watchers=not bool(args.once),
        runtime_mode="once" if args.once else "daemon",
    )
    try:
        runtime.start_background_heartbeat()
        # pri_119: cold-start reconciliation. Daemon boot only — scoped
        # `--once` drains skip this so they cannot mutate sibling-owned
        # claims. Reconciler is read+safe-repair-bounded; never scans,
        # dispatches, or calls providers. Failures here MUST NOT crash
        # the boot path: catch broadly and continue.
        if not args.once and not scheduler.is_paused(runtime.conn)[0]:
            try:
                run_reconciliation_pass(
                    runtime.conn,
                    repo_root=runtime.repo_root,
                    scope="boot",
                    runtime_owner=runtime.owner,
                    apply_safe_repairs=True,
                )
            except Exception as exc:  # noqa: BLE001 - reconciliation must not abort boot
                store.enqueue_event(
                    runtime.conn,
                    source="metabolism_reconciliation",
                    kind="metabolism_reconciliation_boot_error_v1",
                    payload={
                        "runtime_owner": runtime.owner,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                    stable_digest=f"reconciliation_boot_error:{runtime.owner}:{int(time.time())}",
                )
        scheduler_settings = governor.effective_scheduler_settings(runtime.conn)
        interval = float(args.poll_seconds or scheduler_settings.get("poll_seconds") or 10)
        scan_interval = float(scheduler_settings.get("scan_interval_seconds") or 60)
        once_drain_timeout = float(getattr(args, "once_drain_timeout_seconds", 1800) or 1800)
        scoped_once = bool(args.once and (only_ids or only_kinds))
        do_scan = False
        if not scoped_once:
            runtime.last_scan_monotonic = time.monotonic()
        while True:
            if (
                not scoped_once
                and runtime.last_scan_monotonic is not None
                and (time.monotonic() - runtime.last_scan_monotonic) >= scan_interval
            ):
                do_scan = True
            if scoped_once:
                tick_result = runtime.process_scoped_once(
                    ignore_pause=ignore_pause,
                    only_ids=only_ids,
                    only_kinds=only_kinds,
                )
            else:
                tick_result = runtime.process_once(
                    do_scan=do_scan,
                    ignore_pause=ignore_pause,
                    only_ids=only_ids,
                    only_kinds=only_kinds,
                )
            do_scan = False
            if args.once:
                deadline = time.monotonic() + max(once_drain_timeout, 1.0)
                while runtime.processes:
                    runtime.poll_running_jobs()
                    runtime.write_projections()
                    if not runtime.processes:
                        break
                    if time.monotonic() >= deadline:
                        for job_id, info in list(runtime.processes.items()):
                            process = info.get("proc")
                            if process and process.poll() is None:
                                process.terminate()
                            scheduler.schedule_retry(
                                runtime.conn,
                                job_id,
                                delay_seconds=60,
                                error="run --once drain timeout; job terminated for retry",
                                provider=str(info.get("job", {}).get("provider") or "local"),
                            )
                            del runtime.processes[job_id]
                        runtime.write_projections()
                        return 2
                    time.sleep(1.0)
                if (
                    scoped_once
                    and require_dispatch
                    and int((tick_result.get("dispatch") or {}).get("launched") or 0) == 0
                ):
                    return 3
                return 0
            wake_seconds = runtime.next_wake_seconds(
                default_poll_seconds=interval,
                scan_interval_seconds=scan_interval,
            )
            next_scan_dt: str | None = None
            if runtime.last_scan_monotonic is not None:
                seconds_until_scan = max(
                    scan_interval - (time.monotonic() - runtime.last_scan_monotonic),
                    0.0,
                )
                next_scan_dt = (
                    datetime.now(timezone.utc) + timedelta(seconds=seconds_until_scan)
                ).isoformat()
            runtime.enter_phase(LOOP_PHASE_SLEEP, next_scan_at=next_scan_dt)
            time.sleep(wake_seconds)
    finally:
        runtime.enter_phase(LOOP_PHASE_SHUTDOWN)
        runtime.close()


def cmd_status(args: argparse.Namespace) -> int:
    runtime = _runtime(runtime_mode="observer")
    try:
        status = runtime.write_projections()
        if args.json:
            print(json.dumps(status, indent=2, ensure_ascii=False))
            return 0
        print(f"metabolismd: {status['idle_reason']}")
        print(f"running_jobs: {status['counts']['running_jobs']}")
        print(f"waiting_jobs: {status['counts']['waiting_jobs']}")
        print(f"active_agents: {status['counts']['active_agents']}")
        print(f"active_provider_claims: {status['counts']['active_provider_claims']}")
        queue_liveness = status.get("queue_liveness") or {}
        if queue_liveness:
            print(
                f"queue_liveness: {queue_liveness.get('status')} "
                f"orphaned={len(queue_liveness.get('orphaned_jobs') or [])}"
            )
        intake = status.get("raw_seed_intake") or {}
        print(f"raw_seed_intake: {intake.get('watcher_mode') or 'unknown'} active={len(intake.get('active_draft_sessions') or [])}")
        market = status.get("market") or {}
        next_fire = market.get("next_fire")
        if next_fire:
            print(
                f"market_next_fire: {next_fire.get('fire_point') or next_fire.get('name')} at {next_fire.get('target_time_market')}"
            )
        if market.get("nothing_ran_reason"):
            print(f"market_reason: {market['nothing_ran_reason']}")
        provider_pressure = status.get("provider_pressure") or []
        if provider_pressure:
            first = next(
                (
                    row
                    for row in provider_pressure
                    if row.get("blocked") or row.get("active_runtime_claim_count")
                ),
                provider_pressure[0],
            )
            summary = str(first.get("reason") or "").strip()
            if not summary:
                summary = f"load {first.get('active_total')}/{first.get('max_concurrent')}"
            print(f"provider_pressure: {first['provider']} {summary}")
        if status.get("provider_cooldowns"):
            first = status["provider_cooldowns"][0]
            print(f"provider_cooldown: {first['provider']} until {first['cooldown_until']}")
        selector_snapshot = status.get("selector_snapshot") or {}
        if selector_snapshot:
            print(
                "selector: "
                f"candidates={selector_snapshot.get('candidate_count', 0)} "
                f"claimable={selector_snapshot.get('claimable_count', 0)} "
                f"why={selector_snapshot.get('why_nothing_ran') or 'unknown'}"
            )
        selector_tick = status.get("selector_tick") or {}
        if selector_tick:
            print(
                "selector_tick: "
                f"action={selector_tick.get('selected_action') or 'none'} "
                f"status={selector_tick.get('selected_action_status') or 'unknown'}"
            )
        launch_contract_status = status.get("launchable_operation_contracts") or {}
        if launch_contract_status:
            print(
                "launch_contracts: "
                f"posture={launch_contract_status.get('posture') or 'unknown'} "
                f"blockers={launch_contract_status.get('missing_landing_contract_blocker_count', 0)} "
                f"metabolismd_blockers="
                f"{(launch_contract_status.get('metabolismd_owned_automatic_contracts') or {}).get('blocking_count', 0)}"
            )
        return 0
    finally:
        runtime.close()


def cmd_scan(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        result = runtime.process_once(do_scan=True, allow_dispatch=False)
        print(json.dumps(result["scan"], indent=2, ensure_ascii=False))
        return 0
    finally:
        runtime.close()


def cmd_selector_tick(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        report = run_selector_tick(
            runtime.conn,
            runtime.repo_root,
            apply=bool(args.apply),
            limit=int(args.limit),
            receipt_limit=int(args.receipt_limit),
        )
        if bool(args.apply):
            runtime.write_projections()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            action = report.get("selected_action") or "none"
            status = report.get("selected_action_status") or "unknown"
            print(
                f"selector_tick: candidates={report.get('candidate_count', 0)} "
                f"claimable={report.get('claimable_count', 0)} action={action} status={status}"
            )
            if report.get("why_nothing_ran"):
                print(f"why_nothing_ran: {report['why_nothing_ran']}")
        return 0
    finally:
        runtime.close()


def cmd_enqueue(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(args.payload_json) if args.payload_json else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --payload-json: {exc}")
    if not isinstance(payload, dict):
        raise SystemExit("--payload-json must decode to an object")
    event = metabolism_hooks.emit_event(
        REPO_ROOT,
        source=args.source,
        kind=args.kind,
        payload=payload,
        stable_fields={
            "source": args.source,
            "kind": args.kind,
            "payload": payload,
        },
    )
    print(json.dumps(event, indent=2, ensure_ascii=False))
    return 0


def _provider_for_enqueued_operation(
    *,
    operation_id: str,
    parameters: Mapping[str, Any],
    explicit_provider: str | None = None,
) -> str:
    requested = str(explicit_provider or "").strip()
    if requested:
        return requested
    if operation_id == "provider_transform_job":
        provider_id = str(parameters.get("provider_id") or "auto").strip()
        if provider_id == "nvidia_nim":
            return "nvidia"
        return "openrouter_free"
    provider = str(parameters.get("provider") or "").strip()
    return provider or "local"


def cmd_enqueue_job(args: argparse.Namespace) -> int:
    try:
        parameters = json.loads(args.parameters_json) if args.parameters_json else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --parameters-json: {exc}")
    if not isinstance(parameters, dict):
        raise SystemExit("--parameters-json must decode to an object")

    operation_id = str(args.operation_id or "").strip()
    if not operation_id:
        raise SystemExit("operation_id is required")

    provider = _provider_for_enqueued_operation(
        operation_id=operation_id,
        parameters=parameters,
        explicit_provider=args.provider,
    )
    prepared = prepare_launch_operation(
        REPO_ROOT,
        operation_id=operation_id,
        parameters=parameters,
    )
    idempotency_key = str(args.idempotency_key or "").strip()
    if not idempotency_key:
        idempotency_key = f"manual_job:{policy.stable_digest({'operation_id': operation_id, 'provider': provider, 'parameters': parameters})}"

    runtime = _runtime()
    try:
        row, created = store.create_job(
            runtime.conn,
            kind=operation_id,
            provider=provider,
            params={
                "operation_id": operation_id,
                "operation_parameters": parameters,
                "source": "metabolismd_cli",
            },
            idempotency_key=idempotency_key,
            priority=int(args.priority),
            not_before=args.not_before,
            summary={
                "source": "metabolismd_cli",
                "operation_id": operation_id,
                "provider": provider,
                "resolved_parameters": prepared.resolved_parameters,
            },
        )
        payload = {
            "schema": "metabolism_enqueue_job_v1",
            "created": created,
            "job": row,
            "prepared": {
                "operation_id": operation_id,
                "provider": provider,
                "command": prepared.command,
                "resolved_parameters": prepared.resolved_parameters,
            },
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            state = row.get("state") if row else "unknown"
            action = "queued" if created else "existing"
            print(f"{action}: {row.get('id') if row else '<none>'} {state} {operation_id} ({provider})")
        runtime.write_projections()
        return 0
    finally:
        runtime.close()


def cmd_jobs(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        states = args.states.split(",") if args.states else None
        jobs = store.fetch_jobs(runtime.conn, states=states, limit=args.limit)
        if args.json:
            print(json.dumps(jobs, indent=2, ensure_ascii=False))
            return 0
        for job in jobs:
            print(f"{job['id']} {job['state']} {job['kind']} ({job['provider']})")
        return 0
    finally:
        runtime.close()


def cmd_blackboard(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        live_heartbeat = _live_daemon_heartbeat(runtime.conn)
        market = market_clock.build_market_projection(
            runtime.conn,
            daemon_running=live_heartbeat is not None,
        )
        board = blackboard.build_blackboard_projection(
            runtime.conn,
            market=market,
            raw_seed_intake=runtime.raw_seed_intake.write_projection(),
            type_a_recovery=_safe_type_a_recovery_summary(),
        )
        if args.json:
            print(json.dumps(board, indent=2, ensure_ascii=False))
            return 0
        print(blackboard.render_blackboard_markdown(board), end="")
        return 0
    finally:
        runtime.close()


def cmd_pause(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        until = args.until
        if not until and args.for_seconds:
            until = (store.now_dt() + timedelta(seconds=int(args.for_seconds))).isoformat()
        scheduler.set_pause(runtime.conn, paused=True, until=until, reason=args.reason or "manual pause")
        runtime.write_projections()
        return 0
    finally:
        runtime.close()


def cmd_resume(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        scheduler.set_pause(runtime.conn, paused=False, until=None, reason=None)
        runtime.write_projections()
        return 0
    finally:
        runtime.close()


def cmd_repair(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        payload = repair_orphaned_active_jobs(runtime.conn, live=bool(args.live))
        runtime.write_projections()
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        mode = "live" if args.live else "dry-run"
        print(f"repair_mode: {mode}")
        print(f"candidate_count: {payload['candidate_count']}")
        print(f"repaired_count: {payload['repaired_count']}")
        after = payload.get("after") or {}
        print(f"queue_liveness: {after.get('status')}")
        if not args.live and payload["candidate_count"]:
            print("apply: ./repo-python -m tools.meta.control.metabolismd repair --live")
        return 0
    finally:
        runtime.close()


def cmd_reconcile(args: argparse.Namespace) -> int:
    """pri_119: cold-start reconciliation pass — read+repair-bounded.

    Runs the same reconciliation pass that fires at metabolismd boot.
    Without --live: dry-run (no mutations, no event emission). With
    --live: delegates safe orphan recovery to the existing repair
    primitive AND emits one typed metabolism_reconciliation_v1 event
    for audit. Never scans, never dispatches, never calls providers.
    """
    runtime = _runtime()
    try:
        snapshot = run_reconciliation_pass(
            runtime.conn,
            repo_root=runtime.repo_root,
            scope="manual",
            runtime_owner=runtime.owner,
            apply_safe_repairs=bool(args.live),
            log_freshness_threshold_seconds=getattr(args, "log_freshness_seconds", None),
            emit_event=bool(args.live),
        )
        payload = snapshot.to_dict()
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        mode = "live" if args.live else "dry-run"
        summary = payload.get("summary") or {}
        print(f"reconcile_mode: {mode}")
        print(f"healthy: {summary.get('healthy')}")
        print(f"finding_count: {summary.get('finding_count')}")
        sev = summary.get("severity_counts") or {}
        print(
            f"severity: info={sev.get('info', 0)} "
            f"warning={sev.get('warning', 0)} error={sev.get('error', 0)}"
        )
        rule_counts = summary.get("rule_counts") or {}
        for rule, count in sorted(rule_counts.items()):
            print(f"  {rule}: {count}")
        mutations = payload.get("mutations") or {}
        print(
            f"mutations_applied: {mutations.get('applied')} "
            f"repaired={mutations.get('repaired_count', 0)}"
        )
        if not args.live and summary.get("finding_count"):
            print("apply: ./repo-python -m tools.meta.control.metabolismd reconcile --live")
        return 0
    finally:
        runtime.close()


def _state_filter_from_args(args: argparse.Namespace) -> set[str] | None:
    if bool(getattr(args, "all_states", False)):
        return None
    raw = str(getattr(args, "states", "") or "").strip()
    if not raw:
        return {store.JOB_STATE_QUEUED, store.JOB_STATE_RECOVERABLE, store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING}
    return {token.strip() for token in raw.split(",") if token.strip()}


def compact_reaction_job_payloads(
    conn,
    *,
    states: set[str] | None = None,
    live: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    sql = "SELECT id, state, params_json, summary_json FROM jobs WHERE params_json LIKE ? ORDER BY created_at ASC"
    params: list[Any] = ['%"source": "reactions_yaml"%']
    if limit is not None and int(limit) > 0:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    scanned = 0
    changed = 0
    bytes_before = 0
    bytes_after = 0
    samples: list[dict[str, Any]] = []
    for row in rows:
        state = str(row["state"] or "")
        if states is not None and state not in states:
            continue
        scanned += 1
        raw_params = str(row["params_json"] or "{}")
        raw_summary = str(row["summary_json"] or "{}")
        job_params = store.json_loads(raw_params, {})
        if not isinstance(job_params, dict) or job_params.get("source") != "reactions_yaml":
            continue
        signal = job_params.pop("signal", None)
        if isinstance(signal, Mapping):
            job_params["signal_excerpt"] = policy.compact_reaction_signal(signal)
        if "signal" not in raw_params and not isinstance(signal, Mapping):
            continue
        summary = store.json_loads(raw_summary, {})
        if not isinstance(summary, dict):
            summary = {}
        if isinstance(job_params.get("signal_excerpt"), Mapping):
            summary["signal_excerpt"] = dict(job_params["signal_excerpt"])
        next_params = store.json_dumps(job_params)
        next_summary = store.json_dumps(summary)
        if next_params == raw_params and next_summary == raw_summary:
            continue
        before = len(raw_params.encode("utf-8")) + len(raw_summary.encode("utf-8"))
        after = len(next_params.encode("utf-8")) + len(next_summary.encode("utf-8"))
        bytes_before += before
        bytes_after += after
        changed += 1
        if len(samples) < 12:
            samples.append(
                {
                    "id": row["id"],
                    "state": state,
                    "bytes_before": before,
                    "bytes_after": after,
                    "saved_bytes": max(before - after, 0),
                }
            )
        if live:
            conn.execute(
                """
                UPDATE jobs
                SET params_json = ?, summary_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_params, next_summary, _utc_now(), row["id"]),
            )
    return {
        "schema": "metabolism_reaction_job_compaction_v1",
        "generated_at": _utc_now(),
        "live": bool(live),
        "states": sorted(states) if states is not None else "all",
        "scanned_rows": scanned,
        "changed_rows": changed,
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "saved_bytes": max(bytes_before - bytes_after, 0),
        "samples": samples,
    }


def _path_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _wal_path_for_db(db_path: Path) -> Path:
    return db_path.with_name(f"{db_path.name}-wal")


def _shm_path_for_db(db_path: Path) -> Path:
    return db_path.with_name(f"{db_path.name}-shm")


DB_COMPACTION_FREELIST_BYTES_THRESHOLD = 512_000_000
DB_COMPACTION_FREELIST_RATIO_THRESHOLD = 0.10
DB_COMPACTION_FREE_DISK_MULTIPLIER = 2.0
DB_COMPACTION_DEFAULT_DBSTAT_TIMEOUT_SECONDS = 20.0
EVENTS_RETENTION_TABLE_BLOAT_BYTES = 1_000_000_000
EVENTS_RETENTION_DEFAULT_QUERY_TIMEOUT_SECONDS = 3.0
EVENTS_RETENTION_DEFAULT_SAMPLE_LIMIT = 1_000
EVENTS_RETENTION_DEFAULT_PAYLOAD_SAMPLE_LIMIT = 100
EVENTS_RETENTION_OVERSIZED_PAYLOAD_BYTES = 1_000_000
LEGACY_EVENT_PAYLOAD_ARCHIVE_SCHEMA = "metabolism_legacy_event_payload_archive_v1"
LEGACY_EVENT_PAYLOAD_ARCHIVE_RECORD_SCHEMA = "metabolism_legacy_event_payload_archive_record_v1"
ARCHIVED_EVENT_PAYLOAD_REF_SCHEMA = "archived_event_payload_ref_v1"
LEGACY_EVENT_PAYLOAD_ARCHIVE_SOURCE = "runtime_scan"
LEGACY_EVENT_PAYLOAD_ARCHIVE_KIND = "work_ledger_signal"
LEGACY_EVENT_PAYLOAD_ARCHIVE_REL_DIR = Path("state/metabolism/archive/events")
LEGACY_EVENT_PAYLOAD_ARCHIVE_DEFAULT_CHUNK_SIZE = 100
LEGACY_EVENT_PAYLOAD_ARCHIVE_DEFAULT_MAX_CANDIDATES = 100

EVENT_CONSUMERS: tuple[dict[str, str], ...] = (
    {
        "surface": "system/lib/metabolism_store.py::fetch_unprocessed_events",
        "role": "hot operational queue reader over unprocessed events",
        "query_shape": "WHERE processed_at IS NULL ORDER BY id ASC LIMIT ?",
    },
    {
        "surface": "system/lib/metabolism_store.py::count_unprocessed_events",
        "role": "daemon/status event backlog counter",
        "query_shape": "COUNT WHERE processed_at IS NULL",
    },
    {
        "surface": "tools/meta/control/metabolismd.py::MetabolismRuntime._apply_event_policies",
        "role": "job derivation and event processing loop",
        "query_shape": "fetch unprocessed events, derive jobs, mark processed",
    },
    {
        "surface": "tools/meta/control/metabolismd.py::MetabolismRuntime.scan",
        "role": "file/runtime scan event producer",
        "query_shape": "INSERT OR IGNORE events via stable_digest",
    },
    {
        "surface": "tools/meta/control/metabolismd.py::MetabolismRuntime.ingest_raw_seed_watch_events",
        "role": "raw-seed watcher event producer",
        "query_shape": "INSERT OR IGNORE raw_seed_edit_observed events",
    },
    {
        "surface": "tools/meta/control/metabolismd.py::MetabolismRuntime.poll_running_jobs",
        "role": "operation_completed event producer",
        "query_shape": "INSERT OR IGNORE operation completion events",
    },
    {
        "surface": "system/lib/metabolism_hooks.py",
        "role": "hook-originated event producer",
        "query_shape": "INSERT OR IGNORE events through store.enqueue_event",
    },
    {
        "surface": "system/lib/metabolism_market_clock.py",
        "role": "market event producer",
        "query_shape": "INSERT OR IGNORE market_snapshot/feed events",
    },
)


def _relative_or_absolute(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read_json_mapping(path: Path, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
    try:
        if not path.exists() or path.stat().st_size > max_bytes:
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _pragma_scalar(conn, name: str) -> Any:
    row = conn.execute(f"PRAGMA {name}").fetchone()
    if row is None:
        return None
    return row[0]


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _float_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _open_handle_summary(db_path: Path, *, timeout_seconds: float = 3.0) -> dict[str, Any]:
    lsof_path = shutil.which("lsof")
    if not lsof_path:
        return {"status": "unavailable", "reason": "lsof_not_found", "rows": []}
    try:
        completed = subprocess.run(
            [lsof_path, "-nP", str(db_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "rows": []}
    except OSError as exc:
        return {"status": "error", "error": str(exc), "rows": []}
    rows: list[dict[str, Any]] = []
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("COMMAND "):
            continue
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue
        rows.append(
            {
                "command": parts[0],
                "pid": _int_or_zero(parts[1]),
                "fd": parts[3],
                "type": parts[4],
                "name": parts[8],
            }
        )
    status = "ok" if completed.returncode in {0, 1} else "error"
    payload: dict[str, Any] = {
        "status": status,
        "open_handle_count": len(rows),
        "rows": rows[:20],
        "truncated": len(rows) > 20,
    }
    if completed.returncode not in {0, 1}:
        payload["error"] = (completed.stderr or "").strip()[:500]
    return payload


def _largest_db_objects(
    conn,
    *,
    limit: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.perf_counter()

    def progress_handler() -> int:
        return 1 if time.perf_counter() - started > timeout_seconds else 0

    try:
        conn.set_progress_handler(progress_handler, 10_000)
        rows = conn.execute(
            """
            SELECT
                name,
                count(*) AS pages,
                sum(pgsize) AS bytes,
                sum(unused) AS unused_bytes
            FROM dbstat
            GROUP BY name
            ORDER BY bytes DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        status = "ok"
        error = None
    except sqlite3.OperationalError as exc:
        rows = []
        message = str(exc)
        status = "timeout" if "interrupted" in message.lower() else "unavailable"
        error = message
    finally:
        conn.set_progress_handler(None, 0)
    payload: dict[str, Any] = {
        "status": status,
        "wall_seconds": round(time.perf_counter() - started, 6),
        "rows": [
            {
                "name": str(row["name"]),
                "pages": _int_or_zero(row["pages"]),
                "bytes": _int_or_zero(row["bytes"]),
                "unused_bytes": _int_or_zero(row["unused_bytes"]),
            }
            for row in rows
        ],
    }
    if error:
        payload["error"] = error[:500]
    return payload


def _skipped_largest_db_objects(
    reason: str,
    *,
    dbstat_limit: int,
    dbstat_timeout_seconds: float,
) -> dict[str, Any]:
    return {
        "status": "skipped",
        "wall_seconds": 0.0,
        "rows": [],
        "reason": reason,
        "dbstat_limit": max(int(dbstat_limit), 0),
        "dbstat_timeout_seconds": max(float(dbstat_timeout_seconds), 0.0),
    }


def classify_db_compaction_eligibility(
    *,
    db_bytes: int,
    page_size: int,
    page_count: int,
    freelist_count: int,
    active_job_count: int,
    running_job_count: int,
    free_disk_bytes: int,
    largest_db_objects: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    estimated_freelist_bytes = max(page_size, 0) * max(freelist_count, 0)
    freelist_ratio = _float_ratio(freelist_count, page_count)
    vacuum_required = int(db_bytes * DB_COMPACTION_FREE_DISK_MULTIPLIER)
    reasons: list[str] = []

    if db_bytes <= 0:
        reasons.append("db_missing_or_empty")
        return {"eligible": False, "recommended_action": "no_op", "reasons": reasons}

    if active_job_count > 0 or running_job_count > 0:
        reasons.append("claimed_or_running_jobs_present")
        deferred_signal = _db_compaction_deferred_signal(
            db_bytes=db_bytes,
            estimated_freelist_bytes=estimated_freelist_bytes,
            freelist_ratio=freelist_ratio,
            free_disk_bytes=free_disk_bytes,
            vacuum_required=vacuum_required,
            active_job_count=active_job_count,
            running_job_count=running_job_count,
        )
        if deferred_signal.get("freelist_large"):
            reasons.append("reclaimable_freelist_deferred_by_active_jobs")
        reasons.extend(str(reason) for reason in deferred_signal.get("blocking_reasons_if_jobs_clear", []))
        return {
            "eligible": False,
            "recommended_action": "wait_for_low_traffic_window",
            "reasons": reasons,
            "deferred_compaction_signal": deferred_signal,
        }

    if free_disk_bytes < vacuum_required:
        reasons.append("insufficient_free_disk_for_normal_vacuum")
        if estimated_freelist_bytes >= DB_COMPACTION_FREELIST_BYTES_THRESHOLD:
            reasons.append("freelist_large_but_disk_headroom_insufficient")
        return {
            "eligible": False,
            "recommended_action": "no_op",
            "reasons": reasons,
        }

    freelist_large = estimated_freelist_bytes >= DB_COMPACTION_FREELIST_BYTES_THRESHOLD
    freelist_ratio_large = freelist_ratio >= DB_COMPACTION_FREELIST_RATIO_THRESHOLD
    if freelist_large and freelist_ratio_large:
        reasons.append("freelist_reclaimable_space_exceeds_threshold")
        return {
            "eligible": True,
            "recommended_action": "low_traffic_vacuum",
            "reasons": reasons,
        }

    if freelist_large:
        reasons.append("freelist_bytes_large_but_ratio_below_threshold")
        return {
            "eligible": True,
            "recommended_action": "vacuum_into_candidate",
            "reasons": reasons,
        }

    if db_bytes >= 1_000_000_000:
        reasons.append("db_large_but_freelist_below_compaction_threshold")
        if largest_db_objects:
            dominant = max(largest_db_objects, key=lambda row: _int_or_zero(row.get("bytes")))
            dominant_bytes = _int_or_zero(dominant.get("bytes"))
            if dominant_bytes > 0:
                reasons.append(f"dominant_object:{dominant.get('name')}:{dominant_bytes}")
        return {
            "eligible": False,
            "recommended_action": "retention_first",
            "reasons": reasons,
        }

    reasons.append("db_size_below_bloat_threshold")
    return {"eligible": False, "recommended_action": "no_op", "reasons": reasons}


def _db_compaction_deferred_signal(
    *,
    db_bytes: int,
    estimated_freelist_bytes: int,
    freelist_ratio: float,
    free_disk_bytes: int,
    vacuum_required: int,
    active_job_count: int,
    running_job_count: int,
) -> dict[str, Any]:
    freelist_large = estimated_freelist_bytes >= DB_COMPACTION_FREELIST_BYTES_THRESHOLD
    freelist_ratio_large = freelist_ratio >= DB_COMPACTION_FREELIST_RATIO_THRESHOLD
    disk_headroom_ok = free_disk_bytes >= vacuum_required
    blocking_reasons: list[str] = []
    if not disk_headroom_ok:
        blocking_reasons.append("insufficient_free_disk_for_normal_vacuum")
    if not freelist_large and db_bytes >= 1_000_000_000:
        blocking_reasons.append("freelist_below_compaction_threshold")

    if disk_headroom_ok and freelist_large and freelist_ratio_large:
        deferred_action = "low_traffic_vacuum"
    elif disk_headroom_ok and freelist_large:
        deferred_action = "vacuum_into_candidate"
    elif freelist_large:
        deferred_action = "wait_for_disk_headroom"
    elif db_bytes >= 1_000_000_000:
        deferred_action = "retention_first"
    else:
        deferred_action = "no_op"

    if freelist_large and not disk_headroom_ok:
        status = "reclaimable_space_blocked_by_active_jobs_and_disk_headroom"
    elif freelist_large:
        status = "reclaimable_space_blocked_by_active_jobs"
    else:
        status = "active_jobs_block_compaction_check"
    return {
        "status": status,
        "active_job_count": max(active_job_count, 0),
        "running_job_count": max(running_job_count, 0),
        "estimated_freelist_bytes": max(estimated_freelist_bytes, 0),
        "freelist_ratio": freelist_ratio,
        "freelist_large": freelist_large,
        "freelist_ratio_large": freelist_ratio_large,
        "free_disk_bytes": max(free_disk_bytes, 0),
        "vacuum_free_disk_required_estimate": max(vacuum_required, 0),
        "would_be_eligible_without_active_jobs": bool(disk_headroom_ok and freelist_large),
        "deferred_recommended_action": deferred_action,
        "blocking_reasons_if_jobs_clear": blocking_reasons,
    }


def build_db_compaction_eligibility_report(
    conn,
    *,
    paths: store.MetabolismPaths,
    repo_root: Path = REPO_ROOT,
    dbstat_limit: int = 12,
    dbstat_timeout_seconds: float = DB_COMPACTION_DEFAULT_DBSTAT_TIMEOUT_SECONDS,
    include_dbstat: bool = False,
) -> dict[str, Any]:
    db_path = paths.db
    wal_path = _wal_path_for_db(db_path)
    shm_path = _shm_path_for_db(db_path)
    active = store.fetch_jobs(
        conn,
        states=[store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING],
    )
    running_job_count = len([job for job in active if job.get("state") == store.JOB_STATE_RUNNING])
    page_size = _int_or_zero(_pragma_scalar(conn, "page_size"))
    page_count = _int_or_zero(_pragma_scalar(conn, "page_count"))
    freelist_count = _int_or_zero(_pragma_scalar(conn, "freelist_count"))
    journal_mode = str(_pragma_scalar(conn, "journal_mode") or "")
    auto_vacuum = _int_or_zero(_pragma_scalar(conn, "auto_vacuum"))
    db_bytes = _path_size(db_path)
    wal_bytes = _path_size(wal_path)
    shm_bytes = _path_size(shm_path)
    disk_usage = shutil.disk_usage(db_path.parent)
    classification = classify_db_compaction_eligibility(
        db_bytes=db_bytes,
        page_size=page_size,
        page_count=page_count,
        freelist_count=freelist_count,
        active_job_count=len(active),
        running_job_count=running_job_count,
        free_disk_bytes=int(disk_usage.free),
    )
    should_collect_dbstat = bool(include_dbstat) or (
        classification.get("recommended_action") == "retention_first"
    )
    if int(dbstat_limit) <= 0:
        should_collect_dbstat = False
        skip_reason = "dbstat_limit_zero"
    else:
        skip_reason = "classification_decided_without_dbstat"
    if should_collect_dbstat:
        largest_objects_payload = _largest_db_objects(
            conn,
            limit=max(int(dbstat_limit), 0),
            timeout_seconds=max(float(dbstat_timeout_seconds), 0.5),
        )
        largest_objects = [
            row for row in largest_objects_payload.get("rows", []) if isinstance(row, Mapping)
        ]
        classification = classify_db_compaction_eligibility(
            db_bytes=db_bytes,
            page_size=page_size,
            page_count=page_count,
            freelist_count=freelist_count,
            active_job_count=len(active),
            running_job_count=running_job_count,
            free_disk_bytes=int(disk_usage.free),
            largest_db_objects=largest_objects,
        )
    else:
        largest_objects_payload = _skipped_largest_db_objects(
            skip_reason,
            dbstat_limit=dbstat_limit,
            dbstat_timeout_seconds=dbstat_timeout_seconds,
        )
    status_payload = _read_json_mapping(paths.status_json)
    queue_liveness = status_payload.get("queue_liveness") if isinstance(status_payload, Mapping) else {}
    if not isinstance(queue_liveness, Mapping):
        queue_liveness = {}
    estimated_freelist_bytes = page_size * freelist_count
    vacuum_required = int(db_bytes * DB_COMPACTION_FREE_DISK_MULTIPLIER)
    payload = {
        "schema": "metabolism_db_compaction_eligibility_v1",
        "generated_at": _utc_now(),
        "live": False,
        "db_path": _relative_or_absolute(db_path, repo_root),
        "wal_path": _relative_or_absolute(wal_path, repo_root),
        "shm_path": _relative_or_absolute(shm_path, repo_root),
        "db_bytes": db_bytes,
        "wal_bytes": wal_bytes,
        "shm_bytes": shm_bytes,
        "journal_mode": journal_mode,
        "auto_vacuum": auto_vacuum,
        "page_size": page_size,
        "page_count": page_count,
        "freelist_count": freelist_count,
        "estimated_freelist_bytes": estimated_freelist_bytes,
        "freelist_ratio": _float_ratio(freelist_count, page_count),
        "active_job_count": len(active),
        "running_job_count": running_job_count,
        "daemon_health": status_payload.get("daemon_health"),
        "daemon_heartbeat_stalled": bool(queue_liveness.get("daemon_heartbeat_stalled", False)),
        "free_disk_bytes": int(disk_usage.free),
        "vacuum_free_disk_required_estimate": vacuum_required,
        "vacuum_into_free_disk_required_estimate": db_bytes + wal_bytes + shm_bytes,
        "open_handle_summary": _open_handle_summary(db_path),
        "largest_db_objects": largest_objects_payload,
        "dbstat_collection": {
            "mode": "always" if include_dbstat else "auto",
            "collected": largest_objects_payload.get("status") != "skipped",
            "reason": largest_objects_payload.get("reason"),
            "force_flag": "--include-dbstat",
        },
        "eligible": bool(classification.get("eligible")),
        "recommended_action": str(classification.get("recommended_action") or "no_op"),
        "reasons": list(classification.get("reasons") or []),
        "safety_boundary": {
            "dry_run_only": True,
            "does_not_vacuum": True,
            "does_not_delete_rows": True,
            "normal_vacuum_free_disk_multiplier": DB_COMPACTION_FREE_DISK_MULTIPLIER,
        },
    }
    deferred_signal = classification.get("deferred_compaction_signal")
    if isinstance(deferred_signal, Mapping):
        payload["deferred_compaction_signal"] = dict(deferred_signal)
    return payload


def _query_rows_with_timeout(
    conn,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.perf_counter()

    def progress_handler() -> int:
        return 1 if time.perf_counter() - started > timeout_seconds else 0

    try:
        conn.set_progress_handler(progress_handler, 10_000)
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        status = "ok"
        error = None
    except sqlite3.OperationalError as exc:
        rows = []
        message = str(exc)
        status = "timeout" if "interrupted" in message.lower() else "unavailable"
        error = message
    finally:
        conn.set_progress_handler(None, 0)
    payload: dict[str, Any] = {
        "status": status,
        "wall_seconds": round(time.perf_counter() - started, 6),
        "rows": rows,
    }
    if error:
        payload["error"] = error[:500]
    return payload


def _first_row(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows")
    if isinstance(rows, list) and rows and isinstance(rows[0], Mapping):
        return dict(rows[0])
    return {}


def _events_dbstat_payload(
    conn,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    return _query_rows_with_timeout(
        conn,
        """
        SELECT
            name,
            count(*) AS pages,
            sum(pgsize) AS bytes,
            sum(unused) AS unused_bytes
        FROM dbstat
        WHERE name = 'events'
        GROUP BY name
        """,
        timeout_seconds=timeout_seconds,
    )


def _event_index_rows(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT name, sql
        FROM sqlite_schema
        WHERE type = 'index' AND tbl_name = 'events'
        ORDER BY name
        """
    ).fetchall()
    return [{"name": str(row["name"]), "sql": row["sql"]} for row in rows]


def _event_authority_classes() -> list[dict[str, Any]]:
    return [
        {
            "class_id": "operational_queue",
            "selector": "processed_at IS NULL",
            "authority": "live daemon work queue",
            "retention_posture": "never_archive_until_processed",
        },
        {
            "class_id": "processed_job_derivation_history",
            "selector": "processed_at IS NOT NULL and source/kind derive jobs or operation completions",
            "authority": "audit/replay history for daemon decisions",
            "retention_posture": "archive_policy_required_before_delete",
        },
        {
            "class_id": "runtime_diagnostic_history",
            "selector": "file/runtime scan, hook, provider, and observer-derived events",
            "authority": "diagnostic history with likely cold-retention boundary",
            "retention_posture": "candidate_for_cold_archive_after_consumer_mapping",
        },
        {
            "class_id": "raw_seed_watch_history",
            "selector": "kind = raw_seed_edit_observed",
            "authority": "raw-seed intake evidence; source voice remains in raw seed, not this table",
            "retention_posture": "archive_policy_possible_after synced/session projections are verified",
        },
        {
            "class_id": "market_history",
            "selector": "market snapshot/feed events",
            "authority": "market daemon operational history",
            "retention_posture": "archive_policy_possible with market timeline/status owner checks",
        },
    ]


def classify_events_retention_eligibility(
    *,
    row_count: int,
    unprocessed_count: int,
    events_table_bytes: int,
    dominant_source_kind: Mapping[str, Any] | None = None,
    oversized_payload_classes: list[Mapping[str, Any]] | None = None,
    timed_out_surfaces: list[str] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    timed_out = list(timed_out_surfaces or [])
    oversized_classes = list(oversized_payload_classes or [])
    if row_count <= 0:
        if timed_out:
            reasons.append("one_or_more_report_queries_timed_out")
            return {
                "eligible": False,
                "recommended_action": "query_budget_first",
                "reasons": [*reasons, *[f"timed_out:{surface}" for surface in timed_out]],
            }
        return {"eligible": False, "recommended_action": "no_op", "reasons": ["events_table_empty"]}
    if unprocessed_count > 0:
        reasons.append("unprocessed_operational_queue_rows_present")
        return {
            "eligible": False,
            "recommended_action": "query_budget_first",
            "reasons": reasons,
        }
    if timed_out:
        reasons.append("one_or_more_report_queries_timed_out")
    if events_table_bytes >= EVENTS_RETENTION_TABLE_BLOAT_BYTES:
        reasons.append("events_table_large_processed_history")
        if oversized_classes:
            first_oversized = oversized_classes[0]
            reasons.append(
                "oversized_payload_source_kind:"
                f"{first_oversized.get('source')}:{first_oversized.get('kind')}:"
                f"{_int_or_zero(first_oversized.get('max_payload_json_bytes'))}"
            )
        if dominant_source_kind:
            source = dominant_source_kind.get("source")
            kind = dominant_source_kind.get("kind")
            payload_bytes = _int_or_zero(dominant_source_kind.get("payload_json_bytes"))
            row_count = _int_or_zero(dominant_source_kind.get("row_count"))
            if payload_bytes:
                reasons.append(f"dominant_source_kind:{source}:{kind}:{payload_bytes}")
            else:
                reasons.append(f"dominant_source_kind_rows:{source}:{kind}:{row_count}")
        return {
            "eligible": False,
            "recommended_action": "retention_policy_needed",
            "reasons": [*reasons, *[f"timed_out:{surface}" for surface in timed_out]],
        }
    if timed_out:
        return {
            "eligible": False,
            "recommended_action": "query_budget_first",
            "reasons": [*reasons, *[f"timed_out:{surface}" for surface in timed_out]],
        }
    reasons.append("events_table_below_bloat_threshold")
    return {"eligible": False, "recommended_action": "no_op", "reasons": reasons}


def _events_retention_policy_next_actions(
    *,
    recommended_action: str,
    payload_governance_action: str,
    timed_out_surfaces: Sequence[str] | None = None,
) -> dict[str, Any]:
    timed_out = [str(surface) for surface in (timed_out_surfaces or []) if surface]
    commands: list[dict[str, str]] = []
    deferred_commands: list[dict[str, str]] = []
    legacy_archive_probe = {
        "action_id": "legacy_event_payload_archive_dry_run",
        "command": (
            "./repo-python -m tools.meta.control.metabolismd "
            "maintenance legacy-event-payload-archive --json"
        ),
        "why": (
            "Find processed legacy work_ledger_signal payloads eligible "
            "for archive-replace without row deletion or vacuum."
        ),
    }
    db_compaction_recheck = {
        "action_id": "db_compaction_eligibility_after_policy_probe",
        "command": (
            "./repo-python -m tools.meta.control.metabolismd "
            "maintenance db-compaction-eligibility --json"
        ),
        "why": (
            "Re-check compaction blockers after any owner-approved "
            "payload archive or low-traffic window."
        ),
    }
    status = "no_action_required"
    if recommended_action == "retention_policy_needed":
        status = "policy_probe_recommended"
        commands.extend([legacy_archive_probe, db_compaction_recheck])
        if payload_governance_action == "event_payload_governance_needed":
            commands.insert(
                1,
                {
                    "action_id": "map_recent_oversized_payload_class",
                    "command": (
                        "./repo-python -m tools.meta.control.metabolismd "
                        "maintenance events-retention-eligibility --json"
                    ),
                    "why": (
                        "Use the oversized source/kind class as the policy seed "
                        "before any live retention mutation."
                    ),
                },
            )
    elif recommended_action == "query_budget_first":
        status = "query_budget_or_queue_blocked"
        commands.append(
            {
                "action_id": "rerun_with_bounded_query_budget",
                "command": (
                    "./repo-python -m tools.meta.control.metabolismd "
                    "maintenance events-retention-eligibility --json"
                ),
                "why": "Clear report timeouts or unprocessed queue evidence before retention policy work.",
            }
        )
        deferred_commands.extend(
            [
                {
                    **legacy_archive_probe,
                    "action_id": "legacy_event_payload_archive_dry_run_after_queue_clears",
                    "why": (
                        "After the unprocessed queue or timeout blocker clears, probe older "
                        "processed legacy payloads that the recent sample can miss."
                    ),
                },
                {
                    **db_compaction_recheck,
                    "action_id": "db_compaction_eligibility_after_queue_clears",
                    "why": "Re-check compaction only after queue/query blockers clear.",
                },
            ]
        )
    return {
        "status": status,
        "dry_run_first": True,
        "commands": commands,
        "deferred_commands": deferred_commands,
        "timed_out_surfaces": timed_out,
        "sample_scope_note": (
            "recent sample only; older legacy payloads require the archive dry-run probe"
        ),
        "live_mutation_guards": {
            "legacy_payload_archive_live": (
                "requires no claimed/running jobs unless --allow-active explicit recovery"
            ),
            "vacuum_live": (
                "requires db-compaction-eligibility to clear active-job and disk-headroom blockers"
            ),
        },
        "blocked_mutations_without_policy": [
            {
                "mutation": "delete_or_archive_events_table_rows",
                "reason": "consumer mapping and authority-class retention policy not decided here",
            },
            {
                "mutation": "vacuum_or_wal_checkpoint",
                "reason": "owned by db-compaction-eligibility/wal-checkpoint surfaces",
            },
        ],
    }


def _oversized_payload_classes(
    rows: list[Mapping[str, Any]],
    *,
    threshold_bytes: int = EVENTS_RETENTION_OVERSIZED_PAYLOAD_BYTES,
) -> list[dict[str, Any]]:
    classes: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        payload_bytes = _int_or_zero(row.get("payload_json_bytes"))
        if payload_bytes < threshold_bytes:
            continue
        key = (str(row.get("source") or ""), str(row.get("kind") or ""))
        bucket = classes.setdefault(
            key,
            {
                "source": key[0],
                "kind": key[1],
                "sampled_oversized_row_count": 0,
                "processed_oversized_row_count": 0,
                "sample_payload_json_bytes": 0,
                "max_payload_json_bytes": 0,
                "latest_created_at": None,
                "sample_row_ids": [],
            },
        )
        bucket["sampled_oversized_row_count"] += 1
        bucket["processed_oversized_row_count"] += 1 if bool(row.get("processed")) else 0
        bucket["sample_payload_json_bytes"] += payload_bytes
        bucket["max_payload_json_bytes"] = max(
            _int_or_zero(bucket.get("max_payload_json_bytes")),
            payload_bytes,
        )
        created_at = str(row.get("created_at") or "")
        if created_at and (not bucket.get("latest_created_at") or created_at > str(bucket.get("latest_created_at"))):
            bucket["latest_created_at"] = created_at
        if len(bucket["sample_row_ids"]) < 8:
            bucket["sample_row_ids"].append(row.get("id"))
    return sorted(
        classes.values(),
        key=lambda item: (
            -_int_or_zero(item.get("sample_payload_json_bytes")),
            str(item.get("source")),
            str(item.get("kind")),
        ),
    )


def _event_scalar_query(
    conn,
    sql: str,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    payload = _query_rows_with_timeout(conn, sql, timeout_seconds=timeout_seconds)
    row = _first_row(payload)
    return {
        "status": payload.get("status"),
        "wall_seconds": payload.get("wall_seconds"),
        "row": row,
        **({"error": payload["error"]} if payload.get("error") else {}),
    }


def _events_row_summary_payload(
    conn,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    queries = {
        "rowid_high_water": _event_scalar_query(
            conn,
            "SELECT max(id) AS rowid_high_water FROM events",
            timeout_seconds=timeout_seconds,
        ),
        "oldest_created_at": _event_scalar_query(
            conn,
            "SELECT created_at AS oldest_created_at FROM events ORDER BY id ASC LIMIT 1",
            timeout_seconds=timeout_seconds,
        ),
        "newest_created_at": _event_scalar_query(
            conn,
            "SELECT created_at AS newest_created_at FROM events ORDER BY id DESC LIMIT 1",
            timeout_seconds=timeout_seconds,
        ),
        "unprocessed_count": _event_scalar_query(
            conn,
            "SELECT count(*) AS unprocessed_count FROM events WHERE processed_at IS NULL",
            timeout_seconds=timeout_seconds,
        ),
    }
    statuses = [str(payload.get("status") or "missing") for payload in queries.values()]
    status = "ok" if all(item == "ok" for item in statuses) else "partial"
    if any(item == "timeout" for item in statuses):
        status = "timeout"
    rowid_high_water = _int_or_zero(queries["rowid_high_water"].get("row", {}).get("rowid_high_water"))
    unprocessed_count = _int_or_zero(queries["unprocessed_count"].get("row", {}).get("unprocessed_count"))
    row = {
        "row_count": None,
        "row_count_basis": "not_counted_to_avoid_full_table_scan",
        "rowid_high_water": rowid_high_water,
        "estimated_row_count": rowid_high_water,
        "oldest_created_at": queries["oldest_created_at"].get("row", {}).get("oldest_created_at"),
        "newest_created_at": queries["newest_created_at"].get("row", {}).get("newest_created_at"),
        "unprocessed_count": unprocessed_count,
        "processed_count": max(rowid_high_water - unprocessed_count, 0) if rowid_high_water else None,
    }
    return {
        "status": status,
        "wall_seconds": round(
            sum(float(payload.get("wall_seconds") or 0.0) for payload in queries.values()),
            6,
        ),
        "rows": [row],
        "subqueries": queries,
    }


def build_events_retention_eligibility_report(
    conn,
    *,
    paths: store.MetabolismPaths,
    repo_root: Path = REPO_ROOT,
    sample_limit: int = EVENTS_RETENTION_DEFAULT_SAMPLE_LIMIT,
    payload_sample_limit: int = EVENTS_RETENTION_DEFAULT_PAYLOAD_SAMPLE_LIMIT,
    query_timeout_seconds: float = EVENTS_RETENTION_DEFAULT_QUERY_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    sample_limit = max(int(sample_limit), 1)
    payload_sample_limit = min(max(int(payload_sample_limit), 1), sample_limit)
    query_timeout_seconds = max(float(query_timeout_seconds), 0.5)
    db_path = paths.db
    event_table_payload = _events_dbstat_payload(conn, timeout_seconds=query_timeout_seconds)
    event_table_stats = _first_row(event_table_payload)
    summary = _events_row_summary_payload(conn, timeout_seconds=query_timeout_seconds)
    summary_row = _first_row(summary)
    rowid_high_water = _int_or_zero(summary_row.get("rowid_high_water"))
    sample_lower_bound = max(rowid_high_water - sample_limit + 1, 0)
    by_source = _query_rows_with_timeout(
        conn,
        """
        SELECT
            source,
            count(*) AS row_count,
            min(created_at) AS oldest_created_at,
            max(created_at) AS newest_created_at
        FROM events
        WHERE id >= ?
        GROUP BY source
        ORDER BY row_count DESC
        LIMIT 20
        """,
        (sample_lower_bound,),
        timeout_seconds=query_timeout_seconds,
    )
    by_kind = _query_rows_with_timeout(
        conn,
        """
        SELECT
            kind,
            count(*) AS row_count,
            min(created_at) AS oldest_created_at,
            max(created_at) AS newest_created_at
        FROM events
        WHERE id >= ?
        GROUP BY kind
        ORDER BY row_count DESC
        LIMIT 20
        """,
        (sample_lower_bound,),
        timeout_seconds=query_timeout_seconds,
    )
    by_source_kind = _query_rows_with_timeout(
        conn,
        """
        SELECT
            source,
            kind,
            count(*) AS row_count,
            min(created_at) AS oldest_created_at,
            max(created_at) AS newest_created_at
        FROM events
        WHERE id >= ?
        GROUP BY source, kind
        ORDER BY row_count DESC
        LIMIT 25
        """,
        (sample_lower_bound,),
        timeout_seconds=query_timeout_seconds,
    )
    age_buckets = _query_rows_with_timeout(
        conn,
        """
        SELECT bucket, count(*) AS row_count
        FROM (
            SELECT
                CASE
                    WHEN created_at >= datetime('now', '-1 day') THEN 'lt_1d'
                    WHEN created_at >= datetime('now', '-7 day') THEN 'lt_7d'
                    WHEN created_at >= datetime('now', '-30 day') THEN 'lt_30d'
                    ELSE 'gte_30d'
                END AS bucket
            FROM events
            WHERE id >= ?
        )
        GROUP BY bucket
        ORDER BY CASE bucket
            WHEN 'lt_1d' THEN 1
            WHEN 'lt_7d' THEN 2
            WHEN 'lt_30d' THEN 3
            ELSE 4
        END
        """,
        (sample_lower_bound,),
        timeout_seconds=query_timeout_seconds,
    )
    payload_lower_bound = max(rowid_high_water - payload_sample_limit + 1, 0)
    largest_payload_sample = _query_rows_with_timeout(
        conn,
        """
        SELECT
            id,
            source,
            kind,
            length(payload_json) AS payload_json_bytes,
            created_at,
            processed_at IS NOT NULL AS processed
        FROM events
        WHERE id >= ?
        ORDER BY payload_json_bytes DESC
        LIMIT 20
        """,
        (payload_lower_bound,),
        timeout_seconds=query_timeout_seconds,
    )
    payload_summary = _query_rows_with_timeout(
        conn,
        """
        SELECT
            count(*) AS sampled_row_count,
            sum(length(payload_json)) AS payload_json_bytes,
            avg(length(payload_json)) AS avg_payload_json_bytes,
            max(length(payload_json)) AS max_payload_json_bytes
        FROM events
        WHERE id >= ?
        """,
        (payload_lower_bound,),
        timeout_seconds=query_timeout_seconds,
    )

    timed_out_surfaces = [
        name
        for name, payload in {
            "events_dbstat": event_table_payload,
            "summary": summary,
            "by_source": by_source,
            "by_kind": by_kind,
            "by_source_kind": by_source_kind,
            "age_buckets": age_buckets,
            "largest_payload_sample": largest_payload_sample,
            "payload_summary_sample": payload_summary,
        }.items()
        if payload.get("status") == "timeout"
    ]
    by_source_kind_rows = by_source_kind.get("rows") if isinstance(by_source_kind.get("rows"), list) else []
    dominant_source_kind = (
        dict(by_source_kind_rows[0])
        if by_source_kind_rows and isinstance(by_source_kind_rows[0], Mapping)
        else None
    )
    largest_payload_rows = (
        largest_payload_sample.get("rows") if isinstance(largest_payload_sample.get("rows"), list) else []
    )
    oversized_payload_classes = _oversized_payload_classes(
        [dict(row) for row in largest_payload_rows if isinstance(row, Mapping)]
    )
    classification = classify_events_retention_eligibility(
        row_count=_int_or_zero(summary_row.get("row_count") or summary_row.get("estimated_row_count")),
        unprocessed_count=_int_or_zero(summary_row.get("unprocessed_count")),
        events_table_bytes=_int_or_zero(event_table_stats.get("bytes"))
        or (_path_size(db_path) if event_table_payload.get("status") != "ok" else 0),
        dominant_source_kind=dominant_source_kind,
        oversized_payload_classes=oversized_payload_classes,
        timed_out_surfaces=timed_out_surfaces,
    )
    indexes = _event_index_rows(conn)
    stable_digest_unique = any(
        str(row.get("name") or "") == "sqlite_autoindex_events_1" for row in indexes
    )
    payload_governance_action = (
        "event_payload_governance_needed"
        if oversized_payload_classes
        else "no_oversized_payload_class_in_recent_sample"
    )
    return {
        "schema": "metabolism_events_retention_eligibility_v1",
        "generated_at": _utc_now(),
        "live": False,
        "db_path": _relative_or_absolute(db_path, repo_root),
        "events_table": {
            "dbstat": event_table_payload,
            "bytes": _int_or_zero(event_table_stats.get("bytes")),
            "db_bytes_context": _path_size(db_path),
            "unused_bytes": _int_or_zero(event_table_stats.get("unused_bytes")),
        },
        "row_summary": summary,
        "by_source": by_source,
        "by_kind": by_kind,
        "by_source_kind": by_source_kind,
        "age_buckets": age_buckets,
        "payload_size_sample": {
            "sample_limit": payload_sample_limit,
            "sample_lower_bound_id": payload_lower_bound,
            "summary": payload_summary,
            "largest_rows": largest_payload_sample,
        },
        "payload_governance": {
            "inline_threshold_bytes": EVENTS_RETENTION_OVERSIZED_PAYLOAD_BYTES,
            "oversized_source_kinds": oversized_payload_classes,
            "recommended_action": payload_governance_action,
        },
        "stable_digest_duplicate_summary": {
            "unique_index_enforced": stable_digest_unique,
            "duplicate_count": 0 if stable_digest_unique else None,
            "source": "sqlite UNIQUE constraint on events.stable_digest",
        },
        "existing_indexes": indexes,
        "hot_consumers": list(EVENT_CONSUMERS),
        "authority_classes": _event_authority_classes(),
        "eligible": bool(classification.get("eligible")),
        "recommended_action": str(classification.get("recommended_action") or "no_op"),
        "reasons": list(classification.get("reasons") or []),
        "retention_policy_next_actions": _events_retention_policy_next_actions(
            recommended_action=str(classification.get("recommended_action") or "no_op"),
            payload_governance_action=payload_governance_action,
            timed_out_surfaces=timed_out_surfaces,
        ),
        "safety_boundary": {
            "dry_run_only": True,
            "does_not_delete_rows": True,
            "does_not_archive_rows": True,
            "does_not_vacuum": True,
            "bounded_recent_metadata_sample_rows": sample_limit,
            "bounded_recent_payload_sample_rows": payload_sample_limit,
            "per_query_timeout_seconds": query_timeout_seconds,
        },
    }


def _payload_schema(payload: Mapping[str, Any]) -> str:
    return str(payload.get("schema") or payload.get("schema_version") or "").strip()


def _archive_candidate_public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _int_or_zero(row.get("id")),
        "source": str(row.get("source") or ""),
        "kind": str(row.get("kind") or ""),
        "created_at": row.get("created_at"),
        "processed_at": row.get("processed_at"),
        "stable_digest": row.get("stable_digest"),
        "payload_json_bytes": _int_or_zero(row.get("payload_json_bytes")),
        "payload_schema": row.get("payload_schema"),
    }


def _legacy_event_payload_candidate(
    row: Mapping[str, Any],
    *,
    min_payload_bytes: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if str(row.get("source") or "") != LEGACY_EVENT_PAYLOAD_ARCHIVE_SOURCE:
        return None, "source_mismatch"
    if str(row.get("kind") or "") != LEGACY_EVENT_PAYLOAD_ARCHIVE_KIND:
        return None, "kind_mismatch"
    if not row.get("processed_at"):
        return None, "unprocessed_row_refused"
    raw_payload = str(row.get("payload_json") or "")
    payload_bytes = len(raw_payload.encode("utf-8"))
    if payload_bytes < min_payload_bytes:
        return None, "below_inline_threshold"
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None, "payload_json_invalid"
    if not isinstance(payload, Mapping):
        return None, "payload_not_mapping"
    schema = _payload_schema(payload)
    if schema == policy.WORK_LEDGER_SIGNAL_EVENT_SCHEMA:
        return None, "compact_schema_skipped"
    if schema == ARCHIVED_EVENT_PAYLOAD_REF_SCHEMA:
        return None, "already_archived_ref_skipped"
    if schema != "work_ledger_runtime_status_v1":
        return None, f"unsupported_payload_schema:{schema or 'missing'}"
    candidate = dict(row)
    candidate["payload"] = dict(payload)
    candidate["payload_json_bytes"] = payload_bytes
    candidate["payload_schema"] = schema
    candidate["payload_json_sha256"] = _sha256_text(raw_payload)
    return candidate, None


def _iter_target_event_rows(
    conn,
    *,
    min_id: int,
    max_id: int,
    chunk_size: int,
    newest_first: bool,
):
    if max_id <= 0:
        return
    chunk_size = max(int(chunk_size), 1)
    min_id = max(int(min_id), 1)
    max_id = max(int(max_id), min_id)
    if newest_first:
        upper = max_id
        while upper >= min_id:
            lower = max(min_id, upper - chunk_size + 1)
            rows = conn.execute(
                """
                SELECT id, source, kind, payload_json, stable_digest, created_at, processed_at
                FROM events
                WHERE id BETWEEN ? AND ?
                  AND source = ?
                  AND kind = ?
                ORDER BY id DESC
                """,
                (
                    lower,
                    upper,
                    LEGACY_EVENT_PAYLOAD_ARCHIVE_SOURCE,
                    LEGACY_EVENT_PAYLOAD_ARCHIVE_KIND,
                ),
            ).fetchall()
            yield lower, upper, [dict(row) for row in rows]
            upper = lower - 1
    else:
        lower = min_id
        while lower <= max_id:
            upper = min(max_id, lower + chunk_size - 1)
            rows = conn.execute(
                """
                SELECT id, source, kind, payload_json, stable_digest, created_at, processed_at
                FROM events
                WHERE id BETWEEN ? AND ?
                  AND source = ?
                  AND kind = ?
                ORDER BY id ASC
                """,
                (
                    lower,
                    upper,
                    LEGACY_EVENT_PAYLOAD_ARCHIVE_SOURCE,
                    LEGACY_EVENT_PAYLOAD_ARCHIVE_KIND,
                ),
            ).fetchall()
            yield lower, upper, [dict(row) for row in rows]
            lower = upper + 1


def _select_legacy_event_payload_candidates(
    conn,
    *,
    min_payload_bytes: int,
    chunk_size: int,
    max_candidates: int,
    newest_first: bool,
) -> dict[str, Any]:
    summary = _events_row_summary_payload(conn, timeout_seconds=EVENTS_RETENTION_DEFAULT_QUERY_TIMEOUT_SECONDS)
    row = _first_row(summary)
    high_water = _int_or_zero(row.get("rowid_high_water"))
    candidates: list[dict[str, Any]] = []
    skip_reasons: dict[str, int] = {}
    chunks_scanned = 0
    target_rows_scanned = 0
    candidate_limit_hit = False
    last_scanned_range: dict[str, int] | None = None
    max_candidates = max(int(max_candidates), 1)
    for lower, upper, rows in _iter_target_event_rows(
        conn,
        min_id=1,
        max_id=high_water,
        chunk_size=chunk_size,
        newest_first=newest_first,
    ):
        chunks_scanned += 1
        last_scanned_range = {"lower_id": lower, "upper_id": upper}
        target_rows_scanned += len(rows)
        for raw_row in rows:
            candidate, skip_reason = _legacy_event_payload_candidate(
                raw_row,
                min_payload_bytes=min_payload_bytes,
            )
            if candidate is None:
                if skip_reason:
                    skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
                continue
            candidates.append(candidate)
            if len(candidates) >= max_candidates:
                candidate_limit_hit = True
                break
        if candidate_limit_hit:
            break
    return {
        "row_summary": summary,
        "rowid_high_water": high_water,
        "chunks_scanned": chunks_scanned,
        "target_rows_scanned": target_rows_scanned,
        "scan_completed": not candidate_limit_hit and (last_scanned_range is None or last_scanned_range.get("lower_id") == 1),
        "candidate_limit_hit": candidate_limit_hit,
        "last_scanned_range": last_scanned_range,
        "skip_reasons": skip_reasons,
        "candidates": candidates,
    }


def _archive_ref_payload(
    candidate: Mapping[str, Any],
    *,
    archive_rel_path: str,
    archive_sha256: str,
    archive_bytes: int,
    archived_at: str,
) -> dict[str, Any]:
    original_payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
    original_authority = original_payload.get("authority") if isinstance(original_payload.get("authority"), Mapping) else {}
    authority = dict(original_authority)
    authority.setdefault("full_payload_ref", policy.RUNTIME_STATUS_REL.as_posix())
    authority["posture"] = "historical event body archived; current Work Ledger artifact remains authority"
    return {
        "schema": ARCHIVED_EVENT_PAYLOAD_REF_SCHEMA,
        "original_source": candidate.get("source"),
        "original_kind": candidate.get("kind"),
        "original_payload_schema": candidate.get("payload_schema"),
        "original_event_id": candidate.get("id"),
        "original_created_at": candidate.get("created_at"),
        "archive": {
            "path": archive_rel_path,
            "sha256": archive_sha256,
            "bytes": archive_bytes,
            "original_payload_sha256": candidate.get("payload_json_sha256"),
            "original_payload_bytes": candidate.get("payload_json_bytes"),
            "archived_at": archived_at,
        },
        "authority": authority,
        "inline_payload_policy": {
            "class_id": "legacy_derived_runtime_diagnostic_signal",
            "replacement_reason": "oversized historical event payload",
            "stable_digest_preserved": True,
            "row_identity_preserved": True,
        },
    }


def build_legacy_event_payload_archive_report(
    conn,
    *,
    paths: store.MetabolismPaths,
    repo_root: Path = REPO_ROOT,
    live: bool = False,
    chunk_size: int = LEGACY_EVENT_PAYLOAD_ARCHIVE_DEFAULT_CHUNK_SIZE,
    max_candidates: int = LEGACY_EVENT_PAYLOAD_ARCHIVE_DEFAULT_MAX_CANDIDATES,
    min_payload_bytes: int = EVENTS_RETENTION_OVERSIZED_PAYLOAD_BYTES,
    newest_first: bool = True,
    archive_dir: Path | None = None,
) -> dict[str, Any]:
    wal_path = _wal_path_for_db(paths.db)
    wal_bytes_before = _path_size(wal_path)
    selected = _select_legacy_event_payload_candidates(
        conn,
        min_payload_bytes=max(int(min_payload_bytes), 1),
        chunk_size=max(int(chunk_size), 1),
        max_candidates=max(int(max_candidates), 1),
        newest_first=bool(newest_first),
    )
    candidates = [dict(row) for row in selected["candidates"]]
    candidate_payload_bytes = sum(_int_or_zero(row.get("payload_json_bytes")) for row in candidates)
    generated_at = _utc_now()
    archive_root = archive_dir or (repo_root / LEGACY_EVENT_PAYLOAD_ARCHIVE_REL_DIR)
    archive_rel_path: str | None = None
    archive_path: Path | None = None
    archive_rows_written = 0
    archive_bytes_written = 0
    archive_sha256: str | None = None
    rows_replaced = 0
    update_conflict_rows = 0
    chunks_committed = 0
    replacement_payload_bytes = 0

    if live and candidates:
        archive_root.mkdir(parents=True, exist_ok=True)
        candidate_ids = [_int_or_zero(row.get("id")) for row in candidates]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_path = archive_root / (
            f"legacy_work_ledger_signal_{stamp}_{min(candidate_ids)}_{max(candidate_ids)}.jsonl.gz"
        )
        tmp_path = archive_path.with_name(f"{archive_path.name}.tmp")
        with gzip.open(tmp_path, "wt", encoding="utf-8") as handle:
            for candidate in candidates:
                record = {
                    "schema": LEGACY_EVENT_PAYLOAD_ARCHIVE_RECORD_SCHEMA,
                    "archived_at": generated_at,
                    "event": {
                        "id": candidate.get("id"),
                        "source": candidate.get("source"),
                        "kind": candidate.get("kind"),
                        "created_at": candidate.get("created_at"),
                        "processed_at": candidate.get("processed_at"),
                        "stable_digest": candidate.get("stable_digest"),
                        "payload_json": candidate.get("payload_json"),
                        "payload_schema": candidate.get("payload_schema"),
                        "payload_json_bytes": candidate.get("payload_json_bytes"),
                        "payload_json_sha256": candidate.get("payload_json_sha256"),
                    },
                }
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                handle.write("\n")
                archive_rows_written += 1
        tmp_path.replace(archive_path)
        archive_bytes_written = _path_size(archive_path)
        archive_sha256 = _sha256_file(archive_path)
        archive_rel_path = _relative_or_absolute(archive_path, repo_root)

        for start in range(0, len(candidates), max(int(chunk_size), 1)):
            chunk = candidates[start : start + max(int(chunk_size), 1)]
            with store.transaction(conn):
                for candidate in chunk:
                    replacement = _archive_ref_payload(
                        candidate,
                        archive_rel_path=archive_rel_path,
                        archive_sha256=archive_sha256,
                        archive_bytes=archive_bytes_written,
                        archived_at=generated_at,
                    )
                    replacement_json = store.json_dumps(replacement)
                    replacement_payload_bytes += len(replacement_json.encode("utf-8"))
                    result = conn.execute(
                        """
                        UPDATE events
                        SET payload_json = ?
                        WHERE id = ?
                          AND source = ?
                          AND kind = ?
                          AND processed_at IS NOT NULL
                          AND stable_digest = ?
                          AND payload_json = ?
                        """,
                        (
                            replacement_json,
                            _int_or_zero(candidate.get("id")),
                            LEGACY_EVENT_PAYLOAD_ARCHIVE_SOURCE,
                            LEGACY_EVENT_PAYLOAD_ARCHIVE_KIND,
                            str(candidate.get("stable_digest") or ""),
                            str(candidate.get("payload_json") or ""),
                        ),
                    )
                    if result.rowcount == 1:
                        rows_replaced += 1
                    else:
                        update_conflict_rows += 1
            chunks_committed += 1

    return {
        "schema": LEGACY_EVENT_PAYLOAD_ARCHIVE_SCHEMA,
        "generated_at": generated_at,
        "live": bool(live),
        "target_source": LEGACY_EVENT_PAYLOAD_ARCHIVE_SOURCE,
        "target_kind": LEGACY_EVENT_PAYLOAD_ARCHIVE_KIND,
        "mode": "archive_replace",
        "rowid_high_water": selected["rowid_high_water"],
        "chunk_size": max(int(chunk_size), 1),
        "max_candidates": max(int(max_candidates), 1),
        "order": "newest_first" if newest_first else "oldest_first",
        "min_payload_bytes": max(int(min_payload_bytes), 1),
        "chunks_scanned": selected["chunks_scanned"],
        "target_rows_scanned": selected["target_rows_scanned"],
        "scan_completed": bool(selected["scan_completed"]),
        "candidate_limit_hit": bool(selected["candidate_limit_hit"]),
        "last_scanned_range": selected["last_scanned_range"],
        "candidate_rows": len(candidates),
        "candidate_payload_bytes": candidate_payload_bytes,
        "candidate_samples": [_archive_candidate_public(row) for row in candidates[:10]],
        "archive_path": archive_rel_path,
        "archive_rows_written": archive_rows_written,
        "archive_bytes_written": archive_bytes_written,
        "archive_sha256": archive_sha256,
        "rows_replaced": rows_replaced,
        "rows_deleted": 0,
        "chunks_committed": chunks_committed,
        "rows_skipped": sum(int(value) for value in selected["skip_reasons"].values()) + update_conflict_rows,
        "skip_reasons": {
            **selected["skip_reasons"],
            **({"update_conflict_or_race": update_conflict_rows} if update_conflict_rows else {}),
        },
        "replacement_payload_bytes": replacement_payload_bytes,
        "estimated_inline_payload_bytes_saved": max(candidate_payload_bytes - replacement_payload_bytes, 0)
        if live
        else None,
        "wal_bytes_before": wal_bytes_before,
        "wal_bytes_after": _path_size(wal_path),
        "db_compaction_next_action": "rerun_db_compaction_eligibility",
        "event_retention_next_action": "rerun_events_retention_eligibility",
        "row_summary": selected["row_summary"],
        "safety_boundary": {
            "processed_only": True,
            "unprocessed_rows_refused": True,
            "legacy_payload_only": True,
            "compact_schema_rows_skipped": True,
            "archive_before_mutation": True,
            "chunked_transactions": True,
            "does_not_delete_rows": True,
            "does_not_vacuum": True,
            "stable_digest_preserved": True,
            "row_identity_preserved": True,
        },
        "consumer_contract": {
            "hot_queue_reader": "system/lib/metabolism_store.py::fetch_unprocessed_events only reads processed_at IS NULL",
            "work_ledger_job_derivation": "system/lib/metabolism_policy.py::derive_jobs_for_event reads payload.triggers before processing",
            "historical_row_posture": "processed legacy diagnostic payload can be archived while preserving row identity and stable_digest",
        },
    }


def _operation_parameters(params: Mapping[str, Any]) -> dict[str, Any]:
    operation_parameters = params.get("operation_parameters")
    if isinstance(operation_parameters, Mapping):
        return dict(operation_parameters)
    return {}


def _source_list_from_token(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def overnight_priority_for_job(job: Mapping[str, Any]) -> tuple[int | None, str]:
    kind = str(job.get("kind") or "").strip()
    provider = str(job.get("provider") or "").strip()
    params = job.get("params") if isinstance(job.get("params"), Mapping) else {}
    operation_parameters = _operation_parameters(params)
    if kind == "python_std_compliance_cycle":
        return policy.source_kind_overnight_priority("python_holographic"), "python_std_compliance"
    if kind == "kernel_sync_raw_seed_auto":
        return policy.source_kind_overnight_priority("raw_seed_shards"), "raw_seed_sync"
    if kind == "raw_seed_provider_candidate_cycle":
        return policy.source_kind_overnight_priority("raw_seed_shards"), "raw_seed_type_b_provider_candidates"
    if kind == "raw_seed_route_review":
        return policy.PRIORITY_HIGH, "raw_seed_route_review"
    if kind == "raw_seed_distill_cycle":
        return 15, "raw_seed_distill"
    if kind == "nvidia_continuous_navigation_populate":
        source_kinds = _source_list_from_token(operation_parameters.get("source_kinds"))
        return policy.source_kinds_overnight_priority(source_kinds), "nvidia_source_priority"
    if kind == "navigator_refresh":
        source_kind = str(operation_parameters.get("kind") or "").strip()
        return policy.source_kind_overnight_priority(source_kind), f"navigator:{source_kind or 'unknown'}"
    if kind in {"semantic_route_refresh", "kernel_embed_refresh"}:
        source_kind = str(operation_parameters.get("source") or "").strip()
        if source_kind == "python":
            source_kind = "python_holographic"
        return policy.source_kind_overnight_priority(source_kind), f"{kind}:{source_kind or 'unknown'}"
    if kind in {"market_snapshot", "market_feed_bundle"}:
        return 25, "market_after_core_overnight_sources"
    if kind == "work_ledger_project":
        return 70, "work_ledger_after_core_overnight_sources"
    if provider == "openrouter_free":
        return 55, "openrouter_free_metadata_or_candidate"
    if provider == "nvidia":
        return 40, "nvidia_candidate_or_misc"
    return None, "unchanged"


def reprioritize_overnight_jobs(
    conn,
    *,
    states: set[str] | None,
    live: bool,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = store.fetch_jobs(conn, states=sorted(states) if states is not None else None, limit=limit)
    scanned = 0
    changed = 0
    samples: list[dict[str, Any]] = []
    for job in rows:
        scanned += 1
        priority, reason = overnight_priority_for_job(job)
        if priority is None:
            continue
        current = int(job.get("priority") or 0)
        if current == int(priority):
            continue
        changed += 1
        if len(samples) < 20:
            samples.append(
                {
                    "id": job.get("id"),
                    "kind": job.get("kind"),
                    "provider": job.get("provider"),
                    "state": job.get("state"),
                    "priority_before": current,
                    "priority_after": int(priority),
                    "reason": reason,
                }
            )
        if live:
            summary = dict(job.get("summary") or {})
            summary["overnight_reprioritize"] = {
                "priority_before": current,
                "priority_after": int(priority),
                "reason": reason,
                "updated_at": _utc_now(),
            }
            conn.execute(
                """
                UPDATE jobs
                SET priority = ?, summary_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(priority), store.json_dumps(summary), _utc_now(), job.get("id")),
            )
    return {
        "schema": "metabolism_overnight_reprioritize_v1",
        "generated_at": _utc_now(),
        "live": bool(live),
        "states": sorted(states) if states is not None else "all",
        "scanned_rows": scanned,
        "changed_rows": changed,
        "samples": samples,
        "priority_contract": {
            "core_sources": ["raw_seed_shards", "standards_json", "python_holographic"],
            "annex_notes_priority": policy.source_kind_overnight_priority("annex_notes"),
            "work_ledger_priority": 70,
        },
    }


def cmd_maintenance(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        if args.maintenance_action == "compact-reaction-jobs":
            payload = compact_reaction_job_payloads(
                runtime.conn,
                states=_state_filter_from_args(args),
                live=bool(args.live),
                limit=args.limit,
            )
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                mode = "compacted" if args.live else "would compact"
                print(
                    f"{mode}: {payload['changed_rows']} row(s), "
                    f"saved {payload['saved_bytes']} bytes"
                )
            return 0
        if args.maintenance_action == "db-compaction-eligibility":
            payload = build_db_compaction_eligibility_report(
                runtime.conn,
                paths=runtime.paths,
                repo_root=REPO_ROOT,
                dbstat_limit=args.dbstat_limit,
                dbstat_timeout_seconds=args.dbstat_timeout_seconds,
                include_dbstat=bool(getattr(args, "include_dbstat", False)),
            )
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(
                    "db_compaction_eligibility: "
                    f"{payload['recommended_action']} "
                    f"eligible={payload['eligible']} "
                    f"freelist={payload['estimated_freelist_bytes']} bytes"
                )
            return 0
        if args.maintenance_action == "events-retention-eligibility":
            payload = build_events_retention_eligibility_report(
                runtime.conn,
                paths=runtime.paths,
                repo_root=REPO_ROOT,
                sample_limit=args.sample_limit,
                payload_sample_limit=args.payload_sample_limit,
                query_timeout_seconds=args.query_timeout_seconds,
            )
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(
                    "events_retention_eligibility: "
                    f"{payload['recommended_action']} "
                    f"eligible={payload['eligible']} "
                    f"events_bytes={payload['events_table']['bytes']}"
                )
            return 0
        if args.maintenance_action == "legacy-event-payload-archive":
            active = store.fetch_jobs(
                runtime.conn,
                states=[store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING],
            )
            if active and args.live and not args.allow_active:
                raise SystemExit(
                    f"refusing legacy event payload archive while {len(active)} job(s) are claimed/running; "
                    "pass --allow-active only for explicit operator recovery"
                )
            archive_dir = Path(args.archive_dir) if args.archive_dir else None
            if archive_dir is not None and not archive_dir.is_absolute():
                archive_dir = REPO_ROOT / archive_dir
            payload = build_legacy_event_payload_archive_report(
                runtime.conn,
                paths=runtime.paths,
                repo_root=REPO_ROOT,
                live=bool(args.live),
                chunk_size=args.chunk_size,
                max_candidates=args.max_candidates,
                min_payload_bytes=args.min_payload_bytes,
                newest_first=not bool(args.oldest_first),
                archive_dir=archive_dir,
            )
            payload["active_job_count"] = len(active)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                mode = "archived/replaced" if args.live else "would archive/replace"
                print(
                    "legacy_event_payload_archive: "
                    f"{mode} {payload['candidate_rows']} candidate row(s), "
                    f"payload_bytes={payload['candidate_payload_bytes']}"
                )
            return 0
        if args.maintenance_action == "vacuum":
            active = store.fetch_jobs(
                runtime.conn,
                states=[store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING],
            )
            if active and not args.allow_active:
                raise SystemExit(
                    f"refusing VACUUM while {len(active)} job(s) are claimed/running; "
                    "pass --allow-active only for explicit operator recovery"
                )
            before = _path_size(runtime.paths.db)
            payload: dict[str, Any] = {
                "schema": "metabolism_vacuum_v1",
                "generated_at": _utc_now(),
                "live": bool(args.live),
                "db_path": str(runtime.paths.db.relative_to(REPO_ROOT)),
                "bytes_before": before,
                "active_job_count": len(active),
            }
            if args.live:
                runtime.conn.execute("VACUUM")
                payload["bytes_after"] = _path_size(runtime.paths.db)
                payload["saved_bytes"] = max(before - int(payload["bytes_after"]), 0)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                if args.live:
                    print(f"vacuumed: {payload.get('saved_bytes', 0)} bytes saved")
                else:
                    print(f"would vacuum: {before} bytes")
            return 0
        if args.maintenance_action == "wal-checkpoint":
            active = store.fetch_jobs(
                runtime.conn,
                states=[store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING],
            )
            if active and not args.allow_active:
                raise SystemExit(
                    f"refusing WAL checkpoint while {len(active)} job(s) are claimed/running; "
                    "pass --allow-active only for explicit operator recovery"
                )
            wal_path = _wal_path_for_db(runtime.paths.db)
            shm_path = _shm_path_for_db(runtime.paths.db)
            payload = {
                "schema": "metabolism_wal_checkpoint_v1",
                "generated_at": _utc_now(),
                "live": bool(args.live),
                "db_path": str(runtime.paths.db.relative_to(REPO_ROOT)),
                "wal_path": str(wal_path.relative_to(REPO_ROOT)),
                "shm_path": str(shm_path.relative_to(REPO_ROOT)),
                "db_bytes_before": _path_size(runtime.paths.db),
                "wal_bytes_before": _path_size(wal_path),
                "shm_bytes_before": _path_size(shm_path),
                "active_job_count": len(active),
            }
            if args.live:
                row = runtime.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                payload["checkpoint_result"] = {
                    "busy": int(row[0]) if row is not None else None,
                    "log_frames": int(row[1]) if row is not None else None,
                    "checkpointed_frames": int(row[2]) if row is not None else None,
                }
                payload["db_bytes_after"] = _path_size(runtime.paths.db)
                payload["wal_bytes_after"] = _path_size(wal_path)
                payload["shm_bytes_after"] = _path_size(shm_path)
                payload["wal_saved_bytes"] = max(
                    int(payload["wal_bytes_before"]) - int(payload["wal_bytes_after"]),
                    0,
                )
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                if args.live:
                    print(f"checkpointed WAL: {payload.get('wal_saved_bytes', 0)} bytes saved")
                else:
                    print(f"would checkpoint WAL: {_path_size(wal_path)} bytes")
            return 0
        if args.maintenance_action == "reprioritize-overnight":
            payload = reprioritize_overnight_jobs(
                runtime.conn,
                states=_state_filter_from_args(args),
                live=bool(args.live),
                limit=args.limit,
            )
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                mode = "reprioritized" if args.live else "would reprioritize"
                print(f"{mode}: {payload['changed_rows']} row(s)")
            return 0
        raise SystemExit(f"unknown maintenance action: {args.maintenance_action}")
    finally:
        runtime.close()


def cmd_doctor(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        if bool(getattr(args, "full_integrity", False)):
            integrity_pragma = "integrity_check"
            integrity = runtime.conn.execute("PRAGMA integrity_check").fetchone()[0]
        elif bool(getattr(args, "db_check", False)):
            integrity_pragma = "quick_check"
            integrity = runtime.conn.execute("PRAGMA quick_check").fetchone()[0]
        else:
            integrity_pragma = "skipped"
            integrity = "skipped"
        journal_mode = runtime.conn.execute("PRAGMA journal_mode").fetchone()[0]
        installed_path = (Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist")
        launchd_loaded, launchd_message = _launchctl_state(LAUNCH_AGENT_LABEL)
        launchd_stderr_tail = _tail_text(runtime.paths.logs_dir / "metabolismd.err.log", limit=4000)
        installed_program = _plist_program_argument(installed_path)
        source_program = _plist_program_argument(LAUNCH_AGENT_SOURCE)
        stderr_permission_denied = (
            "Operation not permitted" in launchd_stderr_tail
            or "cannot access parent directories" in launchd_stderr_tail
        )
        queue_liveness = build_queue_liveness_report(runtime.conn)
        stderr_permission_denied_suppressed = bool(
            stderr_permission_denied
            and launchd_loaded
            and queue_liveness.get("daemon_running")
            and not queue_liveness.get("daemon_heartbeat_stalled")
        )
        launch_permission_denied = bool(
            stderr_permission_denied and not stderr_permission_denied_suppressed
        )
        launch_recovery_commands = [
            "./repo-python -m tools.meta.control.metabolismd install-launch-agent",
            f"launchctl kickstart -k gui/{os.getuid()}/{LAUNCH_AGENT_LABEL}",
        ]
        if launch_permission_denied:
            launch_recovery_commands.insert(
                0,
                "Grant Full Disk Access for the launchd runner or move the repo out of Desktop/Documents, then reinstall the LaunchAgent.",
            )
        reactions_state = {}
        reactions_path = REPO_ROOT / "tools" / "meta" / "control" / "reactions_state.json"
        if reactions_path.exists():
            reactions_state = json.loads(reactions_path.read_text(encoding="utf-8"))
        if bool(getattr(args, "deep_signals", False)):
            raw_seed_snapshot = policy.build_runtime_signal_events(REPO_ROOT)[0]["payload"]
        else:
            raw_seed_snapshot = {
                "skipped": "pass --deep-signals to rebuild raw-seed/work-ledger/hologram runtime signals",
            }
        intake = runtime.raw_seed_intake.write_projection()
        market_preview = market_clock.build_market_projection(
            runtime.conn,
            daemon_running=_live_daemon_heartbeat(runtime.conn) is not None,
        )
        market_config = _effective_market_config(runtime.conn)
        yfinance_status = _yfinance_status()
        power_status = _pmset_status()
        launch_contract_status = _safe_launchable_operation_contract_status(REPO_ROOT)
        # pri_119: read-only reconciliation block. Never mutates from
        # doctor — apply_safe_repairs=False, emit_event=False keep this
        # pass observation-only.
        try:
            doctor_reconcile = run_reconciliation_pass(
                runtime.conn,
                repo_root=runtime.repo_root,
                scope="doctor",
                runtime_owner=runtime.owner,
                apply_safe_repairs=False,
                emit_event=False,
            ).to_dict()
        except Exception as exc:  # noqa: BLE001 - doctor must not crash on reconciliation
            doctor_reconcile = {
                "schema": "metabolism_reconciliation_v1",
                "scope": "doctor",
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        report = {
            "schema": "metabolism_doctor_v1",
            "generated_at": _utc_now(),
            "db_integrity": integrity,
            "db_integrity_pragma": integrity_pragma,
            "journal_mode": journal_mode,
            "reconciliation": doctor_reconcile,
            "launch_agent": {
                "source_exists": LAUNCH_AGENT_SOURCE.exists(),
                "installed_exists": installed_path.exists(),
                "loaded": launchd_loaded,
                "last_exit_code": _launchctl_last_exit_code(launchd_message),
                "installed_program": installed_program,
                "source_program": source_program,
                "program_drift": bool(installed_program and source_program and installed_program != source_program),
                "permission_denied": launch_permission_denied,
                "stderr_permission_denied_seen": stderr_permission_denied,
                "stderr_permission_denied_suppressed_by_live_daemon": stderr_permission_denied_suppressed,
                "stderr_tail": launchd_stderr_tail[-1200:],
                "recovery_commands": launch_recovery_commands,
                "details": launchd_message[:500],
            },
            "hooks": {
                "claude_runtime_hook_exists": (REPO_ROOT / ".claude/hooks/runtime_hook.py").exists(),
            },
            "reactions_compat": {
                "desired_armed": bool(reactions_state.get("desired_armed")),
                "effective_armed": bool(reactions_state.get("effective_armed")),
            },
            "stale_claims": len([claim for claim in store.list_blackboard_claims(runtime.conn) if claim.get("status") == "expired"]),
            "queue_liveness": queue_liveness,
            "raw_seed": raw_seed_snapshot,
            "raw_seed_intake": intake,
            "launchable_operation_contracts": launch_contract_status,
            "embedding_runtime_present": (REPO_ROOT / "system/lib/embedding_substrate.py").exists(),
            "market": {
                "config": market_config,
                "next_fire": market_preview.get("next_fire"),
                "timeline_path": market_preview.get("timeline_path"),
                "yfinance": yfinance_status,
                "launch_agent": {
                    "source_exists": LAUNCH_AGENT_SOURCE.exists(),
                    "installed_exists": installed_path.exists(),
                    "loaded": launchd_loaded,
                    "last_exit_code": _launchctl_last_exit_code(launchd_message),
                    "permission_denied": launch_permission_denied,
                },
                "power": power_status,
                "note": "LaunchAgent survives terminal close but not system sleep.",
            },
        }
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"db_integrity: {report['db_integrity']}")
            print(f"journal_mode: {report['journal_mode']}")
            print(f"launch_agent_loaded: {report['launch_agent']['loaded']}")
            print(f"launch_agent_exit: {report['launch_agent']['last_exit_code']}")
            print(f"launch_agent_program_drift: {report['launch_agent']['program_drift']}")
            print(f"launch_agent_permission_denied: {report['launch_agent']['permission_denied']}")
            if report["launch_agent"]["recovery_commands"]:
                print(f"launch_agent_recovery: {report['launch_agent']['recovery_commands'][0]}")
            print(f"claude_runtime_hook_exists: {report['hooks']['claude_runtime_hook_exists']}")
            print(f"stale_claims: {report['stale_claims']}")
            print(
                f"queue_liveness: {queue_liveness.get('status')} "
                f"orphaned={len(queue_liveness.get('orphaned_jobs') or [])}"
            )
            if queue_liveness.get("recovery_commands"):
                print(f"queue_recovery: {queue_liveness['recovery_commands'][0]}")
            recon_summary = (doctor_reconcile or {}).get("summary") or {}
            print(
                f"reconciliation: healthy={recon_summary.get('healthy')} "
                f"findings={recon_summary.get('finding_count', 0)} "
                f"ambiguous={recon_summary.get('ambiguous_count', 0)}"
            )
            print(
                "launch_contracts: "
                f"posture={launch_contract_status.get('posture') or 'unknown'} "
                f"blockers={launch_contract_status.get('missing_landing_contract_blocker_count', 0)} "
                f"metabolismd_blockers="
                f"{(launch_contract_status.get('metabolismd_owned_automatic_contracts') or {}).get('blocking_count', 0)}"
            )
            next_fire = report["market"].get("next_fire")
            if next_fire:
                print(
                    f"market_next_fire: {next_fire.get('fire_point') or next_fire.get('name')} at {next_fire.get('target_time_market')}"
                )
            print(f"market_timeline: {report['market']['timeline_path']}")
            print(f"yfinance_available: {report['market']['yfinance']['available']}")
        return 0
    finally:
        runtime.close()


def cmd_raw_seed_status(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        projection = runtime.raw_seed_intake.write_projection()
        if args.json:
            print(json.dumps(projection, indent=2, ensure_ascii=False))
            return 0
        print(f"watcher_mode: {projection.get('watcher_mode')}")
        print(f"watched_families: {len(projection.get('watched_families') or [])}")
        print(f"active_draft_sessions: {len(projection.get('active_draft_sessions') or [])}")
        pending = projection.get("pending_settle_timers") or []
        if pending:
            first = pending[0]
            print(f"next_settle: {first.get('family_number')} {first.get('entry_id')} {first.get('due_at')}")
        last_auto_sync = projection.get("last_auto_sync") or {}
        if last_auto_sync:
            print(
                f"last_auto_sync: family={last_auto_sync.get('family_number')} at {last_auto_sync.get('synced_at') or last_auto_sync.get('updated_at')}"
            )
        print(f"tracker_path: {projection.get('tracker_path')}")
        print(f"timeline_path: {projection.get('timeline_path')}")
        return 0
    finally:
        runtime.close()


def cmd_raw_seed_entries(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        entries = runtime.raw_seed_intake.list_entries(
            family_number=args.family,
            limit=int(args.limit or 20),
        )
        if args.json:
            print(json.dumps(entries, indent=2, ensure_ascii=False))
            return 0
        for entry in entries:
            print(
                f"{entry['entry_id']} family={entry['family_number']} state={entry['state']} "
                f"classification={entry.get('classification') or 'n/a'} updated_at={entry.get('updated_at')}"
            )
        return 0
    finally:
        runtime.close()


def cmd_market(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        if args.market_action == "status":
            snapshot = market_clock.build_market_projection(
                runtime.conn,
                daemon_running=_live_daemon_heartbeat(runtime.conn) is not None,
            )
            if args.json:
                print(json.dumps(snapshot, indent=2, ensure_ascii=False))
                return 0
            print(
                f"market_clock: enabled={snapshot['enabled']} market_tz={snapshot['market_timezone']} operator_tz={snapshot['operator_timezone']}"
            )
            print(f"generated_market: {snapshot['generated_at_market']}")
            next_fire = snapshot.get("next_fire")
            if next_fire:
                print(f"next_fire: {next_fire['fire_point']} at {next_fire['target_time_market']}")
            else:
                print("next_fire: none scheduled")
            due = snapshot.get("due_now") or []
            print(f"due_now: {', '.join(item['fire_point'] for item in due) if due else 'none'}")
            print(f"today_fired: {', '.join(item['fire_point'] for item in (snapshot.get('today_fired') or [])) or 'none'}")
            print(f"queued_jobs: {len(snapshot.get('queued_jobs') or [])}")
            print(f"running_jobs: {len(snapshot.get('running_jobs') or [])}")
            print(f"timeline_path: {snapshot['timeline_path']}")
            if snapshot.get("nothing_ran_reason"):
                print(f"why_nothing_ran: {snapshot['nothing_ran_reason']}")
            for entry in snapshot.get("today") or []:
                status = "fired" if entry.get("fired_at_utc") else ("passed" if entry.get("passed") else "future")
                print(
                    f"  {entry['fire_point']:<14} {entry['target_time_market']}  {status}"
                )
            if snapshot.get("upcoming"):
                print("upcoming:")
                for entry in snapshot["upcoming"][:4]:
                    print(f"  {entry['fire_point']:<14} {entry['target_time_market']}")
            return 0
        if args.market_action == "emit":
            emitted = market_clock.compute_and_emit_fires(runtime.conn)
            print(
                json.dumps(
                    {"emitted": len(emitted), "fire_points": [event["payload"] for event in emitted]},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        if args.market_action == "config":
            payload = _effective_market_config(runtime.conn)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        if args.market_action == "configure":
            if args.enable and args.disable:
                raise SystemExit("--enable and --disable are mutually exclusive")
            if bool(getattr(args, "weekday_open_close", False)) and bool(getattr(args, "market_hours_hourly", False)):
                raise SystemExit("--weekday-open-close and --market-hours-hourly are mutually exclusive")
            current = store.get_setting(runtime.conn, "market_clock", {}) or {}
            if not isinstance(current, dict):
                current = {}
            if bool(getattr(args, "weekday_open_close", False)):
                current.update(market_clock.default_config())
            if bool(getattr(args, "market_hours_hourly", False)):
                current.update(market_clock.market_hours_hourly_config())
            if args.enable:
                current["enabled"] = True
            if args.disable:
                current["enabled"] = False
            if args.timezone:
                try:
                    __import__("zoneinfo").ZoneInfo(args.timezone)
                except Exception as exc:
                    raise SystemExit(f"invalid --timezone: {exc}") from exc
                current["timezone"] = args.timezone
            if args.grace_minutes is not None:
                current["fire_grace_minutes"] = int(args.grace_minutes)
            store.set_setting(runtime.conn, "market_clock", current)
            if args.universe_file:
                store.set_setting(runtime.conn, "market_clock_universe", _load_universe_file(args.universe_file))
            if args.use_default_universe:
                store.set_setting(runtime.conn, "market_clock_universe", [])
            runtime.write_projections()
            payload = _effective_market_config(runtime.conn)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        raise SystemExit(f"unknown market action: {args.market_action}")
    finally:
        runtime.close()


def cmd_governor(args: argparse.Namespace) -> int:
    runtime = _runtime()
    try:
        if args.governor_action == "status":
            payload = governor.build_status(runtime.conn)
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
            print(
                f"governor: mode={payload['mode']} enabled={payload['enabled']} "
                f"dispatch={payload['dispatch_enabled']}"
            )
            if payload.get("dispatch_block_reason"):
                print(f"dispatch_block_reason: {payload['dispatch_block_reason']}")
            print(f"cost_posture: {payload.get('cost_posture')}")
            for provider, budget in sorted((payload.get("provider_budgets") or {}).items()):
                print(
                    f"  {provider:<16} max={budget.get('max_concurrent')} "
                    f"spacing={budget.get('min_seconds_between_dispatch', 0)}s"
                )
            return 0
        if args.governor_action == "set-mode":
            payload = governor.set_mode(
                runtime.conn,
                mode=args.mode,
                enabled=args.enabled,
                cost_posture=args.cost_posture,
                paid_spend_usd_daily_cap=args.paid_spend_usd_daily_cap,
            )
            status = governor.build_status(runtime.conn)
            if args.json:
                print(json.dumps(status, indent=2, ensure_ascii=False))
            else:
                print(f"governor mode set to {payload['mode']}")
            runtime.write_projections()
            return 0
        raise SystemExit(f"unknown governor action: {args.governor_action}")
    finally:
        runtime.close()


def _launch_agent_dest(home: Path | None = None) -> Path:
    user_home = home or Path.home()
    return user_home / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"


def _bootstrap_or_load_launch_agent(*, domain: str, label: str, dest: Path) -> None:
    service = f"{domain}/{label}"
    subprocess.run(["launchctl", "bootout", domain, str(dest)], check=False, capture_output=True, text=True)
    bootstrap = subprocess.run(
        ["launchctl", "bootstrap", domain, str(dest)],
        check=False,
        capture_output=True,
        text=True,
    )
    if bootstrap.returncode != 0:
        message = (bootstrap.stderr or bootstrap.stdout or "").strip()
        if bootstrap.returncode == 5 and "Input/output error" in message:
            subprocess.run(["launchctl", "unload", str(dest)], check=False, capture_output=True, text=True)
            load = subprocess.run(
                ["launchctl", "load", "-w", str(dest)],
                check=False,
                capture_output=True,
                text=True,
            )
            if load.returncode != 0:
                load_message = (load.stderr or load.stdout or "").strip() or "unknown error"
                raise RuntimeError(f"launchctl load fallback failed for {label}: {load_message}")
        else:
            raise RuntimeError(f"launchctl bootstrap failed for {label}: {message or 'unknown error'}")
    subprocess.run(["launchctl", "enable", service], check=False, capture_output=True, text=True)
    subprocess.run(["launchctl", "kickstart", "-k", service], check=False, capture_output=True, text=True)


def install_launch_agent(*, repo_root: Path, home: Path | None = None) -> Path:
    dest = _launch_agent_dest(home)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(dest, render_launch_agent_plist(repo_root, home=home))
    domain = f"gui/{os.getuid()}"
    _bootstrap_or_load_launch_agent(domain=domain, label=LAUNCH_AGENT_LABEL, dest=dest)
    return dest


def uninstall_launch_agent(*, home: Path | None = None) -> Path:
    dest = _launch_agent_dest(home)
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(dest)], check=False)
    if dest.exists():
        dest.unlink()
    return dest


def cmd_install_launch_agent(args: argparse.Namespace) -> int:
    dest = install_launch_agent(repo_root=REPO_ROOT)
    print(str(dest))
    return 0


def cmd_uninstall_launch_agent(args: argparse.Namespace) -> int:
    dest = uninstall_launch_agent()
    print(str(dest))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metabolismd")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--poll-seconds", type=float, default=None)
    run_parser.add_argument("--once", action="store_true")
    run_parser.add_argument("--ignore-pause", action="store_true")
    run_parser.add_argument("--job-id", action="append", default=[])
    run_parser.add_argument("--only-kind", action="append", default=[])
    run_parser.add_argument("--require-dispatch", action="store_true")
    run_parser.add_argument("--once-drain-timeout-seconds", type=float, default=1800)
    run_parser.add_argument(
        "--allow-duplicate-daemon",
        action="store_true",
        help="Bypass the single-resident guard; intended only for explicit recovery diagnostics.",
    )
    run_parser.set_defaults(func=cmd_run)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--json", action="store_true")
    status_parser.set_defaults(func=cmd_status)

    scan_parser = sub.add_parser("scan")
    scan_parser.set_defaults(func=cmd_scan)

    selector_tick_parser = sub.add_parser("selector-tick")
    selector_tick_parser.add_argument("--json", action="store_true")
    selector_tick_parser.add_argument("--apply", action="store_true")
    selector_tick_parser.add_argument("--limit", type=int, default=20)
    selector_tick_parser.add_argument("--receipt-limit", type=int, default=5)
    selector_tick_parser.set_defaults(func=cmd_selector_tick)

    enqueue_parser = sub.add_parser("enqueue")
    enqueue_parser.add_argument("kind")
    enqueue_parser.add_argument("--source", default="cli")
    enqueue_parser.add_argument("--payload-json", default="{}")
    enqueue_parser.set_defaults(func=cmd_enqueue)

    enqueue_job_parser = sub.add_parser("enqueue-job")
    enqueue_job_parser.add_argument("operation_id")
    enqueue_job_parser.add_argument("--provider", default=None)
    enqueue_job_parser.add_argument("--parameters-json", default="{}")
    enqueue_job_parser.add_argument("--priority", type=int, default=20)
    enqueue_job_parser.add_argument("--not-before", default=None)
    enqueue_job_parser.add_argument("--idempotency-key", default=None)
    enqueue_job_parser.add_argument("--json", action="store_true")
    enqueue_job_parser.set_defaults(func=cmd_enqueue_job)

    jobs_parser = sub.add_parser("jobs")
    jobs_parser.add_argument("--states", default=None)
    jobs_parser.add_argument("--limit", type=int, default=40)
    jobs_parser.add_argument("--json", action="store_true")
    jobs_parser.set_defaults(func=cmd_jobs)

    board_parser = sub.add_parser("blackboard")
    board_parser.add_argument("--json", action="store_true")
    board_parser.set_defaults(func=cmd_blackboard)

    pause_parser = sub.add_parser("pause")
    pause_parser.add_argument("--until", default=None)
    pause_parser.add_argument("--for-seconds", type=int, default=None)
    pause_parser.add_argument("--reason", default="manual pause")
    pause_parser.set_defaults(func=cmd_pause)

    resume_parser = sub.add_parser("resume")
    resume_parser.set_defaults(func=cmd_resume)

    repair_parser = sub.add_parser("repair")
    repair_parser.add_argument("--live", action="store_true")
    repair_parser.add_argument("--json", action="store_true")
    repair_parser.set_defaults(func=cmd_repair)

    reconcile_parser = sub.add_parser(
        "reconcile",
        help="pri_119 cold-start reconciliation pass (read+repair-bounded; never scans/dispatches)",
    )
    reconcile_parser.add_argument(
        "--live",
        action="store_true",
        help="Apply safe orphan recovery via existing repair primitive and emit audit event",
    )
    reconcile_parser.add_argument("--json", action="store_true")
    reconcile_parser.add_argument(
        "--log-freshness-seconds",
        type=float,
        default=None,
        help="Override the launch-log freshness threshold (default 600s)",
    )
    reconcile_parser.set_defaults(func=cmd_reconcile)

    maintenance_parser = sub.add_parser("maintenance")
    maintenance_sub = maintenance_parser.add_subparsers(dest="maintenance_action", required=True)

    compact_parser = maintenance_sub.add_parser("compact-reaction-jobs")
    compact_parser.add_argument("--live", action="store_true")
    compact_parser.add_argument("--states", default="queued,recoverable,claimed,running")
    compact_parser.add_argument("--all-states", action="store_true")
    compact_parser.add_argument("--limit", type=int, default=None)
    compact_parser.add_argument("--json", action="store_true")
    compact_parser.set_defaults(func=cmd_maintenance)

    vacuum_parser = maintenance_sub.add_parser("vacuum")
    vacuum_parser.add_argument("--live", action="store_true")
    vacuum_parser.add_argument("--allow-active", action="store_true")
    vacuum_parser.add_argument("--json", action="store_true")
    vacuum_parser.set_defaults(func=cmd_maintenance)
    db_eligibility_parser = maintenance_sub.add_parser("db-compaction-eligibility")
    db_eligibility_parser.add_argument("--json", action="store_true")
    db_eligibility_parser.add_argument("--dbstat-limit", type=int, default=12)
    db_eligibility_parser.add_argument("--dbstat-timeout-seconds", type=float, default=20.0)
    db_eligibility_parser.add_argument(
        "--include-dbstat",
        action="store_true",
        help="Collect largest-object dbstat evidence even when cheap blockers already decide eligibility.",
    )
    db_eligibility_parser.set_defaults(func=cmd_maintenance)
    events_eligibility_parser = maintenance_sub.add_parser("events-retention-eligibility")
    events_eligibility_parser.add_argument("--json", action="store_true")
    events_eligibility_parser.add_argument(
        "--sample-limit",
        type=int,
        default=EVENTS_RETENTION_DEFAULT_SAMPLE_LIMIT,
    )
    events_eligibility_parser.add_argument(
        "--payload-sample-limit",
        type=int,
        default=EVENTS_RETENTION_DEFAULT_PAYLOAD_SAMPLE_LIMIT,
    )
    events_eligibility_parser.add_argument(
        "--query-timeout-seconds",
        type=float,
        default=EVENTS_RETENTION_DEFAULT_QUERY_TIMEOUT_SECONDS,
    )
    events_eligibility_parser.set_defaults(func=cmd_maintenance)
    legacy_archive_parser = maintenance_sub.add_parser("legacy-event-payload-archive")
    legacy_archive_parser.add_argument("--live", action="store_true")
    legacy_archive_parser.add_argument("--allow-active", action="store_true")
    legacy_archive_parser.add_argument("--json", action="store_true")
    legacy_archive_parser.add_argument(
        "--chunk-size",
        type=int,
        default=LEGACY_EVENT_PAYLOAD_ARCHIVE_DEFAULT_CHUNK_SIZE,
    )
    legacy_archive_parser.add_argument(
        "--max-candidates",
        type=int,
        default=LEGACY_EVENT_PAYLOAD_ARCHIVE_DEFAULT_MAX_CANDIDATES,
    )
    legacy_archive_parser.add_argument(
        "--min-payload-bytes",
        type=int,
        default=EVENTS_RETENTION_OVERSIZED_PAYLOAD_BYTES,
    )
    legacy_archive_parser.add_argument("--oldest-first", action="store_true")
    legacy_archive_parser.add_argument("--archive-dir", default=None)
    legacy_archive_parser.set_defaults(func=cmd_maintenance)
    wal_checkpoint_parser = maintenance_sub.add_parser("wal-checkpoint")
    wal_checkpoint_parser.add_argument("--live", action="store_true")
    wal_checkpoint_parser.add_argument("--allow-active", action="store_true")
    wal_checkpoint_parser.add_argument("--json", action="store_true")
    wal_checkpoint_parser.set_defaults(func=cmd_maintenance)

    reprioritize_parser = maintenance_sub.add_parser("reprioritize-overnight")
    reprioritize_parser.add_argument("--live", action="store_true")
    reprioritize_parser.add_argument("--states", default="queued,recoverable")
    reprioritize_parser.add_argument("--all-states", action="store_true")
    reprioritize_parser.add_argument("--limit", type=int, default=None)
    reprioritize_parser.add_argument("--json", action="store_true")
    reprioritize_parser.set_defaults(func=cmd_maintenance)

    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.add_argument("--db-check", action="store_true")
    doctor_parser.add_argument("--full-integrity", action="store_true")
    doctor_parser.add_argument("--deep-signals", action="store_true")
    doctor_parser.set_defaults(func=cmd_doctor)

    market_parser = sub.add_parser("market")
    market_parser.add_argument(
        "market_action",
        choices=["status", "emit", "config", "configure"],
        help=(
            "status: report current market schedule/runtime state. "
            "emit: compute and enqueue due fires. "
            "config: show effective config and universe. "
            "configure: apply narrow operator-safe config updates."
        ),
    )
    market_parser.add_argument("--json", action="store_true")
    market_parser.add_argument("--enable", action="store_true")
    market_parser.add_argument("--disable", action="store_true")
    market_parser.add_argument("--timezone", default=None)
    market_parser.add_argument("--grace-minutes", type=int, default=None)
    market_parser.add_argument(
        "--weekday-open-close",
        action="store_true",
        help="Use the canonical US weekday 09:30/16:00 America/New_York feed schedule.",
    )
    market_parser.add_argument(
        "--market-hours-hourly",
        action="store_true",
        help="Use the US weekday 09:30 open, hourly 10:30-15:30, and 16:00 close feed schedule.",
    )
    market_parser.add_argument("--universe-file", default=None)
    market_parser.add_argument("--use-default-universe", action="store_true")
    market_parser.set_defaults(func=cmd_market)

    governor_parser = sub.add_parser("governor")
    governor_sub = governor_parser.add_subparsers(dest="governor_action", required=True)

    governor_status_parser = governor_sub.add_parser("status")
    governor_status_parser.add_argument("--json", action="store_true")
    governor_status_parser.set_defaults(func=cmd_governor)

    governor_set_parser = governor_sub.add_parser("set-mode")
    governor_set_parser.add_argument("mode", choices=governor.valid_modes())
    governor_set_parser.add_argument("--enabled", action=argparse.BooleanOptionalAction, default=None)
    governor_set_parser.add_argument("--cost-posture", default=None)
    governor_set_parser.add_argument("--paid-spend-usd-daily-cap", type=float, default=None)
    governor_set_parser.add_argument("--json", action="store_true")
    governor_set_parser.set_defaults(func=cmd_governor)

    raw_seed_parser = sub.add_parser("raw-seed")
    raw_seed_sub = raw_seed_parser.add_subparsers(dest="raw_seed_action", required=True)

    raw_seed_status_parser = raw_seed_sub.add_parser("status")
    raw_seed_status_parser.add_argument("--json", action="store_true")
    raw_seed_status_parser.set_defaults(func=cmd_raw_seed_status)

    raw_seed_entries_parser = raw_seed_sub.add_parser("entries")
    raw_seed_entries_parser.add_argument("--family", default=None)
    raw_seed_entries_parser.add_argument("--limit", type=int, default=20)
    raw_seed_entries_parser.add_argument("--json", action="store_true")
    raw_seed_entries_parser.set_defaults(func=cmd_raw_seed_entries)

    install_parser = sub.add_parser("install-launch-agent")
    install_parser.set_defaults(func=cmd_install_launch_agent)

    uninstall_parser = sub.add_parser("uninstall-launch-agent")
    uninstall_parser.set_defaults(func=cmd_uninstall_launch_agent)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
