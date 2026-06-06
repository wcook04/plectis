"""
Always-on governor for metabolismd.

[PURPOSE]
- Teleology: Give the repo-local daemon one explicit gas pedal for active,
  trickle, overnight, sprint, and paused operation without inventing a second
  scheduler.
- Mechanism: Merge a small persisted setting with authored mode profiles and
  project effective scheduler/provider budgets for metabolismd and Zenith.
- Non-goal: Dispatch work directly. This module only describes and gates the
  existing metabolism scheduler.
"""
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from system.lib import metabolism_store as store


SETTING_KEY = "always_on_governor"
DISPATCH_HISTORY_KEY = "provider_dispatch_history"
SCHEMA = "always_on_governor_v1"
DEFAULT_MODE = "trickle"
DEFAULT_COST_POSTURE = "free_first_no_paid_auto"
OPENROUTER_PAID_HISTORY_FREE_MIN_SECONDS = 90
LOCAL_LOAD_GATE_SCHEMA = "local_load_gate_v0"
LOCAL_PRESSURE_SCHEMA = "local_pressure_v0"
LOCAL_PRESSURE_HISTORY_KEY = "local_pressure_history"
REMOTE_LIGHT_LOCAL_LIGHT = "remote_light_local_light"
REMOTE_LIGHT_LOCAL_HEAVY = "remote_light_local_heavy"
LOCAL_HEAVY = "local_heavy"
GRAPH_REBUILD_HEAVY = "graph_rebuild_heavy"
EMBEDDING_HEAVY = "embedding_heavy"
LOCAL_COST_CLASSES = frozenset(
    {
        REMOTE_LIGHT_LOCAL_LIGHT,
        REMOTE_LIGHT_LOCAL_HEAVY,
        LOCAL_HEAVY,
        GRAPH_REBUILD_HEAVY,
        EMBEDDING_HEAVY,
    }
)
HEAVY_LOCAL_COST_CLASSES = frozenset(
    {
        REMOTE_LIGHT_LOCAL_HEAVY,
        LOCAL_HEAVY,
        GRAPH_REBUILD_HEAVY,
        EMBEDDING_HEAVY,
    }
)
LOCAL_LOAD_PER_CPU_LIMITS = {
    "paused": 0.0,
    "trickle": 0.70,
    "active": 0.85,
    "overnight": 1.25,
    "sprint": 1.50,
}
TRICKLE_ALLOWED_LOCAL_COST_CLASSES = frozenset({REMOTE_LIGHT_LOCAL_LIGHT})
LOCAL_PRESSURE_SWAP_USED_BYTES_LIMIT = 1 * 1024 * 1024 * 1024
LOCAL_PRESSURE_COMPRESSED_MEMORY_BYTES_LIMIT = 4 * 1024 * 1024 * 1024
LOCAL_PRESSURE_DISK_TOTAL_MB_S_LIMIT = 100.0
LOCAL_PRESSURE_WINDOWSERVER_CPU_LIMIT = 35.0
LOCAL_PRESSURE_RED_COOLDOWN_SECONDS = 900
BACKGROUND_TASKPOLICY_COST_CLASSES = frozenset(
    {
        REMOTE_LIGHT_LOCAL_HEAVY,
        LOCAL_HEAVY,
        GRAPH_REBUILD_HEAVY,
        EMBEDDING_HEAVY,
    }
)
OPERATION_LOCAL_COST_CLASSES = {
    "kernel_embed_refresh": EMBEDDING_HEAVY,
    "navigator_refresh": EMBEDDING_HEAVY,
    "semantic_route_refresh": GRAPH_REBUILD_HEAVY,
    "nvidia_continuous_navigation_populate": REMOTE_LIGHT_LOCAL_HEAVY,
}
REMOTE_PROVIDER_DEFAULT_MAX_ATTEMPTS = {
    "chatgpt": 5,
    "claude": 5,
    "codex": 5,
    "gemini": 5,
    "nvidia": 3,
    "openrouter_free": 3,
}

MODE_PROFILES: dict[str, dict[str, Any]] = {
    "paused": {
        "label": "Paused",
        "description": "No automatic dispatch. Status/doctor/projections still work.",
        "dispatch_enabled": False,
        "scheduler": {"poll_seconds": 30, "scan_interval_seconds": 300},
        "provider_overrides": {
            "chatgpt": {"max_concurrent": 0},
            "gemini": {"max_concurrent": 0},
            "claude": {"max_concurrent": 0},
            "codex": {"max_concurrent": 0},
            "nvidia": {"max_concurrent": 0},
            "openrouter_free": {"max_concurrent": 0},
            "local": {"max_concurrent": 1},
        },
    },
    "trickle": {
        "label": "Trickle",
        "description": "Low-friction background metabolism while the operator is active.",
        "dispatch_enabled": True,
        "scheduler": {"poll_seconds": 20, "scan_interval_seconds": 300},
        "provider_overrides": {
            "chatgpt": {"max_concurrent": 1, "min_seconds_between_dispatch": 60},
            "gemini": {"max_concurrent": 1, "min_seconds_between_dispatch": 120},
            "claude": {"max_concurrent": 0},
            "codex": {"max_concurrent": 0},
            "nvidia": {"max_concurrent": 1, "min_seconds_between_dispatch": 5},
            "openrouter_free": {
                "max_concurrent": 1,
                "min_seconds_between_dispatch": OPENROUTER_PAID_HISTORY_FREE_MIN_SECONDS,
                "free_only": True,
                "allow_paid": False,
                "rate_limit_source": "openrouter_paid_history_free_variant_daily_cap",
            },
            "local": {"max_concurrent": 2, "min_seconds_between_dispatch": 0},
        },
    },
    "active": {
        "label": "Active",
        "description": "Normal awake operation with conservative remote pressure.",
        "dispatch_enabled": True,
        "scheduler": {"poll_seconds": 10, "scan_interval_seconds": 180},
        "provider_overrides": {
            "chatgpt": {"max_concurrent": 1, "min_seconds_between_dispatch": 45},
            "gemini": {"max_concurrent": 1, "min_seconds_between_dispatch": 60},
            "claude": {"max_concurrent": 0},
            "codex": {"max_concurrent": 1, "min_seconds_between_dispatch": 120},
            "nvidia": {"max_concurrent": 1, "min_seconds_between_dispatch": 2},
            "openrouter_free": {
                "max_concurrent": 1,
                "min_seconds_between_dispatch": OPENROUTER_PAID_HISTORY_FREE_MIN_SECONDS,
                "free_only": True,
                "allow_paid": False,
                "rate_limit_source": "openrouter_paid_history_free_variant_daily_cap",
            },
            "local": {"max_concurrent": 2, "min_seconds_between_dispatch": 0},
        },
    },
    "overnight": {
        "label": "Overnight",
        "description": "Away-from-keyboard metabolism: broader Bridge/NVIDIA use, still no paid OpenRouter spend.",
        "dispatch_enabled": True,
        "scheduler": {"poll_seconds": 5, "scan_interval_seconds": 300},
        "provider_overrides": {
            "chatgpt": {"max_concurrent": 2, "min_seconds_between_dispatch": 30},
            "gemini": {"max_concurrent": 1, "min_seconds_between_dispatch": 45},
            "claude": {"max_concurrent": 0},
            "codex": {"max_concurrent": 1, "min_seconds_between_dispatch": 90},
            "nvidia": {"max_concurrent": 1, "min_seconds_between_dispatch": 2},
            "openrouter_free": {
                "max_concurrent": 1,
                "min_seconds_between_dispatch": OPENROUTER_PAID_HISTORY_FREE_MIN_SECONDS,
                "free_only": True,
                "allow_paid": False,
                "rate_limit_source": "openrouter_paid_history_free_variant_daily_cap",
            },
            "local": {"max_concurrent": 2, "min_seconds_between_dispatch": 0},
        },
    },
    "sprint": {
        "label": "Sprint",
        "description": "Short manual burst. Still keeps OpenRouter paid spend disabled.",
        "dispatch_enabled": True,
        "scheduler": {"poll_seconds": 3, "scan_interval_seconds": 120},
        "provider_overrides": {
            "chatgpt": {"max_concurrent": 3, "min_seconds_between_dispatch": 20},
            "gemini": {"max_concurrent": 2, "min_seconds_between_dispatch": 30},
            "claude": {"max_concurrent": 0},
            "codex": {"max_concurrent": 1, "min_seconds_between_dispatch": 60},
            "nvidia": {"max_concurrent": 1, "min_seconds_between_dispatch": 2},
            "openrouter_free": {
                "max_concurrent": 1,
                "min_seconds_between_dispatch": OPENROUTER_PAID_HISTORY_FREE_MIN_SECONDS,
                "free_only": True,
                "allow_paid": False,
                "rate_limit_source": "openrouter_paid_history_free_variant_daily_cap",
            },
            "local": {"max_concurrent": 3, "min_seconds_between_dispatch": 0},
        },
    },
}


def default_setting() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "enabled": True,
        "mode": DEFAULT_MODE,
        "cost_posture": DEFAULT_COST_POSTURE,
        "paid_spend_usd_daily_cap": 0.0,
        "notes": "Free-first always-on posture. OpenRouter automatic lane must remain free-only.",
    }


def valid_modes() -> list[str]:
    return sorted(MODE_PROFILES)


def load_setting(conn) -> dict[str, Any]:
    raw = store.get_setting(conn, SETTING_KEY, None)
    payload = default_setting()
    if isinstance(raw, Mapping):
        payload.update(dict(raw))
    mode = str(payload.get("mode") or DEFAULT_MODE).strip().lower()
    if mode not in MODE_PROFILES:
        mode = DEFAULT_MODE
    payload["mode"] = mode
    payload["enabled"] = bool(payload.get("enabled", True))
    payload["paid_spend_usd_daily_cap"] = float(payload.get("paid_spend_usd_daily_cap") or 0.0)
    if not str(payload.get("cost_posture") or "").strip():
        payload["cost_posture"] = DEFAULT_COST_POSTURE
    return payload


def set_mode(
    conn,
    *,
    mode: str,
    enabled: bool | None = None,
    cost_posture: str | None = None,
    paid_spend_usd_daily_cap: float | None = None,
) -> dict[str, Any]:
    token = str(mode or "").strip().lower()
    if token not in MODE_PROFILES:
        raise ValueError(f"unknown always-on governor mode: {mode}")
    payload = load_setting(conn)
    payload["mode"] = token
    if enabled is not None:
        payload["enabled"] = bool(enabled)
    if cost_posture is not None:
        payload["cost_posture"] = str(cost_posture or "").strip() or DEFAULT_COST_POSTURE
    if paid_spend_usd_daily_cap is not None:
        payload["paid_spend_usd_daily_cap"] = max(float(paid_spend_usd_daily_cap), 0.0)
    payload["updated_at"] = store.utc_now()
    store.set_setting(conn, SETTING_KEY, payload)
    return payload


def active_profile(conn) -> dict[str, Any]:
    setting = load_setting(conn)
    profile = dict(MODE_PROFILES[setting["mode"]])
    if not setting.get("enabled", True):
        profile = dict(MODE_PROFILES["paused"])
        profile["label"] = "Disabled"
        profile["description"] = "Always-on governor disabled; automatic dispatch is treated as paused."
    return profile


def effective_scheduler_settings(conn) -> dict[str, Any]:
    base = dict(store.get_setting(conn, "scheduler", {}) or {})
    profile = active_profile(conn)
    base.update(dict(profile.get("scheduler") or {}))
    return base


def effective_provider_budget(conn, provider: str, base_budget: Mapping[str, Any] | None = None) -> dict[str, Any]:
    normalized = str(provider or "").strip().lower()
    budget = dict(base_budget or {})
    profile = active_profile(conn)
    overrides = dict((profile.get("provider_overrides") or {}).get(normalized) or {})
    budget.update(overrides)
    if normalized in REMOTE_PROVIDER_DEFAULT_MAX_ATTEMPTS:
        budget.setdefault("max_attempts", REMOTE_PROVIDER_DEFAULT_MAX_ATTEMPTS[normalized])
    if normalized == "openrouter_free":
        budget["free_only"] = True
        budget["allow_paid"] = False
        budget["paid_spend_usd_daily_cap"] = 0.0
        budget.setdefault("min_seconds_between_dispatch", OPENROUTER_PAID_HISTORY_FREE_MIN_SECONDS)
        budget.setdefault("rate_limit_source", "openrouter_paid_history_free_variant_daily_cap")
    return budget


def dispatch_enabled(conn) -> tuple[bool, str]:
    setting = load_setting(conn)
    profile = active_profile(conn)
    if not setting.get("enabled", True):
        return False, "always-on governor disabled"
    if not bool(profile.get("dispatch_enabled", True)):
        return False, f"always-on governor mode is {setting['mode']}"
    return True, ""


def local_load_snapshot() -> dict[str, Any]:
    """Return a small local load snapshot for always-on heat gates.

    This is intentionally stdlib-only and best-effort.  Unsupported platforms
    still emit a structured ``unavailable`` state so callers can avoid treating
    missing telemetry as permission for heavy local work.
    """
    cpu_count = int(os.cpu_count() or 1)
    try:
        load_1m, load_5m, load_15m = os.getloadavg()
    except (AttributeError, OSError):
        return {
            "schema": LOCAL_LOAD_GATE_SCHEMA,
            "status": "unavailable",
            "cpu_count": cpu_count,
            "load_1m": None,
            "load_5m": None,
            "load_15m": None,
            "load_per_cpu_1m": None,
        }
    return {
        "schema": LOCAL_LOAD_GATE_SCHEMA,
        "status": "available",
        "cpu_count": cpu_count,
        "load_1m": round(float(load_1m), 4),
        "load_5m": round(float(load_5m), 4),
        "load_15m": round(float(load_15m), 4),
        "load_per_cpu_1m": round(float(load_1m) / max(cpu_count, 1), 4),
    }


def normalize_local_cost_class(local_cost_class: str | None) -> str:
    cost_class = str(local_cost_class or REMOTE_LIGHT_LOCAL_LIGHT).strip() or REMOTE_LIGHT_LOCAL_LIGHT
    if cost_class not in LOCAL_COST_CLASSES:
        return LOCAL_HEAVY
    return cost_class


def is_heavy_local_cost_class(local_cost_class: str | None) -> bool:
    return normalize_local_cost_class(local_cost_class) in HEAVY_LOCAL_COST_CLASSES


def operation_local_cost_class(
    operation_id: str | None,
    operation_parameters: Mapping[str, Any] | None = None,
) -> str:
    del operation_parameters
    operation = str(operation_id or "").strip()
    return OPERATION_LOCAL_COST_CLASSES.get(operation, REMOTE_LIGHT_LOCAL_LIGHT)


def job_local_cost_class(job: Mapping[str, Any]) -> str:
    params = dict(job.get("params") or {})
    operation_id = str(params.get("operation_id") or job.get("kind") or "").strip()
    return operation_local_cost_class(operation_id, dict(params.get("operation_parameters") or {}))


def should_launch_with_background_policy(local_cost_class: str | None) -> bool:
    return normalize_local_cost_class(local_cost_class) in BACKGROUND_TASKPOLICY_COST_CLASSES


def _run_text(cmd: list[str], *, timeout: float = 0.75) -> str:
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return str(result.stdout or "")


def _unit_bytes(raw_number: str, raw_unit: str) -> int | None:
    try:
        value = float(raw_number)
    except (TypeError, ValueError):
        return None
    unit = str(raw_unit or "").strip().upper()
    multipliers = {
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }
    return int(value * multipliers.get(unit[:1], 1))


def _gb(value: int | float | None) -> float | None:
    if value is None:
        return None
    return round(float(value) / float(1024**3), 3)


def _parse_swap_used_bytes(text: str) -> int | None:
    match = re.search(r"\bused\s*=\s*([0-9.]+)\s*([KMGT])", text, flags=re.IGNORECASE)
    if not match:
        return None
    return _unit_bytes(match.group(1), match.group(2))


def _parse_vm_stat(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    page_size_match = re.search(r"page size of\s+([0-9]+)\s+bytes", text, flags=re.IGNORECASE)
    page_size = int(page_size_match.group(1)) if page_size_match else 4096
    counters: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value_match = re.search(r"([0-9]+)", raw_value.replace(".", ""))
        if value_match:
            counters[key.strip().strip('"').lower()] = int(value_match.group(1))
    stored_pages = counters.get("pages stored in compressor")
    occupied_pages = counters.get("pages occupied by compressor")
    return {
        "page_size": page_size,
        "compressed_memory_bytes": stored_pages * page_size if stored_pages is not None else None,
        "compressor_occupied_bytes": occupied_pages * page_size if occupied_pages is not None else None,
    }


def _parse_memory_free_percent(text: str) -> float | None:
    match = re.search(r"free percentage:\s*([0-9.]+)%", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return round(float(match.group(1)), 2)
    except ValueError:
        return None


def _parse_window_server_cpu(text: str) -> float | None:
    values: list[float] = []
    for line in text.splitlines():
        if "WindowServer" not in line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        command = parts[3]
        if "WindowServer" not in command or "rg " in command:
            continue
        try:
            values.append(float(parts[2]))
        except ValueError:
            continue
    if not values:
        return None
    return round(max(values), 2)


def _parse_iostat_total_mb_s(text: str) -> float | None:
    rows = [line.split() for line in text.splitlines() if line.split()]
    for parts in reversed(rows):
        if len(parts) < 3:
            continue
        try:
            return round(float(parts[-1]), 2)
        except ValueError:
            continue
    return None


def local_pressure_snapshot(*, sample_disk: bool = False) -> dict[str, Any]:
    swap_used_bytes = _parse_swap_used_bytes(_run_text(["sysctl", "vm.swapusage"]))
    vm_stat = _parse_vm_stat(_run_text(["vm_stat"]))
    memory_free_percent = _parse_memory_free_percent(_run_text(["memory_pressure", "-Q"]))
    window_server_cpu = _parse_window_server_cpu(
        _run_text(["ps", "-axo", "user,pid,pcpu,command"])
    )
    disk_total_mb_s = None
    if sample_disk:
        disk_total_mb_s = _parse_iostat_total_mb_s(
            _run_text(["iostat", "-d", "-w", "1", "-c", "2"], timeout=1.75)
        )

    compressed_memory_bytes = vm_stat.get("compressed_memory_bytes")
    red_reasons: list[str] = []
    if swap_used_bytes is not None and swap_used_bytes > LOCAL_PRESSURE_SWAP_USED_BYTES_LIMIT:
        red_reasons.append(
            f"swap used {_gb(swap_used_bytes)} GB > {_gb(LOCAL_PRESSURE_SWAP_USED_BYTES_LIMIT)} GB"
        )
    if (
        compressed_memory_bytes is not None
        and compressed_memory_bytes > LOCAL_PRESSURE_COMPRESSED_MEMORY_BYTES_LIMIT
    ):
        red_reasons.append(
            "compressed memory "
            f"{_gb(compressed_memory_bytes)} GB > {_gb(LOCAL_PRESSURE_COMPRESSED_MEMORY_BYTES_LIMIT)} GB"
        )
    if (
        window_server_cpu is not None
        and window_server_cpu > LOCAL_PRESSURE_WINDOWSERVER_CPU_LIMIT
    ):
        red_reasons.append(
            f"WindowServer CPU {window_server_cpu}% > {LOCAL_PRESSURE_WINDOWSERVER_CPU_LIMIT}%"
        )
    if (
        disk_total_mb_s is not None
        and disk_total_mb_s > LOCAL_PRESSURE_DISK_TOTAL_MB_S_LIMIT
    ):
        red_reasons.append(
            f"disk throughput {disk_total_mb_s} MB/s > {LOCAL_PRESSURE_DISK_TOTAL_MB_S_LIMIT} MB/s"
        )
    observed_any = any(
        value is not None
        for value in (
            swap_used_bytes,
            compressed_memory_bytes,
            memory_free_percent,
            window_server_cpu,
            disk_total_mb_s,
        )
    )
    return {
        "schema": LOCAL_PRESSURE_SCHEMA,
        "status": "available" if observed_any else "unavailable",
        "generated_at": store.utc_now(),
        "sample_disk": bool(sample_disk),
        "pressure_state": "red" if red_reasons else ("green" if observed_any else "unknown"),
        "red_reasons": red_reasons,
        "swap_used_bytes": swap_used_bytes,
        "swap_used_gb": _gb(swap_used_bytes),
        "compressed_memory_bytes": compressed_memory_bytes,
        "compressed_memory_gb": _gb(compressed_memory_bytes),
        "compressor_occupied_bytes": vm_stat.get("compressor_occupied_bytes"),
        "compressor_occupied_gb": _gb(vm_stat.get("compressor_occupied_bytes")),
        "memory_free_percent": memory_free_percent,
        "window_server_cpu_percent": window_server_cpu,
        "disk_total_mb_s": disk_total_mb_s,
        "thermal_state": "unavailable",
    }


def _to_aware_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _record_pressure_red(conn, pressure: Mapping[str, Any], *, now: datetime) -> None:
    reasons = [str(reason) for reason in pressure.get("red_reasons") or [] if str(reason).strip()]
    payload = {
        "schema": "local_pressure_history_v0",
        "last_red_at": now.isoformat(),
        "last_red_reasons": reasons,
        "cooldown_seconds": LOCAL_PRESSURE_RED_COOLDOWN_SECONDS,
    }
    store.set_setting(conn, LOCAL_PRESSURE_HISTORY_KEY, payload)


def _recent_red_cooldown_reason(conn, *, now: datetime) -> str:
    raw = store.get_setting(conn, LOCAL_PRESSURE_HISTORY_KEY, {}) or {}
    if not isinstance(raw, Mapping):
        return ""
    last_red_at = _to_aware_datetime(raw.get("last_red_at"))
    if last_red_at is None:
        return ""
    cooldown = int(raw.get("cooldown_seconds") or LOCAL_PRESSURE_RED_COOLDOWN_SECONDS)
    ready_at = last_red_at + timedelta(seconds=max(cooldown, 0))
    if ready_at <= now:
        return ""
    reasons = [str(reason) for reason in raw.get("last_red_reasons") or [] if str(reason).strip()]
    suffix = f": {'; '.join(reasons[:3])}" if reasons else ""
    return f"recent local red-pressure cooldown until {ready_at.isoformat()}{suffix}"


def local_work_admission(
    conn,
    *,
    local_cost_class: str,
    active_heavy_local_count: int = 0,
    pressure: Mapping[str, Any] | None = None,
    sample_disk: bool = False,
) -> dict[str, Any]:
    """Decide whether a local-cost class is admissible under the current mode."""
    setting = load_setting(conn)
    mode = str(setting.get("mode") or DEFAULT_MODE)
    cost_class = normalize_local_cost_class(local_cost_class)
    heavy_cost = is_heavy_local_cost_class(cost_class)
    snapshot = local_load_snapshot()
    limit = float(LOCAL_LOAD_PER_CPU_LIMITS.get(mode, LOCAL_LOAD_PER_CPU_LIMITS[DEFAULT_MODE]))
    now = datetime.now(timezone.utc)

    def _blocked(reason: str, *, pressure_snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {
            "schema": LOCAL_LOAD_GATE_SCHEMA,
            "status": "blocked",
            "allowed": False,
            "mode": mode,
            "local_cost_class": cost_class,
            "reason": reason,
            "load": snapshot,
            "pressure": dict(pressure_snapshot or {}),
            "load_per_cpu_limit": limit,
            "active_heavy_local_count": int(active_heavy_local_count or 0),
        }

    if mode == "paused":
        return _blocked("always-on governor mode is paused")
    if mode == "trickle" and cost_class not in TRICKLE_ALLOWED_LOCAL_COST_CLASSES:
        return _blocked("trickle admits only remote_light_local_light work")
    pressure_snapshot: Mapping[str, Any] | None = None
    if heavy_cost and int(active_heavy_local_count or 0) > 0:
        return _blocked("another heavy local worker is already running")
    observed = snapshot.get("load_per_cpu_1m")
    if observed is not None and float(observed) > limit and cost_class != REMOTE_LIGHT_LOCAL_LIGHT:
        return _blocked(f"local load gate closed ({observed} > {limit})")
    if heavy_cost:
        pressure_snapshot = dict(pressure or local_pressure_snapshot(sample_disk=sample_disk))
        red_reasons = [
            str(reason)
            for reason in pressure_snapshot.get("red_reasons") or []
            if str(reason).strip()
        ]
        if red_reasons:
            _record_pressure_red(conn, pressure_snapshot, now=now)
            return _blocked(
                "local pressure gate closed: " + "; ".join(red_reasons[:4]),
                pressure_snapshot=pressure_snapshot,
            )
        cooldown_reason = _recent_red_cooldown_reason(conn, now=now)
        if cooldown_reason:
            return _blocked(cooldown_reason, pressure_snapshot=pressure_snapshot)
    return {
        "schema": LOCAL_LOAD_GATE_SCHEMA,
        "status": "admitted",
        "allowed": True,
        "mode": mode,
        "local_cost_class": cost_class,
        "reason": "",
        "load": snapshot,
        "pressure": dict(pressure_snapshot or {}),
        "load_per_cpu_limit": limit,
        "active_heavy_local_count": int(active_heavy_local_count or 0),
    }


def dispatch_history(conn) -> dict[str, str]:
    raw = store.get_setting(conn, DISPATCH_HISTORY_KEY, {}) or {}
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): str(value) for key, value in raw.items() if str(key).strip() and str(value).strip()}


def record_dispatch(conn, provider: str, *, dispatched_at: str | None = None) -> None:
    normalized = str(provider or "").strip().lower()
    if not normalized:
        return
    history = dispatch_history(conn)
    history[normalized] = dispatched_at or store.utc_now()
    store.set_setting(conn, DISPATCH_HISTORY_KEY, history)


def provider_spacing_reason(conn, provider: str, budget: Mapping[str, Any]) -> str:
    min_seconds = int(budget.get("min_seconds_between_dispatch") or 0)
    if min_seconds <= 0:
        return ""
    last_raw = dispatch_history(conn).get(str(provider or "").strip().lower())
    if not last_raw:
        return ""
    try:
        last = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    ready_at = last + timedelta(seconds=min_seconds)
    now = datetime.now(timezone.utc)
    if ready_at <= now:
        return ""
    return f"provider dispatch spacing until {ready_at.isoformat()}"


def build_status(conn) -> dict[str, Any]:
    setting = load_setting(conn)
    profile = active_profile(conn)
    scheduler = effective_scheduler_settings(conn)
    budgets = {}
    for provider, row in {
        str(row.get("provider") or ""): row for row in store.list_provider_rows(conn)
    }.items():
        if not provider:
            continue
        budgets[provider] = effective_provider_budget(conn, provider, row.get("budget") or {})
    enabled, reason = dispatch_enabled(conn)
    return {
        "schema": SCHEMA,
        "generated_at": store.utc_now(),
        "enabled": bool(setting.get("enabled", True)),
        "mode": setting["mode"],
        "label": profile.get("label"),
        "description": profile.get("description"),
        "dispatch_enabled": enabled,
        "dispatch_block_reason": reason or None,
        "cost_posture": setting.get("cost_posture"),
        "paid_spend_usd_daily_cap": setting.get("paid_spend_usd_daily_cap", 0.0),
        "scheduler": scheduler,
        "provider_budgets": budgets,
        "local_pressure": local_pressure_snapshot(sample_disk=False),
        "local_load_gate": local_work_admission(
            conn,
            local_cost_class=REMOTE_LIGHT_LOCAL_LIGHT,
        ),
        "dispatch_history": dispatch_history(conn),
        "valid_modes": valid_modes(),
        "annex_patterns": [
            {"annex_slug": "paseo", "pattern": "one daemon, timeline, multi-client control"},
            {"annex_slug": "mercury-agent", "pattern": "scheduler tasks enter the same agent loop with provider budgets"},
            {"annex_slug": "openclaw-mission-control", "pattern": "background worker with retry/backoff plus governance dashboard"},
            {"annex_slug": "codex", "pattern": "thread/turn/item event-stream control surface"},
        ],
    }
