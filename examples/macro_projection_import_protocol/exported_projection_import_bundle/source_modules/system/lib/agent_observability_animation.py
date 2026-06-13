"""
Animation-ready projection over the agent observability plane.

The canonical JSONL event store remains the source of truth. This module
compiles a bounded event tail plus status reducers into stable graphic
primitives so the frontend can animate what actually happened without
re-deriving event semantics in UI code.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from system.lib.agent_session_attribution import INFRASTRUCTURE_SOURCE_RUNTIMES


KIND = "agent_observability.animation_scene"
SCHEMA_VERSION = "agent_observability_animation_v0"
DELTA_KIND = "agent_observability.animation_delta"
DELTA_SCHEMA_VERSION = "agent_observability_animation_delta_v0"

DEFAULT_WINDOW_MS = 15 * 60 * 1000
DEFAULT_STALE_AFTER_MS = 2 * 60 * 1000
DEFAULT_LOST_AFTER_MS = 10 * 60 * 1000
MIN_SEGMENT_MS = 600
MAX_INSTANT_SEGMENT_MS = 1400
DEFAULT_DELTA_LIMIT = 300
DEFAULT_MAX_DELTA_OPS = 700
MIN_POLL_MS = 250
MAX_POLL_MS = 2500

PROMPT_TYPES = {"turn.prompt", "message.user"}
MODEL_TYPES = {"intent.observed", "plan.observed", "message.assistant", "message.thinking"}
TOOL_START_TYPES = {"tool.proposed", "tool.started", "subagent.started"}
TOOL_END_TYPES = {"tool.completed", "tool.batch.completed", "subagent.completed"}
WAIT_TYPES = {"permission.requested", "runtime.waiting"}
END_TYPES = {"turn.completed", "session.end"}
ERROR_TYPES = {"runtime.error", "tool.error", "session.error"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat(timespec="milliseconds")


def _parse_iso(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _safe_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _compact(value: object, limit: int = 140) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


REASONING_TEXT_LIMIT = 1600


def _reasoning_text(raw_event: Mapping[str, Any], channel: str, *, limit: int = REASONING_TEXT_LIMIT) -> str:
    """Newline-preserving reasoning/narration preview for model-channel events.

    The single-line ``summary`` (140 chars, newlines collapsed) is the lane
    label; this companion field keeps the operator-facing reasoning legible in
    the inspector so a box reads as *what the model is doing*, not just a tool
    name. Only emitted for the model channel (assistant narration, thinking,
    intent/plan), where the upstream payload already carries the agent's own
    EMITTED text — no inference, no reconstruction of hidden reasoning (Claude's
    redacted thinking arrives upstream as the literal "Thinking..." placeholder
    and is surfaced honestly as such). This is a LOCAL operator cockpit over the
    operator's own sessions, not a public surface, so the text is not redacted
    beyond the upstream payload size-gate; the length cap keeps the scene bounded.
    """
    if channel != "model":
        return ""
    payload = _safe_mapping(raw_event.get("payload"))
    best = ""
    for candidate in (payload.get("content"), raw_event.get("summary")):
        value = str(candidate or "").strip()
        if len(value) > len(best):
            best = value
    if not best:
        return ""
    best = best.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(best) > limit:
        best = best[: limit - 1].rstrip() + "…"
    return best


def _event_id(event: Mapping[str, Any]) -> str:
    raw = str(event.get("id") or "").strip()
    if raw:
        return raw
    return f"seq:{int(event.get('seq') or 0)}"


def _node_event_id(event: Mapping[str, Any]) -> str:
    return f"event:{_event_id(event)}"


def _actor_id(session_id: str) -> str:
    return f"actor:{session_id or 'unknown'}"


def _provider_label(provider: object) -> str:
    key = str(provider or "unknown").strip().lower()
    if key in {"codex_app", "codex"} or key.startswith("codex"):
        return "Codex"
    if key in {"claude_code", "claude"} or key.startswith("claude"):
        return "Claude Code"
    if key == "station_render":
        return "Station Render"
    if key == "operator_bridge":
        return "Operator Bridge"
    if key == "metabolism":
        return "Metabolism"
    if key == "backend":
        return "Backend"
    if key == "unknown":
        return "Unknown"
    return " ".join(part[:1].upper() + part[1:] for part in key.replace("-", "_").split("_") if part)


def _tool_name(event: Mapping[str, Any], tool_names: Mapping[str, str] | None = None) -> Optional[str]:
    payload = _safe_mapping(event.get("payload"))
    for key in ("tool_name", "name", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    tool_input = _safe_mapping(payload.get("tool_input"))
    value = tool_input.get("tool_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    tool_id = str(event.get("tool_use_id") or payload.get("tool_use_id") or "").strip()
    if tool_id and tool_names and tool_names.get(tool_id):
        return tool_names[tool_id]
    return None


def _tool_command_text(event: Mapping[str, Any]) -> str:
    payload = _safe_mapping(event.get("payload"))
    tool_input = _safe_mapping(payload.get("tool_input"))
    command = tool_input.get("command") or payload.get("command") or payload.get("content")
    return str(command or event.get("summary") or "")


def _touched_files(event: Mapping[str, Any]) -> list[str]:
    payload = _safe_mapping(event.get("payload"))
    tool_input = _safe_mapping(payload.get("tool_input"))
    candidates: list[Any] = [
        tool_input.get("file_path"),
        tool_input.get("path"),
        tool_input.get("notebook_path"),
        tool_input.get("target_file"),
    ]
    for key in ("files", "paths", "file_paths"):
        value = tool_input.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    if isinstance(event.get("artifact_refs"), list):
        candidates.extend(event.get("artifact_refs") or [])

    out: list[str] = []
    for value in candidates:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text.startswith(("http://", "https://")):
            continue
        if text not in out:
            out.append(text)
    return out[:12]


def _event_time(event: Mapping[str, Any]) -> Optional[datetime]:
    return _parse_iso(event.get("occurred_at") or event.get("observed_at"))


def _event_kind(event: Mapping[str, Any], tool_names: Mapping[str, str] | None = None) -> str:
    canonical = str(event.get("canonical_type") or "")
    runtime = str(event.get("source_runtime") or "")
    if canonical in ERROR_TYPES or canonical.endswith(".error"):
        return "error"
    if canonical in WAIT_TYPES:
        return "wait"
    if canonical in PROMPT_TYPES:
        return "prompt"
    if canonical in MODEL_TYPES:
        return "model"
    if canonical.startswith("compaction."):
        return "compaction"
    if canonical in {"artifact.changed", "artifact.created"}:
        return "render" if runtime == "station_render" else "artifact"
    if canonical.startswith("session."):
        return "lifecycle"
    if canonical.startswith("usage."):
        return "usage"
    if canonical.startswith("subagent."):
        return "subagent"
    if canonical.startswith("tool."):
        tool = (_tool_name(event, tool_names) or "").lower()
        command = _tool_command_text(event).lower()
        if tool in {"read", "grep", "glob", "ls"}:
            return "read"
        if tool in {"edit", "write", "multiedit", "notebookedit"}:
            return "edit"
        if tool in {"bash", "shell", "exec"}:
            if any(token in command for token in ("station_render", "screenshot", "playwright", "render")):
                return "render"
            if any(token in command for token in ("git commit", "scoped_commit", "checkpoint")):
                return "commit"
            if any(token in command for token in ("pytest", "vitest", "npm test", "npm run build", "tsc", "ruff", "lint")):
                return "validation"
        return "tool"
    return "other"


def _event_status(event: Mapping[str, Any], *, paired_end: Mapping[str, Any] | None = None) -> str:
    canonical = str(event.get("canonical_type") or "")
    payload = _safe_mapping(event.get("payload"))
    if canonical in ERROR_TYPES or canonical.endswith(".error") or bool(payload.get("is_error")):
        return "fail"
    exit_code = payload.get("exit_code")
    if exit_code not in (None, "", 0, "0"):
        return "fail"
    if paired_end is None and canonical in TOOL_START_TYPES:
        return "running"
    if canonical in WAIT_TYPES:
        return "blocked"
    if canonical in TOOL_END_TYPES or canonical in END_TYPES:
        return "pass"
    return "observed"


def _semantic_token(kind: str, status: str) -> str:
    if status in {"fail", "blocked"} or kind == "error":
        return "danger"
    if kind in {"validation", "commit"}:
        return "proof"
    if kind in {"edit", "artifact", "render"}:
        return "material"
    if kind in {"prompt", "model"}:
        return "cognition"
    if kind == "read":
        return "evidence"
    if kind == "wait":
        return "attention"
    return "neutral"


def _event_channel(kind: str, canonical_type: str, runtime: str) -> str:
    if _runtime_is_infrastructure(runtime):
        return "infrastructure"
    if canonical_type.startswith("session.") or canonical_type.startswith("turn."):
        return "session_lifecycle"
    if kind in {"prompt", "model", "compaction", "usage"}:
        return "model"
    if kind in {"read", "edit"}:
        return "file_io"
    if kind in {"validation", "render", "commit"}:
        return "proof"
    if kind in {"artifact"}:
        return "artifact"
    if kind in {"error", "wait"}:
        return "attention"
    if kind in {"subagent", "tool"} or canonical_type.startswith("tool."):
        return "tool_io"
    return "quality" if canonical_type.startswith("stream.") else "tool_io"


def _event_priority(kind: str, status: str, canonical_type: str) -> str:
    if status == "fail" or kind == "error":
        return "critical"
    if status == "blocked" or canonical_type == "permission.requested":
        return "high"
    if kind in {"validation", "render", "commit", "edit"}:
        return "normal"
    if kind in {"usage", "compaction", "lifecycle"}:
        return "low"
    return "normal"


def _animation_directive(kind: str, status: str, canonical_type: str) -> str:
    if status in {"fail", "blocked"}:
        return "raise_attention"
    if canonical_type in TOOL_START_TYPES:
        return "start_segment"
    if canonical_type in TOOL_END_TYPES or canonical_type in END_TYPES:
        return "complete_segment"
    if kind == "prompt":
        return "spawn_or_focus_actor"
    if kind == "model":
        return "pulse_actor"
    if kind == "edit":
        return "touch_file"
    if kind in {"validation", "render", "commit"}:
        return "emit_proof"
    if kind == "artifact":
        return "materialize_artifact"
    if kind == "subagent":
        return "link_subagent"
    return "append_event"


def _coalesce_key(
    *,
    session_id: str,
    channel: str,
    canonical_type: str,
    tool_name: str | None,
    tool_use_id: str | None,
    files: Sequence[str],
) -> str:
    if tool_use_id:
        return f"{session_id}:{channel}:tool:{tool_use_id}"
    if files:
        return f"{session_id}:{channel}:file:{files[0]}"
    if tool_name:
        return f"{session_id}:{channel}:tool_name:{tool_name.lower()}"
    return f"{session_id}:{channel}:{canonical_type}"


def _runtime_is_infrastructure(runtime: object) -> bool:
    return str(runtime or "") in INFRASTRUCTURE_SOURCE_RUNTIMES


def _event_sort_key(event: Mapping[str, Any]) -> tuple[datetime, int]:
    parsed = _event_time(event) or datetime.fromtimestamp(0, tz=timezone.utc)
    return parsed, int(event.get("seq") or 0)


def _duration_from_payload(event: Mapping[str, Any]) -> Optional[int]:
    payload = _safe_mapping(event.get("payload"))
    for key in ("duration_ms", "elapsed_ms", "wall_ms", "view_ready_ms", "load_ms"):
        value = payload.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            return int(value)
    duration_s = payload.get("duration_s") or payload.get("elapsed_s")
    if isinstance(duration_s, (int, float)) and duration_s >= 0:
        return int(duration_s * 1000)
    return None


def _merge_unique(existing: Sequence[str] | None, values: Sequence[str] | None, *, limit: int = 16) -> list[str]:
    out: list[str] = []
    for source in (existing or []), (values or []):
        for value in source:
            text = str(value or "").strip()
            if text and text not in out:
                out.append(text)
    return out[:limit]


def _status_int(status: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(status.get(key) or default)
    except (TypeError, ValueError):
        return default


def _earliest_available_seq(status: Mapping[str, Any]) -> int:
    latest = _status_int(status, "seq")
    history_size = _status_int(status, "history_size")
    if latest <= 0 or history_size <= 0:
        return 0
    return max(1, latest - history_size + 1)


def _history_saturation_ratio(status: Mapping[str, Any]) -> float | None:
    max_history = _status_int(status, "max_history")
    if max_history <= 0:
        return None
    return round(min(1.0, _status_int(status, "history_size") / max_history), 4)


def _event_rate_per_s(event_count: int, duration_ms: int) -> float:
    if event_count <= 0:
        return 0.0
    seconds = max(1.0, duration_ms / 1000)
    return round(event_count / seconds, 3)


def _recommended_poll_ms(event_rate_per_s: float, *, degraded: bool, quiet: bool) -> int:
    if degraded:
        return 1500
    if event_rate_per_s >= 40:
        return 1200
    if event_rate_per_s >= 15:
        return 800
    if quiet:
        return 1500
    return 500


def _channel_manifest(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(event.get("animation_channel") or "tool_io") for event in events)
    labels = {
        "session_lifecycle": "Session lifecycle",
        "model": "Prompt/model",
        "tool_io": "Tool I/O",
        "file_io": "File I/O",
        "proof": "Proof",
        "artifact": "Artifact",
        "attention": "Attention",
        "quality": "Quality",
        "infrastructure": "Infrastructure",
    }
    order = [
        "attention",
        "session_lifecycle",
        "model",
        "tool_io",
        "file_io",
        "proof",
        "artifact",
        "quality",
        "infrastructure",
    ]
    # Always emit the full canonical channel set, even channels with zero events
    # in this build's window/slice. The live floor advances by deltas, and each
    # delta rebuilds the manifest from only the events since the cursor; filtering
    # to present-only channels made the channel set (and the default-visible set)
    # COLLAPSE to whatever a 1-2s slice happened to contain, so the scene appeared
    # to "cycle through channels" and silently hid every segment off the surviving
    # channel. A stable full manifest keeps the mixer and the full-scene default
    # constant across frames; counts still reflect this build's events.
    return [
        {
            "id": channel,
            "label": labels.get(channel, channel.replace("_", " ").title()),
            "event_count": counts.get(channel, 0),
            "visible_by_default": channel != "infrastructure",
        }
        for channel in order
    ]


def _cursor_payload(
    *,
    status: Mapping[str, Any],
    since_seq: int,
    events: Sequence[Mapping[str, Any]],
    requested_limit: int,
    requested_window_ms: int,
) -> dict[str, Any]:
    latest_seq = _status_int(status, "seq")
    event_seqs = [int(event.get("seq") or 0) for event in events]
    max_event_seq = max(event_seqs, default=since_seq)
    min_event_seq = min(event_seqs, default=None)
    return {
        "since_seq": int(since_seq or 0),
        "latest_seq": latest_seq,
        "next_since_seq": max(since_seq, max_event_seq),
        "min_event_seq": min_event_seq,
        "max_event_seq": max_event_seq if event_seqs else None,
        "earliest_available_seq": _earliest_available_seq(status),
        "history_size": _status_int(status, "history_size"),
        "max_history": _status_int(status, "max_history"),
        "limit": requested_limit,
        "window_ms": requested_window_ms,
        "has_more": latest_seq > max_event_seq,
    }


def _snapshot_required(status: Mapping[str, Any], since_seq: int, *, allow_initial_delta: bool = False) -> bool:
    if since_seq <= 0 and not allow_initial_delta:
        return True
    earliest = _earliest_available_seq(status)
    if earliest and since_seq and since_seq < earliest - 1:
        return True
    if allow_initial_delta:
        return False
    return _status_int(status, "dropped_count") > 0 or _status_int(status, "gap_count") > 0


def _actor_sort_key(item: Mapping[str, Any]) -> tuple[int, int, str, str]:
    heartbeat = str(item.get("heartbeat") or "")
    status = str(item.get("status") or "")
    currently_live = item.get("currently_live") is True
    mid_turn = item.get("mid_turn") is True
    active_statuses = {
        "editing",
        "validating",
        "rendering",
        "committing",
        "tool_running",
        "model_turn",
        "working",
        "waiting_operator",
    }
    if heartbeat == "live" and (currently_live or mid_turn or status in active_statuses):
        activity_rank = 0
    elif heartbeat == "live":
        activity_rank = 1
    elif currently_live and status in active_statuses:
        activity_rank = 2
    elif heartbeat == "unknown":
        activity_rank = 3
    elif heartbeat == "stale":
        activity_rank = 4
    elif heartbeat == "lost":
        activity_rank = 5
    elif status == "done_unreviewed":
        activity_rank = 6
    else:
        activity_rank = 7
    try:
        lag_ms = int(item.get("lag_ms") or 0)
    except Exception:
        lag_ms = 0
    return (activity_rank, lag_ms, str(item.get("provider_label") or ""), str(item.get("session_id") or ""))


def _backpressure_payload(
    *,
    status: Mapping[str, Any],
    event_count: int,
    duration_ms: int,
    op_count: int = 0,
    dropped_op_count: int = 0,
    max_delta_ops: int = DEFAULT_MAX_DELTA_OPS,
) -> dict[str, Any]:
    event_rate = _event_rate_per_s(event_count, duration_ms)
    degraded = bool(
        dropped_op_count
        or _status_int(status, "dropped_count") > 0
        or _status_int(status, "gap_count") > 0
        or (max_delta_ops > 0 and op_count >= int(max_delta_ops * 0.9))
    )
    return {
        "min_poll_ms": MIN_POLL_MS,
        "recommended_poll_ms": _recommended_poll_ms(event_rate, degraded=degraded, quiet=event_count == 0),
        "max_poll_ms": MAX_POLL_MS,
        "event_rate_per_s": event_rate,
        "history_saturation_ratio": _history_saturation_ratio(status),
        "max_events_per_delta": DEFAULT_DELTA_LIMIT,
        "max_ops_per_delta": max_delta_ops,
        "op_count": op_count,
        "dropped_op_count": dropped_op_count,
        "dropped_event_count": _status_int(status, "dropped_count"),
        "gap_count": _status_int(status, "gap_count"),
        "degraded": degraded,
    }


def _quality_envelope(
    *,
    authority: str,
    confidence: str = "authority_backed",
    missingness: Sequence[str] | None = None,
    source: str = "agent_trace_event",
) -> dict[str, Any]:
    notes = [str(item) for item in (missingness or []) if item]
    return {
        "authority": authority,
        "confidence": confidence,
        "missingness": notes,
        "source": source,
    }


def _generated_state_for_path(path: str) -> str:
    if path.startswith("system/server/ui/src/api/generated/"):
        return "generated_projection"
    if path.startswith("state/observability/") or path.startswith("state/task_ledger/"):
        return "receipt_or_runtime_state"
    if "/generated_" in path or path.endswith(".generated.md"):
        return "generated_projection"
    return "source"


def _file_operation(kind: str, canonical_type: str) -> str:
    if kind == "read":
        return "read"
    if kind == "edit":
        return "write"
    if kind == "validation":
        return "validate"
    if kind == "render":
        return "render"
    if kind == "commit":
        return "commit"
    if kind == "artifact" or canonical_type.startswith("artifact."):
        return "generated"
    if kind == "error":
        return "error"
    return "touch"


def _proof_kind(event: Mapping[str, Any]) -> str | None:
    kind = str(event.get("animation_kind") or "")
    summary = str(event.get("summary") or "").lower()
    tool = str(event.get("tool_name") or "").lower()
    if kind == "validation":
        if "tsc" in summary or "type" in summary:
            return "typecheck"
        if "lint" in summary or "ruff" in summary:
            return "lint"
        if "build" in summary:
            return "build"
        return "test" if "pytest" in summary or "test" in summary else "validation"
    if kind == "render":
        return "render"
    if kind == "commit":
        return "commit"
    if kind == "artifact":
        return "artifact"
    if tool == "bash" and any(token in summary for token in ("pytest", "tsc", "build", "lint", "render")):
        return "validation"
    return None


def _proof_scope(event: Mapping[str, Any]) -> str:
    files = list(event.get("touched_files") or [])
    summary = str(event.get("summary") or "").lower()
    if any(_generated_state_for_path(path) == "generated_projection" for path in files):
        return "generated_projection"
    if any(token in summary for token in ("system/server/tests/test_agent_observability", "agent_observability_animation")):
        return "owned_surface"
    if any(token in summary for token in ("full", "all", "tsc -b", "npm run build")):
        return "full_repo_or_frontend"
    return "unknown"


def _claim_lookup(mission_status: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    claims_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = list(_safe_mapping(mission_status).get("missions") or []) + list(_safe_mapping(mission_status).get("demoted_missions") or [])
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        sid = str(row.get("session_id") or "")
        for claim in row.get("active_claims") or []:
            if not isinstance(claim, Mapping):
                continue
            path = str(claim.get("path") or claim.get("scope_id") or "").strip()
            if not path:
                continue
            claims_by_path[path].append({
                "claim_id": claim.get("claim_id"),
                "path": path,
                "owner_session_id": sid or claim.get("session_id"),
                "scope_kind": claim.get("scope_kind"),
                "leased_until": claim.get("leased_until"),
            })
    return claims_by_path


def _claim_state_for_path(
    *,
    path: str,
    session_id: str,
    claims_by_path: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[str, list[dict[str, Any]]]:
    claims = [dict(claim) for claim in claims_by_path.get(path, [])]
    if not claims:
        return "unknown", []
    if any(str(claim.get("owner_session_id") or "") == session_id for claim in claims):
        return "owned_by_self", claims
    return "owned_by_other", claims


def _build_file_impacts(
    *,
    events: Sequence[Mapping[str, Any]],
    claims_by_path: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    impacts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for event in events:
        paths = list(event.get("touched_files") or [])
        for ref in event.get("artifact_refs") or []:
            if isinstance(ref, str) and not ref.startswith(("http://", "https://")):
                paths.append(ref)
        for path in paths:
            text = str(path or "").strip()
            if not text:
                continue
            operation = _file_operation(str(event.get("animation_kind") or ""), str(event.get("canonical_type") or ""))
            key = (str(event.get("id")), text, operation)
            if key in seen:
                continue
            seen.add(key)
            claim_state, claim_refs = _claim_state_for_path(
                path=text,
                session_id=str(event.get("session_id") or ""),
                claims_by_path=claims_by_path,
            )
            impacts.append({
                "id": f"file-impact:{event.get('id')}:{len(impacts)}",
                "path": text,
                "operation": operation,
                "source": "artifact_ref" if text in (event.get("artifact_refs") or []) else "tool_or_event_projection",
                "session_id": event.get("session_id"),
                "actor_id": event.get("actor_id"),
                "event_id": event.get("id"),
                "seq": event.get("seq"),
                "channel": event.get("animation_channel"),
                "claim_state": claim_state,
                "claim_refs": claim_refs[:4],
                "generated_state": _generated_state_for_path(text),
                "quality": _quality_envelope(
                    authority="projection",
                    confidence="derived_strong" if operation in {"read", "write", "validate", "render", "commit"} else "heuristic",
                    source="event_touched_files",
                ),
            })
    return impacts


def _build_proof_receipts(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for event in events:
        kind = _proof_kind(event)
        if not kind:
            continue
        receipts.append({
            "id": f"proof:{event.get('id')}",
            "kind": kind,
            "status": event.get("status"),
            "session_id": event.get("session_id"),
            "actor_id": event.get("actor_id"),
            "event_id": event.get("id"),
            "seq": event.get("seq"),
            "command_ref": event.get("summary"),
            "artifact_refs": list(event.get("artifact_refs") or []),
            "duration_ms": None,
            "scope": _proof_scope(event),
            "quality": _quality_envelope(authority="canonical_event", source="agent_trace_event"),
        })
    return receipts


def _build_spans(tracks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for track in tracks:
        for segment in track.get("segments") or []:
            if not isinstance(segment, Mapping):
                continue
            start_ms = int(segment.get("start_ms") or 0)
            end_ms = int(segment.get("end_ms") or start_ms)
            spans.append({
                "id": f"span:{segment.get('event_id')}",
                "event_id": segment.get("event_id"),
                "seq": segment.get("seq"),
                "session_id": track.get("session_id"),
                "actor_id": track.get("actor_id"),
                "provider": track.get("provider"),
                "channel": segment.get("channel"),
                "kind": segment.get("kind"),
                "status": segment.get("status"),
                "priority": segment.get("priority"),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": max(0, end_ms - start_ms),
                "coalesce_key": segment.get("coalesce_key"),
                "label": segment.get("label"),
                "quality": _quality_envelope(authority="canonical_event", source="agent_trace_event"),
            })
    return spans


def _build_flows(
    *,
    events_by_session: Mapping[str, Sequence[Mapping[str, Any]]],
    edges: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    for sid, session_events in events_by_session.items():
        ordered = sorted(session_events, key=lambda event: int(event.get("seq") or 0))
        for prev, cur in zip(ordered, ordered[1:]):
            flows.append({
                "id": f"flow:sequence:{prev.get('id')}->{cur.get('id')}",
                "type": "session_sequence",
                "from_event_id": prev.get("id"),
                "to_event_id": cur.get("id"),
                "from_node": prev.get("node_id"),
                "to_node": cur.get("node_id"),
                "session_id": sid,
                "seq": cur.get("seq"),
                "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="seq_order"),
            })
    for edge in edges:
        edge_type = str(edge.get("type") or "")
        if edge_type not in {"tool_lifecycle", "causal_parent", "tool_event", "artifact_emitted"}:
            continue
        flows.append({
            "id": f"flow:{edge.get('id')}",
            "type": edge_type,
            "from_node": edge.get("from"),
            "to_node": edge.get("to"),
            "event_id": edge.get("event_id"),
            "seq": edge.get("seq"),
            "tool_use_id": edge.get("tool_use_id"),
            "quality": _quality_envelope(
                authority="canonical_event" if edge_type in {"tool_lifecycle", "causal_parent"} else "projection",
                confidence="authority_backed" if edge_type in {"tool_lifecycle", "causal_parent"} else "derived_strong",
                source="event_edge",
            ),
        })
    return flows


def _build_counters(
    *,
    actors: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    attention: Sequence[Mapping[str, Any]],
    file_impacts: Sequence[Mapping[str, Any]],
    proof_receipts: Sequence[Mapping[str, Any]],
    status: Mapping[str, Any],
    duration_ms: int,
) -> list[dict[str, Any]]:
    channel_counts = Counter(str(event.get("animation_channel") or "unknown") for event in events)
    counters = [
        ("active_agents", len(actors), "count"),
        ("events", len(events), "count"),
        ("attention_items", len(attention), "count"),
        ("file_impacts", len(file_impacts), "count"),
        ("proof_receipts", len(proof_receipts), "count"),
        ("event_rate_per_s", _event_rate_per_s(len(events), duration_ms), "rate"),
        ("dropped_events", _status_int(status, "dropped_count"), "count"),
        ("stream_gaps", _status_int(status, "gap_count"), "count"),
    ]
    out = [
        {
            "id": f"counter:{name}",
            "name": name,
            "value": value,
            "unit": unit,
            "channel": "quality" if name in {"dropped_events", "stream_gaps"} else "session_lifecycle",
            "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="scene_reducer"),
        }
        for name, value, unit in counters
    ]
    for channel, count in sorted(channel_counts.items()):
        out.append({
            "id": f"counter:channel:{channel}",
            "name": f"channel.{channel}",
            "value": count,
            "unit": "count",
            "channel": channel,
            "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="scene_reducer"),
        })
    return out


def build_agent_observability_animation_scene(
    *,
    events: Sequence[Mapping[str, Any]],
    status: Mapping[str, Any],
    mission_status: Mapping[str, Any] | None = None,
    now: datetime | None = None,
    window_ms: int = DEFAULT_WINDOW_MS,
    include_infrastructure: bool = False,
    session_id: str | None = None,
    source_runtime: str | None = None,
    since_seq: int = 0,
    limit: int = 600,
) -> dict[str, Any]:
    """Compile live trace evidence into frontend animation primitives."""
    requested_limit = max(1, min(int(limit or 600), 2000))
    requested_window_ms = max(1_000, int(window_ms or DEFAULT_WINDOW_MS))
    raw_events = [dict(event) for event in events if isinstance(event, Mapping)]
    raw_event_count = len(raw_events)

    scoped_events: list[dict[str, Any]] = []
    omitted_infrastructure = 0
    omitted_scope = 0
    for event in raw_events:
        seq = int(event.get("seq") or 0)
        runtime = str(event.get("source_runtime") or "unknown")
        if since_seq and seq <= since_seq:
            omitted_scope += 1
            continue
        if session_id and str(event.get("session_id") or "") != session_id:
            omitted_scope += 1
            continue
        if source_runtime and runtime != source_runtime:
            omitted_scope += 1
            continue
        if not include_infrastructure and _runtime_is_infrastructure(runtime):
            omitted_infrastructure += 1
            continue
        scoped_events.append(event)

    scoped_events.sort(key=_event_sort_key)
    if len(scoped_events) > requested_limit:
        scoped_events = scoped_events[-requested_limit:]

    latest_event_time = max((_event_time(event) for event in scoped_events if _event_time(event)), default=None)
    anchor_time = now or latest_event_time or _utc_now()
    window_start = anchor_time - timedelta(milliseconds=requested_window_ms)
    windowed_events: list[dict[str, Any]] = []
    omitted_window = 0
    malformed_time_count = 0
    for event in scoped_events:
        parsed = _event_time(event)
        if parsed is None:
            malformed_time_count += 1
            windowed_events.append(event)
            continue
        if parsed < window_start:
            omitted_window += 1
            continue
        windowed_events.append(event)

    if len(windowed_events) > requested_limit:
        omitted_window += len(windowed_events) - requested_limit
        windowed_events = windowed_events[-requested_limit:]

    if windowed_events:
        first_time = min((_event_time(event) for event in windowed_events if _event_time(event)), default=window_start)
        last_time = max((_event_time(event) for event in windowed_events if _event_time(event)), default=anchor_time)
    else:
        first_time = window_start
        last_time = anchor_time
    if first_time is None:
        first_time = window_start
    if last_time is None:
        last_time = anchor_time
    duration_ms = max(1, int((last_time - first_time).total_seconds() * 1000))

    tool_names: dict[str, str] = {}
    tool_start_by_id: dict[str, dict[str, Any]] = {}
    tool_end_by_id: dict[str, dict[str, Any]] = {}
    claims_by_path = _claim_lookup(mission_status)
    for event in windowed_events:
        tool_id = str(event.get("tool_use_id") or _safe_mapping(event.get("payload")).get("tool_use_id") or "").strip()
        if not tool_id:
            continue
        name = _tool_name(event)
        if name:
            tool_names[tool_id] = name
        canonical = str(event.get("canonical_type") or "")
        if canonical in TOOL_START_TYPES:
            tool_start_by_id.setdefault(tool_id, event)
        elif canonical in TOOL_END_TYPES or canonical in ERROR_TYPES or canonical.endswith(".error"):
            tool_end_by_id.setdefault(tool_id, event)

    actor_candidates: dict[str, dict[str, Any]] = {}

    def ensure_actor(sid: object, provider: object = None) -> dict[str, Any]:
        resolved_sid = str(sid or "unknown").strip() or "unknown"
        actor = actor_candidates.setdefault(
            resolved_sid,
            {
                "session_id": resolved_sid,
                "provider": str(provider or "unknown"),
                "title": None,
                "current_action": None,
                "cwd": None,
                "last_observed_at": None,
                "last_activity_at": None,
                "last_canonical_type": None,
                "lag_ms": None,
                "currently_live": None,
                "mid_turn": None,
                "touched_files": [],
                "source_refs": [],
                "event_count": 0,
            },
        )
        if provider and actor.get("provider") == "unknown":
            actor["provider"] = str(provider)
        return actor

    for session in status.get("active_sessions") or []:
        if not isinstance(session, Mapping):
            continue
        provider = session.get("source_runtime")
        if source_runtime and provider != source_runtime:
            continue
        if not include_infrastructure and _runtime_is_infrastructure(provider):
            continue
        sid = str(session.get("session_id") or "unknown")
        if session_id and sid != session_id:
            continue
        actor = ensure_actor(sid, provider)
        actor.update({
            "title": actor.get("title") or session.get("title") or session.get("summary"),
            "current_action": actor.get("current_action") or session.get("current_activity") or session.get("summary"),
            "cwd": actor.get("cwd") or session.get("cwd"),
            "last_observed_at": actor.get("last_observed_at") or session.get("last_observed_at"),
            "last_activity_at": actor.get("last_activity_at") or session.get("last_activity_at"),
            "last_canonical_type": actor.get("last_canonical_type") or session.get("last_canonical_type"),
            "lag_ms": int(float(session.get("lag_s") or 0) * 1000) if session.get("lag_s") is not None else actor.get("lag_ms"),
        })
        actor["touched_files"] = _merge_unique(actor.get("touched_files"), list(session.get("touched_files") or []))
        if session.get("transcript_path"):
            actor["source_refs"] = _merge_unique(actor.get("source_refs"), [str(session.get("transcript_path"))])

    for row in list(_safe_mapping(mission_status).get("missions") or []) + list(_safe_mapping(mission_status).get("demoted_missions") or []):
        if not isinstance(row, Mapping):
            continue
        provider = row.get("source_runtime")
        if source_runtime and provider != source_runtime:
            continue
        if not include_infrastructure and _runtime_is_infrastructure(provider):
            continue
        sid = str(row.get("session_id") or "unknown")
        if session_id and sid != session_id:
            continue
        actor = ensure_actor(sid, provider)
        actor.update({
            "title": actor.get("title") or row.get("title"),
            "current_action": actor.get("current_action") or row.get("current_activity"),
            "cwd": actor.get("cwd") or row.get("cwd"),
            "last_observed_at": actor.get("last_observed_at") or row.get("last_observed_at"),
            "last_activity_at": actor.get("last_activity_at") or row.get("last_activity_at"),
            "last_canonical_type": actor.get("last_canonical_type") or row.get("last_canonical_type"),
            "lag_ms": int(float(row.get("lag_s") or 0) * 1000) if row.get("lag_s") is not None else actor.get("lag_ms"),
            "currently_live": row.get("currently_live"),
            "mid_turn": row.get("mid_turn"),
        })
        actor["touched_files"] = _merge_unique(actor.get("touched_files"), list(row.get("touched_files") or []))
        raw_refs = _safe_mapping(row.get("raw_refs"))
        if raw_refs.get("events_endpoint"):
            actor["source_refs"] = _merge_unique(actor.get("source_refs"), [str(raw_refs.get("events_endpoint"))])

    normalized_events: list[dict[str, Any]] = []
    events_by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_node_by_tool_start: dict[str, str] = {}
    event_node_by_tool_end: dict[str, str] = {}
    touched_files_by_session: dict[str, list[str]] = defaultdict(list)

    for event in windowed_events:
        sid = str(event.get("session_id") or "unknown")
        provider = str(event.get("source_runtime") or "unknown")
        actor = ensure_actor(sid, provider)
        event_time = _event_time(event) or first_time
        start_ms = max(0, int((event_time - first_time).total_seconds() * 1000))
        kind = _event_kind(event, tool_names)
        tool_id = str(event.get("tool_use_id") or _safe_mapping(event.get("payload")).get("tool_use_id") or "").strip() or None
        paired_end = tool_end_by_id.get(tool_id or "") if tool_id and event is tool_start_by_id.get(tool_id) else None
        status_value = _event_status(event, paired_end=paired_end)
        summary = _compact(event.get("summary") or _safe_mapping(event.get("payload")).get("content") or event.get("canonical_type"))
        files = _touched_files(event)
        canonical_type = str(event.get("canonical_type") or "unknown")
        tool_name = _tool_name(event, tool_names)
        channel = _event_channel(kind, canonical_type, provider)
        reasoning_text = _reasoning_text(event, channel)
        priority = _event_priority(kind, status_value, canonical_type)
        directive = _animation_directive(kind, status_value, canonical_type)
        coalesce_key = _coalesce_key(
            session_id=sid,
            channel=channel,
            canonical_type=canonical_type,
            tool_name=tool_name,
            tool_use_id=tool_id,
            files=files,
        )
        actor["event_count"] = int(actor.get("event_count") or 0) + 1
        actor["provider"] = provider if actor.get("provider") == "unknown" else actor.get("provider")
        actor["current_action"] = summary or actor.get("current_action")
        actor["last_canonical_type"] = event.get("canonical_type") or actor.get("last_canonical_type")
        actor["last_observed_at"] = event.get("observed_at") or actor.get("last_observed_at")
        actor["last_activity_at"] = event.get("occurred_at") or event.get("observed_at") or actor.get("last_activity_at")
        actor["cwd"] = event.get("cwd") or actor.get("cwd")
        actor["touched_files"] = _merge_unique(actor.get("touched_files"), files)
        actor["source_refs"] = _merge_unique(actor.get("source_refs"), [event.get("transcript_path")] if event.get("transcript_path") else [])
        touched_files_by_session[sid] = _merge_unique(touched_files_by_session[sid], files)

        node_id = _node_event_id(event)
        if tool_id and str(event.get("canonical_type") or "") in TOOL_START_TYPES:
            event_node_by_tool_start[tool_id] = node_id
        if tool_id and (str(event.get("canonical_type") or "") in TOOL_END_TYPES or status_value == "fail"):
            event_node_by_tool_end[tool_id] = node_id
        normalized = {
            "id": _event_id(event),
            "node_id": node_id,
            "seq": int(event.get("seq") or 0),
            "session_id": sid,
            "actor_id": _actor_id(sid),
            "source_runtime": provider,
            "provider_label": _provider_label(provider),
            "canonical_type": canonical_type,
            "source_event_name": str(event.get("source_event_name") or ""),
            "animation_kind": kind,
            "animation_channel": channel,
            "animation_directive": directive,
            "status": status_value,
            "priority": priority,
            "semantic_token": _semantic_token(kind, status_value),
            "coalesce_key": coalesce_key,
            "occurred_at": event.get("occurred_at"),
            "observed_at": event.get("observed_at"),
            "time_ms": start_ms,
            "summary": summary,
            "text": reasoning_text,
            "tool_use_id": tool_id,
            "tool_name": tool_name,
            "subagent_id": event.get("subagent_id"),
            "artifact_refs": list(event.get("artifact_refs") or []),
            "touched_files": files,
            "source_ref": {
                "event_id": _event_id(event),
                "seq": int(event.get("seq") or 0),
                "trace_id": event.get("trace_id"),
                "raw_event_available": True,
            },
            "quality": _quality_envelope(
                authority="canonical_event",
                missingness=["missing_parseable_time"] if _event_time(event) is None else [],
                source="agent_trace_event",
            ),
        }
        normalized_events.append(normalized)
        events_by_session[sid].append(normalized)

    actors: list[dict[str, Any]] = []
    for sid, actor in actor_candidates.items():
        provider = str(actor.get("provider") or "unknown")
        last_type = str(actor.get("last_canonical_type") or "")
        lag_ms = actor.get("lag_ms")
        if lag_ms is None:
            parsed = _parse_iso(actor.get("last_observed_at") or actor.get("last_activity_at"))
            lag_ms = int(max(0.0, (anchor_time - parsed).total_seconds()) * 1000) if parsed else None
        heartbeat = "unknown"
        if lag_ms is not None:
            heartbeat = "lost" if lag_ms > DEFAULT_LOST_AFTER_MS else "stale" if lag_ms > DEFAULT_STALE_AFTER_MS else "live"
        current_kind = _event_kind({"canonical_type": last_type, "source_runtime": provider, "payload": {}, "summary": actor.get("current_action")}, tool_names)
        if heartbeat in {"stale", "lost"} and last_type not in END_TYPES:
            status_value = "stale"
        elif last_type in ERROR_TYPES or last_type.endswith(".error"):
            status_value = "blocked"
        elif last_type == "permission.requested":
            status_value = "waiting_operator"
        elif current_kind == "edit":
            status_value = "editing"
        elif current_kind == "validation":
            status_value = "validating"
        elif current_kind == "render":
            status_value = "rendering"
        elif current_kind == "commit":
            status_value = "committing"
        elif current_kind in {"tool", "read", "subagent"} or last_type in TOOL_START_TYPES:
            status_value = "tool_running"
        elif current_kind in {"prompt", "model"}:
            status_value = "model_turn"
        elif last_type in END_TYPES:
            status_value = "done_unreviewed"
        else:
            status_value = "working"
        actors.append({
            "id": _actor_id(sid),
            "session_id": sid,
            "provider": provider,
            "provider_label": _provider_label(provider),
            "title": _compact(actor.get("title") or sid, 96),
            "status": status_value,
            "heartbeat": heartbeat,
            "current_action": _compact(actor.get("current_action") or last_type or "observed", 160),
            "cwd": actor.get("cwd"),
            "last_observed_at": actor.get("last_observed_at"),
            "last_activity_at": actor.get("last_activity_at"),
            "last_canonical_type": last_type or None,
            "lag_ms": lag_ms,
            "currently_live": actor.get("currently_live"),
            "mid_turn": actor.get("mid_turn"),
            "event_count": int(actor.get("event_count") or 0),
            "touched_files": _merge_unique(actor.get("touched_files"), touched_files_by_session.get(sid)),
            "source_refs": list(actor.get("source_refs") or [])[:10],
            "quality": _quality_envelope(
                authority="projection",
                confidence="derived_strong",
                missingness=["stale_source"] if heartbeat in {"stale", "lost"} else [],
                source="agent_trace_status_and_mission_status",
            ),
        })
    actors.sort(key=_actor_sort_key)
    actor_order = {actor["session_id"]: index for index, actor in enumerate(actors)}

    tracks: list[dict[str, Any]] = []
    for actor in actors:
        sid = actor["session_id"]
        segments: list[dict[str, Any]] = []
        for index, event in enumerate(events_by_session.get(sid, [])):
            original = next((raw for raw in windowed_events if _event_id(raw) == event["id"]), {})
            end_ms = event["time_ms"] + (_duration_from_payload(original) or MAX_INSTANT_SEGMENT_MS)
            tool_id = event.get("tool_use_id")
            if tool_id and event["node_id"] == event_node_by_tool_start.get(str(tool_id)):
                end_event = tool_end_by_id.get(str(tool_id))
                if end_event:
                    end_time = _event_time(end_event) or first_time
                    end_ms = max(event["time_ms"] + MIN_SEGMENT_MS, int((end_time - first_time).total_seconds() * 1000))
            end_ms = min(max(event["time_ms"] + MIN_SEGMENT_MS, end_ms), duration_ms + MAX_INSTANT_SEGMENT_MS)
            segments.append({
                "id": f"segment:{event['id']}",
                "event_id": event["id"],
                "event_node_id": event["node_id"],
                "seq": event["seq"],
                "kind": event["animation_kind"],
                "channel": event["animation_channel"],
                "directive": event["animation_directive"],
                "status": event["status"],
                "priority": event["priority"],
                "semantic_token": event["semantic_token"],
                "coalesce_key": event["coalesce_key"],
                "start_ms": event["time_ms"],
                "end_ms": end_ms,
                "lane_index": actor_order.get(sid, 0),
                "label": event.get("tool_name") or event["canonical_type"],
                "summary": event["summary"],
                "canonical_type": event["canonical_type"],
                "source_event_name": event["source_event_name"],
                "tool_use_id": event.get("tool_use_id"),
                "artifact_refs": event.get("artifact_refs") or [],
                "quality": event["quality"],
            })
        tracks.append({
            "id": f"track:{sid}",
            "actor_id": actor["id"],
            "session_id": sid,
            "provider": actor["provider"],
            "provider_label": actor["provider_label"],
            "lane_index": actor_order.get(sid, 0),
            "segments": segments,
        })

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for actor in actors:
        nodes.append({
            "id": actor["id"],
            "type": "actor",
            "label": actor["title"],
            "provider": actor["provider"],
            "status": actor["status"],
            "layout_hint": {"lane_index": actor_order.get(actor["session_id"], 0), "order": 0},
        })
    for event in normalized_events:
        nodes.append({
            "id": event["node_id"],
            "type": "event",
            "label": event["summary"] or event["canonical_type"],
            "event_id": event["id"],
            "seq": event["seq"],
            "kind": event["animation_kind"],
            "channel": event["animation_channel"],
            "directive": event["animation_directive"],
            "status": event["status"],
            "priority": event["priority"],
            "semantic_token": event["semantic_token"],
            "quality": event["quality"],
            "layout_hint": {
                "lane_index": actor_order.get(event["session_id"], 0),
                "time_ms": event["time_ms"],
            },
        })
        edges.append({
            "id": f"edge:{event['actor_id']}->{event['node_id']}",
            "type": "actor_emits",
            "from": event["actor_id"],
            "to": event["node_id"],
            "event_id": event["id"],
            "seq": event["seq"],
        })
        if event.get("tool_use_id"):
            tool_node = f"tool:{event['tool_use_id']}"
            nodes.append({
                "id": tool_node,
                "type": "tool",
                "label": event.get("tool_name") or str(event.get("tool_use_id")),
                "tool_use_id": event.get("tool_use_id"),
                "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="tool_use_id"),
                "layout_hint": {"lane_index": actor_order.get(event["session_id"], 0), "time_ms": event["time_ms"]},
            })
            edges.append({
                "id": f"edge:{event['node_id']}->{tool_node}",
                "type": "tool_event",
                "from": event["node_id"],
                "to": tool_node,
                "event_id": event["id"],
                "seq": event["seq"],
            })
        for ref in event.get("artifact_refs") or []:
            artifact_node = f"artifact:{ref}"
            nodes.append({
                "id": artifact_node,
                "type": "artifact",
                "label": _compact(ref, 80),
                "artifact_ref": ref,
                "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="artifact_ref"),
                "layout_hint": {"lane_index": actor_order.get(event["session_id"], 0), "time_ms": event["time_ms"]},
            })
            edges.append({
                "id": f"edge:{event['node_id']}->{artifact_node}",
                "type": "artifact_emitted",
                "from": event["node_id"],
                "to": artifact_node,
                "event_id": event["id"],
                "seq": event["seq"],
            })

    seen_nodes: dict[str, dict[str, Any]] = {}
    for node in nodes:
        seen_nodes.setdefault(str(node["id"]), node)
    nodes = list(seen_nodes.values())

    for tool_id, start_node in event_node_by_tool_start.items():
        end_node = event_node_by_tool_end.get(tool_id)
        if end_node:
            edges.append({
                "id": f"edge:{start_node}->{end_node}:tool_lifecycle",
                "type": "tool_lifecycle",
                "from": start_node,
                "to": end_node,
                "tool_use_id": tool_id,
            })
    raw_by_id = {_event_id(event): event for event in windowed_events}
    raw_node_by_id = {event.get("id"): _node_event_id(event) for event in windowed_events if event.get("id")}
    for event in windowed_events:
        parent_id = event.get("parent_id")
        if parent_id and parent_id in raw_node_by_id:
            edges.append({
                "id": f"edge:{raw_node_by_id[parent_id]}->{_node_event_id(event)}:causal_parent",
                "type": "causal_parent",
                "from": raw_node_by_id[parent_id],
                "to": _node_event_id(event),
                "event_id": _event_id(event),
                "seq": int(event.get("seq") or 0),
            })

    pulses = [
        {
            "id": f"pulse:{event['id']}",
            "event_id": event["id"],
            "seq": event["seq"],
            "session_id": event["session_id"],
            "actor_id": event["actor_id"],
            "target_id": (
                f"tool:{event['tool_use_id']}" if event.get("tool_use_id")
                else f"artifact:{event['artifact_refs'][0]}" if event.get("artifact_refs")
                else event["node_id"]
            ),
            "kind": event["animation_kind"],
            "channel": event["animation_channel"],
            "directive": event["animation_directive"],
            "status": event["status"],
            "priority": event["priority"],
            "semantic_token": event["semantic_token"],
            "time_ms": event["time_ms"],
            "intensity": 1.0 if event["status"] in {"fail", "blocked"} else 0.72 if event["animation_kind"] in {"tool", "edit", "validation", "render"} else 0.46,
            "summary": event["summary"],
            "quality": event["quality"],
        }
        for event in normalized_events
    ]

    attention: list[dict[str, Any]] = []
    rank = 0
    for event in normalized_events:
        if event["status"] == "fail":
            rank += 1
            attention.append({
                "id": f"attention:{event['id']}",
                "rank": rank,
                "severity": "block",
                "kind": "event_error",
                "session_id": event["session_id"],
                "actor_id": event["actor_id"],
                "event_id": event["id"],
                "label": "Tool or runtime error",
                "reason": event["summary"] or event["canonical_type"],
                "action": "inspect_event",
            })
        elif event["canonical_type"] == "permission.requested":
            rank += 1
            attention.append({
                "id": f"attention:{event['id']}",
                "rank": rank,
                "severity": "block",
                "kind": "waiting_for_operator",
                "session_id": event["session_id"],
                "actor_id": event["actor_id"],
                "event_id": event["id"],
                "label": "Waiting for operator",
                "reason": event["summary"] or "permission requested",
                "action": "review_permission",
            })
    for actor in actors:
        if actor["heartbeat"] in {"stale", "lost"} and actor["status"] != "done_unreviewed":
            rank += 1
            attention.append({
                "id": f"attention:{actor['id']}:heartbeat",
                "rank": rank,
                "severity": "block" if actor["heartbeat"] == "lost" else "warn",
                "kind": "heartbeat",
                "session_id": actor["session_id"],
                "actor_id": actor["id"],
                "event_id": None,
                "label": "Heartbeat " + actor["heartbeat"],
                "reason": f"last observed {actor.get('lag_ms')}ms ago",
                "action": "inspect_worker",
            })

    file_to_sessions: dict[str, set[str]] = defaultdict(set)
    for actor in actors:
        if actor["status"] in {"done_unreviewed", "stale"}:
            continue
        for file_path in actor.get("touched_files") or []:
            file_to_sessions[file_path].add(actor["session_id"])
    for file_path, sessions in sorted(file_to_sessions.items()):
        if len(sessions) < 2:
            continue
        rank += 1
        attention.append({
            "id": f"attention:file_overlap:{file_path}",
            "rank": rank,
            "severity": "warn",
            "kind": "file_overlap",
            "session_id": None,
            "actor_id": None,
            "event_id": None,
            "label": "Same file touched by multiple agents",
            "reason": file_path,
            "action": "compare_workers",
            "session_ids": sorted(sessions),
        })

    status_counter = Counter(actor["status"] for actor in actors)
    provider_counter = Counter(actor["provider"] for actor in actors)
    kind_counter = Counter(event["animation_kind"] for event in normalized_events)
    channel_counter = Counter(event["animation_channel"] for event in normalized_events)
    runtime_counter = Counter(event["source_runtime"] for event in normalized_events)
    segment_count = sum(len(track.get("segments") or []) for track in tracks)
    spans = _build_spans(tracks)
    flows = _build_flows(events_by_session=events_by_session, edges=edges)
    file_impacts = _build_file_impacts(events=normalized_events, claims_by_path=claims_by_path)
    proof_receipts = _build_proof_receipts(normalized_events)
    counters = _build_counters(
        actors=actors,
        events=normalized_events,
        attention=attention,
        file_impacts=file_impacts,
        proof_receipts=proof_receipts,
        status=status,
        duration_ms=duration_ms,
    )
    notes: list[str] = []
    if int(status.get("gap_count") or 0) > 0:
        notes.append("stream_gap_events_present")
    if int(status.get("dropped_count") or 0) > 0:
        notes.append("store_history_dropped_events")
    if malformed_time_count:
        notes.append("some_events_missing_parseable_time")
    if omitted_infrastructure:
        notes.append("infrastructure_runtime_events_omitted")
    if omitted_window:
        notes.append("events_older_than_window_omitted")

    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso(_utc_now()),
        "authority_boundary": "projection_from_agent_trace_events_status_and_mission_status; raw provider payload remains event.payload authority",
        "filters": {
            "session_id": session_id,
            "source_runtime": source_runtime,
            "since_seq": since_seq,
            "limit": requested_limit,
            "window_ms": requested_window_ms,
            "include_infrastructure": include_infrastructure,
        },
        "window": {
            "start_at": _iso(first_time),
            "end_at": _iso(last_time),
            "duration_ms": duration_ms,
            "anchor_at": _iso(anchor_time),
            "anchor_basis": "caller_now" if now is not None else "latest_event_or_wall_clock",
        },
        "summary": {
            "actor_count": len(actors),
            "event_count": len(normalized_events),
            "track_count": len(tracks),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "span_count": len(spans),
            "flow_count": len(flows),
            "counter_count": len(counters),
            "file_impact_count": len(file_impacts),
            "proof_receipt_count": len(proof_receipts),
            "pulse_count": len(pulses),
            "attention_count": len(attention),
            "providers": dict(provider_counter),
            "actor_status_counts": dict(status_counter),
            "animation_kind_counts": dict(kind_counter),
            "animation_channel_counts": dict(channel_counter),
            "runtime_event_counts": dict(runtime_counter),
        },
        "provider_legend": [
            {"source_runtime": provider, "label": _provider_label(provider)}
            for provider in sorted(set(provider_counter) | set(runtime_counter))
        ],
        "channels": _channel_manifest(normalized_events),
        "cursor": _cursor_payload(
            status=status,
            since_seq=since_seq,
            events=normalized_events,
            requested_limit=requested_limit,
            requested_window_ms=requested_window_ms,
        ),
        "stream_contract": {
            "snapshot_endpoint": "/api/agent-observability/animation",
            "delta_endpoint": "/api/agent-observability/animation/delta",
            "websocket_endpoint": "/ws/agent-observability",
            "identity_fields": ["seq", "id", "session_id", "source_runtime", "canonical_type"],
            "coalesce_key_fields": ["session_id", "animation_channel", "tool_use_id", "tool_name", "touched_files"],
            "frontend_rule": "animate from animation_channel + animation_directive; use raw payload only for inspector drilldown",
            "primitive_families": ["actors", "spans", "flows", "counters", "file_impacts", "proof_receipts", "quality"],
            "raw_authority": "agent_trace_event",
        },
        "backpressure": _backpressure_payload(
            status=status,
            event_count=len(normalized_events),
            duration_ms=duration_ms,
            op_count=(
                len(actors) + segment_count + len(normalized_events) + len(nodes) + len(edges)
                + len(spans) + len(flows) + len(counters) + len(file_impacts) + len(proof_receipts)
                + len(pulses) + len(attention)
            ),
        ),
        "actors": actors,
        "tracks": tracks,
        "events": normalized_events,
        "nodes": nodes,
        "edges": edges,
        "spans": spans,
        "flows": flows,
        "counters": counters,
        "file_impacts": file_impacts,
        "proof_receipts": proof_receipts,
        "pulses": pulses,
        "attention": attention,
        "data_quality": {
            "raw_event_count": raw_event_count,
            "scoped_event_count": len(scoped_events),
            "window_event_count": len(windowed_events),
            "omitted_scope_count": omitted_scope,
            "omitted_window_count": omitted_window,
            "omitted_infrastructure_count": omitted_infrastructure,
            "malformed_time_count": malformed_time_count,
            "trace_seq": status.get("seq"),
            "history_size": status.get("history_size"),
            "max_history": status.get("max_history"),
            "dropped_count": status.get("dropped_count"),
            "gap_count": status.get("gap_count"),
            "persistence": _safe_mapping(status.get("persistence")),
            "snapshot_required": _snapshot_required(status, since_seq, allow_initial_delta=True),
            "projection_notes": notes,
        },
        "raw_drilldown_refs": {
            "endpoint_status": "/api/agent-observability/status",
            "endpoint_events": "/api/agent-observability/events",
            "endpoint_mission_status": "/api/agent-observability/mission-status",
            "endpoint_websocket": "/ws/agent-observability",
            "trace_path": status.get("trace_path"),
        },
    }


def build_agent_observability_animation_delta(
    *,
    events: Sequence[Mapping[str, Any]],
    status: Mapping[str, Any],
    mission_status: Mapping[str, Any] | None = None,
    now: datetime | None = None,
    window_ms: int = DEFAULT_WINDOW_MS,
    include_infrastructure: bool = False,
    session_id: str | None = None,
    source_runtime: str | None = None,
    since_seq: int = 0,
    limit: int = DEFAULT_DELTA_LIMIT,
    max_ops: int = DEFAULT_MAX_DELTA_OPS,
) -> dict[str, Any]:
    """Compile only the live animation operations needed after ``since_seq``.

    The scene endpoint is the stable snapshot. This endpoint is the efficient
    high-frequency contract: bounded ops, replay cursor, coalescing keys, and
    explicit backpressure/snapshot hints.
    """
    requested_limit = max(1, min(int(limit or DEFAULT_DELTA_LIMIT), 1000))
    requested_max_ops = max(50, min(int(max_ops or DEFAULT_MAX_DELTA_OPS), 2000))
    scene = build_agent_observability_animation_scene(
        events=events,
        status=status,
        mission_status=mission_status,
        now=now,
        window_ms=window_ms,
        include_infrastructure=include_infrastructure,
        session_id=session_id,
        source_runtime=source_runtime,
        since_seq=since_seq,
        limit=requested_limit,
    )

    ops: list[dict[str, Any]] = []
    dropped_ops = 0

    def push(op: dict[str, Any]) -> None:
        nonlocal dropped_ops
        if len(ops) >= requested_max_ops:
            dropped_ops += 1
            return
        ops.append(op)

    for actor in scene["actors"]:
        push({
            "op": "actor_upsert",
            "id": actor["id"],
            "session_id": actor["session_id"],
            "seq": scene["cursor"]["next_since_seq"],
            "quality": actor.get("quality"),
            "payload": actor,
        })

    for track in scene["tracks"]:
        push({
            "op": "track_upsert",
            "id": track["id"],
            "session_id": track["session_id"],
            "seq": scene["cursor"]["next_since_seq"],
            "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="scene_reducer"),
            "payload": {key: value for key, value in track.items() if key != "segments"},
        })
        for segment in track.get("segments") or []:
            push({
                "op": "segment_upsert",
                "id": segment["id"],
                "session_id": track["session_id"],
                "event_id": segment["event_id"],
                "seq": segment["seq"],
                "channel": segment.get("channel"),
                "directive": segment.get("directive"),
                "coalesce_key": segment.get("coalesce_key"),
                "quality": segment.get("quality"),
                "payload": segment,
            })

    for event in scene["events"]:
        push({
            "op": "event_append",
            "id": event["id"],
            "session_id": event["session_id"],
            "event_id": event["id"],
            "seq": event["seq"],
            "channel": event.get("animation_channel"),
            "directive": event.get("animation_directive"),
            "priority": event.get("priority"),
            "coalesce_key": event.get("coalesce_key"),
            "quality": event.get("quality"),
            "payload": event,
        })

    for node in scene["nodes"]:
        push({
            "op": "node_upsert",
            "id": node["id"],
            "event_id": node.get("event_id"),
            "seq": node.get("seq"),
            "quality": node.get("quality") or _quality_envelope(authority="projection", confidence="derived_strong", source="scene_reducer"),
            "payload": node,
        })

    for edge in scene["edges"]:
        push({
            "op": "edge_upsert",
            "id": edge["id"],
            "event_id": edge.get("event_id"),
            "seq": edge.get("seq"),
            "quality": edge.get("quality") or _quality_envelope(authority="projection", confidence="derived_strong", source="scene_reducer"),
            "payload": edge,
        })

    for span in scene["spans"]:
        push({
            "op": "span_upsert",
            "id": span["id"],
            "session_id": span.get("session_id"),
            "event_id": span.get("event_id"),
            "seq": span.get("seq"),
            "channel": span.get("channel"),
            "coalesce_key": span.get("coalesce_key"),
            "quality": span.get("quality"),
            "payload": span,
        })

    for flow in scene["flows"]:
        push({
            "op": "flow_upsert",
            "id": flow["id"],
            "session_id": flow.get("session_id"),
            "event_id": flow.get("event_id") or flow.get("to_event_id"),
            "seq": flow.get("seq"),
            "quality": flow.get("quality"),
            "payload": flow,
        })

    for counter in scene["counters"]:
        push({
            "op": "counter_update",
            "id": counter["id"],
            "seq": scene["cursor"]["next_since_seq"],
            "channel": counter.get("channel"),
            "quality": counter.get("quality"),
            "payload": counter,
        })

    for impact in scene["file_impacts"]:
        push({
            "op": "file_impact_upsert",
            "id": impact["id"],
            "session_id": impact.get("session_id"),
            "event_id": impact.get("event_id"),
            "seq": impact.get("seq"),
            "channel": impact.get("channel"),
            "quality": impact.get("quality"),
            "payload": impact,
        })

    for receipt in scene["proof_receipts"]:
        push({
            "op": "proof_receipt_upsert",
            "id": receipt["id"],
            "session_id": receipt.get("session_id"),
            "event_id": receipt.get("event_id"),
            "seq": receipt.get("seq"),
            "quality": receipt.get("quality"),
            "payload": receipt,
        })

    for pulse in scene["pulses"]:
        push({
            "op": "pulse_emit",
            "id": pulse["id"],
            "session_id": pulse.get("session_id"),
            "event_id": pulse["event_id"],
            "seq": pulse["seq"],
            "channel": pulse.get("channel"),
            "directive": pulse.get("directive"),
            "priority": pulse.get("priority"),
            "quality": pulse.get("quality") or _quality_envelope(authority="canonical_event", source="agent_trace_event"),
            "payload": pulse,
        })

    for item in scene["attention"]:
        push({
            "op": "attention_upsert",
            "id": item["id"],
            "session_id": item.get("session_id"),
            "event_id": item.get("event_id"),
            "quality": item.get("quality") or _quality_envelope(authority="projection", confidence="derived_strong", source="attention_reducer"),
            "payload": item,
        })

    push({
        "op": "quality_update",
        "id": "data_quality",
        "seq": scene["cursor"]["next_since_seq"],
        "payload": scene["data_quality"],
        "quality": _quality_envelope(authority="projection", confidence="derived_strong", source="scene_reducer"),
    })

    snapshot_required = _snapshot_required(status, since_seq) or dropped_ops > 0
    backpressure = _backpressure_payload(
        status=status,
        event_count=len(scene["events"]),
        duration_ms=int(scene["window"]["duration_ms"]),
        op_count=len(ops),
        dropped_op_count=dropped_ops,
        max_delta_ops=requested_max_ops,
    )

    return {
        "kind": DELTA_KIND,
        "schema_version": DELTA_SCHEMA_VERSION,
        "generated_at": _iso(_utc_now()),
        "authority_boundary": scene["authority_boundary"],
        "filters": scene["filters"] | {"max_ops": requested_max_ops},
        "cursor": scene["cursor"],
        "snapshot_required": snapshot_required,
        "snapshot_reason": (
            "initial_or_expired_cursor"
            if since_seq <= 0 or since_seq < scene["cursor"]["earliest_available_seq"] - 1
            else "trace_gap_or_dropped_events"
            if _status_int(status, "dropped_count") > 0 or _status_int(status, "gap_count") > 0
            else "delta_ops_truncated"
            if dropped_ops
            else None
        ),
        "op_count": len(ops),
        "dropped_op_count": dropped_ops,
        "ops": ops,
        "channels": scene["channels"],
        "backpressure": backpressure,
        "data_quality": scene["data_quality"] | {
            "snapshot_required": snapshot_required,
            "delta_event_count": len(scene["events"]),
            "delta_op_count": len(ops),
            "dropped_delta_op_count": dropped_ops,
        },
        "raw_drilldown_refs": scene["raw_drilldown_refs"],
    }
