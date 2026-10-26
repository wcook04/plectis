#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parent
OBSERVE_HISTORY_DIR = REPO_ROOT / "tools/meta/apply/observe_history"
CONTROL_STATE_PATH = OBSERVE_HISTORY_DIR / "pipeline_control_state.json"

PIPELINE_AUTOPILOT_LABEL = "com.aiworkflow.pipeline-autopilot"
CODEX_SIGNAL_WATCHER_LABEL = "com.aiworkflow.codex-signal-watcher"
CLAUDE_SIGNAL_WATCHER_LABEL = "com.aiworkflow.claude-signal-watcher"
CURSOR_SIGNAL_WATCHER_LABEL = "com.aiworkflow.cursor-signal-watcher"
PIPELINE_LAUNCH_AGENT_LABELS = (
    PIPELINE_AUTOPILOT_LABEL,
    CODEX_SIGNAL_WATCHER_LABEL,
    CLAUDE_SIGNAL_WATCHER_LABEL,
    CURSOR_SIGNAL_WATCHER_LABEL,
)

DEFAULT_PIPELINE_LAUNCH_PROFILE = "safe"
DEFAULT_PIPELINE_SLEEP_POLICY = "system"
VALID_PIPELINE_SLEEP_POLICIES = {"system", "keep_awake"}
WAKE_LOCK_COMMAND = ["caffeinate", "-dimsu"]
DEFAULT_ORCHESTRATOR_AGENT = "codex"
VALID_ORCHESTRATOR_AGENTS = {"none", "codex", "claude", "cursor", "both", "all"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _config_value(value: Any, default: Any = None) -> Any:
    if isinstance(value, Mapping) and "value" in value:
        return value.get("value")
    return value if value is not None else default


def _read_json(path: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})
    return dict(payload) if isinstance(payload, dict) else dict(default or {})


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_master_config(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    from system.lib.kernel.config import load_master_config_at
    return load_master_config_at(repo_root)


def normalize_launch_profile(value: Any, *, default: str = DEFAULT_PIPELINE_LAUNCH_PROFILE) -> str:
    token = str(value or "").strip().lower()
    return token if token in {"safe", "experimental"} else default


def normalize_sleep_policy(value: Any, *, default: str = DEFAULT_PIPELINE_SLEEP_POLICY) -> str:
    token = str(value or "").strip().lower()
    return token if token in VALID_PIPELINE_SLEEP_POLICIES else default


def normalize_orchestrator_agent(
    value: Any,
    *,
    default: str = DEFAULT_ORCHESTRATOR_AGENT,
) -> str:
    token = str(value or "").strip().lower()
    return token if token in VALID_ORCHESTRATOR_AGENTS else default


def orchestrator_runtime_config(repo_root: Path = REPO_ROOT) -> dict[str, str]:
    config = load_master_config(repo_root)
    pipeline_cfg = config.get("pipeline")
    if not isinstance(pipeline_cfg, Mapping):
        pipeline_cfg = {}
    return {
        "primary": normalize_orchestrator_agent(
            _config_value(
                pipeline_cfg.get("orchestrator_primary"),
                DEFAULT_ORCHESTRATOR_AGENT,
            )
        ),
        "fallback": normalize_orchestrator_agent(
            _config_value(pipeline_cfg.get("orchestrator_fallback"), "claude"),
            default="claude",
        ),
    }


def resolve_wake_agent(value: Any = None, *, repo_root: Path = REPO_ROOT) -> str:
    token = str(value or "").strip().lower()
    if token and token != "auto":
        return normalize_orchestrator_agent(token)
    return str(orchestrator_runtime_config(repo_root)["primary"])


def pipeline_runtime_config(repo_root: Path = REPO_ROOT) -> dict[str, str]:
    config = load_master_config(repo_root)
    pipeline_cfg = config.get("pipeline")
    if not isinstance(pipeline_cfg, Mapping):
        pipeline_cfg = {}
    return {
        "default_launch_profile": normalize_launch_profile(
            _config_value(pipeline_cfg.get("default_launch_profile"), DEFAULT_PIPELINE_LAUNCH_PROFILE)
        ),
        "sleep_policy": normalize_sleep_policy(
            _config_value(pipeline_cfg.get("sleep_policy"), DEFAULT_PIPELINE_SLEEP_POLICY)
        ),
    }


def resolve_sleep_policy(value: Any = None, *, repo_root: Path = REPO_ROOT) -> str:
    runtime_policy = pipeline_runtime_config(repo_root)
    default = str(runtime_policy["sleep_policy"])
    if value is not None and str(value).strip():
        return normalize_sleep_policy(value, default=default)

    control_state = load_control_state(repo_root)
    wake_lock = control_state.get("wake_lock") if isinstance(control_state.get("wake_lock"), Mapping) else {}
    control_value = wake_lock.get("sleep_policy")
    if control_value is not None and str(control_value).strip():
        return normalize_sleep_policy(control_value, default=default)
    return default


def load_control_state(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    path = repo_root / CONTROL_STATE_PATH.relative_to(REPO_ROOT)
    default = {
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "paused": False,
        "pause_reason": None,
        "paused_at": None,
        "resumed_at": None,
        "wake_lock": {
            "sleep_policy": DEFAULT_PIPELINE_SLEEP_POLICY,
            "enabled": False,
            "pid": None,
            "started_at": None,
            "command": None,
        },
    }
    state = _read_json(path, default=default)
    state.setdefault("paused", False)
    state.setdefault("pause_reason", None)
    state.setdefault("paused_at", None)
    state.setdefault("resumed_at", None)
    wake_lock = state.get("wake_lock")
    if not isinstance(wake_lock, dict):
        wake_lock = {}
    wake_lock.setdefault("sleep_policy", DEFAULT_PIPELINE_SLEEP_POLICY)
    wake_lock.setdefault("enabled", False)
    wake_lock.setdefault("pid", None)
    wake_lock.setdefault("started_at", None)
    wake_lock.setdefault("command", None)
    state["wake_lock"] = wake_lock
    return state


def save_control_state(state: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> Path:
    payload = dict(state)
    payload["updated_at"] = _utc_now()
    path = repo_root / CONTROL_STATE_PATH.relative_to(REPO_ROOT)
    _write_json(path, payload)
    return path


def is_pipeline_paused(repo_root: Path = REPO_ROOT) -> bool:
    return bool(load_control_state(repo_root).get("paused"))


def launch_agent_dest(label: str) -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{label}.plist"


def launch_agent_service(label: str) -> str:
    return f"gui/{os.getuid()}/{label}"


def mark_pipeline_paused(
    *,
    reason: str,
    repo_root: Path = REPO_ROOT,
    sleep_policy: str | None = None,
) -> dict[str, Any]:
    state = load_control_state(repo_root)
    state["paused"] = True
    state["pause_reason"] = str(reason or "").strip() or "paused"
    state["paused_at"] = _utc_now()
    if sleep_policy is not None:
        state["wake_lock"]["sleep_policy"] = normalize_sleep_policy(sleep_policy)
    save_control_state(state, repo_root)
    return state


def mark_pipeline_resumed(
    *,
    repo_root: Path = REPO_ROOT,
    sleep_policy: str | None = None,
) -> dict[str, Any]:
    state = load_control_state(repo_root)
    state["paused"] = False
    state["pause_reason"] = None
    state["resumed_at"] = _utc_now()
    if sleep_policy is not None:
        state["wake_lock"]["sleep_policy"] = normalize_sleep_policy(sleep_policy)
    save_control_state(state, repo_root)
    return state


def _pid_running(pid: Any) -> bool:
    try:
        parsed = int(pid)
    except (TypeError, ValueError):
        return False
    if parsed <= 0:
        return False
    try:
        os.kill(parsed, 0)
    except OSError:
        return False
    return True


def _wake_lock_process_command(pid: Any) -> str | None:
    try:
        parsed = int(pid)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    try:
        proc = subprocess.run(
            ["ps", "-p", str(parsed), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    command = (proc.stdout or "").strip()
    return command or None


def _command_is_caffeinate(command: str | None) -> bool:
    if not command:
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    if not parts:
        return False
    return Path(parts[0]).name == "caffeinate"


def wake_lock_status(
    *,
    repo_root: Path = REPO_ROOT,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    control_state = dict(state) if state is not None else load_control_state(repo_root)
    wake_lock_raw = control_state.get("wake_lock")
    wake_lock = dict(wake_lock_raw) if isinstance(wake_lock_raw, Mapping) else {}
    sleep_policy = normalize_sleep_policy(wake_lock.get("sleep_policy"))
    desired = sleep_policy == "keep_awake"
    pid = wake_lock.get("pid")
    pid_running = _pid_running(pid)
    process_command = _wake_lock_process_command(pid) if pid_running else None
    process_matches = _command_is_caffeinate(process_command)
    caffeinate_path = shutil.which("caffeinate")

    if not desired:
        status = "not_requested"
        reason = "sleep_policy_not_keep_awake"
    elif process_matches:
        status = "active"
        reason = "stored_pid_is_caffeinate"
    elif pid_running:
        status = "stale_pid_reused"
        reason = "stored_pid_running_but_not_caffeinate"
    elif pid:
        status = "stale_pid_dead"
        reason = "stored_pid_not_running"
    elif wake_lock.get("enabled"):
        status = "enabled_without_pid"
        reason = "enabled_but_no_pid"
    elif not caffeinate_path:
        status = "unavailable"
        reason = "caffeinate_not_found"
    else:
        status = "inactive"
        reason = "keep_awake_requested_without_active_process"

    return {
        "schema": "pipeline_wake_lock_status_v0",
        "status": status,
        "reason": reason,
        "sleep_policy": sleep_policy,
        "desired": desired,
        "enabled": bool(wake_lock.get("enabled")),
        "pid": pid,
        "pid_running": pid_running,
        "process_command": process_command,
        "process_matches": process_matches,
        "caffeinate_available": bool(caffeinate_path),
        "caffeinate_path": caffeinate_path,
        "last_error": wake_lock.get("last_error"),
        "last_error_at": wake_lock.get("last_error_at"),
    }


def stop_wake_lock(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    state = load_control_state(repo_root)
    wake_lock = dict(state.get("wake_lock") or {})
    status = wake_lock_status(repo_root=repo_root, state=state)
    pid = wake_lock.get("pid")
    if status["process_matches"]:
        try:
            os.kill(int(pid), 15)
        except OSError:
            pass
    wake_lock.update(
        {
            "enabled": False,
            "pid": None,
            "started_at": None,
            "command": None,
            "stopped_at": _utc_now(),
        }
    )
    state["wake_lock"] = wake_lock
    save_control_state(state, repo_root)
    return state


def ensure_wake_lock(
    *,
    sleep_policy: str,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    normalized_policy = normalize_sleep_policy(sleep_policy)
    state = load_control_state(repo_root)
    wake_lock = dict(state.get("wake_lock") or {})
    wake_lock["sleep_policy"] = normalized_policy
    state["wake_lock"] = wake_lock

    if normalized_policy != "keep_awake":
        save_control_state(state, repo_root)
        return stop_wake_lock(repo_root=repo_root)

    status = wake_lock_status(repo_root=repo_root, state=state)
    if status["status"] == "active":
        wake_lock.update(
            {
                "enabled": True,
                "pid": status["pid"],
                "command": wake_lock.get("command") or list(WAKE_LOCK_COMMAND),
                "last_error": None,
                "last_error_at": None,
            }
        )
        state["wake_lock"] = wake_lock
        save_control_state(state, repo_root)
        return state

    if not status["caffeinate_available"]:
        wake_lock.update(
            {
                "enabled": False,
                "pid": None,
                "started_at": None,
                "command": None,
                "last_error": "caffeinate_not_found",
                "last_error_at": _utc_now(),
            }
        )
        state["wake_lock"] = wake_lock
        save_control_state(state, repo_root)
        raise RuntimeError("keep_awake requested but caffeinate is not available")

    try:
        proc = subprocess.Popen(
            WAKE_LOCK_COMMAND,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        wake_lock.update(
            {
                "enabled": False,
                "pid": None,
                "started_at": None,
                "command": None,
                "last_error": f"caffeinate_launch_failed: {exc}",
                "last_error_at": _utc_now(),
            }
        )
        state["wake_lock"] = wake_lock
        save_control_state(state, repo_root)
        raise RuntimeError("failed to start caffeinate for keep_awake") from exc

    wake_lock.update(
        {
            "enabled": True,
            "pid": proc.pid,
            "started_at": _utc_now(),
            "command": list(WAKE_LOCK_COMMAND),
            "last_error": None,
            "last_error_at": None,
        }
    )
    state["wake_lock"] = wake_lock
    save_control_state(state, repo_root)
    return state


__all__ = [
    "CLAUDE_SIGNAL_WATCHER_LABEL",
    "CODEX_SIGNAL_WATCHER_LABEL",
    "CURSOR_SIGNAL_WATCHER_LABEL",
    "CONTROL_STATE_PATH",
    "DEFAULT_PIPELINE_LAUNCH_PROFILE",
    "DEFAULT_PIPELINE_SLEEP_POLICY",
    "OBSERVE_HISTORY_DIR",
    "PIPELINE_AUTOPILOT_LABEL",
    "PIPELINE_LAUNCH_AGENT_LABELS",
    "REPO_ROOT",
    "ensure_wake_lock",
    "is_pipeline_paused",
    "launch_agent_dest",
    "launch_agent_service",
    "load_control_state",
    "load_master_config",
    "mark_pipeline_paused",
    "mark_pipeline_resumed",
    "normalize_orchestrator_agent",
    "normalize_launch_profile",
    "normalize_sleep_policy",
    "orchestrator_runtime_config",
    "pipeline_runtime_config",
    "resolve_wake_agent",
    "resolve_sleep_policy",
    "save_control_state",
    "stop_wake_lock",
    "wake_lock_status",
]
