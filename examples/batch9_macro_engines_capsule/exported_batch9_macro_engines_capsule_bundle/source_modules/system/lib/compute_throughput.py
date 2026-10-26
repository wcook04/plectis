"""

[PURPOSE]
- Teleology: Project provider endpoints, bridge workers, and local agent harnesses
  into one audited compute-throughput ledger before any cheap worker dispatch exists.
- Mechanism: Merge the authored compute provider registry with bridge capability
  metadata, NVIDIA runtime status, and read-only provider-pressure state; expose
  route selection for schema-gated zero-write worker packets.
- Non-goal: This module does not dispatch work, probe external networks by default,
  store provider secrets, or promote low-authority output into doctrine.

[INTERFACE]
- Exports: build_compute_ledger, build_compute_audit, route_worker,
  compile_worker_packet, write_compute_surfaces.
- Reads: codex/standards/std_compute_provider.json,
  codex/doctrine/compute/provider_registry.json,
  tools/meta/bridge/provider_capabilities.json, state/metabolism/metabolism.sqlite.
- Writes: only via write_compute_surfaces(), to codex/hologram/compute/.

[FLOW]
- Reads: Provider registry, bridge metadata, local resource snapshots and provider-pressure state; live probes are opt-in.
- Mechanism: Validate registry rows, derive provider/model availability and rank allowed task routes; compile bounded transform-job packets and audit secret-like values.
- Writes: write_compute_surfaces atomically publishes compute ledger, audit and model catalog JSON.

[DEPENDENCIES]
- Couples: type_a_global_policy supplies the local-evidence override policy; provider runtime modules supply optional NVIDIA/OpenRouter observations.
- Reads: std_compute_provider and std_transform_job define provider/task and worker-packet authority.

[CONSTRAINTS]
- Guarantee: Routing and packet compilation describe candidates; they do not execute worker jobs.
- Fails: Unknown/ineligible task routes return explicit unavailable posture; optional probe failures become runtime-status evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.type_a_global_policy import TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY_ID


REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_REL = "codex/standards/std_compute_provider.json"
REGISTRY_REL = "codex/doctrine/compute/provider_registry.json"
BRIDGE_CAPABILITIES_REL = "tools/meta/bridge/provider_capabilities.json"
LEDGER_REL = "codex/hologram/compute/ledger.json"
AUDIT_REL = "codex/hologram/compute/audit.json"
MODEL_CATALOG_REL = "codex/hologram/compute/model_catalog.json"
TRANSFORM_JOB_STANDARD_REL = "codex/standards/std_transform_job.json"

LOW_AUTHORITY_TIERS = frozenset({"bounded_worker", "provider_endpoint"})
HARNESS_SURFACE_KINDS = frozenset(
    {
        "agent_harness",
        "sdk_harness",
        "local_cli_agent",
        "provider_gateway",
    }
)
SECRET_KEY_HINTS = ("api_key", "secret", "token_value", "password", "bearer")
LOCAL_RESOURCE_SNAPSHOT_SCHEMA = "local_resource_snapshot_v0"
COMMAND_BUDGET_GUIDANCE_SCHEMA = "command_budget_guidance_v0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _parse_json_text(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _round_float(value: float | None, digits: int = 3) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _run_probe(args: list[str], *, timeout_s: float = 0.5) -> str:
    try:
        completed = subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _mac_memory_snapshot() -> dict[str, Any]:
    sysctl_out = _run_probe(["/usr/sbin/sysctl", "-n", "hw.memsize"])
    total_bytes = None
    try:
        total_bytes = int(sysctl_out.strip())
    except (TypeError, ValueError):
        total_bytes = None

    vm_stat = _run_probe(["/usr/bin/vm_stat"])
    page_size = 4096
    pages: dict[str, int] = {}
    for line in vm_stat.splitlines():
        if "page size of" in line:
            parts = [part for part in line.replace(".", "").split() if part.isdigit()]
            if parts:
                page_size = int(parts[-1])
            continue
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        digits = "".join(ch for ch in raw_value if ch.isdigit())
        if digits:
            pages[key.strip().lower().replace(" ", "_")] = int(digits)
    if total_bytes is None and pages:
        total_pages = sum(pages.values())
        total_bytes = total_pages * page_size
    free_pages = (
        pages.get("pages_free", 0)
        + pages.get("pages_speculative", 0)
        + pages.get("pages_inactive", 0)
    )
    available_bytes = free_pages * page_size if pages else None
    return {
        "source": "macos_vm_stat",
        "total_bytes": total_bytes,
        "available_bytes_estimate": available_bytes,
        "available_percent_estimate": _round_float(
            (available_bytes / total_bytes) * 100.0
            if available_bytes is not None and total_bytes
            else None
        ),
    }


def _linux_memory_snapshot() -> dict[str, Any]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return {"source": "unavailable"}
    values: dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts:
            continue
        try:
            values[key] = int(parts[0]) * 1024
        except ValueError:
            continue
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    return {
        "source": "linux_proc_meminfo",
        "total_bytes": total,
        "available_bytes_estimate": available,
        "available_percent_estimate": _round_float(
            (available / total) * 100.0 if available is not None and total else None
        ),
    }


def _memory_snapshot() -> dict[str, Any]:
    system = platform.system().lower()
    if system == "darwin":
        return _mac_memory_snapshot()
    if system == "linux":
        return _linux_memory_snapshot()
    return {"source": "unavailable", "platform": platform.system()}


def _resource_pressure_status(
    *,
    free_percent: float,
    load_per_cpu_1m: float | None,
    memory_available_percent: float | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = "clear"
    if free_percent < 5.0:
        status = "blocked"
        reasons.append("disk_free_below_5_percent")
    elif free_percent < 10.0:
        status = "watch"
        reasons.append("disk_free_below_10_percent")
    if load_per_cpu_1m is not None:
        if load_per_cpu_1m >= 2.0:
            status = "blocked" if status == "blocked" else "watch"
            reasons.append("load_average_high_per_cpu")
        elif load_per_cpu_1m >= 1.0:
            if status == "clear":
                status = "watch"
            reasons.append("load_average_near_cpu_capacity")
    if memory_available_percent is not None:
        if memory_available_percent < 5.0:
            status = "blocked"
            reasons.append("memory_available_below_5_percent")
        elif memory_available_percent < 10.0:
            if status == "clear":
                status = "watch"
            reasons.append("memory_available_below_10_percent")
    return status, reasons


def _bounded_worker_count(
    *,
    cpu_count: int,
    status: str,
    load_per_cpu_1m: float | None,
    memory_available_percent: float | None,
    free_percent: float,
) -> int:
    if status == "blocked":
        return 1
    if status == "watch":
        budget = max(1, min(2, cpu_count // 4 or 1))
        if free_percent < 10.0:
            budget = min(budget, 1)
        if load_per_cpu_1m is not None and load_per_cpu_1m >= 1.0:
            budget = min(budget, 1)
        if memory_available_percent is not None and memory_available_percent < 15.0:
            budget = min(budget, 1)
        return budget
    return max(1, min(4, cpu_count // 2 or 1))


def _command_budget_guidance(
    *,
    cpu_count: int,
    free_percent: float,
    load_per_cpu_1m: float | None,
    memory_available_percent: float | None,
    pressure_status: str,
    pressure_reasons: list[str],
) -> dict[str, Any]:
    worker_budget = _bounded_worker_count(
        cpu_count=cpu_count,
        status=pressure_status,
        load_per_cpu_1m=load_per_cpu_1m,
        memory_available_percent=memory_available_percent,
        free_percent=free_percent,
    )
    avoid_live_rebuild = pressure_status != "clear" or free_percent < 10.0
    prefer_focused_validation = pressure_status != "clear"
    if pressure_status == "blocked":
        validation_mode = "single_target_only"
        rebuild_mode = "avoid_generated_rebuilds"
        live_probe_mode = "avoid_live_probes"
        process_mode = "serial_only"
    elif pressure_status == "watch":
        validation_mode = "focused_targets_preferred"
        rebuild_mode = "defer_broad_rebuilds_without_authority_need"
        live_probe_mode = "cached_or_dry_run_first"
        process_mode = "bounded_parallelism"
    else:
        validation_mode = "parallel_allowed_for_independent_targets"
        rebuild_mode = "normal_scoped_rebuilds_allowed"
        live_probe_mode = "live_allowed_when_authority_requires"
        process_mode = "normal_parallelism"

    return {
        "schema_version": COMMAND_BUDGET_GUIDANCE_SCHEMA,
        "pressure_status": pressure_status,
        "pressure_reasons": list(pressure_reasons),
        "worker_budget": {
            "max_parallel_local_processes": worker_budget,
            "max_parallel_pytest_workers": worker_budget,
            "max_parallel_rebuild_processes": 1 if avoid_live_rebuild else min(worker_budget, 2),
            "rule": "Treat this as a local command budget for this checkout, not a provider quota or dispatch policy.",
        },
        "command_modes": {
            "validation": validation_mode,
            "generated_rebuilds": rebuild_mode,
            "live_probes": live_probe_mode,
            "process_parallelism": process_mode,
        },
        "recommendations": {
            "prefer": [
                "cached read-model routes before live/full rebuilds",
                "focused validation for owned paths",
                "dry-run or --check modes before write-heavy builders",
            ],
            "avoid": [
                "full repository pytest while pressure is not clear",
                "parallel pytest or process rebuilds beyond worker_budget",
                "live provider/process probes unless authority requires fresh data",
            ]
            if pressure_status != "clear"
            else [
                "unbounded parallelism",
                "live provider/process probes when cached read models answer the question",
            ],
        },
        "booleans": {
            "avoid_live_rebuild": avoid_live_rebuild,
            "prefer_focused_validation": prefer_focused_validation,
            "allow_parallel_pytest": pressure_status == "clear",
        },
    }


def build_local_resource_snapshot(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    cpu_count = os.cpu_count() or 1
    try:
        load_1m, load_5m, load_15m = os.getloadavg()
    except (AttributeError, OSError):
        load_1m = load_5m = load_15m = None
    usage = shutil.disk_usage(repo_root)
    free_percent = (usage.free / usage.total) * 100.0 if usage.total else 0.0
    memory = _memory_snapshot()
    memory_available_percent = memory.get("available_percent_estimate")
    if memory_available_percent is not None:
        try:
            memory_available_percent = float(memory_available_percent)
        except (TypeError, ValueError):
            memory_available_percent = None
    load_per_cpu = (load_1m / cpu_count) if load_1m is not None and cpu_count else None
    status, reasons = _resource_pressure_status(
        free_percent=free_percent,
        load_per_cpu_1m=load_per_cpu,
        memory_available_percent=memory_available_percent,
    )
    if status == "blocked":
        strategy = "prefer serial local work; avoid broad builders and large generated-state writes until pressure clears"
    elif status == "watch":
        strategy = "prefer focused validation, cached projections, and bounded worker counts"
    else:
        strategy = "local_parallel_validation_allowed_when_tests_are_independent"
    command_budget_guidance = _command_budget_guidance(
        cpu_count=cpu_count,
        free_percent=free_percent,
        load_per_cpu_1m=load_per_cpu,
        memory_available_percent=memory_available_percent,
        pressure_status=status,
        pressure_reasons=reasons,
    )
    return {
        "schema_version": LOCAL_RESOURCE_SNAPSHOT_SCHEMA,
        "generated_at": _utc_now(),
        "platform": platform.platform(),
        "cpu": {
            "count": cpu_count,
            "load_average_1m": _round_float(load_1m),
            "load_average_5m": _round_float(load_5m),
            "load_average_15m": _round_float(load_15m),
            "load_per_cpu_1m": _round_float(load_per_cpu),
        },
        "memory": memory,
        "disk": {
            "path": str(repo_root),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "free_percent": _round_float(free_percent),
        },
        "pressure": {
            "status": status,
            "reasons": reasons,
            "strategy": strategy,
        },
        "command_budget_guidance": command_budget_guidance,
        "privacy": {
            "posture": "local_resource_metadata_only",
            "excludes": ["file_contents", "environment_values", "provider_payloads"],
        },
    }


def load_compute_standard(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    payload = _read_json(repo_root / STANDARD_REL, {})
    return payload if isinstance(payload, dict) else {}


def load_provider_registry(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    payload = _read_json(repo_root / REGISTRY_REL, {})
    return payload if isinstance(payload, dict) else {}


def load_bridge_capabilities(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    payload = _read_json(repo_root / BRIDGE_CAPABILITIES_REL, {})
    return payload if isinstance(payload, dict) else {}


def _nvidia_runtime_status(*, probe_live: bool = False) -> dict[str, Any]:
    try:
        from system.lib import nvidia_nim

        status = nvidia_nim.runtime_status(probe_live=probe_live)
        return status if isinstance(status, dict) else {"error": "non_object_status"}
    except Exception as exc:  # pragma: no cover - defensive against optional envs
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "configured": {"api_key_present": False},
            "limits": {},
            "live_probe": {"status": "error"},
        }


def _openrouter_free_runtime_status(*, probe_live: bool = False) -> dict[str, Any]:
    try:
        from system.lib import openrouter_free_runtime

        status = openrouter_free_runtime.runtime_status(
            probe_live=probe_live,
            include_models=probe_live,
            top_n=8,
        )
        if not isinstance(status, dict):
            return {"error": "non_object_status"}
        payload = dict(status)
        payload.pop("generated_at", None)
        return payload
    except Exception as exc:  # pragma: no cover - defensive against optional envs
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "configured": {
                "api_key_present": False,
                "free_only": True,
                "allow_paid": False,
            },
            "limits": {},
            "live_probe": {"status": "error"},
        }


def _read_provider_pressure(repo_root: Path, provider: str) -> dict[str, Any]:
    db_path = repo_root / "state" / "metabolism" / "metabolism.sqlite"
    if not db_path.exists():
        return {
            "source": "metabolism_store_absent",
            "state": "unknown",
            "allowed": None,
            "cooldown_until": None,
            "budget": {},
            "last_interrupt": {},
        }
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        return {
            "source": "metabolism_store_unreadable",
            "state": "unknown",
            "allowed": None,
            "reason": str(exc),
            "cooldown_until": None,
            "budget": {},
            "last_interrupt": {},
        }
    try:
        row = conn.execute(
            "SELECT provider, state, cooldown_until, budget_json, last_interrupt_json, updated_at "
            "FROM providers WHERE provider = ?",
            (provider,),
        ).fetchone()
    except sqlite3.Error as exc:
        conn.close()
        return {
            "source": "metabolism_store_query_error",
            "state": "unknown",
            "allowed": None,
            "reason": str(exc),
            "cooldown_until": None,
            "budget": {},
            "last_interrupt": {},
        }
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    if row is None:
        return {
            "source": "metabolism_store",
            "state": "untracked",
            "allowed": None,
            "cooldown_until": None,
            "budget": {},
            "last_interrupt": {},
        }
    cooldown_until = row["cooldown_until"]
    cooldown_dt = _parse_dt(cooldown_until)
    now = datetime.now(timezone.utc)
    cooldown_active = cooldown_dt is not None and cooldown_dt > now
    state = str(row["state"] or "").strip() or "unknown"
    allowed = not (state == "cooldown" and cooldown_active)
    return {
        "source": "metabolism_store",
        "state": state,
        "allowed": allowed,
        "cooldown_until": cooldown_until,
        "cooldown_active": cooldown_active,
        "budget": _parse_json_text(row["budget_json"], {}),
        "last_interrupt": _parse_json_text(row["last_interrupt_json"], {}),
        "updated_at": row["updated_at"],
    }


def _task_classes(standard: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = standard.get("task_classes") or {}
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(task_class): dict(policy)
        for task_class, policy in raw.items()
        if isinstance(policy, Mapping)
    }


def _allowed_low_authority_task_classes(standard: Mapping[str, Any]) -> list[str]:
    return sorted(
        task_class
        for task_class, policy in _task_classes(standard).items()
        if bool(policy.get("low_authority_allowed"))
    )


def validate_registry_payload(
    registry: Mapping[str, Any],
    standard: Mapping[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    authority_tiers = set((standard.get("authority_tiers") or {}).keys())
    known_tasks = set(_task_classes(standard).keys())
    providers = registry.get("providers") or {}
    if not isinstance(providers, Mapping):
        return [
            {
                "severity": "error",
                "kind": "registry_providers_missing",
                "message": "provider_registry.json must contain an object at providers.",
            }
        ]
    for provider_id, raw_provider in sorted(providers.items()):
        provider = dict(raw_provider) if isinstance(raw_provider, Mapping) else {}
        if not provider:
            findings.append(
                {
                    "severity": "error",
                    "kind": "provider_not_object",
                    "provider_id": provider_id,
                    "message": "Provider row must be a JSON object.",
                }
            )
            continue
        tier = str(provider.get("authority_tier") or "")
        if tier not in authority_tiers:
            findings.append(
                {
                    "severity": "error",
                    "kind": "unknown_authority_tier",
                    "provider_id": provider_id,
                    "message": f"Unknown authority_tier {tier!r}.",
                }
            )
        if not provider.get("provider_token"):
            findings.append(
                {
                    "severity": "error",
                    "kind": "missing_provider_token",
                    "provider_id": provider_id,
                    "message": "Provider row must declare provider_token.",
                }
            )
        if not provider.get("provenance"):
            findings.append(
                {
                    "severity": "warning",
                    "kind": "missing_provenance",
                    "provider_id": provider_id,
                    "message": "Provider row should cite at least one provenance source.",
                }
            )
        for field in ("allowed_task_classes", "forbidden_task_classes"):
            for task_class in provider.get(field) or []:
                if task_class == "*":
                    continue
                if field == "allowed_task_classes" and task_class == "low_authority_allowed":
                    continue
                if str(task_class) not in known_tasks:
                    findings.append(
                        {
                            "severity": "warning",
                            "kind": "unknown_task_class_reference",
                            "provider_id": provider_id,
                            "field": field,
                            "task_class": task_class,
                            "message": f"{field} references unknown task class {task_class!r}.",
                        }
                    )
    return findings


def _provider_supports_task(
    provider: Mapping[str, Any],
    task_class: str,
    *,
    low_authority_allowed_tasks: set[str],
) -> bool:
    forbidden = set(str(item) for item in provider.get("forbidden_task_classes") or [])
    if "*" in forbidden or task_class in forbidden:
        return False
    allowed = set(str(item) for item in provider.get("allowed_task_classes") or [])
    if "*" in allowed:
        return True
    if "low_authority_allowed" in allowed:
        return task_class in low_authority_allowed_tasks
    return task_class in allowed


def _provider_runtime_overlay(
    repo_root: Path,
    provider_id: str,
    provider: Mapping[str, Any],
    bridge_capabilities: Mapping[str, Any],
    *,
    probe_live: bool,
) -> dict[str, Any]:
    overlay: dict[str, Any] = {}
    if provider_id == "nvidia_nim":
        overlay["nvidia_status"] = _nvidia_runtime_status(probe_live=probe_live)
    if provider_id == "openrouter_api":
        overlay["openrouter_free_status"] = _openrouter_free_runtime_status(probe_live=probe_live)

    bridge_name = str(provider.get("bridge_capability_provider") or "").strip()
    bridge_providers = bridge_capabilities.get("providers") or {}
    if bridge_name and isinstance(bridge_providers, Mapping):
        bridge_row = bridge_providers.get(bridge_name)
        if isinstance(bridge_row, Mapping):
            overlay["bridge_capability"] = {
                "provider": bridge_name,
                "soft_char_cap": bridge_row.get("soft_char_cap"),
                "hard_char_cap": bridge_row.get("hard_char_cap"),
                "runtime_prompt_budget_chars": bridge_row.get("runtime_prompt_budget_chars"),
                "safe_parallelism": bridge_row.get("safe_parallelism"),
                "max_code_blobs": bridge_row.get("max_code_blobs"),
                "preferred_task_shapes": bridge_row.get("preferred_task_shapes") or [],
                "measurement_method": bridge_row.get("measurement_method"),
                "last_measured_at": bridge_row.get("last_measured_at"),
            }
            overlay["provider_pressure"] = _read_provider_pressure(repo_root, bridge_name)

    provider_token = str(provider.get("provider_token") or "").strip()
    if provider_token in {"chatgpt", "gemini", "claude", "codex"} and "provider_pressure" not in overlay:
        overlay["provider_pressure"] = _read_provider_pressure(repo_root, provider_token)
    return overlay


def _provider_health(
    provider: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    status = str(provider.get("status") or "unknown")
    verification = dict(provider.get("verification") or {})
    risk = dict(provider.get("risk") or {})
    if status != "active":
        return {
            "state": "candidate",
            "route_eligible": False,
            "reason": f"provider status is {status}",
        }
    if bool(risk.get("operator_approval_required")):
        return {
            "state": "requires_operator_approval",
            "route_eligible": False,
            "reason": "operator approval required before routing",
        }
    if verification.get("status") == "unverified":
        return {
            "state": "unverified",
            "route_eligible": False,
            "reason": "provider is unverified",
        }
    nvidia_status = dict(overlay.get("nvidia_status") or {})
    if nvidia_status:
        configured = dict(nvidia_status.get("configured") or {})
        if not configured.get("api_key_present"):
            return {
                "state": "not_configured",
                "route_eligible": False,
                "reason": "NVIDIA_API_KEY is not configured",
            }
    openrouter_status = dict(overlay.get("openrouter_free_status") or {})
    if openrouter_status:
        configured = dict(openrouter_status.get("configured") or {})
        if not configured.get("api_key_present"):
            return {
                "state": "not_configured",
                "route_eligible": False,
                "reason": "OPENROUTER_API_KEY is not configured",
            }
    pressure = dict(overlay.get("provider_pressure") or {})
    if pressure and pressure.get("allowed") is False:
        return {
            "state": "blocked",
            "route_eligible": False,
            "reason": pressure.get("reason") or pressure.get("state") or "provider pressure active",
            "cooldown_until": pressure.get("cooldown_until"),
        }
    return {
        "state": "available",
        "route_eligible": True,
        "reason": None,
    }


def _source_refs_for_provider(provider_id: str, provider: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for row in provider.get("provenance") or []:
        if isinstance(row, Mapping):
            refs.append(
                {
                    "kind": "local_provenance",
                    "source": row.get("source"),
                    "claim": row.get("claim"),
                }
            )
    if provider_id == "nvidia_nim":
        refs.extend(
            [
                {
                    "kind": "official_doc",
                    "source": "https://build.nvidia.com/models",
                    "claim": "NVIDIA model catalog is volatile and must be treated as a refreshable source.",
                },
                {
                    "kind": "official_doc",
                    "source": "https://docs.api.nvidia.com/nim/reference/llm-apis",
                    "claim": "NVIDIA hosted LLM endpoint contract.",
                },
                {
                    "kind": "runtime_status",
                    "source": "system.lib.nvidia_nim.runtime_status",
                    "claim": "Repo-local configured model and rate-limit evidence.",
                },
            ]
        )
    elif provider_id == "openrouter_api":
        refs.extend(
            [
                {
                    "kind": "runtime_status",
                    "source": "system.lib.openrouter_free_runtime.runtime_status",
                    "claim": "Repo-local free-only guard, quota assumptions, and optional model metadata.",
                },
                {
                    "kind": "metadata_endpoint",
                    "source": "https://openrouter.ai/api/v1/models",
                    "claim": "OpenRouter model metadata source used only by explicit metadata probes.",
                },
            ]
        )
    return refs


def _limit_source_kind(source: Any, *, provider_id: str) -> str:
    token = str(source or "").strip().lower()
    if not token:
        return "unknown"
    if token == "assumed_default" or "assumed" in token:
        return "assumed_default"
    if token.startswith("env:") or token.startswith("config:") or "operator" in token:
        return "operator_override"
    if "header" in token or "measured" in token:
        return "header_observed"
    if "doc" in token or "openrouter_free_runtime" in token:
        return "official_doc"
    if provider_id == "openrouter_api":
        return "official_doc"
    return "unknown"


def _limit_claims_for_provider(provider_id: str, provider_row: Mapping[str, Any]) -> list[dict[str, Any]]:
    limits = dict(provider_row.get("limits") or {})
    overlay = dict(provider_row.get("runtime_overlay") or {})
    claims: list[dict[str, Any]] = []

    def add_claim(metric: str, value: Any, source: Any, *, scope: str, note: str = "") -> None:
        if value in (None, ""):
            return
        source_kind = _limit_source_kind(source, provider_id=provider_id)
        claims.append(
            {
                "metric": metric,
                "value": value,
                "scope": scope,
                "source_kind": source_kind,
                "source": source or source_kind,
                "confidence": "medium" if source_kind in {"official_doc", "operator_override", "header_observed"} else "low",
                "note": note,
            }
        )

    rpm = limits.get("effective_requests_per_minute", limits.get("requests_per_minute"))
    rpm_source = limits.get("effective_requests_per_minute_source", limits.get("requests_per_minute_source"))
    add_claim(
        "requests_per_minute",
        rpm,
        rpm_source,
        scope="provider_account" if provider_id == "nvidia_nim" else "free_model_variant_burst",
        note=(
            "NVIDIA limit scope is not assumed to be per-model or global until measured."
            if provider_id == "nvidia_nim"
            else "Free-model burst limit; daily account-tier cap still binds sustained usage."
        ),
    )
    add_claim(
        "requests_per_day",
        limits.get("requests_per_day"),
        limits.get("requests_per_day_source"),
        scope="account_tier" if provider_id == "openrouter_api" else "unknown",
        note=(
            "Account-tier daily cap; do not multiply by model count or API key count."
            if provider_id == "openrouter_api"
            else ""
        ),
    )
    add_claim(
        "recommended_min_interval_seconds",
        limits.get("recommended_min_interval_seconds"),
        limits.get("effective_requests_per_minute_source") or limits.get("requests_per_day_source"),
        scope="always_on_scheduler",
        note="Scheduler hint for metabolism jobs; not a provider guarantee.",
    )

    if provider_id == "nvidia_nim":
        nvidia_status = dict(overlay.get("nvidia_status") or {})
        live_probe = dict(nvidia_status.get("live_probe") or {})
        headers = live_probe.get("rate_limit_headers")
        if isinstance(headers, Mapping) and headers:
            claims.append(
                {
                    "metric": "rate_limit_headers",
                    "value": dict(headers),
                    "scope": "http_response",
                    "source_kind": "header_observed",
                    "source": "NVIDIA /v1/models response headers",
                    "confidence": "medium",
                    "note": "Header presence is observed evidence, not yet a durable throughput policy.",
                }
            )
    return claims or [
        {
            "metric": "requests_per_minute",
            "value": None,
            "scope": "unknown",
            "source_kind": "unknown",
            "source": "no_limit_evidence",
            "confidence": "low",
            "note": "No usable limit evidence is available for this provider row.",
        }
    ]


def _pricing_class(provider_id: str, provider_row: Mapping[str, Any], model: Mapping[str, Any] | None = None) -> str:
    if provider_id == "openrouter_api":
        if model and bool(model.get("free")):
            return "free_model"
        return "free_default_with_paid_gate"
    cost = dict(provider_row.get("cost") or {})
    plan = str(cost.get("plan") or "").strip()
    return plan or "provider_account_quota"


def _model_capabilities(provider_id: str, provider_row: Mapping[str, Any], model: Mapping[str, Any] | None = None) -> dict[str, Any]:
    caps = dict(provider_row.get("capabilities") or {})
    if model:
        for key in ("input_modalities", "output_modalities", "supported_parameters", "context_length"):
            if key in model:
                caps[key] = model.get(key)
        if isinstance(model.get("capability_flags"), Mapping):
            caps.update(dict(model["capability_flags"]))
    if provider_id == "nvidia_nim" and "chat_completion" not in caps:
        caps["chat_completion"] = True
    return caps


def _provider_model_row(
    *,
    provider_id: str,
    provider_row: Mapping[str, Any],
    model_id: str,
    display_name: str,
    endpoint_kind: str,
    model: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    overlay = dict(provider_row.get("runtime_overlay") or {})
    status_key = "nvidia_status" if provider_id == "nvidia_nim" else "openrouter_free_status"
    status = dict(overlay.get(status_key) or {})
    live_probe = dict(status.get("live_probe") or {"status": "not_run", "reason": "probe_live_disabled"})
    return {
        "kind": "provider_model_row",
        "schema_version": "provider_model_row_v1",
        "row_id": f"provider_model:{provider_id}:{model_id}",
        "provider_id": provider_id,
        "model_id": model_id,
        "display_name": display_name,
        "endpoint_kind": endpoint_kind,
        "modalities": {
            "input": (model or {}).get("input_modalities"),
            "output": (model or {}).get("output_modalities"),
        },
        "capabilities": _model_capabilities(provider_id, provider_row, model),
        "pricing_class": _pricing_class(provider_id, provider_row, model),
        "limit_claims": _limit_claims_for_provider(provider_id, provider_row),
        "live_probe_status": live_probe,
        "latency_stats": {
            "status": "not_measured",
            "source": "provider_model_catalog_metadata_only",
        },
        "schema_score": {
            "status": "not_benchmarked",
            "score": None,
            "source": "transform_job_pilot_pending",
        },
        "last_seen_at": status.get("generated_at") or None,
        "source_refs": _source_refs_for_provider(provider_id, provider_row),
        "authority_ceiling": provider_row.get("authority_tier") or "provider_endpoint",
    }


def _provider_capacity_lane(row: Mapping[str, Any]) -> dict[str, Any]:
    provider_id = str(row.get("provider_id") or "unknown_provider")
    limits = dict(row.get("limits") or {})
    scope = "unknown"
    if provider_id == "openrouter_api":
        scope = "account_tier"
    elif provider_id == "nvidia_nim":
        scope = "provider_account_unknown_subscope"
    return {
        "lane_id": f"provider:{provider_id}",
        "provider_id": provider_id,
        "independent_throughput": True,
        "throughput_scope": scope,
        "route_role": "independent_capacity_lane",
        "maximization_rule": "Schedule under this provider's own caps; do not treat another provider as consuming this lane.",
        "limits": {
            "requests_per_minute": limits.get("effective_requests_per_minute", limits.get("requests_per_minute")),
            "requests_per_day": limits.get("requests_per_day"),
            "recommended_min_interval_seconds": limits.get("recommended_min_interval_seconds"),
            "source": limits.get("effective_requests_per_minute_source")
            or limits.get("requests_per_minute_source")
            or limits.get("requests_per_day_source"),
        },
    }


def build_provider_model_catalog(
    repo_root: Path = REPO_ROOT,
    *,
    ledger: Mapping[str, Any] | None = None,
    probe_live: bool = False,
) -> dict[str, Any]:
    resolved_ledger = dict(ledger or build_compute_ledger(repo_root, probe_live=probe_live))
    rows: list[dict[str, Any]] = []
    for provider_row in resolved_ledger.get("providers") or []:
        if not isinstance(provider_row, Mapping):
            continue
        provider_id = str(provider_row.get("provider_id") or "")
        overlay = dict(provider_row.get("runtime_overlay") or {})
        if provider_id == "nvidia_nim":
            status = dict(overlay.get("nvidia_status") or {})
            configured = dict(status.get("configured") or {})
            configured_models = [
                ("chat", configured.get("chat_model")),
                ("embedding", configured.get("embed_model")),
                ("code_embedding", configured.get("code_embed_model")),
            ]
            live_probe = dict(status.get("live_probe") or {})
            sample = live_probe.get("models_sample") if isinstance(live_probe.get("models_sample"), list) else []
            configured_models.extend(("catalog_sample", item) for item in sample)
            profiles = provider_row.get("model_profiles") or {}
            if isinstance(profiles, Mapping):
                for profile_id, profile in sorted(profiles.items()):
                    if not isinstance(profile, Mapping):
                        continue
                    configured_models.append((f"model_profile:{profile_id}", profile.get("model_id")))
            seen: set[tuple[str, str]] = set()
            for endpoint_kind, model_id_raw in configured_models:
                model_id = str(model_id_raw or "").strip()
                if not model_id:
                    continue
                key = (endpoint_kind, model_id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    _provider_model_row(
                        provider_id=provider_id,
                        provider_row=provider_row,
                        model_id=model_id,
                        display_name=model_id,
                        endpoint_kind=endpoint_kind,
                    )
                )
        elif provider_id == "openrouter_api":
            status = dict(overlay.get("openrouter_free_status") or {})
            models_payload = dict(status.get("models") or {})
            ranked = models_payload.get("ranked_free_models")
            models = [row for row in ranked if isinstance(row, Mapping)] if isinstance(ranked, list) else []
            if not models:
                models = [
                    {
                        "id": "openrouter/free",
                        "name": "OpenRouter free router",
                        "free": True,
                        "pricing_zero": True,
                        "input_modalities": ["text"],
                        "output_modalities": ["text"],
                        "supported_parameters": [],
                    }
                ]
            for model in models:
                model_id = str(model.get("id") or "").strip()
                if not model_id:
                    continue
                row_model = dict(model)
                row_model["free"] = bool(
                    row_model.get("free")
                    or row_model.get("pricing_zero")
                    or model_id == "openrouter/free"
                    or model_id.endswith(":free")
                )
                rows.append(
                    _provider_model_row(
                        provider_id=provider_id,
                        provider_row=provider_row,
                        model_id=model_id,
                        display_name=str(model.get("name") or model_id),
                        endpoint_kind="chat_completion",
                        model=row_model,
                    )
                )

    return {
        "kind": "provider_model_catalog",
        "schema_version": "provider_model_catalog_v1",
        "generated_at": _utc_now(),
        "probe_live": bool(probe_live),
        "sources": {
            "compute_ledger": LEDGER_REL,
            "provider_registry": REGISTRY_REL,
            "nvidia_status": "system.lib.nvidia_nim.runtime_status",
            "openrouter_free_status": "system.lib.openrouter_free_runtime.runtime_status",
        },
        "policy": {
            "authority": "metadata_and_runtime_status_only",
            "no_inference": True,
            "limit_scope_rule": "Record limit evidence and scope explicitly; do not infer NVIDIA per-model/global scope or multiply OpenRouter account caps.",
            "capacity_lane_rule": "NVIDIA and OpenRouter are independent provider lanes. The system hub may schedule both under separate cooldowns and caps; route fallback is only a same-job recovery concept.",
        },
        "summary": {
            "provider_count": len({row["provider_id"] for row in rows}),
            "model_row_count": len(rows),
            "providers": sorted({row["provider_id"] for row in rows}),
            "capacity_lanes": [
                _provider_capacity_lane(row)
                for row in resolved_ledger.get("providers") or []
                if isinstance(row, Mapping)
                and str(row.get("provider_id") or "") in {"nvidia_nim", "openrouter_api"}
            ],
        },
        "models": rows,
    }


def _provider_row(
    repo_root: Path,
    provider_id: str,
    provider: Mapping[str, Any],
    standard: Mapping[str, Any],
    bridge_capabilities: Mapping[str, Any],
    *,
    probe_live: bool,
) -> dict[str, Any]:
    overlay = _provider_runtime_overlay(
        repo_root,
        provider_id,
        provider,
        bridge_capabilities,
        probe_live=probe_live,
    )
    health = _provider_health(provider, overlay)
    limits = dict(provider.get("limits") or {})
    nvidia_limits = dict((overlay.get("nvidia_status") or {}).get("limits") or {})
    if nvidia_limits:
        limits["effective_requests_per_minute"] = nvidia_limits.get("effective_rate_limit_rpm")
        limits["effective_requests_per_minute_source"] = nvidia_limits.get("rate_limit_source")
        limits["recommended_min_interval_seconds"] = nvidia_limits.get("recommended_min_interval_seconds")
    openrouter_limits = dict((overlay.get("openrouter_free_status") or {}).get("limits") or {})
    if openrouter_limits:
        limits["effective_requests_per_minute"] = openrouter_limits.get("free_model_burst_requests_per_minute")
        limits["effective_requests_per_minute_source"] = "openrouter_free_runtime"
        limits["requests_per_day"] = openrouter_limits.get("free_model_daily_request_limit")
        limits["requests_per_day_source"] = openrouter_limits.get("daily_limit_source")
        limits["recommended_sustained_requests_per_minute"] = openrouter_limits.get(
            "recommended_sustained_requests_per_minute"
        )
        limits["recommended_min_interval_seconds"] = openrouter_limits.get(
            "recommended_min_interval_seconds_for_always_on"
        )
    bridge_row = dict(overlay.get("bridge_capability") or {})
    if bridge_row:
        limits["bridge_soft_char_cap"] = bridge_row.get("soft_char_cap")
        limits["bridge_hard_char_cap"] = bridge_row.get("hard_char_cap")
        limits["bridge_safe_parallelism"] = bridge_row.get("safe_parallelism")

    low_authority_tasks = set(_allowed_low_authority_task_classes(standard))
    allowed_task_classes = list(provider.get("allowed_task_classes") or [])
    if "low_authority_allowed" in allowed_task_classes:
        effective_allowed = sorted(low_authority_tasks)
    elif "*" in allowed_task_classes:
        effective_allowed = sorted(_task_classes(standard).keys())
    else:
        effective_allowed = sorted(str(item) for item in allowed_task_classes)

    return {
        "provider_id": provider_id,
        "display_name": provider.get("display_name") or provider_id,
        "status": provider.get("status"),
        "authority_tier": provider.get("authority_tier"),
        "surface_kind": provider.get("surface_kind"),
        "provider_token": provider.get("provider_token"),
        "verification": provider.get("verification") or {},
        "cost": provider.get("cost") or {},
        "limits": limits,
        "capabilities": provider.get("capabilities") or {},
        "allowed_task_classes": effective_allowed,
        "forbidden_task_classes": list(provider.get("forbidden_task_classes") or []),
        "risk": provider.get("risk") or {},
        "provenance": provider.get("provenance") or [],
        "runtime_overlay": overlay,
        "runtime_health": health,
        "route_eligible": bool(health.get("route_eligible")),
    }


def build_compute_ledger(
    repo_root: Path = REPO_ROOT,
    *,
    probe_live: bool = False,
) -> dict[str, Any]:
    standard = load_compute_standard(repo_root)
    registry = load_provider_registry(repo_root)
    bridge_capabilities = load_bridge_capabilities(repo_root)
    local_resource_snapshot = build_local_resource_snapshot(repo_root)
    providers_raw = registry.get("providers") or {}
    providers = []
    if isinstance(providers_raw, Mapping):
        for provider_id, provider in sorted(providers_raw.items()):
            if not isinstance(provider, Mapping):
                continue
            providers.append(
                _provider_row(
                    repo_root,
                    str(provider_id),
                    provider,
                    standard,
                    bridge_capabilities,
                    probe_live=probe_live,
                )
            )

    task_classes = _task_classes(standard)
    worker_harnesses = [
        provider
        for provider in providers
        if str(provider.get("surface_kind")) in HARNESS_SURFACE_KINDS
        or provider.get("authority_tier") == "authoring_agent"
    ]
    route_preview: dict[str, Any] = {}
    for task_class, policy in sorted(task_classes.items()):
        if bool(policy.get("low_authority_allowed")):
            route_preview[task_class] = _select_route_from_rows(
                task_class,
                policy,
                providers,
                standard,
                include_packet=False,
            )

    return {
        "kind": "compute_throughput_ledger",
        "schema_version": "compute_throughput_ledger_v1",
        "generated_at": _utc_now(),
        "probe_live": bool(probe_live),
        "sources": {
            "standard": STANDARD_REL,
            "provider_registry": REGISTRY_REL,
            "bridge_capabilities": BRIDGE_CAPABILITIES_REL,
            "provider_model_catalog": MODEL_CATALOG_REL,
            "provider_pressure": "state/metabolism/metabolism.sqlite::providers",
            "nvidia_status": "system.lib.nvidia_nim.runtime_status",
            "openrouter_free_status": "system.lib.openrouter_free_runtime.runtime_status",
            "local_resource_snapshot": "system.lib.compute_throughput.build_local_resource_snapshot",
        },
        "policy": {
            "authority_tiers": standard.get("authority_tiers") or {},
            "task_classes": task_classes,
            "worker_packet_contract": standard.get("worker_packet_contract") or {},
        },
        "providers": providers,
        "worker_harnesses": worker_harnesses,
        "route_preview": route_preview,
        "local_resource_snapshot": local_resource_snapshot,
    }


def _candidate_sort_key(provider: Mapping[str, Any]) -> tuple[int, int, str]:
    cost = dict(provider.get("cost") or {})
    try:
        cost_rank = int(cost.get("cost_rank") or 999)
    except (TypeError, ValueError):
        cost_rank = 999
    health = dict(provider.get("runtime_health") or {})
    health_rank = 0 if health.get("state") == "available" else 100
    return (cost_rank, health_rank, str(provider.get("provider_id") or ""))


def _select_route_from_rows(
    task_class: str,
    policy: Mapping[str, Any],
    providers: list[Mapping[str, Any]],
    standard: Mapping[str, Any],
    *,
    include_packet: bool,
) -> dict[str, Any]:
    if not bool(policy.get("low_authority_allowed")):
        authoring_candidates = [
            {
                "provider_id": row.get("provider_id"),
                "display_name": row.get("display_name"),
                "runtime_health": row.get("runtime_health"),
            }
            for row in providers
            if row.get("authority_tier") == "authoring_agent"
        ]
        return {
            "route_allowed": False,
            "reason": policy.get("forbidden_to_low_authority_reason")
            or "Task requires an authoring agent.",
            "required_authority_tier": policy.get("required_authority_tier") or "authoring_agent",
            "selected_provider": None,
            "authoring_candidates": authoring_candidates,
        }

    low_authority_tasks = set(_allowed_low_authority_task_classes(standard))
    accepted: list[Mapping[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in providers:
        provider_id = str(row.get("provider_id") or "")
        tier = str(row.get("authority_tier") or "")
        if tier not in LOW_AUTHORITY_TIERS:
            rejected.append(
                {
                    "provider_id": provider_id,
                    "reason": f"authority tier {tier} is not low authority",
                }
            )
            continue
        if not _provider_supports_task(row, task_class, low_authority_allowed_tasks=low_authority_tasks):
            rejected.append({"provider_id": provider_id, "reason": "task class not allowed"})
            continue
        if not row.get("route_eligible"):
            health = dict(row.get("runtime_health") or {})
            rejected.append(
                {
                    "provider_id": provider_id,
                    "reason": health.get("reason") or health.get("state") or "not route eligible",
                }
            )
            continue
        accepted.append(row)

    accepted = sorted(accepted, key=_candidate_sort_key)
    selected = accepted[0] if accepted else None
    payload: dict[str, Any] = {
        "route_allowed": bool(selected),
        "task_class": task_class,
        "required_authority_tier": policy.get("required_authority_tier"),
        "selected_provider": selected.get("provider_id") if selected else None,
        "capacity_lane_policy": {
            "rule": "Accepted providers are independent throughput lanes. selected_provider is the default for this one packet, not an instruction to idle the other lanes.",
            "fallback_semantics": "Fallback changes a single transform job after lane failure; provider metabolism should materialize separate jobs to consume separate lanes.",
        },
        "parallel_provider_lanes": [_provider_capacity_lane(row) for row in accepted],
        "candidates": [
            {
                "provider_id": row.get("provider_id"),
                "display_name": row.get("display_name"),
                "authority_tier": row.get("authority_tier"),
                "surface_kind": row.get("surface_kind"),
                "cost": row.get("cost"),
                "limits": row.get("limits"),
                "runtime_health": row.get("runtime_health"),
            }
            for row in accepted
        ],
        "rejected_candidates": rejected,
    }
    if not selected:
        payload["reason"] = "No eligible low-authority provider is currently available."
    elif include_packet:
        payload["worker_packet_preview"] = compile_worker_packet(
            task_class,
            policy,
            selected,
        )
    return payload


def compile_worker_packet(
    task_class: str,
    policy: Mapping[str, Any],
    provider: Mapping[str, Any],
) -> dict[str, Any]:
    provider_id = provider.get("provider_id")
    input_packet = {
        "materialized_projection_inputs": list(policy.get("input_packet") or []),
        "source_projection_paths": [],
    }
    output_schema = policy.get("output_schema") or {}
    provider_selection_policy = {
        "prefer": [provider_id] if provider_id else [],
        "fallback": None,
        "paid_gate": False,
        "capacity_lane_id": f"provider:{provider_id}" if provider_id else None,
        "capacity_lane_semantics": "single_provider_packet_on_independent_lane",
        "fallback_means": "same_job_recovery_only_not_capacity_substitution",
    }
    cache_key_material = {
        "task_class": task_class,
        "input_packet": input_packet,
        "output_schema": output_schema,
        "provider_selection_policy": provider_selection_policy,
    }
    return {
        "kind": "transform_job",
        "schema_version": "std_transform_job_v1",
        "id": "tj_<run_id>",
        "task_class": task_class,
        "target_row_id": "<target_row_id>",
        "target_facet": "<target_facet>",
        "target_band": "<target_band>",
        "source_fingerprints": [],
        "connector_neighborhood_ref": "<connector_neighborhood_ref>",
        "input_packet": input_packet,
        "output_schema": output_schema,
        "authority_ceiling": provider.get("authority_tier"),
        "provider_selection_policy": provider_selection_policy,
        "provider_budget": {
            "free_only": True,
            "allow_paid": False,
            "max_usd": 0.0,
            "max_retries": 0,
        },
        "cache_key": hashlib.sha256(
            json.dumps(cache_key_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "promotion_target": {
            "state": "draft",
        },
        "created_by": "compute_throughput.compile_worker_packet",
        "created_at": "<generated_at>",
        "authority_tier": provider.get("authority_tier"),
        "provider_id": provider.get("provider_id"),
        "materialized_projection_inputs": list(policy.get("input_packet") or []),
        "forbidden_surfaces": list(policy.get("forbidden_surfaces") or []),
        "provenance_requirements": [
            "provider_id",
            "task_class",
            "input_packet_digest",
            "source_projection_paths",
            "generated_at",
        ],
        "validation_command": policy.get("validation_command"),
        "receipt_target": "state/compute_workers/receipts/<yyyy-mm>/<receipt_id>.json",
        "row_patch_target": "state/compute_workers/row_patches/<yyyy-mm>/<patch_id>.json",
        "zero_write": True,
        "controller_assimilation_required": True,
    }


def build_provider_receipt(
    *,
    transform_job_id: str,
    provider_id: str,
    model_id: str,
    task_class: str,
    status: str,
    prompt_hash: str,
    input_packet_digest: str,
    output_digest: str | None = None,
    validation_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "provider_receipt",
        "schema_version": "std_provider_receipt_v1",
        "receipt_id": f"rc_{hashlib.sha256(f'{transform_job_id}:{provider_id}:{model_id}:{_utc_now()}'.encode('utf-8')).hexdigest()[:16]}",
        "transform_job_id": transform_job_id,
        "provider_id": provider_id,
        "model_id": model_id,
        "task_class": task_class,
        "prompt_hash": prompt_hash,
        "input_packet_digest": input_packet_digest,
        "local_evidence_override_policy_id": TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY_ID,
        "source_fingerprints": [],
        "neighbor_context_hash": "",
        "output_digest": output_digest,
        "usage": {},
        "cost": {"unit": "free", "amount": 0.0},
        "latency_ms": None,
        "http_status": None,
        "status": status,
        "validation_result": dict(validation_result or {"passed": False, "violations": []}),
        "promotion_state": "draft" if status == "ok" else "rejected",
        "created_at": _utc_now(),
        "persisted_at": None,
    }


def route_worker(
    task_class: str,
    repo_root: Path = REPO_ROOT,
    *,
    probe_live: bool = False,
) -> dict[str, Any]:
    ledger = build_compute_ledger(repo_root, probe_live=probe_live)
    policy = dict((ledger.get("policy") or {}).get("task_classes", {}).get(task_class) or {})
    if not policy:
        return {
            "kind": "compute.worker_route",
            "task_class": task_class,
            "route_allowed": False,
            "error": f"Unknown task class: {task_class}",
            "known_task_classes": sorted((ledger.get("policy") or {}).get("task_classes", {}).keys()),
        }
    route = _select_route_from_rows(
        task_class,
        policy,
        list(ledger.get("providers") or []),
        {"task_classes": (ledger.get("policy") or {}).get("task_classes") or {}},
        include_packet=True,
    )
    return {
        "kind": "compute.worker_route",
        "generated_at": _utc_now(),
        "task_class": task_class,
        "task_policy": policy,
        **route,
    }


def _value_looks_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) < 24:
        return False
    lowered = text.lower()
    if lowered.startswith(("sk-", "nvapi-", "ghp_", "xoxb-", "eyj")):
        return True
    return False


def _scan_for_secret_values(payload: Any, path: str = "$") -> list[str]:
    leaks: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key).lower()
            next_path = f"{path}.{key}"
            if any(hint in key_text for hint in SECRET_KEY_HINTS) and key_text not in {
                "api_key_present",
                "provider_token",
            }:
                if value not in (None, "", False):
                    leaks.append(next_path)
            leaks.extend(_scan_for_secret_values(value, next_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            leaks.extend(_scan_for_secret_values(value, f"{path}[{index}]"))
    elif _value_looks_secret(payload):
        leaks.append(path)
    return leaks


def build_compute_audit(
    repo_root: Path = REPO_ROOT,
    *,
    ledger: Mapping[str, Any] | None = None,
    probe_live: bool = False,
) -> dict[str, Any]:
    standard = load_compute_standard(repo_root)
    registry = load_provider_registry(repo_root)
    resolved_ledger = dict(ledger or build_compute_ledger(repo_root, probe_live=probe_live))
    model_catalog = build_provider_model_catalog(repo_root, ledger=resolved_ledger, probe_live=probe_live)
    findings = validate_registry_payload(registry, standard)

    for provider in resolved_ledger.get("providers") or []:
        provider_id = provider.get("provider_id")
        health = dict(provider.get("runtime_health") or {})
        if provider.get("status") == "active" and not provider.get("route_eligible"):
            findings.append(
                {
                    "severity": "warning",
                    "kind": "active_provider_not_route_eligible",
                    "provider_id": provider_id,
                    "message": health.get("reason") or health.get("state") or "not route eligible",
                }
            )
        verification = dict(provider.get("verification") or {})
        if verification.get("status") == "unverified":
            findings.append(
                {
                    "severity": "info",
                    "kind": "candidate_unverified",
                    "provider_id": provider_id,
                    "message": "Candidate provider is intentionally excluded from routing until verified.",
                }
            )

    for task_class, route in sorted((resolved_ledger.get("route_preview") or {}).items()):
        if not route.get("route_allowed"):
            findings.append(
                {
                    "severity": "warning",
                    "kind": "no_low_authority_route",
                    "task_class": task_class,
                    "message": route.get("reason") or "No low-authority route.",
                }
            )

    for secret_path in _scan_for_secret_values(resolved_ledger):
        findings.append(
            {
                "severity": "error",
                "kind": "secret_value_leak",
                "path": secret_path,
                "message": "Generated compute ledger appears to contain a secret value.",
            }
        )
    for secret_path in _scan_for_secret_values(model_catalog):
        findings.append(
            {
                "severity": "error",
                "kind": "secret_value_leak",
                "path": f"model_catalog:{secret_path}",
                "message": "Generated provider model catalog appears to contain a secret value.",
            }
        )

    severity_counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity") or "info")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    return {
        "kind": "compute_throughput_audit",
        "schema_version": "compute_throughput_audit_v1",
        "generated_at": _utc_now(),
        "ledger_path": LEDGER_REL,
        "summary": {
            "finding_count": len(findings),
            "by_severity": severity_counts,
            "provider_count": len(resolved_ledger.get("providers") or []),
            "model_row_count": int((model_catalog.get("summary") or {}).get("model_row_count") or 0),
            "route_preview_count": len(resolved_ledger.get("route_preview") or {}),
        },
        "findings": findings,
    }


def write_compute_surfaces(
    repo_root: Path = REPO_ROOT,
    *,
    probe_live: bool = False,
) -> dict[str, Any]:
    ledger = build_compute_ledger(repo_root, probe_live=probe_live)
    model_catalog = build_provider_model_catalog(repo_root, ledger=ledger, probe_live=probe_live)
    audit = build_compute_audit(repo_root, ledger=ledger, probe_live=probe_live)
    ledger_path = repo_root / LEDGER_REL
    audit_path = repo_root / AUDIT_REL
    model_catalog_path = repo_root / MODEL_CATALOG_REL
    _write_json_atomic(ledger_path, ledger)
    _write_json_atomic(model_catalog_path, model_catalog)
    _write_json_atomic(audit_path, audit)
    return {
        "kind": "compute_throughput_build",
        "generated_at": _utc_now(),
        "probe_live": bool(probe_live),
        "ledger_path": _rel(repo_root, ledger_path),
        "model_catalog_path": _rel(repo_root, model_catalog_path),
        "audit_path": _rel(repo_root, audit_path),
        "model_catalog_summary": model_catalog.get("summary") or {},
        "audit_summary": audit.get("summary") or {},
    }
