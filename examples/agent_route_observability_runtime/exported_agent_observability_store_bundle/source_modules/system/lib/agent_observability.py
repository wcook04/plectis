"""
Typed agent-observability substrate.

This module is intentionally Python-native and append-only. Provider payloads
remain attached as evidence, but consumers read the canonical event fields.

- When-needed: Open when you need to emit, ingest, or replay agent trace events and observability evidence for Claude hooks, Codex rollouts, or runtime claims.
- Escalates-to: system/lib/agent_execution_trace.py; system/lib/agent_providers.py; system/server/tests/test_agent_observability.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import queue
import threading
import time
import hashlib
import errno
import gzip
import os
import re
import shutil
import subprocess
from collections import Counter, deque
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional


SCHEMA_VERSION = "1.0.0"
API_REVISION = "agent_observability_backend_v2"
DEFAULT_TRACE_RELATIVE_PATH = Path("state/observability/agent_trace/events.jsonl")
BACKGROUND_DOWNSHIFT_RELATIVE_PATH = Path("state/performance/background_loop_downshift.json")
DEFAULT_JSONL_TAIL_READ_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_EVENT_LINE_BYTES = 64 * 1024
DEFAULT_MAX_PAYLOAD_VALUE_BYTES = 16 * 1024
DEFAULT_MAX_PAYLOAD_CONTAINER_ITEMS = 80
DEFAULT_MAX_TRACE_FILE_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_TRACE_ARCHIVES = 4
TRACE_RETENTION_STATUS_SCHEMA_VERSION = "agent_trace_retention_status_v0"
ACTIVITY_CANONICAL_TYPES = {
    "turn.prompt",
    "intent.observed",
    "plan.observed",
    "message.user",
    "message.assistant",
    "message.thinking",
    "tool.proposed",
    "tool.started",
    "tool.completed",
    "subagent.started",
    "subagent.completed",
    "runtime.error",
}
SYSTEM_CONTENT_PREFIXES = (
    "<system-reminder>",
    "<system_reminder>",
    "<environment_context>",
    "# Context from my IDE setup:",
)


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


MAX_EVENT_LINE_BYTES = _env_int(
    "AIW_AGENT_TRACE_MAX_EVENT_LINE_BYTES",
    DEFAULT_MAX_EVENT_LINE_BYTES,
    minimum=16 * 1024,
)
MAX_PAYLOAD_VALUE_BYTES = _env_int(
    "AIW_AGENT_TRACE_MAX_PAYLOAD_VALUE_BYTES",
    DEFAULT_MAX_PAYLOAD_VALUE_BYTES,
    minimum=4 * 1024,
)
MAX_PAYLOAD_CONTAINER_ITEMS = _env_int(
    "AIW_AGENT_TRACE_MAX_PAYLOAD_CONTAINER_ITEMS",
    DEFAULT_MAX_PAYLOAD_CONTAINER_ITEMS,
    minimum=8,
)
MAX_TRACE_FILE_BYTES = _env_int(
    "AIW_AGENT_TRACE_MAX_FILE_BYTES",
    DEFAULT_MAX_TRACE_FILE_BYTES,
    minimum=1 * 1024 * 1024,
)
MAX_TRACE_ARCHIVES = _env_int(
    "AIW_AGENT_TRACE_MAX_ARCHIVES",
    DEFAULT_MAX_TRACE_ARCHIVES,
    minimum=1,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _human_bytes(num: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(max(num, 0))
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num}B"


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _compact_json_bytes(value: Any, *, sort_keys: bool = False) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=sort_keys).encode("utf-8")


def _large_value_ref(value: Any, *, value_type: str, original_bytes: int) -> dict[str, Any]:
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    return {
        "compacted_payload_value": True,
        "value_type": value_type,
        "original_bytes": original_bytes,
        "sha256": hashlib.sha256(str(raw).encode("utf-8")).hexdigest(),
    }


def _compact_payload_value(value: Any, *, depth: int = 0) -> Any:
    if isinstance(value, str):
        original_bytes = len(value.encode("utf-8"))
        if original_bytes > MAX_PAYLOAD_VALUE_BYTES:
            return _large_value_ref(value, value_type="str", original_bytes=original_bytes)
        return value
    if isinstance(value, Mapping):
        if depth >= 8:
            original_bytes = len(_compact_json_bytes(value, sort_keys=True))
            return _large_value_ref(value, value_type="mapping", original_bytes=original_bytes)
        compacted: dict[str, Any] = {}
        omitted_keys: list[str] = []
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_PAYLOAD_CONTAINER_ITEMS:
                omitted_keys.append(str(key))
                continue
            compacted[str(key)] = _compact_payload_value(item, depth=depth + 1)
        if omitted_keys:
            compacted["__compaction_omitted_key_count"] = len(omitted_keys)
            compacted["__compaction_omitted_key_preview"] = omitted_keys[:20]
        return compacted
    if isinstance(value, list):
        if depth >= 8:
            original_bytes = len(_compact_json_bytes(value, sort_keys=True))
            return _large_value_ref(value, value_type="list", original_bytes=original_bytes)
        compacted_items = [
            _compact_payload_value(item, depth=depth + 1)
            for item in value[:MAX_PAYLOAD_CONTAINER_ITEMS]
        ]
        if len(value) > MAX_PAYLOAD_CONTAINER_ITEMS:
            compacted_items.append({
                "compacted_payload_value": True,
                "value_type": "list_tail",
                "omitted_item_count": len(value) - MAX_PAYLOAD_CONTAINER_ITEMS,
            })
        return compacted_items
    return value


def _payload_skeleton(payload: Mapping[str, Any]) -> dict[str, Any]:
    keep_keys = (
        "session_id",
        "thread_id",
        "conversation_id",
        "trace_id",
        "turn_id",
        "tool_use_id",
        "call_id",
        "tool_name",
        "type",
        "timestamp",
        "cwd",
        "transcript_path",
        "rollout_path",
    )
    skeleton = {
        key: _compact_payload_value(payload[key])
        for key in keep_keys
        if key in payload
    }
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, Mapping):
        skeleton["tool_input"] = {
            key: _compact_payload_value(value)
            for key, value in tool_input.items()
            if key in {"file_path", "path", "command", "description", "pattern", "query"}
        }
    return skeleton


def _compact_event_if_oversized(event: dict[str, Any]) -> dict[str, Any]:
    original_bytes = len(_compact_json_bytes(event))
    if original_bytes <= MAX_EVENT_LINE_BYTES:
        return event

    original_payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    payload_bytes = len(_compact_json_bytes(original_payload, sort_keys=True))
    payload_hash = hashlib.sha256(_compact_json_bytes(original_payload, sort_keys=True)).hexdigest()
    compacted = dict(event)
    compacted["payload"] = _compact_payload_value(original_payload)
    compacted["payload_compaction"] = {
        "schema_version": "agent_trace_payload_compaction_v1",
        "strategy": "compact_large_values",
        "trigger": "event_line_bytes",
        "original_line_bytes": original_bytes,
        "original_payload_bytes": payload_bytes,
        "original_payload_sha256": payload_hash,
        "max_event_line_bytes": MAX_EVENT_LINE_BYTES,
    }
    compacted_bytes = len(_compact_json_bytes(compacted))
    if compacted_bytes <= MAX_EVENT_LINE_BYTES:
        compacted["payload_compaction"]["compacted_line_bytes"] = compacted_bytes
        return compacted

    compacted["payload"] = {
        **_payload_skeleton(original_payload),
        "compacted_payload_value": True,
        "value_type": "payload",
        "original_key_count": len(original_payload),
        "original_keys_preview": sorted(str(key) for key in original_payload.keys())[:80],
    }
    compacted["payload_compaction"]["strategy"] = "payload_skeleton"
    compacted["payload_compaction"]["compacted_line_bytes"] = len(_compact_json_bytes(compacted))
    return compacted


def _read_jsonl_tail_lines(
    path: Path,
    *,
    limit: int,
    max_bytes: int = DEFAULT_JSONL_TAIL_READ_BYTES,
) -> list[str]:
    """Read a bounded tail of JSONL lines without loading historical archives."""
    limit = max(1, int(limit or 1))
    max_bytes = max(1024, int(max_bytes or DEFAULT_JSONL_TAIL_READ_BYTES))
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            file_size = handle.tell()
            if file_size <= 0:
                return []

            remaining_budget = min(max_bytes, file_size)
            position = file_size
            chunks: deque[bytes] = deque()
            newline_count = 0
            chunk_size = 64 * 1024

            while position > 0 and remaining_budget > 0 and newline_count <= limit:
                read_size = min(chunk_size, position, remaining_budget)
                position -= read_size
                handle.seek(position)
                chunk = handle.read(read_size)
                chunks.appendleft(chunk)
                newline_count += chunk.count(b"\n")
                remaining_budget -= read_size
    except OSError:
        return []

    text = b"".join(chunks).decode("utf-8", errors="replace")
    lines = text.splitlines()
    if position > 0 and lines:
        # The first line is partial when the bounded read started mid-file.
        lines = lines[1:]
    return [line for line in lines if line.strip()][-limit:]


def _safe_stat_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _safe_mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _relpath(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except (OSError, ValueError):
        return str(path)


def build_agent_trace_retention_status(
    repo_root: Path,
    *,
    trace_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Return a cheap, read-only status packet for the live AgentTraceStore log."""
    repo_root = Path(repo_root)
    path = trace_path or repo_root / DEFAULT_TRACE_RELATIVE_PATH
    archive_dir = path.parent / "archive"
    active_bytes = _safe_stat_size(path)
    archives: list[Path] = []
    archive_rows: list[dict[str, Any]] = []
    if archive_dir.exists():
        archives = sorted(
            archive_dir.glob(f"{path.stem}_*.jsonl.gz"),
            key=lambda item: _safe_mtime_iso(item) or "",
            reverse=True,
        )
        for archive in archives:
            archive_bytes = _safe_stat_size(archive)
            archive_rows.append(
                {
                    "path": _relpath(archive, repo_root=repo_root),
                    "bytes": archive_bytes,
                    "human_size": _human_bytes(archive_bytes),
                    "mtime": _safe_mtime_iso(archive),
                }
            )

    archive_bytes_total = sum(int(row["bytes"]) for row in archive_rows)
    bytes_until_rotation = max(0, MAX_TRACE_FILE_BYTES - active_bytes)
    if active_bytes >= MAX_TRACE_FILE_BYTES:
        status = "rotation_due_on_next_append"
    elif len(archives) > MAX_TRACE_ARCHIVES:
        status = "archive_count_over_policy"
    elif path.exists():
        status = "within_writer_rotation_budget"
    else:
        status = "trace_file_missing_waiting_for_writer"

    return {
        "kind": "agent_trace_retention_status",
        "schema_version": TRACE_RETENTION_STATUS_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "status": status,
        "owner_surface": "system/lib/agent_observability.py::AgentTraceStore._rotate_trace_if_needed_locked",
        "privacy_boundary": (
            "Retention status uses file metadata only; it does not read trace event bodies or provider archives."
        ),
        "active_file": {
            "path": _relpath(path, repo_root=repo_root),
            "exists": path.exists(),
            "bytes": active_bytes,
            "human_size": _human_bytes(active_bytes),
            "mtime": _safe_mtime_iso(path),
            "max_trace_file_bytes": MAX_TRACE_FILE_BYTES,
            "max_trace_file_human": _human_bytes(MAX_TRACE_FILE_BYTES),
            "bytes_until_rotation": bytes_until_rotation,
            "bytes_until_rotation_human": _human_bytes(bytes_until_rotation),
            "rotation_trigger": "before_next_append_when_active_file_bytes_ge_max_trace_file_bytes",
        },
        "archives": {
            "directory": _relpath(archive_dir, repo_root=repo_root),
            "exists": archive_dir.exists(),
            "count": len(archives),
            "max_trace_archives": MAX_TRACE_ARCHIVES,
            "bytes": archive_bytes_total,
            "human_size": _human_bytes(archive_bytes_total),
            "rows": archive_rows[:MAX_TRACE_ARCHIVES],
            "omitted_row_count": max(0, len(archive_rows) - MAX_TRACE_ARCHIVES),
        },
        "policy": {
            "max_trace_file_bytes_env": "AIW_AGENT_TRACE_MAX_FILE_BYTES",
            "max_trace_archives_env": "AIW_AGENT_TRACE_MAX_ARCHIVES",
            "rotation_mode": "gzip_archive_then_unlink_active_file_before_append",
            "archive_pruning_mode": "keep_newest_archives_by_mtime",
            "manual_delete_allowed": False,
        },
        "next_actions": {
            "status_command": "./repo-python -m tools.meta.observability.agent_trace_retention --json",
            "writer_liveness_check": f"lsof -- {_relpath(path, repo_root=repo_root)}",
            "host_pressure_check": (
                "./repo-python kernel.py --host-pressure --host-pressure-no-processes "
                "--host-pressure-compact --host-pressure-event-limit 500"
            ),
            "storage_doctor_card": "./repo-python -m tools.meta.storage_doctor scan --top 12 --format card",
            "mutation_policy": "Do not delete the live trace log; adjust writer retention knobs or let the writer rotate.",
        },
    }


def _compact_summary(text: object, *, limit: int = 220) -> Optional[str]:
    raw = " ".join(str(text or "").strip().split())
    if not raw:
        return None
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 3)].rstrip() + "..."


def _looks_system_injected(text: str) -> bool:
    stripped = str(text or "").strip()
    return not stripped or any(stripped.startswith(prefix) for prefix in SYSTEM_CONTENT_PREFIXES)


def _flatten_tool_result_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item or ""))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _tool_input_summary(tool_name: str, tool_input: Mapping[str, Any] | None) -> str:
    tool_input = tool_input if isinstance(tool_input, Mapping) else {}
    if tool_name in {"Bash", "Shell"}:
        return str(tool_input.get("description") or tool_input.get("command") or tool_name)
    if tool_name in {"Read", "Edit", "Write", "MultiEdit"}:
        return str(tool_input.get("file_path") or tool_input.get("path") or tool_name)
    if tool_name in {"Glob", "Grep", "rg"}:
        return str(tool_input.get("pattern") or tool_input.get("query") or tool_input.get("path") or tool_name)
    if tool_name in {"Agent", "Task"}:
        return str(tool_input.get("description") or tool_input.get("subagent_type") or tool_name)
    if tool_name.startswith("mcp__"):
        return tool_name.replace("mcp__", "", 1)
    return tool_name


def _session_title_from_text(text: object) -> Optional[str]:
    summary = _compact_summary(text, limit=96)
    if not summary:
        return None
    summary = re.sub(r"^#+\s*", "", summary).strip()
    return summary[:1].upper() + summary[1:] if summary else None


def _event_touched_files(event: Mapping[str, Any]) -> list[str]:
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    candidates: list[Any] = []
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), Mapping) else {}
    candidates.extend(
        [
            tool_input.get("file_path"),
            tool_input.get("path"),
            tool_input.get("notebook_path"),
            tool_input.get("target_notebook"),
            tool_input.get("target_file"),
        ]
    )
    for key in ("files", "paths", "file_paths"):
        value = tool_input.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    candidates.extend(event.get("artifact_refs") if isinstance(event.get("artifact_refs"), list) else [])

    paths: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        text = candidate.strip()
        if text.startswith("http://") or text.startswith("https://"):
            continue
        if text not in paths:
            paths.append(text)
    return paths[:12]


CLAUDE_CANONICAL_TYPES = {
    "SessionStart": "session.start",
    "Setup": "session.start",
    "InstructionsLoaded": "context.loaded",
    "UserPromptSubmit": "turn.prompt",
    "UserPromptExpansion": "turn.prompt",
    "PreToolUse": "tool.proposed",
    "PostToolUse": "tool.completed",
    "PostToolUseFailure": "runtime.error",
    "PostToolBatch": "tool.batch.completed",
    "PermissionRequest": "permission.requested",
    "Notification": "runtime.waiting",
    "SubagentStart": "subagent.started",
    "SubagentStop": "subagent.completed",
    "TaskCreated": "subagent.started",
    "PreCompact": "compaction.started",
    "PostCompact": "compaction.completed",
    "Stop": "turn.completed",
    "StopFailure": "runtime.error",
    "SessionEnd": "session.end",
}

CODEX_ROLLOUT_CANONICAL_TYPES = {
    "session_meta": "session.start",
    "turn_context": "context.loaded",
    "task_started": "turn.start",
    "task_complete": "turn.completed",
    "turn_aborted": "runtime.error",
    "user_message": "turn.prompt",
    "agent_message": "intent.observed",
    "agent_reasoning": "plan.observed",
    "function_call": "tool.proposed",
    "function_call_output": "tool.completed",
    "exec_command_end": "tool.completed",
    "token_count": "usage.observed",
}


# Codex rollout filenames embed the session UUID after the timestamp:
# rollout-2026-05-09T23-49-06-019e0eee-1c35-71a0-9e79-33bbf740fa33.jsonl
# This regex matches a standard 8-4-4-4-12 UUID anchored at the file stem
# tail so we can recover the per-session id even on records that don't
# carry one in their payload (everything after the initial session_meta).
_CODEX_ROLLOUT_UUID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def _codex_session_id_from_record(
    record: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    rollout_path: Optional[str],
) -> Optional[str]:
    """Resolve a stable per-session id for a Codex rollout record.

    Codex rollouts emit one ``session_meta`` line carrying the UUID at
    ``payload.id`` and then a stream of ``response_item`` / ``event_msg`` /
    ``turn_context`` records that carry only ``turn_id``. The same UUID is
    embedded in the rollout filename, so we resolve in priority order:

      1. ``payload.session_id`` / ``thread_id`` / ``conversation_id``
         (legacy paths, preserved for upstream compatibility).
      2. ``payload.id`` when the record is a ``session_meta``
         (Codex's actual canonical session-id field).
      3. UUID parsed from the ``rollout_path`` filename (works for every
         record after ``session_meta`` since each rollout file is one
         session).

    Returns ``None`` only when no resolution succeeds; the caller then
    falls back to whatever default the emitter uses.
    """
    for key in ("session_id", "thread_id", "conversation_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    payload_type = payload.get("type") or record.get("type")
    if payload_type == "session_meta":
        candidate = payload.get("id")
        if isinstance(candidate, str) and candidate:
            return candidate
    if rollout_path:
        match = _CODEX_ROLLOUT_UUID_RE.search(rollout_path)
        if match:
            return match.group(1).lower()
    return None


@dataclass(frozen=True)
class AgentEvent:
    id: str
    seq: int
    schema: str
    trace_id: str
    source_runtime: str
    source_event_name: str
    canonical_type: str
    session_id: str
    observed_at: str
    payload: dict[str, Any]
    parent_id: Optional[str] = None
    turn_id: Optional[str] = None
    tool_use_id: Optional[str] = None
    subagent_id: Optional[str] = None
    cwd: Optional[str] = None
    transcript_path: Optional[str] = None
    artifact_refs: list[str] = field(default_factory=list)
    occurred_at: Optional[str] = None
    summary: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


class AgentTraceStore:
    """Thread-safe append-only trace materializer with WebSocket-ready history."""

    def __init__(
        self,
        repo_root: Path,
        *,
        trace_path: Optional[Path] = None,
        max_history: int = 2000,
        queue_size: int = 5000,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.trace_path = trace_path or self.repo_root / DEFAULT_TRACE_RELATIVE_PATH
        self.max_history = max_history
        self._lock = threading.RLock()
        self._history: deque[dict[str, Any]] = deque(maxlen=max_history)
        self._telemetry_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=queue_size)
        self._seq = 0
        self._dropped_count = 0
        self._gap_count = 0
        self._persist_drop_count = 0
        self._persist_error_count = 0
        self._last_persistence_error: Optional[str] = None
        self._persistence_disabled_until_s = 0.0
        self._source_status: dict[str, dict[str, Any]] = {}
        self._active_sessions: dict[str, dict[str, Any]] = {}
        self._canonical_counts: Counter[str] = Counter()
        self._source_counts: Counter[str] = Counter()
        self._sampler_state: dict[str, Any] = {
            "running": False,
            "poll_count": 0,
            "last_poll_at": None,
            "last_error": None,
            "poll_interval_s": None,
        }
        self._load_existing_tail()

    def _load_existing_tail(self) -> None:
        if not self.trace_path.exists():
            return
        lines = _read_jsonl_tail_lines(self.trace_path, limit=self.max_history)
        for line in lines[-self.max_history :]:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            seq = int(event.get("seq") or 0)
            self._seq = max(self._seq, seq)
            self._history.append(event)
            self._index_event_locked(event)

    def _index_event_locked(self, event: Mapping[str, Any]) -> None:
        canonical_type = str(event.get("canonical_type") or "unknown")
        source_runtime = str(event.get("source_runtime") or "unknown")
        session_id = str(event.get("session_id") or "unknown")
        observed_at = str(event.get("observed_at") or event.get("timestamp") or "")
        self._canonical_counts[canonical_type] += 1
        self._source_counts[source_runtime] += 1
        self._source_status[source_runtime] = {
            "source_runtime": source_runtime,
            "last_observed_at": observed_at or None,
            "last_canonical_type": canonical_type,
            "event_count": self._source_counts[source_runtime],
        }
        existing = self._active_sessions.get(session_id, {"session_id": session_id, "activity_count": 0, "touched_files": []})
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        touched_files = list(existing.get("touched_files") or [])
        for path in _event_touched_files(event):
            if path not in touched_files:
                touched_files.append(path)
        if len(touched_files) > 12:
            touched_files = touched_files[-12:]
        title = existing.get("title")
        payload_title = _session_title_from_text(payload.get("title") or payload.get("session_title"))
        if payload_title and (canonical_type == "session.discovered" or not title):
            title = payload_title
        if not title and canonical_type in {"message.user", "turn.prompt"}:
            title = _session_title_from_text(payload.get("content") or event.get("summary"))
        if not title and canonical_type in {"message.assistant", "intent.observed"}:
            title = _session_title_from_text(event.get("summary"))
        is_activity = canonical_type in ACTIVITY_CANONICAL_TYPES
        activity_count = int(existing.get("activity_count") or 0) + (1 if is_activity else 0)
        self._active_sessions[session_id] = {
            **existing,
            "session_id": session_id,
            "trace_id": event.get("trace_id") or existing.get("trace_id"),
            "source_runtime": source_runtime,
            "last_observed_at": observed_at or existing.get("last_observed_at") or None,
            "last_canonical_type": canonical_type,
            "cwd": event.get("cwd") or existing.get("cwd"),
            "transcript_path": event.get("transcript_path") or existing.get("transcript_path"),
            "summary": event.get("summary") or existing.get("summary"),
            "title": title,
            "activity_count": activity_count,
            "last_activity_at": observed_at if is_activity else existing.get("last_activity_at"),
            "current_activity": event.get("summary") if is_activity else existing.get("current_activity"),
            "touched_files": touched_files,
        }
        if canonical_type == "stream.gap":
            self._gap_count += 1

    def _rotate_trace_if_needed_locked(self) -> None:
        if MAX_TRACE_FILE_BYTES <= 0:
            return
        try:
            current_size = self.trace_path.stat().st_size
        except OSError:
            return
        if current_size < MAX_TRACE_FILE_BYTES:
            return

        archive_dir = self.trace_path.parent / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        archive_path = archive_dir / f"{self.trace_path.stem}_{stamp}_{current_size}.jsonl.gz"
        tmp_path = archive_path.with_suffix(archive_path.suffix + ".tmp")
        try:
            with self.trace_path.open("rb") as src, gzip.open(tmp_path, "wb", compresslevel=3) as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            tmp_path.replace(archive_path)
            self.trace_path.unlink()
            archives = sorted(
                archive_dir.glob(f"{self.trace_path.stem}_*.jsonl.gz"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for old_archive in archives[MAX_TRACE_ARCHIVES:]:
                old_archive.unlink(missing_ok=True)
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise exc

    def _write_event_locked(self, event: Mapping[str, Any]) -> bool:
        now = time.monotonic()
        if self._persistence_disabled_until_s > now:
            self._persist_drop_count += 1
            return False
        try:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            self._rotate_trace_if_needed_locked()
            with self.trace_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            self._last_persistence_error = None
            self._persistence_disabled_until_s = 0.0
            return True
        except OSError as exc:
            self._persist_error_count += 1
            self._persist_drop_count += 1
            self._last_persistence_error = f"{type(exc).__name__}: {exc}"
            backoff_s = 60.0 if exc.errno in {errno.ENOSPC, errno.EDQUOT} else 5.0
            self._persistence_disabled_until_s = now + backoff_s
            return False

    def emit(
        self,
        *,
        source_runtime: str,
        source_event_name: str,
        canonical_type: str,
        payload: Mapping[str, Any] | None = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        tool_use_id: Optional[str] = None,
        subagent_id: Optional[str] = None,
        cwd: Optional[str] = None,
        transcript_path: Optional[str] = None,
        artifact_refs: Optional[list[str]] = None,
        occurred_at: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> dict[str, Any]:
        safe_payload = _json_safe(dict(payload or {}))
        observed_at = _now_iso()
        resolved_session_id = (
            str(session_id or safe_payload.get("session_id") or safe_payload.get("thread_id") or "").strip()
            or "unknown"
        )
        resolved_trace_id = (
            str(trace_id or safe_payload.get("trace_id") or resolved_session_id).strip()
            or resolved_session_id
        )

        with self._lock:
            self._seq += 1
            event = AgentEvent(
                id=f"agent-event-{self._seq:09d}",
                seq=self._seq,
                schema=SCHEMA_VERSION,
                trace_id=resolved_trace_id,
                parent_id=parent_id,
                source_runtime=str(source_runtime or "unknown"),
                source_event_name=str(source_event_name or "unknown"),
                canonical_type=str(canonical_type or "runtime.event"),
                session_id=resolved_session_id,
                turn_id=turn_id or safe_payload.get("turn_id"),
                tool_use_id=tool_use_id or safe_payload.get("tool_use_id") or safe_payload.get("call_id"),
                subagent_id=subagent_id or safe_payload.get("subagent_id") or safe_payload.get("agent_id"),
                cwd=cwd or safe_payload.get("cwd"),
                transcript_path=transcript_path or safe_payload.get("transcript_path"),
                artifact_refs=list(artifact_refs or []),
                observed_at=observed_at,
                occurred_at=occurred_at or safe_payload.get("timestamp"),
                summary=summary,
                payload=safe_payload,
            ).to_dict()
            event = _compact_event_if_oversized(event)
            self._history.append(event)
            self._index_event_locked(event)
            self._write_event_locked(event)

        try:
            self._telemetry_queue.put_nowait(event)
        except queue.Full:
            with self._lock:
                self._dropped_count += 1
        return event

    def emit_gap(self, *, source_runtime: str, reason: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self.emit(
            source_runtime=source_runtime,
            source_event_name="stream_gap",
            canonical_type="stream.gap",
            payload={"reason": reason, **dict(payload or {})},
            summary=f"gap: {reason}",
        )

    def ingest_claude_hook(self, action: str, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        event_name = str((payload or {}).get("hook_event_name") or action or "ClaudeHook")
        canonical_type = CLAUDE_CANONICAL_TYPES.get(event_name, "runtime.event")
        tool_name = (payload or {}).get("tool_name")
        summary = _compact_summary(tool_name or (payload or {}).get("prompt") or event_name)
        return self.emit(
            source_runtime="claude_code",
            source_event_name=event_name,
            canonical_type=canonical_type,
            payload=payload or {},
            session_id=(payload or {}).get("session_id"),
            trace_id=(payload or {}).get("session_id"),
            cwd=(payload or {}).get("cwd"),
            transcript_path=(payload or {}).get("transcript_path"),
            summary=summary,
        )

    def ingest_codex_rollout_record(
        self,
        record: Mapping[str, Any],
        *,
        rollout_path: Optional[str] = None,
    ) -> dict[str, Any]:
        payload = record.get("payload") if isinstance(record.get("payload"), Mapping) else record
        payload = dict(payload or {})
        source_event_name = str(payload.get("type") or record.get("type") or "codex_rollout")
        canonical_type = CODEX_ROLLOUT_CANONICAL_TYPES.get(source_event_name, "runtime.event")
        artifact_refs = [rollout_path] if rollout_path else []
        summary = _compact_summary(
            payload.get("last_agent_message")
            or payload.get("message")
            or payload.get("name")
            or payload.get("parsed_cmd")
            or source_event_name
        )
        codex_session_id = _codex_session_id_from_record(
            record, payload, rollout_path=rollout_path,
        )
        return self.emit(
            source_runtime="codex_app",
            source_event_name=source_event_name,
            canonical_type=canonical_type,
            payload={"rollout_path": rollout_path, **dict(record)},
            session_id=codex_session_id,
            trace_id=codex_session_id,
            turn_id=payload.get("turn_id"),
            artifact_refs=artifact_refs,
            occurred_at=record.get("timestamp") if isinstance(record.get("timestamp"), str) else None,
            summary=summary,
        )

    def ingest_codex_app_snapshot(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        current_thread = str(snapshot.get("current_thread_id") or "").strip() or None
        streaming = snapshot.get("streaming_thread_ids") if isinstance(snapshot.get("streaming_thread_ids"), list) else []
        summary = (
            f"focused {current_thread}; {len(streaming)} streaming"
            if current_thread
            else f"codex app snapshot; {len(streaming)} streaming"
        )
        return self.emit(
            source_runtime="codex_app",
            source_event_name="codex_app_snapshot",
            canonical_type="session.snapshot",
            payload=snapshot,
            session_id=current_thread or "codex_app",
            trace_id=current_thread or "codex_app",
            summary=summary,
        )

    def ingest_station_capture(self, capture_result: Mapping[str, Any]) -> dict[str, Any]:
        manifest = capture_result.get("manifest") if isinstance(capture_result.get("manifest"), Mapping) else {}
        results = manifest.get("results") if isinstance(manifest, Mapping) and isinstance(manifest.get("results"), list) else []
        failed = [row for row in results if isinstance(row, Mapping) and row.get("status") != "ok"]
        summary = f"station render {manifest.get('run_stamp') or 'run'}: {len(results)} captures, {len(failed)} failed"
        artifact_refs = [str(capture_result.get("run_dir"))] if capture_result.get("run_dir") else []
        return self.emit(
            source_runtime="station_render",
            source_event_name="capture_run",
            canonical_type="artifact.changed",
            payload=capture_result,
            session_id=str(manifest.get("run_stamp") or "station_render"),
            trace_id=str(manifest.get("run_stamp") or "station_render"),
            artifact_refs=artifact_refs,
            summary=summary,
        )

    def ingest_runtime_claim(
        self,
        *,
        provider: str,
        action: str,
        claim_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        canonical_type = "runtime.claimed" if action == "claim" else "runtime.released"
        return self.emit(
            source_runtime="metabolism",
            source_event_name=f"provider_runtime_{action}",
            canonical_type=canonical_type,
            payload={"provider": provider, "claim_id": claim_id, **dict(payload or {})},
            session_id=f"metabolism:{provider or 'unknown'}",
            trace_id=f"metabolism:{provider or 'unknown'}",
            summary=f"{provider} {action} {claim_id}",
        )

    def ingest_claude_transcript_record(
        self,
        record: Mapping[str, Any],
        *,
        transcript_path: str,
        session_id: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        record_type = str(record.get("type") or "")
        if record_type == "progress":
            message = _compact_summary(record.get("message") or record.get("content") or record.get("text"))
            if message:
                events.append(
                    self.emit(
                        source_runtime="claude_code",
                        source_event_name="progress",
                        canonical_type="message.assistant",
                        payload={"transcript_path": transcript_path, **dict(record)},
                        session_id=session_id or record.get("sessionId") or record.get("session_id"),
                        trace_id=session_id or record.get("sessionId") or record.get("session_id"),
                        cwd=cwd or record.get("cwd"),
                        transcript_path=transcript_path,
                        occurred_at=record.get("timestamp") if isinstance(record.get("timestamp"), str) else None,
                        summary=message,
                    )
                )
            return events
        if record_type not in {"user", "assistant"}:
            return events
        message = record.get("message") if isinstance(record.get("message"), Mapping) else {}
        role = str(message.get("role") or record_type)
        resolved_session = session_id or record.get("sessionId") or record.get("session_id")
        resolved_cwd = cwd or record.get("cwd")
        occurred_at = record.get("timestamp") if isinstance(record.get("timestamp"), str) else None
        content = message.get("content")

        def emit_message(kind: str, text: str, *, block: Mapping[str, Any] | None = None) -> None:
            if _looks_system_injected(text):
                return
            events.append(
                self.emit(
                    source_runtime="claude_code",
                    source_event_name=kind,
                    canonical_type=f"message.{kind}",
                    payload={
                        "role": kind,
                        "content": text,
                        "block": dict(block or {}),
                        "transcript_path": transcript_path,
                        "record_uuid": record.get("uuid"),
                    },
                    session_id=resolved_session,
                    trace_id=resolved_session,
                    cwd=resolved_cwd,
                    transcript_path=transcript_path,
                    occurred_at=occurred_at,
                    summary=_compact_summary(text),
                )
            )

        if isinstance(content, str):
            emit_message("user" if role in {"user", "human"} else "assistant", content)
            return events
        if not isinstance(content, list):
            return events

        for block in content:
            if not isinstance(block, Mapping):
                continue
            block_type = str(block.get("type") or "")
            if block_type == "text":
                emit_message("user" if role in {"user", "human"} else "assistant", str(block.get("text") or ""), block=block)
            elif block_type == "thinking":
                thinking = str(block.get("thinking") or "").strip()
                has_signature = bool(block.get("signature"))
                text = thinking or ("Thinking..." if has_signature else "")
                if text:
                    events.append(
                        self.emit(
                            source_runtime="claude_code",
                            source_event_name="thinking",
                            canonical_type="message.thinking",
                            payload={
                                "role": "thinking",
                                "content": text,
                                "redacted": not bool(thinking),
                                "transcript_path": transcript_path,
                                "record_uuid": record.get("uuid"),
                            },
                            session_id=resolved_session,
                            trace_id=resolved_session,
                            cwd=resolved_cwd,
                            transcript_path=transcript_path,
                            occurred_at=occurred_at,
                            summary=_compact_summary(text),
                        )
                    )
            elif block_type == "tool_use":
                tool_name = str(block.get("name") or "tool")
                tool_input = block.get("input") if isinstance(block.get("input"), Mapping) else {}
                canonical_type = "subagent.started" if tool_name in {"Agent", "Task"} else "tool.started"
                summary = _compact_summary(f"{tool_name}: {_tool_input_summary(tool_name, tool_input)}")
                events.append(
                    self.emit(
                        source_runtime="claude_code",
                        source_event_name="tool_use",
                        canonical_type=canonical_type,
                        payload={
                            "tool_name": tool_name,
                            "tool_input": dict(tool_input or {}),
                            "transcript_path": transcript_path,
                            "record_uuid": record.get("uuid"),
                        },
                        session_id=resolved_session,
                        trace_id=resolved_session,
                        tool_use_id=block.get("id"),
                        subagent_id=block.get("id") if canonical_type == "subagent.started" else None,
                        cwd=resolved_cwd,
                        transcript_path=transcript_path,
                        occurred_at=occurred_at,
                        summary=summary,
                    )
                )
            elif block_type == "tool_result":
                result_text = _flatten_tool_result_content(block.get("content"))
                is_error = bool(block.get("is_error"))
                canonical_type = "runtime.error" if is_error else "tool.completed"
                events.append(
                    self.emit(
                        source_runtime="claude_code",
                        source_event_name="tool_result",
                        canonical_type=canonical_type,
                        payload={
                            "tool_use_id": block.get("tool_use_id"),
                            "content": result_text[:4000],
                            "is_error": is_error,
                            "transcript_path": transcript_path,
                            "record_uuid": record.get("uuid"),
                        },
                        session_id=resolved_session,
                        trace_id=resolved_session,
                        tool_use_id=block.get("tool_use_id"),
                        cwd=resolved_cwd,
                        transcript_path=transcript_path,
                        occurred_at=occurred_at,
                        summary=_compact_summary(("error: " if is_error else "result: ") + result_text),
                    )
                )
        return events

    def get_telemetry_nowait(self) -> Optional[dict[str, Any]]:
        try:
            return self._telemetry_queue.get_nowait()
        except queue.Empty:
            return None

    def replay(
        self,
        *,
        since_seq: int = 0,
        session_id: Optional[str] = None,
        source_runtime: Optional[str] = None,
        canonical_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 500), 2000))
        with self._lock:
            events = list(self._history)
        filtered: list[dict[str, Any]] = []
        for event in events:
            if int(event.get("seq") or 0) <= since_seq:
                continue
            if session_id and event.get("session_id") != session_id:
                continue
            if source_runtime and event.get("source_runtime") != source_runtime:
                continue
            if canonical_type and event.get("canonical_type") != canonical_type:
                continue
            filtered.append(event)
        return filtered[-limit:]

    def status(self) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            active_sessions = []
            for session in self._active_sessions.values():
                last_observed_at = str(session.get("last_observed_at") or "")
                lag_s = None
                try:
                    lag_s = max(0.0, now - datetime.fromisoformat(last_observed_at).timestamp())
                except ValueError:
                    pass
                active_sessions.append({**session, "lag_s": lag_s})
            active_sessions.sort(key=lambda item: str(item.get("last_observed_at") or ""), reverse=True)
            return {
                "schema": SCHEMA_VERSION,
                "api_revision": API_REVISION,
                "trace_path": str(self.trace_path),
                "seq": self._seq,
                "history_size": len(self._history),
                "max_history": self.max_history,
                "dropped_count": self._dropped_count,
                "gap_count": self._gap_count,
                "persistence": {
                    "trace_path": str(self.trace_path),
                    "enabled": self._persistence_disabled_until_s <= time.monotonic(),
                    "retry_in_s": max(0.0, self._persistence_disabled_until_s - time.monotonic()),
                    "dropped_count": self._persist_drop_count,
                    "error_count": self._persist_error_count,
                    "last_error": self._last_persistence_error,
                },
                "source_status": sorted(self._source_status.values(), key=lambda row: row["source_runtime"]),
                "active_sessions": active_sessions[:50],
                "canonical_counts": dict(self._canonical_counts),
                "source_counts": dict(self._source_counts),
                "sampler": dict(self._sampler_state),
            }

    def set_sampler_state(self, **updates: Any) -> None:
        with self._lock:
            self._sampler_state.update(_json_safe(updates))


def emit_agent_event_to_repo(repo_root: Path, **kwargs: Any) -> dict[str, Any]:
    """Convenience helper for subprocess contexts such as hooks and CLIs."""
    return AgentTraceStore(Path(repo_root)).emit(**kwargs)


def ingest_claude_hook_to_repo(repo_root: Path, action: str, payload: Mapping[str, Any] | None) -> dict[str, Any]:
    return AgentTraceStore(Path(repo_root)).ingest_claude_hook(action, payload)


def _jsonl_tail(path: Path, *, limit: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in _read_jsonl_tail_lines(path, limit=max(1, limit)):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _claude_user_text_from_record(record: Mapping[str, Any]) -> Optional[str]:
    if str(record.get("type") or "") != "user":
        return None
    message = record.get("message") if isinstance(record.get("message"), Mapping) else {}
    role = str(message.get("role") or "")
    if role and role not in {"user", "human"}:
        return None
    content = message.get("content")
    if isinstance(content, str):
        return None if _looks_system_injected(content) else content
    if not isinstance(content, list):
        return None
    parts: list[str] = []
    for block in content:
        if not isinstance(block, Mapping):
            continue
        if block.get("type") == "text":
            text = str(block.get("text") or "").strip()
            if text and not _looks_system_injected(text):
                parts.append(text)
    return "\n".join(parts).strip() or None


def claude_transcript_session_title(path: Path, *, line_limit: int = 220) -> Optional[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for index, line in enumerate(fh):
                if index >= line_limit:
                    break
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, Mapping):
                    continue
                title = _session_title_from_text(_claude_user_text_from_record(record))
                if title:
                    return title
    except OSError:
        return None
    return None


def _read_json_file(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _stable_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _project_slug_for_cwd(cwd: str) -> str:
    text = str(cwd or "").strip()
    if not text:
        return ""
    return re.sub(r"[^A-Za-z0-9]+", "-", text)


def _pid_running(pid: object) -> bool:
    try:
        parsed = int(pid)
    except (TypeError, ValueError):
        return False
    if parsed <= 0:
        return False
    try:
        os.kill(parsed, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claude_session_state_files(*, sessions_root: Optional[Path] = None) -> list[Path]:
    root = sessions_root or Path.home() / ".claude" / "sessions"
    if not root.exists():
        return []
    files = [path for path in root.glob("*.json") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    return files


def discover_claude_code_app_sessions(
    *,
    sessions_root: Optional[Path] = None,
    projects_root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Discover live Claude Code app/desktop sessions from the pid sidecar layer."""
    root = sessions_root or Path.home() / ".claude" / "sessions"
    project_root = projects_root or Path.home() / ".claude" / "projects"
    sessions: list[dict[str, Any]] = []
    for path in claude_session_state_files(sessions_root=root):
        record = _read_json_file(path)
        if not record:
            continue
        pid = record.get("pid")
        if not _pid_running(pid):
            continue
        session_id = str(record.get("sessionId") or record.get("session_id") or path.stem).strip()
        cwd = str(record.get("cwd") or "").strip()
        transcript_path = None
        project_slug = _project_slug_for_cwd(cwd)
        if session_id and project_slug:
            candidate = project_root / project_slug / f"{session_id}.jsonl"
            if candidate.exists():
                transcript_path = str(candidate)
        title = claude_transcript_session_title(Path(transcript_path)) if transcript_path else None
        sessions.append(
            {
                "pid": pid,
                "session_id": session_id or str(pid),
                "title": title,
                "cwd": cwd or None,
                "started_at": record.get("startedAt"),
                "kind": record.get("kind"),
                "entrypoint": record.get("entrypoint"),
                "state_path": str(path),
                "transcript_path": transcript_path,
                "transcript_exists": bool(transcript_path),
            }
        )
    sessions.sort(key=lambda row: int(row.get("started_at") or 0), reverse=True)
    return sessions


class AgentObservabilitySampler:
    """Low-cost resident sampler for app/session evidence.

    The sampler is deliberately conservative: it never launches Codex, never
    scans whole transcripts on every tick, and tails only new bytes after a file
    has been seen. The heartbeat gives operators proof that the backend plane is
    alive even when no agent is actively producing hooks.
    """

    def __init__(
        self,
        store: AgentTraceStore,
        repo_root: Path,
        *,
        poll_interval_s: float = 3.0,
        heartbeat_interval_s: float = 30.0,
        codex_probe_interval_s: float = 45.0,
        file_scan_interval_s: float = 5.0,
        process_probe_interval_s: float = 60.0,
        host_pressure_interval_s: float = 60.0,
        operator_bridge_interval_s: float = 10.0,
        operator_bridge_limit: int = 50,
        file_limit: int = 6,
        live_tail_lines: int = 80,
    ) -> None:
        self.store = store
        self.repo_root = Path(repo_root)
        self.poll_interval_s = max(float(poll_interval_s), 1.0)
        self.heartbeat_interval_s = max(float(heartbeat_interval_s), self.poll_interval_s)
        self.codex_probe_interval_s = max(float(codex_probe_interval_s), self.poll_interval_s)
        self.file_scan_interval_s = max(float(file_scan_interval_s), self.poll_interval_s)
        self.process_probe_interval_s = max(float(process_probe_interval_s), self.poll_interval_s)
        self.host_pressure_interval_s = max(float(host_pressure_interval_s), self.poll_interval_s)
        self.operator_bridge_interval_s = max(float(operator_bridge_interval_s), self.poll_interval_s)
        self._base_poll_interval_s = self.poll_interval_s
        self._base_process_probe_interval_s = self.process_probe_interval_s
        self._base_host_pressure_interval_s = self.host_pressure_interval_s
        self.operator_bridge_limit = max(int(operator_bridge_limit), 1)
        self.file_limit = max(int(file_limit), 1)
        self.live_tail_lines = max(int(live_tail_lines), 10)
        self._file_offsets: dict[str, int] = {}
        self._seen_transcript_record_keys: set[str] = set()
        self._last_active_digest: Optional[str] = None
        self._last_metabolism_digest: Optional[str] = None
        self._last_heartbeat_s = -self.heartbeat_interval_s
        self._last_codex_probe_s = 0.0
        self._last_file_scan_s = 0.0
        self._last_process_probe_s = 0.0
        self._last_host_pressure_s = 0.0
        self._last_operator_bridge_s = -self.operator_bridge_interval_s
        self._last_process_digest: Optional[str] = None
        self._last_host_pressure_digest: Optional[str] = None
        self._last_claude_session_digests: dict[str, str] = {}
        self._poll_count = 0

    def poll_once(self) -> None:
        downshift_state = self._apply_background_downshift()
        now = time.monotonic()
        self._poll_count += 1
        self.store.set_sampler_state(
            running=True,
            poll_count=self._poll_count,
            last_poll_at=_now_iso(),
            last_error=None,
            poll_interval_s=self.poll_interval_s,
            background_downshift=downshift_state,
        )
        if now - self._last_heartbeat_s >= self.heartbeat_interval_s:
            self._last_heartbeat_s = now
            self._emit_backend_heartbeat()
        self._emit_active_claude_session()
        self._emit_claude_code_app_sessions()
        self._emit_metabolism_ticks()
        if now - self._last_codex_probe_s >= self.codex_probe_interval_s:
            self._last_codex_probe_s = now
            self._emit_codex_probe()
        if now - self._last_process_probe_s >= self.process_probe_interval_s:
            self._last_process_probe_s = now
            self._emit_process_snapshot()
        if now - self._last_host_pressure_s >= self.host_pressure_interval_s:
            self._last_host_pressure_s = now
            self._emit_host_pressure_snapshot()
        if now - self._last_file_scan_s >= self.file_scan_interval_s:
            self._last_file_scan_s = now
            self._tail_recent_files()
        if now - self._last_operator_bridge_s >= self.operator_bridge_interval_s:
            self._last_operator_bridge_s = now
            self._emit_operator_bridge_actions()

    def _apply_background_downshift(self) -> dict[str, Any] | None:
        path = self.repo_root / BACKGROUND_DOWNSHIFT_RELATIVE_PATH
        if not path.is_file():
            self._restore_background_downshift()
            return None
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._restore_background_downshift()
            return {
                "schema": "background_loop_downshift_runtime_v1",
                "status": "invalid_state_file",
                "path": str(BACKGROUND_DOWNSHIFT_RELATIVE_PATH),
            }
        if (
            receipt.get("schema") != "background_loop_downshift_receipt_v1"
            or receipt.get("loop_kind") != "agent_observability_sampler"
            or receipt.get("result") != "applied"
        ):
            self._restore_background_downshift()
            return {
                "schema": "background_loop_downshift_runtime_v1",
                "status": "not_applicable",
                "path": str(BACKGROUND_DOWNSHIFT_RELATIVE_PATH),
            }
        duration_s = max(float(receipt.get("duration_s") or 0), 0.0)
        age_s = max(time.time() - path.stat().st_mtime, 0.0)
        if duration_s and age_s > duration_s:
            self._restore_background_downshift()
            return {
                "schema": "background_loop_downshift_runtime_v1",
                "status": "expired",
                "age_s": round(age_s, 3),
                "duration_s": duration_s,
                "path": str(BACKGROUND_DOWNSHIFT_RELATIVE_PATH),
            }
        effective_interval = max(
            float(receipt.get("effective_interval_s") or 15.0),
            self._base_poll_interval_s,
        )
        self.poll_interval_s = effective_interval
        self.process_probe_interval_s = max(self._base_process_probe_interval_s, effective_interval * 4)
        self.host_pressure_interval_s = max(self._base_host_pressure_interval_s, effective_interval * 4)
        return {
            "schema": "background_loop_downshift_runtime_v1",
            "status": "applied",
            "loop_kind": "agent_observability_sampler",
            "effective_interval_s": self.poll_interval_s,
            "age_s": round(age_s, 3),
            "duration_s": duration_s,
            "path": str(BACKGROUND_DOWNSHIFT_RELATIVE_PATH),
        }

    def _restore_background_downshift(self) -> None:
        self.poll_interval_s = self._base_poll_interval_s
        self.process_probe_interval_s = self._base_process_probe_interval_s
        self.host_pressure_interval_s = self._base_host_pressure_interval_s

    def mark_stopped(self) -> None:
        self.store.set_sampler_state(running=False, stopped_at=_now_iso())

    def mark_error(self, error: str) -> None:
        self.store.set_sampler_state(running=True, last_error=error, last_poll_at=_now_iso())

    def _emit_backend_heartbeat(self) -> None:
        status = self.store.status()
        self.store.emit(
            source_runtime="backend",
            source_event_name="sampler_heartbeat",
            canonical_type="runtime.heartbeat",
            session_id="agent_observability",
            trace_id="agent_observability",
            payload={
                "api_revision": API_REVISION,
                "poll_interval_s": self.poll_interval_s,
                "seq": status.get("seq"),
                "source_counts": status.get("source_counts"),
                "dropped_count": status.get("dropped_count"),
                "gap_count": status.get("gap_count"),
            },
            summary="agent observability sampler alive",
        )

    def _emit_active_claude_session(self) -> None:
        try:
            from tools.meta.bridge import session_transport

            record = session_transport.read_active_session()
        except Exception:
            record = None
        if not isinstance(record, Mapping):
            return
        extras = record.get("extras") if isinstance(record.get("extras"), Mapping) else {}
        active = extras.get("active_session") if isinstance(extras.get("active_session"), Mapping) else {}
        if not active:
            return
        digest = _stable_digest(active)
        if digest == self._last_active_digest:
            return
        self._last_active_digest = digest
        session_id = str(active.get("session_id") or "claude_active_session")
        last_event = str(active.get("last_event") or "active_session")
        self.store.emit(
            source_runtime="claude_code",
            source_event_name="active_session_heartbeat",
            canonical_type="session.heartbeat",
            session_id=session_id,
            trace_id=session_id,
            cwd=active.get("cwd"),
            transcript_path=active.get("transcript_path"),
            payload={"active_session": dict(active), "record": dict(record)},
            summary=f"Claude active session: {last_event}",
        )

    def _emit_claude_code_app_sessions(self) -> None:
        sessions = discover_claude_code_app_sessions()
        seen: set[str] = set()
        for session in sessions:
            session_id = str(session.get("session_id") or session.get("pid") or "claude_code")
            seen.add(session_id)
            digest = _stable_digest(session)
            transcript_path = session.get("transcript_path")
            if isinstance(transcript_path, str) and transcript_path:
                self._tail_live_claude_transcript(Path(transcript_path), session)
            if self._last_claude_session_digests.get(session_id) == digest:
                continue
            self._last_claude_session_digests[session_id] = digest
            self.store.emit(
                source_runtime="claude_code",
                source_event_name="claude_code_app_session",
                canonical_type="session.discovered",
                session_id=session_id,
                trace_id=session_id,
                cwd=session.get("cwd"),
                transcript_path=session.get("transcript_path"),
                artifact_refs=[
                    path
                    for path in (session.get("state_path"), session.get("transcript_path"))
                    if isinstance(path, str) and path
                ],
                payload=session,
                summary=f"Claude Code app pid {session.get('pid')} ({session.get('entrypoint') or 'unknown'})",
            )
        for session_id in set(self._last_claude_session_digests) - seen:
            self._last_claude_session_digests.pop(session_id, None)
            self.store.emit(
                source_runtime="claude_code",
                source_event_name="claude_code_app_session_gone",
                canonical_type="session.end",
                session_id=session_id,
                trace_id=session_id,
                payload={"session_id": session_id},
                summary=f"Claude Code app session ended: {session_id}",
            )

    def _tail_live_claude_transcript(self, path: Path, session: Mapping[str, Any]) -> None:
        try:
            size = path.stat().st_size
        except OSError:
            return
        key = str(path)
        records: list[dict[str, Any]] = []
        if key not in self._file_offsets:
            records = _jsonl_tail(path, limit=self.live_tail_lines)
            self._file_offsets[key] = size
        else:
            records = self._tail_new_jsonl(path)
        session_id = str(session.get("session_id") or path.stem)
        cwd = str(session.get("cwd") or "") or None
        for record in records:
            if self._remember_transcript_record(path, record):
                self.store.ingest_claude_transcript_record(
                    record,
                    transcript_path=str(path),
                    session_id=session_id,
                    cwd=cwd,
                )

    def _remember_transcript_record(self, path: Path, record: Mapping[str, Any]) -> bool:
        key_parts = [
            str(path),
            str(record.get("uuid") or ""),
            str(record.get("timestamp") or ""),
            str(record.get("type") or ""),
        ]
        key = "|".join(key_parts)
        if not any(key_parts[1:]):
            key = f"{path}|{_stable_digest(record)}"
        if key in self._seen_transcript_record_keys:
            return False
        self._seen_transcript_record_keys.add(key)
        if len(self._seen_transcript_record_keys) > 10000:
            self._seen_transcript_record_keys = set(list(self._seen_transcript_record_keys)[-5000:])
        return True

    def _emit_metabolism_ticks(self) -> None:
        ticks_path = self.repo_root / "state/metabolism/runtime_ticks.json"
        ticks = _read_json_file(ticks_path)
        if not ticks:
            return
        interesting = {
            "current_phase": ticks.get("current_phase"),
            "loop_tick_at": ticks.get("loop_tick_at"),
            "last_job_poll_at": ticks.get("last_job_poll_at"),
            "active_children": ticks.get("active_children"),
        }
        digest = _stable_digest(interesting)
        if digest == self._last_metabolism_digest:
            return
        self._last_metabolism_digest = digest
        self.store.emit(
            source_runtime="metabolism",
            source_event_name="runtime_ticks",
            canonical_type="runtime.heartbeat",
            session_id="metabolismd",
            trace_id="metabolismd",
            payload={"path": str(ticks_path), "ticks": ticks},
            artifact_refs=[str(ticks_path)],
            summary=f"metabolism phase {ticks.get('current_phase') or 'unknown'}",
        )

    def _emit_operator_bridge_actions(self) -> None:
        """Project operator-Chrome HUD action receipts into the canonical stream.

        On the first activation (cursor file missing or unmarked) this
        seeds the cursor with every existing ``action_id`` and emits
        nothing — historical body-bearing rows must NOT be backfilled
        into ``events.jsonl``. Subsequent calls project at most
        ``operator_bridge_limit`` new receipts per poll, emitting through
        this sampler's resident :class:`AgentTraceStore` so the in-memory
        history, telemetry queue, and WebSocket consumers see operator
        events immediately. The projector itself strips body-bearing
        fields defense-in-depth and applies its own bounded JSON cursor
        for dedupe. Errors are routed to ``stream.gap`` so a projector
        exception never breaks the surrounding sampler poll.
        """
        try:
            from system.lib.operator_bridge_tail import project_or_seed_operator_bridge_tail

            project_or_seed_operator_bridge_tail(
                self.repo_root,
                limit=self.operator_bridge_limit,
                emit_event=self.store.emit,
            )
        except Exception as exc:
            self.store.emit_gap(
                source_runtime="operator_bridge",
                reason="operator_bridge_projection_failed",
                payload={"error": str(exc)},
            )

    def _emit_codex_probe(self) -> None:
        try:
            self.store.ingest_codex_app_snapshot(snapshot_codex_app(connect=False))
        except Exception as exc:
            self.store.emit_gap(
                source_runtime="codex_app",
                reason="codex_probe_failed",
                payload={"error": str(exc)},
            )

    def _emit_process_snapshot(self) -> None:
        try:
            output = subprocess.check_output(
                ["ps", "ax", "-o", "pid=,comm=,args="],
                text=True,
                errors="replace",
                timeout=2.0,
            )
        except Exception as exc:
            self.store.emit_gap(
                source_runtime="backend",
                reason="process_probe_failed",
                payload={"error": str(exc)},
            )
            return
        rows: list[dict[str, Any]] = []
        for line in output.splitlines():
            lower = line.lower()
            if not any(token in lower for token in ("claude", "codex")):
                continue
            columns = line.strip().split(None, 2)
            if len(columns) < 2:
                continue
            pid_text = columns[0]
            command = columns[2] if len(columns) > 2 else columns[1]
            kind = "codex" if "codex" in lower else "claude"
            rows.append(
                {
                    "pid": int(pid_text) if pid_text.isdigit() else pid_text,
                    "kind": kind,
                    "command_preview": command[:260],
                }
            )
        summary = {
            "claude_processes": sum(1 for row in rows if row.get("kind") == "claude"),
            "codex_processes": sum(1 for row in rows if row.get("kind") == "codex"),
            "processes": rows[:80],
        }
        digest = _stable_digest(summary)
        if digest == self._last_process_digest:
            return
        self._last_process_digest = digest
        self.store.emit(
            source_runtime="backend",
            source_event_name="agent_process_snapshot",
            canonical_type="runtime.process_snapshot",
            session_id="agent_processes",
            trace_id="agent_processes",
            payload=summary,
            summary=(
                f"processes: Claude {summary['claude_processes']}, "
                f"Codex {summary['codex_processes']}"
            ),
        )

    def _emit_host_pressure_snapshot(self) -> None:
        try:
            from system.lib.host_pressure import build_progress_pressure_packet

            status = self.store.status()
            events = self.store.replay(limit=2000)
            packet = build_progress_pressure_packet(
                self.repo_root,
                trace_status=status,
                recent_events=events,
                window_s=15 * 60,
            )
            compact_signal = {
                "bottleneck_class": packet.get("summary", {}).get("bottleneck_class"),
                "governor_decision": packet.get("summary", {}).get("governor_decision"),
                "active_agents": packet.get("summary", {}).get("active_agents"),
                "pressure_index": packet.get("summary", {}).get("pressure_index"),
                "progress_per_pressure": packet.get("summary", {}).get("progress_per_pressure"),
            }
            digest = _stable_digest(compact_signal)
            if digest == self._last_host_pressure_digest:
                return
            self._last_host_pressure_digest = digest
            self.store.emit(
                source_runtime="backend",
                source_event_name="host_pressure_snapshot",
                canonical_type="runtime.host_pressure",
                session_id="host_pressure",
                trace_id="host_pressure",
                payload=packet,
                summary=(
                    f"host pressure: {compact_signal['bottleneck_class']} "
                    f"({compact_signal['governor_decision']})"
                ),
            )
        except Exception as exc:
            self.store.emit_gap(
                source_runtime="backend",
                reason="host_pressure_snapshot_failed",
                payload={"error": str(exc)},
            )

    def _tail_recent_files(self) -> None:
        for path in recent_codex_rollout_files(limit=self.file_limit):
            for record in self._tail_new_jsonl(path):
                self.store.ingest_codex_rollout_record(record, rollout_path=str(path))
        for path in recent_claude_transcript_files(limit=self.file_limit):
            for record in self._tail_new_jsonl(path):
                self._ingest_claude_transcript_record(path, record)

    def _tail_new_jsonl(self, path: Path) -> list[dict[str, Any]]:
        try:
            size = path.stat().st_size
        except OSError:
            return []
        key = str(path)
        if key not in self._file_offsets:
            # Start at EOF so a cold server does not replay huge histories or
            # duplicate old persisted events. Manual replay endpoints remain
            # available when historical hydration is desired.
            self._file_offsets[key] = size
            return []
        offset = self._file_offsets.get(key, 0)
        if size < offset:
            offset = 0
        if size == offset:
            return []
        try:
            with path.open("rb") as fh:
                fh.seek(offset)
                raw = fh.read(max(0, size - offset))
        except OSError:
            return []
        self._file_offsets[key] = size
        records: list[dict[str, Any]] = []
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                self.store.emit_gap(
                    source_runtime="backend",
                    reason="jsonl_tail_parse_error",
                    payload={"path": str(path), "line_preview": line[:160]},
                )
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
        return records

    def _ingest_claude_transcript_record(self, path: Path, record: Mapping[str, Any]) -> None:
        session_id = str(record.get("sessionId") or record.get("session_id") or path.stem)
        if self._remember_transcript_record(path, record):
            self.store.ingest_claude_transcript_record(record, transcript_path=str(path), session_id=session_id)


def recent_codex_rollout_files(
    *,
    sessions_root: Optional[Path] = None,
    limit: int = 10,
) -> list[Path]:
    root = sessions_root or Path.home() / ".codex" / "sessions"
    if not root.exists():
        return []
    files = [path for path in root.rglob("rollout-*.jsonl") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    return files[: max(1, limit)]


def ingest_recent_codex_rollouts(
    store: AgentTraceStore,
    *,
    sessions_root: Optional[Path] = None,
    file_limit: int = 5,
    tail_lines: int = 40,
) -> dict[str, Any]:
    files = recent_codex_rollout_files(sessions_root=sessions_root, limit=file_limit)
    events: list[dict[str, Any]] = []
    for path in files:
        for record in _jsonl_tail(path, limit=tail_lines):
            events.append(store.ingest_codex_rollout_record(record, rollout_path=str(path)))
    if not files:
        store.emit_gap(
            source_runtime="codex_app",
            reason="no_codex_rollout_files",
            payload={"sessions_root": str(sessions_root or Path.home() / ".codex" / "sessions")},
        )
    return {"files": [str(path) for path in files], "events_ingested": len(events), "events": events}


def recent_claude_transcript_files(*, projects_root: Optional[Path] = None, limit: int = 10) -> list[Path]:
    root = projects_root or Path.home() / ".claude" / "projects"
    if not root.exists():
        return []
    files = [path for path in root.rglob("*.jsonl") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    return files[: max(1, limit)]


def _claude_transcript_canonical_type(record: Mapping[str, Any]) -> str:
    record_type = str(record.get("type") or "").strip()
    if record_type == "user":
        return "turn.prompt"
    if record_type == "assistant":
        content = ((record.get("message") or {}) if isinstance(record.get("message"), Mapping) else {}).get("content")
        if isinstance(content, list):
            if any(isinstance(item, Mapping) and item.get("type") == "tool_use" for item in content):
                return "tool.proposed"
            if any(isinstance(item, Mapping) and item.get("type") == "tool_result" for item in content):
                return "tool.completed"
        return "intent.observed"
    if record_type in {"summary", "system"}:
        return "context.loaded"
    return "runtime.event"


def ingest_recent_claude_transcripts(
    store: AgentTraceStore,
    *,
    projects_root: Optional[Path] = None,
    file_limit: int = 5,
    tail_lines: int = 40,
) -> dict[str, Any]:
    files = recent_claude_transcript_files(projects_root=projects_root, limit=file_limit)
    events: list[dict[str, Any]] = []
    for path in files:
        for record in _jsonl_tail(path, limit=tail_lines):
            session_id = str(record.get("sessionId") or record.get("session_id") or path.stem)
            events.extend(
                store.ingest_claude_transcript_record(
                    record,
                    transcript_path=str(path),
                    session_id=session_id,
                )
            )
    if not files:
        store.emit_gap(
            source_runtime="claude_code",
            reason="no_claude_transcript_files",
            payload={"projects_root": str(projects_root or Path.home() / ".claude" / "projects")},
        )
    return {"files": [str(path) for path in files], "events_ingested": len(events), "events": events}


def snapshot_codex_app(*, port: int = 9224, connect: bool = False) -> dict[str, Any]:
    """Return a best-effort Codex desktop snapshot without making the CLI the surface."""
    from tools.meta.bridge import codex_driver

    if not connect:
        return {
            "mode": "cdp_probe",
            "probe": codex_driver.diagnose_cdp(requested_port=port, scan=False),
        }

    driver = codex_driver.CodexDriver.connect(port=port)
    try:
        threads = [asdict(row) if is_dataclass(row) else _json_safe(row) for row in driver.list_threads(limit=50)]
        current_thread_id = driver.current_thread_id()
        meta = driver.conversation_meta(current_thread_id) if current_thread_id else None
        return {
            "mode": "cdp_connected",
            "port": port,
            "target": {
                "id": driver.target_id,
                "url": driver.target_url,
                "title": driver.target_title,
            },
            "threads": threads,
            "current_thread_id": current_thread_id,
            "streaming_thread_ids": driver.streaming_thread_ids(),
            "current_thread_meta": meta,
        }
    finally:
        driver.close()
