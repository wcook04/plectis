"""
[PURPOSE]
- Teleology: Project each Claude / Codex session rollout into a **span-and-trace
  substrate** — an auditable ledger of externalized agent work with timings,
  sequence, bottleneck metrics, anti-pattern findings, and route-compliance
  scoring against the authored navigation ladder. Financial accounting for
  agent work; NOT a harness; NOT a capture of hidden chain-of-thought.
- Mechanism: Stream-parse `~/.claude/projects/<slug>/*.jsonl` and
  `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl`; pair each `tool_use` /
  `function_call` with its matching `tool_result` / `function_call_output` by
  id; compute `duration_ms` per span; aggregate into per-session traces with
  action-kind percentiles; compute route compliance against
  `trace_rules.navigation_reference_sequence`; detect anti-pattern shapes
  (`grep_before_kernel`, `read_bomb`, `loop_detected`, `stall_detected`,
  `cold_boot_missing_info`, `paper_module_skip`, `deep_without_ladder`).

[STRICT BOUNDARY]
- Parses observable process only: `timestamp`, `type`, `tool_use`/`tool_result`
  blocks (Claude) and `function_call`/`function_call_output` payloads (Codex);
  Bash command strings; Read/Edit/Write/Grep/Glob target paths; `is_error`
  outcomes. NEVER parses `text`, `thinking`, or tool-result content bodies
  beyond a bounded truncation marker.
- Never writes into `~/.claude` or `~/.codex`; only reads.

[INTERFACE]
- `build_agent_execution_trace(...)` returns a dict with `ledger`, `audit`,
  `navigation_cache`, `patterns`, `summary`, and `sessions_full` (the full span
  records, which the builder writes under `state/agent_telemetry/process/`).
- `write_agent_execution_trace(...)` writes the bounded hologram surfaces and
  the full spans/sessions under state/.
- `load_trace_rules(...)` loads the authored rules registry.
"""
from __future__ import annotations

import hashlib
import difflib
import json
import re
import shlex
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from system.lib.strict_json import StrictJsonError, loads_json_strict, read_json_strict

REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_agent_execution_trace.json"
TRACE_RULES_PATH = REPO_ROOT / "codex" / "doctrine" / "process" / "trace_rules.json"

HOLOGRAM_DIR = REPO_ROOT / "codex" / "hologram" / "process"
LEDGER_PATH = HOLOGRAM_DIR / "ledger.json"
AUDIT_PATH = HOLOGRAM_DIR / "audit.json"
NAVIGATION_CACHE_PATH = HOLOGRAM_DIR / "navigation_cache.json"
PATTERNS_PATH = HOLOGRAM_DIR / "patterns.json"
SUMMARY_PATH = HOLOGRAM_DIR / "summary.json"

DEFAULT_STATE_DIR = REPO_ROOT / "state" / "agent_telemetry" / "process"

LEDGER_SCHEMA_VERSION = "agent_execution_trace_ledger_v1"
AUDIT_SCHEMA_VERSION = "agent_execution_trace_audit_v1"
NAV_CACHE_SCHEMA_VERSION = "agent_execution_trace_navigation_cache_v1"
PATTERNS_SCHEMA_VERSION = "agent_execution_trace_patterns_v1"
SUMMARY_SCHEMA_VERSION = "agent_execution_trace_summary_v1"
SUMMARY_THOUGHT_TRACE_SCHEMA_VERSION = "summary_thought_trace_v1"
TRACE_COMPACTNESS_SCHEMA_VERSION = "trace_tape_levels_v1"
CACHED_BOTTLENECK_SUMMARY_SCHEMA_VERSION = "process_bottleneck_summary_cache_v0"
PROCESS_SUMMARY_ROUTE_SCHEMA_VERSION = "process_summary_v1"
PROCESS_SUMMARY_IDENTITY_SCOPE_SCHEMA_VERSION = "process_summary_identity_scope_v1"
PROCESS_SUMMARY_OWNER_SURFACE = "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>"
PROCESS_SUMMARY_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action process_summary_status "
    "--scope <session_id|claude:latest|codex:latest>"
)
PROCESS_SUMMARY_TASK_TOOL_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action task_tool "
    "--scope <session_id|claude:latest|codex:latest>"
)
PROCESS_SUMMARY_UNKNOWN_TOOL_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action unknown_tool "
    "--scope <session_id|claude:latest|codex:latest>"
)
PROCESS_SUMMARY_EXEC_SESSION_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action exec_session_io "
    "--scope <session_id|claude:latest|codex:latest>"
)
PROCESS_TRACE_OWNER_SURFACE = "./repo-python kernel.py --process-trace <session_id>"
PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND = "./repo-python kernel.py --process-bottlenecks --force"
PROCESS_TRACE_REFRESH_COMMAND = "./repo-python tools/meta/factory/build_agent_execution_trace.py"
PROCESS_TRACE_CACHE_CHECK_COMMAND = (
    "./repo-python tools/meta/factory/build_agent_execution_trace.py --cached-summary --limit 6"
)
PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND = (
    "./repo-python tools/meta/factory/build_agent_execution_trace.py --limit 6"
)
PROCESS_BOTTLENECK_BOUNDED_STATUS_COMMAND = "./repo-python kernel.py --process-bottlenecks --limit 6"
PROCESS_TRACE_PRESSURE_SAFE_DIGEST_COMMAND = "./repo-python kernel.py --latency-seed-digest --latency-seed-no-git"
PROCESS_TRACE_HOST_PRESSURE_CHECK_COMMAND = (
    "./repo-python kernel.py --host-pressure --host-pressure-no-processes --host-pressure-compact --host-pressure-event-limit 500"
)
PROCESS_TRACE_MATERIALIZE_COMMAND = PROCESS_TRACE_REFRESH_COMMAND
PROCESS_METADATA_PRIVACY_BOUNDARY = "process packets expose command/status/timing/output-size metadata, not raw task-output bodies"
MICROCOSM_CIRCUIT_ATTRIBUTION_CARD_COMMAND = (
    "PYTHONPATH=microcosm-substrate/src ./repo-python -m microcosm_core circuit-attribution --card"
)
CONTEXT_YIELD_ATTRIBUTION_SCHEMA_VERSION = "context_yield_attribution_packet_v0"
CONTEXT_YIELD_LARGE_OUTPUT_BYTES = 32000
CONTEXT_YIELD_ENTRY_PACKET_ALERT_BYTES = 20000
DOCUMENT_READ_OWNER_SURFACE = "./repo-python kernel.py --entry \"<task>\" --context-budget 12000"
DOCUMENT_READ_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action read_file --scope <path-or-topic>"
)
DOCUMENT_READ_PRIVACY_BOUNDARY = (
    "process packets expose document path/type/timing/output-size metadata; open full prose only after "
    "an owner route selects the document, row, or section"
)
KERNEL_OUTPUT_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action kernel_command --scope <task-or-route>"
)
COMMAND_SURFACE_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action command_surface_inventory --scope <surface>"
)
BASH_OTHER_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action bash_other --scope <path-or-owner>"
)
BASH_OTHER_PROCESS_TRIAGE_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage "
    "--action-kind bash_other"
)
GIT_STATE_SHELL_CHAIN_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action git_state_shell_chain"
)
GIT_OBJECT_MAINTENANCE_CHECK_COMMAND = (
    "./repo-python tools/meta/control/git_gc_maintenance.py --check"
)
GIT_STATE_SNAPSHOT_COMPACT_COMMAND = (
    "./repo-python tools/meta/control/git_state_snapshot.py "
    "--path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact"
)
ARTIFACT_DISCOVERY_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action artifact_discovery_inventory --scope <term-or-root>"
)
ARTIFACT_DISCOVERY_OWNER_SURFACE = ARTIFACT_DISCOVERY_QUOTE_COMMAND
ARTIFACT_DISCOVERY_KERNEL_ROUTE_COMMAND = (
    "./repo-python kernel.py --artifact-discovery-inventory <term-or-root>"
)
BASH_GREP_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action bash_grep --scope <term-or-root>"
)
BASH_FIND_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <term-or-root>"
)
HOST_FILESYSTEM_DISCOVERY_QUOTE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py --action host_filesystem_discovery "
    "--scope <host-path-or-term>"
)
ARTIFACT_DISCOVERY_EXAMPLE_COMMAND = (
    "./repo-python tools/meta/control/action_quote.py "
    "--action artifact_discovery_inventory --scope market --scope type_census"
)
ARTIFACT_DISCOVERY_PRIVACY_BOUNDARY = (
    "artifact_discovery_inventory emits path, size, suffix, and term metadata only; open selected files "
    "or owner content routes only after the metadata row is chosen"
)
HOST_FILESYSTEM_DISCOVERY_PRIVACY_BOUNDARY = (
    "host_filesystem_discovery emits scope metadata and replacement command shapes only; it does not "
    "walk host paths or store host file bodies, stdout, or stderr"
)
TRACE_OUTPUT_PRIVACY_BOUNDARY = (
    "trace tape rows expose observed tool calls, command/read outputs, timings, and bounded edit previews; "
    "packet metadata, discovered commands, full raw bodies, prompt bodies, and hidden reasoning remain omitted"
)
RAW_FIND_COMMAND_RE = re.compile(r"(?:^|[;&|]\s*|\$\()\s*find\s+")
TRACE_COMPACTNESS_PROFILES: dict[str, dict[str, int | bool | str]] = {
    "outline": {
        "row_limit": 0,
        "command_chars": 80,
        "target_limit": 1,
        "edit_preview_lines": 0,
        "output_preview_lines": 0,
        "output_preview_chars": 96,
        "include_tags": False,
        "profile": "final_state_edits_validations_commit",
    },
    "closeout": {
        "row_limit": 24,
        "command_chars": 180,
        "target_limit": 5,
        "edit_preview_lines": 3,
        "output_preview_lines": 1,
        "output_preview_chars": 180,
        "include_tags": False,
        "profile": "terminal_closeout_work_summary",
    },
    "tape": {
        "row_limit": 2000,
        "command_chars": 140,
        "target_limit": 2,
        "edit_preview_lines": 0,
        "output_preview_lines": 1,
        "output_preview_chars": 160,
        "include_tags": False,
        "profile": "observed_action_tape",
    },
    "tape+diff": {
        "row_limit": 2000,
        "command_chars": 220,
        "target_limit": 3,
        "edit_preview_lines": 6,
        "output_preview_lines": 1,
        "output_preview_chars": 220,
        "include_tags": False,
        "profile": "observed_action_tape_with_diff_hunks",
    },
    "audit": {
        "row_limit": 2000,
        "command_chars": 500,
        "target_limit": 5,
        "edit_preview_lines": 12,
        "output_preview_lines": 8,
        "output_preview_chars": 320,
        "include_tags": True,
        "profile": "observed_action_tape_with_audit_metadata",
    },
    "raw": {
        "row_limit": 2000,
        "command_chars": 2048,
        "target_limit": 10,
        "edit_preview_lines": 100,
        "output_preview_lines": 20,
        "output_preview_chars": 500,
        "include_tags": True,
        "profile": "raw_sidecar_replay",
    },
}
TRACE_LEVEL_ALIASES = {
    "compact": "tape",
    "standard": "tape+diff",
    "expanded": "audit",
    "all": "audit",
    "final": "closeout",
    "terminal": "closeout",
    "summary": "closeout",
}


def _normalize_trace_level(level: str | None) -> str:
    raw = (level or "tape").strip() or "tape"
    return TRACE_LEVEL_ALIASES.get(raw, raw)

# ---------------------------------------------------------------------------
# Kernel-flag and command classification (intentionally overlap with
# tools/meta/agent_telemetry/extract.py::classify_bash_command; kept here to
# keep this module stdlib-only and to stay independent of extract.py's
# histogram-only shape).
# ---------------------------------------------------------------------------
_REPO_PYTHON_COMMAND = r"(?:\./|[A-Za-z0-9_./-]+/)?repo-python"
_KERNEL_PREFIX_PATTERNS = (
    re.compile(rf"{_REPO_PYTHON_COMMAND}\s+kernel\.py\b"),
    re.compile(r"python3?\s+kernel\.py\b"),
    re.compile(r"\./kernel\.py\b"),
)
_KERNEL_COMMAND_MARKER = "kernel.py"
_KERNEL_FLAG_RE = re.compile(r"--[a-z][a-z0-9\-]+")
_TEST_OR_BUILD_COMMAND_RE = re.compile(
    r"\b(?:repo-pytest|pytest|py\.test|vitest|jest|tsc|mypy|ruff|pyright)\b"
    r"|python3?\s+-m\s+pytest\b"
    r"|(?:npm|pnpm|yarn)\s+(?:run\s+)?(?:test|build)\b"
    r"|npx\s+(?:vitest|tsc)\b"
)
_REPO_TOOL_COMMAND_RE = re.compile(
    rf"(?:{_REPO_PYTHON_COMMAND}|python3?)\s+"
    r"(?:-m\s+(?:tools(?:\.[\w]+)*|system(?:\.[\w]+)*)|tools/meta/[\w./-]+\.py|annex_import\.py|pipeline_[\w.-]+\.py|run_[\w.-]+\.py)\b"
    r"|tools/meta/[\w./-]+\.py"
)
_GREP_COMMAND_RE = re.compile(r"\b(grep|rg|ripgrep|ag|ack)\b")
_FIND_COMMAND_RE = re.compile(r"\bfind\b")
_CAT_COMMAND_RE = re.compile(r"\b(cat|less|more|head|tail)\b")
_TEST_OR_BUILD_MARKERS = (
    "repo-pytest",
    "pytest",
    "py.test",
    "vitest",
    "jest",
    "tsc",
    "mypy",
    "ruff",
    "pyright",
    "npm ",
    "pnpm ",
    "yarn ",
    "npx ",
)
_REPO_TOOL_MARKERS = (
    "repo-python",
    "python",
    "tools/meta/",
    "annex_import.py",
    "pipeline_",
    "run_",
)
_GREP_MARKERS = ("grep", "rg", "ripgrep", "ag", "ack")
_FIND_MARKERS = ("find",)
_CAT_MARKERS = ("cat", "less", "more", "head", "tail")

_TOOL_ACTION_KIND = {
    "Bash": "bash_other",
    "Read": "read_file",
    "Edit": "edit_file",
    "MultiEdit": "edit_file",
    "Write": "write_file",
    "NotebookEdit": "notebook_edit",
    "Grep": "grep_tool",
    "Glob": "glob_tool",
    "Task": "task_tool",
    "Agent": "task_tool",
    "WebFetch": "webfetch",
    "WebSearch": "webfetch",
}

_CODEX_EXEC_FUNCTION_NAMES = {"exec_command", "shell", "bash", "Bash"}
_CODEX_SESSION_IO_FUNCTION_NAMES = {"write_stdin", "read_thread_terminal"}
_CODEX_TASK_FUNCTION_NAMES = {
    "close_agent",
    "request_user_input",
    "resume_agent",
    "send_input",
    "spawn_agent",
    "update_plan",
    "wait_agent",
}
_CODEX_MCP_FUNCTION_NAMES = {
    "automation_update",
    "list_mcp_resources",
    "list_mcp_resource_templates",
    "load_workspace_dependencies",
    "read_mcp_resource",
    "request_plugin_install",
    "tool_search_tool",
}
_CODEX_READ_FUNCTION_NAMES = {"view_image"}


@dataclass
class Span:
    span_id: str
    agent: str
    session_id: str
    action_kind: str
    start_ts: str
    end_ts: str
    duration_ms: int
    outcome: str = "ok"
    sequence_index: int = 0
    turn_index: int = 0
    tool_name: str = ""
    command: str | None = None
    normalized_command: str | None = None
    target_paths: list[str] = field(default_factory=list)
    kernel_flags: list[str] = field(default_factory=list)
    is_grep_shape: bool = False
    is_kernel_shape: bool = False
    is_read_shape: bool = False
    retry_count: int = 0
    error_message_truncated: str | None = None
    parent_span_id: str | None = None
    output_byte_count: int = 0
    output_line_count: int = 0
    stdout_byte_count: int | None = None
    stderr_byte_count: int | None = None
    edit_summary: dict[str, Any] | None = None
    output_preview: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "span_id": self.span_id,
            "agent": self.agent,
            "session_id": self.session_id,
            "action_kind": self.action_kind,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome,
            "sequence_index": self.sequence_index,
            "turn_index": self.turn_index,
            "tool_name": self.tool_name,
            "is_grep_shape": self.is_grep_shape,
            "is_kernel_shape": self.is_kernel_shape,
            "is_read_shape": self.is_read_shape,
            "output_byte_count": self.output_byte_count,
            "output_line_count": self.output_line_count,
        }
        if self.stdout_byte_count is not None:
            payload["stdout_byte_count"] = self.stdout_byte_count
        if self.stderr_byte_count is not None:
            payload["stderr_byte_count"] = self.stderr_byte_count
        if self.edit_summary:
            payload["edit_summary"] = dict(self.edit_summary)
        if self.output_preview:
            payload["output_preview"] = list(self.output_preview)
        if self.command is not None:
            payload["command"] = self.command
        if self.normalized_command is not None:
            payload["normalized_command"] = self.normalized_command
        if self.target_paths:
            payload["target_paths"] = list(self.target_paths)
        if self.kernel_flags:
            payload["kernel_flags"] = list(self.kernel_flags)
        shape_tags = _command_shape_tags(
            self.action_kind,
            self.normalized_command or self.command or "",
            self.target_paths,
        )
        if shape_tags:
            payload["shape_tags"] = shape_tags
        if self.retry_count:
            payload["retry_count"] = self.retry_count
        if self.error_message_truncated:
            payload["error_message_truncated"] = self.error_message_truncated
        if self.parent_span_id:
            payload["parent_span_id"] = self.parent_span_id
        return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        cleaned = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _span_at_or_after(span: Mapping[str, Any], cutoff: datetime | None) -> bool:
    if cutoff is None:
        return True
    cutoff_utc = _ensure_utc(cutoff)
    for key in ("end_ts", "start_ts"):
        parsed = _parse_iso(str(span.get(key) or ""))
        if parsed is None:
            continue
        return _ensure_utc(parsed) >= cutoff_utc
    return True


def _ensure_example_command_shape_tags(example: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(example)
    if row.get("command_shape_tags") is None:
        row["command_shape_tags"] = _command_shape_tags(
            str(row.get("action_kind") or ""),
            str(row.get("normalized_command") or row.get("command") or ""),
            row.get("target_paths") or [],
        )
    return row


def _ensure_examples_command_shape_tags(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [_ensure_example_command_shape_tags(row) for row in rows if isinstance(row, Mapping)]


def _duration_ms(start: str | None, end: str | None) -> int:
    a = _parse_iso(start)
    b = _parse_iso(end)
    if a is None or b is None:
        return 0
    delta = (b - a).total_seconds() * 1000.0
    return int(max(delta, 0))


def _relpath(path: Path, *, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_read_json(path: Path) -> Any:
    try:
        return read_json_strict(path)
    except (OSError, StrictJsonError):
        return None


def _safe_read_json_with_receipt(path: Path, *, repo_root: Path) -> tuple[Any, dict[str, Any]]:
    rel = _relpath(path, repo_root=repo_root)
    try:
        raw = path.read_bytes()
    except OSError:
        return None, {
            "path": rel,
            "exists": False,
            "sha256": None,
            "mtime": _file_mtime_iso(path),
        }
    receipt = {
        "path": rel,
        "exists": True,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "mtime": _file_mtime_iso(path),
    }
    try:
        return loads_json_strict(raw.decode("utf-8"), source=str(path)), receipt
    except (UnicodeDecodeError, StrictJsonError):
        return None, receipt


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _file_mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return None


def _truncate(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    raw = str(text)
    if len(raw) <= limit:
        return raw
    return raw[: max(limit - 3, 0)] + "..."


def _truncate_utf8_bytes(text: str, max_bytes: int, *, suffix: str) -> str:
    if max_bytes <= 0:
        return text
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    suffix_bytes = suffix.encode("utf-8")
    budget = max(max_bytes - len(suffix_bytes), 0)
    return raw[:budget].decode("utf-8", errors="ignore").rstrip() + suffix


def _payload_text_for_sizing(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        pieces: list[str] = []
        for item in value:
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, Mapping) and isinstance(item.get("text"), str):
                pieces.append(str(item.get("text") or ""))
            else:
                pieces.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
        return "\n".join(pieces)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _text_output_metrics(text: str) -> dict[str, int]:
    if not text:
        return {"output_byte_count": 0, "output_line_count": 0}
    return {
        "output_byte_count": len(text.encode("utf-8")),
        "output_line_count": len(text.splitlines()) or 1,
    }


def _output_metrics_from_value(value: Any) -> dict[str, int | None]:
    metrics = _text_output_metrics(_payload_text_for_sizing(value))
    return {**metrics, "stdout_byte_count": None, "stderr_byte_count": None}


def _output_metrics_from_codex_output(raw_output: Any, parsed_output: Mapping[str, Any] | None) -> dict[str, int | None]:
    if parsed_output:
        stdout = parsed_output.get("stdout")
        stderr = parsed_output.get("stderr")
        stdout_available = stdout is not None
        stderr_available = stderr is not None
        if stdout_available or stderr_available:
            stdout_text = _payload_text_for_sizing(stdout)
            stderr_text = _payload_text_for_sizing(stderr)
            combined = stdout_text + stderr_text
            metrics = _text_output_metrics(combined)
            return {
                **metrics,
                "stdout_byte_count": len(stdout_text.encode("utf-8")),
                "stderr_byte_count": len(stderr_text.encode("utf-8")),
            }
        if parsed_output.get("content") is not None:
            return _output_metrics_from_value(parsed_output.get("content"))
    return _output_metrics_from_value(raw_output)


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_READ_LINE_NUMBER_RE = re.compile(r"^\s*(?:\d+\s*[→|]\s?|\d+:\s?|\d+\t)")
_TOOL_SCAFFOLD_LINE_RE = re.compile(
    r"^(?:Chunk ID:|Wall time:|Process (?:exited|running)|Original token count:|Output:|Total output lines:)\b"
)


def _strip_tool_scaffold_for_preview(text: str) -> str:
    lines = str(text or "").splitlines()
    output_markers = [idx for idx, line in enumerate(lines) if line.strip() == "Output:"]
    if output_markers:
        return "\n".join(lines[output_markers[-1] + 1 :])
    return "\n".join(line for line in lines if not _TOOL_SCAFFOLD_LINE_RE.match(line.strip()))


def _clean_preview_line(line: str, *, char_limit: int) -> str:
    cleaned = _ANSI_RE.sub("", str(line)).rstrip()
    cleaned = _READ_LINE_NUMBER_RE.sub("", cleaned)
    return _truncate(cleaned, char_limit) or ""


def _output_preview_from_text(text: str, *, max_lines: int = 8, line_chars: int = 220) -> list[str]:
    rows: list[str] = []
    for raw_line in _strip_tool_scaffold_for_preview(text).splitlines():
        line = _clean_preview_line(raw_line, char_limit=line_chars)
        if not line:
            continue
        rows.append(line)
        if len(rows) >= max_lines:
            break
    return rows


def _output_preview_from_value(value: Any, *, max_lines: int = 8, line_chars: int = 220) -> list[str]:
    return _output_preview_from_text(_payload_text_for_sizing(value), max_lines=max_lines, line_chars=line_chars)


def _output_preview_from_codex_output(
    raw_output: Any,
    parsed_output: Mapping[str, Any] | None,
    *,
    max_lines: int = 8,
    line_chars: int = 220,
) -> list[str]:
    if parsed_output:
        stdout = parsed_output.get("stdout")
        stderr = parsed_output.get("stderr")
        pieces: list[str] = []
        if stdout is not None:
            pieces.append(_payload_text_for_sizing(stdout))
        if stderr is not None:
            pieces.append(_payload_text_for_sizing(stderr))
        if pieces:
            return _output_preview_from_text("\n".join(pieces), max_lines=max_lines, line_chars=line_chars)
        if parsed_output.get("content") is not None:
            return _output_preview_from_value(parsed_output.get("content"), max_lines=max_lines, line_chars=line_chars)
    return _output_preview_from_value(raw_output, max_lines=max_lines, line_chars=line_chars)


def _preview_diff_line(line: str, *, limit: int = 160) -> str:
    raw = str(line or "").replace("\t", "    ").rstrip("\n\r")
    return _truncate(raw, limit) or ""


def _diff_stats_from_old_new(
    *,
    old_text: Any,
    new_text: Any,
    path: str | None = None,
    preview_limit: int = 12,
) -> dict[str, Any]:
    old_raw = "" if old_text is None else str(old_text)
    new_raw = "" if new_text is None else str(new_text)
    old_lines = old_raw.splitlines()
    new_lines = new_raw.splitlines()
    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path or 'input'}",
            tofile=f"b/{path or 'input'}",
            lineterm="",
            n=1,
        )
    )
    plus_lines: list[str] = []
    minus_lines: list[str] = []
    preview: list[str] = []
    for line in diff_lines:
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            plus_lines.append(line[1:])
            if len(preview) < preview_limit:
                preview.append("+" + _preview_diff_line(line[1:]))
        elif line.startswith("-"):
            minus_lines.append(line[1:])
            if len(preview) < preview_limit:
                preview.append("-" + _preview_diff_line(line[1:]))
    return {
        "added_line_count": len(plus_lines),
        "removed_line_count": len(minus_lines),
        "old_line_count": len(old_lines),
        "new_line_count": len(new_lines),
        "preview": preview,
    }


def _merge_edit_summaries(
    summaries: Iterable[Mapping[str, Any]],
    *,
    action: str,
    target_paths: Iterable[str],
    preview_limit: int = 12,
) -> dict[str, Any] | None:
    rows = [dict(row) for row in summaries if isinstance(row, Mapping)]
    if not rows:
        return None
    previews: list[str] = []
    for row in rows:
        for line in row.get("preview") or []:
            if len(previews) >= preview_limit:
                break
            previews.append(str(line))
    paths = []
    for path in target_paths:
        raw = str(path or "")
        if raw and raw not in paths:
            paths.append(raw)
    return {
        "action": action,
        "target_paths": paths[:5],
        "hunk_count": len(rows),
        "added_line_count": sum(_summary_int(row.get("added_line_count")) for row in rows),
        "removed_line_count": sum(_summary_int(row.get("removed_line_count")) for row in rows),
        "old_line_count": sum(_summary_int(row.get("old_line_count")) for row in rows),
        "new_line_count": sum(_summary_int(row.get("new_line_count")) for row in rows),
        "preview": previews,
        "preview_policy": "bounded_plus_minus_lines",
    }


def _edit_summary_from_claude_input(tool_name: str, tool_input: Mapping[str, Any], target_paths: list[str]) -> dict[str, Any] | None:
    path = str(tool_input.get("file_path") or (target_paths[0] if target_paths else ""))
    if tool_name == "Write":
        content = str(tool_input.get("content") or "")
        lines = content.splitlines()
        return {
            "action": "write_file",
            "target_paths": [path] if path else [],
            "hunk_count": 1 if lines else 0,
            "added_line_count": len(lines),
            "removed_line_count": 0,
            "old_line_count": 0,
            "new_line_count": len(lines),
            "preview": ["+" + _preview_diff_line(line) for line in lines[:12]],
            "preview_policy": "bounded_plus_minus_lines",
        }
    if tool_name == "Edit":
        row = _diff_stats_from_old_new(
            old_text=tool_input.get("old_string"),
            new_text=tool_input.get("new_string"),
            path=path,
        )
        return _merge_edit_summaries([row], action="edit_file", target_paths=[path] if path else target_paths)
    if tool_name == "MultiEdit":
        summaries = []
        for edit in tool_input.get("edits") or []:
            if not isinstance(edit, Mapping):
                continue
            summaries.append(
                _diff_stats_from_old_new(
                    old_text=edit.get("old_string"),
                    new_text=edit.get("new_string"),
                    path=path,
                )
            )
        return _merge_edit_summaries(summaries, action="multi_edit_file", target_paths=[path] if path else target_paths)
    if tool_name == "NotebookEdit":
        source = tool_input.get("new_source") or tool_input.get("source")
        if source is None:
            return None
        lines = str(source).splitlines()
        return {
            "action": "notebook_edit",
            "target_paths": [path] if path else target_paths[:5],
            "hunk_count": 1 if lines else 0,
            "added_line_count": len(lines),
            "removed_line_count": 0,
            "old_line_count": 0,
            "new_line_count": len(lines),
            "preview": ["+" + _preview_diff_line(line) for line in lines[:12]],
            "preview_policy": "bounded_plus_minus_lines",
        }
    return None


def _patch_text_from_codex_args(args: Mapping[str, Any]) -> str:
    for key in ("patch", "input", "diff", "unified_diff", "__raw"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _extract_patch_target_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for line in str(patch_text or "").splitlines():
        raw = line.strip()
        candidate = ""
        if raw.startswith("*** Update File:"):
            candidate = raw.split(":", 1)[1].strip()
        elif raw.startswith("*** Add File:"):
            candidate = raw.split(":", 1)[1].strip()
        elif raw.startswith("*** Delete File:"):
            candidate = raw.split(":", 1)[1].strip()
        elif raw.startswith(("+++ ", "--- ")):
            candidate = raw[4:].strip()
            if candidate in {"/dev/null", "dev/null"}:
                candidate = ""
            if candidate.startswith(("a/", "b/")):
                candidate = candidate[2:]
        if candidate and candidate not in paths:
            paths.append(candidate)
        if len(paths) >= 5:
            break
    return paths


def _edit_summary_from_patch_text(patch_text: str, *, target_paths: Iterable[str]) -> dict[str, Any] | None:
    if not str(patch_text or "").strip():
        return None
    plus_lines: list[str] = []
    minus_lines: list[str] = []
    preview: list[str] = []
    hunk_count = 0
    for line in str(patch_text).splitlines():
        if line.startswith("@@"):
            hunk_count += 1
            continue
        if line.startswith(("+++", "---", "***", "Index:", "diff ")):
            continue
        if line.startswith("+"):
            plus_lines.append(line[1:])
            if len(preview) < 12:
                preview.append("+" + _preview_diff_line(line[1:]))
        elif line.startswith("-"):
            minus_lines.append(line[1:])
            if len(preview) < 12:
                preview.append("-" + _preview_diff_line(line[1:]))
    paths = list(target_paths)
    if not paths:
        paths = _extract_patch_target_paths(patch_text)
    return {
        "action": "apply_patch",
        "target_paths": paths[:5],
        "hunk_count": hunk_count or (1 if plus_lines or minus_lines else 0),
        "added_line_count": len(plus_lines),
        "removed_line_count": len(minus_lines),
        "old_line_count": len(minus_lines),
        "new_line_count": len(plus_lines),
        "preview": preview,
        "preview_policy": "bounded_plus_minus_lines",
    }


def _is_kernel_command(cmd: str) -> bool:
    if _KERNEL_COMMAND_MARKER not in str(cmd or "").lower():
        return False
    return any(pat.search(cmd) for pat in _KERNEL_PREFIX_PATTERNS)


def _extract_kernel_flags(cmd: str) -> list[str]:
    if not _is_kernel_command(cmd):
        return []
    return list({match.group(0) for match in _KERNEL_FLAG_RE.finditer(cmd)})


_KERNEL_ROUTE_FLAG_PRIORITY: tuple[str, ...] = (
    "--entry",
    "--context-pack",
    "--navigation-metabolism",
    "--paper-module",
    "--paper-module-coverage",
    "--paper-lattice",
    "--option-surface",
    "--row",
    "--kind-atlas",
    "--session-diagnostics",
    "--process-bottlenecks",
    "--process-audit",
    "--command-profile",
    "--latency-seed-digest",
    "--candidate-work-item-type",
    "--annex-inspiration",
    "--info",
    "--preflight",
    "--pulse",
    "--phase",
    "--facts",
    "--fact-audit",
    "--docs-route",
    "--skill-find",
    "--skill-list",
    "--navigate",
    "--locate",
    "--compile",
    "--agent-operating-packet",
    "--agent-principles",
    "--raw-seed-ideas",
    "--raw-seed-help",
    "--append-agent-seed",
)


def _pick_primary_kernel_flag(flags: Iterable[str]) -> str | None:
    flag_set = {str(flag) for flag in flags if flag}
    if not flag_set:
        return None
    for canonical in _KERNEL_ROUTE_FLAG_PRIORITY:
        if canonical in flag_set:
            return canonical
    return max(flag_set, key=lambda flag: (len(flag), flag))


def _bash_action_kind(cmd: str) -> str:
    lower = cmd.lower()
    if _is_kernel_command(lower):
        return "kernel_command"
    if any(marker in lower for marker in _TEST_OR_BUILD_MARKERS) and _TEST_OR_BUILD_COMMAND_RE.search(lower):
        return "test_or_build_command"
    if any(marker in lower for marker in _REPO_TOOL_MARKERS) and _REPO_TOOL_COMMAND_RE.search(lower):
        return "repo_tool_command"
    if any(marker in lower for marker in _GREP_MARKERS) and _GREP_COMMAND_RE.search(lower):
        return "bash_grep"
    if any(marker in lower for marker in _FIND_MARKERS) and _FIND_COMMAND_RE.search(lower):
        return "bash_find"
    if any(marker in lower for marker in _CAT_MARKERS) and _CAT_COMMAND_RE.search(lower):
        return "bash_cat"
    return "bash_other"


def _is_work_ledger_session_preflight_command(lower_command: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[;&|]\s*)(?:(?:\./)?repo-python\s+|python3?\s+)?"
            r"tools/meta/factory/work_ledger\.py\s+session-preflight\b",
            lower_command,
        )
    )


def _is_mission_transaction_preflight_command(lower_command: str) -> bool:
    return bool(
        re.search(
            r"(?:^|[;&|]\s*)(?:(?:\./)?repo-python\s+|python3?\s+)?"
            r"tools/meta/control/mission_transaction_preflight\.py\b",
            lower_command,
        )
    )


def _normalize_command(cmd: str, *, limit: int = 120) -> str:
    collapsed = " ".join((cmd or "").split())
    return _truncate(collapsed, limit) or ""


def _extract_target_paths(cmd: str) -> list[str]:
    tokens = []
    for match in re.finditer(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9_.-]+", cmd or ""):
        tok = match.group(0).strip("./")
        if tok and "/" in tok:
            tokens.append(tok)
    seen: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.append(t)
        if len(seen) >= 5:
            break
    return seen


def _codex_function_basename(fn_name: str) -> str:
    return str(fn_name or "").rsplit(".", 1)[-1]


def _codex_tool_summary(fn_name: str, args: Mapping[str, Any]) -> str:
    parts = [str(fn_name or "function_call")]
    for key in ("session_id", "yield_time_ms", "timeout_ms", "agent_type", "path"):
        if key in args and args.get(key) not in (None, ""):
            parts.append(f"{key}={args.get(key)}")
    if "chars" in args:
        parts.append(f"chars_len={len(str(args.get('chars') or ''))}")
    tool_uses = args.get("tool_uses")
    if isinstance(tool_uses, list):
        parts.append(f"tool_uses={len(tool_uses)}")
    targets = args.get("targets")
    if isinstance(targets, list):
        parts.append(f"targets={len(targets)}")
    return " ".join(parts)


def _command_shape_tags(kind: str, command: str | None, target_paths: Iterable[str]) -> list[str]:
    targets = tuple(str(path) for path in target_paths if str(path))
    return list(_command_shape_tags_cached(str(kind or ""), command or "", targets))


def _process_bottleneck_triage_quote_command(kind: str) -> str:
    action_kind = str(kind or "bash_other")
    return (
        "./repo-python tools/meta/control/action_quote.py --action process_bottleneck_triage "
        f"--action-kind {action_kind}"
    )


def _first_concrete_test_scope(examples: Iterable[Mapping[str, Any]]) -> str | None:
    for example in examples:
        if not isinstance(example, Mapping):
            continue
        paths = [str(path).strip() for path in example.get("target_paths") or [] if str(path).strip()]
        if not paths:
            paths = _extract_target_paths(str(example.get("normalized_command") or ""))
        for path in paths:
            if (
                path
                and "<" not in path
                and ">" not in path
                and path.endswith((".py", ".ts", ".tsx", ".js", ".jsx"))
            ):
                return path
    return None


@lru_cache(maxsize=8192)
def _command_shape_tags_cached(kind: str, command: str, targets: tuple[str, ...]) -> tuple[str, ...]:
    lower = command.lower()
    tags: list[str] = []
    git_diff_command = re.search(r"(?:^|[;&|]\s*)(?:\./repo-git|git)\s+diff\b", lower)
    git_metadata_probe_command = re.search(
        r"(?:^|[;&|]\s*)(?:\./repo-git|git)\s+rev-parse\b",
        lower,
    )
    git_diff_summary_mode = any(
        flag in lower
        for flag in ("--name-status", "--name-only", "--stat", "--numstat", "--shortstat")
    )
    git_diff_scoped_patch = bool(
        git_diff_command and re.search(r"(?:\./repo-git|git)\s+diff\b.*\s--\s+\S", lower)
    )
    if (
        re.search(r"\|\s*(?:tail|head|sed|grep|rg)\b", lower)
        or re.search(r"\|\s*(?:python3?|./repo-python)\b", lower)
        or re.search(r">\s*/tmp/", lower)
    ):
        tags.append("output_limited")
    python_module_cli = bool(
        re.search(
            r"(?:^|[;&|]\s*)(?:[a-z_][a-z0-9_]*=\S+\s+)*(?:(?:\./)?repo-python|python3?)\s+-m\s+[\w.]+",
            lower,
        )
    )
    if python_module_cli:
        tags.append("python_module_cli")
        if "output_limited" in tags:
            tags.append("python_module_cli_output_limited")
    python_inline = bool(
        re.search(
            r"(?:^|[;&|]\s*)(?:cd\s+\S+\s*&&\s*)?(?:(?:\./)?repo-python|python3?)\s+(?:-c\s+|-\s*<<)",
            lower,
        )
    )
    if python_inline:
        tags.append("python_inline")
        if (
            "import json" in lower
            or "json.load" in lower
            or "json.loads" in lower
            or "open(" in lower
            or ".read(" in lower
            or "pathlib" in lower
            or "from pathlib import path" in lower
            or any(path.endswith((".json", ".jsonl", ".csv", ".tsv")) for path in targets)
        ):
            tags.append("inline_python_data_probe")
    if lower.lstrip().startswith("until ") or ("tasks/" in lower and (".output" in lower or ".exit" in lower)):
        tags.append("background_poll")
    if any(("/tasks/" in path or "tasks/" in path) and path.endswith((".output", ".exit")) for path in targets):
        tags.append("task_output_file")
    if any("tool-results/" in path for path in targets):
        tags.append("tool_result_file")
    if any("/tmp/" in path or path.startswith("tmp/") for path in targets):
        tags.append("tmp_artifact_file")
    if kind == "test_or_build_command":
        test_targets = [path for path in targets if path.endswith((".py", ".ts", ".tsx", ".js", ".jsx"))]
        if test_targets:
            tags.append("focused_test_target")
        if "pytest" in lower and not test_targets:
            tags.append("suite_wide_pytest")
        if "vitest" in lower and not test_targets:
            tags.append("suite_wide_vitest")
        if "git stash" in lower:
            tags.append("stash_wrapped_test")
    if kind == "repo_tool_command":
        if any(path.startswith("tools/meta/factory/") for path in targets):
            tags.append("factory_builder")
        if any(path.startswith("tools/meta/") for path in targets):
            tags.append("repo_meta_tool")
    if _is_work_ledger_session_preflight_command(lower) or _is_mission_transaction_preflight_command(lower):
        tags.append("preflight_full_drilldown" if "--full" in lower else "preflight_compact_owner_status")
    if kind == "kernel_command":
        if "--entry" in lower:
            tags.append("entry_packet")
        if "--context-pack" in lower:
            tags.append("context_pack")
        if "--navigation-metabolism" in lower:
            tags.append("navigation_metabolism_packet")
        if "--process-bottlenecks" in lower or "--process-audit" in lower or "--session-diagnostics" in lower:
            tags.append("process_diagnostic_packet")
        if "--host-pressure" in lower:
            tags.append("host_pressure_packet")
        if "--paper-module" in lower:
            tags.append("paper_module")
        if "--kind-atlas" in lower:
            tags.append("kind_atlas_packet")
        if "--option-surface" in lower or "--row" in lower:
            tags.append("option_surface_packet")
        if "--info" in lower:
            tags.append("info_packet")
        if "--preflight" in lower:
            tags.append("preflight_packet")
    if kind == "bash_find":
        if RAW_FIND_COMMAND_RE.search(lower):
            tags.append("raw_find_scan")
    if kind == "bash_grep":
        if re.search(r"(?:^|[;&|]\s*)(?:grep|git\s+grep|rg)\s+", lower):
            tags.append("raw_search_scan")
    if kind in {"bash_cat", "bash_other"} and (
        git_metadata_probe_command
        or "git status" in lower
        or "git diff --cached" in lower
        or "git log" in lower
    ):
        if git_metadata_probe_command or ";" in lower or "&&" in lower or "|" in lower:
            tags.append("git_state_shell_chain")
    if "git_state_snapshot.py" in lower and "--diff-review" in lower:
        tags.append("diff_review_context_packet")
    if git_diff_command:
        if git_diff_summary_mode:
            tags.append("git_diff_ladder")
        elif git_diff_scoped_patch:
            tags.append("scoped_diff_hunk")
        else:
            tags.append("global_raw_diff")
    if kind == "read_file":
        if any(path.endswith((".md", ".markdown", ".txt")) and not path.startswith(("/tmp/", "tmp/")) for path in targets):
            tags.append("document_read")
    if kind == "exec_session_io":
        if "write_stdin" in lower:
            tags.append("exec_session_poll")
        if "yield_time_ms=" in lower:
            tags.append("configured_wait")
    seen: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.append(tag)
    return tuple(seen)


_DIRECT_DATA_PLANE_ACTION_KINDS = {
    "apply_patch",
    "bash_cat",
    "bash_find",
    "bash_grep",
    "edit_file",
    "grep_tool",
    "glob_tool",
    "read_file",
    "repo_tool_command",
    "test_or_build_command",
    "write_file",
}

_LEGITIMATE_RETURN_REASONS = {
    "authority",
    "bounded_context",
    "diagnostic",
    "exact_refresh",
    "freshness",
    "runtime_state",
}
_KERNEL_ROUTE_REASON_VALUES = _LEGITIMATE_RETURN_REASONS | {"route"}

_DEFAULT_KERNEL_ROUTE_REASON_BY_FLAG = {
    "--agent-operating-packet": "bounded_context",
    "--command-profile": "diagnostic",
    "--context-pack": "bounded_context",
    "--coverage-enforcement-matrix": "diagnostic",
    "--docs-route": "authority",
    "--entry": "route",
    "--facts": "authority",
    "--kind-atlas": "authority",
    "--navigation-metabolism": "diagnostic",
    "--option-surface": "authority",
    "--paper-module": "authority",
    "--phase": "runtime_state",
    "--preflight": "runtime_state",
    "--process-audit": "diagnostic",
    "--process-bottlenecks": "diagnostic",
    "--process-patterns": "diagnostic",
    "--pulse": "runtime_state",
    "--raw-seed-browse": "authority",
    "--raw-seed-ideas": "authority",
    "--raw-seed-navigation": "authority",
    "--raw-seed-query": "authority",
    "--route-refresh": "exact_refresh",
    "--session-diagnostics": "diagnostic",
    "--shards": "authority",
    "--stale": "freshness",
}
_KERNEL_ROUTE_REASON_STANDARD_REF = "types.RouteLeaseModeControl.kernel_route_reason_by_flag"


@lru_cache(maxsize=1)
def _kernel_route_reason_by_flag() -> dict[str, str]:
    payload = _safe_read_json(STANDARD_PATH)
    raw_map: Any = None
    if isinstance(payload, Mapping):
        route_control = payload.get("types", {}).get("RouteLeaseModeControl", {})
        if isinstance(route_control, Mapping):
            raw_map = route_control.get("kernel_route_reason_by_flag")
    if not isinstance(raw_map, Mapping):
        return dict(_DEFAULT_KERNEL_ROUTE_REASON_BY_FLAG)

    cleaned: dict[str, str] = {}
    for flag, reason in raw_map.items():
        if not isinstance(flag, str) or not flag.startswith("--"):
            continue
        if not isinstance(reason, str) or reason not in _KERNEL_ROUTE_REASON_VALUES:
            continue
        cleaned[flag] = reason
    if not cleaned:
        return dict(_DEFAULT_KERNEL_ROUTE_REASON_BY_FLAG)

    merged = dict(_DEFAULT_KERNEL_ROUTE_REASON_BY_FLAG)
    merged.update(cleaned)
    return merged


def _kernel_call_reason(span: Span) -> str | None:
    if not span.is_kernel_shape:
        return None
    flags = set(span.kernel_flags)
    for flag, reason in _kernel_route_reason_by_flag().items():
        if flag in flags:
            return reason
    lower = (span.normalized_command or span.command or "").lower()
    if "refresh" in lower or "--full" in lower:
        return "exact_refresh"
    return "unknown"


def _is_direct_data_plane_action(span: Span) -> bool:
    if span.action_kind in _DIRECT_DATA_PLANE_ACTION_KINDS:
        return True
    lower = (span.normalized_command or span.command or "").lower()
    if span.action_kind == "bash_other" and re.search(
        r"\b(?:git\s+(?:diff|status)|rg|grep|sed|cat|pytest|py_compile)\b",
        lower,
    ):
        return True
    return False


def _mode_signal(
    *,
    signal_id: str,
    span: Span | None,
    severity: str,
    reason: str,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "signal_id": signal_id,
        "severity": severity,
        "reason": reason,
    }
    if span is not None:
        payload.update(
            {
                "span_id": span.span_id,
                "sequence_index": span.sequence_index,
                "kernel_call_reason": _kernel_call_reason(span),
                "normalized_command": span.normalized_command,
                "target_paths": list(span.target_paths[:3]),
                "command_shape_tags": _command_shape_tags(
                    span.action_kind,
                    span.normalized_command or span.command or "",
                    span.target_paths,
                ),
            }
        )
    if detail:
        payload.update(dict(detail))
    return payload


def _route_lease_mode_control(spans: list[Span]) -> dict[str, Any]:
    """Infer route-lease consumption from observable commands only.

    The lease itself is emitted by ``--entry``; traces do not capture hidden
    reasoning, so this reducer only classifies command-shape evidence after
    that entry handoff.
    """
    entry_spans = [
        sp
        for sp in spans
        if sp.is_kernel_shape and "--entry" in set(sp.kernel_flags)
    ]
    if not entry_spans:
        return {
            "schema_version": "route_lease_mode_control_v0",
            "status": "route_lease_not_seen",
            "route_reason_standard_ref": _KERNEL_ROUTE_REASON_STANDARD_REF,
            "signal_counts": {},
            "signals": [],
        }

    lease_span = entry_spans[0]
    after_lease = [sp for sp in spans if sp.sequence_index > lease_span.sequence_index]
    first_direct = next((sp for sp in after_lease if _is_direct_data_plane_action(sp)), None)
    before_direct = [
        sp
        for sp in after_lease
        if first_direct is None or sp.sequence_index < first_direct.sequence_index
    ]
    kernel_before_direct = [sp for sp in before_direct if sp.is_kernel_shape]
    kernel_after_lease = [sp for sp in after_lease if sp.is_kernel_shape]

    signals: list[dict[str, Any]] = [
        _mode_signal(
            signal_id="entry_lease_issued",
            span=lease_span,
            severity="info",
            reason="--entry issued route_lease_v0 control-plane handoff",
        )
    ]

    if after_lease and first_direct is None:
        signals.append(
            _mode_signal(
                signal_id="route_lease_unconsumed",
                span=kernel_after_lease[0] if kernel_after_lease else lease_span,
                severity="info",
                reason="no direct data-plane action observed after entry lease in this session window",
                detail={"observed_post_lease_span_count": len(after_lease)},
            )
        )

    for sp in kernel_before_direct:
        reason = _kernel_call_reason(sp) or "unknown"
        tags = _command_shape_tags(sp.action_kind, sp.normalized_command or sp.command or "", sp.target_paths)
        if "output_limited" in tags or "tmp_artifact_file" in tags:
            signals.append(
                _mode_signal(
                    signal_id="full_output_kernel_bloat",
                    span=sp,
                    severity="warning",
                    reason="kernel output was piped or redirected instead of using a compact route mode",
                )
            )
        elif reason in _LEGITIMATE_RETURN_REASONS:
            signals.append(
                _mode_signal(
                    signal_id="legitimate_return_to_kernel",
                    span=sp,
                    severity="info",
                    reason=f"kernel call after lease is shaped as {reason}",
                )
            )
        else:
            signals.append(
                _mode_signal(
                    signal_id="second_kernel_call_before_direct_action",
                    span=sp,
                    severity="warning",
                    reason="another kernel command ran before any observed direct local action after entry",
                )
            )
        if sp.target_paths and reason not in _LEGITIMATE_RETURN_REASONS:
            signals.append(
                _mode_signal(
                    signal_id="kernel_call_for_known_path_question",
                    span=sp,
                    severity="warning",
                    reason="kernel command carried concrete path targets that usually belong to direct local tools",
                )
            )

    broad_spans: dict[str, list[Span]] = defaultdict(list)
    for sp in kernel_after_lease:
        reason = _kernel_call_reason(sp) or "unknown"
        if reason not in {"route", "bounded_context", "unknown"}:
            continue
        command = sp.normalized_command or sp.command or ""
        if not command:
            continue
        broad_spans[command].append(sp)
    for command, occurrences in broad_spans.items():
        count = len(occurrences)
        if count >= 2:
            first_span = occurrences[0]
            repeat_span = occurrences[1]
            signals.append(
                _mode_signal(
                    signal_id="broad_route_repeated_without_new_authority_question",
                    span=repeat_span,
                    severity="warning",
                    reason="same broad kernel route repeated after entry lease",
                    detail={
                        "repeated_count": count,
                        "first_span_id": first_span.span_id,
                        "first_sequence_index": first_span.sequence_index,
                    },
                )
            )

    counts = Counter(str(row.get("signal_id") or "") for row in signals if row.get("signal_id"))
    warning_count = sum(1 for row in signals if row.get("severity") == "warning")
    return {
        "schema_version": "route_lease_mode_control_v0",
        "status": "warning" if warning_count else "observed",
        "route_reason_standard_ref": _KERNEL_ROUTE_REASON_STANDARD_REF,
        "lease_span_id": lease_span.span_id,
        "lease_sequence_index": lease_span.sequence_index,
        "direct_action_after_lease": first_direct is not None,
        "first_direct_action_span_id": first_direct.span_id if first_direct else None,
        "signal_counts": dict(sorted(counts.items())),
        "warning_count": warning_count,
        "signals": signals[:20],
    }


def _aggregate_mode_control(session_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    session_hits: dict[str, set[str]] = defaultdict(set)
    lease_session_count = 0
    warning_session_count = 0
    for row in session_rows:
        session_id = str(row.get("session_id") or "")
        mode = row.get("route_lease_mode_control") if isinstance(row.get("route_lease_mode_control"), Mapping) else {}
        if mode.get("status") == "route_lease_not_seen":
            continue
        lease_session_count += 1
        if int(mode.get("warning_count") or 0) > 0:
            warning_session_count += 1
        for signal in mode.get("signals") or []:
            if not isinstance(signal, Mapping):
                continue
            signal_id = str(signal.get("signal_id") or "")
            if not signal_id:
                continue
            counts[signal_id] += 1
            session_hits[signal_id].add(session_id)
            if len(examples[signal_id]) < 3:
                example = dict(signal)
                example["session_id"] = session_id
                examples[signal_id].append(example)
    return {
        "schema_version": "route_lease_mode_control_aggregate_v0",
        "lease_session_count": lease_session_count,
        "warning_session_count": warning_session_count,
        "signal_counts": dict(sorted(counts.items())),
        "signals": [
            {
                "signal_id": signal_id,
                "count": count,
                "session_count": len(session_hits.get(signal_id) or set()),
                "examples": examples.get(signal_id, []),
            }
            for signal_id, count in counts.most_common()
        ],
    }


def _example_matches_frontend_vitest(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    target_paths = [str(path).lower() for path in example.get("target_paths") or [] if str(path)]
    joined_targets = " ".join(target_paths)
    return (
        "vitest" in command
        and (
            "system/server/ui" in command
            or "rootnavigator" in command
            or "system/server/ui" in joined_targets
            or "rootnavigator" in joined_targets
        )
    )


def _example_matches_paper_module_output_limiter(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    return "paper_module" in tags and "output_limited" in tags and "--paper-module" in command


def _example_matches_task_ledger_rebuild(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    return "tools/meta/factory/task_ledger_apply.py" in command and bool(re.search(r"\brebuild\b", command))


def _example_matches_task_ledger_quick_capture(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    if "tools/meta/factory/task_ledger_apply.py" not in command:
        return False
    return bool(re.search(r"\b(?:quick-capture|capture)\b", command))


def _example_matches_microcosm_circuit_attribution(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    if "circuit-attribution" not in command:
        return False
    return bool(
        re.search(r"\b(?:python3?|repo-python)\s+-m\s+microcosm_core\b", command)
        or re.search(r"\bmicrocosm\s+circuit-attribution\b", command)
    )


def _example_matches_host_filesystem_find(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    if not RAW_FIND_COMMAND_RE.search(command):
        return False
    host_root = bool(
        re.search(r"\bfind\s+(?:/users/|['\"]?\$home\b|['\"]?~/)", command)
    )
    cloud_term = any(
        term in command
        for term in (
            "google drive",
            "googledrive",
            "google-drive",
            "icloud drive",
            "icloud-drive",
            "onedrive",
            "one drive",
            "dropbox",
            "drivefs",
        )
    )
    return host_root or cloud_term


def _example_matches_git_object_find(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    if not RAW_FIND_COMMAND_RE.search(command):
        return False
    return ".git/objects" in command or "/.git/objects" in command or "git/objects" in command


def _kernel_flag_quote_scope(flag: str) -> str:
    scope = flag.strip().lstrip("-").strip()
    scope = re.sub(r"[^A-Za-z0-9_.:-]+", "-", scope).strip("-")
    return scope or "kernel"


def _kernel_flag_command_surface_hint(flag: str) -> dict[str, Any]:
    scope = _kernel_flag_quote_scope(flag)
    return {
        "hint_id": "route_kernel_flag_through_command_surface",
        "reason": "Kernel bottleneck evidence names a concrete route flag, so quote that route before rerunning a broad kernel packet.",
        "kernel_flag": flag,
        "concrete_preferred_next": (
            "./repo-python tools/meta/control/action_quote.py "
            f"--action kernel_command --scope {scope}"
        ),
        "preferred_next": (
            "./repo-python tools/meta/control/action_quote.py "
            "--action kernel_command --scope <kernel-surface>"
        ),
        "owner_surface": (
            "./repo-python tools/meta/control/action_quote.py "
            f"--action command_surface_inventory --scope {scope}"
        ),
    }


def _merge_repair_hints_by_id(*groups: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for hint in group:
            if not isinstance(hint, Mapping):
                continue
            hint_id = str(hint.get("hint_id") or "")
            if hint_id and hint_id in seen:
                continue
            if hint_id:
                seen.add(hint_id)
            merged.append(dict(hint))
    return merged


def _bottleneck_repair_hints(kind: str, examples: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    tag_counts: Counter[str] = Counter()
    example_rows: list[Mapping[str, Any]] = []
    for example in examples:
        if not isinstance(example, Mapping):
            continue
        example_rows.append(example)
        tag_counts.update(str(tag) for tag in example.get("command_shape_tags") or [])
    hints: list[dict[str, Any]] = []
    if kind == "test_or_build_command":
        if any(_example_matches_frontend_vitest(example) for example in example_rows):
            hints.append({
                "hint_id": "route_frontend_vitest_through_action_quote",
                "reason": "Slow examples include frontend Vitest or RootNavigator validation commands.",
                "preferred_next": "./repo-python tools/meta/control/action_quote.py --action frontend_vitest_validation --scope system/server/ui/src/pages/RootNavigator.tsx",
            })
        if tag_counts.get("focused_test_target"):
            focused_scope = _first_concrete_test_scope(example_rows)
            focused_hint = {
                "hint_id": "route_focused_validation_through_action_quote",
                "reason": "Slow examples already name focused test/build targets, so the next step is a concise owner quote or narrower validation plan rather than another broad run.",
                "preferred_next": "./repo-python tools/meta/control/action_quote.py --action test_or_build_command --scope <path-or-node> --session-id <work-ledger-session>",
                "quote_surface": "./repo-python tools/meta/control/action_quote.py --action test_or_build_command --scope <path-or-node>",
            }
            if focused_scope:
                concrete_next = (
                    "./repo-python tools/meta/control/action_quote.py --action test_or_build_command "
                    f"--scope {shlex.quote(focused_scope)}"
                )
                focused_hint["concrete_preferred_next"] = concrete_next
                focused_hint["replacement_commands"] = [concrete_next]
            hints.append(focused_hint)
        if tag_counts.get("suite_wide_pytest") or tag_counts.get("suite_wide_vitest"):
            hints.append({
                "hint_id": "scope_tests_before_full_suite",
                "reason": "Slow examples include suite-wide test commands without explicit test targets.",
                "preferred_next": "Run focused test paths or node ids first; reserve full-suite pytest/vitest for final verification.",
            })
        if tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "avoid_tail_masked_test_runs",
                "reason": "Slow test/build examples are hidden behind tail/head/grep/python filters or /tmp redirection.",
                "preferred_next": "Use a focused command plus concise pytest/vitest flags instead of piping broad runs through output limiters.",
            })
        if tag_counts.get("stash_wrapped_test"):
            hints.append({
                "hint_id": "avoid_stash_wrapped_validation",
                "reason": "A slow test command is wrapped in git stash operations inside a dirty shared worktree.",
                "preferred_next": "Use scoped validation against owned paths; do not wrap validation in stash unless explicitly claimed and safe.",
            })
    elif kind == "repo_tool_command":
        if any(_example_matches_task_ledger_rebuild(example) for example in example_rows):
            hints.append({
                "hint_id": "use_task_ledger_rebuild_check_before_full_rebuild",
                "reason": "Slow repo-tool examples include full Task Ledger projection rebuilds.",
                "preferred_next": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress",
                "replacement_commands": [
                    "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress",
                    "./repo-python tools/meta/factory/task_ledger_apply.py authority-health --projection-check --quiet-progress",
                    "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1 --quiet-progress",
                ],
            })
        if any(_example_matches_task_ledger_quick_capture(example) for example in example_rows):
            hints.append({
                "hint_id": "append_task_ledger_capture_before_projection_rebuild",
                "reason": "Slow repo-tool examples include Task Ledger capture commands that can wait on projection rebuild work.",
                "preferred_next": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                    "--projection-rebuild-policy off ..."
                ),
                "replacement_commands": [
                    (
                        "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                        "--projection-rebuild-policy off ..."
                    ),
                    "./repo-python tools/meta/factory/task_ledger_apply.py intake-status",
                    "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1 --quiet-progress",
                ],
            })
        if tag_counts.get("factory_builder"):
            hints.append({
                "hint_id": "prefer_check_or_targeted_builder_mode",
                "reason": "Slow examples invoke repo factory builders.",
                "preferred_next": "Prefer builder --check, target/domain flags, or the owner route's compact status before full regeneration.",
                "quote_surface": COMMAND_SURFACE_QUOTE_COMMAND,
                "replacement_commands": [
                    COMMAND_SURFACE_QUOTE_COMMAND,
                    "./repo-python kernel.py --command-profile <owner-surface>",
                ],
            })
        if tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "use_owner_compact_status_instead_of_tail",
                "reason": "Slow repo-tool examples pipe builder output through tail/grep.",
                "preferred_next": "Add or use a compact owner status/check packet rather than truncating a full builder run.",
                "quote_surface": COMMAND_SURFACE_QUOTE_COMMAND,
                "replacement_commands": [
                    COMMAND_SURFACE_QUOTE_COMMAND,
                    "./repo-python kernel.py --command-profile <owner-surface>",
                ],
            })
    elif kind == "kernel_command":
        if any(_example_matches_paper_module_output_limiter(example) for example in example_rows):
            hints.append({
                "hint_id": "route_paper_module_output_through_action_quote",
                "reason": "Slow kernel examples read full paper modules through shell output limiters.",
                "preferred_next": "./repo-python tools/meta/control/action_quote.py --action paper_module_index",
            })
        if tag_counts.get("process_diagnostic_packet") and tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "replace_process_diagnostic_limiter_with_status_packet",
                "reason": "Slow kernel process-diagnostic examples pipe or redirect broad output instead of using bounded status routes.",
                "preferred_next": "./repo-python kernel.py --process-bottlenecks",
                "replacement_commands": [
                    "./repo-python kernel.py --process-bottlenecks",
                    "./repo-python kernel.py --process-audit",
                    "./repo-python kernel.py --command-profile process-audit",
                ],
            })
        if tag_counts.get("entry_packet") and tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "replace_entry_limiter_with_bounded_entry_or_context_pack",
                "reason": "Slow entry examples add shell output limiters around an already bounded routing packet.",
                "preferred_next": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                "quote_surface": KERNEL_OUTPUT_QUOTE_COMMAND,
                "replacement_commands": [
                    "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                    "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                    KERNEL_OUTPUT_QUOTE_COMMAND,
                    "./repo-python kernel.py --row <kind_id>:<row_id> --band card",
                ],
            })
        if tag_counts.get("host_pressure_packet"):
            hints.append({
                "hint_id": "replace_host_pressure_full_packet_with_compact_recheck",
                "reason": "Slow host-pressure examples emit broad pressure packets when only admission or recovery status is needed.",
                "preferred_next": "./repo-python kernel.py --host-pressure --host-pressure-no-processes --host-pressure-compact --host-pressure-event-limit 100",
                "replacement_commands": [
                    "./repo-python kernel.py --host-pressure --host-pressure-no-processes --host-pressure-compact --host-pressure-event-limit 100",
                    "./repo-python kernel.py --host-pressure --host-pressure-no-processes --host-pressure-event-limit 500 --json",
                    "./repo-python kernel.py --command-profile host-pressure",
                ],
            })
        if tag_counts.get("context_pack") and tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "replace_context_pack_limiter_with_selected_lens",
                "reason": "Slow context-pack examples hide large packets behind shell output limiters.",
                "preferred_next": "Use the routine context-pack row handles, then drill into a selected row/card instead of truncating the full packet.",
                "replacement_commands": [
                    "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                    "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                    "./repo-python kernel.py --row <kind_id>:<row_id> --band card",
                ],
            })
        if tag_counts.get("kind_atlas_packet") or tag_counts.get("option_surface_packet"):
            hints.append({
                "hint_id": "replace_inventory_limiter_with_cluster_or_card_band",
                "reason": "Slow option-surface or kind-atlas examples truncate broad inventory output.",
                "preferred_next": "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag",
                "replacement_commands": [
                    "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag",
                    "./repo-python kernel.py --option-surface <kind_id> --band card --ids <row_id>",
                    "./repo-python kernel.py --row <kind_id>:<row_id> --band card",
                ],
            })
        if tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "replace_kernel_output_limiter_with_compact_mode",
                "reason": "Slow kernel examples pipe or redirect output instead of using a bounded route mode.",
                "preferred_next": "Use a compact kernel mode, command card, selected lens, or row/card drilldown rather than truncating full output.",
                "quote_surface": KERNEL_OUTPUT_QUOTE_COMMAND,
                "replacement_commands": [
                    KERNEL_OUTPUT_QUOTE_COMMAND,
                    "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                    "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                    "./repo-python kernel.py --latency-seed-digest --latency-seed-no-git",
                ],
            })
        if tag_counts.get("context_pack"):
            hints.append({
                "hint_id": "start_with_summary_or_selected_lens",
                "reason": "Slow kernel examples include context-pack calls.",
                "preferred_next": "Use summary-first packets, selected lenses, or stable-row drilldowns before widening context-pack evidence.",
            })
        if tag_counts.get("info_packet"):
            hints.append({
                "hint_id": "prefer_pulse_or_entry_over_info_dump",
                "reason": "Slow kernel examples include --info output truncation.",
                "preferred_next": "Use --pulse, --entry, or a command card before reopening --info.",
            })
    elif kind in {"bash_cat", "bash_grep", "bash_other"}:
        shell_limiter_hint = {
            "hint_id": "replace_shell_limiter_with_compact_packet",
            "reason": "Slow examples rely on shell output limiters.",
            "preferred_next": "Prefer a compact kernel/tool packet that emits only the needed fields.",
            "quote_surface": COMMAND_SURFACE_QUOTE_COMMAND,
            "replacement_commands": [
                COMMAND_SURFACE_QUOTE_COMMAND,
                "./repo-python kernel.py --command-profile <owner-surface>",
            ],
        }
        shell_limiter_emitted = False
        git_state_count = int(tag_counts.get("git_state_shell_chain") or 0)
        global_diff_count = int(tag_counts.get("global_raw_diff") or 0)
        output_limited_count = int(tag_counts.get("output_limited") or 0)
        raw_search_count = int(tag_counts.get("raw_search_scan") or 0)
        tmp_artifact_count = int(tag_counts.get("tmp_artifact_file") or 0)
        background_poll_count = int(tag_counts.get("background_poll") or 0)
        inline_python_data_probe_count = int(tag_counts.get("inline_python_data_probe") or 0)
        python_module_cli_output_limited_count = int(
            tag_counts.get("python_module_cli_output_limited") or 0
        )
        specific_scan_count = max(
            git_state_count,
            global_diff_count,
            raw_search_count,
            tmp_artifact_count,
            background_poll_count,
            inline_python_data_probe_count,
            python_module_cli_output_limited_count,
        )
        if output_limited_count > specific_scan_count:
            hints.append(shell_limiter_hint)
            shell_limiter_emitted = True
        exact_python_module_replacements: list[str] = []
        if any(_example_matches_microcosm_circuit_attribution(example) for example in example_rows):
            exact_python_module_replacements.append(MICROCOSM_CIRCUIT_ATTRIBUTION_CARD_COMMAND)
        python_module_cli_hint = {
            "hint_id": "replace_python_module_tail_with_compact_cli_mode",
            "reason": "Slow examples run Python module CLIs and hide broad output behind shell limiters.",
            "preferred_next": (
                exact_python_module_replacements[0]
                if exact_python_module_replacements
                else "Use or add a compact/json/status flag on the module CLI instead of piping full output through tail/head/grep."
            ),
            "quote_surface": COMMAND_SURFACE_QUOTE_COMMAND,
            "replacement_commands": exact_python_module_replacements + [
                "./repo-python tools/meta/control/action_quote.py --action command_surface --scope <module-or-command>",
                "python -m <module> --help",
                "Add a checked compact/json/status mode to the owning module CLI when repeated probes need the same summary.",
            ],
        }
        if exact_python_module_replacements:
            python_module_cli_hint["specific_replacement_reason"] = (
                "The observed microcosm_core circuit-attribution command already exposes a compact --card route."
            )
        if tag_counts.get("python_module_cli_output_limited"):
            hints.append(python_module_cli_hint)
        if tag_counts.get("global_raw_diff"):
            hints.append({
                "hint_id": "replace_global_raw_diff_with_diff_review_context",
                "reason": "Slow examples include raw global git diff output before path/risk selection.",
                "preferred_next": "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact",
            })
        if tag_counts.get("git_state_shell_chain"):
            hints.append({
                "hint_id": "replace_git_shell_chain_with_state_snapshot",
                "reason": "Slow examples combine git status, staged diff, branch, or log checks through shell output limiters.",
                "preferred_next": GIT_STATE_SHELL_CHAIN_QUOTE_COMMAND,
                "owner_surface": "./repo-python tools/meta/control/git_state_snapshot.py --scope <path> --path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact",
                "replacement_commands": [
                    GIT_STATE_SHELL_CHAIN_QUOTE_COMMAND,
                    "./repo-python tools/meta/control/git_state_snapshot.py --scope <path> --path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact",
                    "./repo-python tools/meta/control/git_state_snapshot.py --path-limit 40 --recent-limit 3 --skip-git-metadata-write-probe --compact",
                ],
            })
        if tag_counts.get("background_poll"):
            hints.append({
                "hint_id": "replace_polling_with_status_surface",
                "reason": "Slow examples poll background task output files.",
                "preferred_next": "./repo-python kernel.py --process-summary claude:latest",
                "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
                "quote_surface": PROCESS_SUMMARY_QUOTE_COMMAND,
                "replacement_commands": [
                    "./repo-python kernel.py --process-summary claude:latest",
                    PROCESS_SUMMARY_QUOTE_COMMAND,
                    PROCESS_TRACE_OWNER_SURFACE,
                    PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
                ],
                "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
            })
        tmp_artifact_hint = {
            "hint_id": "replace_tmp_artifact_scan_with_owner_summary",
            "reason": "Slow examples scan temporary artifact files through shell commands.",
            "preferred_next": "./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>",
            "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
            "quote_surface": PROCESS_SUMMARY_QUOTE_COMMAND,
            "replacement_commands": [
                PROCESS_SUMMARY_OWNER_SURFACE,
                PROCESS_SUMMARY_QUOTE_COMMAND,
                PROCESS_TRACE_OWNER_SURFACE,
                PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            ],
            "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
        }
        raw_search_hint = {
            "hint_id": "replace_raw_search_scan_with_owner_route",
            "reason": "Slow examples use recursive grep/rg discovery scans.",
            "preferred_next": BASH_GREP_QUOTE_COMMAND,
            "owner_surface": ARTIFACT_DISCOVERY_OWNER_SURFACE,
            "scope_narrowing": (
                "Use stable object names, slugs, path fragments, or rare domain terms; drop common glue words "
                "before running the inventory route."
            ),
            "quote_surface": BASH_GREP_QUOTE_COMMAND,
            "replacement_commands": [
                BASH_GREP_QUOTE_COMMAND,
                ARTIFACT_DISCOVERY_OWNER_SURFACE,
                ARTIFACT_DISCOVERY_KERNEL_ROUTE_COMMAND,
                "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
                "rg --files <known-roots> | rg '<name-or-term>'",
            ],
            "privacy_boundary": ARTIFACT_DISCOVERY_PRIVACY_BOUNDARY,
        }
        if raw_search_count and tmp_artifact_count:
            if kind == "bash_grep" or raw_search_count >= tmp_artifact_count:
                hints.extend([raw_search_hint, tmp_artifact_hint])
            else:
                hints.extend([tmp_artifact_hint, raw_search_hint])
        elif tmp_artifact_count:
            hints.append(tmp_artifact_hint)
        elif raw_search_count:
            hints.append(raw_search_hint)
        if tag_counts.get("inline_python_data_probe"):
            process_triage_quote_command = _process_bottleneck_triage_quote_command(kind)
            hints.append({
                "hint_id": "replace_inline_python_data_probe_with_owner_tool",
                "reason": "Slow examples use inline Python to read or shape local data files.",
                "preferred_next": process_triage_quote_command,
                "quote_surface": COMMAND_SURFACE_QUOTE_COMMAND,
                "replacement_commands": [
                    process_triage_quote_command,
                    BASH_OTHER_QUOTE_COMMAND,
                    COMMAND_SURFACE_QUOTE_COMMAND,
                    "./repo-python kernel.py --command-profile <owner-surface>",
                    "Create or reuse a checked ./repo-python tools/... owner command with compact JSON output.",
                ],
            })
        if tag_counts.get("output_limited") and not shell_limiter_emitted:
            hints.append(shell_limiter_hint)
        if kind == "bash_other" and not hints:
            hints.append({
                "hint_id": "route_unclassified_bash_output_through_action_quote",
                "reason": "Output-heavy shell examples did not match a narrower command-shape owner.",
                "preferred_next": BASH_OTHER_QUOTE_COMMAND,
                "quote_surface": COMMAND_SURFACE_QUOTE_COMMAND,
                "replacement_commands": [
                    BASH_OTHER_QUOTE_COMMAND,
                    COMMAND_SURFACE_QUOTE_COMMAND,
                    "./repo-python kernel.py --command-profile <owner-surface>",
                ],
            })
    elif kind == "bash_find":
        if tag_counts.get("raw_find_scan"):
            if any(_example_matches_git_object_find(example) for example in example_rows):
                hints.append({
                    "hint_id": "replace_git_object_find_scan_with_gc_maintenance_check",
                    "reason": (
                        "Slow examples walk .git/objects directly; use the Git maintenance read model "
                        "instead of path-level object scans."
                    ),
                    "preferred_next": GIT_OBJECT_MAINTENANCE_CHECK_COMMAND,
                    "owner_surface": GIT_OBJECT_MAINTENANCE_CHECK_COMMAND,
                    "quote_surface": GIT_STATE_SHELL_CHAIN_QUOTE_COMMAND,
                    "replacement_commands": [
                        GIT_OBJECT_MAINTENANCE_CHECK_COMMAND,
                        GIT_STATE_SHELL_CHAIN_QUOTE_COMMAND,
                        GIT_STATE_SNAPSHOT_COMPACT_COMMAND,
                        "./repo-git count-objects -vH",
                    ],
                    "pre_action_card": {
                        "status": "git_object_status_first",
                        "before": "find .git/objects -type f ...",
                        "first_route": GIT_OBJECT_MAINTENANCE_CHECK_COMMAND,
                        "fallback_route": GIT_STATE_SNAPSHOT_COMPACT_COMMAND,
                        "scope_rule": "Use Git count-object and maintenance status surfaces before walking the object database.",
                    },
                    "privacy_boundary": (
                        "git_gc_maintenance emits Git object counts, sizes, and maintenance admission metadata; "
                        "it does not expose object contents or require path-level object walks"
                    ),
                })
            if any(_example_matches_host_filesystem_find(example) for example in example_rows):
                hints.append({
                    "hint_id": "replace_host_find_scan_with_host_filesystem_quote",
                    "reason": (
                        "Slow examples search broad host roots or cloud-drive names, which should not route "
                        "through repo artifact inventory."
                    ),
                    "preferred_next": "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <host-path-or-term>",
                    "owner_surface": HOST_FILESYSTEM_DISCOVERY_QUOTE_COMMAND,
                    "quote_surface": "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <host-path-or-term>",
                    "replacement_commands": [
                        "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <host-path-or-term>",
                        HOST_FILESYSTEM_DISCOVERY_QUOTE_COMMAND,
                        "mdfind -onlyin \"$HOME\" '<name predicate>' | head -20",
                        "find \"$HOME\" -maxdepth 3 <name-predicate> -print -quit",
                    ],
                    "pre_action_card": {
                        "status": "host_filesystem_scope_first",
                        "before": "broad find over /Users, $HOME, or cloud-drive folder names",
                        "first_route": "./repo-python tools/meta/control/action_quote.py --action bash_find --scope <host-path-or-term>",
                        "fallback_route": HOST_FILESYSTEM_DISCOVERY_QUOTE_COMMAND,
                        "scope_rule": "Use the host root or cloud-drive name; do not invoke repo artifact inventory for host paths.",
                    },
                    "privacy_boundary": HOST_FILESYSTEM_DISCOVERY_PRIVACY_BOUNDARY,
                })
            hints.append({
                "hint_id": "replace_find_scan_with_rg_files_or_option_surface",
                "reason": "Slow examples use raw find scans for discovery.",
                "preferred_next": BASH_FIND_QUOTE_COMMAND,
                "owner_surface": ARTIFACT_DISCOVERY_OWNER_SURFACE,
                "quote_surface": BASH_FIND_QUOTE_COMMAND,
                "replacement_commands": [
                    BASH_FIND_QUOTE_COMMAND,
                    ARTIFACT_DISCOVERY_OWNER_SURFACE,
                    ARTIFACT_DISCOVERY_KERNEL_ROUTE_COMMAND,
                    "rg --files <known-roots> | rg '<name-or-term>'",
                    "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag",
                ],
                "privacy_boundary": ARTIFACT_DISCOVERY_PRIVACY_BOUNDARY,
            })
        if tag_counts.get("output_limited"):
            hints.append({
                "hint_id": "avoid_head_masked_find_runs",
                "reason": "Slow find examples are hidden behind head/tail rather than using a bounded discovery surface.",
                "preferred_next": "Use a typed option surface or rg --files with a precise path/pattern instead of truncating broad find output.",
            })
    elif kind == "read_file":
        read_hint_count = len(hints)
        if tag_counts.get("task_output_file") or tag_counts.get("tool_result_file"):
            hints.append({
                "hint_id": "replace_output_file_read_with_status_surface",
                "reason": "Slow reads target provider task output or tool-result files.",
                "preferred_next": "Use the owning process/session/status packet or rerun the command with a compact output mode instead of opening large output files.",
                "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
                "quote_surface": PROCESS_SUMMARY_QUOTE_COMMAND,
                "replacement_commands": [
                    PROCESS_SUMMARY_OWNER_SURFACE,
                    PROCESS_SUMMARY_QUOTE_COMMAND,
                    PROCESS_TRACE_OWNER_SURFACE,
                    PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
                ],
                "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
            })
        if tag_counts.get("tmp_artifact_file"):
            hints.append({
                "hint_id": "replace_tmp_file_read_with_structured_summary",
                "reason": "Slow reads target temporary artifacts.",
                "preferred_next": "Parse the artifact into a compact JSON/status summary, or rerun the owner command in a bounded mode.",
                "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
                "quote_surface": PROCESS_SUMMARY_QUOTE_COMMAND,
                "replacement_commands": [
                    PROCESS_SUMMARY_OWNER_SURFACE,
                    PROCESS_SUMMARY_QUOTE_COMMAND,
                    PROCESS_TRACE_OWNER_SURFACE,
                    PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
                ],
                "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
            })
        if tag_counts.get("document_read"):
            hints.append({
                "hint_id": "prefer_card_or_section_before_full_doc_read",
                "reason": "Slow reads target prose documents.",
                "preferred_next": "Use a card/row/section route or a bounded line range before reopening the whole document.",
                "owner_surface": DOCUMENT_READ_OWNER_SURFACE,
                "quote_surface": DOCUMENT_READ_QUOTE_COMMAND,
                "replacement_commands": [
                    DOCUMENT_READ_OWNER_SURFACE,
                    DOCUMENT_READ_QUOTE_COMMAND,
                    "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                    "./repo-python kernel.py --docs-route <query-or-path>",
                    "./repo-python kernel.py --option-surface <kind_id> --band card --ids <row_id>",
                    "./repo-python kernel.py --paper-module <slug>",
                ],
                "privacy_boundary": DOCUMENT_READ_PRIVACY_BOUNDARY,
            })
        if len(hints) == read_hint_count:
            hints.append({
                "hint_id": "prefer_bounded_read_or_identifier_search",
                "reason": "Slow reads target source or otherwise unclassified files without a more specific owner hint.",
                "preferred_next": DOCUMENT_READ_QUOTE_COMMAND,
                "owner_surface": "known_path_bounded_read",
                "quote_surface": DOCUMENT_READ_QUOTE_COMMAND,
                "replacement_commands": [
                    DOCUMENT_READ_QUOTE_COMMAND,
                    "rg -n '<symbol-or-error>' <known-path-or-root>",
                    "sed -n '<start>,<end>p' <known-path>",
                    ARTIFACT_DISCOVERY_OWNER_SURFACE,
                    "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
                ],
                "privacy_boundary": (
                    "bounded reads expose only the selected symbol, line range, or metadata row; "
                    "full file bodies remain a deliberate drilldown"
                ),
            })
    elif kind == "exec_session_io":
        if tag_counts.get("exec_session_poll") or tag_counts.get("configured_wait"):
            hints.append({
                "hint_id": "inspect_preceding_exec_or_add_status_surface",
                "reason": "Slow spans wait on an existing Codex exec session rather than starting a new shell command.",
                "preferred_next": PROCESS_SUMMARY_EXEC_SESSION_QUOTE_COMMAND,
                "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
                "quote_surface": PROCESS_SUMMARY_EXEC_SESSION_QUOTE_COMMAND,
                "replacement_commands": [
                    PROCESS_SUMMARY_EXEC_SESSION_QUOTE_COMMAND,
                    PROCESS_SUMMARY_QUOTE_COMMAND,
                    PROCESS_SUMMARY_OWNER_SURFACE,
                    PROCESS_TRACE_OWNER_SURFACE,
                    PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
                ],
                "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
            })
    elif kind in {"task_tool", "unknown_tool"}:
        exact_quote_command = (
            PROCESS_SUMMARY_UNKNOWN_TOOL_QUOTE_COMMAND
            if kind == "unknown_tool"
            else PROCESS_SUMMARY_TASK_TOOL_QUOTE_COMMAND
        )
        hints.append({
            "hint_id": "replace_long_tool_wait_with_process_summary",
            "reason": "Slow spans come from tool/runtime waits without a stable shell command to optimize directly.",
            "preferred_next": exact_quote_command,
            "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
            "quote_surface": PROCESS_SUMMARY_QUOTE_COMMAND,
            "replacement_commands": [
                exact_quote_command,
                PROCESS_SUMMARY_OWNER_SURFACE,
                PROCESS_SUMMARY_QUOTE_COMMAND,
                PROCESS_TRACE_OWNER_SURFACE,
                PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            ],
            "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
        })
    return hints


def _bottleneck_actionability(kind: str, examples: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    example_rows = [example for example in examples if isinstance(example, Mapping)]
    tag_counts: Counter[str] = Counter()
    for example in example_rows:
        tag_counts.update(str(tag) for tag in example.get("command_shape_tags") or [])
    if kind == "exec_session_io" and example_rows:
        wait_like = tag_counts.get("exec_session_poll", 0) or tag_counts.get("configured_wait", 0)
        if wait_like >= max(1, len(example_rows) // 2):
            return {
                "actionability_class": "wait_state_polling",
                "optimization_priority_score": 35,
                "ranking_note": (
                    "Configured exec-session waits measure an already-running operation; inspect the "
                    "owning process/session before treating the wait itself as optimization work."
                ),
                "preferred_next": PROCESS_SUMMARY_EXEC_SESSION_QUOTE_COMMAND,
            }
    if kind == "task_tool":
        return {
            "actionability_class": "external_tool_wait",
            "optimization_priority_score": 55,
            "ranking_note": (
                "Tool/runtime waits are real latency but usually need a process/session summary before "
                "a stable source patch target exists."
            ),
            "preferred_next": PROCESS_SUMMARY_OWNER_SURFACE,
        }
    return {
        "actionability_class": "directly_actionable",
        "optimization_priority_score": 100,
    }


def _bottleneck_summary_sort_key(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(row.get("optimization_priority_score") or 0),
        int(row.get("p95_ms") or 0),
        int(row.get("slow_count") or 0),
        int(row.get("total_duration_ms") or 0),
    )


_CONTEXT_YIELD_MOTIF_META: dict[str, dict[str, Any]] = {
    "metadata_cargo": {
        "owner_surface": "tools/meta/factory/work_ledger.py or tools/meta/control/mission_transaction_preflight.py",
        "existing_route": "./repo-python tools/meta/factory/work_ledger.py session-preflight <same args>",
        "candidate_patch": "Use compact preflight as the owner status route; reserve --full for selected drilldowns and keep handle rows bounded with preview/hash/byte-count/drilldown.",
        "safety_gate": "session id, overlap path, mutation/referenced paths, updated_at, recent command preview, and full-title drilldown remain visible",
        "disconfirming_check": "Rerun the overlap-producing compact preflight and confirm it stays under the large-packet threshold without long title/prompt fields per row.",
    },
    "raw_global_diff": {
        "owner_surface": "system/lib/git_state_snapshot.py",
        "existing_route": "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
        "candidate_patch": "Route first-contact diff review through the diff-review packet before raw patch bodies enter active context.",
        "safety_gate": "raw hunks stay available through scoped ./repo-git diff -- <path>",
        "disconfirming_check": "Confirm the command was measured-but-not-printed or already scoped to a selected path.",
    },
    "entry_over_admission": {
        "owner_surface": "system/lib/kernel/commands/comprehension_snapshot.py",
        "existing_route": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
        "candidate_patch": "Move non-decisive first-contact sections behind high-scent drilldowns while preserving route lease and safety fields.",
        "safety_gate": "selected lane, first legal action, banned routes, source-coupling/currentness, and omission receipts remain present",
        "disconfirming_check": "Cold agent can still identify lane, unsafe action, next legal action, and recovery route.",
    },
    "diagnostic_packet_over_budget": {
        "owner_surface": "system/lib/kernel/commands/navigate.py",
        "existing_route": "./repo-python kernel.py --process-bottlenecks --force",
        "candidate_patch": "Add a compact card/lens or owner packet for the diagnostic section that dominates output.",
        "safety_gate": "diagnostic preserves the actionable bottleneck, owner route, and validation command",
        "disconfirming_check": "A smaller packet does not force broad search or full trace reads to recover the same diagnosis.",
    },
    "context_pack_selected_rows": {
        "owner_surface": "system/lib/kernel/commands/comprehension_snapshot.py",
        "existing_route": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
        "candidate_patch": "Tighten selected-row admission or add banded drilldowns for repeated context-pack sections.",
        "safety_gate": "context pack still exposes selected source authority, route, and follow-up commands",
        "disconfirming_check": "Selected rows are genuinely needed for the immediate task, not just adjacent context.",
    },
    "tool_result_carryover": {
        "owner_surface": PROCESS_SUMMARY_OWNER_SURFACE,
        "existing_route": PROCESS_SUMMARY_OWNER_SURFACE,
        "candidate_patch": "Replace large task/tool-result file rereads with compact process/session/status packets and explicit reopen routes.",
        "safety_gate": "the raw result remains refetchable by session id, command, or owner status route",
        "disconfirming_check": "The file read is the only source of non-recomputable evidence needed for the next action.",
    },
    "raw_body_before_selection": {
        "owner_surface": ARTIFACT_DISCOVERY_OWNER_SURFACE,
        "existing_route": ARTIFACT_DISCOVERY_OWNER_SURFACE,
        "candidate_patch": "Replace broad raw shell discovery with owner inventory/status packets before opening bodies.",
        "safety_gate": "the inventory emits enough identity, size, suffix, path, and route scent to choose the next file or row",
        "disconfirming_check": "The command is already a precise path read or scoped hunk required for semantic review.",
    },
    "retrieval_over_recall": {
        "owner_surface": DOCUMENT_READ_OWNER_SURFACE,
        "existing_route": DOCUMENT_READ_OWNER_SURFACE,
        "candidate_patch": "Use a card, row, paper-module section, or bounded range before full prose/file reads.",
        "safety_gate": "the selected route preserves authority and can reopen the exact document section",
        "disconfirming_check": "The whole document is the artifact under direct edit or review.",
    },
    "diff_file_overlap": {
        "owner_surface": "system/lib/agent_execution_trace.py",
        "existing_route": "./repo-python kernel.py --process-bottlenecks --force",
        "candidate_patch": "Warn when a session carries both scoped diff hunks and full file reads for the same path.",
        "safety_gate": "warning must not forbid scoped hunk review when patch-body semantics are required",
        "disconfirming_check": "File read and diff hunk are separated by an edit that made both views necessary.",
    },
}

_CONTEXT_YIELD_GOVERNANCE_STATUSES = (
    "ungoverned",
    "governed_route_available_but_not_used",
    "accepted_required_context",
    "false_positive",
    "stale_pre_repair",
    "needs_owner_patch",
)
_CONTEXT_YIELD_ACTIONABLE_STATUSES = (
    "ungoverned",
    "governed_route_available_but_not_used",
    "needs_owner_patch",
)
_CONTEXT_YIELD_TINY_OUTPUT_BYTES = 1024
_CONTEXT_YIELD_SCOPED_ACCEPTED_BYTES = 4096
_CONTEXT_YIELD_BOUNDED_DIAGNOSTIC_ACCEPTED_BYTES = 48_000
_CONTEXT_YIELD_BOUNDED_PREFLIGHT_ACCEPTED_BYTES = _CONTEXT_YIELD_BOUNDED_DIAGNOSTIC_ACCEPTED_BYTES


def _context_yield_motif_score(active_bytes: int, span_count: int) -> str:
    if active_bytes >= 1_000_000 or span_count >= 20:
        return "high"
    if active_bytes >= 128_000 or span_count >= 5:
        return "medium"
    return "low"


def _example_preview(example: Mapping[str, Any]) -> dict[str, Any]:
    return _summary_drop_none(
        {
            "session_id": example.get("session_id"),
            "span_id": example.get("span_id"),
            "action_kind": example.get("action_kind"),
            "normalized_command_preview": _truncate(str(example.get("normalized_command") or ""), 180)
            if example.get("normalized_command")
            else None,
            "target_paths": list(example.get("target_paths") or [])[:3],
            "output_byte_count": _summary_int(example.get("output_byte_count")),
            "command_shape_tags": list(example.get("command_shape_tags") or [])[:8],
            "start_ts": example.get("start_ts"),
            "end_ts": example.get("end_ts"),
            "sequence_index": example.get("sequence_index"),
        }
    )


def _context_yield_motifs_for_example(example: Mapping[str, Any]) -> list[str]:
    kind = str(example.get("action_kind") or "")
    command = str(example.get("normalized_command") or "")
    lower = command.lower()
    output_bytes = _summary_int(example.get("output_byte_count"))
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    motifs: list[str] = []
    if "global_raw_diff" in tags:
        motifs.append("raw_global_diff")
    if "git_state_shell_chain" in tags:
        motifs.append("raw_body_before_selection")
    if "raw_search_scan" in tags or "raw_find_scan" in tags:
        motifs.append("raw_body_before_selection")
    if "entry_packet" in tags and output_bytes >= CONTEXT_YIELD_ENTRY_PACKET_ALERT_BYTES:
        motifs.append("entry_over_admission")
    if "context_pack" in tags and output_bytes >= CONTEXT_YIELD_LARGE_OUTPUT_BYTES:
        motifs.append("context_pack_selected_rows")
    if (
        ("navigation_metabolism_packet" in tags or "process_diagnostic_packet" in tags)
        and output_bytes >= CONTEXT_YIELD_LARGE_OUTPUT_BYTES
    ):
        motifs.append("diagnostic_packet_over_budget")
    if "task_output_file" in tags or "tool_result_file" in tags:
        motifs.append("tool_result_carryover")
    if kind == "read_file" and "document_read" in tags and output_bytes >= CONTEXT_YIELD_LARGE_OUTPUT_BYTES:
        motifs.append("retrieval_over_recall")
    preflight_command = bool(
        {"preflight_full_drilldown", "preflight_compact_owner_status"}.intersection(tags)
        or _is_work_ledger_session_preflight_command(lower)
        or _is_mission_transaction_preflight_command(lower)
    )
    preflight_full_drilldown = (
        "preflight_full_drilldown" in tags
        or (preflight_command and "--full" in lower)
    )
    preflight_over_budget_compact = (
        preflight_command
        and not preflight_full_drilldown
        and output_bytes >= CONTEXT_YIELD_LARGE_OUTPUT_BYTES
    )
    if (
        (preflight_full_drilldown and output_bytes >= 4000)
        or preflight_over_budget_compact
        or (
            output_bytes >= CONTEXT_YIELD_LARGE_OUTPUT_BYTES
            and "observed_path_overlaps" in lower
        )
    ):
        motifs.append("metadata_cargo")
    seen: list[str] = []
    for motif in motifs:
        if motif not in seen:
            seen.append(motif)
    return seen


def _context_yield_route_used(motif: str, example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    if motif == "raw_body_before_selection":
        return (
            "action_quote.py" in command and "artifact_discovery_inventory" in command
        ) or "--artifact-discovery-inventory" in command
    if motif == "raw_global_diff":
        return "diff_review_context_packet" in tags or (
            "git_state_snapshot.py" in command and "--diff-review" in command
        )
    if motif == "tool_result_carryover":
        return "--process-summary" in command or "--process-trace" in command
    if motif == "diagnostic_packet_over_budget":
        return _context_yield_bounded_diagnostic_packet(example)
    if motif == "context_pack_selected_rows":
        return _context_yield_bounded_context_pack_packet(example)
    if motif == "metadata_cargo":
        return _context_yield_bounded_preflight_packet(example)
    if motif in {"entry_over_admission", "context_pack_selected_rows", "diagnostic_packet_over_budget"}:
        return False
    return False


def _context_yield_bounded_context_pack_packet(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    output_bytes = _summary_int(example.get("output_byte_count"))
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    return (
        "context_pack" in tags
        and "--context-pack" in command
        and output_bytes <= _CONTEXT_YIELD_BOUNDED_DIAGNOSTIC_ACCEPTED_BYTES
    )


def _context_yield_bounded_preflight_packet(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    output_bytes = _summary_int(example.get("output_byte_count"))
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    preflight_command = bool(
        {"preflight_compact_owner_status"}.intersection(tags)
        or _is_work_ledger_session_preflight_command(command)
        or _is_mission_transaction_preflight_command(command)
    )
    return (
        preflight_command
        and "--full" not in command
        and "preflight_full_drilldown" not in tags
        and output_bytes <= _CONTEXT_YIELD_BOUNDED_PREFLIGHT_ACCEPTED_BYTES
    )


def _context_yield_bounded_diagnostic_packet(example: Mapping[str, Any]) -> bool:
    command = str(example.get("normalized_command") or "").lower()
    output_bytes = _summary_int(example.get("output_byte_count"))
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    if output_bytes > _CONTEXT_YIELD_BOUNDED_DIAGNOSTIC_ACCEPTED_BYTES:
        return False
    if "navigation_metabolism_packet" in tags and "--navigation-metabolism" in command:
        return True
    if "process_diagnostic_packet" not in tags:
        return False
    if "--process-bottlenecks" in command:
        return True
    if "--process-audit" in command and "--full" not in command:
        return True
    if "--session-diagnostics" in command and "--full" not in command:
        return True
    return False


def _context_yield_governance_status(
    motif: str,
    example: Mapping[str, Any],
    *,
    route_available: bool,
) -> str:
    output_bytes = _summary_int(example.get("output_byte_count"))
    target_paths = [str(path) for path in example.get("target_paths") or [] if str(path)]
    tags = {str(tag) for tag in example.get("command_shape_tags") or []}
    if _context_yield_route_used(motif, example):
        return "accepted_required_context"
    if not route_available:
        return "ungoverned"
    if motif == "raw_body_before_selection":
        if output_bytes < _CONTEXT_YIELD_TINY_OUTPUT_BYTES and not target_paths:
            return "false_positive"
        if target_paths and output_bytes < _CONTEXT_YIELD_SCOPED_ACCEPTED_BYTES:
            return "accepted_required_context"
        if tags.intersection({"raw_search_scan", "raw_find_scan", "git_state_shell_chain"}):
            return "governed_route_available_but_not_used"
        return "needs_owner_patch"
    if motif == "raw_global_diff":
        return "governed_route_available_but_not_used" if "global_raw_diff" in tags else "accepted_required_context"
    if motif == "retrieval_over_recall" and output_bytes >= CONTEXT_YIELD_LARGE_OUTPUT_BYTES:
        return "governed_route_available_but_not_used"
    if motif == "tool_result_carryover":
        return "governed_route_available_but_not_used" if route_available else "ungoverned"
    if motif in {
        "metadata_cargo",
        "entry_over_admission",
        "context_pack_selected_rows",
        "diagnostic_packet_over_budget",
        "diff_file_overlap",
    }:
        return "needs_owner_patch"
    return "governed_route_available_but_not_used"


def _context_yield_status_counts_payload(counts: Mapping[str, Any], *, fallback_span_count: int) -> dict[str, int]:
    counter = Counter({str(key): int(value or 0) for key, value in dict(counts).items()})
    if fallback_span_count and not any(counter.get(status, 0) for status in _CONTEXT_YIELD_GOVERNANCE_STATUSES):
        counter["needs_owner_patch"] = fallback_span_count
    return {status: int(counter.get(status, 0)) for status in _CONTEXT_YIELD_GOVERNANCE_STATUSES}


def _context_yield_status_bytes_payload(
    counts: Mapping[str, Any],
    *,
    fallback_active_bytes: int,
) -> dict[str, int]:
    counter = Counter({str(key): int(value or 0) for key, value in dict(counts).items()})
    if fallback_active_bytes and not any(counter.get(status, 0) for status in _CONTEXT_YIELD_GOVERNANCE_STATUSES):
        counter["needs_owner_patch"] = fallback_active_bytes
    return {status: int(counter.get(status, 0)) for status in _CONTEXT_YIELD_GOVERNANCE_STATUSES}


def _context_yield_actionable_status_count(status_counts: Mapping[str, int]) -> int:
    return sum(int(status_counts.get(status) or 0) for status in _CONTEXT_YIELD_ACTIONABLE_STATUSES)


def _context_yield_actionable_status_bytes(status_bytes: Mapping[str, int]) -> int:
    return sum(int(status_bytes.get(status) or 0) for status in _CONTEXT_YIELD_ACTIONABLE_STATUSES)


def _context_yield_route_gap(status_counts: Mapping[str, int], *, route_available: bool) -> str:
    if not route_available:
        return "no_existing_route_recorded"
    if int(status_counts.get("governed_route_available_but_not_used") or 0):
        return "route_available_but_not_used_for_active_examples"
    if int(status_counts.get("needs_owner_patch") or 0):
        return "owner_patch_needed_after_status_classification"
    if int(status_counts.get("accepted_required_context") or 0) or int(status_counts.get("false_positive") or 0):
        return "examples_already_scoped_or_low_cost"
    if int(status_counts.get("stale_pre_repair") or 0):
        return "examples_precede_configured_repair_boundary"
    return "no_actionable_gap"


def _context_yield_decision(
    *,
    motif: str,
    status_counts: Mapping[str, int],
    meta: Mapping[str, Any],
    active_bytes: int,
    actionable_active_bytes: int,
    span_count: int,
    actionable_span_count: int,
) -> dict[str, Any]:
    actionable_count = _context_yield_actionable_status_count(status_counts)
    patch_owner_surface = meta.get("owner_surface") if actionable_count else None
    no_source_exception = actionable_count == 0
    if int(status_counts.get("governed_route_available_but_not_used") or 0):
        why = "existing route is recorded but high-cost examples still enter active context before that route is used"
    elif int(status_counts.get("needs_owner_patch") or 0):
        why = "examples require a smaller owner patch before this motif can retire"
    elif int(status_counts.get("ungoverned") or 0):
        why = "examples do not have a recorded owner route"
    elif no_source_exception:
        why = "examples are scoped, low-cost, stale, or accepted and should not drive an owner patch"
    else:
        why = "status distribution is inconclusive"
    return {
        "patch_owner_surface": patch_owner_surface,
        "no_source_exception": no_source_exception,
        "why_this_is_next": why,
        "rank_basis": {
            "motif": motif,
            "actionable_active_bytes": actionable_active_bytes,
            "actionable_span_count": actionable_span_count,
            "active_bytes": active_bytes,
            "span_count": span_count,
            "sort_order": "actionable_active_bytes_then_total_active_bytes_then_span_count",
        },
    }


def _counter_payload(counter: Mapping[str, Any], *, limit: int = 8) -> dict[str, int]:
    normalized = Counter({str(key): int(value or 0) for key, value in dict(counter).items() if str(key)})
    return {key: int(value) for key, value in normalized.most_common(limit)}


def _context_yield_cluster_payload(raw_row: Mapping[str, Any], status: str) -> dict[str, Any]:
    tag_counts = raw_row.get("governance_status_tag_counts") or {}
    action_counts = raw_row.get("governance_status_action_counts") or {}
    target_counts = raw_row.get("governance_status_target_counts") or {}
    return {
        "status": status,
        "tag_counts": _counter_payload(tag_counts.get(status) or {}),
        "action_kind_counts": _counter_payload(action_counts.get(status) or {}),
        "targeting": _counter_payload(target_counts.get(status) or {}),
    }


def _context_yield_scope_candidate(examples: Iterable[Mapping[str, Any]]) -> str | None:
    actionable_statuses = {
        "ungoverned",
        "governed_route_available_but_not_used",
        "needs_owner_patch",
    }
    example_rows = [example for example in examples if isinstance(example, Mapping)]
    preferred_rows = [
        example
        for example in example_rows
        if str(example.get("governance_status") or "") in actionable_statuses
    ]
    for example in preferred_rows or example_rows:
        for path in example.get("target_paths") or []:
            scope = str(path or "").strip()
            if _context_yield_valid_scope(scope):
                return scope
    return None


def _context_yield_valid_scope(scope: str) -> bool:
    return bool(
        scope
        and scope not in {".", "./"}
        and "<" not in scope
        and ">" not in scope
        and "\n" not in scope
    )


def _context_yield_scope_candidate_from_counts(raw_row: Mapping[str, Any], status: str) -> str | None:
    counts_by_status = raw_row.get("governance_status_path_counts")
    if not isinstance(counts_by_status, Mapping):
        return None
    path_counts = counts_by_status.get(status)
    if not isinstance(path_counts, Mapping):
        return None
    ranked_paths = sorted(
        ((str(path), int(count or 0)) for path, count in path_counts.items()),
        key=lambda item: (-item[1], item[0]),
    )
    for path, _count in ranked_paths:
        if _context_yield_valid_scope(path):
            return path
    return None


def _concrete_context_yield_route(route: Any, scope: str | None) -> str | None:
    route_text = str(route or "").strip()
    if not route_text or not scope:
        return None
    quoted_scope = shlex.quote(scope)
    for placeholder in ("<term-or-root>", "<host-path-or-term>", "<path-or-owner>"):
        if placeholder in route_text:
            return route_text.replace(placeholder, quoted_scope)
    return None


def _context_yield_steering(
    *,
    motif: str,
    status_counts: Mapping[str, int],
    meta: Mapping[str, Any],
    raw_row: Mapping[str, Any],
) -> dict[str, Any]:
    applies_to_status = "governed_route_available_but_not_used"
    does_not_apply_to = [
        "accepted_required_context",
        "false_positive",
        "stale_pre_repair",
    ]
    if motif == "raw_body_before_selection":
        accepted_guard = (
            "Scoped low-output rg/find on selected files remains accepted; tiny-output discovery "
            "with no raw body remains a false positive, not a route-use failure."
        )
        scope_narrowing = (
            "Inventory with object-specific terms or path fragments instead of full prose clauses."
        )
    elif motif == "raw_global_diff":
        accepted_guard = "Scoped path diff after path/risk/owner selection remains accepted."
        scope_narrowing = None
    elif motif == "tool_result_carryover":
        accepted_guard = (
            "Direct task/tool-result file reads remain accepted only when the raw body is the "
            "non-recomputable evidence needed for the next action; otherwise use process-summary first."
        )
        scope_narrowing = None
    else:
        accepted_guard = "Owner-route steering applies only to classified high-cost route-not-used examples."
        scope_narrowing = None
    actionable_count = int(status_counts.get(applies_to_status) or 0)
    command_shape_clusters = _context_yield_cluster_payload(raw_row, applies_to_status)
    payload = {
        "point_of_use_surface": "./repo-python kernel.py --process-bottlenecks --force",
        "replacement_route": meta.get("existing_route"),
        "applies_to_status": applies_to_status,
        "applies_to_count": actionable_count,
        "does_not_apply_to": does_not_apply_to,
        "accepted_case_guard": accepted_guard,
        "post_repair_check": "./repo-python kernel.py --process-bottlenecks --force --after <repair_time>",
        "command_shape_clusters": command_shape_clusters,
    }
    if motif == "raw_body_before_selection":
        quote_routes: list[str] = []
        action_kind_counts = command_shape_clusters.get("action_kind_counts") or {}
        if action_kind_counts.get("bash_grep"):
            quote_routes.append(BASH_GREP_QUOTE_COMMAND)
        if action_kind_counts.get("bash_find"):
            quote_routes.append(BASH_FIND_QUOTE_COMMAND)
        if quote_routes:
            payload["preferred_quote_route"] = quote_routes[0]
            payload["quote_routes"] = quote_routes
        payload["pre_action_card"] = {
            "status": "route_first_for_broad_discovery",
            "before": "raw recursive rg/find over multiple roots or raw artifact trees",
            "first_route": quote_routes[0] if quote_routes else meta.get("existing_route"),
            "fallback_route": meta.get("existing_route"),
            "scope_rule": (
                "Use a stable object name, slug, path fragment, or rare code term; "
                "drop glue words and prose clauses."
            ),
            "accepted_exception": "Known-file scoped rg/find with low output remains acceptable.",
        }
    scope_hint = _context_yield_scope_candidate(raw_row.get("examples") or [])
    if not scope_hint:
        scope_hint = _context_yield_scope_candidate_from_counts(raw_row, applies_to_status)
    if scope_hint:
        concrete_replacement_route = _concrete_context_yield_route(
            payload.get("replacement_route"),
            scope_hint,
        )
        concrete_preferred_quote_route = _concrete_context_yield_route(
            payload.get("preferred_quote_route"),
            scope_hint,
        )
        pre_action_card = (
            dict(payload.get("pre_action_card"))
            if isinstance(payload.get("pre_action_card"), Mapping)
            else None
        )
        concrete_first_route = (
            _concrete_context_yield_route(pre_action_card.get("first_route"), scope_hint)
            if pre_action_card
            else None
        )
        if concrete_replacement_route:
            payload["concrete_replacement_route"] = concrete_replacement_route
        if concrete_preferred_quote_route:
            payload["concrete_preferred_quote_route"] = concrete_preferred_quote_route
        if pre_action_card and concrete_first_route:
            pre_action_card["concrete_first_route"] = concrete_first_route
            payload["pre_action_card"] = pre_action_card
        if concrete_replacement_route or concrete_preferred_quote_route or concrete_first_route:
            payload["scope_hint"] = scope_hint
    if scope_narrowing:
        payload["scope_narrowing"] = scope_narrowing
    return payload


def _compute_context_yield_attribution(
    *,
    aggregate_spans: list[Mapping[str, Any]],
    session_rows: list[Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    motif_rows: dict[str, dict[str, Any]] = {}
    scoped_diff_paths: dict[str, set[str]] = defaultdict(set)
    read_paths: dict[str, set[str]] = defaultdict(set)
    path_examples: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)

    for example in aggregate_spans:
        session_id = str(example.get("session_id") or "")
        paths = [str(path) for path in example.get("target_paths") or [] if str(path)]
        tags = {str(tag) for tag in example.get("command_shape_tags") or []}
        if "scoped_diff_hunk" in tags:
            scoped_diff_paths[session_id].update(paths)
            for path in paths:
                path_examples[(session_id, path)].append(example)
        if str(example.get("action_kind") or "") == "read_file":
            read_paths[session_id].update(paths)
            for path in paths:
                path_examples[(session_id, path)].append(example)
        for motif in _context_yield_motifs_for_example(example):
            meta = _CONTEXT_YIELD_MOTIF_META.get(motif, {})
            route_available = bool(meta.get("existing_route"))
            governance_status = _context_yield_governance_status(
                motif,
                example,
                route_available=route_available,
            )
            row = motif_rows.setdefault(
                motif,
                {
                    "motif": motif,
                    "active_bytes": 0,
                    "span_count": 0,
                    "session_ids": set(),
                    "examples": [],
                    "governance_status_counts": Counter(),
                    "governance_status_bytes": Counter(),
                    "governance_status_tag_counts": defaultdict(Counter),
                    "governance_status_action_counts": defaultdict(Counter),
                    "governance_status_target_counts": defaultdict(Counter),
                    "governance_status_path_counts": defaultdict(Counter),
                    "owner_route_used_count": 0,
                    "oldest_example_at": None,
                    "newest_example_at": None,
                },
            )
            output_byte_count = _summary_int(example.get("output_byte_count"))
            row["active_bytes"] = int(row.get("active_bytes") or 0) + output_byte_count
            row["span_count"] = int(row.get("span_count") or 0) + 1
            row["session_ids"].add(str(example.get("session_id") or ""))
            row["governance_status_counts"][governance_status] += 1
            row["governance_status_bytes"][governance_status] += output_byte_count
            row["governance_status_action_counts"][governance_status][
                str(example.get("action_kind") or "unknown")
            ] += 1
            target_bucket = "target_paths_present" if paths else "no_target_paths"
            row["governance_status_target_counts"][governance_status][target_bucket] += 1
            for path in paths:
                row["governance_status_path_counts"][governance_status][path] += 1
            for tag in sorted(tags) or ["untagged"]:
                row["governance_status_tag_counts"][governance_status][tag] += 1
            if _context_yield_route_used(motif, example):
                row["owner_route_used_count"] = int(row.get("owner_route_used_count") or 0) + 1
            example_ts = str(example.get("end_ts") or example.get("start_ts") or "")
            if example_ts:
                oldest = row.get("oldest_example_at")
                newest = row.get("newest_example_at")
                row["oldest_example_at"] = min(str(oldest), example_ts) if oldest else example_ts
                row["newest_example_at"] = max(str(newest), example_ts) if newest else example_ts
            if len(row["examples"]) < 3:
                preview = _example_preview(example)
                preview["governance_status"] = governance_status
                row["examples"].append(preview)

    overlap_examples: list[dict[str, Any]] = []
    overlap_bytes = 0
    for session_id, diff_paths in scoped_diff_paths.items():
        overlap_paths = sorted(path for path in diff_paths if path in read_paths.get(session_id, set()))
        for path in overlap_paths[:5]:
            examples = path_examples.get((session_id, path), [])
            overlap_bytes += sum(_summary_int(ex.get("output_byte_count")) for ex in examples)
            overlap_examples.append(
                {
                    "session_id": session_id,
                    "path": path,
                    "span_count": len(examples),
                    "active_bytes": sum(_summary_int(ex.get("output_byte_count")) for ex in examples),
                }
            )
    if overlap_examples:
        motif_rows["diff_file_overlap"] = {
            "motif": "diff_file_overlap",
            "active_bytes": overlap_bytes,
            "span_count": sum(int(row.get("span_count") or 0) for row in overlap_examples),
            "session_ids": {str(row.get("session_id") or "") for row in overlap_examples},
            "examples": overlap_examples[:3],
        }

    rows: list[dict[str, Any]] = []
    for motif, raw_row in motif_rows.items():
        meta = _CONTEXT_YIELD_MOTIF_META.get(motif, {})
        active_bytes = int(raw_row.get("active_bytes") or 0)
        span_count = int(raw_row.get("span_count") or 0)
        session_ids = sorted(str(sid) for sid in raw_row.get("session_ids") or [] if str(sid))
        governance_status_counts = _context_yield_status_counts_payload(
            raw_row.get("governance_status_counts") or {},
            fallback_span_count=span_count,
        )
        governance_status_bytes = _context_yield_status_bytes_payload(
            raw_row.get("governance_status_bytes") or {},
            fallback_active_bytes=active_bytes,
        )
        actionable_span_count = _context_yield_actionable_status_count(governance_status_counts)
        actionable_active_bytes = _context_yield_actionable_status_bytes(governance_status_bytes)
        owner_route_used_count = int(raw_row.get("owner_route_used_count") or 0)
        route_available = bool(meta.get("existing_route"))
        route_gap = _context_yield_route_gap(governance_status_counts, route_available=route_available)
        rows.append(
            {
                "motif": motif,
                "active_bytes": active_bytes,
                "actionable_active_bytes": actionable_active_bytes,
                "non_actionable_active_bytes": max(active_bytes - actionable_active_bytes, 0),
                "span_count": span_count,
                "actionable_span_count": actionable_span_count,
                "session_count": len(session_ids),
                "session_ids": session_ids[:5],
                "repetition_count": span_count,
                "owner_surface": meta.get("owner_surface"),
                "existing_route": meta.get("existing_route"),
                "candidate_patch": meta.get("candidate_patch"),
                "safety_gate": meta.get("safety_gate"),
                "disconfirming_check": meta.get("disconfirming_check"),
                "governance_status_counts": governance_status_counts,
                "governance_status_bytes": governance_status_bytes,
                "owner_coverage": {
                    "existing_route": meta.get("existing_route"),
                    "route_available": route_available,
                    "route_used": owner_route_used_count > 0,
                    "route_used_count": owner_route_used_count,
                    "route_not_used_count": max(span_count - owner_route_used_count, 0),
                    "route_gap": route_gap,
                },
                "recency_boundary": {
                    "post_repair_only": None,
                    "oldest_example_at": raw_row.get("oldest_example_at"),
                    "newest_example_at": raw_row.get("newest_example_at"),
                    "stale_pre_repair_count": governance_status_counts["stale_pre_repair"],
                    "repair_epoch_status": "not_configured",
                },
                "decision": _context_yield_decision(
                    motif=motif,
                    status_counts=governance_status_counts,
                    meta=meta,
                    active_bytes=active_bytes,
                    actionable_active_bytes=actionable_active_bytes,
                    span_count=span_count,
                    actionable_span_count=actionable_span_count,
                ),
                "steering": _context_yield_steering(
                    motif=motif,
                    status_counts=governance_status_counts,
                    meta=meta,
                    raw_row=raw_row,
                ),
                "next_wave_score": _context_yield_motif_score(actionable_active_bytes, actionable_span_count),
                "examples": list(raw_row.get("examples") or [])[:3],
                "omission_receipt": {
                    "omitted": ["raw command output bodies", "raw file bodies", "raw private prompt bodies"],
                    "reason": "Context-yield attribution ranks observable metadata, byte counts, tags, paths, and owner routes without replaying raw bodies.",
                    "drilldown": PROCESS_TRACE_OWNER_SURFACE,
                },
            }
        )
    rows.sort(
        key=lambda row: (
            int(row.get("actionable_active_bytes") or 0),
            int(row.get("active_bytes") or 0),
            int(row.get("span_count") or 0),
        ),
        reverse=True,
    )
    top_actionable_row = next((row for row in rows if int(row.get("actionable_active_bytes") or 0) > 0), None)
    top_total_row = rows[0] if rows else None
    known = {
        "entry_over_admission": any(row.get("motif") == "entry_over_admission" for row in rows),
        "raw_global_diff": any(row.get("motif") == "raw_global_diff" for row in rows),
        "metadata_cargo": any(row.get("motif") == "metadata_cargo" for row in rows),
    }
    return {
        "kind": "context_yield_attribution_packet",
        "schema_version": CONTEXT_YIELD_ATTRIBUTION_SCHEMA_VERSION,
        "generated_at": generated_at,
        "summary": {
            "session_count": len(session_rows),
            "span_count": len(aggregate_spans),
            "motif_count": len(rows),
            "raw_bodies_omitted": True,
            "known_motif_coverage": known,
            "top_motif": top_actionable_row["motif"] if top_actionable_row else None,
            "top_active_bytes": top_actionable_row["active_bytes"] if top_actionable_row else 0,
            "top_actionable_bytes": top_actionable_row["actionable_active_bytes"] if top_actionable_row else 0,
            "top_total_motif": top_total_row["motif"] if top_total_row else None,
            "top_total_active_bytes": top_total_row["active_bytes"] if top_total_row else 0,
            "rank_basis": "actionable_active_bytes_then_total_active_bytes_then_span_count",
        },
        "rows": rows[:10],
        "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
        "next": [
            {
                "command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
                "reason": "Refresh the authoritative trace window before selecting the next context-economy owner patch.",
            },
            {
                "command": PROCESS_TRACE_OWNER_SURFACE,
                "reason": "Open a specific session only after a motif row identifies the needed evidence.",
            },
        ],
    }


def _skipped_context_yield_attribution(
    *,
    aggregate_spans: list[Mapping[str, Any]],
    session_rows: list[Mapping[str, Any]],
    generated_at: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "kind": "context_yield_attribution_packet",
        "schema_version": CONTEXT_YIELD_ATTRIBUTION_SCHEMA_VERSION,
        "generated_at": generated_at,
        "summary": {
            "session_count": len(session_rows),
            "span_count": len(aggregate_spans),
            "motif_count": 0,
            "raw_bodies_omitted": True,
            "known_motif_coverage": {
                "entry_over_admission": False,
                "raw_global_diff": False,
                "metadata_cargo": False,
            },
            "top_motif": None,
            "top_active_bytes": 0,
            "top_actionable_bytes": 0,
            "top_total_motif": None,
            "top_total_active_bytes": 0,
            "rank_basis": "not_computed",
            "computation_status": "skipped",
            "skip_reason": reason,
            "full_payload_command": "./repo-python kernel.py --process-audit",
        },
        "rows": [],
        "privacy_boundary": PROCESS_METADATA_PRIVACY_BOUNDARY,
        "next": [
            {
                "command": "./repo-python kernel.py --process-audit",
                "reason": "Use the full process audit when context-yield attribution rows are required.",
            },
        ],
    }


def _is_grep_shape_tool(tool_name: str) -> bool:
    return tool_name in {"Grep", "Glob"}


def _is_read_shape_tool(tool_name: str) -> bool:
    return tool_name in {"Read", "NotebookRead"}


def _iter_jsonl(path: Path, *, strict: bool = True) -> Iterator[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    if strict:
                        yield loads_json_strict(line, source=f"{path}:{line_number}")
                    else:
                        value = json.loads(line)
                        if isinstance(value, dict):
                            yield value
                except (StrictJsonError, json.JSONDecodeError):
                    continue
    except OSError:
        return


# ---------------------------------------------------------------------------
# Rules registry
# ---------------------------------------------------------------------------
def load_trace_rules(path: Path | None = None) -> dict[str, Any]:
    payload = _safe_read_json(path or TRACE_RULES_PATH)
    if not isinstance(payload, Mapping):
        raise ValueError(f"trace_rules.json not loadable: {path or TRACE_RULES_PATH}")
    return dict(payload)


def _ladder_flags_in_order(rules: Mapping[str, Any]) -> list[str]:
    seq = rules.get("navigation_reference_sequence") or []
    return [str(entry.get("kernel_flag") or "").strip() for entry in seq if isinstance(entry, Mapping) and entry.get("kernel_flag")]


def _all_ladder_flags(rules: Mapping[str, Any]) -> set[str]:
    flags = set(_ladder_flags_in_order(rules))
    flags.update(str(f).strip() for f in (rules.get("kernel_flag_aliases_included_in_ladder") or []) if str(f).strip())
    return flags


# ---------------------------------------------------------------------------
# Claude parser
# ---------------------------------------------------------------------------
def parse_claude_session(
    path: Path,
    *,
    repo_root: Path,
    rules: Mapping[str, Any],
    include_output_previews: bool = True,
    strict_json: bool = True,
    finalize_profile: str = "full",
) -> dict[str, Any] | None:
    session_id = path.stem
    agent = "claude_code"
    repo_root_str = str(repo_root)
    ladder_flags = _all_ladder_flags(rules)
    trunc_cmd = int(((rules.get("observability_boundary") or {}).get("truncate_command_at_chars")) or 2048)
    trunc_err = int(((rules.get("observability_boundary") or {}).get("truncate_error_message_at_chars")) or 512)
    span_cap = int(((rules.get("ingest") or {}).get("per_session_span_cap")) or 2000)

    tool_use_by_id: dict[str, dict[str, Any]] = {}
    pending: list[dict[str, Any]] = []
    spans: list[Span] = []
    cwd_hits = 0
    turn_index = 0
    started_at: str | None = None
    ended_at: str | None = None
    git_branch: str | None = None
    model_counts: Counter[str] = Counter()
    last_record_ts: str | None = None

    for rec in _iter_jsonl(path, strict=strict_json):
        ts = rec.get("timestamp")
        if ts:
            started_at = started_at or ts
            ended_at = ts
            last_record_ts = ts
        cwd = rec.get("cwd")
        if cwd and cwd.startswith(repo_root_str):
            cwd_hits += 1
        git_branch = git_branch or rec.get("gitBranch")
        rtype = rec.get("type")
        if rtype == "user" and rec.get("uuid"):
            turn_index += 1
        msg = rec.get("message") or {}
        model = msg.get("model")
        if model:
            model_counts[model] += 1
        content = msg.get("content") if isinstance(msg.get("content"), list) else None
        if rtype == "assistant" and content:
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                use_id = block.get("id") or ""
                if not use_id:
                    continue
                tool_use_by_id[use_id] = {
                    "record": rec,
                    "block": block,
                    "turn_index": turn_index,
                    "start_ts": ts,
                }
        elif rtype == "user" and content:
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_result":
                    continue
                use_id = block.get("tool_use_id") or ""
                if not use_id or use_id not in tool_use_by_id:
                    continue
                opened = tool_use_by_id.pop(use_id)
                start_ts = opened.get("start_ts") or ts
                end_ts = ts or start_ts
                tool_block = opened.get("block") or {}
                tool_name = str(tool_block.get("name") or "unknown")
                action_kind = _TOOL_ACTION_KIND.get(tool_name, "unknown_tool")
                command = None
                normalized = None
                target_paths: list[str] = []
                kernel_flags: list[str] = []
                edit_summary: dict[str, Any] | None = None
                tool_input = tool_block.get("input") or {}
                if tool_name == "Bash":
                    raw_cmd = (tool_input.get("command") or "")
                    command = _truncate(raw_cmd, trunc_cmd)
                    normalized = _normalize_command(raw_cmd)
                    action_kind = _bash_action_kind(raw_cmd)
                    kernel_flags = _extract_kernel_flags(raw_cmd)
                    target_paths = _extract_target_paths(raw_cmd)
                elif tool_name in {"Read", "Edit", "MultiEdit", "Write", "NotebookEdit"}:
                    p = tool_input.get("file_path") or ""
                    if p:
                        target_paths = [p]
                    if tool_name != "Read":
                        normalized = _normalize_command(f"{tool_name} {' '.join(target_paths)}")
                    edit_summary = _edit_summary_from_claude_input(tool_name, tool_input, target_paths)
                elif tool_name in {"Grep", "Glob"}:
                    pat = tool_input.get("pattern") or ""
                    normalized = _normalize_command(f"{tool_name} {pat}")
                    path_filter = tool_input.get("path")
                    if path_filter:
                        target_paths = [str(path_filter)]
                is_error = bool(block.get("is_error"))
                err_text = None
                output_metrics = _output_metrics_from_value(block.get("content"))
                if is_error:
                    raw_err = block.get("content")
                    if isinstance(raw_err, list):
                        bits = []
                        for piece in raw_err:
                            if isinstance(piece, dict) and isinstance(piece.get("text"), str):
                                bits.append(piece["text"])
                        raw_err = "\n".join(bits)
                    err_text = _truncate(str(raw_err or ""), trunc_err)
                span = Span(
                    span_id=f"{session_id}:{use_id}",
                    agent=agent,
                    session_id=session_id,
                    action_kind=action_kind,
                    start_ts=str(start_ts or ""),
                    end_ts=str(end_ts or start_ts or ""),
                    duration_ms=_duration_ms(start_ts, end_ts or start_ts),
                    outcome="error" if is_error else "ok",
                    sequence_index=len(spans),
                    turn_index=opened.get("turn_index") or turn_index,
                    tool_name=tool_name,
                    command=command,
                    normalized_command=normalized,
                    target_paths=target_paths,
                    kernel_flags=kernel_flags,
                    is_grep_shape=(action_kind in {"bash_grep", "grep_tool", "glob_tool"}) or (tool_name in {"Grep", "Glob"}),
                    is_kernel_shape=action_kind == "kernel_command" or any(flag in ladder_flags for flag in kernel_flags),
                    is_read_shape=tool_name in {"Read", "NotebookRead"},
                    error_message_truncated=err_text,
                    output_byte_count=int(output_metrics.get("output_byte_count") or 0),
                    output_line_count=int(output_metrics.get("output_line_count") or 0),
                    stdout_byte_count=output_metrics.get("stdout_byte_count"),
                    stderr_byte_count=output_metrics.get("stderr_byte_count"),
                    edit_summary=edit_summary,
                    output_preview=(
                        _output_preview_from_value(block.get("content"))
                        if include_output_previews
                        else []
                    ),
                )
                spans.append(span)
                if len(spans) >= span_cap:
                    break
        if len(spans) >= span_cap:
            pending.append({"truncated": True, "reason": "per_session_span_cap"})
            break

    if cwd_hits == 0:
        return None

    finalizer = (
        _finalize_session_bottleneck_rankings
        if finalize_profile == "bottleneck_rankings"
        else _finalize_session
    )
    return finalizer(
        agent=agent,
        session_id=session_id,
        source_path=path,
        spans=spans,
        started_at=started_at,
        ended_at=ended_at,
        git_branch=git_branch,
        model_counts=model_counts,
        rules=rules,
        repo_root=repo_root,
        truncation_notes=pending,
        last_record_ts=last_record_ts,
    )


# ---------------------------------------------------------------------------
# Codex parser
# ---------------------------------------------------------------------------
def parse_codex_session(
    path: Path,
    *,
    repo_root: Path,
    rules: Mapping[str, Any],
    include_output_previews: bool = True,
    parse_output_payloads: bool = True,
    strict_json: bool = True,
    finalize_profile: str = "full",
) -> dict[str, Any] | None:
    session_id = path.stem.replace("rollout-", "")
    agent = "codex"
    repo_root_str = str(repo_root)
    ladder_flags = _all_ladder_flags(rules)
    trunc_cmd = int(((rules.get("observability_boundary") or {}).get("truncate_command_at_chars")) or 2048)
    trunc_err = int(((rules.get("observability_boundary") or {}).get("truncate_error_message_at_chars")) or 512)
    span_cap = int(((rules.get("ingest") or {}).get("per_session_span_cap")) or 2000)

    call_by_id: dict[str, dict[str, Any]] = {}
    spans: list[Span] = []
    started_at: str | None = None
    ended_at: str | None = None
    cwd_hits = 0
    turn_index = 0
    truncation_notes: list[dict[str, Any]] = []
    cwd_from_meta: str | None = None

    for rec in _iter_jsonl(path, strict=strict_json):
        ts = rec.get("timestamp")
        if ts:
            started_at = started_at or ts
            ended_at = ts
        rtype = rec.get("type")
        if rtype == "session_meta":
            payload = rec.get("payload") or {}
            cwd_from_meta = cwd_from_meta or payload.get("cwd")
            if isinstance(cwd_from_meta, str) and cwd_from_meta.startswith(repo_root_str):
                cwd_hits += 1
        elif rtype == "turn_context":
            turn_index += 1
            payload = rec.get("payload") or {}
            cwd_val = payload.get("cwd")
            if isinstance(cwd_val, str) and cwd_val.startswith(repo_root_str):
                cwd_hits += 1
        elif rtype == "response_item":
            payload = rec.get("payload") or {}
            ptype = payload.get("type")
            call_id = payload.get("call_id") or payload.get("id") or ""
            if ptype == "function_call" and call_id:
                call_by_id[call_id] = {
                    "record": rec,
                    "payload": payload,
                    "turn_index": turn_index,
                    "start_ts": ts,
                }
            elif ptype == "function_call_output" and call_id and call_id in call_by_id:
                opened = call_by_id.pop(call_id)
                start_ts = opened.get("start_ts") or ts
                end_ts = ts or start_ts
                call_payload = opened.get("payload") or {}
                fn_name = str(call_payload.get("name") or "function_call")
                args_raw = call_payload.get("arguments") or ""
                if isinstance(args_raw, str):
                    try:
                        parsed = (
                            loads_json_strict(args_raw, source=f"{path}:{call_id}:arguments")
                            if strict_json
                            else json.loads(args_raw)
                        )
                    except (StrictJsonError, json.JSONDecodeError, TypeError):
                        parsed = {"__raw": args_raw}
                    args = parsed if isinstance(parsed, dict) else {"__raw": parsed}
                elif isinstance(args_raw, dict):
                    args = args_raw
                else:
                    args = {}
                raw_cmd = ""
                target_paths: list[str] = []
                edit_summary: dict[str, Any] | None = None
                fn_base = _codex_function_basename(fn_name)
                if fn_base in _CODEX_EXEC_FUNCTION_NAMES:
                    raw_cmd_list = args.get("command") or args.get("cmd") or []
                    if isinstance(raw_cmd_list, list):
                        raw_cmd = " ".join(str(part) for part in raw_cmd_list)
                    else:
                        raw_cmd = str(raw_cmd_list)
                    action_kind = _bash_action_kind(raw_cmd) if raw_cmd else "exec_command"
                    target_paths = _extract_target_paths(raw_cmd)
                elif fn_base == "apply_patch":
                    action_kind = "apply_patch"
                    patch_target = args.get("target") or args.get("path")
                    if patch_target:
                        target_paths = [str(patch_target)]
                    patch_text = _patch_text_from_codex_args(args)
                    patch_paths = _extract_patch_target_paths(patch_text)
                    for patch_path in patch_paths:
                        if patch_path not in target_paths:
                            target_paths.append(patch_path)
                    edit_summary = _edit_summary_from_patch_text(patch_text, target_paths=target_paths)
                    raw_cmd = _normalize_command(f"apply_patch {' '.join(target_paths[:3])}")
                elif fn_base in _CODEX_SESSION_IO_FUNCTION_NAMES:
                    action_kind = "exec_session_io"
                    raw_cmd = _codex_tool_summary(fn_name, args)
                elif fn_name == "multi_tool_use.parallel" or fn_base in _CODEX_TASK_FUNCTION_NAMES:
                    action_kind = "task_tool"
                    raw_cmd = _codex_tool_summary(fn_name, args)
                elif fn_base in _CODEX_MCP_FUNCTION_NAMES:
                    action_kind = "mcp_tool"
                    raw_cmd = _codex_tool_summary(fn_name, args)
                elif fn_base in _CODEX_READ_FUNCTION_NAMES:
                    action_kind = "read_file"
                    raw_cmd = _codex_tool_summary(fn_name, args)
                    path_arg = args.get("path")
                    if path_arg:
                        target_paths = [str(path_arg)]
                else:
                    action_kind = "unknown_tool"
                kernel_flags = _extract_kernel_flags(raw_cmd) if raw_cmd else []
                output_raw = payload.get("output")
                if parse_output_payloads:
                    if isinstance(output_raw, str):
                        try:
                            parsed_output = loads_json_strict(output_raw, source=f"{path}:{call_id}:output")
                        except (StrictJsonError, TypeError):
                            parsed_output = {"content": output_raw}
                        output_payload = (
                            parsed_output if isinstance(parsed_output, dict) else {"content": str(parsed_output)}
                        )
                    elif isinstance(output_raw, dict):
                        output_payload = output_raw
                    else:
                        output_payload = {}
                    output_metrics = _output_metrics_from_codex_output(output_raw, output_payload)
                    output_preview = (
                        _output_preview_from_codex_output(output_raw, output_payload)
                        if include_output_previews
                        else []
                    )
                    is_error = bool(output_payload.get("success") is False) or bool(output_payload.get("is_error"))
                    output_text = output_payload.get("content") if isinstance(output_payload.get("content"), str) else None
                    err_text = _truncate(output_text, trunc_err) if is_error else None
                else:
                    output_metrics = _output_metrics_from_value(output_raw)
                    output_preview = []
                    is_error = False
                    err_text = None
                span = Span(
                    span_id=f"{session_id}:{call_id}",
                    agent=agent,
                    session_id=session_id,
                    action_kind=action_kind,
                    start_ts=str(start_ts or ""),
                    end_ts=str(end_ts or start_ts or ""),
                    duration_ms=_duration_ms(start_ts, end_ts or start_ts),
                    outcome="error" if is_error else "ok",
                    sequence_index=len(spans),
                    turn_index=opened.get("turn_index") or turn_index,
                    tool_name=fn_name,
                    command=_truncate(raw_cmd, trunc_cmd) if raw_cmd else None,
                    normalized_command=_normalize_command(raw_cmd) if raw_cmd else None,
                    target_paths=target_paths,
                    kernel_flags=kernel_flags,
                    is_grep_shape=action_kind in {"bash_grep"},
                    is_kernel_shape=action_kind == "kernel_command" or any(flag in ladder_flags for flag in kernel_flags),
                    is_read_shape=False,
                    error_message_truncated=err_text,
                    output_byte_count=int(output_metrics.get("output_byte_count") or 0),
                    output_line_count=int(output_metrics.get("output_line_count") or 0),
                    stdout_byte_count=output_metrics.get("stdout_byte_count"),
                    stderr_byte_count=output_metrics.get("stderr_byte_count"),
                    edit_summary=edit_summary,
                    output_preview=output_preview,
                )
                spans.append(span)
                if len(spans) >= span_cap:
                    truncation_notes.append({"truncated": True, "reason": "per_session_span_cap"})
                    break

    if cwd_hits == 0 and not spans:
        return None

    finalizer = (
        _finalize_session_bottleneck_rankings
        if finalize_profile == "bottleneck_rankings"
        else _finalize_session
    )
    return finalizer(
        agent=agent,
        session_id=session_id,
        source_path=path,
        spans=spans,
        started_at=started_at,
        ended_at=ended_at,
        git_branch=None,
        model_counts=Counter(),
        rules=rules,
        repo_root=repo_root,
        truncation_notes=truncation_notes,
        last_record_ts=ended_at,
    )


# ---------------------------------------------------------------------------
# Per-session finalize: turns, compliance, anti-pattern detections, digests
# ---------------------------------------------------------------------------
def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    if len(values) == 1:
        return int(values[0])
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return int(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def _compute_route_compliance(spans: list[Span], rules: Mapping[str, Any]) -> dict[str, Any]:
    ladder_order = _ladder_flags_in_order(rules)
    ladder_flags = _all_ladder_flags(rules)
    first_kernel = next((sp.sequence_index for sp in spans if sp.is_kernel_shape), -1)
    first_grep = next((sp.sequence_index for sp in spans if sp.is_grep_shape), -1)
    first_read = next((sp.sequence_index for sp in spans if sp.is_read_shape), -1)
    rung_map = {f: i for i, f in enumerate(ladder_order)}
    ladder_rungs_hit: list[str] = []
    ladder_rungs_order: list[str] = []
    for sp in spans:
        for flag in sp.kernel_flags:
            if flag in ladder_flags:
                if flag not in ladder_rungs_hit:
                    ladder_rungs_hit.append(flag)
                ladder_rungs_order.append(flag)
    deviation_count = 0
    if first_kernel < 0:
        score = 0.0
    else:
        pre_kernel = spans[:first_kernel]
        grep_or_read_before = sum(1 for sp in pre_kernel if sp.is_grep_shape or sp.is_read_shape)
        if grep_or_read_before == 0:
            score = 1.0
        else:
            score = max(0.0, 1.0 - grep_or_read_before * 0.1)
        deviation_count = grep_or_read_before
    max_rung = -1
    for flag in ladder_rungs_hit:
        max_rung = max(max_rung, rung_map.get(flag, -1))
    ladder_position = max_rung + 1 if max_rung >= 0 else 0
    violations: list[dict[str, Any]] = []
    if first_grep >= 0 and (first_kernel < 0 or first_grep < first_kernel):
        violations.append({"rule": "grep_before_kernel", "grep_span": first_grep, "kernel_span": first_kernel})
    return {
        "score": round(score, 3),
        "first_kernel_span_index": first_kernel,
        "first_grep_span_index": first_grep,
        "first_read_span_index": first_read,
        "ladder_position": ladder_position,
        "deviation_count": deviation_count,
        "ladder_rungs_hit": ladder_rungs_hit,
        "ladder_rungs_order": ladder_rungs_order,
        "intended_sequence": ladder_order,
        "violations": violations,
    }


def _compute_bottlenecks(spans: list[Span], rules: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    by_kind: dict[str, list[int]] = defaultdict(list)
    output_by_kind: dict[str, list[int]] = defaultdict(list)
    longest_by_kind: dict[str, list[Span]] = defaultdict(list)
    for sp in spans:
        by_kind[sp.action_kind].append(sp.duration_ms)
        output_by_kind[sp.action_kind].append(sp.output_byte_count)
        longest_by_kind[sp.action_kind].append(sp)
    result: dict[str, dict[str, Any]] = {}
    thresholds = rules.get("slow_action_thresholds_ms") or {}
    for kind, durs in by_kind.items():
        threshold = int(thresholds.get(kind) or thresholds.get("default") or 20000)
        slow_multi = float(rules.get("very_slow_multiplier") or 3.0)
        longest = sorted(longest_by_kind[kind], key=lambda sp: sp.duration_ms, reverse=True)[:3]
        result[kind] = {
            "count": len(durs),
            "p50_ms": _percentile(durs, 0.5),
            "p95_ms": _percentile(durs, 0.95),
            "max_ms": max(durs) if durs else 0,
            "threshold_ms": threshold,
            "very_slow_threshold_ms": int(threshold * slow_multi),
            "slow_count": sum(1 for d in durs if d > threshold),
            "very_slow_count": sum(1 for d in durs if d > int(threshold * slow_multi)),
            "total_output_bytes": sum(output_by_kind.get(kind) or []),
            "max_output_bytes": max(output_by_kind.get(kind) or [0]),
            "p95_output_bytes": _percentile(output_by_kind.get(kind) or [0], 0.95),
            "longest_spans": [
                {
                    "span_id": sp.span_id,
                    "duration_ms": sp.duration_ms,
                    "normalized_command": sp.normalized_command,
                    "target_paths": list(sp.target_paths[:2]),
                    "outcome": sp.outcome,
                    "output_byte_count": sp.output_byte_count,
                    "output_line_count": sp.output_line_count,
                }
                for sp in longest
            ],
        }
    return result


def _detect_anti_patterns(spans: list[Span], *, session_started_at: str | None, session_ended_at: str | None, rules: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    severities = rules.get("anti_pattern_severities") or {}
    cold_boot_count = int(rules.get("cold_boot_probe_span_count") or 3)
    loop_threshold = int(rules.get("loop_threshold_count") or 3)
    loop_window_ms = int(rules.get("loop_window_ms") or 120000)
    stall_threshold = int(rules.get("stall_inactivity_threshold_ms") or 90000)
    read_bomb_threshold = int(rules.get("read_bomb_line_threshold") or 1500)
    deep_threshold = int(rules.get("deep_without_ladder_span_threshold") or 25)

    first_kernel = next((sp.sequence_index for sp in spans if sp.is_kernel_shape), -1)
    first_grep = next((sp.sequence_index for sp in spans if sp.is_grep_shape), -1)
    if first_grep >= 0 and (first_kernel < 0 or first_grep < first_kernel):
        findings.append({
            "pattern_id": "anti_pattern_grep_before_kernel",
            "severity": severities.get("anti_pattern_grep_before_kernel", "warning"),
            "first_grep_span": first_grep,
            "first_kernel_span": first_kernel,
        })

    cold_boot_slice = spans[:cold_boot_count]
    cold_boot_kernel_hits = [
        sp
        for sp in cold_boot_slice
        if sp.is_kernel_shape and any(f in {"--info", "--preflight", "--pulse"} for f in sp.kernel_flags)
    ]
    if spans and not cold_boot_kernel_hits:
        findings.append({
            "pattern_id": "anti_pattern_cold_boot_missing_info",
            "severity": severities.get("anti_pattern_cold_boot_missing_info", "warning"),
            "inspected_span_count": min(cold_boot_count, len(spans)),
        })

    if len(spans) >= deep_threshold and not any(sp.is_kernel_shape for sp in spans):
        findings.append({
            "pattern_id": "anti_pattern_deep_without_ladder",
            "severity": severities.get("anti_pattern_deep_without_ladder", "warning"),
            "span_count": len(spans),
        })

    grep_like = [sp for sp in spans if sp.is_grep_shape or sp.is_read_shape]
    paper_module_hits = [sp for sp in spans if "--paper-module" in sp.kernel_flags]
    if len(grep_like) >= 6 and not paper_module_hits:
        findings.append({
            "pattern_id": "anti_pattern_paper_module_skip",
            "severity": severities.get("anti_pattern_paper_module_skip", "warning"),
            "read_or_grep_count": len(grep_like),
        })

    prev_end: datetime | None = None
    prev_end_ts: str | None = None
    for sp in spans:
        start = _parse_iso(sp.start_ts)
        if prev_end is not None and start is not None:
            gap_ms = int((start - prev_end).total_seconds() * 1000)
            if gap_ms > stall_threshold:
                findings.append({
                    "pattern_id": "anti_pattern_stall_detected",
                    "severity": severities.get("anti_pattern_stall_detected", "warning"),
                    "gap_ms": gap_ms,
                    "before_span": sp.sequence_index,
                    "prev_end_ts": prev_end_ts,
                    "start_ts": sp.start_ts,
                })
                break
        end = _parse_iso(sp.end_ts)
        if end is not None:
            prev_end = end
            prev_end_ts = sp.end_ts

    window: list[Span] = []
    seen_loop = False
    for sp in spans:
        window.append(sp)
        if not sp.normalized_command:
            continue
        start = _parse_iso(sp.start_ts)
        if start is None:
            continue
        cutoff = start.timestamp() * 1000 - loop_window_ms
        trimmed = []
        for other in window:
            other_start = _parse_iso(other.start_ts)
            if other_start is None:
                continue
            if other_start.timestamp() * 1000 >= cutoff:
                trimmed.append(other)
        window = trimmed
        matching = [o for o in window if o.normalized_command == sp.normalized_command]
        if len(matching) >= loop_threshold and not seen_loop:
            findings.append({
                "pattern_id": "anti_pattern_loop_detected",
                "severity": severities.get("anti_pattern_loop_detected", "warning"),
                "normalized_command": sp.normalized_command,
                "count_in_window_ms": loop_window_ms,
                "repeated_count": len(matching),
            })
            seen_loop = True

    positive_severities = rules.get("positive_pattern_severities") or {}
    if first_kernel >= 0 and first_grep == -1 and any(
        f in {"--info", "--preflight", "--pulse"} for sp in spans[:2] for f in sp.kernel_flags
    ):
        findings.append({
            "pattern_id": "positive_kernel_ladder_climb",
            "severity": positive_severities.get("positive_kernel_ladder_climb", "info"),
            "first_kernel_span": first_kernel,
        })

    return findings


def _summarize_hot_targets(spans: list[Span], *, top_n: int = 10) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for sp in spans:
        for p in sp.target_paths:
            counts[p] += 1
    return [{"path": k, "count": v} for k, v in counts.most_common(top_n)]


def _span_shape_tags(sp: Span) -> list[str]:
    return _command_shape_tags(sp.action_kind, sp.normalized_command or sp.command or "", sp.target_paths)


def _span_mapping_value(span: Mapping[str, Any] | Span) -> dict[str, Any]:
    if isinstance(span, Span):
        return span.as_dict()
    return dict(span)


def _span_display_command(span: Mapping[str, Any], *, char_limit: int) -> str:
    command = str(span.get("normalized_command") or span.get("command") or "").strip()
    paths = [str(path) for path in span.get("target_paths") or [] if str(path)]
    if (
        command
        and str(span.get("action_kind") or "") in {"edit_file", "write_file", "notebook_edit", "apply_patch"}
        and paths
    ):
        tool_name = str(span.get("tool_name") or span.get("action_kind") or "edit")
        display_paths = [Path(path).name if "/" in path else path for path in paths[:2]]
        command = f"{tool_name} {' '.join(display_paths)}".strip()
    if not command:
        tool_name = str(span.get("tool_name") or span.get("action_kind") or "span")
        display_paths = [Path(path).name if "/" in path else path for path in paths[:2]]
        command = f"{tool_name} {' '.join(display_paths)}".strip()
    return _truncate(command, char_limit) or ""


def _compact_edit_summary(value: Any, *, preview_limit: int) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    preview = [str(line) for line in list(value.get("preview") or [])[:preview_limit]]
    payload = _summary_drop_none(
        {
            "action": value.get("action"),
            "paths": list(value.get("target_paths") or [])[:3],
            "hunks": value.get("hunk_count"),
            "plus": value.get("added_line_count"),
            "minus": value.get("removed_line_count"),
            "preview": preview if preview_limit > 0 else None,
            "preview_policy": value.get("preview_policy"),
        }
    )
    return payload or None


def _trace_output_summary(span: Mapping[str, Any], *, preview_lines: int = 0, preview_chars: int = 160) -> dict[str, Any]:
    preview = [
        _clean_preview_line(str(line), char_limit=preview_chars)
        for line in list(span.get("output_preview") or [])[:preview_lines]
    ]
    preview = [line for line in preview if line]
    return _summary_drop_none(
        {
            "outcome": span.get("outcome"),
            "bytes": span.get("output_byte_count"),
            "lines": span.get("output_line_count"),
            "stdout_bytes": span.get("stdout_byte_count"),
            "stderr_bytes": span.get("stderr_byte_count"),
            "preview": preview if preview_lines > 0 else None,
            "preview_policy": "bounded_output_snippet" if preview else None,
        }
    )


def _compact_trace_level(
    spans: Iterable[Mapping[str, Any] | Span],
    *,
    session_id: str,
    level: str,
) -> dict[str, Any]:
    spec = TRACE_COMPACTNESS_PROFILES.get(level)
    if spec is None:
        raise ValueError(f"unknown trace compactness level: {level}")
    rows_in = [_span_mapping_value(span) for span in spans]
    row_limit = int(spec["row_limit"])
    command_chars = int(spec["command_chars"])
    target_limit = int(spec["target_limit"])
    edit_preview_lines = int(spec["edit_preview_lines"])
    output_preview_lines = int(spec["output_preview_lines"])
    output_preview_chars = int(spec["output_preview_chars"])
    include_tags = bool(spec["include_tags"])
    rows: list[dict[str, Any]] = []
    for span in rows_in[:row_limit]:
        tags = _command_shape_tags(
            str(span.get("action_kind") or ""),
            str(span.get("normalized_command") or span.get("command") or ""),
            span.get("target_paths") or [],
        )
        row = _summary_drop_none(
            {
                "i": span.get("sequence_index"),
                "turn": span.get("turn_index") if level in {"audit", "raw"} else None,
                "span_id": span.get("span_id") if level in {"audit", "raw"} else None,
                "kind": span.get("action_kind"),
                "ms": span.get("duration_ms"),
                "command": _span_display_command(span, char_limit=command_chars),
                "output": _trace_output_summary(
                    span,
                    preview_lines=output_preview_lines,
                    preview_chars=output_preview_chars,
                ),
                "edit": _compact_edit_summary(span.get("edit_summary"), preview_limit=edit_preview_lines),
                "targets": list(span.get("target_paths") or [])[:target_limit],
                "kernel_flags": list(span.get("kernel_flags") or [])[:8] if level in {"audit", "raw"} else None,
                "tags": tags[:8] if include_tags else None,
            }
        )
        rows.append(row)
    omitted_count = max(len(rows_in) - len(rows), 0)
    return {
        "level": level,
        "profile": spec.get("profile"),
        "session_id": session_id,
        "row_count": len(rows),
        "span_count": len(rows_in),
        "omitted_span_count": omitted_count,
        "row_limit": row_limit,
        "rows": rows,
        "omission_receipt": {
            "omitted": [
                "raw stdout/stderr bodies",
                "raw tool-result bodies",
                "prompt bodies",
                "assistant prose and thinking",
                "edit preview lines beyond the selected compactness level",
            ],
            "reason": TRACE_OUTPUT_PRIVACY_BOUNDARY,
            "drilldown": f"./repo-python kernel.py --process-trace {session_id} --process-trace-level audit --process-trace-format audit-json",
        },
    }


def build_trace_compactness_levels(
    spans: Iterable[Mapping[str, Any] | Span],
    *,
    session_id: str,
    selected_level: str = "tape",
    session: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    levels = list(TRACE_COMPACTNESS_PROFILES)
    selected_level = _normalize_trace_level(selected_level)
    if selected_level not in set(levels):
        raise ValueError(f"unknown trace compactness level: {selected_level}")
    span_rows = [_span_mapping_value(span) for span in spans]
    selected = [selected_level]
    if selected_level == "closeout":
        closeout_summary = _trace_closeout_summary(
            span_rows,
            session=session or {"session_id": session_id},
        )
        levels_payload = {
            "closeout": {
                "level": "closeout",
                "profile": TRACE_COMPACTNESS_PROFILES["closeout"].get("profile"),
                "session_id": session_id,
                "row_count": len(closeout_summary.get("recent_terminal_rows") or []),
                "span_count": len(span_rows),
                "omitted_span_count": max(len(span_rows) - len(closeout_summary.get("recent_terminal_rows") or []), 0),
                "rows": list(closeout_summary.get("recent_terminal_rows") or []),
                "summary": closeout_summary,
                "omission_receipt": {
                    "omitted": [
                        "raw stdout/stderr bodies",
                        "raw tool-result bodies",
                        "prompt bodies",
                        "assistant prose and thinking",
                        "full chronological tape rows",
                    ],
                    "reason": TRACE_OUTPUT_PRIVACY_BOUNDARY,
                    "drilldown": f"./repo-python kernel.py --process-trace {session_id} --process-trace-level tape",
                },
            }
        }
    else:
        closeout_summary = None
        levels_payload = {
            level: _compact_trace_level(span_rows, session_id=session_id, level=level)
            for level in selected
        }
    payload = {
        "schema_version": TRACE_COMPACTNESS_SCHEMA_VERSION,
        "boundary": TRACE_OUTPUT_PRIVACY_BOUNDARY,
        "selected_level": selected_level,
        "available_levels": [
            {
                "level": level,
                "profile": spec.get("profile"),
                "row_limit": spec.get("row_limit"),
                "command_chars": spec.get("command_chars"),
                "edit_preview_lines": spec.get("edit_preview_lines"),
            }
            for level, spec in TRACE_COMPACTNESS_PROFILES.items()
        ],
        "levels": levels_payload,
    }
    if closeout_summary is not None:
        payload["closeout_summary"] = closeout_summary
    return payload


def _short_int(value: Any) -> str:
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        return "0"
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _short_ms(value: Any) -> str:
    try:
        ms = int(value or 0)
    except (TypeError, ValueError):
        return "0ms"
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{ms}ms"


def _is_validation_command(command: str) -> bool:
    raw = str(command or "")
    return bool(
        re.search(
            r"\b(repo-pytest|pytest|py_compile|json\.loads|npm\s+(?:run\s+)?test|npm\s+(?:run\s+)?build|pnpm|yarn|tsc|mypy|ruff)\b",
            raw,
        )
    )


def _is_commit_command(command: str) -> bool:
    raw = str(command or "")
    return bool(re.search(r"\b(git\s+commit|scoped_commit\.py|./checkpoint|record-execution-receipt)\b", raw))


def _tape_action_label(kind: Any, command: str = "") -> str:
    if _is_validation_command(command):
        return "test"
    if _is_commit_command(command):
        return "commit"
    action = str(kind or "")
    if action in {"kernel_command", "bash_command", "bash_grep", "exec_command", "repo_tool_command"}:
        return "cmd"
    if action.startswith("bash_") or action.endswith("_command"):
        return "cmd"
    if action in {"read_file", "grep_tool", "glob_tool"}:
        return "read"
    if action in {"edit_file", "write_file", "notebook_edit", "apply_patch"}:
        return "edit"
    if action == "exec_session_io":
        return "wait"
    if action == "task_tool":
        return "tool"
    if action == "mcp_tool":
        return "mcp"
    return action or "step"


def _turn_think_line(turn: int, spans: list[Mapping[str, Any]]) -> str:
    counts: Counter[str] = Counter(
        _tape_action_label(span.get("action_kind"), str(span.get("normalized_command") or span.get("command") or ""))
        for span in spans
    )
    parts = [f"{name}x{count}" for name, count in counts.most_common(4)]
    out_bytes = sum(int(span.get("output_byte_count") or 0) for span in spans)
    edit_plus = 0
    edit_minus = 0
    for span in spans:
        edit = span.get("edit_summary")
        if isinstance(edit, Mapping):
            edit_plus += int(edit.get("added_line_count") or 0)
            edit_minus += int(edit.get("removed_line_count") or 0)
    edit_part = f" diff=+{edit_plus}/-{edit_minus}" if edit_plus or edit_minus else ""
    return f"T{turn} {' '.join(parts) or 'no-tools'} out={_short_int(out_bytes)}b{edit_part}"


def _compact_turns_line(span_rows: list[Mapping[str, Any]], *, limit: int = 8) -> str:
    by_turn: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for span in span_rows:
        by_turn[int(span.get("turn_index") or 0)].append(span)
    parts: list[str] = []
    for turn, spans in sorted(by_turn.items())[:limit]:
        counts: Counter[str] = Counter(
            _tape_action_label(span.get("action_kind"), str(span.get("normalized_command") or span.get("command") or ""))
            for span in spans
        )
        top = ",".join(f"{name}{count}" for name, count in counts.most_common(3))
        out_bytes = sum(int(span.get("output_byte_count") or 0) for span in spans)
        parts.append(f"T{turn}:{top or 'no-tools'}:{_short_int(out_bytes)}b")
    omitted = len(by_turn) - len(parts)
    suffix = f" +{omitted}T" if omitted > 0 else ""
    return f"think {'; '.join(parts)}{suffix}".strip()


def _output_status_text(
    output: Mapping[str, Any] | None,
    *,
    duration_ms: Any = None,
    preview: bool = True,
    compact: bool = False,
    tiny: bool = False,
) -> str:
    output = output or {}
    status = str(output.get("outcome") or "ok")
    duration = _short_ms(duration_ms)
    if duration and not tiny:
        status = f"{status} {duration}"
    if output:
        if tiny:
            status = f"{status} {_short_int(output.get('bytes'))}b"
        elif compact:
            status = f"{status} {_short_int(output.get('bytes'))}b/{_short_int(output.get('lines'))}l"
        else:
            status = f"{status} | {_short_int(output.get('bytes'))}b/{_short_int(output.get('lines'))}l"
    preview_rows = [str(line) for line in list(output.get("preview") or []) if str(line)]
    if preview and preview_rows:
        status = f"{status}: {preview_rows[0]}"
    return status


def _render_output_preview(
    output: Mapping[str, Any],
    *,
    duration_ms: Any = None,
    indent: str = "    ",
    preview: bool = True,
) -> list[str]:
    if not output:
        return []
    out = f"{indent}{_output_status_text(output, duration_ms=duration_ms, preview=preview)}"
    preview_rows = [str(line) for line in list(output.get("preview") or []) if str(line)] if preview else []
    if preview_rows:
        lines = [out]
        lines.extend(f"{indent}    {line}" for line in preview_rows[1:])
        return lines
    return [out]


def _trace_final_state_line(span_rows: list[Mapping[str, Any]], *, session: Mapping[str, Any], level: str) -> str:
    counts: Counter[str] = Counter()
    edit_plus = 0
    edit_minus = 0
    commit_refs: list[str] = []
    validation_count = 0
    for span in span_rows:
        command = str(span.get("normalized_command") or span.get("command") or "")
        label = _tape_action_label(span.get("action_kind"), command)
        counts[label] += 1
        if label == "test":
            validation_count += 1
        if label == "commit":
            for line in [command, *[str(row) for row in span.get("output_preview") or []]]:
                for match in re.findall(r"\b[0-9a-f]{7,40}\b", line):
                    if match not in commit_refs:
                        commit_refs.append(match)
        edit = span.get("edit_summary")
        if isinstance(edit, Mapping):
            edit_plus += int(edit.get("added_line_count") or 0)
            edit_minus += int(edit.get("removed_line_count") or 0)
    count_bits = [f"{name}={count}" for name, count in counts.most_common()]
    if validation_count and "test" not in counts:
        count_bits.append(f"test={validation_count}")
    commit = f" commit={commit_refs[-1][:10]}" if commit_refs else ""
    return (
        f"trace {session.get('agent') or '?'} {session.get('session_id') or ''} "
        f"turns={session.get('turn_count') or '?'} {' '.join(count_bits)} "
        f"edit=+{edit_plus}/-{edit_minus}{commit} level={level}"
    ).strip()


def _trace_provider_arg(session: Mapping[str, Any]) -> str:
    agent = str(session.get("agent") or "").lower()
    if "claude" in agent:
        return "claude"
    if "codex" in agent:
        return "codex"
    return "auto"


def _trace_session_token(session: Mapping[str, Any]) -> str:
    return str(session.get("session_id") or "latest")


def _trace_exact_closeout_command(session: Mapping[str, Any]) -> str:
    provider = _trace_provider_arg(session)
    session_token = _trace_session_token(session)
    return (
        "./repo-python tools/meta/observability/cli_prompt_trace.py "
        f"--provider {provider} --session {session_token} --format thread-closeouts --allow-ambiguous"
    )


def _closeout_row(
    span: Mapping[str, Any],
    *,
    command_chars: int = 180,
    output_preview_lines: int = 1,
    edit_preview_lines: int = 2,
) -> dict[str, Any]:
    command = _span_display_command(span, char_limit=command_chars).replace("\n", " ").strip()
    output = _trace_output_summary(span, preview_lines=output_preview_lines, preview_chars=160)
    edit = _compact_edit_summary(span.get("edit_summary"), preview_limit=edit_preview_lines)
    return _summary_drop_none(
        {
            "sequence_index": span.get("sequence_index"),
            "turn": span.get("turn_index"),
            "action": _tape_action_label(span.get("action_kind"), command),
            "command": command,
            "duration_ms": span.get("duration_ms"),
            "outcome": output.get("outcome"),
            "output": output or None,
            "diff": edit,
            "targets": list(span.get("target_paths") or [])[:5],
        }
    )


def _trace_closeout_summary(span_rows: list[Mapping[str, Any]], *, session: Mapping[str, Any]) -> dict[str, Any]:
    target_counts: Counter[str] = Counter()
    changed_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    edit_plus = 0
    edit_minus = 0
    validation_spans: list[Mapping[str, Any]] = []
    commit_spans: list[Mapping[str, Any]] = []

    for span in span_rows:
        command = str(span.get("normalized_command") or span.get("command") or "")
        label = _tape_action_label(span.get("action_kind"), command)
        action_counts[label] += 1
        if _is_validation_command(command):
            validation_spans.append(span)
        if _is_commit_command(command):
            commit_spans.append(span)
        for path in [str(path) for path in list(span.get("target_paths") or []) if str(path)]:
            target_counts[path] += 1
        edit = span.get("edit_summary")
        if isinstance(edit, Mapping):
            edit_plus += int(edit.get("added_line_count") or 0)
            edit_minus += int(edit.get("removed_line_count") or 0)
            edit_paths = list(edit.get("target_paths") or edit.get("paths") or span.get("target_paths") or [])
            for path in [str(path) for path in edit_paths if str(path)]:
                changed_counts[path] += 1

    recent_spans = [span for span in span_rows if _span_display_command(span, char_limit=120).strip()][-6:]
    session_token = _trace_session_token(session)
    detail_levels = ["outline", "closeout", "tape", "tape+diff", "audit", "raw"]
    return {
        "schema_version": "process_trace_closeout_summary_v1",
        "boundary": TRACE_OUTPUT_PRIVACY_BOUNDARY,
        "session_id": session_token,
        "agent": session.get("agent"),
        "action_counts": dict(action_counts),
        "worked_on_paths": [
            {"path": path, "span_count": count}
            for path, count in target_counts.most_common(8)
        ],
        "changed_files": [
            {"path": path, "edit_span_count": count}
            for path, count in changed_counts.most_common(8)
        ],
        "edit_summary": {"plus": edit_plus, "minus": edit_minus},
        "validation_rows": [_closeout_row(span) for span in validation_spans[-4:]],
        "commit_rows": [_closeout_row(span) for span in commit_spans[-3:]],
        "recent_terminal_rows": [_closeout_row(span, command_chars=140, output_preview_lines=0, edit_preview_lines=0) for span in recent_spans],
        "exact_closeout_message": {
            "source_boundary": "local_private_provider_trace",
            "prose_omitted_from_process_trace": True,
            "command": _trace_exact_closeout_command(session),
        },
        "detail_drilldowns": [
            {
                "level": level,
                "command": f"./repo-python kernel.py --process-trace {session_token} --process-trace-level {level}",
            }
            for level in detail_levels
        ],
    }


def _render_closeout_trace_tape(
    span_rows: list[Mapping[str, Any]],
    *,
    session: Mapping[str, Any],
) -> str:
    closeout = _trace_closeout_summary(span_rows, session=session)
    lines = [_trace_final_state_line(span_rows, session=session, level="closeout")]
    lines.append(
        "closeout scope=observable-actions assistant_prose=omitted "
        f"exact_closeout={closeout['exact_closeout_message']['command']}"
    )
    worked_on = [row["path"] for row in closeout["worked_on_paths"][:5]]
    changed = [row["path"] for row in closeout["changed_files"][:5]]
    if worked_on:
        lines.append(f"worked_on {' | '.join(worked_on)}")
    if changed:
        edit = closeout["edit_summary"]
        lines.append(f"changed +{_short_int(edit.get('plus'))}/-{_short_int(edit.get('minus'))} {' | '.join(changed)}")
    validation_rows = closeout["validation_rows"]
    if validation_rows:
        lines.append("validation")
        for row in validation_rows:
            lines.append(
                f"  {row.get('sequence_index', '---')} {row.get('command')} "
                f"| {row.get('outcome') or 'observed'} {_short_ms(row.get('duration_ms'))}"
            )
    else:
        lines.append("validation none-captured")
    commit_rows = closeout["commit_rows"]
    if commit_rows:
        lines.append("commits")
        for row in commit_rows:
            lines.append(f"  {row.get('sequence_index', '---')} {row.get('command')}")
    recent_rows = closeout["recent_terminal_rows"]
    if recent_rows:
        lines.append("recent")
        for row in recent_rows:
            lines.append(
                f"  {row.get('sequence_index', '---')} {row.get('action')} {row.get('command')} "
                f"| {row.get('outcome') or 'observed'}"
            )
    lines.append(
        "drilldown outline|tape|tape+diff|audit|raw via "
        f"./repo-python kernel.py --process-trace {_trace_session_token(session)} --process-trace-level <level>"
    )
    return "\n".join(lines)


def _tape_marker(label: str) -> str:
    return "$" if label == "cmd" else label


def _ultra_tape_marker(label: str) -> str:
    return {
        "cmd": "$",
        "read": "R",
        "edit": "E",
        "test": "T",
        "commit": "C",
        "wait": "W",
        "tool": "tool",
        "mcp": "mcp",
    }.get(label, label[:1] or "?")


def _render_trace_tape_rows(
    span_rows: list[Mapping[str, Any]],
    *,
    session: Mapping[str, Any],
    level: str,
    command_chars: int,
    output_preview_lines: int,
    output_preview_chars: int,
    edit_preview_lines: int,
    include_turns: bool,
    inline_output: bool,
    compact_status: bool = False,
    tiny_status: bool = False,
    ultra: bool = False,
) -> list[str]:
    by_turn: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    if include_turns:
        for span in span_rows:
            by_turn[int(span.get("turn_index") or 0)].append(span)

    lines: list[str] = [_trace_final_state_line(span_rows, session=session, level=level)]
    if not include_turns:
        turns_line = _compact_turns_line(span_rows)
        if turns_line:
            lines.append(turns_line)
    current_turn: int | None = None
    for raw in span_rows:
        turn = int(raw.get("turn_index") or 0)
        if include_turns and turn != current_turn:
            current_turn = turn
            lines.append(_turn_think_line(turn, by_turn.get(turn, [])))
        command = _span_display_command(raw, char_limit=command_chars).replace("\n", " ").strip()
        label = _tape_action_label(raw.get("action_kind"), str(raw.get("normalized_command") or raw.get("command") or ""))
        marker = _tape_marker(label)
        if ultra:
            marker = _ultra_tape_marker(label)
        seq = raw.get("sequence_index")
        prefix = f"{int(seq):03d}" if isinstance(seq, int) else "---"
        output = _trace_output_summary(
            raw,
            preview_lines=output_preview_lines,
            preview_chars=output_preview_chars,
        )
        output_has_preview = output_preview_lines > 0
        edit = _compact_edit_summary(raw.get("edit_summary"), preview_limit=edit_preview_lines)
        if inline_output:
            status = _output_status_text(
                output,
                duration_ms=raw.get("duration_ms"),
                preview=output_has_preview,
                compact=compact_status,
                tiny=tiny_status,
            )
            if ultra:
                status = status.replace(" ", "")
                edit_suffix = ""
                if isinstance(edit, Mapping):
                    edit_suffix = f" +{_short_int(edit.get('plus'))}/-{_short_int(edit.get('minus'))}"
                lines.append(f"{prefix}{marker}{command}|{status}{edit_suffix}".rstrip())
            else:
                lines.append(f"{prefix} {marker} {command} | {status}".rstrip())
        else:
            lines.append(f"{prefix} {marker} {command}".rstrip())
            targets = [str(path) for path in list(raw.get("target_paths") or []) if str(path)]
            if targets and label in {"read", "edit"}:
                lines.append(f"    file {' | '.join(targets[:3])}")
            if output:
                lines.extend(
                    _render_output_preview(
                        output,
                        duration_ms=raw.get("duration_ms"),
                        preview=output_has_preview,
                    )
                )
        if isinstance(edit, Mapping) and not ultra:
            edit_paths = [str(path) for path in list(edit.get("paths") or []) if str(path)]
            path_text = f" {' | '.join(edit_paths[:3])}" if edit_paths and not inline_output else ""
            lines.append(
                f"    diff +{_short_int(edit.get('plus'))} -{_short_int(edit.get('minus'))}{path_text}".rstrip()
            )
            for preview_line in list(edit.get("preview") or []):
                lines.append(f"      {preview_line}")
    return lines


def render_trace_tape(
    spans: Iterable[Mapping[str, Any] | Span],
    *,
    session: Mapping[str, Any],
    selected_level: str = "tape",
    max_chars: int = 10000,
) -> str:
    """Render a low-scaffold chronological trace for human browsing."""
    level = _normalize_trace_level(selected_level)
    if level not in TRACE_COMPACTNESS_PROFILES:
        level = "tape"
    span_rows = [_span_mapping_value(span) for span in spans]
    if level == "outline":
        lines = [_trace_final_state_line(span_rows, session=session, level=level)]
        edit_count = sum(1 for span in span_rows if isinstance(span.get("edit_summary"), Mapping))
        validation_count = sum(
            1 for span in span_rows if _is_validation_command(str(span.get("normalized_command") or span.get("command") or ""))
        )
        commit_count = sum(
            1 for span in span_rows if _is_commit_command(str(span.get("normalized_command") or span.get("command") or ""))
        )
        lines.append(
            f"outline edits={edit_count} validations={validation_count} commits={commit_count} "
            f"spans={len(span_rows)} out={_short_int(session.get('total_output_bytes'))}b"
        )
        return "\n".join(lines)
    if level == "closeout":
        return _render_closeout_trace_tape(span_rows, session=session)
    spec = TRACE_COMPACTNESS_PROFILES[level]
    row_limit = int(spec["row_limit"])
    visible_raw_rows = span_rows[:row_limit]
    strategies = [
        {
            "command_chars": int(spec["command_chars"]),
            "output_preview_lines": int(spec["output_preview_lines"]),
            "output_preview_chars": int(spec["output_preview_chars"]),
            "edit_preview_lines": int(spec["edit_preview_lines"]),
            "include_turns": True,
            "inline_output": False,
        },
        {
            "command_chars": min(int(spec["command_chars"]), 100),
            "output_preview_lines": min(int(spec["output_preview_lines"]), 1),
            "output_preview_chars": min(int(spec["output_preview_chars"]), 90),
            "edit_preview_lines": min(int(spec["edit_preview_lines"]), 2),
            "include_turns": True,
            "inline_output": True,
            "compact_status": True,
        },
        {
            "command_chars": min(int(spec["command_chars"]), 64),
            "output_preview_lines": 0,
            "output_preview_chars": 0,
            "edit_preview_lines": 0,
            "include_turns": True,
            "inline_output": True,
            "compact_status": True,
        },
        {
            "command_chars": min(int(spec["command_chars"]), 36),
            "output_preview_lines": 0,
            "output_preview_chars": 0,
            "edit_preview_lines": 0,
            "include_turns": False,
            "inline_output": True,
            "tiny_status": True,
        },
        {
            "command_chars": min(int(spec["command_chars"]), 14),
            "output_preview_lines": 0,
            "output_preview_chars": 0,
            "edit_preview_lines": 0,
            "include_turns": False,
            "inline_output": True,
            "tiny_status": True,
            "ultra": True,
        },
    ]
    chosen_lines: list[str] = []
    for strategy in strategies:
        chosen_lines = _render_trace_tape_rows(visible_raw_rows, session=session, level=level, **strategy)
        text = "\n".join(chosen_lines)
        if max_chars <= 0 or len(text.encode("utf-8")) <= max_chars:
            break
    lines = chosen_lines
    omitted = max(len(span_rows) - len(visible_raw_rows), 0)
    if omitted:
        lines.append(f"... {omitted} spans omitted by {level} row limit")
    text = "\n".join(lines)
    if max_chars > 0 and len(text.encode("utf-8")) > max_chars:
        return _truncate_utf8_bytes(
            text,
            max_chars,
            suffix=f"\n... truncated at {max_chars} bytes; rerun with --process-trace-max-chars",
        )
    return text


def _build_trace_index(span_rows: list[Mapping[str, Any]], *, session_id: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for idx, span in enumerate(span_rows):
        command = str(span.get("normalized_command") or span.get("command") or "")
        edit = span.get("edit_summary")
        row_id = f"r{idx:04d}"
        rows.append(
            _summary_drop_none(
                {
                    "row_id": row_id,
                    "span_id": span.get("span_id"),
                    "sequence_index": span.get("sequence_index"),
                    "turn": span.get("turn_index"),
                    "action": _tape_action_label(span.get("action_kind"), command),
                    "command": _span_display_command(span, char_limit=220),
                    "targets": list(span.get("target_paths") or [])[:5],
                    "output": {
                        "bytes": span.get("output_byte_count"),
                        "lines": span.get("output_line_count"),
                        "preview_pointer": f"trace.raw_sidecar.jsonl#{row_id}.output_preview",
                    },
                    "diff": {
                        "plus": edit.get("added_line_count"),
                        "minus": edit.get("removed_line_count"),
                        "preview_pointer": f"trace.raw_sidecar.jsonl#{row_id}.edit_summary",
                    }
                    if isinstance(edit, Mapping)
                    else None,
                    "raw_pointer": f"trace.raw_sidecar.jsonl#{row_id}",
                }
            )
        )
    return {
        "schema_version": "trace_index_v1",
        "session_id": session_id,
        "row_count": len(rows),
        "rows": rows,
    }


def build_trace_tape_artifacts(
    span_rows: Iterable[Mapping[str, Any] | Span],
    *,
    session: Mapping[str, Any],
    selected_level: str,
    tape_max_chars: int,
    include_raw_sidecar: bool = False,
) -> dict[str, Any]:
    spans = [_span_mapping_value(span) for span in span_rows]
    session_id = str(session.get("session_id") or "")
    tape = render_trace_tape(spans, session=session, selected_level=selected_level, max_chars=tape_max_chars)
    index = _build_trace_index(spans, session_id=session_id)
    raw_sidecar = None
    if include_raw_sidecar:
        raw_lines = []
        for idx, span in enumerate(spans):
            row = dict(span)
            row["row_id"] = f"r{idx:04d}"
            raw_lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
        raw_sidecar = "\n".join(raw_lines)
    return {
        "trace.tape.txt": {
            "bytes": len(tape.encode("utf-8")),
            "content": tape,
        },
        "trace.index.json": index,
        "trace.raw_sidecar.jsonl": {
            "bytes": len(raw_sidecar.encode("utf-8")) if raw_sidecar is not None else None,
            "content": raw_sidecar,
            "omitted": raw_sidecar is None,
            "reason": None if raw_sidecar is not None else "raw sidecar is only emitted with --process-trace-format raw-json",
        },
    }


def _summarize_task_result_reads(spans: list[Span], *, session_id: str, limit: int = 6) -> dict[str, Any]:
    rows = [
        sp
        for sp in spans
        if sp.action_kind == "read_file"
        and {"task_output_file", "tool_result_file"}.intersection(set(_span_shape_tags(sp)))
    ]
    if not rows:
        return {
            "count": 0,
            "total_output_bytes": 0,
            "top_reads": [],
        }
    by_tag: Counter[str] = Counter()
    by_target_kind: Counter[str] = Counter()
    for sp in rows:
        tags = set(_span_shape_tags(sp))
        if "task_output_file" in tags:
            by_tag["task_output_file"] += 1
        if "tool_result_file" in tags:
            by_tag["tool_result_file"] += 1
        if "tmp_artifact_file" in tags:
            by_tag["tmp_artifact_file"] += 1
        if any("tool-results/" in path for path in sp.target_paths):
            by_target_kind["tool_results"] += 1
        elif any("tasks/" in path for path in sp.target_paths):
            by_target_kind["task_outputs"] += 1
        else:
            by_target_kind["other_result_files"] += 1
    top_reads = [
        {
            "span_id": sp.span_id,
            "sequence_index": sp.sequence_index,
            "target_kind": (
                "tool_results"
                if any("tool-results/" in path for path in sp.target_paths)
                else "task_outputs"
                if any("tasks/" in path for path in sp.target_paths)
                else "other_result_files"
            ),
            "output_byte_count": sp.output_byte_count,
            "output_line_count": sp.output_line_count,
            "start_ts": sp.start_ts,
            "end_ts": sp.end_ts,
            "command_shape_tags": list(_span_shape_tags(sp)[:6]),
        }
        for sp in sorted(rows, key=lambda item: item.output_byte_count, reverse=True)[:limit]
    ]
    return {
        "count": len(rows),
        "total_output_bytes": sum(sp.output_byte_count for sp in rows),
        "target_kind_counts": dict(by_target_kind.most_common()),
        "tag_counts": dict(by_tag.most_common()),
        "top_reads": top_reads,
        "raw_body_policy": "omitted_from_process_summary",
        "raw_reopen_route": f"./repo-python kernel.py --process-trace {session_id}",
    }


def _summary_thought_trace(
    *,
    route_compliance: Mapping[str, Any],
    top_commands: list[dict[str, Any]],
    target_hot_list: list[dict[str, Any]],
    anti_patterns: list[dict[str, Any]],
    bottleneck_preview: list[dict[str, Any]],
    kernel_flag_counts: Mapping[str, int],
    action_kind_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Project the observable command/path/process summary without reading model prose."""
    repeated_commands = [
        {"signal": "repeated_command", "command": row.get("command"), "count": row.get("count")}
        for row in top_commands
        if int(row.get("count") or 0) >= 3 and row.get("command")
    ]
    hot_targets = [
        {"signal": "hot_target", "path": row.get("path"), "count": row.get("count")}
        for row in target_hot_list
        if int(row.get("count") or 0) >= 3 and row.get("path")
    ]
    pattern_signals = [
        {
            "signal": "process_pattern",
            "pattern_id": row.get("pattern_id"),
            "severity": row.get("severity"),
        }
        for row in anti_patterns
        if row.get("pattern_id")
    ]
    slow_signals = [
        {
            "signal": "slow_span",
            "action_kind": row.get("action_kind"),
            "duration_ms": row.get("duration_ms"),
            "normalized_command": row.get("normalized_command"),
        }
        for row in bottleneck_preview[:3]
        if row.get("action_kind")
    ]
    return {
        "schema_version": SUMMARY_THOUGHT_TRACE_SCHEMA_VERSION,
        "boundary": "observable_actions_only_not_hidden_chain_of_thought",
        "counters": {
            "top_command_count": len(top_commands),
            "hot_target_count": len(target_hot_list),
            "kernel_flag_count": sum(int(v or 0) for v in kernel_flag_counts.values()),
            "action_kind_count": len(action_kind_counts),
            "anti_pattern_count": len(anti_patterns),
            "bottleneck_preview_count": len(bottleneck_preview),
            "candidate_signal_count": len(repeated_commands) + len(hot_targets) + len(pattern_signals) + len(slow_signals),
        },
        "route_trace": {
            "score": route_compliance.get("score"),
            "first_kernel_span_index": route_compliance.get("first_kernel_span_index"),
            "first_grep_span_index": route_compliance.get("first_grep_span_index"),
            "first_read_span_index": route_compliance.get("first_read_span_index"),
            "ladder_position": route_compliance.get("ladder_position"),
            "deviation_count": route_compliance.get("deviation_count"),
            "ladder_rungs_hit": list(route_compliance.get("ladder_rungs_hit") or [])[:12],
        },
        "command_trace": list(top_commands[:10]),
        "focus_trace": list(target_hot_list[:10]),
        "candidate_signals": (repeated_commands + hot_targets + pattern_signals + slow_signals)[:20],
    }


def _ranking_span_payload(sp: Span) -> dict[str, Any]:
    return {
        "span_id": sp.span_id,
        "agent": sp.agent,
        "session_id": sp.session_id,
        "action_kind": sp.action_kind,
        "start_ts": sp.start_ts,
        "end_ts": sp.end_ts,
        "duration_ms": sp.duration_ms,
        "outcome": sp.outcome,
        "sequence_index": sp.sequence_index,
        "turn_index": sp.turn_index,
        "tool_name": sp.tool_name,
        "command": sp.command,
        "normalized_command": sp.normalized_command,
        "target_paths": list(sp.target_paths),
        "kernel_flags": list(sp.kernel_flags),
        "output_byte_count": sp.output_byte_count,
        "output_line_count": sp.output_line_count,
        "stdout_byte_count": sp.stdout_byte_count,
        "stderr_byte_count": sp.stderr_byte_count,
    }


def _finalize_session_bottleneck_rankings(
    *,
    agent: str,
    session_id: str,
    source_path: Path,
    spans: list[Span],
    started_at: str | None,
    ended_at: str | None,
    git_branch: str | None,
    model_counts: Counter[str],
    rules: Mapping[str, Any],
    repo_root: Path,
    truncation_notes: list[dict[str, Any]],
    last_record_ts: str | None,
) -> dict[str, Any]:
    """Finalize only the fields required by live process-bottleneck rankings."""
    del rules, git_branch, model_counts
    action_kind_counts: Counter[str] = Counter(sp.action_kind for sp in spans)
    action_kind_durations: dict[str, int] = defaultdict(int)
    kernel_flag_counts: Counter[str] = Counter()
    for sp in spans:
        action_kind_durations[sp.action_kind] += sp.duration_ms
        for flag in sp.kernel_flags:
            kernel_flag_counts[flag] += 1
    spans_payload = [_ranking_span_payload(sp) for sp in spans]
    session_row = {
        "session_id": session_id,
        "agent": agent,
        "source_path": _relpath(source_path, repo_root=repo_root),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": _duration_ms(started_at, ended_at),
        "span_count": len(spans),
        "total_output_bytes": sum(sp.output_byte_count for sp in spans),
        "turn_count": max((sp.turn_index for sp in spans), default=0),
        "action_kind_counts": dict(sorted(action_kind_counts.items())),
        "action_kind_durations_ms": dict(sorted(action_kind_durations.items())),
        "kernel_flag_counts": dict(kernel_flag_counts.most_common(20)),
        "route_compliance": {},
        "route_lease_mode_control": {"status": "skipped_bottleneck_rankings_profile"},
        "anti_patterns": [],
        "bottleneck_preview": [],
        "summary_thought_trace": {
            "schema_version": SUMMARY_THOUGHT_TRACE_SCHEMA_VERSION,
            "boundary": "observable_actions_only_not_hidden_chain_of_thought",
            "profile": "skipped_bottleneck_rankings_profile",
        },
        "truncation_notes": list(truncation_notes),
        "last_record_ts": last_record_ts,
    }
    return {"session": session_row, "spans": spans_payload}


def _finalize_session(
    *,
    agent: str,
    session_id: str,
    source_path: Path,
    spans: list[Span],
    started_at: str | None,
    ended_at: str | None,
    git_branch: str | None,
    model_counts: Counter[str],
    rules: Mapping[str, Any],
    repo_root: Path,
    truncation_notes: list[dict[str, Any]],
    last_record_ts: str | None,
) -> dict[str, Any]:
    turn_count = max((sp.turn_index for sp in spans), default=0)
    action_kind_counts: Counter[str] = Counter(sp.action_kind for sp in spans)
    action_kind_durations: dict[str, int] = defaultdict(int)
    for sp in spans:
        action_kind_durations[sp.action_kind] += sp.duration_ms
    kernel_flag_counts: Counter[str] = Counter()
    for sp in spans:
        for f in sp.kernel_flags:
            kernel_flag_counts[f] += 1
    normalized_command_counts: Counter[str] = Counter(sp.normalized_command for sp in spans if sp.normalized_command)
    route_compliance = _compute_route_compliance(spans, rules)
    bottlenecks = _compute_bottlenecks(spans, rules)
    anti_patterns = _detect_anti_patterns(spans, session_started_at=started_at, session_ended_at=ended_at, rules=rules)
    route_lease_mode_control = _route_lease_mode_control(spans)
    duration_ms = _duration_ms(started_at, ended_at)
    longest = sorted(spans, key=lambda sp: sp.duration_ms, reverse=True)[:5]
    top_commands = [
        {"command": cmd, "count": cnt} for cmd, cnt in normalized_command_counts.most_common(10)
    ]
    target_hot_list = _summarize_hot_targets(spans, top_n=10)
    task_result_reads = _summarize_task_result_reads(spans, session_id=session_id)
    spans_payload = [sp.as_dict() for sp in spans]
    chronological_trace_outline = _compact_trace_level(
        spans_payload,
        session_id=session_id,
        level="outline",
    )
    bottleneck_preview = [
        {
            "span_id": sp.span_id,
            "action_kind": sp.action_kind,
            "duration_ms": sp.duration_ms,
            "normalized_command": sp.normalized_command,
            "target_paths": list(sp.target_paths[:2]),
            "outcome": sp.outcome,
            "output_byte_count": sp.output_byte_count,
            "output_line_count": sp.output_line_count,
            "command_shape_tags": list(_span_shape_tags(sp)[:6]),
        }
        for sp in longest
    ]
    session_row = {
        "session_id": session_id,
        "agent": agent,
        "source_path": _relpath(source_path, repo_root=repo_root),
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "span_count": len(spans),
        "total_output_bytes": sum(sp.output_byte_count for sp in spans),
        "turn_count": turn_count,
        "action_kind_counts": dict(sorted(action_kind_counts.items())),
        "action_kind_durations_ms": dict(sorted(action_kind_durations.items())),
        "kernel_flag_counts": dict(kernel_flag_counts.most_common(20)),
        "top_normalized_commands": top_commands,
        "target_path_hot_list": target_hot_list,
        "task_result_reads": task_result_reads,
        "chronological_trace_outline": chronological_trace_outline,
        "route_compliance": route_compliance,
        "route_lease_mode_control": route_lease_mode_control,
        "bottlenecks": bottlenecks,
        "anti_patterns": anti_patterns,
        "bottleneck_preview": bottleneck_preview,
        "summary_thought_trace": _summary_thought_trace(
            route_compliance=route_compliance,
            top_commands=top_commands,
            target_hot_list=target_hot_list,
            anti_patterns=anti_patterns,
            bottleneck_preview=bottleneck_preview,
            kernel_flag_counts=dict(kernel_flag_counts),
            action_kind_counts=dict(action_kind_counts),
        ),
        "model_counts": dict(model_counts),
        "git_branch": git_branch,
        "truncation_notes": list(truncation_notes),
        "last_record_ts": last_record_ts,
    }
    return {"session": session_row, "spans": spans_payload}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def _claude_project_slug(repo_root: Path) -> str:
    """Claude Code encodes project paths as slashes-and-underscores -> hyphens, with a leading hyphen."""
    return "-" + str(repo_root).replace("/", "-").lstrip("-").replace("_", "-")


def discover_claude_sessions(*, repo_root: Path, home: Path, since_ts: str | None, limit: int | None) -> list[Path]:
    slug = _claude_project_slug(repo_root)
    projects_dir = home / ".claude" / "projects" / slug
    if not projects_dir.exists():
        return []
    files = list(projects_dir.glob("*.jsonl"))
    if since_ts:
        cutoff = _parse_iso(since_ts)
        if cutoff is not None:
            files = [f for f in files if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) >= cutoff]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if limit is not None and limit > 0:
        files = files[:limit]
    return files


def discover_codex_sessions(*, home: Path, since_ts: str | None, limit: int | None) -> list[Path]:
    sessions_dir = home / ".codex" / "sessions"
    if not sessions_dir.exists():
        return []
    if not since_ts and limit is not None and limit > 0:
        files = _discover_codex_sessions_from_date_dirs(sessions_dir, limit=limit)
        if files:
            return files
    files = list(sessions_dir.rglob("rollout-*.jsonl"))
    if since_ts:
        cutoff = _parse_iso(since_ts)
        if cutoff is not None:
            files = [f for f in files if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) >= cutoff]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if limit is not None and limit > 0:
        files = files[:limit]
    return files


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _named_child_dirs(path: Path) -> list[Path]:
    try:
        children = [child for child in path.iterdir() if child.is_dir()]
    except OSError:
        return []
    return sorted(children, key=lambda child: child.name, reverse=True)


def _discover_codex_sessions_from_date_dirs(sessions_dir: Path, *, limit: int) -> list[Path]:
    """Fast path for ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl."""
    files: list[Path] = []
    for year_dir in _named_child_dirs(sessions_dir):
        if not (len(year_dir.name) == 4 and year_dir.name.isdigit()):
            continue
        for month_dir in _named_child_dirs(year_dir):
            if not (len(month_dir.name) == 2 and month_dir.name.isdigit()):
                continue
            for day_dir in _named_child_dirs(month_dir):
                if not (len(day_dir.name) == 2 and day_dir.name.isdigit()):
                    continue
                try:
                    day_files = list(day_dir.glob("rollout-*.jsonl"))
                except OSError:
                    continue
                day_files.sort(key=_safe_mtime, reverse=True)
                files.extend(day_files)
                if len(files) >= limit:
                    return files[:limit]
    return files


def _process_trace_sources(repo_root: Path) -> dict[str, list[str]]:
    return {
        "live": [
            _relpath(repo_root / STANDARD_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / TRACE_RULES_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        ],
        "derived": [
            _relpath(repo_root / LEDGER_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / AUDIT_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / NAVIGATION_CACHE_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / PATTERNS_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / SUMMARY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        ],
    }


def _summary_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _summary_drop_none(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items() if value is not None}


def _summary_top_mapping_items(value: Mapping[str, Any] | None, *, limit: int = 10) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    items = sorted(value.items(), key=lambda item: (-_summary_int(item[1]), str(item[0])))
    return {str(key): count for key, count in items[:limit]}


def _summary_compact_command_rows(rows: list[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _summary_drop_none(
                {
                    "command": _truncate(str(row.get("command") or row.get("normalized_command") or ""), 180)
                    if row.get("command") or row.get("normalized_command")
                    else None,
                    "count": row.get("count"),
                    "total_duration_ms": row.get("total_duration_ms"),
                    "p95_ms": row.get("p95_ms"),
                    "exit_code": row.get("exit_code"),
                }
            )
        )
    return compact


def _summary_compact_bottleneck_preview(rows: list[Any], *, limit: int = 6) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        target_paths = row.get("target_paths")
        if target_paths is None and row.get("target_path"):
            target_paths = [row.get("target_path")]
        compact.append(
            _summary_drop_none(
                {
                    "action_kind": row.get("action_kind"),
                    "duration_ms": row.get("duration_ms"),
                    "outcome": row.get("outcome"),
                    "normalized_command": _truncate(str(row.get("normalized_command") or ""), 180)
                    if row.get("normalized_command")
                    else None,
                    "target_paths": list(target_paths or [])[:2],
                    "command_shape_tags": list(row.get("command_shape_tags") or [])[:6],
                    "output_byte_count": row.get("output_byte_count"),
                }
            )
        )
    return compact


COMPACT_REPAIR_HINT_PRIORITIES = {
    "replace_git_object_find_scan_with_gc_maintenance_check": 9,
    "replace_raw_search_scan_with_owner_route": 10,
    "replace_host_find_scan_with_host_filesystem_quote": 11,
    "replace_find_scan_with_rg_files_or_option_surface": 12,
    "replace_git_shell_chain_with_state_snapshot": 13,
    "replace_global_raw_diff_with_diff_review_context": 14,
    "replace_polling_with_status_surface": 15,
    "inspect_preceding_exec_or_add_status_surface": 16,
    "route_session_diagnostics_through_command_surface": 17,
    "use_cached_or_filtered_process_bottleneck_status": 18,
    "route_focused_validation_through_action_quote": 19,
    "replace_python_module_tail_with_compact_cli_mode": 70,
    "replace_shell_limiter_with_compact_packet": 80,
}


def _summary_compact_repair_hint_sort_key(row_with_index: tuple[int, Any]) -> tuple[int, int]:
    index, row = row_with_index
    if not isinstance(row, Mapping):
        return (100, index)
    hint_id = str(row.get("hint_id") or "")
    return (COMPACT_REPAIR_HINT_PRIORITIES.get(hint_id, 50), index)


def _summary_compact_repair_hints(rows: list[Any], *, limit: int = 2) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    ranked_rows = sorted(enumerate(rows), key=_summary_compact_repair_hint_sort_key)
    for _index, row in ranked_rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        hint_id = row.get("hint_id")
        concrete_preferred_next = row.get("concrete_preferred_next")
        preferred_next = row.get("preferred_next")
        owner_surface = row.get("owner_surface")
        if hint_id == "route_kernel_flag_through_command_surface" and concrete_preferred_next:
            preferred_next = None
            owner_surface = None
        compact.append(
            _summary_drop_none(
                {
                    "hint_id": hint_id,
                    "kernel_flag": row.get("kernel_flag"),
                    "concrete_preferred_next": concrete_preferred_next,
                    "preferred_next": preferred_next,
                    "owner_surface": owner_surface,
                }
            )
        )
    return compact


def _kernel_flag_repair_hints(by_flag: Iterable[Any], *, limit: int = 2) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in by_flag:
        if not isinstance(row, Mapping):
            continue
        flag = str(row.get("kernel_flag") or "")
        if flag == "--session-diagnostics":
            hint = {
                "hint_id": "route_session_diagnostics_through_command_surface",
                "preferred_next": (
                    "./repo-python tools/meta/control/action_quote.py "
                    "--action command_surface_inventory --scope session-diagnostics"
                ),
                "owner_surface": (
                    "./repo-python kernel.py --session-diagnostics "
                    "--lens all --last 10 --store both --json --diagnostics-summary"
                ),
            }
        elif flag == "--process-bottlenecks":
            hint = {
                "hint_id": "use_cached_or_filtered_process_bottleneck_status",
                "concrete_preferred_next": (
                    "./repo-python kernel.py --process-bottlenecks "
                    "--process-action-kind kernel_command"
                ),
                "preferred_next": "./repo-python kernel.py --process-bottlenecks --process-action-kind <action-kind>",
                "owner_surface": "./repo-python tools/meta/factory/build_agent_execution_trace.py --cached-summary --limit 6",
            }
        else:
            hint = _kernel_flag_command_surface_hint(flag)
        hint_id = str(hint.get("hint_id") or "")
        if hint_id in seen:
            continue
        seen.add(hint_id)
        hints.append(hint)
        if len(hints) >= limit:
            break
    return hints


def _summary_compact_kernel_flag_rows(rows: list[Any], *, limit: int = 2) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _summary_drop_none(
                {
                    "kernel_flag": row.get("kernel_flag"),
                    "count": row.get("count"),
                    "p95_ms": row.get("p95_ms"),
                    "total_duration_ms": row.get("total_duration_ms"),
                    "slow_count": row.get("slow_count"),
                }
            )
        )
    return compact


def _summary_compact_pattern_rows(rows: list[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _summary_drop_none(
                {
                    "pattern_id": row.get("pattern_id"),
                    "severity": row.get("severity"),
                    "instances": row.get("instances"),
                    "session_hits": len(row.get("session_id_hits") or []),
                }
            )
        )
    return compact


def _summary_compact_audit_findings(rows: list[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            _summary_drop_none(
                {
                    "rule": row.get("rule"),
                    "severity": row.get("severity"),
                    "subject": row.get("subject"),
                    "message": row.get("message"),
                }
            )
        )
    return compact


def _summary_compact_process_bottlenecks(
    value: Mapping[str, Any] | None,
    *,
    limit: int = 8,
    example_limit: int = 3,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    items = sorted(
        value.items(),
        key=lambda item: (
            -_bottleneck_summary_sort_key(item[1] if isinstance(item[1], Mapping) else {})[0],
            -_bottleneck_summary_sort_key(item[1] if isinstance(item[1], Mapping) else {})[1],
            -_bottleneck_summary_sort_key(item[1] if isinstance(item[1], Mapping) else {})[2],
            -_bottleneck_summary_sort_key(item[1] if isinstance(item[1], Mapping) else {})[3],
            str(item[0]),
        ),
    )
    compact: dict[str, Any] = {}
    for key, row in items[:limit]:
        if not isinstance(row, Mapping):
            continue
        repair_hints = _summary_compact_repair_hints(list(row.get("repair_hints") or []), limit=2)
        by_flag = list(row.get("by_kernel_flag") or [])
        if not repair_hints and str(key) == "kernel_command":
            repair_hints = _kernel_flag_repair_hints(by_flag, limit=2)
        compact_row: dict[str, Any] = {
            "span_count": row.get("span_count"),
            "count": row.get("count"),
            "p50_ms": row.get("p50_ms"),
            "p95_ms": row.get("p95_ms"),
            "max_ms": row.get("max_ms"),
            "total_duration_ms": row.get("total_duration_ms"),
            "slow_count": row.get("slow_count"),
            "threshold_ms": row.get("threshold_ms"),
            "total_output_bytes": row.get("total_output_bytes"),
            "max_output_bytes": row.get("max_output_bytes"),
            "p95_output_bytes": row.get("p95_output_bytes"),
            "actionability_class": row.get("actionability_class"),
            "optimization_priority_score": row.get("optimization_priority_score"),
            "ranking_note": row.get("ranking_note"),
            "repair_hints": repair_hints,
        }
        examples = list(row.get("example_spans") or [])
        if example_limit > 0:
            compact_row["example_spans"] = _summary_compact_bottleneck_preview(
                examples,
                limit=example_limit,
            )
        elif examples:
            compact_row["example_count"] = len(examples)
        if by_flag:
            compact_row["by_kernel_flag_top"] = _summary_compact_kernel_flag_rows(by_flag, limit=2)
            compact_row["by_kernel_flag_count"] = len(by_flag)
            if len(by_flag) > 2:
                compact_row["by_kernel_flag_omitted"] = len(by_flag) - 2
        compact[str(key)] = compact_row
    return compact


def _summary_compact_thought_trace(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    command_trace = [
        _summary_drop_none(
            {
                "command": _truncate(str(row.get("command") or ""), 140) if row.get("command") else None,
                "count": row.get("count"),
            }
        )
        for row in list(value.get("command_trace") or [])[:2]
        if isinstance(row, Mapping)
    ]
    focus_trace = [
        _summary_drop_none(
            {
                "path": _truncate(str(row.get("path") or ""), 120) if row.get("path") else None,
                "count": row.get("count"),
            }
        )
        for row in list(value.get("focus_trace") or [])[:2]
        if isinstance(row, Mapping)
    ]
    candidate_signals = [
        _summary_drop_none(
            {
                "signal": row.get("signal"),
                "count": row.get("count"),
                "command": _truncate(str(row.get("command") or ""), 140) if row.get("command") else None,
                "path": _truncate(str(row.get("path") or ""), 120) if row.get("path") else None,
                "action_kind": row.get("action_kind"),
            }
        )
        for row in list(value.get("candidate_signals") or [])[:2]
        if isinstance(row, Mapping)
    ]
    return {
        "schema_version": value.get("schema_version"),
        "boundary": value.get("boundary"),
        "counters": dict(value.get("counters") or {}),
        "route_trace": dict(value.get("route_trace") or {}),
        "command_trace": command_trace,
        "focus_trace": focus_trace,
        "candidate_signals": candidate_signals,
    }


def _summary_compact_task_result_reads(value: Any, *, limit: int = 4) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"count": 0, "total_output_bytes": 0, "top_reads": []}
    return _summary_drop_none(
        {
            "count": value.get("count"),
            "total_output_bytes": value.get("total_output_bytes"),
            "target_kind_counts": dict(value.get("target_kind_counts") or {}),
            "tag_counts": dict(value.get("tag_counts") or {}),
            "top_reads": [
                _summary_drop_none(
                    {
                        "span_id": row.get("span_id"),
                        "sequence_index": row.get("sequence_index"),
                        "target_kind": row.get("target_kind"),
                        "output_byte_count": row.get("output_byte_count"),
                        "output_line_count": row.get("output_line_count"),
                        "command_shape_tags": list(row.get("command_shape_tags") or [])[:6],
                    }
                )
                for row in list(value.get("top_reads") or [])[:limit]
                if isinstance(row, Mapping)
            ],
            "raw_body_policy": value.get("raw_body_policy"),
            "raw_reopen_route": value.get("raw_reopen_route"),
        }
    )


def _summary_compact_audit_summary(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(summary, Mapping):
        return {}
    return _summary_drop_none(
        {
            "session_count": summary.get("session_count"),
            "claude_count": summary.get("claude_count"),
            "codex_count": summary.get("codex_count"),
            "total_span_count": summary.get("total_span_count"),
            "total_output_bytes": summary.get("total_output_bytes"),
            "finding_count": summary.get("finding_count"),
            "error_count": summary.get("error_count"),
            "warning_count": summary.get("warning_count"),
            "average_route_compliance": summary.get("average_route_compliance"),
            "parse_failure_count": summary.get("parse_failure_count"),
            "window": dict(summary.get("window") or {}),
            "pattern_counts": _summary_top_mapping_items(summary.get("pattern_counts"), limit=6),
            "route_lease_mode_control_counts": _summary_top_mapping_items(
                summary.get("route_lease_mode_control_counts"),
                limit=6,
            ),
            "route_lease_session_count": summary.get("route_lease_session_count"),
            "route_lease_warning_session_count": summary.get("route_lease_warning_session_count"),
        }
    )


def _summary_compact_process_session(session: Mapping[str, Any]) -> dict[str, Any]:
    compliance = session.get("route_compliance") if isinstance(session.get("route_compliance"), Mapping) else {}
    return {
        "session_id": session.get("session_id"),
        "agent": session.get("agent"),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "duration_ms": session.get("duration_ms"),
        "span_count": session.get("span_count"),
        "total_output_bytes": session.get("total_output_bytes"),
        "turn_count": session.get("turn_count"),
        "action_kind_counts": _summary_top_mapping_items(session.get("action_kind_counts"), limit=8),
        "kernel_flag_counts": _summary_top_mapping_items(session.get("kernel_flag_counts"), limit=8),
        "top_normalized_commands": _summary_compact_command_rows(
            list(session.get("top_normalized_commands") or []),
            limit=3,
        ),
        "target_path_hot_list": list(session.get("target_path_hot_list") or [])[:3],
        "task_result_reads": _summary_compact_task_result_reads(session.get("task_result_reads")),
        "chronological_trace_outline": {
            "omitted": True,
            "reason": "process_summary_default_uses_trace_drilldown_for_ordered_outline",
            "drilldown": f"./repo-python kernel.py --process-trace {session.get('session_id')}",
        },
        "route_compliance": {
            "score": compliance.get("score"),
            "ladder_position": compliance.get("ladder_position"),
            "deviation_count": compliance.get("deviation_count"),
            "ladder_rungs_hit": list(compliance.get("ladder_rungs_hit") or [])[:12],
        },
        "anti_patterns": _summary_compact_pattern_rows(list(session.get("anti_patterns") or []), limit=3),
        "bottleneck_preview": _summary_compact_bottleneck_preview(
            list(session.get("bottleneck_preview") or []),
            limit=2,
        ),
        "summary_thought_trace": _summary_compact_thought_trace(session.get("summary_thought_trace")),
    }


def _summary_compact_process_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    summary = audit.get("summary") if isinstance(audit.get("summary"), Mapping) else {}
    return {
        "summary": _summary_compact_audit_summary(summary),
        "slow_action_shapes": _summary_compact_audit_findings(
            [
                row
                for row in list(audit.get("findings") or [])
                if isinstance(row, Mapping) and row.get("rule") == "slow_action_shape"
            ],
            limit=2,
        ),
        "top_patterns": _summary_compact_pattern_rows(list(audit.get("patterns") or []), limit=2),
        "top_bottlenecks": _summary_compact_process_bottlenecks(
            audit.get("bottlenecks"),
            limit=2,
            example_limit=0,
        ),
        "context_yield_top_motifs": [
            {
                "motif": row.get("motif"),
                "active_bytes": row.get("active_bytes"),
                "span_count": row.get("span_count"),
                "owner_surface": row.get("owner_surface"),
                "next_wave_score": row.get("next_wave_score"),
            }
            for row in list((audit.get("context_yield_attribution") or {}).get("rows") or [])[:2]
            if isinstance(row, Mapping)
        ],
        "parse_failure_count": len(audit.get("parse_failures") or []),
    }


def _summary_compact_source_freshness(source_freshness: Mapping[str, Any]) -> dict[str, Any]:
    receipt = source_freshness.get("source_hash_receipt")
    compact_receipt: dict[str, Any] = {}
    if isinstance(receipt, Mapping):
        projections = [row for row in list(receipt.get("projections") or []) if isinstance(row, Mapping)]
        static_sources = [row for row in list(receipt.get("static_sources") or []) if isinstance(row, Mapping)]
        compact_receipt = _summary_drop_none(
            {
                "schema_version": receipt.get("schema_version"),
                "profile": "compact_paths_counts_and_static_hash",
                "projection_count": len(projections),
                "static_source_count": len(static_sources),
                "projection_paths": [row.get("path") for row in projections if row.get("path")],
                "static_source_paths": [row.get("path") for row in static_sources if row.get("path")],
                "static_source_hash_sha256": receipt.get("static_source_hash_sha256"),
                "validity_scope": receipt.get("validity_scope"),
                "dynamic_rollouts_revalidated": receipt.get("dynamic_rollouts_revalidated"),
            }
        )
    return _summary_drop_none(
        {
            "schema_version": source_freshness.get("schema_version"),
            "mode": source_freshness.get("mode"),
            "status": source_freshness.get("status"),
            "ok": source_freshness.get("ok"),
            "generated_at": source_freshness.get("generated_at"),
            "age_seconds": source_freshness.get("age_seconds"),
            "static_source_status": source_freshness.get("static_source_status"),
            "dynamic_rollout_status": source_freshness.get("dynamic_rollout_status"),
            "requested_window": dict(source_freshness.get("requested_window") or {}),
            "wall_ms": source_freshness.get("wall_ms"),
            "source_hash_receipt": compact_receipt,
            "refresh_command": source_freshness.get("refresh_command"),
            "force_live_command": source_freshness.get("force_live_command"),
            "warnings": list(source_freshness.get("warnings") or []),
        }
    )


def _summary_compact_warning_index(warnings: Iterable[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for warning in warnings:
        if not isinstance(warning, Mapping):
            continue
        warning_id = warning.get("warning_id")
        if not warning_id:
            continue
        rows.append({
            "warning_id": warning_id,
            "detail_ref": "identity_scope.warnings",
        })
    return rows


def _process_summary_identity_scope(raw: str, session: Mapping[str, Any]) -> dict[str, Any]:
    request = str(raw or "latest").strip().lower()
    selected_session_id = session.get("session_id")
    selected_agent = session.get("agent")
    if request in {"", "latest"}:
        selection_basis = "latest_ended_session"
        current_session_claim = "not_claimed"
        concurrency_posture = "not_self_identity_safe"
        warning_reason = (
            "`latest` selects the newest completed process trace; concurrent sibling "
            "seeds can make that a different agent's session."
        )
    elif request in {"codex", "codex:latest", "claude", "claude:latest"}:
        selection_basis = "agent_latest_ended_session"
        current_session_claim = "not_claimed"
        concurrency_posture = "agent_scoped_not_self_identity_safe"
        warning_reason = (
            f"`{raw}` selects the newest completed trace for that agent family, "
            "not necessarily this live wake."
        )
    else:
        selection_basis = "explicit_session_id"
        current_session_claim = "explicit_user_or_callsite_selection"
        concurrency_posture = "explicit_trace_selection"
        warning_reason = ""
    warnings = []
    if warning_reason:
        warnings.append({
            "warning_id": "process_summary_latest_alias_not_self_identity",
            "reason": warning_reason,
            "safe_action": (
                "Treat the selected session as evidence only after checking selected_session_id/selected_agent, "
                "or rerun with an explicit session id."
            ),
        })
    return {
        "schema_version": PROCESS_SUMMARY_IDENTITY_SCOPE_SCHEMA_VERSION,
        "request_alias": raw or "latest",
        "selection_basis": selection_basis,
        "selected_session_id": selected_session_id,
        "selected_agent": selected_agent,
        "current_session_claim": current_session_claim,
        "concurrency_posture": concurrency_posture,
        "safe_trace_command": f"./repo-python kernel.py --process-trace {selected_session_id}",
        "warnings": warnings,
    }


def _read_model_receipt(path: Path, *, repo_root: Path) -> dict[str, Any]:
    return {
        "path": _relpath(path, repo_root=repo_root),
        "exists": path.exists(),
        "sha256": _file_sha256(path),
        "mtime": _file_mtime_iso(path),
    }


def _process_summary_age_seconds(payload: Mapping[str, Any] | None) -> float | None:
    generated_dt = _parse_iso(str((payload or {}).get("generated_at") or ""))
    if generated_dt is None:
        return None
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - generated_dt).total_seconds(), 3)


def _default_process_session_limit(repo_root: Path) -> int:
    try:
        rules = load_trace_rules(repo_root / TRACE_RULES_PATH.relative_to(REPO_ROOT))
        return int(((rules.get("ingest") or {}).get("default_session_lookback_count")) or 20)
    except Exception:
        return 20


def _effective_process_session_limit(repo_root: Path, session_limit: int | None) -> int:
    if session_limit is not None:
        return session_limit
    return _default_process_session_limit(repo_root)


def _process_summary_window_matches(
    payload: Mapping[str, Any],
    *,
    since_ts: str | None,
    session_limit: int | None,
) -> bool:
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    window = summary.get("window") if isinstance(summary.get("window"), Mapping) else {}
    return window.get("since") == since_ts and _summary_int(window.get("session_limit")) == _summary_int(session_limit)


def _process_summary_cached_read_models(
    *,
    repo_root: Path,
    since_ts: str | None,
    session_limit: int | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    ledger_path = repo_root / LEDGER_PATH.relative_to(REPO_ROOT)
    audit_path = repo_root / AUDIT_PATH.relative_to(REPO_ROOT)
    summary_path = repo_root / SUMMARY_PATH.relative_to(REPO_ROOT)
    standard_path = repo_root / STANDARD_PATH.relative_to(REPO_ROOT)
    rules_path = repo_root / TRACE_RULES_PATH.relative_to(REPO_ROOT)

    ledger = _safe_read_json(ledger_path)
    audit = _safe_read_json(audit_path)
    summary = _safe_read_json(summary_path)
    source_receipts = [_read_model_receipt(path, repo_root=repo_root) for path in (standard_path, rules_path)]
    projection_receipts = [_read_model_receipt(path, repo_root=repo_root) for path in (ledger_path, audit_path, summary_path)]
    static_hash = hashlib.sha256(
        json.dumps(source_receipts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    status = "hit"
    warnings: list[str] = []
    ok = True

    if not isinstance(ledger, Mapping):
        status = "missing_or_malformed_ledger"
        warnings.append("Process ledger projection is missing or malformed; refresh or rerun with --force.")
        ok = False
    if not isinstance(audit, Mapping):
        status = "missing_or_malformed_audit"
        warnings.append("Process audit projection is missing or malformed; refresh or rerun with --force.")
        ok = False
    if not isinstance(summary, Mapping):
        status = "missing_or_malformed_summary"
        warnings.append("Process summary projection is missing or malformed; refresh or rerun with --force.")
        ok = False

    if ok:
        windows_match = all(
            _process_summary_window_matches(payload, since_ts=since_ts, session_limit=session_limit)
            for payload in (ledger, audit, summary)
            if isinstance(payload, Mapping)
        )
        if not windows_match:
            status = "window_mismatch"
            warnings.append("Cached process read models were generated for a different --after/--limit window.")
            ok = False

    source_mtimes = []
    for path in (standard_path, rules_path):
        try:
            source_mtimes.append(path.stat().st_mtime)
        except OSError:
            warnings.append(f"Static source missing: {_relpath(path, repo_root=repo_root)}")
            ok = False
            status = "static_source_missing"
    projection_mtimes = []
    for path in (ledger_path, audit_path, summary_path):
        try:
            projection_mtimes.append(path.stat().st_mtime)
        except OSError:
            pass
    static_source_status = "unknown"
    if source_mtimes and projection_mtimes:
        static_source_status = "current" if min(projection_mtimes) >= max(source_mtimes) else "stale_static_sources"
        if static_source_status != "current":
            status = "stale_readable_static_sources"
            warnings.append("Static trace rules or standard changed after one or more process projections.")

    freshness = {
        "schema_version": "process_summary_read_model_freshness_v1",
        "mode": "cached_read_model",
        "status": status,
        "ok": ok,
        "generated_at": (summary or ledger or audit or {}).get("generated_at") if ok else None,
        "age_seconds": _process_summary_age_seconds(summary if isinstance(summary, Mapping) else None),
        "static_source_status": static_source_status,
        "dynamic_rollout_status": "not_revalidated_cached_projection_read",
        "requested_window": {"since": since_ts, "session_limit": session_limit},
        "source_hash_receipt": {
            "schema_version": "process_summary_source_hash_receipt_v0",
            "projections": projection_receipts,
            "static_sources": source_receipts,
            "static_source_hash_sha256": static_hash,
            "validity_scope": "static_rules_and_cached_projection_files_only",
            "dynamic_rollouts_revalidated": False,
        },
        "refresh_command": PROCESS_TRACE_REFRESH_COMMAND,
        "force_live_command": "./repo-python kernel.py --process-summary latest --force",
        "warnings": warnings,
    }
    if not ok:
        return None, None, None, freshness
    return dict(ledger), dict(audit), dict(summary), freshness


def _process_summary_force_command(
    request: str,
    *,
    since_ts: str | None = None,
    session_limit: int | None = None,
) -> str:
    command = f"./repo-python kernel.py --process-summary {request} --force"
    if since_ts:
        command += f" --after {since_ts}"
    if session_limit is not None:
        command += f" --limit {session_limit}"
    return command


def _build_process_summary_packet_from_models(
    *,
    ledger: Mapping[str, Any],
    audit: Mapping[str, Any],
    request: str,
    sources: Mapping[str, Any],
    source_freshness: Mapping[str, Any],
    since_ts: str | None = None,
    command_session_limit: int | None = None,
) -> tuple[int, dict[str, Any]]:
    session = select_session(ledger, request)
    if session is None:
        alt = [
            {"session_id": row.get("session_id"), "agent": row.get("agent"), "ended_at": row.get("ended_at")}
            for row in (ledger.get("sessions") or [])[:10]
            if isinstance(row, Mapping)
        ]
        return 1, {
            "kind": "kernel.navigate.process_summary",
            "schema_version": PROCESS_SUMMARY_ROUTE_SCHEMA_VERSION,
            "query": {"command": "process-summary", "request": request},
            "source_freshness": dict(source_freshness),
            "error": (
                f"No session matches {request!r}. Run `./repo-python tools/meta/factory/build_agent_execution_trace.py` "
                "to refresh the ledger, or rerun with --force for a live rebuild."
            ),
            "alternatives": alt,
        }

    audit_summary = dict((audit.get("summary") or {}))
    identity_scope = _process_summary_identity_scope(request, session)
    full_trace_command = f"./repo-python kernel.py --process-trace {session.get('session_id')}"
    live_summary_command = _process_summary_force_command(
        request,
        since_ts=since_ts,
        session_limit=command_session_limit,
    )
    return 0, {
        "kind": "kernel.navigate.process_summary",
        "schema_version": PROCESS_SUMMARY_ROUTE_SCHEMA_VERSION,
        "query": {
            "command": "process-summary",
            "request": request,
            "force_live": str(source_freshness.get("mode") or "") == "live_in_memory",
        },
        "identity_scope": identity_scope,
        "summary": {
            "session_id": session.get("session_id"),
            "agent": session.get("agent"),
            "span_count": session.get("span_count"),
            "duration_ms": session.get("duration_ms"),
            "route_compliance_score": (session.get("route_compliance") or {}).get("score"),
            "ladder_position": (session.get("route_compliance") or {}).get("ladder_position"),
            "audit_warning_count": audit_summary.get("warning_count"),
            "audit_error_count": audit_summary.get("error_count"),
            "audit_finding_count": audit_summary.get("finding_count"),
        },
        "source_freshness": _summary_compact_source_freshness(source_freshness),
        "sources": dict(sources),
        "payload": {
            "session": _summary_compact_process_session(session),
            "audit_summary": _summary_compact_process_audit(audit),
            "next_reads": list((sources.get("derived") if isinstance(sources, Mapping) else []) or []),
            "output_economy": {
                "profile": "compact_owner_route",
                "default_target_bytes": 16000,
                "raw_bodies_omitted": True,
                "default_authority": "metadata_counts_and_bounded_examples_only",
                "omitted_fields": [
                    "session.spans",
                    "session.turns",
                    "session.chronological_trace_outline.rows",
                    "audit.findings",
                    "audit.full_bottleneck_examples",
                    "audit.bottlenecks.full_by_kernel_flag_rows",
                    "summary_thought_trace.full_candidate_signals",
                    "source_freshness.full_per_file_hash_receipts",
                ],
                "full_authority_commands": [
                    full_trace_command,
                    live_summary_command,
                    "./repo-python kernel.py --process-audit",
                ],
            },
        },
        "next": [
            {
                "command": full_trace_command,
                "reason": "Drill into the full selected session only after the compact packet identifies the need.",
            },
            {
                "command": live_summary_command,
                "reason": "Force a live in-memory rebuild when the cached read model is not fresh enough for the decision.",
            },
            {
                "command": "./repo-python kernel.py --process-bottlenecks",
                "reason": "Browse the bounded bottleneck packet if latency shapes are the chosen axis.",
            },
            {
                "command": "./repo-python kernel.py --process-patterns",
                "reason": "Browse recurring anti-patterns when process repetition is the chosen axis.",
            },
        ],
        "warnings": _summary_compact_warning_index(identity_scope.get("warnings") or []),
    }


def _missing_process_summary_status_packet(
    *,
    request: str,
    sources: Mapping[str, Any],
    source_freshness: Mapping[str, Any],
    force_live_command: str,
) -> dict[str, Any]:
    return {
        "kind": "kernel.navigate.process_summary",
        "schema_version": PROCESS_SUMMARY_ROUTE_SCHEMA_VERSION,
        "query": {
            "command": "process-summary",
            "request": request,
            "force_live": False,
        },
        "summary": {
            "status": "missing_cached_summary",
            "selected_session_id": None,
            "selected_agent": None,
            "session_available": False,
            "authority": "status_only_no_live_rollout_parse",
        },
        "source_freshness": source_freshness,
        "sources": dict(sources),
        "payload": {
            "status": "missing_cached_summary",
            "reason": "Cached process summary read models are unavailable for this window.",
            "output_economy": {
                "profile": "compact_missing_read_model_status",
                "default_authority": "freshness_receipt_and_pressure_safe_followups_only",
                "raw_bodies_omitted": True,
                "live_rollout_parse_started": False,
                "omitted_fields": [
                    "session.spans",
                    "session.turns",
                    "audit.findings",
                    "audit.full_bottleneck_examples",
                    "raw rollout bodies",
                ],
            },
            "pressure_safe_fallbacks": [
                "./repo-python kernel.py --latency-seed-digest --latency-seed-no-git",
                "./repo-python kernel.py --process-bottlenecks",
            ],
        },
        "next": [
            {
                "command": "./repo-python kernel.py --latency-seed-digest --latency-seed-no-git",
                "reason": "Use the pressure-safe latency digest when process read models are absent.",
            },
            {
                "command": "./repo-python kernel.py --process-bottlenecks",
                "reason": "Use the cached speedboard-backed bottleneck triage packet without live rollout parsing.",
            },
            {
                "command": force_live_command,
                "reason": "Force authoritative live rollout parsing only when the decision needs session-scoped detail.",
            },
            {
                "command": PROCESS_TRACE_REFRESH_COMMAND,
                "reason": "Refresh the cached process summary read model when host pressure allows.",
            },
        ],
        "warnings": list(source_freshness.get("warnings") or []),
    }


def build_process_summary_route_packet(
    *,
    repo_root: Path = REPO_ROOT,
    request: str | None = None,
    since_ts: str | None = None,
    session_limit: int | None = None,
    force_live: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Build the kernel --process-summary packet from cached read models unless --force is explicit."""
    repo_root = repo_root.resolve()
    raw = (request or "latest").strip() or "latest"
    sources = _process_trace_sources(repo_root)
    started = time.perf_counter()
    effective_session_limit = _effective_process_session_limit(repo_root, session_limit)
    default_session_limit = _default_process_session_limit(repo_root)
    command_session_limit = session_limit if session_limit is not None and session_limit != default_session_limit else None
    force_live_command = _process_summary_force_command(
        raw,
        since_ts=since_ts,
        session_limit=command_session_limit,
    )
    if force_live:
        payload = build_agent_execution_trace(repo_root=repo_root, since_ts=since_ts, session_limit=effective_session_limit)
        source_freshness = {
            "schema_version": "process_summary_read_model_freshness_v1",
            "mode": "live_in_memory",
            "status": "fresh",
            "ok": True,
            "generated_at": (payload.get("summary") or payload.get("ledger") or {}).get("generated_at"),
            "age_seconds": 0.0,
            "wall_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "dynamic_rollout_status": "revalidated_live_in_memory",
            "requested_window": {"since": since_ts, "session_limit": effective_session_limit},
            "refresh_command": PROCESS_TRACE_REFRESH_COMMAND,
            "force_live_command": force_live_command,
            "warnings": [],
        }
        return _build_process_summary_packet_from_models(
            ledger=payload["ledger"],
            audit=payload["audit"],
            request=raw,
            sources=sources,
            source_freshness=source_freshness,
            since_ts=since_ts,
            command_session_limit=command_session_limit,
        )

    ledger, audit, _summary, source_freshness = _process_summary_cached_read_models(
        repo_root=repo_root,
        since_ts=since_ts,
        session_limit=effective_session_limit,
    )
    source_freshness["wall_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
    source_freshness["force_live_command"] = force_live_command
    if ledger is None or audit is None:
        status = str(source_freshness.get("status") or "")
        if status.startswith("missing_or_malformed_"):
            return 0, _missing_process_summary_status_packet(
                request=raw,
                sources=sources,
                source_freshness=source_freshness,
                force_live_command=force_live_command,
            )
        return 1, {
            "kind": "kernel.navigate.process_summary",
            "schema_version": PROCESS_SUMMARY_ROUTE_SCHEMA_VERSION,
            "query": {
                "command": "process-summary",
                "request": raw,
                "force_live": False,
            },
            "source_freshness": source_freshness,
            "error": "Cached process summary read model is unavailable for this window; rerun with --force for live rebuild or refresh the projection.",
            "next": [
                {
                    "command": force_live_command,
                    "reason": "Force authoritative live rollout parsing for this request.",
                },
                {
                    "command": PROCESS_TRACE_REFRESH_COMMAND,
                    "reason": "Refresh the cached process summary read model.",
                },
            ],
            "warnings": list(source_freshness.get("warnings") or []),
        }
    return _build_process_summary_packet_from_models(
        ledger=ledger,
        audit=audit,
        request=raw,
        sources=sources,
        source_freshness=source_freshness,
        since_ts=since_ts,
        command_session_limit=command_session_limit,
    )


def build_process_trace_route_packet(
    *,
    repo_root: Path = REPO_ROOT,
    request: str | None = None,
    since_ts: str | None = None,
    session_limit: int | None = None,
    trace_level: str = "tape",
    include_tape: bool = False,
    tape_max_chars: int = 10000,
    include_raw_sidecar: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Build a chronological command/output/edit trace packet for one session."""
    repo_root = repo_root.resolve()
    raw = (request or "latest").strip() or "latest"
    selected_level = _normalize_trace_level(trace_level)
    if selected_level not in set(TRACE_COMPACTNESS_PROFILES):
        return 2, {
            "kind": "kernel.navigate.process_trace",
            "schema_version": "process_trace_route_v2",
            "query": {"command": "process-trace", "request": raw, "trace_level": selected_level},
            "error": f"Unknown trace compactness level {selected_level!r}.",
            "available_levels": list(TRACE_COMPACTNESS_PROFILES),
        }
    effective_session_limit = _effective_process_session_limit(repo_root, session_limit)
    payload = build_agent_execution_trace(
        repo_root=repo_root,
        since_ts=since_ts,
        session_limit=effective_session_limit,
    )
    ledger = payload["ledger"]
    session = select_session(ledger, raw)
    sources = _process_trace_sources(repo_root)
    if session is None:
        alt = [
            {"session_id": row.get("session_id"), "agent": row.get("agent"), "ended_at": row.get("ended_at")}
            for row in (ledger.get("sessions") or [])[:10]
            if isinstance(row, Mapping)
        ]
        return 1, {
            "kind": "kernel.navigate.process_trace",
            "schema_version": "process_trace_route_v2",
            "query": {"command": "process-trace", "request": raw, "trace_level": selected_level},
            "error": (
                f"No session matches {raw!r}. Run `./repo-python tools/meta/factory/build_agent_execution_trace.py` "
                "to refresh the ledger."
            ),
            "alternatives": alt,
        }
    session_id = str(session.get("session_id") or "")
    span_rows = list((payload.get("spans_by_session") or {}).get(session_id) or [])
    compactness = build_trace_compactness_levels(
        span_rows,
        session_id=session_id,
        selected_level=selected_level,
        session=session,
    )
    compliance = session.get("route_compliance") if isinstance(session.get("route_compliance"), Mapping) else {}
    session_header = _summary_drop_none(
        {
            "session_id": session.get("session_id"),
            "agent": session.get("agent"),
            "started_at": session.get("started_at"),
            "ended_at": session.get("ended_at"),
            "duration_ms": session.get("duration_ms"),
            "span_count": session.get("span_count"),
            "total_output_bytes": session.get("total_output_bytes"),
            "turn_count": session.get("turn_count"),
            "action_kind_counts": _summary_top_mapping_items(session.get("action_kind_counts"), limit=8),
            "kernel_flag_counts": _summary_top_mapping_items(session.get("kernel_flag_counts"), limit=8),
            "route_compliance": {
                "score": compliance.get("score"),
                "ladder_position": compliance.get("ladder_position"),
                "deviation_count": compliance.get("deviation_count"),
                "ladder_rungs_hit": list(compliance.get("ladder_rungs_hit") or [])[:12],
            },
        }
    )
    artifacts = build_trace_tape_artifacts(
        span_rows,
        session=session_header,
        selected_level=selected_level,
        tape_max_chars=tape_max_chars,
        include_raw_sidecar=include_raw_sidecar,
    )
    trace_tape = artifacts["trace.tape.txt"]["content"] if include_tape else None
    closeout_summary = _trace_closeout_summary(span_rows, session=session_header)
    payload = _summary_drop_none(
        {
            "session": session_header,
            "trace_compactness": compactness,
            "closeout": closeout_summary,
            "trace_tape": trace_tape,
            "artifacts": artifacts if include_tape or include_raw_sidecar or selected_level in {"audit", "raw"} else None,
            "output_economy": {
                "profile": "chronological_command_output_edit_trace",
                "raw_bodies_omitted": True,
                "default_level": "tape",
                "selected_level": selected_level,
                "raw_span_rows_omitted": True,
                "raw_span_reopen_route": f"./repo-python tools/meta/factory/build_agent_execution_trace.py --json --limit {effective_session_limit}",
            },
            "next_reads": list((sources.get("derived") if isinstance(sources, Mapping) else []) or []),
        }
    )
    return 0, {
        "kind": "kernel.navigate.process_trace",
        "schema_version": "process_trace_route_v2",
        "query": {
            "command": "process-trace",
            "request": raw,
            "trace_level": selected_level,
            "after": since_ts,
            "limit": effective_session_limit,
        },
        "summary": {
            "session_id": session.get("session_id"),
            "agent": session.get("agent"),
            "span_count": session.get("span_count"),
            "duration_ms": session.get("duration_ms"),
            "total_output_bytes": session.get("total_output_bytes"),
            "route_compliance_score": (session.get("route_compliance") or {}).get("score"),
            "ladder_position": (session.get("route_compliance") or {}).get("ladder_position"),
        },
        "sources": sources,
        "payload": {
            **payload,
        },
        "next": [
            {
                "command": f"./repo-python kernel.py --process-trace {session_id} --process-trace-level closeout",
                "reason": "Show what this agent worked on, changed, validated, committed, and where exact closeout prose can be reopened.",
            },
            {
                "command": f"./repo-python kernel.py --process-trace {session_id} --process-trace-level outline",
                "reason": "Show only final action counts and edit totals.",
            },
            {
                "command": f"./repo-python kernel.py --process-trace {session_id} --process-trace-level tape+diff",
                "reason": "Show every observed action with bounded edit hunks.",
            },
            {
                "command": "./repo-python kernel.py --process-bottlenecks",
                "reason": "Browse aggregate latency/output pressure by action shape.",
            },
        ],
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Public build / write entry points
# ---------------------------------------------------------------------------
def load_process_bottleneck_summary_cache(
    *,
    repo_root: Path = REPO_ROOT,
    limit: int | None = None,
    action_kinds: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Read the materialized process bottleneck summary without parsing rollouts."""
    started = time.perf_counter()
    repo_root = repo_root.resolve()
    summary_path = repo_root / SUMMARY_PATH.relative_to(REPO_ROOT)
    standard_path = repo_root / STANDARD_PATH.relative_to(REPO_ROOT)
    rules_path = repo_root / TRACE_RULES_PATH.relative_to(REPO_ROOT)
    source_paths = [standard_path, rules_path]
    warnings: list[str] = []

    def rel(path: Path) -> str:
        return _relpath(path, repo_root=repo_root)

    source_receipts = [
        {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": _file_sha256(path),
            "mtime": _file_mtime_iso(path),
        }
        for path in source_paths
    ]
    summary, projection_receipt = _safe_read_json_with_receipt(
        summary_path,
        repo_root=repo_root,
    )
    status = "available"
    ok = True
    session_count = 0
    if not isinstance(summary, Mapping):
        status = "missing_or_malformed_projection"
        ok = False
        warnings.append(
            "Process summary projection is missing or malformed; this cached-summary probe is the cheap proof, "
            "and materialization should wait until host pressure allows it."
        )
        summary = {}
    else:
        payload_summary = summary.get("summary")
        top_bottlenecks = summary.get("top_bottlenecks")
        top_output_producers = summary.get("top_output_producers")
        malformed_summary_scalar = False
        if isinstance(payload_summary, Mapping):
            try:
                session_count = int(payload_summary.get("session_count") or 0)
            except (TypeError, ValueError):
                malformed_summary_scalar = True
            if session_count < 0:
                malformed_summary_scalar = True
        if (
            not isinstance(payload_summary, Mapping)
            or not isinstance(top_bottlenecks, list)
            or (top_output_producers is not None and not isinstance(top_output_producers, list))
            or malformed_summary_scalar
        ):
            status = "missing_or_malformed_projection"
            ok = False
            session_count = 0
            warnings.append(
                "Process summary projection has an invalid shape; this cached-summary probe is the cheap proof, "
                "and materialization should wait until host pressure allows it."
            )
            summary = {}

    source_mtimes = []
    for path in source_paths:
        try:
            source_mtimes.append(path.stat().st_mtime)
        except OSError:
            warnings.append(f"Static source missing: {rel(path)}")
            ok = False
    try:
        projection_mtime = summary_path.stat().st_mtime
    except OSError:
        projection_mtime = 0.0

    static_source_status = "unknown"
    if source_mtimes and projection_mtime:
        static_source_status = "current" if projection_mtime >= max(source_mtimes) else "stale_static_sources"
        if static_source_status != "current":
            if ok:
                status = "stale_static_sources"
            warnings.append("Static trace rules or standard changed after the process summary projection.")

    requested_action_kinds = []
    seen_action_kinds: set[str] = set()
    for raw_action_kind in action_kinds or []:
        action_kind = str(raw_action_kind).strip()
        if not action_kind or action_kind in seen_action_kinds:
            continue
        seen_action_kinds.add(action_kind)
        requested_action_kinds.append(action_kind)

    row_limit = None
    if limit is not None and limit > 0:
        row_limit = int(limit)
    source_rows = list(summary.get("top_bottlenecks") or [])
    source_output_rows = list(summary.get("top_output_producers") or [])
    rows = source_rows
    output_rows = source_output_rows
    if requested_action_kinds:
        requested_set = set(requested_action_kinds)
        rows = [
            row
            for row in source_rows
            if isinstance(row, Mapping) and row.get("action_kind") in requested_set
        ]
        output_rows = [
            row
            for row in source_output_rows
            if isinstance(row, Mapping) and row.get("action_kind") in requested_set
        ]
    if row_limit is not None:
        rows = rows[:row_limit]
        output_rows = output_rows[:row_limit]
    matched_action_kinds = sorted(
        {
            str(row.get("action_kind"))
            for row in rows + output_rows
            if isinstance(row, Mapping) and row.get("action_kind")
        }
    )
    action_kind_filter = None
    if requested_action_kinds:
        action_kind_filter = {
            "requested": requested_action_kinds,
            "matched": matched_action_kinds,
            "missing": [
                action_kind
                for action_kind in requested_action_kinds
                if action_kind not in matched_action_kinds
            ],
            "source_top_bottleneck_count": len(source_rows),
            "source_top_output_producer_count": len(source_output_rows),
            "filtered_top_bottleneck_count": len(rows),
            "filtered_top_output_producer_count": len(output_rows),
        }

    cache_check_command_parts = [
        "./repo-python",
        "tools/meta/factory/build_agent_execution_trace.py",
        "--cached-summary",
    ]
    if row_limit is not None:
        cache_check_command_parts.extend(["--limit", str(row_limit)])
    for action_kind in requested_action_kinds:
        cache_check_command_parts.extend(["--action-kind", action_kind])
    cache_check_command = " ".join(cache_check_command_parts)

    static_source_hash = hashlib.sha256(
        json.dumps(source_receipts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    probe = {
        "schema_version": "process_bottleneck_summary_probe_v0",
        "probe_ok": True,
        "read_model_available": ok,
        "read_model_status": status,
        "default_cli_exit_code": 0,
        "check_cli_exit_code": 0 if ok else 1,
        "pressure_policy": "cache_check_before_live_rebuild",
        "meaning": (
            "The cached-summary command is a cheap probe. probe_ok=true means "
            "the probe completed without parsing live rollouts; ok/read_model_available "
            "state whether the cached read model can support bottleneck ranking."
        ),
    }
    decision_authority = {
        "schema_version": "process_bottleneck_summary_cache_decision_v0",
        "status": "cached_summary_available" if ok else "read_model_missing_or_invalid",
        "read_model_available": ok,
        "read_model_status": status,
        "safe_now": "cached_summary_read" if ok else "cache_probe_only",
        "quote_loop_required": False,
        "safe_first_command": cache_check_command,
        "host_pressure_check_command": PROCESS_TRACE_HOST_PRESSURE_CHECK_COMMAND,
        "pressure_safe_fallback_command": PROCESS_TRACE_PRESSURE_SAFE_DIGEST_COMMAND,
        "materialize_when_pressure_allows_command": PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
        "status_after_materialize_command": PROCESS_BOTTLENECK_BOUNDED_STATUS_COMMAND,
        "authoritative_decision_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
        "reentry_condition": (
            "Use this cached-summary probe as the terminal cheap read. If the read model is missing under "
            "host pressure, stay on the no-git latency digest; after pressure clears, materialize the bounded "
            "process summary, read bounded process bottlenecks, and force live only when current rankings are required."
        ),
        "privacy": PROCESS_METADATA_PRIVACY_BOUNDARY,
    }
    return {
        "kind": "agent_execution_trace_cached_bottleneck_summary",
        "schema_version": CACHED_BOTTLENECK_SUMMARY_SCHEMA_VERSION,
        "generated_at": _utc_iso(),
        "ok": ok,
        "probe_ok": True,
        "probe": probe,
        "status": status,
        "decision_authority": decision_authority,
        "query": {
            "limit": row_limit,
            **({"action_kinds": requested_action_kinds} if requested_action_kinds else {}),
        },
        "summary": {
            "row_count": len(rows),
            "source_row_count": len(source_rows),
            "session_count": session_count,
            "wall_ms": elapsed_ms,
            "static_source_status": static_source_status,
            "dynamic_rollout_status": "not_revalidated_cached_projection_read",
            **(
                {"filtered_action_kind_count": len(matched_action_kinds)}
                if requested_action_kinds
                else {}
            ),
        },
        "payload": {
            "top_bottlenecks": rows,
            "top_output_producers": output_rows,
            **({"action_kind_filter": action_kind_filter} if action_kind_filter else {}),
            "source_summary": dict(summary.get("summary") or {}),
        },
        "source_hash_receipt": {
            "schema_version": "process_bottleneck_summary_source_hash_receipt_v0",
            "projection": projection_receipt,
            "static_sources": source_receipts,
            "static_source_hash_sha256": static_source_hash,
            "validity_scope": "static_rules_and_projection_file_only",
            "dynamic_rollouts_revalidated": False,
        },
        "refresh": {
            "command": PROCESS_TRACE_MATERIALIZE_COMMAND,
            "materialize_read_model_command": PROCESS_TRACE_MATERIALIZE_COMMAND,
            "bounded_materialize_read_model_command": PROCESS_TRACE_BOUNDED_MATERIALIZE_COMMAND,
            "bounded_status_command": PROCESS_BOTTLENECK_BOUNDED_STATUS_COMMAND,
            "cache_check_command": cache_check_command,
            "pressure_safe_first_command": cache_check_command,
            "host_pressure_check_command": PROCESS_TRACE_HOST_PRESSURE_CHECK_COMMAND,
            "pressure_safe_fallback_command": PROCESS_TRACE_PRESSURE_SAFE_DIGEST_COMMAND,
            "status_kernel_command": "./repo-python kernel.py --process-bottlenecks",
            "live_kernel_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            "force_live_kernel_command": PROCESS_BOTTLENECK_FORCE_LIVE_COMMAND,
            "why": (
                "Use cache/status commands under host pressure; materialize the read model when pressure allows; "
                "force live only when the decision requires authoritative current rankings."
            ),
        },
        "warnings": warnings,
    }


def build_agent_execution_trace(
    *,
    repo_root: Path = REPO_ROOT,
    rules_path: Path | None = None,
    home: Path | None = None,
    session_files_claude: list[Path] | None = None,
    session_files_codex: list[Path] | None = None,
    since_ts: str | None = None,
    session_limit: int | None = None,
    timestamp: str | None = None,
    include_output_previews: bool = True,
    include_context_yield_attribution: bool = True,
    aggregate_action_kinds: Sequence[str] | None = None,
    parse_codex_output_payloads: bool = True,
    build_profile: str = "full",
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    bottleneck_rankings_profile = build_profile == "bottleneck_rankings"
    rules = load_trace_rules(rules_path or (repo_root / TRACE_RULES_PATH.relative_to(REPO_ROOT)))
    home = (home or Path.home()).resolve()
    if session_limit is None:
        session_limit = int(((rules.get("ingest") or {}).get("default_session_lookback_count")) or 20)
    hard_cap = int(((rules.get("ingest") or {}).get("hard_session_cap")) or 200)
    session_limit = min(session_limit, hard_cap)

    if session_files_claude is None:
        session_files_claude = discover_claude_sessions(
            repo_root=repo_root, home=home, since_ts=since_ts, limit=session_limit
        )
    if session_files_codex is None:
        session_files_codex = discover_codex_sessions(home=home, since_ts=since_ts, limit=session_limit)

    session_rows: list[dict[str, Any]] = []
    spans_by_session: dict[str, list[dict[str, Any]]] = {}
    findings: list[dict[str, Any]] = []
    parse_failures: list[dict[str, Any]] = []

    for path in session_files_claude:
        try:
            result = parse_claude_session(
                path,
                repo_root=repo_root,
                rules=rules,
                include_output_previews=include_output_previews,
                strict_json=not bottleneck_rankings_profile,
                finalize_profile=build_profile,
            )
        except Exception as exc:  # noqa: BLE001 - defensive parser boundary
            parse_failures.append({"session_path": _relpath(path, repo_root=repo_root), "error": str(exc)[:300]})
            findings.append({
                "severity": "warning",
                "rule": "session_parse_error",
                "session_id": path.stem,
                "message": f"Failed to parse Claude session {path.name}: {exc}",
            })
            continue
        if result is None:
            continue
        session_rows.append(result["session"])
        spans_by_session[result["session"]["session_id"]] = result["spans"]

    for path in session_files_codex:
        try:
            result = parse_codex_session(
                path,
                repo_root=repo_root,
                rules=rules,
                include_output_previews=include_output_previews,
                parse_output_payloads=parse_codex_output_payloads,
                strict_json=not bottleneck_rankings_profile,
                finalize_profile=build_profile,
            )
        except Exception as exc:  # noqa: BLE001
            parse_failures.append({"session_path": _relpath(path, repo_root=repo_root), "error": str(exc)[:300]})
            findings.append({
                "severity": "warning",
                "rule": "session_parse_error",
                "session_id": path.stem,
                "message": f"Failed to parse Codex session {path.name}: {exc}",
            })
            continue
        if result is None:
            continue
        session_rows.append(result["session"])
        spans_by_session[result["session"]["session_id"]] = result["spans"]

    session_rows.sort(key=lambda row: str(row.get("ended_at") or ""), reverse=True)

    # --------- aggregate audit: bottlenecks, findings, patterns ---------
    aggregate_durations: dict[str, list[int]] = defaultdict(list)
    aggregate_output_bytes: dict[str, list[int]] = defaultdict(list)
    aggregate_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    aggregate_spans: list[dict[str, Any]] = []
    kernel_flag_durations: dict[str, list[int]] = defaultdict(list)
    kernel_flag_output_bytes: dict[str, list[int]] = defaultdict(list)
    aggregate_cutoff = _parse_iso(since_ts)
    aggregate_action_kind_filter = {
        str(action_kind or "").strip()
        for action_kind in (aggregate_action_kinds or [])
        if str(action_kind or "").strip()
    }
    aggregate_observed_span_count = 0
    aggregate_observed_output_bytes = 0
    for row in session_rows:
        session_id = str(row.get("session_id") or "")
        for span in spans_by_session.get(session_id, []):
            if not isinstance(span, Mapping):
                continue
            if not _span_at_or_after(span, aggregate_cutoff):
                continue
            kind = str(span.get("action_kind") or "unknown_tool")
            duration_ms = int(span.get("duration_ms") or 0)
            output_byte_count = int(span.get("output_byte_count") or 0)
            aggregate_observed_span_count += 1
            aggregate_observed_output_bytes += output_byte_count
            if aggregate_action_kind_filter and kind not in aggregate_action_kind_filter:
                continue
            aggregate_durations[kind].append(duration_ms)
            aggregate_output_bytes[kind].append(output_byte_count)
            if kind == "kernel_command":
                primary_flag = _pick_primary_kernel_flag(span.get("kernel_flags") or [])
                if primary_flag:
                    kernel_flag_durations[primary_flag].append(duration_ms)
                    kernel_flag_output_bytes[primary_flag].append(output_byte_count)
            example = {
                "session_id": session_id,
                "span_id": span.get("span_id"),
                "action_kind": kind,
                "duration_ms": duration_ms,
                "normalized_command": span.get("normalized_command"),
                "target_paths": list((span.get("target_paths") or [])[:2]),
                "outcome": span.get("outcome"),
                "output_byte_count": output_byte_count,
                "output_line_count": int(span.get("output_line_count") or 0),
                "start_ts": span.get("start_ts"),
                "end_ts": span.get("end_ts"),
                "sequence_index": span.get("sequence_index"),
            }
            if include_context_yield_attribution:
                example["command_shape_tags"] = _command_shape_tags(
                    kind,
                    str(span.get("command") or span.get("normalized_command") or ""),
                    example["target_paths"],
                )
            aggregate_examples[kind].append(example)
            aggregate_spans.append(example)
    aggregate_bottlenecks: dict[str, Any] = {}
    thresholds = rules.get("slow_action_thresholds_ms") or {}
    for kind, durs in aggregate_durations.items():
        threshold = int(thresholds.get(kind) or thresholds.get("default") or 20000)
        repair_hint_spans = list(aggregate_examples.get(kind) or [])
        example_spans = sorted(
            repair_hint_spans,
            key=lambda row: int(row.get("duration_ms") or 0),
            reverse=True,
        )[:3]
        output_example_spans = sorted(
            aggregate_examples.get(kind) or [],
            key=lambda row: int(row.get("output_byte_count") or 0),
            reverse=True,
        )[:3]
        if not include_context_yield_attribution:
            example_spans = _ensure_examples_command_shape_tags(example_spans)
            output_example_spans = _ensure_examples_command_shape_tags(output_example_spans)
            repair_hint_spans = example_spans
        aggregate_bottlenecks[kind] = {
            "count": len(durs),
            "p50_ms": _percentile(durs, 0.5),
            "p95_ms": _percentile(durs, 0.95),
            "max_ms": max(durs) if durs else 0,
            "total_duration_ms": sum(durs),
            "slow_count": sum(1 for duration_ms in durs if duration_ms > threshold),
            "threshold_ms": threshold,
            "total_output_bytes": sum(aggregate_output_bytes.get(kind) or []),
            "max_output_bytes": max(aggregate_output_bytes.get(kind) or [0]),
            "p95_output_bytes": _percentile(aggregate_output_bytes.get(kind) or [0], 0.95),
            "example_spans": example_spans,
            "repair_hints": _bottleneck_repair_hints(kind, repair_hint_spans or example_spans),
            "output_example_spans": output_example_spans,
            "output_repair_hints": _bottleneck_repair_hints(kind, output_example_spans),
            **_bottleneck_actionability(kind, example_spans),
        }
        if aggregate_bottlenecks[kind]["p95_ms"] > threshold:
            findings.append({
                "severity": "warning",
                "rule": "slow_action_shape",
                "action_kind": kind,
                "message": f"Action kind {kind!r} p95 {aggregate_bottlenecks[kind]['p95_ms']}ms exceeds threshold {threshold}ms.",
                "repair_kind": "skill_or_kernel_helper",
                "repair_surface": "tools/meta/agent_telemetry/extract.py (for command shape) or codex/doctrine/skills/kernel/",
            })

    if "kernel_command" in aggregate_bottlenecks and kernel_flag_durations:
        kernel_threshold = int(aggregate_bottlenecks["kernel_command"].get("threshold_ms") or 0) or int(
            (thresholds.get("kernel_command") or thresholds.get("default") or 20000)
        )
        flag_rows: list[dict[str, Any]] = []
        for flag, durs in kernel_flag_durations.items():
            bytes_list = kernel_flag_output_bytes.get(flag) or [0]
            flag_rows.append({
                "kernel_flag": flag,
                "count": len(durs),
                "p50_ms": _percentile(durs, 0.5),
                "p95_ms": _percentile(durs, 0.95),
                "max_ms": max(durs) if durs else 0,
                "total_duration_ms": sum(durs),
                "slow_count": sum(1 for d in durs if d > kernel_threshold),
                "threshold_ms": kernel_threshold,
                "total_output_bytes": sum(bytes_list),
                "max_output_bytes": max(bytes_list) if bytes_list else 0,
                "p95_output_bytes": _percentile(bytes_list, 0.95),
            })
        flag_rows.sort(key=lambda r: (r.get("p95_ms") or 0, r.get("slow_count") or 0), reverse=True)
        aggregate_bottlenecks["kernel_command"]["by_kernel_flag"] = flag_rows[:10]
        flag_repair_hints = _kernel_flag_repair_hints(flag_rows, limit=3)
        if flag_repair_hints:
            aggregate_bottlenecks["kernel_command"]["repair_hints"] = _merge_repair_hints_by_id(
                flag_repair_hints,
                aggregate_bottlenecks["kernel_command"].get("repair_hints") or [],
            )

    aggregate_patterns: dict[str, dict[str, Any]] = defaultdict(lambda: {"instances": 0, "session_id_hits": []})
    for row in session_rows:
        for ap in row.get("anti_patterns") or []:
            pid = str(ap.get("pattern_id") or "")
            if not pid:
                continue
            agg = aggregate_patterns[pid]
            agg["pattern_id"] = pid
            agg["severity"] = ap.get("severity")
            agg["instances"] = int(agg.get("instances", 0)) + 1
            agg.setdefault("session_id_hits", []).append(row.get("session_id"))
            agg["representative_example"] = ap
    patterns_list = list(aggregate_patterns.values())
    patterns_list.sort(key=lambda entry: entry.get("instances", 0), reverse=True)
    for entry in patterns_list:
        if str(entry.get("severity")) in {"warning", "error"} and int(entry.get("instances", 0)) >= 1:
            findings.append({
                "severity": entry["severity"],
                "rule": "anti_pattern_detected",
                "pattern_id": entry["pattern_id"],
                "message": f"Anti-pattern {entry['pattern_id']!r} fired in {entry['instances']} session(s).",
                "repair_kind": "skill_or_adapter_refresh",
                "repair_surface": "codex/doctrine/skills/kernel/navigation_seed.md or CLAUDE.md",
            })

    mode_control = _aggregate_mode_control(session_rows)
    for signal in mode_control.get("signals") or []:
        signal_id = str(signal.get("signal_id") or "")
        if not signal_id:
            continue
        if signal_id in {"entry_lease_issued", "legitimate_return_to_kernel", "route_lease_unconsumed"}:
            continue
        findings.append({
            "severity": "warning",
            "rule": "route_lease_mode_control_signal",
            "signal_id": signal_id,
            "message": f"Route-lease mode-control signal {signal_id!r} fired {int(signal.get('count') or 0)} time(s).",
            "repair_kind": "process_audit_mode_control",
            "repair_surface": "system/lib/agent_execution_trace.py",
        })

    for row in session_rows:
        rc = row.get("route_compliance") or {}
        score = float(rc.get("score") or 0.0)
        floor = float(rules.get("route_compliance_floor_warning") or 0.5)
        if score < floor:
            findings.append({
                "severity": "warning",
                "rule": "route_non_compliance",
                "session_id": row.get("session_id"),
                "message": f"Session {row.get('session_id')} route_compliance={score:.2f} below floor {floor:.2f}.",
                "repair_kind": "agent_orientation",
                "repair_surface": "codex/doctrine/skills/kernel/navigation_seed.md",
            })

    generated_at = timestamp or _utc_iso()
    aggregate_total_span_count = len(aggregate_spans)
    aggregate_total_output_bytes = sum(
        int(row.get("output_byte_count") or 0)
        for row in aggregate_spans
        if isinstance(row, Mapping)
    )
    summary = {
        "session_count": len(session_rows),
        "claude_count": sum(1 for r in session_rows if r.get("agent") == "claude_code"),
        "codex_count": sum(1 for r in session_rows if r.get("agent") == "codex"),
        "total_span_count": aggregate_total_span_count,
        "total_output_bytes": aggregate_total_output_bytes,
        "finding_count": len(findings),
        "error_count": sum(1 for f in findings if str(f.get("severity")) == "error"),
        "warning_count": sum(1 for f in findings if str(f.get("severity")) == "warning"),
        "pattern_counts": {str(p["pattern_id"]): int(p.get("instances", 0)) for p in patterns_list},
        "route_lease_mode_control_counts": dict(mode_control.get("signal_counts") or {}),
        "route_lease_session_count": int(mode_control.get("lease_session_count") or 0),
        "route_lease_warning_session_count": int(mode_control.get("warning_session_count") or 0),
        "average_route_compliance": (
            round(statistics.fmean(float((r.get("route_compliance") or {}).get("score") or 0.0) for r in session_rows), 3)
            if session_rows else 0.0
        ),
        "parse_failure_count": len(parse_failures),
        "window": {"since": since_ts, "session_limit": session_limit},
    }
    if aggregate_action_kind_filter:
        summary["aggregate_filter"] = {
            "action_kinds": sorted(aggregate_action_kind_filter),
            "source_span_count": aggregate_observed_span_count,
            "source_output_bytes": aggregate_observed_output_bytes,
            "filtered_span_count": aggregate_total_span_count,
            "filtered_output_bytes": aggregate_total_output_bytes,
        }
    if not parse_codex_output_payloads:
        summary["codex_output_payload_mode"] = "raw_payload_fast_metrics"
    if build_profile != "full":
        summary["build_profile"] = build_profile
    if include_context_yield_attribution:
        context_yield_attribution = _compute_context_yield_attribution(
            aggregate_spans=aggregate_spans,
            session_rows=session_rows,
            generated_at=generated_at,
        )
    else:
        context_yield_attribution = _skipped_context_yield_attribution(
            aggregate_spans=aggregate_spans,
            session_rows=session_rows,
            generated_at=generated_at,
            reason="caller_requested_bottleneck_rankings_without_context_yield_rows",
        )

    sources = {
        "live": [
            _relpath(repo_root / STANDARD_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / TRACE_RULES_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        ],
        "derived": [
            _relpath(repo_root / LEDGER_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / AUDIT_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / NAVIGATION_CACHE_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / PATTERNS_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
            _relpath(repo_root / SUMMARY_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        ],
        "rollouts": {
            "claude_session_count": len(session_files_claude),
            "codex_session_count": len(session_files_codex),
        },
    }

    ledger = {
        "kind": "agent_execution_trace_ledger",
        "schema_version": LEDGER_SCHEMA_VERSION,
        "generated_at": generated_at,
        "standard": _relpath(repo_root / STANDARD_PATH.relative_to(REPO_ROOT), repo_root=repo_root),
        "summary": summary,
        "sessions": [_bounded_session_row(r) for r in session_rows[: int(((rules.get("ingest") or {}).get("default_session_lookback_count")) or 20)]],
        "sources": sources,
    }

    audit = {
        "kind": "agent_execution_trace_audit",
        "schema_version": AUDIT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "summary": summary,
        "findings": findings,
        "bottlenecks": aggregate_bottlenecks,
        "patterns": patterns_list,
        "context_yield_attribution": context_yield_attribution,
        "mode_control": mode_control,
        "parse_failures": parse_failures,
        "sources": sources,
    }

    navigation_cache = {
        "kind": "agent_execution_trace_navigation_cache",
        "schema_version": NAV_CACHE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "rows": [_nav_row(r) for r in session_rows[:50]],
    }

    patterns_artifact = {
        "kind": "agent_execution_trace_patterns",
        "schema_version": PATTERNS_SCHEMA_VERSION,
        "generated_at": generated_at,
        "patterns": patterns_list,
        "mode_control": mode_control,
    }

    kernel_flag_top_n = int(rules.get("kernel_command_flag_top_n") or 8)
    kernel_command_row = aggregate_bottlenecks.get("kernel_command") or {}
    top_kernel_command_flags = list(kernel_command_row.get("by_kernel_flag") or [])[:kernel_flag_top_n]

    summary_artifact = {
        "kind": "agent_execution_trace_summary",
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_at": generated_at,
        "summary": summary,
        "top_bottlenecks": sorted(
            (
                {"action_kind": k, **v}
                for k, v in aggregate_bottlenecks.items()
            ),
            key=_bottleneck_summary_sort_key,
            reverse=True,
        )[: int(rules.get("bottleneck_top_n") or 10)],
        "top_output_producers": sorted(
            (
                {"action_kind": k, **v}
                for k, v in aggregate_bottlenecks.items()
                if int(v.get("total_output_bytes") or 0) > 0
            ),
            key=lambda row: row.get("total_output_bytes") or 0,
            reverse=True,
        )[: int(rules.get("bottleneck_top_n") or 10)],
        "top_kernel_command_flags": top_kernel_command_flags,
        "top_patterns": patterns_list[: int(rules.get("pattern_top_n") or 10)],
        "context_yield_attribution": context_yield_attribution,
        "sources": sources,
    }

    return {
        "ledger": ledger,
        "audit": audit,
        "navigation_cache": navigation_cache,
        "patterns": patterns_artifact,
        "summary": summary_artifact,
        "sessions_full": session_rows,
        "spans_by_session": spans_by_session,
    }


def _bounded_session_row(row: Mapping[str, Any]) -> dict[str, Any]:
    trimmed = dict(row)
    trimmed.pop("bottlenecks", None)
    return trimmed


def _nav_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": row.get("session_id"),
        "agent": row.get("agent"),
        "started_at": row.get("started_at"),
        "ended_at": row.get("ended_at"),
        "duration_ms": row.get("duration_ms"),
        "span_count": row.get("span_count"),
        "route_compliance": (row.get("route_compliance") or {}).get("score"),
        "ladder_position": (row.get("route_compliance") or {}).get("ladder_position"),
        "kernel_flag_counts": dict(list((row.get("kernel_flag_counts") or {}).items())[:5]),
        "action_kind_counts": dict(list((row.get("action_kind_counts") or {}).items())[:8]),
        "search_text": " ".join(
            [
                str(row.get("session_id") or ""),
                str(row.get("agent") or ""),
                " ".join((row.get("kernel_flag_counts") or {}).keys()),
                " ".join(
                    f"{ap.get('pattern_id','')}" for ap in row.get("anti_patterns", [])
                ),
            ]
        ).lower(),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_agent_execution_trace(
    *,
    repo_root: Path = REPO_ROOT,
    rules_path: Path | None = None,
    home: Path | None = None,
    session_files_claude: list[Path] | None = None,
    session_files_codex: list[Path] | None = None,
    since_ts: str | None = None,
    session_limit: int | None = None,
    timestamp: str | None = None,
    write_state_dir: Path | None = None,
) -> dict[str, Any]:
    payload = build_agent_execution_trace(
        repo_root=repo_root,
        rules_path=rules_path,
        home=home,
        session_files_claude=session_files_claude,
        session_files_codex=session_files_codex,
        since_ts=since_ts,
        session_limit=session_limit,
        timestamp=timestamp,
    )
    out_dir = repo_root / HOLOGRAM_DIR.relative_to(REPO_ROOT)
    _write_json(out_dir / LEDGER_PATH.name, payload["ledger"])
    _write_json(out_dir / AUDIT_PATH.name, payload["audit"])
    _write_json(out_dir / NAVIGATION_CACHE_PATH.name, payload["navigation_cache"])
    _write_json(out_dir / PATTERNS_PATH.name, payload["patterns"])
    _write_json(out_dir / SUMMARY_PATH.name, payload["summary"])

    stamp = (timestamp or _utc_iso()).replace(":", "-")
    state_dir = (write_state_dir or (repo_root / DEFAULT_STATE_DIR.relative_to(REPO_ROOT))) / stamp
    state_dir.mkdir(parents=True, exist_ok=True)
    sessions_jsonl = state_dir / "sessions.jsonl"
    spans_jsonl = state_dir / "spans.jsonl"
    with sessions_jsonl.open("w", encoding="utf-8") as fh:
        for row in payload["sessions_full"]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with spans_jsonl.open("w", encoding="utf-8") as fh:
        for sid, spans in payload["spans_by_session"].items():
            for sp in spans:
                fh.write(json.dumps(sp, ensure_ascii=False) + "\n")

    return {
        "kind": "agent_execution_trace_write_receipt",
        "ledger_path": _relpath(out_dir / LEDGER_PATH.name, repo_root=repo_root),
        "audit_path": _relpath(out_dir / AUDIT_PATH.name, repo_root=repo_root),
        "navigation_cache_path": _relpath(out_dir / NAVIGATION_CACHE_PATH.name, repo_root=repo_root),
        "patterns_path": _relpath(out_dir / PATTERNS_PATH.name, repo_root=repo_root),
        "summary_path": _relpath(out_dir / SUMMARY_PATH.name, repo_root=repo_root),
        "state_sessions_jsonl": _relpath(sessions_jsonl, repo_root=repo_root),
        "state_spans_jsonl": _relpath(spans_jsonl, repo_root=repo_root),
        "summary": dict(payload["summary"].get("summary") or {}) or dict(payload["ledger"].get("summary") or {}),
    }


def load_execution_trace_audit(*, repo_root: Path = REPO_ROOT, build_if_missing: bool = True) -> dict[str, Any]:
    path = repo_root / AUDIT_PATH.relative_to(REPO_ROOT)
    payload = _safe_read_json(path)
    if isinstance(payload, Mapping):
        return dict(payload)
    if build_if_missing:
        return build_agent_execution_trace(repo_root=repo_root)["audit"]
    return {"kind": "agent_execution_trace_audit", "summary": {}, "findings": [], "bottlenecks": {}, "patterns": []}


def load_execution_trace_ledger(*, repo_root: Path = REPO_ROOT, build_if_missing: bool = True) -> dict[str, Any]:
    path = repo_root / LEDGER_PATH.relative_to(REPO_ROOT)
    payload = _safe_read_json(path)
    if isinstance(payload, Mapping):
        return dict(payload)
    if build_if_missing:
        return build_agent_execution_trace(repo_root=repo_root)["ledger"]
    return {"kind": "agent_execution_trace_ledger", "summary": {}, "sessions": []}


def select_session(ledger: Mapping[str, Any], request: str) -> dict[str, Any] | None:
    raw = str(request or "").strip().lower()
    sessions = list(ledger.get("sessions") or [])
    if not sessions:
        return None
    non_empty_sessions = [row for row in sessions if int(row.get("span_count") or 0) > 0]
    if raw in {"latest", ""}:
        return dict((non_empty_sessions or sessions)[0])
    if raw in {"claude:latest", "claude"}:
        fallback = None
        for row in sessions:
            if row.get("agent") == "claude_code":
                if fallback is None:
                    fallback = row
                if int(row.get("span_count") or 0) > 0:
                    return dict(row)
        return dict(fallback) if fallback is not None else None
    if raw in {"codex:latest", "codex"}:
        fallback = None
        for row in sessions:
            if row.get("agent") == "codex":
                if fallback is None:
                    fallback = row
                if int(row.get("span_count") or 0) > 0:
                    return dict(row)
        return dict(fallback) if fallback is not None else None
    for row in sessions:
        if str(row.get("session_id") or "").lower() == raw:
            return dict(row)
    return None


def compare_agents(ledger: Mapping[str, Any]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {
        "claude_code": {"sessions": 0, "total_spans": 0, "avg_route_compliance": 0.0, "grep_share": 0.0, "kernel_share": 0.0, "anti_pattern_counts": Counter()},
        "codex": {"sessions": 0, "total_spans": 0, "avg_route_compliance": 0.0, "grep_share": 0.0, "kernel_share": 0.0, "anti_pattern_counts": Counter()},
    }
    compliance_rolling: dict[str, list[float]] = {"claude_code": [], "codex": []}
    grep_share: dict[str, list[float]] = {"claude_code": [], "codex": []}
    kernel_share: dict[str, list[float]] = {"claude_code": [], "codex": []}
    for row in ledger.get("sessions") or []:
        agent = str(row.get("agent") or "")
        if agent not in buckets:
            continue
        buckets[agent]["sessions"] += 1
        span_count = int(row.get("span_count") or 0) or 1
        buckets[agent]["total_spans"] += int(row.get("span_count") or 0)
        compliance_rolling[agent].append(float((row.get("route_compliance") or {}).get("score") or 0.0))
        ak = row.get("action_kind_counts") or {}
        grep_count = int(ak.get("grep_tool", 0)) + int(ak.get("glob_tool", 0)) + int(ak.get("bash_grep", 0))
        kernel_count = int(ak.get("kernel_command", 0))
        grep_share[agent].append(grep_count / span_count)
        kernel_share[agent].append(kernel_count / span_count)
        for ap in row.get("anti_patterns") or []:
            buckets[agent]["anti_pattern_counts"][str(ap.get("pattern_id") or "")] += 1
    for agent, bucket in buckets.items():
        bucket["avg_route_compliance"] = round(statistics.fmean(compliance_rolling[agent]), 3) if compliance_rolling[agent] else 0.0
        bucket["grep_share"] = round(statistics.fmean(grep_share[agent]), 3) if grep_share[agent] else 0.0
        bucket["kernel_share"] = round(statistics.fmean(kernel_share[agent]), 3) if kernel_share[agent] else 0.0
        bucket["anti_pattern_counts"] = dict(bucket["anti_pattern_counts"])
    return buckets
