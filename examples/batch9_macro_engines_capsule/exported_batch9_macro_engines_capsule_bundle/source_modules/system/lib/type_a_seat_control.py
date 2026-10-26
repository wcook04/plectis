"""
[PURPOSE]
- Teleology: Route provider-neutral Type A seat requests through the existing
  Autonomy Plan/Runtime root without touching human-owned desktop threads by
  default.
- Mechanism: Normalize `seat_request` records, evaluate operator presence,
  gate unsafe thread policies, dispatch only through runtime-owned transports,
  and project pending requests into the approval inbox.
- Interface: `route_seat_request`, `approve_seat_request`,
  `iter_pending_approval_requests`, and a small CLI for approval callbacks.

[CONSTRAINTS]
- Claude.app is a focus-affecting desktop adapter. This module never submits
  into Claude.app; v1 can only stage a no-submit ledger row.
- Model names are provider-adapter data. The router passes model profile
  strings through without hardcoding provider model catalogs.
- Seat request state lives under
  `state/autonomy_runtime/<queue_id>/runtime/plans/<plan_id>/...`; this module
  does not create a second queue store.

[INTERFACE]
- Exports: Seat request normalization, route_seat_request and pending-seat-request approval projection helpers.

[FLOW]
- Validate thread/transport policy, evaluate operator presence and dispatch only a runtime-owned permitted route or project a pending approval.

[DEPENDENCIES]
- Autonomy Plan/Runtime owners, approval records and provider-neutral seat transport helpers.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.type_a_global_policy import (
    type_a_local_evidence_override_policy,
    type_a_policy_prompt_prefix,
)


REQUEST_KIND = "type_a_seat_request"
SCHEMA_VERSION = "1.1"
DEFAULT_IDLE_THRESHOLD_SECONDS = 600

LOWER_CLASS_PROVIDERS = {"nvidia_nim", "openrouter_api"}
VALID_PROVIDERS = {"codex", "claude_native", "claude_app", *LOWER_CLASS_PROVIDERS}
VALID_THREAD_POLICIES = {
    "fresh_thread",
    "same_thread_if_safe",
    "stage_only",
    "notification_only",
    "packet_transform",
}
VALID_APPROVAL_MODES = {"review_required", "approved", "autonomous"}
AFK_MODES = {"afk", "overnight", "overnight_afk", "autonomous_afk"}

TERMINAL_APPROVAL_STATUSES = {
    "completed",
    "failed",
    "manual_assist_required",
    "ready_to_dispatch",
    "running",
    "staged",
    "rejected",
}


@dataclasses.dataclass(frozen=True)
class TypeASeatPaths:
    plan_root: Path
    request_dir: Path
    request_path: Path
    seat_dir: Path
    ledger_path: Path


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _stable_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp-{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Expected JSON object at {path}")
    return dict(payload)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")


def _relative(repo_root: Path, path: str | Path | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _path_list(value: Any) -> list[Path]:
    return [Path(_string(item)) for item in _safe_list(value) if _string(item)]


def _string_list(value: Any) -> list[str]:
    return [_string(item) for item in _safe_list(value) if _string(item)]


def _model_profile(request: Mapping[str, Any]) -> dict[str, Any]:
    profile = request.get("model_profile")
    if isinstance(profile, Mapping):
        return dict(profile)
    if _string(profile):
        return {"model": _string(profile)}
    return {}


def _model_id(request: Mapping[str, Any]) -> str:
    profile = _model_profile(request)
    return _string(profile.get("model") or profile.get("model_id") or profile.get("id"))


def _seat_class(provider: str, request: Mapping[str, Any]) -> str:
    explicit = _string(request.get("seat_class"))
    if explicit:
        return explicit
    if provider in LOWER_CLASS_PROVIDERS:
        return "bounded_provider_worker"
    if provider == "claude_app":
        return "desktop_stage"
    return "runtime_owned_agent"


def _default_tool_policy(provider: str, request: Mapping[str, Any]) -> dict[str, Any]:
    policy = _safe_mapping(request.get("tool_policy"))
    if provider in LOWER_CLASS_PROVIDERS or _seat_class(provider, request) == "report_only":
        return {
            "allow_bash": False,
            "allow_filesystem": False,
            "allow_tool_calling": False,
            **policy,
        }
    return policy


def _default_provider_budget(provider: str, request: Mapping[str, Any]) -> dict[str, Any]:
    budget = _safe_mapping(request.get("provider_budget"))
    if provider == "openrouter_api":
        return {
            "free_only": True,
            "allow_paid": False,
            "max_usd": 0.0,
            "max_retries": 0,
            **budget,
        }
    if provider == "nvidia_nim":
        return {
            "free_only": True,
            "allow_paid": False,
            "max_usd": 0.0,
            "max_retries": 0,
            **budget,
        }
    return budget


def _tool_policy_requests_bash(policy: Mapping[str, Any]) -> bool:
    if bool(policy.get("allow_bash")):
        return True
    tools = _string_list(policy.get("tools"))
    return any(tool.lower() == "bash" for tool in tools)


def _prompt_artifact_display(value: Any) -> str:
    if isinstance(value, Mapping):
        return _string(value.get("path") or value.get("artifact_path") or value.get("ref"))
    return _string(value)


def plan_runtime_root(repo_root: Path, *, queue_id: str, plan_id: str) -> Path:
    return repo_root / "state" / "autonomy_runtime" / queue_id / "runtime" / "plans" / plan_id


def seat_paths(repo_root: Path, *, queue_id: str, plan_id: str, seat_id: str) -> TypeASeatPaths:
    plan_root = plan_runtime_root(repo_root, queue_id=queue_id, plan_id=plan_id)
    return TypeASeatPaths(
        plan_root=plan_root,
        request_dir=plan_root / "seat_requests",
        request_path=plan_root / "seat_requests" / f"{seat_id}.json",
        seat_dir=plan_root / "seats" / seat_id,
        ledger_path=plan_root / "seats" / seat_id / "seat_ledger.jsonl",
    )


def macos_idle_seconds() -> int | None:
    """Return macOS HID idle seconds, or None when the probe is unavailable."""
    try:
        proc = subprocess.run(
            ["/usr/sbin/ioreg", "-c", "IOHIDSystem"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', proc.stdout or "")
    if not match:
        return None
    try:
        return int(match.group(1)) // 1_000_000_000
    except ValueError:
        return None


def evaluate_operator_presence(
    policy: Mapping[str, Any] | None,
    *,
    idle_seconds: int | None = None,
) -> dict[str, Any]:
    """Decide whether this runtime is allowed to behave as AFK/autonomous."""
    payload = _safe_mapping(policy)
    explicit_mode = _string(payload.get("mode") or payload.get("presence") or "attended").lower()
    threshold_raw = payload.get("idle_threshold_seconds")
    try:
        threshold = int(threshold_raw if threshold_raw is not None else DEFAULT_IDLE_THRESHOLD_SECONDS)
    except (TypeError, ValueError):
        threshold = DEFAULT_IDLE_THRESHOLD_SECONDS

    override = payload.get("idle_seconds_override")
    if idle_seconds is None and override is not None:
        try:
            idle_seconds = int(override)
        except (TypeError, ValueError):
            idle_seconds = None
    if idle_seconds is None and explicit_mode in AFK_MODES:
        idle_seconds = macos_idle_seconds()

    explicit_afk = explicit_mode in AFK_MODES
    afk = explicit_afk and idle_seconds is not None and idle_seconds >= threshold
    reason = "explicit_afk_and_idle_threshold_met" if afk else "attended_wins"
    if explicit_afk and idle_seconds is None:
        reason = "idle_probe_unavailable"
    elif explicit_afk and idle_seconds is not None and idle_seconds < threshold:
        reason = "idle_threshold_not_met"
    elif not explicit_afk:
        reason = "no_explicit_afk_runtime_mode"

    return {
        "mode": "afk" if afk else "attended",
        "explicit_mode": explicit_mode,
        "idle_seconds": idle_seconds,
        "idle_threshold_seconds": threshold,
        "is_afk": afk,
        "reason": reason,
        "observed_at": _iso_now(),
    }


def _request_id_seed(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "queue_id": request.get("queue_id"),
        "plan_id": request.get("plan_id"),
        "step_id": request.get("step_id"),
        "seat_id": request.get("seat_id"),
        "provider": request.get("provider"),
        "prompt_artifact": request.get("prompt_artifact"),
    }


def normalize_seat_request(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    request_path: str | Path | None = None,
) -> dict[str, Any]:
    request = dict(payload)
    queue_id = _string(request.get("queue_id") or "default")
    plan_id = _string(request.get("plan_id") or "default_plan")
    step_id = _string(request.get("step_id") or "manual_step")
    seat_id = _string(request.get("seat_id") or f"seat_{_stable_hash(_request_id_seed(request))[:12]}")
    provider = _string(request.get("provider") or "codex")
    thread_policy = _string(request.get("thread_policy") or "fresh_thread")
    approval_mode = _string(request.get("approval_mode") or "review_required")
    now = _iso_now()
    paths = seat_paths(repo_root, queue_id=queue_id, plan_id=plan_id, seat_id=seat_id)
    normalized_request_path = _relative(repo_root, request_path) if request_path else _relative(repo_root, paths.request_path)
    ledger_rel = _relative(repo_root, paths.ledger_path)
    model_profile = request.get("model_profile")
    if _string(model_profile) and not isinstance(model_profile, Mapping):
        model_profile = {"model": _string(model_profile)}
    elif isinstance(model_profile, Mapping):
        model_profile = dict(model_profile)
    else:
        model_profile = {}

    normalized = {
        **request,
        "kind": REQUEST_KIND,
        "schema_version": SCHEMA_VERSION,
        "request_id": _string(request.get("request_id")) or _stable_hash(_request_id_seed({
            **request,
            "queue_id": queue_id,
            "plan_id": plan_id,
            "step_id": step_id,
            "seat_id": seat_id,
            "provider": provider,
        }))[:24],
        "queue_id": queue_id,
        "plan_id": plan_id,
        "step_id": step_id,
        "seat_id": seat_id,
        "provider": provider,
        "seat_class": _seat_class(provider, request),
        "execution_profile": _safe_mapping(request.get("execution_profile")),
        "tool_policy": _default_tool_policy(provider, request),
        "provider_budget": _default_provider_budget(provider, request),
        "local_evidence_override_policy": type_a_local_evidence_override_policy(
            _safe_mapping(request.get("local_evidence_override_policy"))
        ),
        "artifact_contract": _safe_mapping(request.get("artifact_contract")),
        "failure_policy": _safe_mapping(request.get("failure_policy")),
        "runner_contract": _safe_mapping(request.get("runner_contract")),
        "model_profile": model_profile,
        "prompt_artifact": request.get("prompt_artifact"),
        "thread_policy": thread_policy,
        "approval_mode": approval_mode,
        "operator_presence_policy": _safe_mapping(request.get("operator_presence_policy")),
        "allowed_write_roots": _string_list(request.get("allowed_write_roots")),
        "dispatch_options": _safe_mapping(request.get("dispatch_options")),
        "thread_evidence": _safe_mapping(request.get("thread_evidence")),
        "status": _string(request.get("status") or "draft"),
        "ledger_refs": {
            **_safe_mapping(request.get("ledger_refs")),
            "request": normalized_request_path,
            "seat_ledger": ledger_rel,
        },
        "created_at": _string(request.get("created_at")) or now,
        "updated_at": _string(request.get("updated_at")) or now,
    }
    return normalized


def write_seat_request(repo_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    request = normalize_seat_request(repo_root, payload)
    paths = seat_paths(
        repo_root,
        queue_id=request["queue_id"],
        plan_id=request["plan_id"],
        seat_id=request["seat_id"],
    )
    _write_json(paths.request_path, request)
    return request


def load_seat_request(repo_root: Path, request_path: str | Path) -> dict[str, Any]:
    path = _repo_path(repo_root, request_path)
    return normalize_seat_request(repo_root, _read_json(path), request_path=path)


def append_seat_ledger(
    repo_root: Path,
    request: Mapping[str, Any],
    event: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    paths = seat_paths(
        repo_root,
        queue_id=_string(request.get("queue_id")),
        plan_id=_string(request.get("plan_id")),
        seat_id=_string(request.get("seat_id")),
    )
    row = {
        "kind": "type_a_seat_event",
        "schema_version": "type_a_seat_event_v1",
        "event_id": f"tase_{uuid.uuid4().hex[:16]}",
        "recorded_at": _iso_now(),
        "event": event,
        "queue_id": request.get("queue_id"),
        "plan_id": request.get("plan_id"),
        "step_id": request.get("step_id"),
        "seat_id": request.get("seat_id"),
        "provider": request.get("provider"),
        "request_id": request.get("request_id"),
        **_safe_mapping(extra),
    }
    _append_jsonl(paths.ledger_path, row)
    return row


def _persist_request(
    repo_root: Path,
    request: Mapping[str, Any],
    *,
    request_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized = normalize_seat_request(repo_root, request, request_path=request_path)
    path = _repo_path(repo_root, request_path) if request_path else seat_paths(
        repo_root,
        queue_id=normalized["queue_id"],
        plan_id=normalized["plan_id"],
        seat_id=normalized["seat_id"],
    ).request_path
    _write_json(path, normalized)
    return normalized


def _mark_request(
    repo_root: Path,
    request: Mapping[str, Any],
    *,
    status: str,
    reason: str,
    decision: Mapping[str, Any] | None = None,
    dispatch_result: Mapping[str, Any] | None = None,
    request_path: str | Path | None = None,
) -> dict[str, Any]:
    updated = {
        **dict(request),
        "status": status,
        "reason": reason,
        "control_decision": _safe_mapping(decision),
        "dispatch_result": _safe_mapping(dispatch_result),
        "updated_at": _iso_now(),
    }
    saved = _persist_request(repo_root, updated, request_path=request_path)
    append_seat_ledger(
        repo_root,
        saved,
        "seat_status",
        {
            "status": status,
            "reason": reason,
            "control_decision": _safe_mapping(decision),
            "dispatch_result": _safe_mapping(dispatch_result),
        },
    )
    return {"ok": True, "status": status, "reason": reason, "request": saved}


def _read_prompt(repo_root: Path, request: Mapping[str, Any]) -> str:
    explicit = _string(request.get("prompt"))
    if explicit:
        return explicit
    artifact = request.get("prompt_artifact")
    artifact_path = _prompt_artifact_display(artifact)
    if not artifact_path:
        return ""
    path = _repo_path(repo_root, artifact_path)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_prompt_with_type_a_policy(repo_root: Path, request: Mapping[str, Any]) -> str:
    prompt = _read_prompt(repo_root, request)
    if not prompt:
        return ""
    return type_a_policy_prompt_prefix(
        _safe_mapping(request.get("local_evidence_override_policy"))
    ) + prompt


def _dispatch_codex(repo_root: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    options = _safe_mapping(request.get("dispatch_options"))
    if not bool(options.get("enabled")):
        return {"ok": True, "status": "manual_assist_required", "reason": "codex_dispatch_disabled"}
    prompt = _read_prompt_with_type_a_policy(repo_root, request)
    if not prompt:
        return {"ok": True, "status": "manual_assist_required", "reason": "prompt_missing"}

    from tools.meta.bridge.codex_manager_transport import (  # noqa: PLC0415
        CodexManagerRequest,
        run_codex_manager,
    )

    profile = _model_profile(request)
    paths = seat_paths(
        repo_root,
        queue_id=_string(request.get("queue_id")),
        plan_id=_string(request.get("plan_id")),
        seat_id=_string(request.get("seat_id")),
    )
    codex_request = CodexManagerRequest(
        repo_root=repo_root,
        prompt=prompt,
        plan_id=_string(request.get("plan_id")),
        subphase_id=_string(request.get("subphase_id") or options.get("subphase_id") or "unknown"),
        step_id=_string(request.get("step_id") or "seat_request"),
        seat_id=_string(request.get("seat_id")),
        output_dir=paths.seat_dir / "codex_manager",
        allowed_write_roots=_path_list(request.get("allowed_write_roots")),
        port=int(options.get("port") or 9224),
        required_connectors=_string_list(profile.get("connectors") or options.get("required_connectors")),
        model=_string(profile.get("model") or profile.get("model_id") or options.get("model") or "gpt-5.4"),
        effort=_string(profile.get("effort") or options.get("effort") or "medium"),
        approval_policy=_string(profile.get("approval_policy") or options.get("approval_policy") or "never"),
        timeout_s=int(options.get("timeout_s") or 900),
        launch_enabled=bool(options.get("launch_enabled")),
        session_id_prefix=_string(options.get("session_id_prefix") or "codex-manager:"),
    )
    result = run_codex_manager(codex_request)
    artifacts = [
        _relative(repo_root, path)
        for path in [
            result.probe_path,
            result.start_path,
            result.final_message_path,
            result.closeout_path,
            result.schema_path,
        ]
        if path
    ]
    if result.status == "succeeded":
        status = "completed"
    elif result.status in {"failed", "timeout"}:
        status = "failed"
    else:
        status = "manual_assist_required"
    return {
        "ok": True,
        "status": status,
        "reason": result.reason or f"codex_manager_{result.status}",
        "provider_status": result.status,
        "session_id": result.session_id,
        "thread_id": result.thread_id,
        "rollout_path": result.rollout_path,
        "artifacts": artifacts,
    }


def _dispatch_claude_native(repo_root: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    options = _safe_mapping(request.get("dispatch_options"))
    if not bool(options.get("enabled")):
        return {"ok": True, "status": "manual_assist_required", "reason": "claude_native_dispatch_disabled"}
    prompt = _read_prompt_with_type_a_policy(repo_root, request)
    if not prompt:
        return {"ok": True, "status": "manual_assist_required", "reason": "prompt_missing"}

    from tools.meta.bridge.claude_native_bridge import ClaudeNativeWorker  # noqa: PLC0415

    profile = _model_profile(request)
    model = _string(profile.get("model") or profile.get("model_id") or options.get("model") or "sonnet")
    tools = _string_list(profile.get("tools") or options.get("tools"))
    permission_mode = _string(profile.get("permission_mode") or options.get("permission_mode") or "bypassPermissions")
    timeout_s = int(options.get("timeout_s") or 600)
    worker = ClaudeNativeWorker(
        executable=_string(options.get("executable")) or None,
        default_model=model,
        default_permission_mode=permission_mode,
        default_tools=tuple(tools),
        default_timeout_s=timeout_s,
    )
    result = worker.dispatch_oneshot(
        prompt,
        label=_string(request.get("seat_id")) or "type_a_seat",
        cwd=str(repo_root),
        model=model,
        tools=tuple(tools),
        permission_mode=permission_mode,
        system_prompt=_string(options.get("system_prompt")) or None,
        system_prompt_file=_string(options.get("system_prompt_file")) or None,
        effort=_string(profile.get("effort") or options.get("effort")) or None,
        no_session_persistence=bool(options.get("no_session_persistence", True)),
        session_id=_string(options.get("session_id")) or None,
        extra_args=tuple(_string_list(options.get("extra_args"))),
        timeout_s=timeout_s,
        env_override={str(k): str(v) for k, v in _safe_mapping(options.get("env_override")).items()},
    )
    return {
        "ok": True,
        "status": "completed" if result.ok else "failed",
        "reason": "claude_native_completed" if result.ok else "claude_native_failed",
        "session_id": result.session_id,
        "model": result.model_used,
        "returncode": result.returncode,
        "stop_reason": result.stop_reason,
        "error_text": result.error_text,
    }


def _stage_claude_app(repo_root: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    prompt = _read_prompt_with_type_a_policy(repo_root, request)
    ledger = append_seat_ledger(
        repo_root,
        request,
        "claude_app_stage_only",
        {
            "submitted": False,
            "prompt_artifact": request.get("prompt_artifact"),
            "prompt_chars": len(prompt),
            "stage_only": True,
            "reason": "claude_app_stage_only_no_submit",
        },
    )
    return {
        "ok": True,
        "status": "staged",
        "reason": "claude_app_stage_only_no_submit",
        "submitted": False,
        "ledger_event_id": ledger["event_id"],
    }


def _dispatch_bounded_provider_worker(repo_root: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    provider = _string(request.get("provider"))
    runner_contract = {
        **_safe_mapping(request.get("runner_contract")),
        **_safe_mapping(request.get("dispatch_options")),
    }
    job_path = (
        _string(runner_contract.get("transform_job_path"))
        or _string(runner_contract.get("job_path"))
        or _prompt_artifact_display(request.get("prompt_artifact"))
    )
    if not job_path:
        return {
            "ok": True,
            "status": "manual_assist_required",
            "reason": "transform_job_path_missing",
        }

    from system.lib import type_a_worker_harness  # noqa: PLC0415

    job_payload = _read_json(_repo_path(repo_root, job_path))
    job_payload["provider_budget"] = {
        **_safe_mapping(job_payload.get("provider_budget")),
        **_safe_mapping(request.get("provider_budget")),
    }
    job_payload["execution_profile"] = {
        **_safe_mapping(job_payload.get("execution_profile")),
        **_safe_mapping(request.get("execution_profile")),
    }
    job_payload["failure_policy"] = {
        **_safe_mapping(job_payload.get("failure_policy")),
        **_safe_mapping(request.get("failure_policy")),
    }
    result = type_a_worker_harness.run_transform_job(
        repo_root,
        job=job_payload,
        provider_id=provider,
        model_id=_string(runner_contract.get("model") or runner_contract.get("model_id") or _model_id(request)) or None,
        force=bool(runner_contract.get("force")),
        dry_run=bool(runner_contract.get("dry_run")),
    )
    receipt = result.receipt
    receipt_status = _string(receipt.get("status"))
    if receipt_status in {"ok", "cache_hit"}:
        status = "completed"
    elif receipt_status in {"blocked_duplicate", "policy_reject"}:
        status = "manual_assist_required"
    else:
        status = "failed"
    return {
        "ok": True,
        "status": status,
        "reason": f"worker_harness_{receipt_status or 'unknown'}",
        "provider_status": receipt_status,
        "receipt_id": receipt.get("receipt_id"),
        "transform_job_id": receipt.get("transform_job_id"),
        "artifact_refs": result.artifact_refs,
        "model": receipt.get("model_id"),
        "runtime_provider": receipt.get("runtime_provider"),
    }


def route_seat_request(
    repo_root: Path,
    *,
    request: Mapping[str, Any] | None = None,
    request_path: str | Path | None = None,
    actor_id: str = "system",
    reason: str | None = None,
) -> dict[str, Any]:
    if request is None:
        if request_path is None:
            raise ValueError("route_seat_request requires request or request_path")
        payload = load_seat_request(repo_root, request_path)
    else:
        payload = normalize_seat_request(repo_root, request, request_path=request_path)

    presence = evaluate_operator_presence(payload.get("operator_presence_policy"))
    payload = {
        **payload,
        "presence_decision": presence,
        "last_actor_id": _string(actor_id) or "system",
        "last_operator_reason": _string(reason) or None,
    }
    persisted = _persist_request(repo_root, payload, request_path=request_path)

    provider = _string(persisted.get("provider"))
    thread_policy = _string(persisted.get("thread_policy"))
    approval_mode = _string(persisted.get("approval_mode"))
    thread_evidence = _safe_mapping(persisted.get("thread_evidence"))
    options = _safe_mapping(persisted.get("dispatch_options"))

    decision = {
        "provider": provider,
        "thread_policy": thread_policy,
        "approval_mode": approval_mode,
        "presence": presence,
        "local_evidence_override_policy": _safe_mapping(
            persisted.get("local_evidence_override_policy")
        ),
    }

    if provider not in VALID_PROVIDERS:
        return _mark_request(
            repo_root,
            persisted,
            status="manual_assist_required",
            reason="unknown_provider",
            decision=decision,
            request_path=request_path,
        )
    if _string(persisted.get("seat_class")) == "report_only" and _tool_policy_requests_bash(
        _safe_mapping(persisted.get("tool_policy"))
    ):
        return _mark_request(
            repo_root,
            persisted,
            status="manual_assist_required",
            reason="report_only_seat_cannot_run_bash",
            decision=decision,
            request_path=request_path,
        )
    if provider in LOWER_CLASS_PROVIDERS and _tool_policy_requests_bash(_safe_mapping(persisted.get("tool_policy"))):
        return _mark_request(
            repo_root,
            persisted,
            status="manual_assist_required",
            reason="bounded_provider_worker_cannot_run_bash",
            decision=decision,
            request_path=request_path,
        )
    if thread_policy not in VALID_THREAD_POLICIES:
        return _mark_request(
            repo_root,
            persisted,
            status="manual_assist_required",
            reason="unknown_thread_policy",
            decision=decision,
            request_path=request_path,
        )
    if approval_mode not in VALID_APPROVAL_MODES:
        return _mark_request(
            repo_root,
            persisted,
            status="manual_assist_required",
            reason="unknown_approval_mode",
            decision=decision,
            request_path=request_path,
        )

    approved = approval_mode == "approved"
    autonomous_afk = approval_mode == "autonomous" and bool(presence.get("is_afk"))

    if provider == "claude_app" and not approved:
        return _mark_request(
            repo_root,
            persisted,
            status="pending_approval",
            reason="claude_app_requires_explicit_approval",
            decision=decision,
            request_path=request_path,
        )

    if approval_mode == "review_required" or (approval_mode == "autonomous" and not autonomous_afk):
        return _mark_request(
            repo_root,
            persisted,
            status="pending_approval",
            reason="operator_review_required" if presence.get("mode") == "attended" else "approval_required",
            decision=decision,
            request_path=request_path,
        )

    if not approved and not autonomous_afk:
        return _mark_request(
            repo_root,
            persisted,
            status="pending_approval",
            reason="approval_required",
            decision=decision,
            request_path=request_path,
        )

    if thread_policy == "same_thread_if_safe":
        if not bool(thread_evidence.get("positive_idle_gate")):
            return _mark_request(
                repo_root,
                persisted,
                status="manual_assist_required",
                reason="same_thread_requires_positive_idle_gate",
                decision=decision,
                request_path=request_path,
            )
        rollout_proof = (
            thread_evidence.get("positive_rollout_gate")
            or thread_evidence.get("rollout_compatible")
            or thread_evidence.get("existing_rollout_proof")
        )
        if not bool(rollout_proof):
            return _mark_request(
                repo_root,
                persisted,
                status="manual_assist_required",
                reason="same_thread_requires_positive_rollout_gate",
                decision=decision,
                request_path=request_path,
            )

    if thread_policy == "notification_only":
        return _mark_request(
            repo_root,
            persisted,
            status="manual_assist_required",
            reason="notification_only_requires_operator",
            decision=decision,
            request_path=request_path,
        )

    if provider in LOWER_CLASS_PROVIDERS:
        if thread_policy not in {"packet_transform", "fresh_thread"}:
            return _mark_request(
                repo_root,
                persisted,
                status="manual_assist_required",
                reason="bounded_provider_worker_requires_packet_transform",
                decision=decision,
                request_path=request_path,
            )
        dispatch_result = _dispatch_bounded_provider_worker(repo_root, persisted)
        return _mark_request(
            repo_root,
            persisted,
            status=_string(dispatch_result.get("status")) or "manual_assist_required",
            reason=_string(dispatch_result.get("reason")) or "dispatch_result_missing_reason",
            decision=decision,
            dispatch_result=dispatch_result,
            request_path=request_path,
        )

    if provider == "claude_app":
        wants_submit = bool(options.get("submit") or options.get("auto_submit"))
        runtime_owned = bool(thread_evidence.get("runtime_owned_thread"))
        if wants_submit and not (approved and runtime_owned):
            return _mark_request(
                repo_root,
                persisted,
                status="manual_assist_required",
                reason="claude_app_submit_requires_approved_runtime_owned_thread",
                decision=decision,
                request_path=request_path,
            )
        if wants_submit:
            return _mark_request(
                repo_root,
                persisted,
                status="manual_assist_required",
                reason="claude_app_submit_not_supported_v1",
                decision=decision,
                request_path=request_path,
            )
        if thread_policy != "stage_only":
            return _mark_request(
                repo_root,
                persisted,
                status="manual_assist_required",
                reason="claude_app_v1_requires_stage_only",
                decision=decision,
                request_path=request_path,
            )
        dispatch_result = _stage_claude_app(repo_root, persisted)
        return _mark_request(
            repo_root,
            persisted,
            status=dispatch_result["status"],
            reason=dispatch_result["reason"],
            decision=decision,
            dispatch_result=dispatch_result,
            request_path=request_path,
        )

    dispatch_result = (
        _dispatch_codex(repo_root, persisted)
        if provider == "codex"
        else _dispatch_claude_native(repo_root, persisted)
    )
    return _mark_request(
        repo_root,
        persisted,
        status=_string(dispatch_result.get("status")) or "manual_assist_required",
        reason=_string(dispatch_result.get("reason")) or "dispatch_result_missing_reason",
        decision=decision,
        dispatch_result=dispatch_result,
        request_path=request_path,
    )


def approve_seat_request(
    repo_root: Path,
    *,
    request_path: str | Path,
    actor_id: str = "human_operator",
    reason: str | None = None,
) -> dict[str, Any]:
    request = load_seat_request(repo_root, request_path)
    request["approval_mode"] = "approved"
    request["approved_by"] = _string(actor_id) or "human_operator"
    request["approved_at"] = _iso_now()
    request["approval_reason"] = _string(reason) or None
    return route_seat_request(
        repo_root,
        request=request,
        request_path=request_path,
        actor_id=actor_id,
        reason=reason,
    )


def reject_seat_request(
    repo_root: Path,
    *,
    request_path: str | Path,
    actor_id: str = "human_operator",
    reason: str | None = None,
) -> dict[str, Any]:
    request = load_seat_request(repo_root, request_path)
    return _mark_request(
        repo_root,
        {
            **request,
            "rejected_by": _string(actor_id) or "human_operator",
            "rejected_at": _iso_now(),
            "rejection_reason": _string(reason) or None,
        },
        status="rejected",
        reason="operator_rejected",
        request_path=request_path,
    )


def build_approval_metadata(request: Mapping[str, Any]) -> dict[str, Any]:
    model_profile = _model_profile(request)
    presence = _safe_mapping(request.get("presence_decision"))
    runner_contract = _safe_mapping(request.get("runner_contract"))
    dispatch_options = _safe_mapping(request.get("dispatch_options"))
    provider_budget = _safe_mapping(request.get("provider_budget"))
    return {
        "request_id": _string(request.get("request_id")),
        "queue_id": _string(request.get("queue_id")),
        "plan_id": _string(request.get("plan_id")),
        "step_id": _string(request.get("step_id")),
        "seat_id": _string(request.get("seat_id")),
        "provider": _string(request.get("provider")),
        "seat_class": _string(request.get("seat_class")),
        "model": _string(model_profile.get("model") or model_profile.get("model_id") or model_profile.get("id")),
        "effort": _string(model_profile.get("effort")),
        "thread_policy": _string(request.get("thread_policy")),
        "approval_mode": _string(request.get("approval_mode")),
        "presence_mode": _string(presence.get("mode") or "attended"),
        "presence_reason": _string(presence.get("reason")),
        "idle_seconds": presence.get("idle_seconds"),
        "prompt_artifact": _prompt_artifact_display(request.get("prompt_artifact")),
        "status": _string(request.get("status")),
        "reason": _string(request.get("reason")),
        "allowed_write_roots": _string_list(request.get("allowed_write_roots")),
        "dispatch_enabled": bool(dispatch_options.get("enabled")),
        "transform_job_path": _string(
            runner_contract.get("transform_job_path")
            or runner_contract.get("job_path")
            or dispatch_options.get("transform_job_path")
            or dispatch_options.get("job_path")
        ),
        "free_only": provider_budget.get("free_only"),
        "allow_paid": provider_budget.get("allow_paid"),
        "max_usd": provider_budget.get("max_usd"),
        "local_evidence_override_policy_id": _string(
            _safe_mapping(request.get("local_evidence_override_policy")).get("policy_id")
        ),
    }


def iter_pending_approval_requests(repo_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    runtime_root = repo_root / "state" / "autonomy_runtime"
    for path in sorted(runtime_root.glob("*/runtime/plans/*/seat_requests/*.json")):
        try:
            request = load_seat_request(repo_root, path)
        except Exception:
            continue
        status = _string(request.get("status"))
        if status == "pending_approval":
            rows.append((path, request))
    return rows


def approval_command(repo_root: Path, request_path: Path) -> str:
    rel = _relative(repo_root, request_path) or request_path.as_posix()
    return f"./repo-python -m system.lib.type_a_seat_control approve --request {rel} --actor human_operator"


def _json_out(payload: Mapping[str, Any]) -> None:
    print(json.dumps(dict(payload), indent=2, ensure_ascii=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route Type A seat requests through the safe control plane.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to current directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    route_p = sub.add_parser("route", help="Route an existing seat request.")
    route_p.add_argument("--request", required=True, help="Repo-relative or absolute seat request JSON path.")
    route_p.add_argument("--actor", default="system")
    route_p.add_argument("--reason", default=None)

    approve_p = sub.add_parser("approve", help="Approve and route an existing seat request.")
    approve_p.add_argument("--request", required=True, help="Repo-relative or absolute seat request JSON path.")
    approve_p.add_argument("--actor", default="human_operator")
    approve_p.add_argument("--reason", default=None)

    reject_p = sub.add_parser("reject", help="Reject an existing seat request.")
    reject_p.add_argument("--request", required=True, help="Repo-relative or absolute seat request JSON path.")
    reject_p.add_argument("--actor", default="human_operator")
    reject_p.add_argument("--reason", default=None)

    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    if args.command == "route":
        _json_out(route_seat_request(repo_root, request_path=args.request, actor_id=args.actor, reason=args.reason))
        return 0
    if args.command == "approve":
        _json_out(approve_seat_request(repo_root, request_path=args.request, actor_id=args.actor, reason=args.reason))
        return 0
    if args.command == "reject":
        _json_out(reject_seat_request(repo_root, request_path=args.request, actor_id=args.actor, reason=args.reason))
        return 0
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
