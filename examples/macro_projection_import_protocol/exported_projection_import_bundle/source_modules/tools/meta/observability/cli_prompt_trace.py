#!/usr/bin/env python3
"""CLI prompt trace extractor — per-prompt slice of Claude Code / Codex CLI sessions.

For one operator prompt, produce a provenance-preserving compact view of every
tool call and its output in the order the agent ran them. Reads the session
JSONL directly from disk, so it does not depend on opening or expanding command
cards in the live TUI.

Sources (discovered automatically from current cwd's slug):
  - Claude Code: ~/.claude/projects/<slug>/<session-uuid>.jsonl
  - Codex CLI:   ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl

Output modes:
  --format compact  prompt + each tool call (command + truncated output)
  --format full     prompt + each tool call (raw output, no truncation)
  --format thread-closeouts
                    session metadata + exact final closeouts + high-level
                    changed-file/command summary, no tool bodies
  --format json     provider-agnostic envelope (schema cli_prompt_trace_v0)

Selection:
  --latest          most recent turn (default)
  --turn N          1-based index; negative counts from end (--turn -2)
  --list            list all turns with prompt previews
  --check           parseability probe; exits 0/1 with JSON status

Examples:
  ./repo-python tools/meta/observability/cli_prompt_trace.py --latest
  ./repo-python tools/meta/observability/cli_prompt_trace.py --latest --format json
  ./repo-python tools/meta/observability/cli_prompt_trace.py --list
  ./repo-python tools/meta/observability/cli_prompt_trace.py --provider codex --turn -2
  ./repo-python tools/meta/observability/cli_prompt_trace.py --latest -o /tmp/trace.txt
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import difflib
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]
HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
CODEX_SESSIONS_ROOT = HOME / ".codex" / "sessions"

TRACE_STRUCTURER_BASE = HOME / "Library" / "Application Support" / "Agent Trace Structurer"
TRACE_STRUCTURER_CAPTURES = TRACE_STRUCTURER_BASE / "Captures"
TRACE_STRUCTURER_CLIPS = TRACE_STRUCTURER_BASE / "Clips"
TRACE_STRUCTURER_RAW = TRACE_STRUCTURER_BASE / "Raw Sources"
# Exports/AIW Captures is the only dir the macOS app's revealDownloadedFile()
# accepts via isSameOrChild(url, of: downloadsExportURL()). We stage the thin
# clip there so Finder Reveal works without needing a Swift rebuild.
TRACE_STRUCTURER_EXPORTS = TRACE_STRUCTURER_BASE / "Exports" / "AIW Captures"
TRACE_STRUCTURER_HISTORY = TRACE_STRUCTURER_BASE / "clipboard_history.json"
TRACE_STRUCTURER_MISSION_INDEX = TRACE_STRUCTURER_BASE / "mission_index.json"
TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT = (
    TRACE_STRUCTURER_BASE / "mission_index_goal_roster_refresh_receipt.json"
)
TRACE_STRUCTURER_GOAL_FLEET_ACTION_RECEIPT = (
    TRACE_STRUCTURER_BASE / "goal_fleet_action_receipt.json"
)
TRACE_STRUCTURER_MISSION_SUMMARY_CACHE = TRACE_STRUCTURER_BASE / "mission_summary_cache.json"
TRACE_STRUCTURER_TITLE_ALIASES = TRACE_STRUCTURER_BASE / "title_aliases.json"
TRACE_STRUCTURER_VARIANT_ARTIFACTS = TRACE_STRUCTURER_BASE / "Variant Artifacts"
TRACE_STRUCTURER_VARIANT_INDEX = TRACE_STRUCTURER_BASE / "variant_artifact_index.json"
TRACE_STRUCTURER_TYPE_B_SOURCE_CARRIERS = TRACE_STRUCTURER_BASE / "Type B Source Excerpts"
STRUCTURER_PARSER_PATH = REPO_ROOT / "tools" / "agent_trace_structurer" / "parser.mjs"
TRACE_STRUCTURER_NODE_ENV_KEYS = (
    "AIW_TRACE_NODE",
    "AIW_NODE",
    "NODE_BINARY",
    "NODE",
)
TRACE_STRUCTURER_NODE_FALLBACK_PATHS = (
    "/opt/homebrew/bin/node",
    "/usr/local/bin/node",
    "/usr/bin/node",
)
TRACE_STRUCTURER_NODE_PATH_DIRS = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)
CODEX_SESSION_INDEX = HOME / ".codex" / "session_index.jsonl"
CODEX_GOALS_DB = HOME / ".codex" / "goals_1.sqlite"
# Claude desktop app stores operator-edited session titles here, keyed by
# the desktop's own sessionId. Each record carries cliSessionId pointing at
# the corresponding ~/.claude/projects/<slug>/<uuid>.jsonl. Layout:
#   .../claude-code-sessions/<workspace>/<window>/local_<uuid>.json
CLAUDE_DESKTOP_SESSIONS = HOME / "Library" / "Application Support" / "Claude" / "claude-code-sessions"

SCHEMA_VERSION = "cli_prompt_trace_v0"

COMPACT_OUTPUT_TRUNCATE_CHARS = 1500
COMPACT_PROMPT_TRUNCATE_CHARS = 4000
COMPACT_INPUT_PREVIEW_CHARS = 240
JSON_REDACTED_OUTPUT_PREVIEW_CHARS = 240
SESSION_AMBIGUITY_WINDOW_SECONDS = 120
SHORT_PROMPT_CHAIN_WORD_THRESHOLD = 25
TRACE_CAPSULE_CLOSEOUT_CHARS = 2400
TRACE_CLOSEOUT_COMMAND_LIMIT = 25
TRACE_CAPSULE_VISIBLE_NOTE_MAX_CHARS = 4000
TRACE_CAPSULE_COMMAND_RETURN_INLINE_LINES = 36
TRACE_CAPSULE_COMMAND_RETURN_INLINE_BYTES = 6000
TRACE_CAPSULE_COMMAND_RETURN_DECISIVE_LINES = 96
TRACE_CAPSULE_COMMAND_RETURN_DECISIVE_BYTES = 16000
TRACE_CAPSULE_COMMAND_RETURN_EXCERPT_HEAD = 10
TRACE_CAPSULE_COMMAND_RETURN_EXCERPT_TAIL = 6
TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT = 8
TRACE_CAPSULE_SOURCE_EXCERPT_LINES = 120
TRACE_CAPSULE_SOURCE_EXCERPT_BYTES = 24000
TRACE_CAPSULE_SOURCE_EXCERPT_LINE_BYTES = 6000
TRACE_CAPSULE_DECISION_BUNDLE_SOURCE_SLICE_BYTES = TRACE_CAPSULE_SOURCE_EXCERPT_BYTES
TRACE_CAPSULE_DECISION_BUNDLE_TOTAL_SOURCE_BYTES = 120000
TRACE_CAPSULE_PROMPT_FILE_BYTES = 12000
TYPE_B_SOURCE_EXCERPT_SCHEMA_VERSION = "type_b_source_excerpt_v1"
TYPE_B_SOURCE_EXCERPT_CARRIER_SCHEMA_VERSION = "type_b_source_excerpt_carrier_v1"
TRACE_CAPSULE_TYPE_B_SOURCE_AFFORDANCE_ID = "type_b_source_excerpt_available"
TRACE_CAPSULE_TYPE_B_SOURCE_AFFORDANCE_PATH_PREFIXES = (
    "tools/meta/observability/cli_prompt_trace.py",
    "system/server/tests/test_cli_prompt_trace_capsule.py",
    "tools/agent_trace_structurer/",
    "codex/doctrine/skills/doctrine/agent_trace_structurer.md",
    "codex/doctrine/paper_modules/agent_trace_structurer_surface.md",
    "codex/standards/std_agent_trace_lossless_clip.json",
    "system/lib/type_b_candidate_queue.py",
)


def _trace_structurer_node_resolution() -> dict[str, Any]:
    searched: list[dict[str, str]] = []
    for key in TRACE_STRUCTURER_NODE_ENV_KEYS:
        value = (os.environ.get(key) or "").strip()
        if not value:
            continue
        candidate = Path(value).expanduser()
        searched.append({"source": key, "path": str(candidate)})
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return {
                "status": "found",
                "source": key,
                "executable": str(candidate),
                "searched": searched,
            }

    path_hit = shutil.which("node")
    if path_hit:
        searched.append({"source": "PATH", "path": path_hit})
        return {
            "status": "found",
            "source": "PATH",
            "executable": path_hit,
            "searched": searched,
        }

    for path_value in TRACE_STRUCTURER_NODE_FALLBACK_PATHS:
        candidate = Path(path_value)
        searched.append({"source": "fallback", "path": str(candidate)})
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return {
                "status": "found",
                "source": "fallback",
                "executable": str(candidate),
                "searched": searched,
            }

    return {
        "status": "not_found",
        "source": "not_found",
        "executable": "",
        "searched": searched,
    }


def _trace_structurer_node_env() -> dict[str, str]:
    env = dict(os.environ)
    path_parts = [part for part in (env.get("PATH") or "").split(os.pathsep) if part]
    for path_dir in TRACE_STRUCTURER_NODE_PATH_DIRS:
        if path_dir not in path_parts:
            path_parts.append(path_dir)
    env["PATH"] = os.pathsep.join(path_parts)
    return env


CLAUDE_COMPLETE_STOP_REASONS = {"end_turn", "max_tokens", "stop_sequence", "refusal"}
CODEX_EXIT_CODE_RE = re.compile(r"Process exited with code\s+(-?\d+)")

# Conservative secret patterns. Field-level redaction floor; not a full DLP scanner.
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("anthropic_api_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("github_pat", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("authorization_header", re.compile(r"(?i)Authorization\s*:\s*[A-Za-z0-9._~+/=-]{16,}")),
]


def _parse_codex_exit_code(output: str) -> int | None:
    if not output:
        return None
    m = CODEX_EXIT_CODE_RE.search(output)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _redact_secrets(text: str) -> tuple[str, list[str]]:
    """Apply conservative pattern-based redaction. Returns (redacted_text, hit_names)."""
    if not text:
        return text, []
    hits: list[str] = []
    out = text
    for name, pat in SECRET_PATTERNS:
        new_out, n = pat.subn(f"[REDACTED:{name}]", out)
        if n > 0:
            hits.extend([name] * n)
            out = new_out
    return out, hits


def _iso_from_epoch(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat()


def _iso_diff_seconds(a: str, b: str) -> float | None:
    try:
        t1 = _dt.datetime.fromisoformat(a.replace("Z", "+00:00"))
        t2 = _dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
        return abs((t1 - t2).total_seconds())
    except Exception:
        return None


def _iso_timestamp_ms(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return int(_dt.datetime.fromisoformat(text).timestamp() * 1000)
    except Exception:
        return None


def _latest_iso_timestamp(*values: object) -> str:
    latest_value = ""
    latest_ms: int | None = None
    for value in values:
        ms = _iso_timestamp_ms(value)
        if ms is None:
            continue
        if latest_ms is None or ms > latest_ms:
            latest_ms = ms
            latest_value = str(value)
    return latest_value


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _file_tail_sha16(path: Path, *, max_bytes: int = 4096) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > max_bytes:
                f.seek(max(0, size - max_bytes))
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return ""


def _project_slug_for_cwd(cwd: Path) -> str:
    return str(cwd).replace("/", "-").replace("_", "-")


def _resolve_claude_project_dir(cwd: Path) -> Path | None:
    raw = _project_slug_for_cwd(cwd)
    seen: list[Path] = []
    for slug in (raw, raw if raw.startswith("-") else f"-{raw}", raw.lstrip("-")):
        p = CLAUDE_PROJECTS / slug
        if p not in seen:
            seen.append(p)
    for p in seen:
        if p.is_dir():
            return p
    return None


def _iso_diff_ms(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    try:
        t1 = _dt.datetime.fromisoformat(a.replace("Z", "+00:00"))
        t2 = _dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
        return int((t2 - t1).total_seconds() * 1000)
    except Exception:
        return None


@dataclass
class ToolEvent:
    index: int
    name: str
    input: dict
    tool_call_id: str | None
    started_at: str | None
    completed_at: str | None
    duration_ms: int | None
    is_error: bool
    output_text: str
    output_char_count: int
    output_sha256_16: str
    exit_code: int | None = None
    source_record_indices: list[int] = field(default_factory=list)


@dataclass
class AssistantEvent:
    text: str
    source_record_index: int
    timestamp: str | None = None


@dataclass
class Turn:
    provider: str
    session_id: str
    session_file: str
    turn_id: str
    turn_index: int
    cwd: str | None
    started_at: str | None
    completed_at: str | None
    prompt_text: str
    prompt_char_count: int
    prompt_sha256_16: str
    tool_events: list[ToolEvent]
    assistant_text: str
    assistant_events: list[AssistantEvent] = field(default_factory=list)
    is_complete: bool = False
    partial_reason: str | None = None
    last_stop_reason: str | None = None
    source_record_indices: list[int] = field(default_factory=list)
    source_ref: dict = field(default_factory=dict)


# --- Claude parser --- #

def _flatten_claude_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for c in content:
        if not isinstance(c, dict):
            continue
        ct = c.get("type")
        if ct == "text":
            parts.append(c.get("text", ""))
        elif ct == "image":
            parts.append("[image attachment]")
        elif ct == "tool_use":
            parts.append(f"[tool_use {c.get('name')!r}]")
        elif ct == "tool_result":
            inner = c.get("content")
            if isinstance(inner, str):
                parts.append(inner)
            elif isinstance(inner, list):
                for b in inner:
                    if isinstance(b, dict) and b.get("type") == "text":
                        parts.append(b.get("text", ""))
    return "\n".join(p for p in parts if p)


def _is_real_claude_prompt(rec: dict) -> bool:
    if rec.get("type") != "user":
        return False
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        if not content:
            return False
        return not any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content)
    return False


def parse_claude_session(path: Path) -> list[Turn]:
    try:
        stat = path.stat()
        file_size = stat.st_size
        file_mtime = _dt.datetime.fromtimestamp(stat.st_mtime, _dt.timezone.utc).isoformat()
    except Exception:
        file_size = None
        file_mtime = None

    records: list[tuple[int, dict]] = []
    with path.open() as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append((i, json.loads(line)))
            except Exception:
                continue

    session_id = ""
    cwd: str | None = None
    for _, r in records:
        if not session_id and r.get("sessionId"):
            session_id = r["sessionId"]
        if cwd is None and r.get("cwd"):
            cwd = r["cwd"]
        if session_id and cwd:
            break

    # Sequential grouping: a "real prompt" user record opens a turn; every record
    # that follows belongs to that turn until the next real prompt opens a new one.
    # Assistant records carry tool_use blocks but no promptId, so promptId-only grouping
    # would orphan every tool call.
    turn_groups: list[list[tuple[int, dict]]] = []
    cur_group: list[tuple[int, dict]] | None = None
    for idx, r in records:
        if _is_real_claude_prompt(r):
            cur_group = [(idx, r)]
            turn_groups.append(cur_group)
        elif cur_group is not None:
            cur_group.append((idx, r))

    turns: list[Turn] = []
    n_groups = len(turn_groups)
    for ti, recs in enumerate(turn_groups, start=1):
        pid = (recs[0][1].get("promptId") if recs else "") or f"turn_{ti}"
        prompt_text = ""
        prompt_ts: str | None = None
        completed_ts: str | None = None
        assistant_parts: list[str] = []
        assistant_events: list[AssistantEvent] = []
        tool_events: list[ToolEvent] = []
        pending: dict[str, tuple[dict, int, str | None, str]] = {}
        source_indices: list[int] = []
        last_stop_reason: str | None = None
        prompt_record_idx: int | None = None
        last_assistant_idx: int | None = None

        for idx, r in recs:
            source_indices.append(idx)
            rtype = r.get("type")
            ts = r.get("timestamp")
            if rtype == "user":
                msg = r.get("message") or {}
                content = msg.get("content")
                if not prompt_text and _is_real_claude_prompt(r):
                    prompt_text = _flatten_claude_content(content)
                    prompt_ts = ts
                    prompt_record_idx = idx
                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict) or c.get("type") != "tool_result":
                            continue
                        tuid = c.get("tool_use_id")
                        inner = c.get("content")
                        if isinstance(inner, str):
                            output_text = inner
                        elif isinstance(inner, list):
                            output_text = _flatten_claude_content(inner)
                        else:
                            output_text = ""
                        is_error = bool(c.get("is_error"))
                        if tuid and tuid in pending:
                            tool_input, src_idx, used_ts, name = pending.pop(tuid)
                            tool_events.append(ToolEvent(
                                index=0,
                                name=name,
                                input=tool_input,
                                tool_call_id=tuid,
                                started_at=used_ts,
                                completed_at=ts,
                                duration_ms=_iso_diff_ms(used_ts, ts),
                                is_error=is_error,
                                output_text=output_text,
                                output_char_count=len(output_text),
                                output_sha256_16=_sha16(output_text),
                                source_record_indices=[src_idx, idx],
                            ))
                        else:
                            tool_events.append(ToolEvent(
                                index=0,
                                name="?",
                                input={},
                                tool_call_id=tuid,
                                started_at=None,
                                completed_at=ts,
                                duration_ms=None,
                                is_error=is_error,
                                output_text=output_text,
                                output_char_count=len(output_text),
                                output_sha256_16=_sha16(output_text),
                                source_record_indices=[idx],
                            ))
            elif rtype == "assistant":
                msg = r.get("message") or {}
                content = msg.get("content") or []
                completed_ts = ts
                last_assistant_idx = idx
                stop_reason = msg.get("stop_reason")
                if stop_reason:
                    last_stop_reason = stop_reason
                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict):
                            continue
                        if c.get("type") == "text":
                            text = c.get("text", "")
                            assistant_parts.append(text)
                            if str(text).strip():
                                assistant_events.append(AssistantEvent(
                                    text=str(text),
                                    source_record_index=idx,
                                    timestamp=ts,
                                ))
                        elif c.get("type") == "tool_use":
                            tuid = c.get("id") or ""
                            if tuid:
                                pending[tuid] = (
                                    c.get("input") or {},
                                    idx,
                                    ts,
                                    c.get("name") or "?",
                                )

        missing_result_count = len(pending)
        for tuid, (tool_input, src_idx, used_ts, name) in pending.items():
            tool_events.append(ToolEvent(
                index=0,
                name=name,
                input=tool_input,
                tool_call_id=tuid,
                started_at=used_ts,
                completed_at=None,
                duration_ms=None,
                is_error=False,
                output_text="[no result yet — turn in progress or interrupted]",
                output_char_count=0,
                output_sha256_16="",
                source_record_indices=[src_idx],
            ))

        tool_events.sort(key=lambda e: e.started_at or e.completed_at or "")
        for i, e in enumerate(tool_events, start=1):
            e.index = i

        assistant_text = "\n".join(p for p in assistant_parts if p).strip()

        has_successor = ti < n_groups
        if has_successor:
            is_complete = True
            partial_reason: str | None = None
        elif missing_result_count > 0:
            is_complete = False
            partial_reason = f"{missing_result_count} tool call(s) without results"
        elif last_stop_reason in CLAUDE_COMPLETE_STOP_REASONS:
            is_complete = True
            partial_reason = None
        elif last_stop_reason == "tool_use":
            is_complete = False
            partial_reason = "last assistant ended with tool_use; awaiting next assistant turn"
        elif last_stop_reason is None:
            is_complete = False
            partial_reason = "no assistant stop_reason observed yet"
        else:
            is_complete = False
            partial_reason = f"unrecognized stop_reason {last_stop_reason!r}"

        source_ref = {
            "session_file": str(path),
            "session_file_size_bytes": file_size,
            "session_file_mtime_utc": file_mtime,
            "record_count_in_turn": len(source_indices),
            "prompt_record_index": prompt_record_idx,
            "completion_record_index": last_assistant_idx if is_complete else None,
            "missing_result_count": missing_result_count,
            "raw_authority": "provider_session_jsonl",
        }

        turns.append(Turn(
            provider="claude_code",
            session_id=session_id,
            session_file=str(path),
            turn_id=pid,
            turn_index=ti,
            cwd=cwd,
            started_at=prompt_ts,
            completed_at=completed_ts,
            prompt_text=prompt_text,
            prompt_char_count=len(prompt_text),
            prompt_sha256_16=_sha16(prompt_text) if prompt_text else "",
            tool_events=tool_events,
            assistant_text=assistant_text,
            assistant_events=assistant_events,
            is_complete=is_complete,
            partial_reason=partial_reason,
            last_stop_reason=last_stop_reason,
            source_record_indices=source_indices,
            source_ref=source_ref,
        ))

    return turns


# --- Codex parser --- #

def parse_codex_session(path: Path) -> list[Turn]:
    try:
        stat = path.stat()
        file_size = stat.st_size
        file_mtime = _dt.datetime.fromtimestamp(stat.st_mtime, _dt.timezone.utc).isoformat()
    except Exception:
        file_size = None
        file_mtime = None

    records: list[tuple[int, dict]] = []
    with path.open() as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append((i, json.loads(line)))
            except Exception:
                continue

    session_id = ""
    cwd: str | None = None
    for _, r in records:
        if r.get("type") == "session_meta":
            p = r.get("payload") or {}
            session_id = p.get("id") or session_id
            cwd = p.get("cwd") or cwd
            break

    turns: list[Turn] = []
    cur: dict | None = None
    turn_counter = 0

    def _codex_prompt_part(state: dict, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if text.startswith("# AGENTS.md instructions") or text.startswith("<environment_context>"):
            return
        if "<INSTRUCTIONS>" in text and "project-doc" in text:
            return
        if state["prompt_parts"] and state["prompt_parts"][-1] == text:
            return
        if text in state["prompt_parts"]:
            return
        state["prompt_parts"].append(text)

    def _codex_output_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                text = _codex_output_text(item)
                if text:
                    parts.append(text)
            return "\n".join(parts)
        if isinstance(value, dict):
            for key in ("output", "text", "content"):
                if key in value:
                    text = _codex_output_text(value.get(key))
                    if text:
                        return text
            try:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
            except TypeError:
                return str(value)
        return str(value)

    def _finalize(state: dict) -> Turn:
        prompt_text = "\n\n".join(state["prompt_parts"]).strip() or state["prompt_text"]
        events: list[ToolEvent] = []
        missing_outputs = 0
        for ci, (name, args, src_idx, started, call_id) in enumerate(state["calls"], start=1):
            try:
                tool_input = json.loads(args) if args else {}
            except Exception:
                tool_input = {"_raw_arguments": args}
            out_info = state["outputs"].get(call_id)
            if out_info:
                out_text, out_idx, out_ts = out_info
                exit_code = _parse_codex_exit_code(out_text)
                is_error = (exit_code is not None and exit_code != 0)
                events.append(ToolEvent(
                    index=ci,
                    name=name,
                    input=tool_input,
                    tool_call_id=call_id,
                    started_at=started,
                    completed_at=out_ts,
                    duration_ms=_iso_diff_ms(started, out_ts),
                    is_error=is_error,
                    output_text=out_text,
                    output_char_count=len(out_text),
                    output_sha256_16=_sha16(out_text),
                    exit_code=exit_code,
                    source_record_indices=[src_idx, out_idx],
                ))
            else:
                missing_outputs += 1
                events.append(ToolEvent(
                    index=ci,
                    name=name,
                    input=tool_input,
                    tool_call_id=call_id,
                    started_at=started,
                    completed_at=None,
                    duration_ms=None,
                    is_error=False,
                    output_text="[no output recorded]",
                    output_char_count=0,
                    output_sha256_16="",
                    exit_code=None,
                    source_record_indices=[src_idx],
                ))

        assistant_text = state["assistant"] or "\n".join(p for p in state["assistant_parts"] if p).strip()

        is_complete = state["completed_at"] is not None
        if is_complete and missing_outputs > 0:
            partial_reason: str | None = f"{missing_outputs} function_call(s) without function_call_output"
            is_complete = False
        elif is_complete:
            partial_reason = None
        elif missing_outputs > 0:
            partial_reason = f"no task_complete; {missing_outputs} function_call(s) without output"
        else:
            partial_reason = "no task_complete event for this turn_id"

        source_ref = {
            "session_file": str(path),
            "session_file_size_bytes": file_size,
            "session_file_mtime_utc": file_mtime,
            "record_count_in_turn": len(state["source_indices"]),
            "prompt_record_index": None,
            "completion_record_index": None,
            "missing_result_count": missing_outputs,
            "raw_authority": "provider_session_jsonl",
        }

        return Turn(
            provider="codex",
            session_id=session_id,
            session_file=str(path),
            turn_id=state["turn_id"],
            turn_index=state["index"],
            cwd=cwd,
            started_at=state["started_at"],
            completed_at=state["completed_at"],
            prompt_text=prompt_text,
            prompt_char_count=len(prompt_text),
            prompt_sha256_16=_sha16(prompt_text) if prompt_text else "",
            tool_events=events,
            assistant_text=assistant_text,
            assistant_events=[
                AssistantEvent(
                    text=str(row.get("text") or ""),
                    source_record_index=int(row.get("source_record_index") or 0),
                    timestamp=row.get("timestamp"),
                )
                for row in state.get("assistant_events", [])
                if str(row.get("text") or "").strip()
            ],
            is_complete=is_complete,
            partial_reason=partial_reason,
            last_stop_reason=None,
            source_record_indices=state["source_indices"],
            source_ref=source_ref,
        )

    def _new_state(turn_id: str, started: str | None) -> dict:
        return {
            "turn_id": turn_id,
            "index": 0,
            "started_at": started,
            "completed_at": None,
            "prompt_text": "",
            "assistant": "",
            "assistant_parts": [],
            "assistant_events": [],
            "prompt_parts": [],
            "calls": [],
            "outputs": {},
            "source_indices": [],
        }

    for idx, r in records:
        rtype = r.get("type")
        ts = r.get("timestamp")
        payload = r.get("payload") or {}
        ptype = payload.get("type")

        if rtype == "event_msg" and ptype == "task_started":
            if cur is not None:
                turn_counter += 1
                cur["index"] = turn_counter
                turns.append(_finalize(cur))
            cur = _new_state(payload.get("turn_id") or f"turn_{turn_counter + 1}", ts)
            cur["source_indices"].append(idx)
        elif rtype == "event_msg" and ptype == "task_complete":
            if cur is not None:
                cur["completed_at"] = ts
                last = payload.get("last_agent_message")
                if last:
                    cur["assistant"] = last
                    if not cur["assistant_events"] or cur["assistant_events"][-1]["text"] != last:
                        cur["assistant_events"].append({
                            "text": last,
                            "source_record_index": idx,
                            "timestamp": ts,
                        })
                cur["source_indices"].append(idx)
        elif cur is not None:
            cur["source_indices"].append(idx)
            if rtype == "event_msg" and ptype == "user_message":
                _codex_prompt_part(cur, str(payload.get("message") or payload.get("text") or ""))
                continue
            if rtype != "response_item":
                continue
            if ptype == "message":
                role = payload.get("role")
                content = payload.get("content") or []
                parts: list[str] = []
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") in ("input_text", "output_text", "text"):
                            parts.append(c.get("text", ""))
                msg_text = "\n".join(p for p in parts if p)
                if role == "user" and not cur["prompt_text"]:
                    cur["prompt_text"] = msg_text
                if role == "user":
                    _codex_prompt_part(cur, msg_text)
                elif role == "assistant":
                    if msg_text:
                        cur["assistant_parts"].append(msg_text)
                        cur["assistant_events"].append({
                            "text": msg_text,
                            "source_record_index": idx,
                            "timestamp": ts,
                        })
            elif ptype == "function_call":
                cur["calls"].append((
                    payload.get("name") or "?",
                    payload.get("arguments") or "",
                    idx,
                    ts,
                    payload.get("call_id") or "",
                ))
            elif ptype == "function_call_output":
                cid = payload.get("call_id") or ""
                cur["outputs"][cid] = (_codex_output_text(payload.get("output")), idx, ts)
            elif ptype == "custom_tool_call":
                cur["calls"].append((
                    payload.get("name") or "?",
                    payload.get("input") or "",
                    idx,
                    ts,
                    payload.get("call_id") or "",
                ))
            elif ptype == "custom_tool_call_output":
                cid = payload.get("call_id") or ""
                output = _codex_output_text(payload.get("output"))
                try:
                    out_obj = json.loads(output)
                    if isinstance(out_obj, dict):
                        output = _codex_output_text(out_obj.get("output") or output)
                        meta = out_obj.get("metadata") or {}
                        if isinstance(meta, dict) and "exit_code" in meta:
                            output = output.rstrip() + f"\nProcess exited with code {meta.get('exit_code')}"
                except Exception:
                    pass
                cur["outputs"][cid] = (output, idx, ts)

    if cur is not None:
        turn_counter += 1
        cur["index"] = turn_counter
        turns.append(_finalize(cur))

    return turns


# --- Discovery --- #

def find_claude_sessions(cwd: Path) -> list[Path]:
    project_dir = _resolve_claude_project_dir(cwd)
    if not project_dir:
        return []
    return sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def find_codex_sessions(cwd: Path | None = None) -> list[Path]:
    if not CODEX_SESSIONS_ROOT.is_dir():
        return []
    sessions = sorted(
        CODEX_SESSIONS_ROOT.glob("**/rollout-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cwd:
        return sessions
    filtered: list[Path] = []
    for p in sessions[:80]:
        try:
            with p.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        break
                    if rec.get("type") == "session_meta":
                        scwd = (rec.get("payload") or {}).get("cwd")
                        if scwd == str(cwd):
                            filtered.append(p)
                        break
                    if rec.get("type"):
                        break
        except Exception:
            continue
    return filtered or sessions


def _peek_codex_session_id(path: Path) -> str:
    """Pull the canonical session_meta.id from the first record of a Codex rollout."""
    meta = _peek_codex_session_meta(path)
    if meta.get("id"):
        return str(meta["id"])
    return ""


def _peek_codex_session_meta(path: Path) -> dict:
    """Pull a compact, non-body Codex session_meta projection from a rollout."""
    try:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") == "session_meta":
                    payload = rec.get("payload") or {}
                    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
                    subagent = source.get("subagent") if isinstance(source.get("subagent"), dict) else {}
                    thread_spawn = (
                        subagent.get("thread_spawn")
                        if isinstance(subagent.get("thread_spawn"), dict)
                        else {}
                    )
                    parent_thread_id = (
                        payload.get("forked_from_id")
                        or thread_spawn.get("parent_thread_id")
                        or ""
                    )
                    return {
                        "id": str(payload.get("id") or ""),
                        "cwd": str(payload.get("cwd") or ""),
                        "timestamp": str(payload.get("timestamp") or rec.get("timestamp") or ""),
                        "model_provider": str(payload.get("model_provider") or ""),
                        "thread_source": str(payload.get("thread_source") or ""),
                        "forked_from_id": str(payload.get("forked_from_id") or ""),
                        "parent_thread_id": str(parent_thread_id or ""),
                        "agent_nickname": str(
                            payload.get("agent_nickname")
                            or thread_spawn.get("agent_nickname")
                            or ""
                        ),
                        "agent_role": str(
                            payload.get("agent_role")
                            or thread_spawn.get("agent_role")
                            or thread_spawn.get("agent_type")
                            or ""
                        ),
                    }
                if rec.get("type"):
                    return {}
    except Exception:
        pass
    return {}


def _enumerate_candidates(provider: str, cwd: Path) -> list[dict]:
    rows: list[dict] = []
    if provider in ("claude", "auto"):
        for p in find_claude_sessions(cwd):
            try:
                stat = p.stat()
            except Exception:
                continue
            rows.append({
                "provider": "claude_code",
                "session_file": str(p),
                "session_id": p.stem,
                "mtime_epoch": stat.st_mtime,
                "mtime_ns": stat.st_mtime_ns,
                "mtime_utc": _iso_from_epoch(stat.st_mtime),
                "size_bytes": stat.st_size,
            })
    if provider in ("codex", "auto"):
        for p in find_codex_sessions(cwd):
            try:
                stat = p.stat()
            except Exception:
                continue
            meta = _peek_codex_session_meta(p)
            sid = str(meta.get("id") or "") or p.stem
            rows.append({
                "provider": "codex",
                "session_file": str(p),
                "session_id": sid,
                "thread_source": meta.get("thread_source") or "",
                "forked_from_id": meta.get("forked_from_id") or "",
                "parent_thread_id": meta.get("parent_thread_id") or "",
                "agent_nickname": meta.get("agent_nickname") or "",
                "agent_role": meta.get("agent_role") or "",
                "mtime_epoch": stat.st_mtime,
                "mtime_ns": stat.st_mtime_ns,
                "mtime_utc": _iso_from_epoch(stat.st_mtime),
                "size_bytes": stat.st_size,
            })
    rows.sort(key=lambda r: r["mtime_epoch"], reverse=True)
    return rows


def discover_session(
    provider: str,
    cwd: Path,
    session_hint: str | None,
    *,
    allow_ambiguous: bool = False,
) -> tuple[str, Path, str, list[dict]]:
    """Returns (provider, path, selection_reason, ambiguous_peers)."""
    rows = _enumerate_candidates(provider, cwd)
    if not rows:
        raise SystemExit(f"no sessions found for provider={provider} cwd={cwd}")
    if session_hint:
        matches = [r for r in rows if session_hint in r["session_id"] or session_hint in r["session_file"]]
        if not matches:
            ids = ", ".join(r["session_id"][:24] for r in rows[:5])
            raise SystemExit(
                f"no session matches --session {session_hint!r}. "
                f"Recent candidates: {ids}. Run --sessions to see all."
            )
        return (matches[0]["provider"], Path(matches[0]["session_file"]),
                "explicit_session_hint", [])
    if len(rows) == 1:
        return (rows[0]["provider"], Path(rows[0]["session_file"]),
                "single_candidate", [])
    top = rows[0]
    peers: list[dict] = []
    for r in rows[1:8]:
        diff = _iso_diff_seconds(top["mtime_utc"], r["mtime_utc"])
        if diff is not None and diff <= SESSION_AMBIGUITY_WINDOW_SECONDS:
            peers.append(r)
    if peers and not allow_ambiguous:
        lines = [
            f"refusing auto-selection: {len(peers) + 1} sessions updated within "
            f"{SESSION_AMBIGUITY_WINDOW_SECONDS}s for provider={provider} cwd={cwd}.",
            "pin one with --session <id-fragment>, or pass --allow-ambiguous to silently pick the most recent.",
            "candidates:",
        ]
        for c in [top] + peers:
            lines.append(
                f"  {c['provider']:>11}  mtime={c['mtime_utc']}  size_b={c['size_bytes']:>10}  "
                f"id={c['session_id'][:36]}"
            )
        raise SystemExit("\n".join(lines))
    return (top["provider"], Path(top["session_file"]),
            "most_recent_unambiguous" if not peers else "most_recent_ambiguous_allowed", peers)


def list_session_candidates(provider: str, cwd: Path) -> str:
    rows = _enumerate_candidates(provider, cwd)
    lines = [f"{len(rows)} candidate session(s) for provider={provider} cwd={cwd}:"]
    for r in rows[:30]:
        lines.append(
            f"  {r['provider']:>11}  mtime={r['mtime_utc']}  size_b={r['size_bytes']:>10}  "
            f"id={r['session_id'][:40]}  file={r['session_file']}"
        )
    return "\n".join(lines)


def load_turns(provider: str, path: Path) -> list[Turn]:
    if provider == "claude_code":
        return parse_claude_session(path)
    if provider == "codex":
        return parse_codex_session(path)
    raise SystemExit(f"unknown provider {provider}")


def select_turn(turns: list[Turn], *, turn_arg: int | None, active: bool, allow_partial: bool) -> Turn:
    if not turns:
        raise SystemExit("no turns in session")
    if turn_arg is not None:
        if turn_arg < 0:
            idx = len(turns) + turn_arg
        else:
            idx = turn_arg - 1
        if not (0 <= idx < len(turns)):
            raise SystemExit(f"turn index {turn_arg} out of range (have {len(turns)})")
        chosen = turns[idx]
        if not chosen.is_complete and not allow_partial:
            sys.stderr.write(
                f"warning: turn {turn_arg} is partial — {chosen.partial_reason}; "
                f"pass --allow-partial to suppress\n"
            )
        return chosen
    if active:
        return turns[-1]
    for t in reversed(turns):
        if t.is_complete:
            return t
    if allow_partial:
        return turns[-1]
    raise SystemExit(
        f"no completed turn found ({len(turns)} turn(s) in session). "
        f"Latest partial: {turns[-1].partial_reason}. "
        f"Pass --latest-active or --allow-partial to include the in-progress turn."
    )


def _prompt_word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_']+", text or ""))


def _compact_one_line(text: Any, *, limit: int = 120) -> str:
    if text is None:
        return ""
    redacted, _ = _redact_secrets(str(text))
    compact = re.sub(r"\s+", " ", html.unescape(redacted)).strip()
    if limit > 0 and len(compact) > limit:
        return compact[: max(0, limit - 3)].rstrip() + "..."
    return compact


def _prompt_title_from_text(prompt_text: str, *, limit: int = 120) -> str:
    """Derive a human label from an operator prompt when session title metadata is absent."""
    if not prompt_text:
        return ""
    lines = str(prompt_text).splitlines()
    saw_request_header = False
    candidates: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("## my request"):
            saw_request_header = True
            continue
        if lower.startswith("# files mentioned by the user"):
            continue
        if lower.startswith("## screenshot "):
            continue
        if lower.startswith("<image") or lower.startswith("</image"):
            continue
        if lower.startswith("![") or lower.startswith("[image"):
            continue
        if "/temporaryitems/" in lower or "screencaptureui" in lower:
            continue
        if lower.startswith("# agents.md instructions"):
            break
        if lower.startswith("<environment_context>") or lower.startswith("<instructions>"):
            break
        if line.startswith("## ") and not saw_request_header:
            continue
        candidates.append(line)
    if not candidates:
        return ""
    first = candidates[0]
    sentence = re.split(r"(?<=[.!?])\s+", first, maxsplit=1)[0]
    return _compact_one_line(sentence or first, limit=limit)


def _claude_subagent_sidechain_dir(parent_session_file: Path) -> Path:
    return parent_session_file.parent / parent_session_file.stem / "subagents"


def _claude_subagent_sidechain_summaries(parent_session_file: Path) -> list[dict]:
    sidechain_dir = _claude_subagent_sidechain_dir(parent_session_file)
    if not sidechain_dir.is_dir():
        return []
    summaries: list[dict] = []
    for path in sorted(sidechain_dir.glob("agent-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            stat = path.stat()
        except Exception:
            continue
        first: dict | None = None
        attribution_agent = ""
        model = ""
        last_ts = ""
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if first is None:
                        first = rec
                    if rec.get("timestamp"):
                        last_ts = str(rec.get("timestamp"))
                    if rec.get("attributionAgent") and not attribution_agent:
                        attribution_agent = str(rec.get("attributionAgent") or "")
                    msg = rec.get("message") or {}
                    if isinstance(msg, dict) and msg.get("model") and not model:
                        model = str(msg.get("model") or "")
        except Exception:
            continue
        if not isinstance(first, dict):
            continue
        prompt_text = _flatten_claude_content((first.get("message") or {}).get("content"))
        agent_id = str(first.get("agentId") or path.stem.replace("agent-", ""))
        try:
            turns = parse_claude_session(path)
        except Exception:
            turns = []
        latest_turn = turns[-1] if turns else None
        summaries.append({
            "schema": "agent_trace_subagent_sidechain_v1",
            "provider": "claude_code",
            "parent_session_id": str(first.get("sessionId") or parent_session_file.stem),
            "session_id": agent_id,
            "agent_id": agent_id,
            "attribution_agent": _compact_one_line(attribution_agent, limit=40),
            "session_file": str(path),
            "started_at": first.get("timestamp"),
            "completed_at": (latest_turn.completed_at if latest_turn else None) or last_ts or _iso_from_epoch(stat.st_mtime),
            "mtime_utc": _iso_from_epoch(stat.st_mtime),
            "size_bytes": stat.st_size,
            "prompt_sha16": _sha16(prompt_text) if prompt_text else "",
            "prompt_title": _prompt_title_from_text(prompt_text, limit=90),
            "prompt_preview": _compact_one_line(prompt_text, limit=180),
            "turn_count": len(turns),
            "tool_count": sum(len(t.tool_events) for t in turns),
            "error_count": sum(1 for t in turns for e in t.tool_events if e.is_error),
            "status": "completed" if latest_turn and latest_turn.is_complete else "running",
            "model": _compact_one_line(model, limit=48),
        })
    return summaries


_CODEX_SUBAGENT_META_INDEX: dict[str, list[dict]] | None = None


def _codex_subagent_meta_index() -> dict[str, list[dict]]:
    global _CODEX_SUBAGENT_META_INDEX
    if _CODEX_SUBAGENT_META_INDEX is not None:
        return _CODEX_SUBAGENT_META_INDEX
    index: dict[str, list[dict]] = {}
    if not CODEX_SESSIONS_ROOT.is_dir():
        _CODEX_SUBAGENT_META_INDEX = index
        return index
    for path in CODEX_SESSIONS_ROOT.glob("**/rollout-*.jsonl"):
        try:
            stat = path.stat()
        except Exception:
            continue
        meta = _peek_codex_session_meta(path)
        parent_session_id = str(meta.get("parent_thread_id") or meta.get("forked_from_id") or "")
        if not parent_session_id:
            continue
        if str(meta.get("thread_source") or "") != "subagent" and not meta.get("forked_from_id"):
            continue
        child_session_id = str(meta.get("id") or "")
        if not child_session_id:
            continue
        row = {
            "provider": "codex",
            "parent_session_id": parent_session_id,
            "agent_id": child_session_id,
            "agent_nickname": meta.get("agent_nickname") or "",
            "agent_role": meta.get("agent_role") or "",
            "session_file": str(path),
            "started_at": meta.get("timestamp") or "",
            "mtime_utc": _iso_from_epoch(stat.st_mtime),
            "mtime_epoch": stat.st_mtime,
            "size_bytes": stat.st_size,
        }
        index.setdefault(parent_session_id, []).append(row)
    for rows in index.values():
        rows.sort(key=lambda row: float(row.get("mtime_epoch") or 0), reverse=True)
    _CODEX_SUBAGENT_META_INDEX = index
    return index


def _codex_subagent_sidechain_summaries(parent_session_id: str, *, limit: int | None = 24) -> list[dict]:
    parent_key = str(parent_session_id or "").strip()
    if not parent_key:
        return []
    summaries: list[dict] = []
    meta_rows = list(_codex_subagent_meta_index().get(parent_key, []))
    if limit is not None:
        meta_rows = meta_rows[: max(1, limit)]
    for meta in meta_rows:
        path = Path(str(meta.get("session_file") or ""))
        try:
            turns = parse_codex_session(path)
        except Exception:
            turns = []
        latest_turn = turns[-1] if turns else None
        prompt_turn = next((t for t in turns if (t.prompt_text or "").strip()), latest_turn)
        prompt_text = (prompt_turn.prompt_text if prompt_turn else "") or ""
        agent_role = _compact_one_line(meta.get("agent_role") or "", limit=40)
        agent_nickname = _compact_one_line(meta.get("agent_nickname") or "", limit=40)
        summaries.append({
            "schema": "agent_trace_subagent_sidechain_v1",
            "provider": "codex",
            "parent_session_id": parent_key,
            "session_id": meta.get("agent_id") or "",
            "agent_id": meta.get("agent_id") or "",
            "agent_nickname": agent_nickname,
            "attribution_agent": agent_role or agent_nickname,
            "session_file": str(path),
            "started_at": meta.get("started_at") or (latest_turn.started_at if latest_turn else None),
            "completed_at": (latest_turn.completed_at if latest_turn else None) or meta.get("mtime_utc"),
            "mtime_utc": meta.get("mtime_utc") or "",
            "size_bytes": meta.get("size_bytes") or 0,
            "prompt_sha16": _sha16(prompt_text) if prompt_text else "",
            "prompt_title": _prompt_title_from_text(prompt_text, limit=90),
            "prompt_preview": _compact_one_line(prompt_text, limit=180),
            "turn_count": len(turns),
            "tool_count": sum(len(t.tool_events) for t in turns),
            "error_count": sum(1 for t in turns for e in t.tool_events if e.is_error),
            "status": "completed" if latest_turn and latest_turn.is_complete else "running",
            "model": "",
        })
    return summaries


def _relationship_for_subagent_child(sidechain: dict | None, *, provider: str = "") -> dict:
    provider_key = str(provider or (sidechain or {}).get("provider") or "")
    parent_signal = "function_call:spawn_agent" if provider_key == "codex" else "tool_use:Agent"
    child_signal = "codex_subagent_session" if provider_key == "codex" else "claude_sidechain_jsonl"
    if sidechain:
        return {
            "schema": "agent_trace_subagent_relationship_v1",
            "kind": "linked_sidechain",
            "parent_signal": parent_signal,
            "child_signal": child_signal,
            "confidence": "high",
            "match_rule": "same_parent_session_and_prompt_sha16",
        }
    return {
        "schema": "agent_trace_subagent_relationship_v1",
        "kind": "deployment_only",
        "parent_signal": parent_signal,
        "child_signal": "not_found",
        "confidence": "medium",
        "match_rule": "parent_tool_use_only",
    }


def _attach_sidechain_to_deployment(dep: dict, sidechain: dict | None) -> dict:
    out = dict(dep)
    out["relationship"] = _relationship_for_subagent_child(sidechain, provider=str(dep.get("provider") or ""))
    out["relationship_kind"] = out["relationship"]["kind"]
    out["relationship_confidence"] = out["relationship"]["confidence"]
    out["linked_child_trace"] = bool(sidechain)
    if sidechain:
        child_trace = {
            key: sidechain.get(key)
            for key in (
                "schema",
                "provider",
                "session_id",
                "parent_session_id",
                "agent_id",
                "attribution_agent",
                "session_file",
                "started_at",
                "completed_at",
                "mtime_utc",
                "size_bytes",
                "turn_count",
                "tool_count",
                "error_count",
                "status",
                "model",
                "prompt_sha16",
                "prompt_title",
            )
        }
        out["child_trace"] = child_trace
        out["agent_id"] = sidechain.get("agent_id") or out.get("agent_id") or ""
        out["attribution_agent"] = sidechain.get("attribution_agent") or out.get("attribution_agent") or ""
        if sidechain.get("model") and not out.get("model"):
            out["model"] = sidechain["model"]
        out["status"] = sidechain.get("status") or out.get("status") or ""
    return out


def _sidechain_only_deployment(sidechain: dict, deployment_index: int) -> dict:
    label = sidechain.get("prompt_title") or sidechain.get("attribution_agent") or sidechain.get("agent_id") or "Sub-agent trace"
    provider = str(sidechain.get("provider") or "claude_code")
    parent_signal = "function_call:spawn_agent" if provider == "codex" else "missing_or_uncached_tool_use"
    child_signal = "codex_subagent_session" if provider == "codex" else "claude_sidechain_jsonl"
    return {
        "schema": "agent_trace_subagent_deployment_v1",
        "deployment_index": deployment_index,
        "provider": provider,
        "session_id": sidechain.get("parent_session_id") or "",
        "turn_index": None,
        "turn_id": "",
        "tool_index": None,
        "tool_name": "spawn_agent" if provider == "codex" else "Agent",
        "tool_call_id": "",
        "description": "",
        "label": _compact_one_line(label, limit=90),
        "subagent_type": sidechain.get("attribution_agent") or "",
        "model": sidechain.get("model") or "",
        "status": sidechain.get("status") or "",
        "started_at": sidechain.get("started_at"),
        "completed_at": sidechain.get("completed_at"),
        "duration_ms": _iso_diff_ms(sidechain.get("started_at"), sidechain.get("completed_at")),
        "prompt_preview": sidechain.get("prompt_preview") or "",
        "prompt_sha16": sidechain.get("prompt_sha16") or "",
        "prompt_char_count": 0,
        "relationship": {
            "schema": "agent_trace_subagent_relationship_v1",
            "kind": "sidechain_only",
            "parent_signal": parent_signal,
            "child_signal": child_signal,
            "confidence": "medium",
            "match_rule": "sidechain_parent_session_directory",
        },
        "relationship_kind": "sidechain_only",
        "relationship_confidence": "medium",
        "linked_child_trace": True,
        "child_trace": {
            key: sidechain.get(key)
            for key in (
                "schema",
                "provider",
                "session_id",
                "parent_session_id",
                "agent_id",
                "attribution_agent",
                "session_file",
                "started_at",
                "completed_at",
                "mtime_utc",
                "size_bytes",
                "turn_count",
                "tool_count",
                "error_count",
                "status",
                "model",
                "prompt_sha16",
                "prompt_title",
            )
        },
        "agent_id": sidechain.get("agent_id") or "",
        "attribution_agent": sidechain.get("attribution_agent") or "",
    }


def _subagent_deployment_from_tool_event(turn: Turn, ev: ToolEvent, deployment_index: int) -> dict | None:
    tool_name = (ev.name or "").strip()
    input_obj = ev.input if isinstance(ev.input, dict) else {}
    lower_name = tool_name.lower()
    is_codex_spawn = lower_name == "spawn_agent" or lower_name.endswith(".spawn_agent")
    has_subagent_shape = any(k in input_obj for k in ("subagent_type", "agent_type", "description", "prompt", "message"))
    if lower_name not in {"agent", "task"} and not input_obj.get("subagent_type") and not is_codex_spawn:
        return None
    if lower_name == "task" and not has_subagent_shape:
        return None

    description = _compact_one_line(input_obj.get("description") or input_obj.get("task") or "", limit=90)
    prompt_text = str(input_obj.get("prompt") or input_obj.get("message") or input_obj.get("objective") or "")
    prompt_title = _prompt_title_from_text(prompt_text, limit=90)
    subagent_type = _compact_one_line(
        input_obj.get("subagent_type")
        or input_obj.get("agent_type")
        or input_obj.get("agent_role")
        or "",
        limit=40,
    )
    model = _compact_one_line(input_obj.get("model") or "", limit=40)
    label = description or prompt_title or subagent_type or tool_name or "Sub-agent"
    status = "failed" if ev.is_error else ("completed" if ev.completed_at else "running")
    prompt_preview = _compact_one_line(prompt_text, limit=180)
    output_agent_id = ""
    output_nickname = ""
    try:
        output_obj = json.loads(ev.output_text or "")
        if isinstance(output_obj, dict):
            output_agent_id = _compact_one_line(output_obj.get("agent_id") or "", limit=80)
            output_nickname = _compact_one_line(output_obj.get("nickname") or "", limit=40)
    except Exception:
        pass
    return {
        "schema": "agent_trace_subagent_deployment_v1",
        "deployment_index": deployment_index,
        "provider": turn.provider,
        "session_id": turn.session_id,
        "turn_index": turn.turn_index,
        "turn_id": turn.turn_id,
        "tool_index": ev.index,
        "tool_name": tool_name,
        "tool_call_id": ev.tool_call_id or "",
        "description": description,
        "label": label,
        "subagent_type": subagent_type,
        "model": model,
        "status": status,
        "started_at": ev.started_at,
        "completed_at": ev.completed_at,
        "duration_ms": ev.duration_ms,
        "prompt_preview": prompt_preview,
        "prompt_sha16": _sha16(prompt_text) if prompt_text else "",
        "prompt_char_count": len(prompt_text),
        "relationship": _relationship_for_subagent_child(None, provider=turn.provider),
        "relationship_kind": "deployment_only",
        "relationship_confidence": "medium",
        "linked_child_trace": False,
        "agent_id": output_agent_id,
        "agent_nickname": output_nickname,
    }


def _subagent_deployments_for_turn(turn: Turn, *, limit: int | None = None) -> list[dict]:
    deployments: list[dict] = []
    for ev in turn.tool_events:
        dep = _subagent_deployment_from_tool_event(turn, ev, len(deployments) + 1)
        if dep is not None:
            deployments.append(dep)
    if limit is not None:
        return deployments[:limit]
    return deployments


def _subagent_deployment_packet(turns: list[Turn], *, sidechains: list[dict] | None = None, limit: int | None = 24) -> dict:
    deployments: list[dict] = []
    for turn in turns:
        deployments.extend(_subagent_deployments_for_turn(turn))
    sidechain_rows = list(sidechains or [])
    sidechains_by_prompt: dict[str, list[dict]] = {}
    sidechains_by_agent_id: dict[str, dict] = {}
    for sc in sidechain_rows:
        prompt_sha = str(sc.get("prompt_sha16") or "")
        if prompt_sha:
            sidechains_by_prompt.setdefault(prompt_sha, []).append(sc)
        agent_id = str(sc.get("agent_id") or "")
        if agent_id:
            sidechains_by_agent_id[agent_id] = sc
    matched_sidechain_ids: set[str] = set()
    enriched: list[dict] = []
    for dep in deployments:
        prompt_sha = str(dep.get("prompt_sha16") or "")
        agent_id = str(dep.get("agent_id") or "")
        match = None
        if agent_id and sidechains_by_agent_id.get(agent_id):
            match = sidechains_by_agent_id[agent_id]
        elif prompt_sha and sidechains_by_prompt.get(prompt_sha):
            match = sidechains_by_prompt[prompt_sha].pop(0)
        if match and match.get("agent_id"):
            matched_sidechain_ids.add(str(match["agent_id"]))
        enriched.append(_attach_sidechain_to_deployment(dep, match))
    deployments = enriched
    for sc in sidechain_rows:
        agent_id = str(sc.get("agent_id") or "")
        if agent_id and agent_id in matched_sidechain_ids:
            continue
        deployments.append(_sidechain_only_deployment(sc, len(deployments) + 1))
    if not deployments:
        return {"count": 0, "deployments": [], "latest_label": "", "models": [], "linked_trace_count": 0}
    deployments.sort(
        key=lambda dep: (
            str(dep.get("started_at") or dep.get("completed_at") or ""),
            int(dep.get("turn_index") or 0),
            int(dep.get("tool_index") or 0),
        ),
        reverse=True,
    )
    models = sorted({str(dep.get("model") or "") for dep in deployments if dep.get("model")})
    linked_trace_count = sum(1 for dep in deployments if dep.get("linked_child_trace"))
    recent = deployments if limit is None else deployments[: max(1, limit)]
    return {
        "count": len(deployments),
        "deployments": recent,
        "latest_label": str(recent[0].get("label") or ""),
        "models": models,
        "linked_trace_count": linked_trace_count,
        "visible_count": len(recent),
    }


def _subagent_sidechains_for_turn_window(turn: Turn, *, limit: int | None = 24) -> list[dict]:
    if turn.provider == "claude_code" and turn.session_file:
        return _claude_subagent_sidechain_summaries(Path(turn.session_file))
    if turn.provider == "codex" and turn.session_id:
        deployments = _subagent_deployments_for_turn(turn, limit=1)
        if not deployments:
            return []
        return _codex_subagent_sidechain_summaries(turn.session_id, limit=limit)
    return []


def _subagent_packet_for_turn_window(turn: Turn, *, limit: int | None = 24) -> dict:
    return _subagent_deployment_packet(
        [turn],
        sidechains=_subagent_sidechains_for_turn_window(turn, limit=limit),
        limit=limit,
    )


def _capsule_subagent_section_lines(packet: dict) -> list[str]:
    count = int(packet.get("count") or 0)
    if count <= 0:
        return []
    deployments = list(packet.get("deployments") or [])
    linked_count = int(packet.get("linked_trace_count") or 0)
    visible_count = int(packet.get("visible_count") or len(deployments))
    lines = [
        "",
        "SUBAGENTS",
        f"summary: count={count} linked_child_traces={linked_count} visible={visible_count} collapsed_under_parent=true",
    ]
    for idx, dep in enumerate(deployments, start=1):
        row_id = f"S{idx:03d}"
        status = _capsule_clean_text(str(dep.get("status") or "unknown"))
        relationship = _capsule_clean_text(str(dep.get("relationship_kind") or "deployment_only"))
        label = _capsule_clean_text(str(dep.get("label") or dep.get("prompt_title") or "Sub-agent")[:120])
        details: list[str] = []
        for key, label_key in (
            ("provider", "provider"),
            ("tool_name", "tool"),
            ("turn_index", "parent_turn"),
            ("agent_id", "child_session"),
            ("subagent_type", "type"),
            ("model", "model"),
        ):
            value = dep.get(key)
            if value is None or value == "":
                continue
            details.append(f"{label_key}={_capsule_clean_text(str(value))}")
        if dep.get("linked_child_trace"):
            details.append("linked_child_trace=true")
        lines.append(f"{row_id} {status} {relationship} {label}" + (f" {' '.join(details)}" if details else ""))
        preview = _capsule_clean_text(str(dep.get("prompt_preview") or "")[:180])
        if preview:
            lines.append(f"{row_id}.prompt_preview: {preview}")
    return lines


def _subagent_child_turn_from_deployment(dep: dict) -> tuple[Turn | None, str]:
    child = dep.get("child_trace") if isinstance(dep.get("child_trace"), dict) else {}
    session_file = str(child.get("session_file") or dep.get("session_file") or "")
    if not session_file:
        return (None, "missing_child_session_file")
    path = Path(session_file)
    if not path.is_file():
        return (None, "child_session_file_not_found")
    provider = str(child.get("provider") or dep.get("provider") or "").strip()
    try:
        if provider == "claude_code":
            turns = parse_claude_session(path)
        elif provider == "codex":
            turns = parse_codex_session(path)
        else:
            return (None, f"unsupported_child_provider:{provider or 'unknown'}")
    except Exception as exc:
        return (None, f"child_parse_failed:{type(exc).__name__}")
    if not turns:
        return (None, "child_session_has_no_turns")
    selected = next((turn for turn in reversed(turns) if turn.is_complete), turns[-1])
    try:
        return (merge_full_thread(full_thread_turns(turns, selected)), "")
    except Exception as exc:
        return (None, f"child_full_thread_merge_failed:{type(exc).__name__}")


def _capsule_subagent_trace_bundle(
    packet: dict,
    *,
    include_prompt_body: bool,
    intern_repeated_prompts: bool,
    depth: int,
    visited: set[str],
) -> tuple[list[str], dict]:
    deployments = [
        dep
        for dep in list(packet.get("deployments") or [])
        if isinstance(dep, dict) and dep.get("linked_child_trace")
    ]
    if not deployments:
        return ([], {
            "schema_version": "agent_trace_subagent_embedded_bundle_v1",
            "mode": "none",
            "count": 0,
            "rendered_count": 0,
            "omitted_count": 0,
            "bytes": 0,
            "depth": depth,
            "rows": [],
        })

    lines = [
        "",
        "SUBAGENT_TRACE_BUNDLE",
        (
            "bundle: schema=agent_trace_subagent_embedded_bundle_v1 "
            f"count={len(deployments)} mode=inline_recursive depth={depth} "
            "source_window=full_thread size_policy=no_limit_operator_requested"
        ),
    ]
    rows: list[dict[str, Any]] = []
    rendered_count = 0
    omitted_count = 0
    total_bytes = 0
    for idx, dep in enumerate(deployments, start=1):
        row_id = f"S{idx:03d}"
        child = dep.get("child_trace") if isinstance(dep.get("child_trace"), dict) else {}
        provider = str(child.get("provider") or dep.get("provider") or "")
        child_session = str(child.get("session_id") or child.get("agent_id") or dep.get("agent_id") or "")
        visit_identity = child_session or str(child.get("session_file") or dep.get("session_file") or "")
        visit_key = f"{provider or 'unknown'}:{visit_identity}" if visit_identity else ""
        label = _capsule_clean_text(str(dep.get("label") or child.get("prompt_title") or "Sub-agent trace")[:160])
        if visit_key and visit_key in visited:
            reason = "cycle_or_duplicate_child_session"
            omitted_count += 1
            rows.append({
                "row_id": row_id,
                "status": "omitted",
                "reason": reason,
                "provider": provider,
                "session_id": child_session,
                "label": label,
            })
            lines.append(f"OMIT_SUBAGENT_TRACE {row_id} provider={provider} child_session={child_session} reason={reason} label={label}")
            continue
        child_turn, reason = _subagent_child_turn_from_deployment(dep)
        if child_turn is None:
            omitted_count += 1
            rows.append({
                "row_id": row_id,
                "status": "omitted",
                "reason": reason,
                "provider": provider,
                "session_id": child_session,
                "label": label,
            })
            lines.append(f"OMIT_SUBAGENT_TRACE {row_id} provider={provider} child_session={child_session} reason={reason} label={label}")
            continue
        child_title = label or _prompt_title_from_text(child_turn.prompt_text) or f"{child_turn.provider} subagent"
        next_visited = set(visited)
        if visit_key:
            next_visited.add(visit_key)
        child_text, child_meta = render_trace_capsule_text(
            child_turn,
            title=child_title,
            source_window="full_thread",
            intern_repeated_prompts=intern_repeated_prompts,
            include_raw_sidecar=True,
            include_prompt_body=include_prompt_body,
            embed_subagent_traces=True,
            _subagent_depth=depth + 1,
            _subagent_visited=next_visited,
        )
        child_bytes = len(child_text.encode("utf-8"))
        total_bytes += child_bytes
        rendered_count += 1
        rows.append({
            "row_id": row_id,
            "status": "embedded",
            "provider": child_turn.provider,
            "session_id": child_turn.session_id,
            "turn_index": child_turn.turn_index,
            "title": child_title,
            "bytes": child_bytes,
            "subagent_count": child_meta.get("subagent_count", 0),
            "embedded_subagent_trace_count": child_meta.get("embedded_subagent_trace_count", 0),
        })
        lines.append(
            f"BEGIN_SUBAGENT_TRACE {row_id} provider={child_turn.provider} "
            f"child_session={child_turn.session_id} turn={child_turn.turn_index} "
            f"bytes={child_bytes} title={_capsule_clean_text(child_title)}"
        )
        lines.append(child_text.rstrip())
        lines.append(f"END_SUBAGENT_TRACE {row_id} provider={child_turn.provider} child_session={child_turn.session_id}")
    lines.append(
        f"bundle_result: rendered={rendered_count} omitted={omitted_count} "
        f"bytes={total_bytes} size_policy=no_limit_operator_requested"
    )
    return (lines, {
        "schema_version": "agent_trace_subagent_embedded_bundle_v1",
        "mode": "inline_recursive",
        "count": len(deployments),
        "rendered_count": rendered_count,
        "omitted_count": omitted_count,
        "bytes": total_bytes,
        "depth": depth,
        "size_policy": "no_limit_operator_requested",
        "rows": rows,
    })


def _workflow_xml_value(text: str, tag: str) -> str:
    match = re.search(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", text or "", re.S)
    if not match:
        return ""
    return html.unescape(match.group(1)).strip()


WORKFLOW_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _workflow_safe_scalar(value: str, *, max_len: int = 2048) -> str:
    text = str(value or "").strip()
    if not text or len(text) > max_len:
        return ""
    if "\x00" in text or "\\n" in text or "\\r" in text:
        return ""
    return text


def _workflow_safe_id(value: str) -> str:
    text = _workflow_safe_scalar(value, max_len=128)
    if not text or not WORKFLOW_SAFE_ID_RE.match(text):
        return ""
    return text


def _workflow_has_standalone_task_notification(text: str) -> bool:
    for line in str(text or "").splitlines():
        if line.strip() == "<task-notification>":
            return True
    return False


def _workflow_label_value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*:\s*([^\n\r]+)", text or "", re.I)
    if not match:
        return ""
    value = _workflow_safe_scalar(match.group(1))
    if not value:
        return ""
    value = re.sub(r"^\|\s*", "", value).strip()
    return value.strip("`\"' ")


def _workflow_int_value(text: str, tag: str) -> int:
    value = _workflow_xml_value(text, tag)
    try:
        return int(value)
    except Exception:
        return 0


def _expand_trace_path(value: str) -> Path | None:
    text = _workflow_safe_scalar(str(value or "").strip(), max_len=4096)
    if not text:
        return None
    text = text.strip("`\"' ")
    if text.startswith("file:"):
        text = text[5:]
    return Path(text).expanduser()


def _workflow_row_key(row: dict) -> str:
    return str(row.get("run_id") or row.get("task_id") or row.get("transcript_dir") or row.get("row_id") or "")


def _merge_workflow_row(target: dict, update: dict) -> None:
    for key, value in update.items():
        if value in ("", None, [], {}):
            continue
        if key in {"agent_count", "subagent_tokens", "tool_uses", "duration_ms"}:
            target[key] = max(int(target.get(key) or 0), int(value or 0))
        elif key == "status":
            current = str(target.get(key) or "")
            incoming = str(value or "")
            if not current or current in {"launched", "notified"} or incoming == "completed":
                target[key] = incoming
        elif not target.get(key):
            target[key] = value
        elif key == "source_event_indices":
            target.setdefault(key, [])
            target[key].extend([idx for idx in value if idx not in target[key]])


def _workflow_execution_rows_for_turn(turn: Turn) -> list[dict]:
    rows: list[dict[str, Any]] = []
    by_key: dict[str, dict] = {}
    by_task_id: dict[str, dict] = {}

    def add_or_merge(row: dict) -> None:
        key = _workflow_row_key(row)
        existing = by_key.get(key) if key else None
        if existing is None and row.get("task_id"):
            existing = by_task_id.get(str(row["task_id"]))
        if existing is not None:
            _merge_workflow_row(existing, row)
            if existing.get("task_id"):
                by_task_id[str(existing["task_id"])] = existing
            if _workflow_row_key(existing):
                by_key[_workflow_row_key(existing)] = existing
            return
        row["row_id"] = f"W{len(rows) + 1:03d}"
        rows.append(row)
        if key:
            by_key[key] = row
        if row.get("task_id"):
            by_task_id[str(row["task_id"])] = row

    evidence_sources: list[tuple[str, int | None, str | None, str | None, str]] = []
    for ev in turn.tool_events:
        event_text = "\n".join(
            part
            for part in [
                ev.output_text or "",
                json.dumps(ev.input, ensure_ascii=False) if isinstance(ev.input, dict) else "",
            ]
            if part
        )
        evidence_sources.append((event_text, ev.index, ev.started_at, ev.completed_at, str(ev.name or "")))
    if turn.assistant_text:
        evidence_sources.append((turn.assistant_text, None, turn.started_at, turn.completed_at, "assistant_text"))
    if turn.prompt_text:
        evidence_sources.append((turn.prompt_text, None, turn.started_at, turn.completed_at, "prompt_text"))

    for text, event_index, started_at, completed_at, source_name in evidence_sources:
        if not text:
            continue
        source_norm = re.sub(r"[^a-z0-9]+", "_", str(source_name or "").strip().lower()).strip("_")
        notification_task_id = _workflow_safe_id(_workflow_xml_value(text, "task-id"))
        launch_source = source_norm == "workflow"
        notification_source = source_norm in {"task_notification", "tasknotification"} or (
            source_norm != "prompt_text" and _workflow_has_standalone_task_notification(text)
        ) or (
            source_norm == "prompt_text"
            and bool(notification_task_id)
            and notification_task_id in by_task_id
        )
        has_launch = (
            launch_source
            and (
                "Workflow launched" in text
                or bool(_workflow_label_value(text, "Transcript dir"))
                or bool(_workflow_label_value(text, "Run ID"))
            )
        )
        has_notification = notification_source and ("<task-notification>" in text or bool(_workflow_xml_value(text, "agent_count")))
        if has_launch:
            task_id = _workflow_safe_id(_workflow_label_value(text, "Task ID"))
            run_id = _workflow_safe_id(_workflow_label_value(text, "Run ID"))
            transcript_dir = _workflow_label_value(text, "Transcript dir")
            script_file = _workflow_label_value(text, "Script file")
            add_or_merge({
                "schema": "agent_trace_child_execution_row_v1",
                "kind": "claude_workflow",
                "provider": turn.provider,
                "origin_provider": turn.provider,
                "execution_engine": "workflow",
                "worker_provider": "claude_code",
                "evidence_plane": "tool_event",
                "parent_session_id": turn.session_id,
                "task_id": task_id,
                "run_id": run_id,
                "transcript_dir": transcript_dir,
                "script_file": script_file,
                "status": "launched",
                "started_at": started_at,
                "completed_at": completed_at,
                "source_event_indices": [event_index] if event_index is not None else [],
            })
        if has_notification:
            task_id = notification_task_id
            output_file = _workflow_xml_value(text, "output-file")
            status = _workflow_xml_value(text, "status")
            summary = _workflow_xml_value(text, "summary")
            add_or_merge({
                "schema": "agent_trace_child_execution_row_v1",
                "kind": "claude_workflow",
                "provider": turn.provider,
                "origin_provider": turn.provider,
                "execution_engine": "workflow",
                "worker_provider": "claude_code",
                "evidence_plane": "task_notification",
                "parent_session_id": turn.session_id,
                "task_id": task_id,
                "output_file": output_file,
                "status": status or "notified",
                "summary": summary,
                "agent_count": _workflow_int_value(text, "agent_count"),
                "subagent_tokens": _workflow_int_value(text, "subagent_tokens"),
                "tool_uses": _workflow_int_value(text, "tool_uses"),
                "duration_ms": _workflow_int_value(text, "duration_ms"),
                "started_at": started_at,
                "completed_at": completed_at,
                "source_event_indices": [event_index] if event_index is not None else [],
            })

    for row in rows:
        row.setdefault("agent_count", 0)
        row.setdefault("subagent_tokens", 0)
        row.setdefault("tool_uses", 0)
        row.setdefault("duration_ms", None)
    return rows


def _workflow_transcript_dir(row: dict, turn: Turn) -> tuple[Path | None, str]:
    explicit = _expand_trace_path(str(row.get("transcript_dir") or ""))
    if explicit is not None:
        return explicit, "declared_transcript_dir"
    run_id = _workflow_safe_id(str(row.get("run_id") or "").strip())
    if row.get("run_id") and not run_id:
        return None, "invalid_workflow_run_id"
    if run_id and turn.session_file:
        parent_file = Path(turn.session_file).expanduser()
        return parent_file.parent / parent_file.stem / "subagents" / "workflows" / run_id, "derived_from_session_file_and_run_id"
    return None, "missing_workflow_transcript_dir"


def _workflow_worker_rows(row: dict, turn: Turn) -> tuple[list[dict], dict]:
    transcript_dir, dir_source = _workflow_transcript_dir(row, turn)
    expected = int(row.get("agent_count") or 0)
    if transcript_dir is None:
        return [], {
            "status": "missing",
            "reason": dir_source,
            "path": "",
            "path_source": dir_source,
            "expected_worker_count": expected,
            "actual_worker_count": 0,
        }
    try:
        transcript_dir_is_dir = transcript_dir.is_dir()
    except OSError as exc:
        return [], {
            "status": "missing",
            "reason": f"workflow_transcript_dir_stat_failed:{type(exc).__name__}",
            "path": _compact_one_line(str(transcript_dir), limit=240),
            "path_source": dir_source,
            "expected_worker_count": expected,
            "actual_worker_count": 0,
        }
    if not transcript_dir_is_dir:
        return [], {
            "status": "missing",
            "reason": "workflow_transcript_dir_missing",
            "path": str(transcript_dir),
            "path_source": dir_source,
            "expected_worker_count": expected,
            "actual_worker_count": 0,
        }
    try:
        worker_paths = sorted(transcript_dir.glob("agent-*.jsonl"), key=lambda p: p.name)
    except OSError as exc:
        return [], {
            "status": "missing",
            "reason": f"workflow_transcript_dir_glob_failed:{type(exc).__name__}",
            "path": _compact_one_line(str(transcript_dir), limit=240),
            "path_source": dir_source,
            "expected_worker_count": expected,
            "actual_worker_count": 0,
        }
    workers: list[dict[str, Any]] = []
    for idx, path in enumerate(worker_paths, start=1):
        agent_id = path.stem.replace("agent-", "")
        meta_path = path.with_suffix(".meta.json")
        agent_type = ""
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            if isinstance(meta, dict):
                agent_type = _compact_one_line(str(meta.get("agentType") or ""), limit=60)
        except Exception:
            agent_type = ""
        prompt_text = ""
        started_at = ""
        completed_at = ""
        try:
            with path.open() as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if isinstance(rec, dict):
                        if not started_at and rec.get("timestamp"):
                            started_at = str(rec.get("timestamp"))
                        if rec.get("timestamp"):
                            completed_at = str(rec.get("timestamp"))
                        if not prompt_text and rec.get("type") == "user":
                            prompt_text = _flatten_claude_content((rec.get("message") or {}).get("content"))
                    if prompt_text and started_at:
                        break
        except Exception:
            pass
        try:
            stat = path.stat()
            size_bytes = stat.st_size
            mtime_utc = _iso_from_epoch(stat.st_mtime)
        except Exception:
            size_bytes = 0
            mtime_utc = ""
        workers.append({
            "schema": "agent_trace_child_execution_row_v1",
            "kind": "workflow_worker_trace",
            "provider": "claude_code",
            "workflow_row_id": row.get("row_id") or "",
            "workflow_run_id": row.get("run_id") or "",
            "task_id": row.get("task_id") or "",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "session_file": str(path),
            "prompt_sha16": _sha16(prompt_text) if prompt_text else "",
            "prompt_title": _prompt_title_from_text(prompt_text, limit=90),
            "started_at": started_at,
            "completed_at": completed_at or mtime_utc,
            "mtime_utc": mtime_utc,
            "size_bytes": size_bytes,
            "worker_index": idx,
        })
    return workers, {
        "status": "available",
        "reason": "",
        "path": str(transcript_dir),
        "path_source": dir_source,
        "expected_worker_count": expected,
        "actual_worker_count": len(workers),
    }


def _workflow_worker_turn(worker: dict) -> tuple[Turn | None, str]:
    session_file = str(worker.get("session_file") or "")
    if not session_file:
        return None, "missing_worker_session_file"
    path = Path(session_file)
    if not path.is_file():
        return None, "worker_session_file_not_found"
    try:
        turns = parse_claude_session(path)
    except Exception as exc:
        return None, f"worker_parse_failed:{type(exc).__name__}"
    if not turns:
        return None, "worker_session_has_no_turns"
    selected = next((turn for turn in reversed(turns) if turn.is_complete), turns[-1])
    try:
        return merge_full_thread(full_thread_turns(turns, selected)), ""
    except Exception as exc:
        return None, f"worker_full_thread_merge_failed:{type(exc).__name__}"


def _workflow_aggregate_output_lines(row: dict) -> tuple[list[str], dict]:
    output_path = _expand_trace_path(str(row.get("output_file") or ""))
    if output_path is None:
        return [], {"status": "not_declared", "path": "", "bytes": 0, "redactions": []}
    if not output_path.is_file():
        return [], {"status": "missing", "path": str(output_path), "bytes": 0, "redactions": []}
    try:
        raw = output_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return [], {"status": f"read_failed:{type(exc).__name__}", "path": str(output_path), "bytes": 0, "redactions": []}
    redacted, hits = _redact_secrets(raw)
    aggregate_worker_records = _workflow_aggregate_worker_records(redacted)
    lines = [
        f"BEGIN_WORKFLOW_AGGREGATE_OUTPUT {row.get('row_id')} path={output_path} bytes={len(redacted.encode('utf-8'))}",
        redacted.rstrip(),
        f"END_WORKFLOW_AGGREGATE_OUTPUT {row.get('row_id')} path={output_path}",
    ]
    return lines, {
        "status": "embedded",
        "path": str(output_path),
        "bytes": len(redacted.encode("utf-8")),
        "redactions": hits,
        "aggregate_worker_record_count": len(aggregate_worker_records),
        "aggregate_worker_records": aggregate_worker_records,
    }


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _workflow_aggregate_json_docs(text: str) -> list[Any]:
    docs: list[Any] = []
    try:
        docs.append(json.loads(text))
        return docs
    except Exception:
        pass
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] not in "[{":
            continue
        try:
            docs.append(json.loads(stripped))
        except Exception:
            continue
    return docs


def _workflow_aggregate_pick(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if value not in (None, "", [], {}):
            return value
    return ""


def _workflow_aggregate_nested(row: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = row
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if current not in (None, "", [], {}):
            return current
    return ""


def _workflow_aggregate_looks_like_worker(row: dict[str, Any]) -> bool:
    keys = {str(key).lower() for key in row}
    worker_keys = {
        "agentid", "agent_id", "workerid", "worker_id", "taskid", "task_id",
        "phase", "status", "state", "model", "prompt", "result", "summary",
        "duration_ms", "tokens", "token_count", "tool_uses", "tool_use_count",
    }
    return bool(keys & worker_keys)


def _workflow_aggregate_normalize_worker(row: dict[str, Any], *, index: int, path_hint: str) -> dict[str, Any]:
    result_value = _workflow_aggregate_pick(row, "result", "summary", "output", "answer", "error", "message")
    if isinstance(result_value, dict):
        result_value = _workflow_aggregate_pick(result_value, "summary", "text", "message", "error")
    prompt_value = _workflow_aggregate_pick(row, "prompt", "title", "task", "instruction", "description")
    usage = row.get("usage") if isinstance(row.get("usage"), dict) else {}
    tool_uses = _workflow_aggregate_pick(row, "tool_uses", "toolUseCount", "tool_use_count", "tools")
    if isinstance(tool_uses, list):
        tool_uses = len(tool_uses)
    label = _workflow_aggregate_pick(
        row,
        "agent_id", "agentId", "worker_id", "workerId", "id", "name", "task_id", "taskId",
    )
    if not label:
        label = f"aggregate_worker_{index:03d}"
    state = _workflow_aggregate_pick(row, "state", "status", "result_status", "outcome")
    if not state and isinstance(row.get("ok"), bool):
        state = "completed" if row.get("ok") else "failed"
    token_count = _coerce_int(_workflow_aggregate_pick(
        row,
        "token_count", "tokenCount", "tokens", "total_tokens", "totalTokens",
    ) or _workflow_aggregate_nested(usage, ("total_tokens",), ("totalTokens",)))
    return {
        "schema": "workflow_aggregate_worker_record_v1",
        "index": index,
        "path_hint": path_hint,
        "worker_label": _compact_one_line(str(label), limit=80),
        "phase": _compact_one_line(str(_workflow_aggregate_pick(row, "phase", "stage", "step") or "aggregate_worker"), limit=80),
        "model": _compact_one_line(str(_workflow_aggregate_pick(row, "model", "agent_type", "agentType", "provider") or "unknown"), limit=80),
        "state": _compact_one_line(str(state or "unknown"), limit=80),
        "prompt_sha16": _sha16(str(prompt_value)) if prompt_value else "",
        "prompt_preview": _compact_one_line(str(prompt_value or ""), limit=160),
        "result_sha16": _sha16(str(result_value)) if result_value else "",
        "result_preview": _compact_one_line(str(result_value or ""), limit=160),
        "token_count": token_count,
        "tool_use_count": _coerce_int(tool_uses),
        "duration_ms": _coerce_int(_workflow_aggregate_pick(row, "duration_ms", "durationMs", "elapsed_ms", "elapsedMs")),
        "raw_sha16": _sha16(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)),
    }


def _workflow_aggregate_worker_records(text: str) -> list[dict[str, Any]]:
    docs = _workflow_aggregate_json_docs(text)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(value: Any, path: str) -> None:
        if len(records) >= 500:
            return
        if isinstance(value, dict):
            if _workflow_aggregate_looks_like_worker(value):
                record = _workflow_aggregate_normalize_worker(value, index=len(records) + 1, path_hint=path)
                key = record.get("raw_sha16") or f"{path}:{len(records)}"
                if key not in seen:
                    seen.add(key)
                    records.append(record)
            for key, child in value.items():
                if isinstance(child, (dict, list)):
                    visit(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value, start=1):
                if isinstance(child, (dict, list)):
                    visit(child, f"{path}[{index}]")

    for doc in docs:
        visit(doc, "")
    return records


def _workflow_outline_from_aggregate_record(
    row: dict,
    record: dict[str, Any],
    *,
    outline_role: str,
    aggregate_inclusion_proof: str,
    label_prefix: str = "",
) -> dict[str, Any]:
    worker_label = str(record.get("worker_label") or f"aggregate_worker_{record.get('index') or 0}")
    if label_prefix:
        worker_label = f"{label_prefix}:{worker_label}"
    return {
        "schema": "workflow_worker_outline_row_v1",
        "outline_role": outline_role,
        "workflow_row_id": row.get("row_id") or "",
        "workflow_run_id": row.get("run_id") or "",
        "worker_label": worker_label,
        "phase": str(record.get("phase") or "aggregate_worker"),
        "model": str(record.get("model") or "unknown"),
        "state": str(record.get("state") or "unknown"),
        "prompt_sha16": str(record.get("prompt_sha16") or ""),
        "prompt_preview": _compact_one_line(str(record.get("prompt_preview") or ""), limit=120),
        "result_sha16": str(record.get("result_sha16") or ""),
        "result_preview": _compact_one_line(str(record.get("result_preview") or ""), limit=120),
        "token_count": int(record.get("token_count") or 0),
        "tool_use_count": int(record.get("tool_use_count") or 0),
        "duration_ms": int(record.get("duration_ms") or row.get("duration_ms") or 0),
        "transcript_availability": "aggregate_only",
        "transcript_bytes": 0,
        "aggregate_record_count": 1,
        "aggregate_worker_record_sha16": str(record.get("raw_sha16") or ""),
        "aggregate_inclusion_proof": aggregate_inclusion_proof,
    }


def _workflow_stratified_aggregate_outline_rows(
    row: dict,
    *,
    aggregate_worker_records: list[dict[str, Any]],
    aggregate_inclusion_proof: str,
) -> list[dict[str, Any]]:
    if not aggregate_worker_records:
        return []
    rows: list[dict[str, Any]] = []
    selected_keys: set[str] = set()

    def record_key(record: dict[str, Any]) -> str:
        return str(record.get("raw_sha16") or record.get("worker_label") or record.get("index") or "")

    def add_record(record: dict[str, Any], role: str, prefix: str) -> None:
        key = f"{role}:{record_key(record)}"
        if key in selected_keys:
            return
        selected_keys.add(key)
        rows.append(_workflow_outline_from_aggregate_record(
            row,
            record,
            outline_role=role,
            label_prefix=prefix,
            aggregate_inclusion_proof=aggregate_inclusion_proof,
        ))

    phases: dict[str, dict[str, Any]] = {}
    for record in aggregate_worker_records:
        phase = _compact_one_line(str(record.get("phase") or "unknown"), limit=80)
        bucket = phases.setdefault(phase, {
            "count": 0,
            "states": {},
            "token_count": 0,
            "tool_use_count": 0,
            "duration_ms": 0,
            "sha_material": [],
        })
        bucket["count"] += 1
        state = _compact_one_line(str(record.get("state") or "unknown"), limit=60)
        bucket["states"][state] = bucket["states"].get(state, 0) + 1
        bucket["token_count"] += int(record.get("token_count") or 0)
        bucket["tool_use_count"] += int(record.get("tool_use_count") or 0)
        bucket["duration_ms"] += int(record.get("duration_ms") or 0)
        bucket["sha_material"].append(record.get("raw_sha16") or "")
    for phase, bucket in sorted(phases.items(), key=lambda item: (-int(item[1]["count"]), item[0]))[:6]:
        state_summary = ",".join(f"{state}:{count}" for state, count in sorted(bucket["states"].items())) or "none"
        rows.append({
            "schema": "workflow_worker_outline_row_v1",
            "outline_role": "aggregate_phase_summary",
            "workflow_row_id": row.get("row_id") or "",
            "workflow_run_id": row.get("run_id") or "",
            "worker_label": f"aggregate_phase:{phase}",
            "phase": phase,
            "model": str(row.get("worker_provider") or "aggregate"),
            "state": "aggregate_phase_summary",
            "prompt_sha16": "",
            "prompt_preview": "",
            "result_sha16": _sha16("|".join(str(item) for item in bucket["sha_material"])),
            "result_preview": f"workers={bucket['count']} states={state_summary}",
            "token_count": int(bucket["token_count"]),
            "tool_use_count": int(bucket["tool_use_count"]),
            "duration_ms": int(bucket["duration_ms"]),
            "transcript_availability": "aggregate_only",
            "transcript_bytes": 0,
            "aggregate_record_count": int(bucket["count"]),
            "aggregate_worker_record_sha16": _sha16("|".join(str(item) for item in bucket["sha_material"])),
            "aggregate_inclusion_proof": aggregate_inclusion_proof,
        })

    for record in aggregate_worker_records[:2]:
        add_record(record, "aggregate_first_worker", "aggregate_first")
    last_records = aggregate_worker_records[-2:] if len(aggregate_worker_records) > 2 else []
    for record in last_records:
        add_record(record, "aggregate_last_worker", "aggregate_last")
    outlier_specs = (
        ("aggregate_token_outlier", "aggregate_outlier_tokens", "token_count"),
        ("aggregate_tool_outlier", "aggregate_outlier_tools", "tool_use_count"),
        ("aggregate_duration_outlier", "aggregate_outlier_duration", "duration_ms"),
    )
    for role, prefix, key in outlier_specs:
        candidate = max(aggregate_worker_records, key=lambda record: int(record.get(key) or 0))
        if int(candidate.get(key) or 0) > 0:
            add_record(candidate, role, prefix)
    done_states = {"done", "complete", "completed", "success", "succeeded", "ok"}
    failed_records = [
        record
        for record in aggregate_worker_records
        if str(record.get("state") or "").strip().lower() not in done_states
    ]
    for record in failed_records[:8]:
        add_record(record, "aggregate_failed_or_non_done_worker", "aggregate_non_done")

    selected_record_hashes = {
        str(outline.get("aggregate_worker_record_sha16") or "")
        for outline in rows
        if outline.get("aggregate_worker_record_sha16")
        and int(outline.get("aggregate_record_count") or 1) == 1
    }
    omitted_records = [
        record for record in aggregate_worker_records if str(record.get("raw_sha16") or "") not in selected_record_hashes
    ]
    if omitted_records:
        rows.append({
            "schema": "workflow_worker_outline_row_v1",
            "outline_role": "aggregate_omitted_middle_hash",
            "workflow_row_id": row.get("row_id") or "",
            "workflow_run_id": row.get("run_id") or "",
            "worker_label": f"aggregate_omitted_middle:{len(omitted_records)}",
            "phase": "aggregate_worker",
            "model": str(row.get("worker_provider") or "aggregate"),
            "state": "omitted_middle_hash",
            "prompt_sha16": "",
            "prompt_preview": "",
            "result_sha16": _sha16(json.dumps(omitted_records, sort_keys=True, ensure_ascii=False)),
            "result_preview": f"omitted_middle_workers={len(omitted_records)}",
            "token_count": sum(int(record.get("token_count") or 0) for record in omitted_records),
            "tool_use_count": sum(int(record.get("tool_use_count") or 0) for record in omitted_records),
            "duration_ms": sum(int(record.get("duration_ms") or 0) for record in omitted_records),
            "transcript_availability": "aggregate_only",
            "transcript_bytes": 0,
            "aggregate_record_count": len(omitted_records),
            "aggregate_worker_record_sha16": _sha16(json.dumps(omitted_records, sort_keys=True, ensure_ascii=False)),
            "aggregate_inclusion_proof": aggregate_inclusion_proof,
        })
    return rows


def _workflow_worker_outline_index(
    row: dict,
    *,
    workers: list[dict],
    expected_workers: int,
    transcript_receipt: dict,
    output_receipt: dict,
) -> dict[str, Any]:
    actual_workers = len(workers)
    if expected_workers and actual_workers >= expected_workers:
        transcript_availability = "complete"
    elif actual_workers:
        transcript_availability = "partial"
    elif transcript_receipt.get("status") == "missing":
        transcript_availability = "missing"
    else:
        transcript_availability = str(transcript_receipt.get("status") or "unknown")

    aggregate_status = str(output_receipt.get("status") or "not_declared")
    aggregate_inclusion_proof = (
        f"aggregate_output_embedded:{_sha16(str(output_receipt.get('path') or ''))}"
        if aggregate_status == "embedded"
        else f"aggregate_output_{aggregate_status}"
    )
    rows: list[dict[str, Any]] = []
    for worker in workers:
        prompt_preview = str(worker.get("prompt_title") or "")
        rows.append({
            "schema": "workflow_worker_outline_row_v1",
            "outline_role": "transcript_trace",
            "workflow_row_id": row.get("row_id") or "",
            "workflow_run_id": row.get("run_id") or "",
            "worker_label": str(worker.get("agent_id") or f"worker_{worker.get('worker_index') or len(rows) + 1}"),
            "phase": "workflow_worker",
            "model": str(worker.get("agent_type") or row.get("worker_provider") or "unknown"),
            "state": "transcript_file_seen",
            "prompt_sha16": str(worker.get("prompt_sha16") or ""),
            "prompt_preview": _compact_one_line(prompt_preview, limit=120),
            "result_sha16": "",
            "result_preview": "",
            "token_count": 0,
            "tool_use_count": 0,
            "duration_ms": row.get("duration_ms") or 0,
            "transcript_availability": "available",
            "transcript_bytes": int(worker.get("size_bytes") or 0),
            "aggregate_record_count": 0,
            "aggregate_worker_record_sha16": "",
            "aggregate_inclusion_proof": aggregate_inclusion_proof,
        })
    aggregate_worker_records = [
        record for record in output_receipt.get("aggregate_worker_records") or [] if isinstance(record, dict)
    ]
    rows.extend(_workflow_stratified_aggregate_outline_rows(
        row,
        aggregate_worker_records=aggregate_worker_records,
        aggregate_inclusion_proof=aggregate_inclusion_proof,
    ))
    missing = max(0, int(expected_workers or 0) - actual_workers)
    if missing:
        rows.append({
            "schema": "workflow_worker_outline_row_v1",
            "outline_role": "missing_transcript_count",
            "workflow_row_id": row.get("row_id") or "",
            "workflow_run_id": row.get("run_id") or "",
            "worker_label": f"missing_workers:{missing}",
            "phase": "workflow_worker",
            "model": str(row.get("worker_provider") or "unknown"),
            "state": "transcript_missing",
            "prompt_sha16": "",
            "prompt_preview": "",
            "result_sha16": "",
            "result_preview": "",
            "token_count": int(row.get("subagent_tokens") or 0),
            "tool_use_count": int(row.get("tool_uses") or 0),
            "duration_ms": row.get("duration_ms") or 0,
            "transcript_availability": transcript_availability,
            "transcript_bytes": 0,
            "aggregate_record_count": len(aggregate_worker_records),
            "aggregate_worker_record_sha16": _sha16(json.dumps(aggregate_worker_records, sort_keys=True, ensure_ascii=False)) if aggregate_worker_records else "",
            "aggregate_inclusion_proof": aggregate_inclusion_proof,
        })
    return {
        "schema_version": "workflow_worker_outline_index_v1",
        "workflow_row_id": row.get("row_id") or "",
        "workflow_run_id": row.get("run_id") or "",
        "expected_worker_count": expected_workers,
        "actual_worker_trace_count": actual_workers,
        "aggregate_worker_record_count": len(aggregate_worker_records),
        "outline_row_count": len(rows),
        "stratified_outline_row_count": sum(1 for outline in rows if str(outline.get("outline_role") or "").startswith("aggregate_")),
        "transcript_availability": transcript_availability,
        "aggregate_inclusion_proof": aggregate_inclusion_proof,
        "aggregate_status": aggregate_status,
        "rows": rows,
    }


def _capsule_child_execution_bundle(
    turn: Turn,
    *,
    subagent_packet: dict,
    subagent_trace_bundle: dict,
    include_prompt_body: bool,
    intern_repeated_prompts: bool,
    depth: int,
    visited: set[str],
) -> tuple[list[str], dict]:
    workflow_rows = _workflow_execution_rows_for_turn(turn)
    native_subagent_count = int(subagent_packet.get("count") or 0)
    subagent_embedded_count = int(subagent_trace_bundle.get("rendered_count") or 0)
    if not workflow_rows and native_subagent_count == 0:
        return [], {
            "schema_version": "agent_trace_child_execution_bundle_v1",
            "mode": "none",
            "native_subagent_count": 0,
            "workflow_count": 0,
            "workflow_worker_count": 0,
            "workflow_worker_outline_count": 0,
            "embedded_trace_count": 0,
            "embedded_workflow_trace_count": 0,
            "aggregate_output_count": 0,
            "aggregate_only_count": 0,
            "omitted_count": 0,
            "bytes": 0,
            "depth": depth,
            "rows": [],
        }

    bundle_rows: list[dict[str, Any]] = []
    lines: list[str] = [
        "",
        "CHILD_EXECUTION_BUNDLE",
        (
            "child_executions: schema=agent_trace_child_execution_bundle_v1 "
            f"native_subagents={native_subagent_count} "
            f"subagent_embedded={subagent_embedded_count} "
            f"workflows={len(workflow_rows)} "
            "mode=inline_recursive "
            f"depth={depth} size_policy=no_limit_operator_requested"
        ),
    ]
    embedded_count = subagent_embedded_count
    omitted_count = int(subagent_trace_bundle.get("omitted_count") or 0)
    workflow_worker_count = 0
    aggregate_output_count = 0
    aggregate_only_count = 0
    total_bytes = int(subagent_trace_bundle.get("bytes") or 0)
    embedded_workflow_trace_count = 0
    workflow_worker_outline_count = 0

    for row in workflow_rows:
        workers, transcript_receipt = _workflow_worker_rows(row, turn)
        expected_workers = int(row.get("agent_count") or 0)
        actual_workers = len(workers)
        workflow_worker_count += max(expected_workers, actual_workers)
        output_lines, output_receipt = _workflow_aggregate_output_lines(row)
        worker_outline_index = _workflow_worker_outline_index(
            row,
            workers=workers,
            expected_workers=expected_workers,
            transcript_receipt=transcript_receipt,
            output_receipt=output_receipt,
        )
        workflow_worker_outline_count += int(worker_outline_index.get("outline_row_count") or 0)
        if output_lines:
            aggregate_output_count += 1
            total_bytes += int(output_receipt.get("bytes") or 0)
        if not workers and output_receipt.get("status") == "embedded":
            aggregate_only_count += 1

        workflow_meta = {
            **row,
            "kind": "claude_workflow",
            "expected_worker_count": expected_workers,
            "actual_worker_trace_count": actual_workers,
            "worker_trace_coverage": f"{actual_workers}/{expected_workers or actual_workers}",
            "aggregate_derivation": (
                "structured_worker_outputs"
                if workers
                else (
                    "workflow_synthesis"
                    if output_receipt.get("status") == "embedded"
                    else "unknown"
                )
            ),
            "aggregate_schema_validated": False,
            "adversarial_recheck_coverage": "0",
            "transcript_dir_receipt": transcript_receipt,
            "aggregate_output": output_receipt,
            "workflow_worker_outline_index": worker_outline_index,
        }
        bundle_rows.append(workflow_meta)
        lines.append(
            f"WORKFLOW {row.get('row_id')} provider={row.get('provider')} task_id={row.get('task_id') or 'unknown'} "
            f"run_id={row.get('run_id') or 'unknown'} status={row.get('status') or 'unknown'} "
            f"origin_provider={row.get('origin_provider') or row.get('provider') or 'unknown'} "
            f"execution_engine={row.get('execution_engine') or 'workflow'} "
            f"worker_provider={row.get('worker_provider') or 'unknown'} "
            f"evidence_plane={row.get('evidence_plane') or 'unknown'} "
            f"worker_count={max(expected_workers, actual_workers)} worker_traces={actual_workers} "
            f"worker_trace_coverage={actual_workers}/{expected_workers or actual_workers} "
            f"aggregate_derivation={workflow_meta['aggregate_derivation']} "
            f"aggregate_schema_validated=false adversarial_recheck_coverage=0 "
            f"tokens={row.get('subagent_tokens') or 0} tool_uses={row.get('tool_uses') or 0} "
            f"duration_ms={row.get('duration_ms') or 0} transcript_dir={transcript_receipt.get('path') or row.get('transcript_dir') or 'missing'} "
            f"output_file={row.get('output_file') or 'none'} summary={_capsule_clean_text(str(row.get('summary') or ''))}"
        )
        if output_lines:
            lines.extend(output_lines)
        elif row.get("output_file"):
            lines.append(
                f"OMIT_WORKFLOW_AGGREGATE_OUTPUT {row.get('row_id')} path={row.get('output_file')} "
                f"reason={output_receipt.get('status')}"
            )

        lines.append(
            f"WORKFLOW_WORKER_OUTLINE_INDEX {row.get('row_id')} "
            f"schema={worker_outline_index.get('schema_version')} "
            f"expected={worker_outline_index.get('expected_worker_count') or 0} "
            f"actual={worker_outline_index.get('actual_worker_trace_count') or 0} "
            f"aggregate_records={worker_outline_index.get('aggregate_worker_record_count') or 0} "
            f"outline_rows={worker_outline_index.get('outline_row_count') or 0} "
            f"stratified_rows={worker_outline_index.get('stratified_outline_row_count') or 0} "
            f"transcript_availability={worker_outline_index.get('transcript_availability') or 'unknown'} "
            f"aggregate_inclusion_proof={worker_outline_index.get('aggregate_inclusion_proof') or 'none'}"
        )
        for outline in worker_outline_index.get("rows") or []:
            if not isinstance(outline, dict):
                continue
            lines.append(
                "workflow_worker_outline: "
                f"workflow={outline.get('workflow_row_id') or ''} "
                f"outline_role={outline.get('outline_role') or 'transcript_trace'} "
                f"worker_label={outline.get('worker_label') or ''} "
                f"phase={outline.get('phase') or ''} "
                f"model={outline.get('model') or ''} "
                f"state={outline.get('state') or ''} "
                f"prompt_sha16={outline.get('prompt_sha16') or 'none'} "
                f"prompt_preview=\"{_capsule_claim_value(outline.get('prompt_preview'))}\" "
                f"result_sha16={outline.get('result_sha16') or 'none'} "
                f"result_preview=\"{_capsule_claim_value(outline.get('result_preview'))}\" "
                f"token_count={outline.get('token_count') or 0} "
                f"tool_use_count={outline.get('tool_use_count') or 0} "
                f"duration_ms={outline.get('duration_ms') or 0} "
                f"transcript_availability={outline.get('transcript_availability') or 'unknown'} "
                f"transcript_bytes={outline.get('transcript_bytes') or 0} "
                f"aggregate_record_count={outline.get('aggregate_record_count') or 0} "
                f"aggregate_worker_record_sha16={outline.get('aggregate_worker_record_sha16') or 'none'} "
                f"aggregate_inclusion_proof={outline.get('aggregate_inclusion_proof') or 'none'}"
            )

        if expected_workers and actual_workers < expected_workers:
            missing = expected_workers - actual_workers
            omitted_count += missing
            lines.append(
                f"OMIT_CHILD_TRACE {row.get('row_id')}.missing kind=workflow_worker_trace "
                f"workflow_run={row.get('run_id') or 'unknown'} reason=workflow_worker_transcripts_missing "
                f"expected={expected_workers} found={actual_workers}"
            )
            bundle_rows.append({
                "kind": "missing_child_trace",
                "workflow_row_id": row.get("row_id"),
                "workflow_run_id": row.get("run_id") or "",
                "reason": "workflow_worker_transcripts_missing",
                "expected_worker_count": expected_workers,
                "actual_worker_trace_count": actual_workers,
                "missing_count": missing,
            })

        for worker in workers:
            child_row_id = f"{row.get('row_id')}.A{int(worker.get('worker_index') or 0):03d}"
            visit_key = f"claude_workflow:{row.get('run_id') or row.get('task_id') or 'unknown'}:{worker.get('agent_id')}"
            if visit_key in visited:
                omitted_count += 1
                bundle_rows.append({**worker, "row_id": child_row_id, "status": "omitted", "reason": "cycle_or_duplicate_child_session"})
                lines.append(
                    f"OMIT_CHILD_TRACE {child_row_id} kind=workflow_worker_trace "
                    f"workflow_run={row.get('run_id') or 'unknown'} agent_id={worker.get('agent_id')} "
                    "reason=cycle_or_duplicate_child_session"
                )
                continue
            child_turn, reason = _workflow_worker_turn(worker)
            if child_turn is None:
                omitted_count += 1
                bundle_rows.append({**worker, "row_id": child_row_id, "status": "omitted", "reason": reason})
                lines.append(
                    f"OMIT_CHILD_TRACE {child_row_id} kind=workflow_worker_trace "
                    f"workflow_run={row.get('run_id') or 'unknown'} agent_id={worker.get('agent_id')} reason={reason}"
                )
                continue
            next_visited = set(visited)
            next_visited.add(visit_key)
            child_title = (
                str(worker.get("prompt_title") or "").strip()
                or _prompt_title_from_text(child_turn.prompt_text)
                or f"Workflow worker {worker.get('agent_id')}"
            )
            child_text, child_meta = render_trace_capsule_text(
                child_turn,
                title=f"{row.get('run_id') or row.get('task_id') or 'workflow'} / {worker.get('agent_id')}: {child_title}",
                source_window="full_thread",
                intern_repeated_prompts=intern_repeated_prompts,
                include_raw_sidecar=True,
                include_prompt_body=include_prompt_body,
                embed_subagent_traces=True,
                embed_child_executions=True,
                _subagent_depth=0,
                _subagent_visited=set(),
                _child_execution_depth=depth + 1,
                _child_execution_visited=next_visited,
            )
            child_bytes = len(child_text.encode("utf-8"))
            total_bytes += child_bytes
            embedded_count += 1
            embedded_workflow_trace_count += 1
            bundle_rows.append({
                **worker,
                "row_id": child_row_id,
                "status": "embedded",
                "bytes": child_bytes,
                "child_provider_session_id": child_turn.session_id,
                "child_turn_index": child_turn.turn_index,
                "embedded_subagent_trace_count": child_meta.get("embedded_subagent_trace_count", 0),
                "embedded_child_trace_count": child_meta.get("embedded_child_trace_count", 0),
            })
            lines.append(
                f"BEGIN_CHILD_TRACE {child_row_id} kind=workflow_worker_trace provider=claude_code "
                f"workflow_run={row.get('run_id') or 'unknown'} task_id={row.get('task_id') or 'unknown'} "
                f"agent_id={worker.get('agent_id')} child_session={child_turn.session_id} "
                f"turn={child_turn.turn_index} bytes={child_bytes} title={_capsule_clean_text(child_title)}"
            )
            lines.append(child_text.rstrip())
            lines.append(
                f"END_CHILD_TRACE {child_row_id} kind=workflow_worker_trace provider=claude_code "
                f"workflow_run={row.get('run_id') or 'unknown'} agent_id={worker.get('agent_id')}"
            )

    lines.append(
        f"child_execution_result: workflows={len(workflow_rows)} workers={workflow_worker_count} "
        f"embedded={embedded_count} aggregate_outputs={aggregate_output_count} "
        f"aggregate_only={aggregate_only_count} omitted={omitted_count} "
        f"bytes={total_bytes} size_policy=no_limit_operator_requested"
    )
    return lines, {
        "schema_version": "agent_trace_child_execution_bundle_v1",
        "mode": "inline_recursive",
        "native_subagent_count": native_subagent_count,
        "subagent_embedded_count": subagent_embedded_count,
        "workflow_count": len(workflow_rows),
        "workflow_worker_count": workflow_worker_count,
        "embedded_trace_count": embedded_count,
        "embedded_workflow_trace_count": embedded_workflow_trace_count,
        "aggregate_output_count": aggregate_output_count,
        "aggregate_only_count": aggregate_only_count,
        "workflow_worker_outline_count": workflow_worker_outline_count,
        "omitted_count": omitted_count,
        "bytes": total_bytes,
        "depth": depth,
        "size_policy": "no_limit_operator_requested",
        "rows": bundle_rows,
    }


def _prompt_cycle_word_count(text: str) -> int:
    """Word count used to decide prompt-cycle boundaries.

    Claude hook feedback is often a verbose synthetic prompt. It should stay in
    the copied window as evidence, but it must not terminate a short-prompt
    chain that was really started by the previous operator instruction.
    """
    stripped = (text or "").lstrip()
    synthetic_prefixes = (
        "Stop hook feedback:",
        "PreToolUse hook feedback:",
        "PostToolUse hook feedback:",
        "[Request interrupted by user]",
    )
    if stripped.startswith(synthetic_prefixes):
        first_line = stripped.splitlines()[0] if stripped.splitlines() else stripped
        return _prompt_word_count(first_line)
    return _prompt_word_count(text)


def prompt_cycle_turns(turns: list[Turn], selected: Turn, *, threshold_words: int) -> list[Turn]:
    """Return the prompt-cycle window ending at selected.

    A short operator prompt such as "reinstall app for me please" is normally a
    continuation command, not a new mission. When the selected turn's prompt is
    below the threshold, include prior turns back through the nearest prompt
    that reaches the threshold. If the selected prompt itself is long enough,
    the window is just that selected turn.
    """
    try:
        selected_pos = next(i for i, turn in enumerate(turns) if turn.turn_index == selected.turn_index)
    except StopIteration:
        return [selected]

    threshold = max(1, threshold_words)
    if _prompt_cycle_word_count(selected.prompt_text) >= threshold:
        return [selected]

    start_pos = 0
    for i in range(selected_pos - 1, -1, -1):
        if _prompt_cycle_word_count(turns[i].prompt_text) >= threshold:
            start_pos = i
            break
    return turns[start_pos:selected_pos + 1]


def full_thread_turns(turns: list[Turn], selected: Turn) -> list[Turn]:
    """Return every parsed turn through selected.

    This is an explicit operator-selected window. It can be large, so it is not
    the default copy path.
    """
    try:
        selected_pos = next(i for i, turn in enumerate(turns) if turn.turn_index == selected.turn_index)
    except StopIteration:
        return [selected]
    return turns[:selected_pos + 1]


def _trace_window_prompt_counts(window: list[Turn]) -> list[dict[str, int]]:
    return [
        {"turn_index": turn.turn_index, "words": _prompt_cycle_word_count(turn.prompt_text)}
        for turn in window
    ]


def _trace_window_turn_summaries(window: list[Turn]) -> list[dict[str, Any]]:
    return [
        {
            "turn_index": turn.turn_index,
            "started_at": turn.started_at,
            "completed_at": turn.completed_at,
            "prompt_sha16": turn.prompt_sha256_16,
            "prompt_chars": turn.prompt_char_count,
            "prompt_words": _prompt_cycle_word_count(turn.prompt_text),
            "assistant_sha16": _sha16(turn.assistant_text) if turn.assistant_text else "",
            "assistant_chars": len(turn.assistant_text or ""),
            "tool_count": len(turn.tool_events),
            "is_complete": turn.is_complete,
            "partial_reason": turn.partial_reason,
        }
        for turn in window
    ]


def _split_prompt_turn_blocks(prompt_text: str) -> list[dict[str, Any]]:
    """Recover merged ``[turn N]`` prompt blocks from full-thread windows."""
    lines = (prompt_text or "").splitlines()
    blocks: list[dict[str, Any]] = []
    current_turn: int | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_turn, current_lines
        if current_turn is None:
            return
        while current_lines and current_lines[-1] == "":
            current_lines.pop()
        text = "\n".join(current_lines).strip()
        blocks.append({"turn_index": current_turn, "text": text})
        current_turn = None
        current_lines = []

    for line in lines:
        match = re.match(r"^\[turn\s+(\d+)\]\s*$", line.strip())
        if match:
            flush()
            current_turn = int(match.group(1))
            current_lines = []
        elif current_turn is not None:
            current_lines.append(line)
    flush()

    if blocks:
        return blocks
    value = (prompt_text or "").strip()
    return [{"turn_index": None, "text": value}] if value else []


PROMPT_SHARED_CHUNK_MIN_CHARS = 500
PROMPT_SHARED_CHUNK_MIN_LINES = 5


def _shared_line_prefix(texts: list[str]) -> str:
    if len(texts) < 2 or not all(texts):
        return ""
    line_sets = [text.splitlines(keepends=True) for text in texts]
    prefix: list[str] = []
    for index in range(min(len(lines) for lines in line_sets)):
        candidate = line_sets[0][index]
        if all(lines[index] == candidate for lines in line_sets[1:]):
            prefix.append(candidate)
        else:
            break
    value = "".join(prefix)
    if len(value) < PROMPT_SHARED_CHUNK_MIN_CHARS or len(prefix) < PROMPT_SHARED_CHUNK_MIN_LINES:
        return ""
    return value


def _shared_line_suffix(texts: list[str]) -> str:
    if len(texts) < 2 or not all(texts):
        return ""
    line_sets = [text.splitlines(keepends=True) for text in texts]
    suffix: list[str] = []
    for offset in range(1, min(len(lines) for lines in line_sets) + 1):
        candidate = line_sets[0][-offset]
        if all(lines[-offset] == candidate for lines in line_sets[1:]):
            suffix.append(candidate)
        else:
            break
    suffix.reverse()
    value = "".join(suffix)
    if len(value) < PROMPT_SHARED_CHUNK_MIN_CHARS or len(suffix) < PROMPT_SHARED_CHUNK_MIN_LINES:
        return ""
    return value


def _prompt_intern_manifest(prompt_text: str) -> dict[str, Any]:
    blocks = _split_prompt_turn_blocks(prompt_text)
    by_text: dict[str, list[int | None]] = {}
    for block in blocks:
        text = str(block.get("text") or "")
        if not text:
            continue
        by_text.setdefault(text, []).append(block.get("turn_index"))

    repeated = [
        (text, turns)
        for text, turns in by_text.items()
        if len(turns) > 1
    ]
    pool: list[dict[str, Any]] = []
    ref_by_text: dict[str, str] = {}
    for index, (text, turns) in enumerate(repeated, start=1):
        ref = f"prompt_{index:03d}"
        ref_by_text[text] = ref
        pool.append({
            "id": ref,
            "sha16": _sha16(text),
            "chars": len(text),
            "turn_indices": [turn for turn in turns if turn is not None],
            "text": text,
        })

    partial_blocks = [
        block for block in blocks
        if str(block.get("text") or "") and str(block.get("text") or "") not in ref_by_text
    ]
    partial_texts = [str(block.get("text") or "") for block in partial_blocks]
    shared_prefix = _shared_line_prefix(partial_texts)
    prefix_texts = [
        text[len(shared_prefix):] if shared_prefix and text.startswith(shared_prefix) else text
        for text in partial_texts
    ]
    shared_suffix = _shared_line_suffix(prefix_texts)
    if shared_prefix and shared_suffix:
        # Avoid aliasing the same lines twice if the common suffix overlaps the
        # already-aliased prefix in short prompts.
        min_remaining = min(len(text) for text in prefix_texts) if prefix_texts else 0
        if len(shared_suffix) >= min_remaining:
            shared_suffix = ""
    chunks: list[dict[str, Any]] = []
    if shared_prefix:
        chunks.append({
            "id": "prompt_chunk_001",
            "role": "common_prefix",
            "sha16": _sha16(shared_prefix),
            "chars": len(shared_prefix),
            "turn_indices": [block.get("turn_index") for block in partial_blocks if block.get("turn_index") is not None],
            "text": shared_prefix,
        })
    if shared_suffix:
        chunks.append({
            "id": f"prompt_chunk_{len(chunks) + 1:03d}",
            "role": "common_suffix",
            "sha16": _sha16(shared_suffix),
            "chars": len(shared_suffix),
            "turn_indices": [block.get("turn_index") for block in partial_blocks if block.get("turn_index") is not None],
            "text": shared_suffix,
        })
    chunk_by_role = {row["role"]: row for row in chunks}

    turn_refs = []
    for block in blocks:
        text = str(block.get("text") or "")
        ref = ref_by_text.get(text)
        segments: list[dict[str, Any]] = []
        inline_chars = 0
        if ref:
            segments.append({"type": "prompt_ref", "id": ref})
        else:
            remaining = text
            prefix = chunk_by_role.get("common_prefix")
            suffix = chunk_by_role.get("common_suffix")
            if prefix and remaining.startswith(str(prefix["text"])):
                segments.append({"type": "chunk_ref", "id": prefix["id"], "role": prefix["role"]})
                remaining = remaining[len(str(prefix["text"])):]
            suffix_text = str(suffix["text"]) if suffix else ""
            has_suffix = bool(suffix_text and remaining.endswith(suffix_text))
            middle = remaining[: len(remaining) - len(suffix_text)] if has_suffix else remaining
            if middle:
                inline_chars += len(middle)
                segments.append({
                    "type": "inline",
                    "chars": len(middle),
                    "sha16": _sha16(middle),
                    "text": middle,
                })
            if suffix and has_suffix:
                segments.append({"type": "chunk_ref", "id": suffix["id"], "role": suffix["role"]})
        turn_refs.append({
            "turn_index": block.get("turn_index"),
            "prompt_ref": ref,
            "sha16": _sha16(text) if text else "",
            "chars": len(text),
            "inline_chars": inline_chars if segments else len(text),
            "chunk_refs": [segment["id"] for segment in segments if segment.get("type") == "chunk_ref"],
            "segments": segments,
        })

    return {
        "schema": "agent_trace_prompt_intern_pool_v2",
        "status": "available" if (pool or chunks) else "not_needed",
        "pool": pool,
        "chunks": chunks,
        "turn_refs": turn_refs,
        "repeated_prompt_count": len(pool),
        "interned_turn_count": sum(len(row["turn_indices"]) for row in pool),
        "chunk_count": len(chunks),
        "chunk_ref_count": sum(len(row.get("chunk_refs") or []) for row in turn_refs),
        "policy": "Repeated identical prompt bodies appear once in pool[].text; later turns carry prompt_ref. Shared line-prefix/suffix chunks become prompt_chunk refs; unique deltas remain verbatim inline.",
    }


def _render_prompt_with_interns(prompt_text: str) -> list[str]:
    manifest = _prompt_intern_manifest(prompt_text)
    if manifest["status"] != "available":
        return [prompt_text]

    ref_by_text = {
        row["text"]: row["id"]
        for row in manifest["pool"]
    }
    lines = [
        (
            "# prompt_intern_pool "
            f"schema={manifest['schema']} "
            f"repeated_prompt_count={manifest['repeated_prompt_count']} "
            f"interned_turn_count={manifest['interned_turn_count']} "
            f"chunk_count={manifest.get('chunk_count', 0)}"
        )
    ]
    for row in manifest["pool"]:
        turns = ",".join(str(turn) for turn in row["turn_indices"])
        lines.append(
            f"# prompt_alias {row['id']} chars={row['chars']} "
            f"sha16={row['sha16']} turns={turns}"
        )
        lines.append(f"[{row['id']}]")
        lines.append(row["text"])
        lines.append(f"[/{row['id']}]")
        lines.append("")

    for row in manifest.get("chunks", []):
        turns = ",".join(str(turn) for turn in row["turn_indices"])
        lines.append(
            f"# prompt_chunk {row['id']} role={row['role']} chars={row['chars']} "
            f"sha16={row['sha16']} turns={turns}"
        )
        lines.append(f"[{row['id']}]")
        lines.append(row["text"])
        lines.append(f"[/{row['id']}]")
        lines.append("")

    lines.append("# prompt_turn_sequence")
    refs_by_turn = {
        row.get("turn_index"): row
        for row in manifest.get("turn_refs", [])
    }
    for block in _split_prompt_turn_blocks(prompt_text):
        text = str(block.get("text") or "")
        turn = block.get("turn_index")
        sha16 = _sha16(text) if text else ""
        turn_ref = refs_by_turn.get(turn) or {}
        ref = ref_by_text.get(text)
        turn_label = f"[turn {turn}]" if turn is not None else "[turn unknown]"
        if ref:
            lines.append(f"{turn_label} prompt_ref={ref}")
        else:
            segments = turn_ref.get("segments") if isinstance(turn_ref, dict) else None
            if segments:
                lines.append(f"{turn_label} prompt_segmented chars={len(text)} sha16={sha16}")
                for segment in segments:
                    if segment.get("type") == "chunk_ref":
                        lines.append(f"{turn_label} prompt_chunk_ref={segment.get('id')} role={segment.get('role')}")
                    elif segment.get("type") == "inline":
                        lines.append(
                            f"{turn_label} prompt_inline_delta chars={segment.get('chars')} "
                            f"sha16={segment.get('sha16')}"
                        )
                        if segment.get("text"):
                            lines.append(str(segment["text"]))
            elif text:
                lines.append(f"{turn_label} prompt_inline chars={len(text)} sha16={sha16}")
                lines.append(text)
        lines.append("")
    return lines


def _prompt_intern_summary_line(prompt_text: str) -> str | None:
    manifest = _prompt_intern_manifest(prompt_text)
    if manifest["status"] != "available":
        return None
    refs = ",".join(row["id"] for row in manifest["pool"])
    return (
        f"# prompt_interning repeated_prompt_count={manifest['repeated_prompt_count']} "
        f"interned_turn_count={manifest['interned_turn_count']} pool={refs}"
    )


def _merged_trace_window(
    window: list[Turn],
    *,
    mode: str,
    threshold_words: int | None = None,
) -> Turn:
    if not window:
        raise SystemExit("empty trace window")
    if len(window) == 1:
        turn = window[0]
        trace_window = {
            "mode": mode if mode == "full_thread" else "single_turn",
            "start_turn_index": turn.turn_index,
            "end_turn_index": turn.turn_index,
            "turn_count": 1,
            "tool_count": len(turn.tool_events),
            "prompt_word_counts": _trace_window_prompt_counts(window),
            "turn_summaries": _trace_window_turn_summaries(window),
            "prompt_sha16": turn.prompt_sha256_16,
            "terminal_prompt_sha16": turn.prompt_sha256_16,
        }
        if threshold_words is not None:
            trace_window["short_prompt_threshold_words"] = max(1, threshold_words)
        source_ref = dict(turn.source_ref or {})
        source_ref["trace_window"] = trace_window
        if mode in {"prompt_cycle", "short_prompt_chain", "single_turn"}:
            source_ref["prompt_cycle"] = trace_window
        elif mode == "full_thread":
            source_ref["full_thread"] = trace_window
        return replace(turn, source_ref=source_ref)

    merged_events: list[ToolEvent] = []
    merged_assistant_events: list[AssistantEvent] = []
    for turn in window:
        for ev in turn.tool_events:
            merged_events.append(replace(ev, index=len(merged_events) + 1))
        for ev in turn.assistant_events:
            merged_assistant_events.append(ev)

    prompt_blocks = [
        f"[turn {turn.turn_index}]\n{turn.prompt_text or ''}".rstrip()
        for turn in window
        if (turn.prompt_text or "").strip()
    ]
    assistant_blocks = [
        f"[turn {turn.turn_index}]\n{turn.assistant_text}".rstrip()
        for turn in window
        if (turn.assistant_text or "").strip()
    ]
    prompt_text = "\n\n".join(prompt_blocks)
    start = window[0]
    end = window[-1]
    prompt_sha16 = _sha16(prompt_text) if prompt_text else ""
    trace_window = {
        "mode": mode,
        "start_turn_index": start.turn_index,
        "end_turn_index": end.turn_index,
        "turn_count": len(window),
        "tool_count": len(merged_events),
        "prompt_word_counts": _trace_window_prompt_counts(window),
        "turn_summaries": _trace_window_turn_summaries(window),
        "prompt_sha16": prompt_sha16,
        "terminal_prompt_sha16": end.prompt_sha256_16,
    }
    if threshold_words is not None:
        trace_window["short_prompt_threshold_words"] = max(1, threshold_words)
    source_ref = dict(end.source_ref or {})
    source_ref["trace_window"] = trace_window
    if mode in {"prompt_cycle", "short_prompt_chain", "single_turn"}:
        source_ref["prompt_cycle"] = trace_window
    elif mode == "full_thread":
        source_ref["full_thread"] = trace_window
    merged_indices: list[int] = []
    for turn in window:
        merged_indices.extend(turn.source_record_indices)
    return Turn(
        provider=end.provider,
        session_id=end.session_id,
        session_file=end.session_file,
        turn_id=f"{start.turn_id}..{end.turn_id}",
        turn_index=end.turn_index,
        cwd=end.cwd or start.cwd,
        started_at=start.started_at,
        completed_at=end.completed_at,
        prompt_text=prompt_text,
        prompt_char_count=len(prompt_text),
        prompt_sha256_16=prompt_sha16,
        tool_events=merged_events,
        assistant_text="\n\n".join(assistant_blocks),
        assistant_events=merged_assistant_events,
        is_complete=all(turn.is_complete for turn in window),
        partial_reason=end.partial_reason if not end.is_complete else None,
        last_stop_reason=end.last_stop_reason,
        source_record_indices=merged_indices,
        source_ref=source_ref,
    )


def merge_prompt_cycle(window: list[Turn], *, threshold_words: int) -> Turn:
    mode = "single_turn" if len(window) == 1 else "short_prompt_chain"
    return _merged_trace_window(window, mode=mode, threshold_words=threshold_words)


def merge_full_thread(window: list[Turn]) -> Turn:
    return _merged_trace_window(window, mode="full_thread")


def _attach_full_thread_trace_window(turn: Turn, turns: list[Turn], selected: Turn) -> Turn:
    """Attach whole-thread coverage facts to selected/latest windows.

    The rendered capsule may still copy only the selected/latest response, but
    Type B consumers need to know whether a wider thread exists before making
    any "no edits" or "full thread" claim.
    """
    try:
        full_turn = merge_full_thread(full_thread_turns(turns, selected))
    except Exception:
        return turn
    full_window = (full_turn.source_ref or {}).get("trace_window") or (full_turn.source_ref or {}).get("full_thread")
    if not isinstance(full_window, dict):
        return turn
    source_ref = dict(turn.source_ref or {})
    source_ref["full_thread_trace_window"] = full_window
    source_ref.setdefault("full_thread", full_window)
    return replace(turn, source_ref=source_ref)


def select_trace_window(
    turns: list[Turn],
    *,
    turn_arg: int | None,
    active: bool,
    allow_partial: bool,
    prompt_cycle: bool,
    full_thread: bool,
    threshold_words: int,
) -> Turn:
    selected = select_turn(turns, turn_arg=turn_arg, active=active, allow_partial=allow_partial)
    if full_thread:
        return merge_full_thread(full_thread_turns(turns, selected))
    if not prompt_cycle:
        return _attach_full_thread_trace_window(selected, turns, selected)
    cycle = merge_prompt_cycle(
        prompt_cycle_turns(turns, selected, threshold_words=threshold_words),
        threshold_words=threshold_words,
    )
    return _attach_full_thread_trace_window(cycle, turns, selected)


# --- Rendering --- #

def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + f"\n... [truncated {len(s) - limit} chars; sha256_16={_sha16(s)}]"


def _tool_base_name(name: str) -> str:
    return str(name or "").rsplit(".", 1)[-1]


def _fmt_input(name: str, inp: dict) -> str:
    base_name = _tool_base_name(name)
    if base_name == "Bash":
        cmd = inp.get("command", "")
        return f"$ {cmd}"
    if base_name == "Read":
        loc = inp.get("file_path", "")
        extras = []
        if inp.get("offset"):
            extras.append(f"offset={inp.get('offset')}")
        if inp.get("limit"):
            extras.append(f"limit={inp.get('limit')}")
        return f"Read {loc}" + (f"  ({', '.join(extras)})" if extras else "")
    if base_name == "Edit":
        return (
            f"Edit {inp.get('file_path', '')}  "
            f"old_chars={len(inp.get('old_string') or '')}  "
            f"new_chars={len(inp.get('new_string') or '')}"
        )
    if base_name == "Write":
        return f"Write {inp.get('file_path', '')}  content_chars={len(inp.get('content') or '')}"
    if base_name == "Glob":
        return f"Glob pattern={inp.get('pattern')!r}"
    if base_name == "Grep":
        bits = [f"pattern={inp.get('pattern')!r}"]
        if inp.get("glob"):
            bits.append(f"glob={inp.get('glob')!r}")
        if inp.get("path"):
            bits.append(f"path={inp.get('path')!r}")
        return "Grep " + "  ".join(bits)
    if base_name in ("exec_command", "shell"):
        cmd = inp.get("cmd") or inp.get("command") or ""
        return f"$ {cmd}"
    if base_name == "apply_patch":
        raw_patch = inp.get("_raw_arguments") or inp.get("_raw_input") or ""
        return f"apply_patch  input_chars={len(raw_patch or json.dumps(inp))}"
    j = json.dumps(inp, ensure_ascii=False)
    if len(j) > COMPACT_INPUT_PREVIEW_CHARS:
        return j[:COMPACT_INPUT_PREVIEW_CHARS] + "..."
    return j


def _render(turn: Turn, *, full: bool, intern_repeated_prompts: bool = False) -> str:
    lines: list[str] = []
    head = f"=== TURN {turn.turn_index} — {turn.provider} session {turn.session_id[:16] if turn.session_id else '?'}"
    if turn.cwd:
        head += f"  cwd={turn.cwd}"
    lines.append(head)
    if turn.started_at:
        lines.append(f"=== started {turn.started_at}")
    if turn.completed_at:
        lines.append(f"=== completed {turn.completed_at}")
    if turn.is_complete:
        lines.append("=== status complete")
    else:
        lines.append(f"=== status partial — {turn.partial_reason}")
    lines.append(f"=== source {turn.session_file}")
    lines.append("")
    lines.append("--- PROMPT ---")
    if full:
        if intern_repeated_prompts:
            lines.extend(_render_prompt_with_interns(turn.prompt_text))
        else:
            lines.append(turn.prompt_text)
    else:
        lines.append(_truncate(turn.prompt_text, COMPACT_PROMPT_TRUNCATE_CHARS))
    lines.append("")

    total = len(turn.tool_events)
    for ev in turn.tool_events:
        header = f"--- TOOL {ev.index}/{total} [{ev.name}]"
        if ev.started_at:
            header += f"  {ev.started_at}"
        if ev.duration_ms is not None:
            header += f"  ({ev.duration_ms} ms)"
        if ev.exit_code is not None:
            header += f"  exit={ev.exit_code}"
        if ev.is_error:
            header += "  ERROR"
        header += " ---"
        lines.append(header)
        lines.append(_fmt_input(ev.name, ev.input))
        if ev.output_text:
            if full:
                lines.append(ev.output_text)
            else:
                lines.append(_truncate(ev.output_text, COMPACT_OUTPUT_TRUNCATE_CHARS))
        lines.append("")

    if turn.assistant_text:
        lines.append("--- ASSISTANT ---")
        lines.append(turn.assistant_text)

    return "\n".join(lines)


def render_compact(turn: Turn) -> str:
    return _render(turn, full=False)


def render_full(turn: Turn, *, intern_repeated_prompts: bool = False) -> str:
    return _render(turn, full=True, intern_repeated_prompts=intern_repeated_prompts)


def _closeout_duration_label(ms: int | None) -> str:
    if ms is None:
        return "unknown"
    if ms < 1000:
        return f"{ms} ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes = int(seconds // 60)
    remainder = int(seconds % 60)
    return f"{minutes}m {remainder}s"


def _md_table_code(value: Any) -> str:
    text = str(value if value is not None else "")
    text = text.replace("`", "'").replace("|", "\\|")
    return f"`{text}`"


def _closeout_command_display(ev: ToolEvent) -> str:
    command = _capsule_command(ev)
    if command:
        candidates = _capsule_command_surface_argvs(command)
        if candidates and candidates[0]:
            exe = Path(candidates[0][0]).name or "command"
        else:
            exe = _tool_base_name(ev.name) or "command"
        return f"{exe} command_sha16={_sha16(command)}"
    base = _tool_base_name(ev.name)
    if base:
        return base
    return "tool"


def _closeout_command_summary_rows(turn: Turn, *, limit: int = TRACE_CLOSEOUT_COMMAND_LIMIT) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for ev, output_text, exit_code, is_error in _renderable_trace_tool_events(turn.tool_events):
        display = _closeout_command_display(ev)
        row = buckets.setdefault(display, {
            "command": display,
            "count": 0,
            "known_duration_count": 0,
            "total_duration_ms": 0,
            "max_duration_ms": 0,
            "failures": 0,
            "output_chars": 0,
        })
        row["count"] += 1
        if ev.duration_ms is not None:
            row["known_duration_count"] += 1
            row["total_duration_ms"] += ev.duration_ms
            row["max_duration_ms"] = max(row["max_duration_ms"], ev.duration_ms)
        if is_error or (exit_code is not None and exit_code != 0):
            row["failures"] += 1
        row["output_chars"] += len(output_text or "")
    rows = list(buckets.values())
    rows.sort(key=lambda row: (-row["count"], -row["total_duration_ms"], row["command"]))
    return rows[:max(1, limit)]


def _closeout_changed_file_rows(turn: Turn, *, limit: int = 50) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for ev in turn.tool_events:
        for delta in _capsule_tool_edit_deltas(ev):
            path = str(delta.get("path") or "").strip()
            if not path:
                continue
            row = buckets.setdefault(path, {
                "path": path,
                "events": 0,
                "additions": 0,
                "deletions": 0,
            })
            row["events"] += 1
            row["additions"] += int(delta.get("additions") or 0)
            row["deletions"] += int(delta.get("deletions") or 0)
    rows = list(buckets.values())
    rows.sort(key=lambda row: (-row["events"], row["path"]))
    return rows[:max(1, limit)]


def _trace_source_fingerprint(turn: Turn) -> str:
    """Cheap stable fingerprint for estimate/report metadata.

    Raw sidecar SHA is still used when an artifact is materialized. This avoids
    constructing multi-megabyte raw paste text when the UI only needs report
    bytes or a compact source identity.
    """
    h = hashlib.sha256()
    for part in (
        turn.provider,
        turn.session_id,
        turn.turn_id,
        str(turn.turn_index),
        turn.prompt_sha256_16,
        str(len(turn.tool_events)),
        str(len(turn.assistant_events)),
    ):
        h.update(str(part or "").encode("utf-8"))
        h.update(b"\0")
    for ev in turn.tool_events:
        h.update(str(ev.output_sha256_16 or "").encode("utf-8"))
        h.update(str(ev.output_char_count or 0).encode("utf-8"))
        h.update(b"\0")
    for ev in turn.assistant_events:
        h.update(_sha16(ev.text or "").encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def _closeout_report_meta(
    turn: Turn,
    *,
    command_limit: int = TRACE_CLOSEOUT_COMMAND_LIMIT,
    source_sha16: str | None = None,
) -> dict[str, Any]:
    renderable = _renderable_trace_tool_events(turn.tool_events)
    durations = [ev.duration_ms for ev, *_ in renderable if ev.duration_ms is not None]
    failures = [
        ev for ev, _output, exit_code, is_error in renderable
        if is_error or (exit_code is not None and exit_code != 0)
    ]
    closeout_blocks = [
        row for row in _split_prompt_turn_blocks(turn.assistant_text)
        if str(row.get("text") or "").strip()
    ]
    if not closeout_blocks and turn.assistant_text.strip():
        closeout_blocks = [{"turn_index": turn.turn_index, "text": turn.assistant_text.strip()}]
    changed_files = _closeout_changed_file_rows(turn)
    command_rows = _closeout_command_summary_rows(turn, limit=command_limit)
    visible_progress_rows = _closeout_visible_progress_rows(turn)
    return {
        "schema_version": "agent_trace_closeout_report_meta_v1",
        "turn_count": int(((turn.source_ref or {}).get("trace_window") or {}).get("turn_count") or 1),
        "tool_event_count": len(renderable),
        "failed_tool_event_count": len(failures),
        "known_duration_count": len(durations),
        "total_duration_ms": sum(durations),
        "max_duration_ms": max(durations) if durations else None,
        "changed_file_count": len(changed_files),
        "changed_files": changed_files,
        "command_summary_limit": command_limit,
        "command_summary_rows": command_rows,
        "closeout_count": len(closeout_blocks),
        "closeout_char_count": sum(len(str(row.get("text") or "")) for row in closeout_blocks),
        "visible_progress_note_count": len(visible_progress_rows),
        "visible_progress_category_counts": _category_counts(row["category"] for row in visible_progress_rows),
        "visible_progress_rows": visible_progress_rows,
        "source_sha16": source_sha16 or _trace_source_fingerprint(turn),
    }


def _category_counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "other")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _closeout_visible_progress_rows(turn: Turn, *, limit: int = 24) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in sorted(turn.assistant_events, key=lambda row: row.source_record_index):
        text = _capsule_clean_text(" ".join((ev.text or "").strip().split()))
        if not text:
            continue
        category = _capsule_reasoning_category(text)
        if category == "closeout":
            continue
        rows.append({
            "note_id": f"N{len(rows) + 1:03d}",
            "category": category,
            "source_record_index": ev.source_record_index,
            "excerpt": _capsule_reasoning_excerpt(text, max_chars=170),
            "text": text,
            "sha16": _sha16(text),
        })
        if len(rows) >= limit:
            break
    return rows


def _visible_thinking_block(text: str, *, max_chars: int = 4000) -> str:
    clean = (text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return (
        clean[:max_chars].rstrip()
        + f"\n\n[app-visible thinking note truncated; omitted_chars={len(clean) - max_chars}; sha16={_sha16(clean)}]"
    )


def _prompt_ref_by_turn(prompt_text: str) -> dict[int | None, dict[str, Any]]:
    manifest = _prompt_intern_manifest(prompt_text)
    return {
        row.get("turn_index"): row
        for row in manifest.get("turn_refs", [])
    }


def _single_line(text: str, *, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + f"... [sha16={_sha16(clean)}]"


def render_thread_closeout_report(
    turn: Turn,
    *,
    title: str | None = None,
    intern_repeated_prompts: bool = False,
    command_limit: int = TRACE_CLOSEOUT_COMMAND_LIMIT,
    generated_at: str | None = None,
) -> str:
    """Render a compact full-session handoff: metadata + visible progress + final closeouts.

    This is the low-bulk companion to ``--format trace-paste --full-thread``.
    It deliberately omits raw tool bodies while preserving prompt bodies,
    app-visible thinking/progress notes, prompt-intern refs, and exact final
    closeout prose for a future Type A pass to choose the right raw JSONL
    drilldown when needed.
    """
    trace_window = (turn.source_ref or {}).get("trace_window") or {}
    turn_summaries = trace_window.get("turn_summaries") if isinstance(trace_window, dict) else None
    summary_by_turn = {
        row.get("turn_index"): row
        for row in turn_summaries or []
        if isinstance(row, dict)
    }
    prompt_by_turn = {
        row.get("turn_index"): str(row.get("text") or "")
        for row in _split_prompt_turn_blocks(turn.prompt_text)
    }
    ref_by_turn = _prompt_ref_by_turn(turn.prompt_text) if intern_repeated_prompts else {}
    closeout_blocks = [
        row for row in _split_prompt_turn_blocks(turn.assistant_text)
        if str(row.get("text") or "").strip()
    ]
    if not closeout_blocks and turn.assistant_text.strip():
        closeout_blocks = [{"turn_index": turn.turn_index, "text": turn.assistant_text.strip()}]

    title_text = title or f"{turn.provider} thread {turn.session_id[:8] if turn.session_id else 'unknown'}"
    mode = trace_window.get("mode") if isinstance(trace_window, dict) else None
    start = trace_window.get("start_turn_index") if isinstance(trace_window, dict) else None
    end = trace_window.get("end_turn_index") if isinstance(trace_window, dict) else None
    turn_count = trace_window.get("turn_count") if isinstance(trace_window, dict) else None
    mode = mode or "selected_turn"
    start = start if start is not None else turn.turn_index
    end = end if end is not None else turn.turn_index
    turn_count = turn_count if turn_count is not None else 1
    if mode == "single_turn":
        mode = "selected_turn"
    tool_count = trace_window.get("tool_count") if isinstance(trace_window, dict) else None
    tool_count = tool_count if tool_count is not None else len(turn.tool_events)
    generated = generated_at or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_meta = _closeout_report_meta(turn, command_limit=command_limit)

    lines = [
        f"# {title_text} — Closeout Report",
        "",
        "Thread-level projection generated by `cli_prompt_trace.py`; raw provider JSONL remains the source authority.",
        "",
        "## Metadata",
        "",
        f"- Generated: `{generated}`",
        f"- Provider: `{turn.provider}`",
        f"- Session: `{turn.session_id}`",
        f"- Source JSONL: `{turn.session_file}`",
        f"- Window: `{mode}` turns `{start}`-`{end}` (`{turn_count}` turns)",
        f"- Tool events omitted: `{tool_count}`",
        f"- Report schema: `{TRACE_CLOSEOUT_REPORT_SCHEMA_VERSION}`",
        f"- Prompt body policy: `included_with_prompt_interning_when_repeated`",
        f"- Closeout body policy: `exact_final_assistant_messages_included`",
        f"- Commands: `{report_meta['tool_event_count']}` events, `{report_meta['failed_tool_event_count']}` failed/error events",
        f"- Observed runtime: `{_closeout_duration_label(report_meta['total_duration_ms'])}` total across `{report_meta['known_duration_count']}` timed events; max `{_closeout_duration_label(report_meta['max_duration_ms'])}`",
        f"- Files changed: `{report_meta['changed_file_count']}`",
        f"- App-visible thinking/progress notes: `{report_meta['visible_progress_note_count']}` (`assistant_visible_only`; server-hidden reasoning is not available)",
    ]

    progress_rows = report_meta["visible_progress_rows"]
    category_counts = report_meta["visible_progress_category_counts"]
    lines.extend([
        "",
        "## App-Visible Thinking Trace",
        "",
        "Source: app-visible assistant thinking/progress/status messages already emitted in the transcript. Server-hidden reasoning is not accessible or included.",
    ])
    if category_counts:
        counts = ", ".join(f"`{key}` {value}" for key, value in sorted(category_counts.items()))
        lines.append(f"- Category counts: {counts}")
    else:
        lines.append("- Category counts: none")
    if progress_rows:
        lines.extend([
            "",
            "| Note | Category | Source | Excerpt |",
            "|---|---|---:|---|",
        ])
        for row in progress_rows:
            excerpt = html.escape(str(row["excerpt"]).replace("|", "\\|"))
            lines.append(
                f"| `{row['note_id']}` | `{row['category']}` | {row['source_record_index']} | {excerpt} |"
            )
    else:
        lines.append("- No app-visible thinking/progress notes outside closeout were detected.")

    if progress_rows:
        lines.extend(["", "### Visible Note Bodies", ""])
        for row in progress_rows:
            body = html.escape(_visible_thinking_block(str(row.get("text") or "")))
            lines.extend([
                f"#### {row['note_id']} `{row['category']}`",
                "",
                f"- Source record: `{row['source_record_index']}`",
                f"- sha16: `{row['sha16']}`",
                "",
                "<pre>",
                body,
                "</pre>",
                "",
            ])

    if intern_repeated_prompts:
        manifest = _prompt_intern_manifest(turn.prompt_text)
        lines.extend([
            "",
            "## Prompt Intern Pool",
            "",
            f"- Status: `{manifest['status']}`",
            f"- Repeated prompt count: `{manifest['repeated_prompt_count']}`",
            f"- Interned turn count: `{manifest['interned_turn_count']}`",
        ])
        for row in manifest.get("pool", []):
            turns = ", ".join(str(x) for x in row.get("turn_indices", []))
            lines.append(
                f"- `{row['id']}`: turns `{turns}`, chars `{row['chars']}`, sha16 `{row['sha16']}`"
            )
        for row in manifest.get("chunks", []):
            turns = ", ".join(str(x) for x in row.get("turn_indices", []))
            lines.append(
                f"- `{row['id']}`: `{row.get('role')}`, turns `{turns}`, chars `{row['chars']}`, sha16 `{row['sha16']}`"
            )

    if (turn.prompt_text or "").strip():
        prompt_lines = _render_prompt_with_interns(turn.prompt_text) if intern_repeated_prompts else [turn.prompt_text]
        prompt_body = "\n".join(prompt_lines).replace("```", "` ` `")
        lines.extend([
            "",
            "## Prompt Bodies",
            "",
            "```text",
            prompt_body,
            "```",
        ])

    lines.extend([
        "",
        "## Changed Files",
        "",
    ])
    changed_files = report_meta["changed_files"]
    if changed_files:
        lines.extend([
            "| Path | Events | +/- |",
            "|---|---:|---:|",
        ])
        for row in changed_files:
            lines.append(
                f"| {_md_table_code(row['path'])} | {row['events']} | +{row['additions']} / -{row['deletions']} |"
            )
    else:
        lines.append("_No edit/write file deltas detected in the selected window._")

    lines.extend([
        "",
        f"## Top Commands ({min(command_limit, len(report_meta['command_summary_rows']))})",
        "",
    ])
    command_rows = report_meta["command_summary_rows"]
    if command_rows:
        lines.extend([
            "| Count | Timed | Total | Max | Failures | Output chars | Command / tool |",
            "|---:|---:|---:|---:|---:|---:|---|",
        ])
        for row in command_rows:
            lines.append(
                f"| {row['count']} | {row['known_duration_count']} | `{_closeout_duration_label(row['total_duration_ms'])}` | "
                f"`{_closeout_duration_label(row['max_duration_ms'] if row['known_duration_count'] else None)}` | "
                f"{row['failures']} | {row['output_chars']} | {_md_table_code(row['command'])} |"
            )
    else:
        lines.append("_No command/tool events detected in the selected window._")

    lines.extend([
        "",
        "## Turn Index",
        "",
        "| Turn | Complete | Completed | Tools | Prompt | Closeout | Summary |",
        "|---:|---|---|---:|---|---|---|",
    ])
    for block in closeout_blocks:
        idx = block.get("turn_index")
        text = str(block.get("text") or "").strip()
        meta = summary_by_turn.get(idx, {})
        prompt_text = prompt_by_turn.get(idx, "")
        prompt_ref = ref_by_turn.get(idx, {})
        prompt_ref_text = prompt_ref.get("prompt_ref") or "inline"
        prompt_chars = meta.get("prompt_chars", len(prompt_text))
        prompt_sha = meta.get("prompt_sha16") or (_sha16(prompt_text) if prompt_text else "")
        close_sha = meta.get("assistant_sha16") or _sha16(text)
        completed = meta.get("completed_at") or ""
        complete = "yes" if meta.get("is_complete", True) else "no"
        tools = meta.get("tool_count", "")
        summary = _single_line(text)
        lines.append(
            f"| {idx if idx is not None else '?'} | `{complete}` | `{completed}` | {tools} | "
            f"`{prompt_ref_text}` `{prompt_chars}` chars `{prompt_sha}` | "
            f"`{len(text)}` chars `{close_sha}` | {summary} |"
        )

    lines.extend(["", "## Exact Closeouts", ""])
    for block in closeout_blocks:
        idx = block.get("turn_index")
        text = str(block.get("text") or "").strip()
        meta = summary_by_turn.get(idx, {})
        prompt_ref = ref_by_turn.get(idx, {})
        ref = prompt_ref.get("prompt_ref") or "inline"
        prompt_sha = meta.get("prompt_sha16") or ""
        lines.extend([
            f"### Turn {idx if idx is not None else '?'}",
            "",
            f"- Prompt: `{ref}`, sha16 `{prompt_sha}`",
            f"- Closeout chars: `{len(text)}`, sha16 `{_sha16(text)}`",
            "",
            "<details>",
            "<summary>Exact closeout message</summary>",
            "",
            "<pre>",
            html.escape(text),
            "</pre>",
            "",
            "</details>",
            "",
        ])

    return "\n".join(lines).rstrip() + "\n"


def _trace_paste_marker_for(name: str) -> str:
    """Map a tool name onto the bare marker line the Structurer parser recognises."""
    base_name = _tool_base_name(name)
    if base_name in ("Bash", "exec_command", "shell"):
        return "Bash"
    if base_name == "Read":
        return "Read"
    if base_name == "Edit":
        return "Edited"
    if base_name == "Write":
        return "Wrote"
    if base_name == "apply_patch":
        return "Bash"
    if base_name == "Glob":
        return "Bash"
    if base_name == "Grep":
        return "Bash"
    if base_name == "MultiEdit":
        return "Edited"
    if base_name == "NotebookEdit":
        return "Edited"
    return "Bash"


def _raw_apply_patch_input(inp: dict) -> str:
    raw = inp.get("_raw_arguments") or inp.get("_raw_input")
    return raw if isinstance(raw, str) else ""


def _apply_patch_file_deltas(patch: str) -> list[dict[str, Any]]:
    if not patch:
        return []
    marker_re = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$")
    action_by_marker = {"Add": "Created", "Update": "Edited", "Delete": "Deleted"}
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in patch.splitlines():
        marker = marker_re.match(line)
        if marker:
            if current:
                rows.append(current)
            current = {
                "action": action_by_marker.get(marker.group(1), "Edited"),
                "path": marker.group(2).strip(),
                "lines": [line],
                "additions": 0,
                "deletions": 0,
            }
            continue
        if current is None:
            continue
        if line.startswith("*** End Patch"):
            current["lines"].append(line)
            rows.append(current)
            current = None
            continue
        current["lines"].append(line)
        if line.startswith("+") and not line.startswith("+++"):
            current["additions"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            current["deletions"] += 1
    if current:
        rows.append(current)
    return rows


def _capsule_delta_line_count(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text.splitlines()))


def _capsule_changed_line_counts(old: str, new: str) -> tuple[int, int]:
    diff = difflib.unified_diff(
        (old or "").splitlines(),
        (new or "").splitlines(),
        lineterm="",
    )
    additions = 0
    deletions = 0
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return additions, deletions


def _capsule_diff_preview(old: str, new: str, *, path: str, max_lines: int = 48) -> list[str]:
    diff = list(difflib.unified_diff(
        (old or "").splitlines(),
        (new or "").splitlines(),
        fromfile=f"{path}:before",
        tofile=f"{path}:after",
        n=3,
        lineterm="",
    ))
    lines: list[str] = []
    for line in diff:
        if line.startswith(("---", "+++")):
            continue
        if line.startswith(("@@", "+", "-", " ")):
            lines.append(_capsule_clean_text(line[:500]))
        if len(lines) >= max_lines:
            diff_sha16 = _sha16("\n".join(diff))
            lines.append(f"[diff preview truncated; sha16={diff_sha16}]")
            break
    return lines


def _capsule_write_preview(content: str, *, max_lines: int = 36) -> list[str]:
    raw_lines = (content or "").splitlines()
    lines = ["@@ write preview"]
    for line in raw_lines[:max_lines]:
        lines.append(_capsule_clean_text(f"+{line}"[:500]))
    if len(raw_lines) > max_lines:
        lines.append(f"[write preview truncated {len(raw_lines) - max_lines} lines; sha16={_sha16(content)}]")
    return lines


def _capsule_tool_edit_deltas(ev: ToolEvent) -> list[dict[str, Any]]:
    inp = ev.input or {}
    base_name = _tool_base_name(ev.name)
    if base_name == "apply_patch":
        return _apply_patch_file_deltas(_raw_apply_patch_input(inp))
    if base_name == "Edit":
        path = str(inp.get("file_path") or "")
        old = str(inp.get("old_string") or "")
        new = str(inp.get("new_string") or "")
        if not path or (not old and not new):
            return []
        additions, deletions = _capsule_changed_line_counts(old, new)
        return [{
            "action": "Edited",
            "path": path,
            "lines": _capsule_diff_preview(old, new, path=path),
            "additions": additions,
            "deletions": deletions,
        }]
    if base_name == "MultiEdit":
        path = str(inp.get("file_path") or "")
        edits = inp.get("edits") if isinstance(inp.get("edits"), list) else []
        if not path or not edits:
            return []
        delta = {"action": "Edited", "path": path, "lines": [], "additions": 0, "deletions": 0}
        for idx, edit in enumerate(edits, start=1):
            if not isinstance(edit, dict):
                continue
            old = str(edit.get("old_string") or "")
            new = str(edit.get("new_string") or "")
            if not old and not new:
                continue
            additions, deletions = _capsule_changed_line_counts(old, new)
            delta["additions"] += additions
            delta["deletions"] += deletions
            if len(delta["lines"]) < 72:
                delta["lines"].append(f"@@ edit {idx}")
                delta["lines"].extend(_capsule_diff_preview(old, new, path=path, max_lines=24))
        return [delta] if delta["additions"] or delta["deletions"] else []
    if base_name == "Write":
        path = str(inp.get("file_path") or "")
        content = str(inp.get("content") or "")
        if not path:
            return []
        return [{
            "action": "Wrote",
            "path": path,
            "lines": _capsule_write_preview(content),
            "additions": _capsule_delta_line_count(content),
            "deletions": 0,
        }]
    return []


TRACE_CAPSULE_DIFF_MAX_TOTAL_LINES = 2400
TRACE_CAPSULE_DIFF_MAX_FILE_LINES = 1200
TRACE_CAPSULE_FINAL_DELTA_MAX_TOTAL_LINES = 1800
TRACE_CAPSULE_COMMIT_CHANGED_PATH_LIMIT = 160
TRACE_CAPSULE_LANDED_COMMIT_SEQUENCE_LIMIT = 12


def _capsule_git_pathspecs(paths: list[str], *, limit: int = 80) -> list[str]:
    pathspecs: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        clean = _capsule_public_trace_path(str(raw_path or ""))
        if clean.startswith("repo:"):
            clean = clean[len("repo:"):].lstrip("/")
        if not clean or clean.startswith("/") or clean.startswith("../"):
            continue
        if "\x00" in clean or "\n" in clean or "\r" in clean:
            continue
        if clean not in seen:
            seen.add(clean)
            pathspecs.append(clean)
    return pathspecs[:limit]


def _capsule_repo_for_cwd(cwd: str | None) -> Path:
    repo = Path(cwd or REPO_ROOT)
    if not repo.exists() or not (repo / ".git").exists():
        return REPO_ROOT
    return repo


def _capsule_commit_changed_paths(*, commit_hash: str, cwd: str | None) -> list[str]:
    commit_clean = (commit_hash or "").strip()
    if not commit_clean or not re.fullmatch(r"[0-9a-f]{7,40}", commit_clean, re.IGNORECASE):
        return []
    repo = _capsule_repo_for_cwd(cwd)
    commands = [
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", "--find-renames", commit_clean],
        ["git", "-C", str(repo), "show", "--name-only", "--format=", "--no-ext-diff", "--find-renames", commit_clean],
    ]
    for args in commands:
        try:
            proc = subprocess.run(args, text=True, capture_output=True, timeout=8)
        except Exception:  # pragma: no cover - defensive around local git state.
            continue
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            continue
        paths = _capsule_git_pathspecs(
            [line.strip() for line in proc.stdout.splitlines() if line.strip()],
            limit=TRACE_CAPSULE_COMMIT_CHANGED_PATH_LIMIT,
        )
        if paths:
            return paths[:TRACE_CAPSULE_COMMIT_CHANGED_PATH_LIMIT]
    return []


def _capsule_is_test_path(path: str) -> bool:
    clean = _capsule_public_trace_path(path)
    if clean.startswith("repo:"):
        clean = clean[len("repo:"):].lstrip("/")
    parts = tuple(part.lower() for part in clean.split("/") if part)
    base = parts[-1] if parts else ""
    if any(part in {"test", "tests", "__tests__", "spec", "specs"} for part in parts):
        return True
    return (
        base.startswith("test_")
        or base.endswith("_test.py")
        or base.endswith("_unit_test.py")
        or base.endswith(".test.py")
        or base.endswith(".test.ts")
        or base.endswith(".test.tsx")
        or base.endswith(".test.js")
        or base.endswith(".test.mjs")
        or base.endswith(".spec.ts")
        or base.endswith(".spec.tsx")
        or base.endswith(".spec.js")
    )


def _capsule_is_generated_projection_path(path: str) -> bool:
    clean = _capsule_public_trace_path(path)
    if clean.startswith("repo:"):
        clean = clean[len("repo:"):].lstrip("/")
    base = Path(clean).name
    generated_names = {
        "AGENT_ROUTES.md",
        "ARCHITECTURE.md",
        "ORGANS.md",
        "AI_WORKFLOW_SYSTEM_PACKET.md",
        "AI_WORKFLOW_SYSTEM_PACKET.last_green.md",
        "content-graph.json",
        "content-manifest.json",
        "projection-status.json",
        "object-map.json",
        "llms.txt",
        "robots.txt",
        "security.txt",
    }
    generated_prefixes = (
        "dist/type_b/",
        "docs/dissemination/",
        "obsidian/prompt_shelf/packets/",
        "sites/microcosm/",
        "state/",
    )
    return base in generated_names or clean.startswith(generated_prefixes)


def _capsule_is_source_owner_path(path: str, *, edit_paths: set[str]) -> bool:
    clean = _capsule_public_trace_path(path)
    if clean.startswith("repo:"):
        clean = clean[len("repo:"):].lstrip("/")
    if clean in edit_paths:
        return True
    source_prefixes = (
        "apps/",
        "codex/doctrine/paper_modules/",
        "codex/doctrine/skills/",
        "codex/standards/",
        "microcosm-substrate/core/",
        "microcosm-substrate/src/",
        "system/",
        "tools/",
    )
    source_suffixes = (
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".mjs",
        ".py",
        ".swift",
        ".ts",
        ".tsx",
    )
    return clean.startswith(source_prefixes) or clean.endswith(source_suffixes)


def _capsule_unique_paths(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in _capsule_git_pathspecs(
        [str(path or "") for path in paths],
        limit=TRACE_CAPSULE_COMMIT_CHANGED_PATH_LIMIT,
    ):
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def _capsule_changed_path_classes(
    *,
    commit_changed_paths: list[str],
    edit_event_paths: list[str],
) -> dict[str, Any]:
    commit_paths = _capsule_unique_paths(commit_changed_paths)
    edit_paths = _capsule_unique_paths(edit_event_paths)
    edit_set = set(edit_paths)
    all_paths = commit_paths or edit_paths
    test_paths = [path for path in all_paths if _capsule_is_test_path(path)]
    generated_paths = [path for path in all_paths if _capsule_is_generated_projection_path(path)]
    source_owner_paths = [
        path
        for path in all_paths
        if path not in test_paths
        and path not in generated_paths
        and _capsule_is_source_owner_path(path, edit_paths=edit_set)
    ]
    classified = set(source_owner_paths) | set(test_paths) | set(generated_paths)
    unclassified = [path for path in all_paths if path not in classified]
    return {
        "schema_version": "agent_trace_changed_path_classes_v1",
        "authority": "commit_changed_paths" if commit_paths else "edit_event_paths",
        "commit_changed_paths": commit_paths,
        "edit_event_paths": edit_paths,
        "source_owner_paths": source_owner_paths,
        "generated_projection_paths": generated_paths,
        "test_paths": test_paths,
        "unclassified_commit_paths": unclassified if commit_paths else [],
        "all_changed_paths": all_paths,
        "classification_basis": "source_owner_test_and_projection_path_heuristics",
    }


def _capsule_commit_path_class_counts(paths: list[str]) -> dict[str, Any]:
    commit_paths = _capsule_unique_paths(paths)
    test_paths = [path for path in commit_paths if _capsule_is_test_path(path)]
    generated_paths = [path for path in commit_paths if _capsule_is_generated_projection_path(path)]
    classified = set(test_paths) | set(generated_paths)
    source_owner_paths = [
        path
        for path in commit_paths
        if path not in classified
        and _capsule_is_source_owner_path(path, edit_paths=set())
    ]
    classified |= set(source_owner_paths)
    unclassified = [path for path in commit_paths if path not in classified]
    return {
        "schema_version": "agent_trace_commit_path_classes_v1",
        "commit_changed_paths": commit_paths,
        "source_owner_paths": source_owner_paths,
        "generated_projection_paths": generated_paths,
        "test_paths": test_paths,
        "unclassified_commit_paths": unclassified,
        "counts": {
            "commit_changed_paths": len(commit_paths),
            "source_owner_paths": len(source_owner_paths),
            "generated_projection_paths": len(generated_paths),
            "test_paths": len(test_paths),
            "unclassified_commit_paths": len(unclassified),
        },
    }


def _capsule_owner_surface_for_paths(paths: list[str]) -> str:
    surfaces: list[str] = []
    seen: set[str] = set()
    for path in _capsule_unique_paths(paths):
        parts = [part for part in path.split("/") if part]
        if not parts:
            continue
        if parts[0] == "tools" and len(parts) >= 3:
            surface = "/".join(parts[:3])
        elif parts[0] == "codex" and len(parts) >= 4:
            surface = "/".join(parts[:4])
        elif parts[0] == "system" and len(parts) >= 3:
            surface = "/".join(parts[:3])
        elif len(parts) >= 2:
            surface = "/".join(parts[:2])
        else:
            surface = parts[0]
        if surface not in seen:
            seen.add(surface)
            surfaces.append(surface)
    if not surfaces:
        return "unknown"
    if len(surfaces) == 1:
        return surfaces[0]
    suffix = f",+{len(surfaces) - 4}_more" if len(surfaces) > 4 else ""
    return "mixed:" + ",".join(surfaces[:4]) + suffix


def _capsule_landed_commit_validation_refs(
    *,
    terminal_check_rows: list[CapsuleEvidenceClassification],
    terminal_governance_rows: list[CapsuleEvidenceClassification],
    limit: int = 8,
) -> list[str]:
    refs: list[str] = []
    for prefix, rows in (("check", terminal_check_rows), ("governance", terminal_governance_rows)):
        for row in rows:
            label = _capsule_clean_text(row.label or row.identity or prefix)
            refs.append(f"{prefix}:{row.result or 'unknown'}:{label}")
            if len(refs) >= limit:
                return refs
    return refs


def _capsule_landed_commit_sequence(
    *,
    commit_rows: list[tuple[str, str]],
    cwd: str | None,
    terminal_commit_hash: str,
    final_delta: dict[str, Any],
    publication_state: str,
    git_publication_trace: dict[str, Any] | None,
    validation_refs: list[str],
) -> list[dict[str, Any]]:
    unique_rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for commit_hash, title in commit_rows:
        clean_hash = (commit_hash or "").strip()
        if not clean_hash or clean_hash in seen:
            continue
        seen.add(clean_hash)
        unique_rows.append((clean_hash, _capsule_clean_text(title or "scoped commit")))
    if len(unique_rows) > TRACE_CAPSULE_LANDED_COMMIT_SEQUENCE_LIMIT:
        unique_rows = unique_rows[-TRACE_CAPSULE_LANDED_COMMIT_SEQUENCE_LIMIT:]

    terminal_hash = (terminal_commit_hash or "").strip()
    git_publication_trace = git_publication_trace or {}
    local_checkpoint_commit = str(git_publication_trace.get("local_checkpoint_commit") or "").strip()
    local_source_commit = str(git_publication_trace.get("local_source_commit") or "").strip()
    remote_published_commit = str(git_publication_trace.get("remote_published_commit") or "").strip()
    git_remote_publication = str(git_publication_trace.get("git_remote_publication") or "none").strip() or "none"
    sequence: list[dict[str, Any]] = []
    for index, (commit_hash, title) in enumerate(unique_rows, start=1):
        changed_paths = _capsule_commit_changed_paths(commit_hash=commit_hash, cwd=cwd)
        path_classes = _capsule_commit_path_class_counts(changed_paths)
        is_terminal = commit_hash == terminal_hash or index == len(unique_rows)
        containment_status = (
            "terminal_final_delta_attached"
            if is_terminal and final_delta.get("attached")
            else ("terminal_final_delta_unavailable" if is_terminal else "sequence_path_scan_only")
        )
        git_publication_role = "none"
        if local_checkpoint_commit and commit_hash == local_checkpoint_commit:
            git_publication_role = "local_checkpoint_commit"
        elif local_source_commit and commit_hash == local_source_commit:
            git_publication_role = "local_source_commit"
        if remote_published_commit and commit_hash == remote_published_commit:
            git_publication_role = "remote_published_commit"
        sequence.append({
            "schema_version": "agent_trace_landed_commit_v1",
            "index": index,
            "role": "terminal" if is_terminal else "earlier_landed",
            "hash": commit_hash,
            "title": title,
            "owner_surface": _capsule_owner_surface_for_paths(changed_paths),
            "commit_changed_paths": changed_paths,
            "path_class_counts": path_classes["counts"],
            "validation_refs": validation_refs,
            "validation_binding": "selected_window_terminal_receipts" if validation_refs else "not_captured",
            "containment_status": containment_status,
            "publication_state": publication_state or "unknown",
            "git_publication_role": git_publication_role,
            "git_remote_publication": git_remote_publication if git_publication_role != "none" else "none",
        })
    return sequence


def _capsule_landed_commit_sequence_summary(sequence: list[dict[str, Any]]) -> str:
    if not sequence:
        return "none"
    terminal = next((row for row in reversed(sequence) if row.get("role") == "terminal"), sequence[-1])
    return (
        f"commits={len(sequence)} terminal={terminal.get('hash') or 'unknown'} "
        f"earlier={max(0, len(sequence) - 1)}"
    )


def _capsule_landed_commit_sequence_section_lines(sequence: list[dict[str, Any]]) -> list[str]:
    lines = ["LANDED_COMMIT_SEQUENCE"]
    terminal = next((row for row in reversed(sequence) if row.get("role") == "terminal"), None)
    lines.append(
        "landed_commit_sequence_summary: "
        f"commits={len(sequence)} "
        f"terminal_commit={(terminal or {}).get('hash') or 'none'} "
        f"limit={TRACE_CAPSULE_LANDED_COMMIT_SEQUENCE_LIMIT} "
        "final_delta_scope=terminal_commit_only"
    )
    if not sequence:
        lines.append("[no landed commits detected in selected window]")
        return lines
    for row in sequence:
        counts = row.get("path_class_counts") or {}
        title = _capsule_clean_text(str(row.get("title") or "scoped commit"))
        if len(title) > 160:
            title = title[:157].rstrip() + "..."
        validation_refs = row.get("validation_refs") or []
        validation_summary = ";".join(str(ref) for ref in validation_refs[:3]) or "none"
        lines.append(
            "landed_commit: "
            f"index={row.get('index')} "
            f"role={row.get('role')} "
            f"hash={row.get('hash')} "
            f"title={title} "
            f"owner_surface={row.get('owner_surface') or 'unknown'} "
            f"commit_changed_paths={counts.get('commit_changed_paths', 0)} "
            f"source_owner_paths={counts.get('source_owner_paths', 0)} "
            f"test_paths={counts.get('test_paths', 0)} "
            f"generated_projection_paths={counts.get('generated_projection_paths', 0)} "
            f"unclassified_commit_paths={counts.get('unclassified_commit_paths', 0)} "
            f"validation_binding={row.get('validation_binding') or 'not_captured'} "
            f"validation_refs={validation_summary} "
            f"containment={row.get('containment_status') or 'unknown'} "
            f"publication_state={row.get('publication_state') or 'unknown'} "
            f"git_publication_role={row.get('git_publication_role') or 'none'} "
            f"git_remote_publication={row.get('git_remote_publication') or 'none'}"
        )
    return lines


def _capsule_path_list_summary(paths: list[str], *, max_items: int = 8) -> str:
    if not paths:
        return "none"
    head = [_capsule_public_trace_path(path) for path in paths[:max_items]]
    suffix = f";+{len(paths) - max_items}_more" if len(paths) > max_items else ""
    return ";".join(head) + suffix


def _capsule_changed_summary(path_classes: dict[str, Any]) -> str:
    commit_count = len(path_classes.get("commit_changed_paths") or [])
    edit_count = len(path_classes.get("edit_event_paths") or [])
    source_count = len(path_classes.get("source_owner_paths") or [])
    test_count = len(path_classes.get("test_paths") or [])
    projection_count = len(path_classes.get("generated_projection_paths") or [])
    unclassified_count = len(path_classes.get("unclassified_commit_paths") or [])
    authority = path_classes.get("authority") or "edit_event_paths"
    if commit_count:
        return (
            f"commit_paths={commit_count} edit_event_paths={edit_count} "
            f"source_owner_paths={source_count} test_paths={test_count} "
            f"generated_projection_paths={projection_count} "
            f"unclassified_commit_paths={unclassified_count}"
        )
    if edit_count:
        return (
            f"edit_event_paths={edit_count} source_owner_paths={source_count} "
            f"test_paths={test_count} generated_projection_paths={projection_count}"
        )
    return f"none captured authority={authority}"


def _capsule_truncated_raw_diff_lines(
    text: str,
    *,
    max_total_lines: int = TRACE_CAPSULE_FINAL_DELTA_MAX_TOTAL_LINES,
) -> tuple[list[str], int, str]:
    raw_lines = [line.rstrip("\n").replace("\x00", "[nul]")[:600] for line in (text or "").splitlines()]
    raw_lines = [line for line in raw_lines if line.strip()]
    if len(raw_lines) <= max_total_lines:
        return raw_lines, 0, ""
    kept = raw_lines[:max_total_lines]
    omitted = len(raw_lines) - len(kept)
    sha16 = _sha16("\n".join(raw_lines))
    kept.append(f"[final delta truncated; omitted_lines={omitted}; sha16={sha16}]")
    return kept, omitted, sha16


def _capsule_final_delta_paths(diff_lines: list[str], fallback_paths: list[str]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        clean = _capsule_public_trace_path(path)
        if clean.startswith("repo:"):
            clean = clean[len("repo:"):].lstrip("/")
        if clean and clean not in seen:
            seen.add(clean)
            paths.append(clean)

    for line in diff_lines:
        match = re.match(r"^diff --git a/(.+?) b/(.+)$", line)
        if match:
            add(match.group(2))
    for path in fallback_paths:
        add(path)
    return paths[:80]


def _capsule_final_delta_for_trace(
    *,
    commit_hash: str,
    changed_paths: list[str],
    cwd: str | None,
    max_total_lines: int = TRACE_CAPSULE_FINAL_DELTA_MAX_TOTAL_LINES,
) -> dict[str, Any]:
    repo = _capsule_repo_for_cwd(cwd)
    pathspecs = _capsule_git_pathspecs(changed_paths)
    commit_clean = (commit_hash or "").strip()
    if commit_clean and not re.fullmatch(r"[0-9a-f]{7,40}", commit_clean, re.IGNORECASE):
        commit_clean = ""

    base: dict[str, Any] = {
        "schema_version": "agent_trace_final_delta_v1",
        "attached": False,
        "state": "not_captured",
        "source": "none",
        "authority": "edit_event_log_only",
        "commit": commit_clean,
        "pathspecs": pathspecs,
        "paths": pathspecs,
        "line_count": 0,
        "omitted_lines": 0,
        "truncated_sha16": "",
        "command": "",
        "lines": [],
        "reason": "no_commit_or_worktree_delta_captured",
    }

    if commit_clean:
        args = [
            "git",
            "-C",
            str(repo),
            "show",
            "--format=fuller",
            "--stat",
            "--patch",
            "--no-ext-diff",
            "--unified=3",
            "--find-renames",
            commit_clean,
        ]
        if pathspecs:
            args.extend(["--", *pathspecs])
        source = "git_show_commit"
        command = f"git show --stat --patch --no-ext-diff --unified=3 {commit_clean}"
        if pathspecs:
            command += " -- " + " ".join(shlex.quote(path) for path in pathspecs[:8])
            if len(pathspecs) > 8:
                command += f" ...(+{len(pathspecs) - 8} paths)"
    elif pathspecs and cwd:
        args = [
            "git",
            "-C",
            str(repo),
            "diff",
            "--no-ext-diff",
            "--unified=3",
            "--",
            *pathspecs,
        ]
        source = "git_diff_worktree"
        command = "git diff --no-ext-diff --unified=3 -- " + " ".join(shlex.quote(path) for path in pathspecs[:8])
        if len(pathspecs) > 8:
            command += f" ...(+{len(pathspecs) - 8} paths)"
    else:
        if pathspecs:
            base["reason"] = "worktree_delta_requires_turn_cwd"
        return base

    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=8)
    except Exception as exc:  # pragma: no cover - defensive around local git state.
        base.update({
            "state": "capture_failed",
            "source": source,
            "command": command,
            "reason": f"git_command_failed:{_capsule_clean_text(str(exc))[:160]}",
        })
        return base

    output = proc.stdout or ""
    if proc.returncode != 0 or not output.strip():
        reason = "git_command_returned_no_patch"
        if proc.returncode != 0:
            stderr = _capsule_clean_text((proc.stderr or "").strip())[:160]
            reason = f"git_command_failed_exit_{proc.returncode}" + (f":{stderr}" if stderr else "")
        base.update({
            "state": "unavailable",
            "source": source,
            "command": command,
            "reason": reason,
        })
        return base

    lines, omitted, sha16 = _capsule_truncated_raw_diff_lines(output, max_total_lines=max_total_lines)
    paths = _capsule_final_delta_paths(lines, pathspecs)
    base.update({
        "attached": True,
        "state": f"{source}_attached",
        "source": source,
        "authority": "final_substrate_delta",
        "paths": paths,
        "line_count": len(lines),
        "omitted_lines": omitted,
        "truncated_sha16": sha16,
        "command": command,
        "lines": lines,
        "reason": "attached",
    })
    return base


def _capsule_final_delta_section_lines(final_delta: dict[str, Any]) -> list[str]:
    lines = ["FINAL_DELTA"]
    attached = bool(final_delta.get("attached"))
    source = str(final_delta.get("source") or "none")
    commit = str(final_delta.get("commit") or "none")
    reason = _capsule_clean_text(str(final_delta.get("reason") or "none"))
    paths = list(final_delta.get("paths") or [])
    lines.append(
        "final_delta_summary: "
        f"attached={'true' if attached else 'false'} "
        f"state={final_delta.get('state') or 'not_captured'} "
        f"source={source} commit={commit} paths={len(paths)} "
        f"lines={int(final_delta.get('line_count') or 0)} "
        f"omitted_lines={int(final_delta.get('omitted_lines') or 0)} "
        f"reason={reason or 'none'}"
    )
    lines.append(
        "diff_authority: "
        f"{final_delta.get('authority') or 'edit_event_log_only'} "
        "patch_attempts_are_not_final_state=true "
        f"final_substrate_delta_attached={'true' if attached else 'false'}"
    )
    if source == "git_show_commit":
        lines.append("final_delta_scope: terminal_commit_delta_only=true semantic_landed_work=LANDED_COMMIT_SEQUENCE")
    elif source == "git_diff_worktree":
        lines.append("final_delta_scope: worktree_delta_only=true semantic_landed_work=not_committed")
    command = str(final_delta.get("command") or "")
    if command:
        lines.extend(_capsule_command_display_lines(command))
    body = [str(line) for line in (final_delta.get("lines") or [])]
    lines.extend(body if body else ["[final substrate delta not attached]"])
    return lines


def _capsule_polarity_diff_line(raw_line: Any) -> str:
    line = _capsule_clean_text(str(raw_line)[:500])
    if line.startswith("@@"):
        return line
    if line.startswith("+") and not line.startswith("+++"):
        return f"+ | {line[1:]}"
    if line.startswith("-") and not line.startswith("---"):
        return f"- | {line[1:]}"
    if line.startswith(" "):
        return f"  | {line[1:]}"
    return line


def _capsule_diff_body_lines(
    raw_lines: list[Any],
    *,
    max_file_lines: int = TRACE_CAPSULE_DIFF_MAX_FILE_LINES,
) -> tuple[list[str], int, str]:
    clean_lines = [
        _capsule_polarity_diff_line(line)
        for line in (raw_lines or [])
        if str(line or "").strip()
    ]
    if len(clean_lines) <= max_file_lines:
        return clean_lines, 0, ""
    kept = clean_lines[:max_file_lines]
    omitted = len(clean_lines) - len(kept)
    sha16 = _sha16("\n".join(clean_lines))
    kept.append(f"[diff body truncated; omitted_lines={omitted}; sha16={sha16}]")
    return kept, omitted, sha16


def _capsule_diff_section_lines(
    edit_rows: list[dict[str, Any]],
    *,
    max_total_lines: int = TRACE_CAPSULE_DIFF_MAX_TOTAL_LINES,
    max_file_lines: int = TRACE_CAPSULE_DIFF_MAX_FILE_LINES,
) -> list[str]:
    lines = ["EDIT_EVENT_LOG"]
    if not edit_rows:
        lines.append(
            "edit_event_log_summary: rows=0 chronology_only=true patch_attempts_are_not_final_state=true"
        )
        lines.append("none captured")
        return lines

    path_count = len({str(row.get("path") or "") for row in edit_rows if row.get("path")})
    additions = sum(int(row.get("additions") or 0) for row in edit_rows)
    deletions = sum(int(row.get("deletions") or 0) for row in edit_rows)
    lines.append(
        "edit_event_log_summary: "
        f"files={path_count} rows={len(edit_rows)} additions=+{additions} deletions=-{deletions} "
        "source=tool_edit_events chronology_only=true patch_attempts_are_not_final_state=true"
    )
    lines.append(
        f"edited_files_summary: files={path_count} additions=+{additions} deletions=-{deletions} source=edit_event_log"
    )

    emitted_body_lines = 0
    omitted_file_count = 0
    omitted_body_lines = 0
    truncated_sha16s: list[str] = []
    for index, row in enumerate(edit_rows, start=1):
        raw_body = row.get("lines") if isinstance(row.get("lines"), list) else []
        body_lines, file_omitted, file_sha16 = _capsule_diff_body_lines(
            raw_body,
            max_file_lines=max_file_lines,
        )
        next_header = (
            f"D{index:03d} {_capsule_clean_text(str(row.get('path') or ''))} "
            f"+{int(row.get('additions') or 0)} -{int(row.get('deletions') or 0)}"
        )
        next_block_cost = 1 + len(body_lines)
        if emitted_body_lines + next_block_cost > max_total_lines:
            omitted_file_count = len(edit_rows) - index + 1
            omitted_body_lines += len(raw_body)
            if raw_body:
                truncated_sha16s.append(_sha16("\n".join(str(line) for line in raw_body)))
            break
        lines.append(next_header)
        lines.extend(body_lines or ["[no diff body captured]"])
        emitted_body_lines += next_block_cost
        omitted_body_lines += file_omitted
        if file_sha16:
            truncated_sha16s.append(file_sha16)

    if omitted_file_count or omitted_body_lines:
        sha_part = f" sha16={_sha16('|'.join(truncated_sha16s))}" if truncated_sha16s else ""
        lines.append(
            f"diff_omission: omitted_files={omitted_file_count} omitted_lines={omitted_body_lines}{sha_part}"
        )
    return lines


def _trace_paste_body(ev: ToolEvent) -> str:
    inp = ev.input or {}
    base_name = _tool_base_name(ev.name)
    if base_name == "Bash":
        return f"$ {inp.get('command', '')}"
    if base_name in ("exec_command", "shell"):
        cmd = inp.get("cmd") or inp.get("command") or ""
        return f"$ {cmd}"
    if base_name in ("Read", "Edit", "Write", "MultiEdit"):
        return str(inp.get("file_path", "")) or ""
    if base_name == "Glob":
        return f"$ glob {inp.get('pattern', '')}"
    if base_name == "Grep":
        pat = inp.get("pattern", "")
        glob = inp.get("glob") or ""
        scope = f" --glob {glob!r}" if glob else ""
        return f"$ grep {pat!r}{scope}"
    if base_name == "apply_patch":
        return "$ apply_patch"
    return json.dumps(inp, ensure_ascii=False)[:200]


def _running_session_id(output_text: str) -> str:
    m = re.search(r"Process running with session ID\s+(\d+)", output_text or "")
    return m.group(1) if m else ""


def _poll_session_id(ev: ToolEvent) -> str:
    if _tool_base_name(ev.name) != "write_stdin":
        return ""
    value = (ev.input or {}).get("session_id")
    return str(value) if value not in (None, "") else ""


def _renderable_trace_tool_events(events: list[ToolEvent]) -> list[tuple[ToolEvent, str, int | None, bool]]:
    """Collapse Codex async process polling into the shell command that spawned it."""
    polls_by_session: dict[str, list[ToolEvent]] = {}
    for ev in events:
        sid = _poll_session_id(ev)
        if sid:
            polls_by_session.setdefault(sid, []).append(ev)

    rendered: list[tuple[ToolEvent, str, int | None, bool]] = []
    for ev in events:
        if _poll_session_id(ev):
            continue
        output_text = ev.output_text
        exit_code = ev.exit_code
        is_error = ev.is_error
        sid = _running_session_id(output_text)
        if sid and sid in polls_by_session:
            poll_outputs = [
                p.output_text
                for p in polls_by_session[sid]
                if p.output_text and not p.output_text.startswith("[no ")
            ]
            if poll_outputs:
                output_text = "\n".join(poll_outputs)
            poll_exit_codes = [p.exit_code for p in polls_by_session[sid] if p.exit_code is not None]
            if poll_exit_codes:
                exit_code = poll_exit_codes[-1]
            is_error = is_error or any(p.is_error for p in polls_by_session[sid])
        rendered.append((ev, output_text, exit_code, is_error))
    return rendered


def render_trace_paste(
    turn: Turn,
    *,
    include_prompt: bool = True,
    intern_repeated_prompts: bool = False,
) -> str:
    """Render in Agent Trace Structurer parser-compatible plain text.

    Uses bare tool markers (Bash, Read, Edited, Wrote, Success, Failed) so
    parser.mjs::classifyClipboardText returns 'agent_trace' and parseAgentTrace
    detects a richer trace_format than 'plain_text'.

    include_prompt=False omits the raw user prompt body but keeps a metadata
    line (chars + sha) so downstream consumers know it existed. The default
    "selected mission latest trace" action elides the prompt body because the
    operator usually wants the tool/assistant activity, not the original
    instructions.
    """
    lines: list[str] = []
    lines.append(f"# {turn.provider} session {turn.session_id} turn {turn.turn_index}")
    trace_window = (turn.source_ref or {}).get("trace_window") or (turn.source_ref or {}).get("prompt_cycle")
    if isinstance(trace_window, dict):
        start = trace_window.get("start_turn_index")
        end = trace_window.get("end_turn_index")
        count = trace_window.get("turn_count")
        sha = trace_window.get("prompt_sha16") or turn.prompt_sha256_16
        threshold = trace_window.get("short_prompt_threshold_words")
        mode = trace_window.get("mode") or "selected_turn"
        threshold_text = f" short_prompt_threshold_words={threshold}" if threshold is not None else ""
        lines.append(
            f"# trace_window turns={start}-{end} count={count} "
            f"mode={mode} prompt_window_sha16={sha}{threshold_text}"
        )
    if turn.cwd:
        lines.append(f"cwd: {turn.cwd}")
    if turn.started_at:
        lines.append(f"started: {turn.started_at}")
    if turn.completed_at:
        lines.append(f"completed: {turn.completed_at}")
    lines.append(f"status: {'complete' if turn.is_complete else 'partial'}")
    lines.append("")

    if turn.prompt_text:
        if include_prompt:
            lines.append("Prompt")
            if intern_repeated_prompts:
                lines.extend(_render_prompt_with_interns(turn.prompt_text))
            else:
                lines.append(turn.prompt_text)
            lines.append("")
        else:
            if intern_repeated_prompts:
                summary_line = _prompt_intern_summary_line(turn.prompt_text)
                if summary_line:
                    lines.append(summary_line)
            lines.append(
                f"# prompt_omitted chars={turn.prompt_char_count} "
                f"sha16={turn.prompt_sha256_16}"
            )
            lines.append("")

    renderable_tools = _renderable_trace_tool_events(turn.tool_events)
    total = len(renderable_tools)
    items: list[tuple[int, str, Any]] = []
    for render_index, wrapped in enumerate(renderable_tools, start=1):
        ev = wrapped[0]
        source_index = (ev.source_record_indices or [ev.index])[0]
        items.append((source_index, "tool", (render_index, wrapped)))
    for ev in turn.assistant_events:
        if ev.text.strip():
            items.append((ev.source_record_index, "assistant", ev))
    items.sort(key=lambda row: (row[0], 0 if row[1] == "assistant" else 1))

    emitted_assistant_texts: set[str] = set()
    for _, kind, payload in items:
        if kind == "assistant":
            ev = payload
            text = ev.text.strip()
            if not text or text in emitted_assistant_texts:
                continue
            lines.append("Assistant")
            lines.append(text)
            lines.append("")
            emitted_assistant_texts.add(text)
            continue

        render_index, wrapped = payload
        ev, output_text, exit_code, is_error = wrapped
        marker = _trace_paste_marker_for(ev.name)
        lines.append("Ran")
        desc = (ev.input or {}).get("description") if _tool_base_name(ev.name) == "Bash" else None
        if not desc:
            desc = f"{ev.name} ({render_index}/{total})"
        lines.append(str(desc))
        lines.append(marker)
        body = _trace_paste_body(ev)
        if body:
            lines.append(body)
        if output_text and not output_text.startswith("[no "):
            lines.append(output_text)
        if exit_code is not None and exit_code != 0:
            lines.append(f"Failed (exit {exit_code})")
        elif is_error:
            lines.append("Failed")
        else:
            lines.append("Success")
        lines.append("")

        if _tool_base_name(ev.name) == "apply_patch":
            for delta in _apply_patch_file_deltas(_raw_apply_patch_input(ev.input or {})):
                lines.append(delta["action"])
                lines.append(delta["path"])
                lines.append(f"+{delta.get('additions', 0)}")
                lines.append(f"-{delta.get('deletions', 0)}")
                lines.extend(delta.get("lines") or [])
                lines.append("")

    if turn.assistant_text and turn.assistant_text.strip() not in emitted_assistant_texts:
        lines.append("Assistant")
        lines.append(turn.assistant_text)
    return "\n".join(lines)


def _copy_to_macos_clipboard(content: str) -> bool:
    try:
        proc = subprocess.run(["pbcopy"], input=content, text=True, timeout=10)
        return proc.returncode == 0
    except Exception:
        return False


def write_structurer_clip(
    turn: Turn,
    *,
    include_prompt: bool = True,
    intern_repeated_prompts: bool = False,
) -> dict:
    """Render trace-paste, run parser.mjs, write raw + full packet + thin clip.

    Writes three artifacts in their canonical Structurer directories so the
    System Bar can choose tier per action (Copy Compressed -> thin clip,
    Copy Full -> raw text, Copy Parsed -> full packet) and Finder Reveal
    has a guaranteed existing path. Prepends a schema-compatible entry onto
    clipboard_history.json with all path aliases populated.
    """
    if not STRUCTURER_PARSER_PATH.exists():
        return {"ok": False, "error": f"parser not found at {STRUCTURER_PARSER_PATH}"}

    raw_text = render_trace_paste(
        turn,
        include_prompt=include_prompt,
        intern_repeated_prompts=intern_repeated_prompts,
    )
    raw_bytes = raw_text.encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()[:8]
    timestamp_iso = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    timestamp_fs = timestamp_iso.replace(":", "-")
    base = f"clip-{timestamp_fs}-agent_trace-{digest}"
    raw_path = TRACE_STRUCTURER_RAW / f"{base}.raw.txt"
    capture_path = TRACE_STRUCTURER_CAPTURES / f"{base}.json"
    thin_path = TRACE_STRUCTURER_CLIPS / f"{base}.json"
    export_path = TRACE_STRUCTURER_EXPORTS / f"{base}.json"

    TRACE_STRUCTURER_RAW.mkdir(parents=True, exist_ok=True)
    TRACE_STRUCTURER_CAPTURES.mkdir(parents=True, exist_ok=True)
    TRACE_STRUCTURER_CLIPS.mkdir(parents=True, exist_ok=True)
    TRACE_STRUCTURER_EXPORTS.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw_text, encoding="utf-8")

    parser_result = _build_thin_clip_via_node(raw_path, capture_path, thin_path)
    if not parser_result.get("ok"):
        return {
            "ok": False,
            "error": parser_result.get("error", "parser failed"),
            "raw_path": str(raw_path),
        }

    # Stage a Reveal-able copy of the thin clip in Exports/AIW Captures so the
    # Swift app's revealDownloadedFile() check (isSameOrChild downloadsExportURL)
    # passes. The Exports copy is the same bytes as the Clips/ thin clip.
    try:
        export_path.write_bytes(thin_path.read_bytes())
    except Exception:
        pass

    raw_bytes_on_disk = raw_path.stat().st_size if raw_path.exists() else len(raw_bytes)
    full_bytes = capture_path.stat().st_size if capture_path.exists() else 0
    thin_bytes = thin_path.stat().st_size if thin_path.exists() else 0
    export_bytes = export_path.stat().st_size if export_path.exists() else 0
    thin_ratio = round(thin_bytes / raw_bytes_on_disk, 4) if raw_bytes_on_disk else None
    source_watermark = _source_watermark_for_turn(turn)

    title, title_source = _resolve_session_title(
        turn.provider, turn.session_id, Path(turn.session_file),
        codex_thread_names=_load_codex_thread_names(),
        title_aliases=_load_title_aliases(),
        claude_desktop_titles=_load_claude_desktop_titles(),
    )
    if not title:
        first_line = ""
        for raw in (turn.prompt_text or "").splitlines():
            stripped = raw.strip()
            if stripped:
                first_line = stripped
                break
        title = first_line[:120] or f"{turn.provider} turn {turn.turn_index}"
        if title_source == "no_title_resolved":
            title_source = "current_turn_prompt_preview"

    now_local = _dt.datetime.now()
    trace_window = (turn.source_ref or {}).get("trace_window") or (turn.source_ref or {}).get("prompt_cycle")
    prompt_cycle_label = ""
    if isinstance(trace_window, dict) and trace_window.get("turn_count", 1) != 1:
        prompt_cycle_label = f"turns {trace_window.get('start_turn_index')}-{trace_window.get('end_turn_index')}"
    else:
        prompt_cycle_label = f"turn {turn.turn_index}"

    history_entry = {
        "captured_at": timestamp_iso,
        "exported_at": timestamp_iso,
        "recorded_at": timestamp_iso,
        "kind": "agent_trace",
        "content_kind": "text",
        "filename": f"{base}.json",
        "input_hash": digest,
        "chars": len(raw_text),
        "bytes": len(raw_bytes),
        "raw_bytes": raw_bytes_on_disk,
        "source_bytes": raw_bytes_on_disk,
        "content_bytes": raw_bytes_on_disk,
        "clipboard_bytes": raw_bytes_on_disk,
        "clip_bytes": thin_bytes,
        "full_packet_bytes": full_bytes,
        "source_lines": parser_result.get("input_lines", 0),
        "source_chunks": parser_result.get("source_chunks", 0),
        "events": parser_result.get("trace_blocks", 0),
        "artifacts": parser_result.get("artifacts", 0),
        "ids": parser_result.get("entities", 0),
        "patterns": parser_result.get("sections", 0),
        "raw_path": str(raw_path),
        "stored_path": str(capture_path),
        "full_packet_path": str(capture_path),
        "clip_store_path": str(thin_path),
        "download_path": str(export_path),
        "export_path": str(export_path),
        "path": str(export_path),
        "storage_scope": "downloads_export",
        "time_label": now_local.strftime("%H:%M:%S"),
        "hud_caption": f"{turn.provider} · {title[:48]} · {prompt_cycle_label} · {len(turn.tool_events)} tools",
        "validations": 0,
        "mutations": 0,
        "file_count": 0,
        "commands": sum(1 for e in turn.tool_events if e.name in ("Bash", "exec_command", "shell")),
        "originator": "cli_prompt_trace",
        "source_watermark": source_watermark,
        "copied_source_watermark": source_watermark,
        "cli_prompt_trace": {
            "schema": SCHEMA_VERSION,
            "trace_id": turn.turn_id,
            "session_id": turn.session_id,
            "session_file": turn.session_file,
            "turn_index": turn.turn_index,
            "is_complete": turn.is_complete,
            "partial_reason": turn.partial_reason,
            "tool_count": len(turn.tool_events),
            "error_count": sum(1 for e in turn.tool_events if e.is_error),
            "title": title,
            "title_source": title_source,
            "prompt_sha16": turn.prompt_sha256_16,
            "prompt_char_count": turn.prompt_char_count,
            "raw_bytes": raw_bytes_on_disk,
            "thin_clip_bytes": thin_bytes,
            "full_packet_bytes": full_bytes,
            "thin_to_raw_ratio": thin_ratio,
            "source_watermark": source_watermark,
            "copied_source_watermark": source_watermark,
        },
    }
    if isinstance(trace_window, dict):
        history_entry["trace_window"] = trace_window
        history_entry["cli_prompt_trace"]["trace_window"] = trace_window

    history: list = []
    if TRACE_STRUCTURER_HISTORY.exists():
        try:
            history = json.loads(TRACE_STRUCTURER_HISTORY.read_text() or "[]")
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []
    new_history = [history_entry] + history
    tmp = TRACE_STRUCTURER_HISTORY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(new_history, indent=2, ensure_ascii=False))
    tmp.replace(TRACE_STRUCTURER_HISTORY)

    reveal_check = {
        "raw_path_exists": raw_path.exists(),
        "stored_path_exists": capture_path.exists(),
        "clip_store_path_exists": thin_path.exists(),
        "export_path_exists": export_path.exists(),
        "history_path_exists": TRACE_STRUCTURER_HISTORY.exists(),
        "swift_reveal_target": str(export_path) if export_path.exists() else None,
    }

    return {
        "ok": True,
        "kind": "cli_prompt_trace.structurer_clip_written",
        "provider": turn.provider,
        "session_id": turn.session_id,
        "turn_id": turn.turn_id,
        "turn_index": turn.turn_index,
        "trace_id": turn.turn_id,
        "is_complete": turn.is_complete,
        "tool_count": len(turn.tool_events),
        "title": title,
        "title_source": title_source,
        "prompt_sha16": turn.prompt_sha256_16,
        "prompt_char_count": turn.prompt_char_count,
        "trace_window": trace_window if isinstance(trace_window, dict) else None,
        "source_watermark": source_watermark,
        "copied_source_watermark": source_watermark,
        "source_text_hash": digest,
        "raw_path": str(raw_path),
        "stored_path": str(capture_path),
        "clip_store_path": str(thin_path),
        "export_path": str(export_path),
        "history_path": str(TRACE_STRUCTURER_HISTORY),
        "bytes": {
            "raw": raw_bytes_on_disk,
            "thin_clip": thin_bytes,
            "full_packet": full_bytes,
            "export_copy": export_bytes,
            "thin_to_raw_ratio": thin_ratio,
        },
        "reveal_check": reveal_check,
        "parser_verdict": {k: v for k, v in parser_result.items() if k != "ok"},
    }


TRACE_CAPSULE_SCHEMA_VERSION = "agent_trace_capsule_text_v3"
TRACE_CLOSEOUT_REPORT_SCHEMA_VERSION = "agent_trace_closeout_report_v1"


@dataclass(frozen=True)
class CapsuleEvidenceClassification:
    bucket: str
    result: str
    label: str
    identity: str
    evidence_scope: str = "unknown"
    validation_class: str = ""
    residual_id: str = ""
    residual_ids: tuple[str, ...] = ()
    ambient_warning_class: str = ""
    validation_obligation_ids: tuple[str, ...] = ()
    validation_file_selectors: tuple[str, ...] = ()
    validation_domain: str = "unknown"
    validation_subject: str = "unknown"
    workspace_role: str = "none"
    gate_effect: str = "ambient"


@dataclass(frozen=True)
class CapsuleReasoningEvent:
    note_id: str
    category: str
    text: str
    source_index: int = 0


@dataclass(frozen=True)
class CapsuleEpisodeEvidence:
    source_index: int
    row_id: str
    kind: str
    result: str = ""
    identity: str = ""


@dataclass(frozen=True)
class CapsuleEvidenceSummary:
    checks: tuple[CapsuleEvidenceClassification, ...]
    terminal_checks: tuple[CapsuleEvidenceClassification, ...]
    governance_receipts: tuple[CapsuleEvidenceClassification, ...]
    terminal_governance: tuple[CapsuleEvidenceClassification, ...]
    diagnostics: tuple[CapsuleEvidenceClassification, ...]
    recovered_failures: int
    final_validation_basis: str

    @property
    def check_counts(self) -> tuple[int, int, int]:
        return _capsule_result_counts(list(self.checks))

    @property
    def terminal_check_counts(self) -> tuple[int, int, int]:
        return _capsule_result_counts(list(self.terminal_checks))

    @property
    def governance_counts(self) -> tuple[int, int, int]:
        return _capsule_result_counts(list(self.governance_receipts))

    @property
    def terminal_governance_counts(self) -> tuple[int, int, int]:
        return _capsule_result_counts(list(self.terminal_governance))

    @property
    def diagnostic_fail_count(self) -> int:
        return sum(1 for row in self.diagnostics if row.result == "fail")

    @property
    def terminal_check_by_identity(self) -> dict[str, CapsuleEvidenceClassification]:
        return {row.identity: row for row in self.terminal_checks if row.identity}

    @property
    def captured_residual_ids(self) -> tuple[str, ...]:
        ids = sorted({
            residual_id
            for row in (*self.checks, *self.governance_receipts)
            for residual_id in (row.residual_ids or ((row.residual_id,) if row.residual_id else ()))
        })
        return tuple(ids)


@dataclass(frozen=True)
class CapsuleResidualTaxonomy:
    open_product_residuals: tuple[str, ...] = ()
    open_validation_process_residuals: tuple[str, ...] = ()
    closed_residuals_seen: tuple[str, ...] = ()
    blocked_external_observation_residuals: tuple[str, ...] = ()
    projection_or_view_artifacts_seen: tuple[str, ...] = ()
    unresolved_residual_mentions: tuple[str, ...] = ()
    passive_residual_mentions_observed: tuple[str, ...] = ()

    @property
    def all_residual_mentions(self) -> tuple[str, ...]:
        return tuple(sorted({
            *self.open_product_residuals,
            *self.open_validation_process_residuals,
            *self.closed_residuals_seen,
            *self.blocked_external_observation_residuals,
            *self.projection_or_view_artifacts_seen,
            *self.unresolved_residual_mentions,
        }))


def _fs_safe_token(value: str, fallback: str = "artifact") -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", value or "").strip("-._")
    return token[:120] or fallback


def _short_session_tag(session_id: str) -> str:
    return (session_id or "session")[:8]


def _duration_label(started_at: str | None, completed_at: str | None) -> str:
    if not started_at or not completed_at:
        return ""
    ms = _iso_diff_ms(started_at, completed_at)
    if ms is None or ms < 0:
        return ""
    seconds = ms // 1000
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def _capsule_command(ev: ToolEvent) -> str:
    text = _trace_paste_body(ev)
    if text.startswith("$ "):
        return text
    base_name = _tool_base_name(ev.name)
    if base_name == "Read" and text:
        return f"Read {text}"
    if base_name in ("Edit", "Write", "MultiEdit") and text:
        return f"{base_name} {text}"
    return text or ev.name


def _capsule_role(ev: ToolEvent, command: str) -> str:
    lower = command.lower()
    base_name = _tool_base_name(ev.name)
    surface_lower = "\n".join(_capsule_command_surface_lines(command)).lower()
    is_boot = any(token in surface_lower for token in ("kernel.py --pulse", "kernel.py --phase", "kernel.py --entry", "kernel.py --preflight", "kernel.py --info"))
    is_search = any(token in surface_lower for token in ("rg ", "grep ", "jq ", "sed ", "head ", "tail ", "wc "))
    if base_name in ("Edit", "Write", "MultiEdit", "apply_patch") or "apply_patch" in lower:
        return "edit"
    try:
        bucket, _, _ = _capsule_command_bucket_and_label(command, "cmd")
        if bucket == "check":
            return "test"
        if bucket == "governance":
            return "gov"
        if bucket == "diagnostic":
            if is_boot:
                return "boot"
            if is_search:
                return "srch"
            if base_name == "Read":
                return "read"
            return "diag"
    except NameError:
        pass
    if any(token in surface_lower for token in ("py_compile", "node --check", "node --test", "pytest", "repo-pytest", "swiftc -parse", "trace_variant_smoke.py", "trace_size_smoke.py")):
        return "test"
    if is_boot:
        return "boot"
    if is_search:
        return "srch"
    if base_name == "Read":
        return "read"
    return "cmd"


def _capsule_status(exit_code: int | None, is_error: bool) -> str:
    if exit_code is not None:
        return "pass" if exit_code == 0 else "fail"
    return "fail" if is_error else "pass"


def _capsule_output_lines(output: str, *, role: str, status: str) -> tuple[list[str], bool]:
    if not output or output.startswith("[no "):
        return (["no captured output"], False)
    redacted_output, redaction_hits = _redact_secrets(output)
    raw_lines = redacted_output.strip("\n").splitlines()
    filtered: list[str] = []
    truncated_line = False
    codex_event_json_run: list[str] = []
    transport_re = re.compile(
        r"^(?:"
        r"Process exited with code -?\d+|"
        r"Process running with session ID \d+|"
        r"with session ID \d+|"
        r"with code -?\d+|"
        r"\d+(?:\.\d+)? seconds|"
        r"Chunk ID: .+|"
        r"Wall time: .+|"
        r"Original token count: .+"
        r")$"
    )

    def flush_codex_event_json_run() -> None:
        nonlocal codex_event_json_run, truncated_line
        if not codex_event_json_run:
            return
        truncated_line = True
        if len(codex_event_json_run) == 1:
            line = codex_event_json_run[0]
            filtered.append(f"[codex event JSON line omitted; chars={len(line)}; sha16={_sha16(line)}]")
        else:
            total_chars = sum(len(line) for line in codex_event_json_run)
            filtered.append(
                "[codex event JSON lines omitted; "
                f"count={len(codex_event_json_run)} chars={total_chars} "
                f"first_sha16={_sha16(codex_event_json_run[0])} "
                f"last_sha16={_sha16(codex_event_json_run[-1])}]"
            )
        codex_event_json_run = []

    for line in raw_lines:
        stripped = line.strip()
        if transport_re.match(stripped):
            continue
        if stripped.startswith('{"id":"agent-event-') or (
            '"source_runtime":"codex_app"' in stripped and '"payload":' in stripped
        ):
            codex_event_json_run.append(line)
            continue
        flush_codex_event_json_run()
        if "data:image/" in line and ";base64," in line:
            filtered.append(f"[image data URI omitted; chars={len(line)}; sha16={_sha16(line)}]")
            truncated_line = True
            continue
        if "[reasoning note omitted" in line:
            filtered.append(f"[legacy reasoning omission marker output omitted; chars={len(line)}; sha16={_sha16(line)}]")
            truncated_line = True
            continue
        if len(line) > 1400:
            filtered.append(_capsule_clean_text(line[:1100].rstrip()) + f" [line truncated {len(line) - 1100} chars; sha16={_sha16(line)}]")
            truncated_line = True
            continue
        filtered.append(_capsule_clean_text(line.rstrip()))
    flush_codex_event_json_run()
    if redaction_hits:
        filtered.insert(0, f"[redaction applied: {_capsule_redaction_hit_summary(redaction_hits)}]")
    if not filtered:
        return (["no captured output"], False)
    joined = "\n".join(filtered)
    if "TRACE CAPSULE v" in joined and "\nSUMMARY\n" in joined and "\nTIMELINE\n" in joined:
        return (["[nested trace capsule output omitted]"], True)
    structural_re = re.compile(
        r"^(?:TRACE CAPSULE v\d+|SUMMARY|TIMELINE|OMISSIONS|K\d{3}\s+|"
        r"coverage:|status:|result:|changed:|final_validation:|checks:|terminal_checks:|"
        r"governance_receipts:|terminal_governance:|diagnostics:|visible_progress:|"
        r"thinking:|reasoning_digest:|episodes:|validation_progress:|commit:|open:)"
    )
    filtered = [
        f"> {line}" if structural_re.match(line.strip()) else line
        for line in filtered
    ]
    joined = "\n".join(filtered)

    byte_len = len(joined.encode("utf-8"))
    line_count = len(filtered)
    if status == "pass":
        digest_label = ""
        if role == "boot":
            digest_label = "boot"
        elif role == "srch" and (line_count > 12 or byte_len > 1800):
            digest_label = "search"
        elif role == "diag" and (line_count > 12 or byte_len > 1800):
            digest_label = "diagnostic"
        elif role == "gov" and (line_count > 24 or byte_len > 3000) and not (
            '"status": "blocked"' in joined.lower()
            or '"stop_reason":' in joined.lower()
            or '"direct_push_allowed": false' in joined.lower()
        ):
            digest_label = "governance"
        if digest_label:
            return ([
                f"[{digest_label} output summarized; "
                f"lines={line_count} bytes={byte_len} sha16={_sha16(joined)}; "
                "raw_sidecar=available]"
            ], True)
    if status == "fail":
        full_line_limit, full_byte_limit, head, tail = 80, 12000, 48, 24
    elif role in {"boot", "srch", "read", "diag"}:
        full_line_limit, full_byte_limit, head, tail = 32, 5000, 18, 10
    else:
        full_line_limit, full_byte_limit, head, tail = 80, 9000, 44, 18
    if line_count <= full_line_limit and byte_len <= full_byte_limit:
        return (filtered, truncated_line)
    omitted = max(0, line_count - head - tail)
    compacted = filtered[:head] + [f"[captured output omitted {omitted} lines; sha16={_sha16(joined)}]"] + filtered[-tail:]
    return (compacted, True)


def _capsule_output_is_nested_trace(output: str) -> bool:
    return bool(output and "TRACE CAPSULE v" in output and "\nSUMMARY\n" in output and "\nTIMELINE\n" in output)


def _capsule_command_return_text(output: str) -> tuple[list[str], list[str]]:
    redacted, hits = _redact_secrets((output or "").strip("\n"))
    if not redacted:
        return [], hits
    lines: list[str] = []
    codex_event_json_run: list[str] = []
    transport_re = re.compile(
        r"^(?:"
        r"Process exited with code -?\d+|"
        r"Process running with session ID \d+|"
        r"with session ID \d+|"
        r"with code -?\d+|"
        r"\d+(?:\.\d+)? seconds|"
        r"Chunk ID: .+|"
        r"Wall time: .+|"
        r"Original token count: .+"
        r")$"
    )

    def flush_codex_event_json_run() -> None:
        nonlocal codex_event_json_run
        if not codex_event_json_run:
            return
        if len(codex_event_json_run) == 1:
            line = codex_event_json_run[0]
            lines.append(f"[codex event JSON line omitted; chars={len(line)}; sha16={_sha16(line)}]")
        else:
            total_chars = sum(len(line) for line in codex_event_json_run)
            lines.append(
                "[codex event JSON lines omitted; "
                f"count={len(codex_event_json_run)} chars={total_chars} "
                f"first_sha16={_sha16(codex_event_json_run[0])} "
                f"last_sha16={_sha16(codex_event_json_run[-1])}]"
            )
        codex_event_json_run = []

    for line in redacted.splitlines():
        stripped = line.strip()
        if transport_re.match(stripped):
            continue
        if stripped.startswith('{"id":"agent-event-') or (
            '"source_runtime":"codex_app"' in stripped and '"payload":' in stripped
        ):
            codex_event_json_run.append(line)
            continue
        flush_codex_event_json_run()
        if "data:image/" in line and ";base64," in line:
            lines.append(f"[image data URI omitted; chars={len(line)}; sha16={_sha16(line)}]")
            continue
        if "[reasoning note omitted" in line:
            lines.append(f"[legacy reasoning omission marker output omitted; chars={len(line)}; sha16={_sha16(line)}]")
            continue
        if len(line) > 1400:
            lines.append(
                _capsule_clean_text(line[:1100].rstrip())
                + f" [line truncated {len(line) - 1100} chars; sha16={_sha16(line)}]"
            )
        else:
            lines.append(_capsule_clean_text(line.rstrip()))
    flush_codex_event_json_run()
    structural_re = re.compile(
        r"^(?:TRACE CAPSULE v\d+|SUMMARY|TIMELINE|OMISSIONS|K\d{3}\s+|"
        r"coverage:|status:|result:|changed:|final_validation:|checks:|terminal_checks:|"
        r"governance_receipts:|terminal_governance:|diagnostics:|visible_progress:|"
        r"thinking:|reasoning_digest:|episodes:|validation_progress:|commit:|open:)"
    )
    lines = [
        f"> {line}" if structural_re.match(line.strip()) else line
        for line in lines
    ]
    return lines, hits


def _capsule_redaction_hit_summary(hits: list[str]) -> str:
    if not hits:
        return "none"
    counts: dict[str, int] = {}
    for hit in hits:
        counts[hit] = counts.get(hit, 0) + 1
    return ",".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _capsule_command_return_reason(
    *,
    role: str,
    status: str,
    line_count: int,
    byte_count: int,
    redacted: bool,
    nested_trace: bool = False,
) -> str:
    if nested_trace:
        return "duplicate_generated_state"
    if redacted:
        return "secret_redaction"
    if status == "fail":
        return "failing_output" if (
            line_count <= TRACE_CAPSULE_COMMAND_RETURN_DECISIVE_LINES
            and byte_count <= TRACE_CAPSULE_COMMAND_RETURN_DECISIVE_BYTES
        ) else "large_failing_output"
    if role in {"test", "gov"}:
        return "validation_output" if (
            line_count <= TRACE_CAPSULE_COMMAND_RETURN_DECISIVE_LINES
            and byte_count <= TRACE_CAPSULE_COMMAND_RETURN_DECISIVE_BYTES
        ) else "large_validation_output"
    if line_count <= TRACE_CAPSULE_COMMAND_RETURN_INLINE_LINES and byte_count <= TRACE_CAPSULE_COMMAND_RETURN_INLINE_BYTES:
        return "small_output"
    if role in {"boot", "diag", "srch"}:
        return "size_budget"
    return "large_output"


def _capsule_command_return_disposition(reason: str) -> str:
    if reason == "secret_redaction":
        return "redacted"
    if reason in {"failing_output", "validation_output", "small_output"}:
        return "inline"
    return "sidecar"


def _capsule_output_payload_block(label: str, body_lines: list[str]) -> list[str]:
    lines = [f"{label}:"]
    if not body_lines:
        lines.append("|")
        return lines
    for line in body_lines:
        lines.append(f"| {line}" if line else "|")
    return lines


def _capsule_command_return_excerpt(lines: list[str]) -> list[str]:
    head = TRACE_CAPSULE_COMMAND_RETURN_EXCERPT_HEAD
    tail = TRACE_CAPSULE_COMMAND_RETURN_EXCERPT_TAIL
    if len(lines) <= head + tail + 1:
        return lines
    omitted = len(lines) - head - tail
    joined = "\n".join(lines)
    return [
        *lines[:head],
        f"[output sidecar excerpt omitted {omitted} lines; sha16={_sha16(joined)}]",
        *lines[-tail:],
    ]


def _capsule_command_return_sections(
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    *,
    source_sha16: str,
    raw_sidecar_available: bool = True,
) -> tuple[list[str], list[str], dict[str, int]]:
    rows: list[str] = ["COMMAND_RETURNS"]
    manifest: list[str] = ["SIDECAR_MANIFEST"]
    stats = {
        "commands": len(renderable),
        "outputs": 0,
        "inline": 0,
        "sidecar": 0,
        "redacted": 0,
        "no_output": 0,
        "lost": 0,
        "accounted": 0,
    }
    manifest.append(
        f"raw_sidecar_source: {'inline_trace_paste' if raw_sidecar_available else 'not_materialized'} "
        f"sha16={source_sha16}"
    )
    manifest.append("server_hidden_reasoning: not_included")

    for idx, wrapped in enumerate(renderable, start=1):
        ev, output_text, exit_code, is_error = wrapped
        command_id = f"C{idx:03d}"
        output = output_text or ""
        has_output = bool(output and not output.startswith("[no "))
        status = _capsule_status(exit_code, is_error)
        role = _capsule_role(ev, _capsule_clean_text(_capsule_command(ev)))
        exit_part = f" exit={exit_code}" if exit_code is not None else ""
        handle = (
            f"raw://trace/{source_sha16}/{command_id}.output"
            if raw_sidecar_available
            else f"raw-unavailable://trace/{source_sha16}/{command_id}.output"
        )
        if not has_output:
            stats["no_output"] += 1
            if ev.output_char_count:
                stats["lost"] += 1
            rows.append(
                f"O{idx:03d} {command_id} {role}{exit_part} no_output lines=0 bytes=0 sha16=none"
            )
            rows.extend(_capsule_command_display_lines(_capsule_command(ev)))
            rows.append("output: none captured")
            manifest.append(f"{command_id}.output no_output")
            continue

        stats["outputs"] += 1
        output_bytes = len(output.encode("utf-8"))
        output_lines = max(1, len(output.strip("\n").splitlines()))
        output_sha = _sha16(output)
        nested_trace = _capsule_output_is_nested_trace(output)
        if nested_trace:
            display_lines: list[str] = ["[nested trace capsule output omitted; raw_sidecar=available]"]
            redaction_hits: list[str] = []
        else:
            display_lines, redaction_hits = _capsule_command_return_text(output)
        reason = _capsule_command_return_reason(
            role=role,
            status=status,
            line_count=output_lines,
            byte_count=output_bytes,
            redacted=bool(redaction_hits),
            nested_trace=nested_trace,
        )
        disposition = _capsule_command_return_disposition(reason)
        stats[disposition] += 1
        stats["accounted"] += 1
        if disposition in {"sidecar", "redacted"} and not raw_sidecar_available:
            stats["lost"] += 1
        rows.append(
            f"O{idx:03d} {command_id} {role}{exit_part} {disposition} "
            f"lines={output_lines} bytes={output_bytes} sha16={output_sha} omission_reason={reason}"
        )
        rows.extend(_capsule_command_display_lines(_capsule_command(ev)))
        if disposition == "inline":
            rows.extend(_capsule_output_payload_block("output", display_lines))
        elif disposition == "redacted":
            rows.append(f"output_sidecar: {handle}")
            rows.append(f"redaction_hits: {_capsule_redaction_hit_summary(redaction_hits)}")
            rows.extend(_capsule_output_payload_block("redacted_output", _capsule_command_return_excerpt(display_lines)))
        else:
            rows.append(f"output_sidecar: {handle}")
            rows.extend(_capsule_output_payload_block("excerpt", _capsule_command_return_excerpt(display_lines)))
        manifest.append(
            f"{command_id}.output handle={handle} disposition={disposition} "
            f"lines={output_lines} bytes={output_bytes} sha16={output_sha}"
        )

    rows.insert(
        1,
        "command_return_summary: "
        f"commands={stats['commands']} outputs={stats['outputs']} inline={stats['inline']} "
        f"sidecar={stats['sidecar']} redacted={stats['redacted']} "
        f"no_output={stats['no_output']} lost={stats['lost']}"
    )
    rows.insert(
        2,
        "no_loss: "
        f"outputs_total={stats['outputs']} accounted={stats['accounted']} "
        f"lost_outputs={stats['lost']} status={'pass' if stats['lost'] == 0 else 'fail'}"
    )
    manifest.insert(
        1,
        "raw_sidecar_coverage: "
        f"{'complete' if stats['lost'] == 0 else 'partial'} "
        f"outputs_total={stats['outputs']} accounted={stats['accounted']} lost={stats['lost']}"
    )
    return rows, manifest, stats


def _capsule_public_trace_path(path: str) -> str:
    clean = (path or "").strip().strip("'\"")
    if not clean:
        return ""
    if clean.startswith("repo:/"):
        clean = clean[len("repo:/"):].lstrip("/")
    try:
        if Path(clean).is_absolute():
            clean_path = Path(clean)
            try:
                clean = str(clean_path.relative_to(REPO_ROOT))
            except ValueError:
                clean = str(clean_path)
    except Exception:
        pass
    return clean


def _capsule_source_path_allowed(path: str) -> bool:
    clean = _capsule_public_trace_path(path)
    if not clean or clean == "-":
        return False
    lower = clean.lower()
    normalized = lower.replace("\\", "/")
    if "/.codex/attachments/" in normalized:
        return True
    blocked_tokens = (
        "/.codex/",
        "/.claude/",
        "library/application support/",
        "state/prompt_shelf/usage/raw_events/",
        "state/operator_bridge/thread_exports/",
        "state/operator_bridge/prompt_shelf_artifacts/",
    )
    return not any(token in normalized for token in blocked_tokens)


def _parse_line_range_value(value: str | None) -> tuple[int | None, int | None]:
    text = (value or "").strip()
    if not text:
        return (None, None)
    match = re.match(r"^(?P<start>\d+)(?:\s*(?:-|:|,)\s*(?P<end>\d+))?$", text)
    if not match:
        raise ValueError(f"invalid line range {value!r}; use START-END")
    start = int(match.group("start"))
    end = int(match.group("end") or match.group("start"))
    if start < 1 or end < start:
        raise ValueError(f"invalid line range {value!r}; start must be >= 1 and end >= start")
    return (start, end)


def _arg_value(argv: list[str], *names: str) -> str:
    for index, token in enumerate(argv):
        for name in names:
            if token == name and index + 1 < len(argv):
                return argv[index + 1]
            prefix = f"{name}="
            if token.startswith(prefix):
                return token[len(prefix):]
    return ""


def _capsule_type_b_source_excerpt_ref(argv: list[str]) -> dict[str, Any] | None:
    if "--type-b-source-excerpt" not in argv:
        return None
    if not any(Path(token).name == "cli_prompt_trace.py" for token in argv):
        return None
    path = _arg_value(argv, "--source-path")
    if not path:
        return None
    public_path = _capsule_public_trace_path(path)
    if not _capsule_source_path_allowed(public_path):
        return None
    try:
        start, end = _parse_line_range_value(_arg_value(argv, "--line-range"))
    except ValueError:
        start, end = (None, None)
    return {
        "kind": "agent_requested_source_excerpt",
        "command": "type_b_source_excerpt",
        "path": public_path,
        "start_line": start,
        "end_line": end,
        "symbol": _arg_value(argv, "--symbol"),
        "full_file": "--full-file" in argv,
    }


def _type_b_source_public_path(path: Path) -> str:
    return _capsule_public_trace_path(str(path))


def _resolve_type_b_source_path(raw_path: str, cwd: Path) -> Path:
    if not raw_path.strip():
        raise SystemExit("--source-path is required with --type-b-source-excerpt")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = cwd / path
    try:
        return path.resolve()
    except OSError as exc:
        raise SystemExit(f"could not resolve source path: {raw_path}: {exc}") from exc


def _utf8_prefix(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text
    return data[:max_bytes].decode("utf-8", errors="ignore")


def _capsule_clip_numbered_lines_by_byte_budget(
    numbered: list[str],
    *,
    max_bytes: int,
    max_line_bytes: int = TRACE_CAPSULE_SOURCE_EXCERPT_LINE_BYTES,
    marker_label: str = "source_slice",
) -> tuple[list[str], dict[str, Any]]:
    source_bytes = len("\n".join(numbered).encode("utf-8"))
    max_bytes = max(0, int(max_bytes or 0))
    max_line_bytes = max(256, int(max_line_bytes or 0))
    if source_bytes <= max_bytes and all(len(line.encode("utf-8")) <= max_line_bytes for line in numbered):
        return numbered, {
            "byte_truncated": False,
            "source_byte_count": source_bytes,
            "emitted_byte_count": source_bytes,
            "omitted_byte_count": 0,
            "omitted_line_count": 0,
            "line_byte_truncated_count": 0,
            "byte_budget": max_bytes,
        }

    out: list[str] = []
    line_byte_truncated_count = 0
    stopped_at_index = len(numbered)
    for index, line in enumerate(numbered):
        used = len("\n".join(out).encode("utf-8"))
        separator_bytes = 1 if out else 0
        remaining = max_bytes - used - separator_bytes
        if remaining <= 0:
            stopped_at_index = index
            break
        line_bytes = len(line.encode("utf-8"))
        line_budget = min(max_line_bytes, remaining)
        if line_bytes <= line_budget:
            out.append(line)
            continue

        marker = f" [{marker_label} line byte-truncated; original_bytes={line_bytes}; sha16={_sha16(line)}]"
        prefix_budget = line_budget - len(marker.encode("utf-8"))
        if prefix_budget >= 80:
            out.append(_utf8_prefix(line, prefix_budget) + marker)
        else:
            compact_marker = (
                f"[{marker_label} byte budget reached before line {index + 1}; "
                f"original_line_bytes={line_bytes}; sha16={_sha16(line)}]"
            )
            out.append(_utf8_prefix(compact_marker, max(0, remaining)))
        line_byte_truncated_count += 1
        stopped_at_index = index + 1
        break

    emitted_bytes = len("\n".join(out).encode("utf-8"))
    omitted_line_count = max(0, len(numbered) - stopped_at_index) + line_byte_truncated_count
    return out, {
        "byte_truncated": True,
        "source_byte_count": source_bytes,
        "emitted_byte_count": emitted_bytes,
        "omitted_byte_count": max(0, source_bytes - emitted_bytes),
        "omitted_line_count": omitted_line_count,
        "line_byte_truncated_count": line_byte_truncated_count,
        "byte_budget": max_bytes,
    }


def _python_symbol_ranges(text: str, symbol: str) -> list[tuple[int, int, str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    rows: list[tuple[int, int, str]] = []

    def visit(node: ast.AST, prefix: tuple[str, ...] = ()) -> None:
        name = getattr(node, "name", None)
        next_prefix = prefix
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and name:
            qualname = ".".join((*prefix, str(name)))
            lineno = int(getattr(node, "lineno", 1) or 1)
            end = int(getattr(node, "end_lineno", lineno) or lineno)
            rows.append((lineno, max(lineno, end), qualname))
            next_prefix = (*prefix, str(name))
        for child in ast.iter_child_nodes(node):
            visit(child, next_prefix)

    visit(tree)
    exact = [row for row in rows if row[2] == symbol]
    if exact:
        return exact
    tail = symbol.split(".")[-1]
    return [row for row in rows if row[2].split(".")[-1] == tail]


def _generic_symbol_range(lines: list[str], symbol: str, limit: int) -> tuple[int, int] | None:
    tail = re.escape(symbol.split(".")[-1])
    patterns = [
        re.compile(rf"^\s*(?:export\s+)?(?:async\s+)?function\s+{tail}\b"),
        re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+{tail}\s*="),
        re.compile(rf"^\s*(?:export\s+)?class\s+{tail}\b"),
        re.compile(rf"^\s*(?:async\s+)?def\s+{tail}\b"),
        re.compile(rf"^\s*class\s+{tail}\b"),
    ]
    for index, line in enumerate(lines):
        if not any(pattern.search(line) for pattern in patterns):
            continue
        start = index + 1
        brace_depth = 0
        seen_brace = False
        for end_index in range(index, min(len(lines), index + limit)):
            row = lines[end_index]
            brace_depth += row.count("{") - row.count("}")
            seen_brace = seen_brace or "{" in row
            if seen_brace and brace_depth <= 0 and end_index > index:
                return (start, end_index + 1)
        return (start, min(len(lines), index + limit))
    return None


def _select_type_b_source_excerpt(
    *,
    cwd: Path,
    source_path: str,
    line_range: str | None,
    symbol: str | None,
    full_file: bool,
    max_lines: int,
) -> dict[str, Any]:
    resolved = _resolve_type_b_source_path(source_path, cwd)
    public_path = _type_b_source_public_path(resolved)
    if not _capsule_source_path_allowed(public_path):
        raise SystemExit(f"source path is not allowed for Type B bundle excerpts: {public_path}")
    try:
        if not resolved.is_file():
            raise SystemExit(f"source path is not a regular file: {public_path}")
    except OSError as exc:
        raise SystemExit(f"could not stat source path: {public_path}: {exc}") from exc
    try:
        raw_bytes = resolved.read_bytes()
    except OSError as exc:
        raise SystemExit(f"could not read source path: {public_path}: {exc}") from exc
    text = raw_bytes.decode("utf-8", errors="replace")
    if "\x00" in text:
        raise SystemExit(f"source path appears binary and cannot be excerpted: {public_path}")

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"source path is empty: {public_path}")
    start: int
    end: int
    selection = "full_file" if full_file else "auto_full_file"
    if line_range:
        try:
            parsed_start, parsed_end = _parse_line_range_value(line_range)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        start = parsed_start or 1
        end = parsed_end or start
        selection = "line_range"
    elif symbol:
        ranges = _python_symbol_ranges(text, symbol) if resolved.suffix == ".py" else []
        if ranges:
            start, end, _qualname = ranges[0]
            selection = "python_symbol"
        else:
            generic = _generic_symbol_range(lines, symbol, max_lines)
            if not generic:
                raise SystemExit(f"symbol not found in {public_path}: {symbol}")
            start, end = generic
            selection = "symbol"
    else:
        start, end = (1, len(lines))

    start = max(1, min(start, len(lines)))
    end = max(start, min(end, len(lines)))
    capped_end = min(end, start + max_lines - 1)
    selected_lines = lines[start - 1:capped_end]
    redacted, redaction_hits = _redact_secrets("\n".join(selected_lines))
    redacted_lines = redacted.split("\n")
    numbered = [f"{line_no}:{line}" for line_no, line in zip(range(start, start + len(redacted_lines)), redacted_lines)]
    numbered, byte_clip = _capsule_clip_numbered_lines_by_byte_budget(
        numbered,
        max_bytes=TRACE_CAPSULE_SOURCE_EXCERPT_BYTES,
        max_line_bytes=TRACE_CAPSULE_SOURCE_EXCERPT_LINE_BYTES,
        marker_label="type_b_source_excerpt",
    )
    return {
        "schema_version": TYPE_B_SOURCE_EXCERPT_SCHEMA_VERSION,
        "path": public_path,
        "selection": selection,
        "symbol": symbol or "",
        "requested_range": {"start": start, "end": end},
        "emitted_range": {"start": start, "end": start + max(0, len(numbered) - 1)},
        "line_count": len(numbered),
        "omitted_line_count": max(0, end - capped_end) + int(byte_clip.get("omitted_line_count") or 0),
        "source_byte_count": int(byte_clip.get("source_byte_count") or 0),
        "emitted_byte_count": int(byte_clip.get("emitted_byte_count") or 0),
        "omitted_byte_count": int(byte_clip.get("omitted_byte_count") or 0),
        "byte_budget": int(byte_clip.get("byte_budget") or TRACE_CAPSULE_SOURCE_EXCERPT_BYTES),
        "byte_truncated": bool(byte_clip.get("byte_truncated")),
        "line_byte_truncated_count": int(byte_clip.get("line_byte_truncated_count") or 0),
        "redaction_hits": sorted(set(redaction_hits)),
        "lines": numbered,
    }


def render_type_b_source_excerpt(
    *,
    cwd: Path,
    source_path: str,
    line_range: str | None = None,
    symbol: str | None = None,
    full_file: bool = False,
    max_lines: int = TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
) -> tuple[str, dict[str, Any]]:
    max_lines = max(1, min(int(max_lines or TRACE_CAPSULE_SOURCE_EXCERPT_LINES), 240))
    row = _select_type_b_source_excerpt(
        cwd=cwd,
        source_path=source_path,
        line_range=line_range,
        symbol=symbol,
        full_file=full_file,
        max_lines=max_lines,
    )
    return "\n".join(row["lines"]), row


def _type_b_source_excerpt_carrier_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": TYPE_B_SOURCE_EXCERPT_CARRIER_SCHEMA_VERSION,
        "excerpt_schema_version": row.get("schema_version") or TYPE_B_SOURCE_EXCERPT_SCHEMA_VERSION,
        "path": str(row.get("path") or ""),
        "selection": str(row.get("selection") or ""),
        "symbol": str(row.get("symbol") or ""),
        "requested_range": row.get("requested_range") or {},
        "emitted_range": row.get("emitted_range") or {},
        "line_count": int(row.get("line_count") or 0),
        "omitted_line_count": int(row.get("omitted_line_count") or 0),
        "source_byte_count": int(row.get("source_byte_count") or 0),
        "emitted_byte_count": int(row.get("emitted_byte_count") or 0),
        "omitted_byte_count": int(row.get("omitted_byte_count") or 0),
        "byte_budget": int(row.get("byte_budget") or TRACE_CAPSULE_SOURCE_EXCERPT_BYTES),
        "byte_truncated": bool(row.get("byte_truncated")),
        "redaction_hits": list(row.get("redaction_hits") or []),
        "lines": list(row.get("lines") or []),
    }


def _write_type_b_source_excerpt_carrier(row: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    payload = _type_b_source_excerpt_carrier_payload(row)
    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    digest = _sha16(body)
    public_path = str(payload.get("path") or "unknown")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", public_path).strip("_") or "source"
    safe_name = safe_name[-120:]
    TRACE_STRUCTURER_TYPE_B_SOURCE_CARRIERS.mkdir(parents=True, exist_ok=True)
    out_path = TRACE_STRUCTURER_TYPE_B_SOURCE_CARRIERS / f"{digest}_{safe_name}.json"
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(body + "\n", encoding="utf-8")
    tmp.replace(out_path)
    return out_path, payload


def render_type_b_source_excerpt_trace_carrier_receipt(
    row: dict[str, Any],
    sidecar_path: Path,
) -> str:
    emitted = row.get("emitted_range") or {}
    start = emitted.get("start") or ""
    end = emitted.get("end") or ""
    selector = str(row.get("selection") or "unknown")
    symbol = str(row.get("symbol") or "")
    line_count = int(row.get("line_count") or 0)
    omitted = int(row.get("omitted_line_count") or 0)
    payload = _type_b_source_excerpt_carrier_payload(row)
    sha16 = _sha16(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    parts = [
        "type_b_source_excerpt_carrier:",
        f"schema={TYPE_B_SOURCE_EXCERPT_CARRIER_SCHEMA_VERSION}",
        f"path={row.get('path') or 'unknown'}",
        f"range={start}-{end}",
        f"selector={selector}",
        f"lines={line_count}",
        f"omitted={omitted}",
        f"bytes={int(row.get('emitted_byte_count') or 0)}",
        f"omitted_bytes={int(row.get('omitted_byte_count') or 0)}",
        f"sidecar={shlex.quote(str(sidecar_path))}",
        f"sha16={sha16}",
    ]
    if symbol:
        parts.insert(5, f"symbol={symbol}")
    return " ".join(parts)


def _type_b_source_excerpt_trace_carrier_receipt(
    *,
    cwd: Path,
    source_path: str,
    line_range: str | None = None,
    symbol: str | None = None,
    full_file: bool = False,
    max_lines: int = TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
) -> tuple[str, dict[str, Any], Path]:
    _text, row = render_type_b_source_excerpt(
        cwd=cwd,
        source_path=source_path,
        line_range=line_range,
        symbol=symbol,
        full_file=full_file,
        max_lines=max_lines,
    )
    sidecar_path, _payload = _write_type_b_source_excerpt_carrier(row)
    return render_type_b_source_excerpt_trace_carrier_receipt(row, sidecar_path), row, sidecar_path


def _capsule_prompt_file_ref_paths(prompt_text: str) -> list[str]:
    paths: list[str] = []

    def add_path(raw: str) -> None:
        clean = (raw or "").strip().strip("`'\"<>.,;")
        if not clean:
            return
        if clean.startswith("~"):
            clean = str(Path(clean).expanduser())
        if clean not in paths:
            paths.append(clean)

    for raw_line in (prompt_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^##\s+[^:]{1,120}:\s+(?P<path>/\S+)$", line)
        if match:
            add_path(match.group("path"))
            continue
        for match in re.finditer(
            r"(?P<path>/(?:Users|tmp|private/tmp)/[^\s`\"'<>)]{1,500})",
            line,
        ):
            candidate = match.group("path")
            if any(candidate.endswith(suffix) for suffix in (
                ".txt", ".md", ".json", ".jsonl", ".log", ".py", ".swift", ".mjs", ".html"
            )):
                add_path(candidate)
    return paths


def _capsule_prompt_file_excerpt(path: str) -> tuple[list[str], str, int] | None:
    try:
        resolved = Path(path).expanduser()
    except Exception:
        return None
    try:
        if not resolved.is_file():
            return None
    except OSError:
        return None
    public_path = _capsule_public_trace_path(str(resolved))
    if not _capsule_source_path_allowed(public_path):
        return None
    try:
        raw_bytes = resolved.read_bytes()[:TRACE_CAPSULE_PROMPT_FILE_BYTES]
    except OSError:
        return None
    if not raw_bytes:
        return None
    text = raw_bytes.decode("utf-8", errors="replace")
    if "\x00" in text:
        return None
    redacted, _hits = _redact_secrets(text)
    display_lines = redacted.splitlines()
    ref = {"start_line": 1}
    numbered = _capsule_numbered_source_lines(display_lines, ref)
    if not numbered:
        return None
    return numbered, public_path, len(raw_bytes)


def _capsule_sed_script_range(script: str) -> tuple[int | None, int | None]:
    compact = (script or "").strip().strip("'\"").replace(" ", "")
    match = re.match(r"^(?P<start>\d+)(?:,(?P<end>\d+))?p$", compact)
    if not match:
        return (None, None)
    start = int(match.group("start"))
    end = int(match.group("end") or match.group("start"))
    return (start, end)


def _capsule_source_read_ref_from_argv(argv: list[str], line: str) -> dict[str, Any] | None:
    if not argv:
        return None
    type_b_ref = _capsule_type_b_source_excerpt_ref(argv)
    if type_b_ref:
        return type_b_ref
    exe = Path(argv[0]).name
    if exe == "sed":
        script = ""
        script_index = -1
        idx = 1
        while idx < len(argv):
            token = argv[idx]
            if token == "-n" and idx + 1 < len(argv):
                script = argv[idx + 1]
                script_index = idx + 1
                idx += 2
                continue
            if token.startswith("-n") and len(token) > 2:
                script = token[2:]
                script_index = idx
                idx += 1
                continue
            if token == "-e" and idx + 1 < len(argv):
                script = argv[idx + 1]
                script_index = idx + 1
                idx += 2
                continue
            if not token.startswith("-") and not script:
                script = token
                script_index = idx
            idx += 1
        start, end = _capsule_sed_script_range(script)
        path = ""
        if script_index >= 0:
            for token in argv[script_index + 1:]:
                if not token.startswith("-"):
                    path = token
                    break
        if path and _capsule_source_path_allowed(path):
            return {
                "kind": "read",
                "command": exe,
                "path": _capsule_public_trace_path(path),
                "start_line": start,
                "end_line": end,
            }
    if exe == "nl":
        path = ""
        for token in argv[1:]:
            if token.startswith("-"):
                continue
            path = token
        if path and _capsule_source_path_allowed(path):
            pipe_match = re.search(r"\|\s*sed\s+-n\s+['\"]?(?P<script>\d+(?:,\d+)?p)['\"]?", line)
            start, end = _capsule_sed_script_range(pipe_match.group("script") if pipe_match else "")
            return {
                "kind": "read",
                "command": exe,
                "path": _capsule_public_trace_path(path),
                "start_line": start,
                "end_line": end,
            }
    if exe == "cat":
        path = next((token for token in argv[1:] if not token.startswith("-")), "")
        if path and _capsule_source_path_allowed(path):
            return {
                "kind": "read",
                "command": exe,
                "path": _capsule_public_trace_path(path),
                "start_line": None,
                "end_line": None,
            }
    if exe in {"head", "tail"}:
        count: int | None = None
        path = ""
        idx = 1
        while idx < len(argv):
            token = argv[idx]
            if token in {"-n", "--lines"} and idx + 1 < len(argv):
                try:
                    count = int(argv[idx + 1].lstrip("+"))
                except ValueError:
                    count = None
                idx += 2
                continue
            if token.startswith("-n") and len(token) > 2:
                try:
                    count = int(token[2:].lstrip("+"))
                except ValueError:
                    count = None
                idx += 1
                continue
            if not token.startswith("-"):
                path = token
            idx += 1
        if path and _capsule_source_path_allowed(path):
            return {
                "kind": "read",
                "command": exe,
                "path": _capsule_public_trace_path(path),
                "start_line": 1 if exe == "head" else None,
                "end_line": count if exe == "head" and count is not None else None,
            }
    if exe in {"rg", "grep"} and any(arg == "-n" or arg.startswith("-n") or "n" in arg[1:] for arg in argv[1:] if arg.startswith("-")):
        def search_path_candidate(token: str) -> bool:
            public = _capsule_public_trace_path(token)
            if not _capsule_source_path_allowed(public):
                return False
            if re.search(r"[\^\$\|\(\)\[\]\{\}]", public):
                return False
            return "/" in public or "\\" in public or bool(Path(public).suffix)

        candidate_paths = [token for token in argv[2:] if not token.startswith("-")]
        path = next((token for token in reversed(candidate_paths) if search_path_candidate(token)), "")
        return {
            "kind": "search",
            "command": exe,
            "path": _capsule_public_trace_path(path) if path else "search_results",
            "start_line": None,
            "end_line": None,
        }
    return None


def _capsule_source_read_ref(command: str) -> dict[str, Any] | None:
    clean = _capsule_clean_text(command or "")
    base_name = ""
    if clean.startswith("Read "):
        path = clean.split(" ", 1)[1].strip()
        if _capsule_source_path_allowed(path):
            return {
                "kind": "read",
                "command": "Read",
                "path": _capsule_public_trace_path(path),
                "start_line": None,
                "end_line": None,
            }
    for line in _capsule_command_surface_lines(clean):
        argv = _capsule_argv_from_shell_line(line)
        if argv:
            base_name = Path(argv[0]).name
        ref = _capsule_source_read_ref_from_argv(argv, line)
        if ref:
            return ref
    if base_name:
        return None
    return None


def _capsule_numbered_source_lines(lines: list[str], ref: dict[str, Any]) -> list[str]:
    numbered: list[str] = []
    start_line = ref.get("start_line")
    emitted = 0
    byte_budget = 0
    for raw_line in lines:
        if emitted >= TRACE_CAPSULE_SOURCE_EXCERPT_LINES:
            break
        line = raw_line.rstrip("\n")
        source_line: int | None = None
        content = line
        match = re.match(r"^\s*(?P<line>\d+)\s+(?P<body>.*)$", line)
        if match:
            source_line = int(match.group("line"))
            content = match.group("body")
        else:
            search_match = re.match(r"^(?:(?P<path>[^:\s][^:]*):)?(?P<line>\d+):(?P<body>.*)$", line)
            if search_match:
                source_line = int(search_match.group("line"))
                content = search_match.group("body")
            elif isinstance(start_line, int):
                source_line = start_line + emitted
        label = f"L{source_line}" if source_line is not None else "L?"
        rendered = f"| {label} {content}"
        rendered_bytes = len(rendered.encode("utf-8"))
        if byte_budget + rendered_bytes > TRACE_CAPSULE_SOURCE_EXCERPT_BYTES:
            numbered.append(f"| [source excerpt byte budget reached; sha16={_sha16(chr(10).join(lines))}]")
            break
        numbered.append(rendered)
        byte_budget += rendered_bytes
        emitted += 1
    return numbered


def _capsule_numbered_line_numbers(numbered: list[str]) -> list[int]:
    values: list[int] = []
    for line in numbered:
        match = re.match(r"^\|\s+L(?P<line>\d+)\b", line)
        if match:
            values.append(int(match.group("line")))
    return values


def _capsule_type_b_source_excerpt_from_carrier(
    output_text: str,
    ref: dict[str, Any],
) -> tuple[list[str], str, str | None]:
    for raw_line in (output_text or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("type_b_source_excerpt_carrier:"):
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            return [], "", "requested_excerpt_sidecar_receipt_invalid"
        fields: dict[str, str] = {}
        for token in tokens[1:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            fields[key] = value
        sidecar_raw = fields.get("sidecar") or ""
        if not sidecar_raw:
            return [], "", "requested_excerpt_sidecar_receipt_missing_path"
        sidecar_path = Path(sidecar_raw).expanduser()
        try:
            if not sidecar_path.is_file():
                return [], "", "requested_excerpt_sidecar_missing"
            payload_text = sidecar_path.read_text(encoding="utf-8")
            payload = json.loads(payload_text)
        except (OSError, json.JSONDecodeError):
            return [], "", "requested_excerpt_sidecar_unreadable"
        if not isinstance(payload, dict):
            return [], "", "requested_excerpt_sidecar_invalid"
        if payload.get("schema_version") != TYPE_B_SOURCE_EXCERPT_CARRIER_SCHEMA_VERSION:
            return [], "", "requested_excerpt_sidecar_schema_mismatch"
        receipt_sha = fields.get("sha16") or ""
        payload_sha = _sha16(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        if receipt_sha and receipt_sha != payload_sha:
            return [], "", "requested_excerpt_sidecar_sha_mismatch"
        payload_path = _capsule_public_trace_path(str(payload.get("path") or ""))
        ref_path = _capsule_public_trace_path(str(ref.get("path") or ""))
        if payload_path != ref_path:
            return [], "", "requested_excerpt_sidecar_path_mismatch"
        raw_lines = payload.get("lines") or []
        if not isinstance(raw_lines, list) or not all(isinstance(item, str) for item in raw_lines):
            return [], "", "requested_excerpt_sidecar_lines_invalid"
        numbered = _capsule_numbered_source_lines(list(raw_lines), ref)
        if not numbered:
            return [], "", "requested_excerpt_sidecar_no_numbered_lines"
        carrier_output = f"{payload_path}\ncarrier_sidecar={sidecar_path}\n" + "\n".join(raw_lines)
        return numbered, carrier_output, None
    return [], "", "requested_excerpt_sidecar_receipt_absent"


def _capsule_source_ref_key(ref: dict[str, Any]) -> tuple[str, str, int | None, int | None, str]:
    return (
        str(ref.get("path") or ""),
        str(ref.get("symbol") or ref.get("command") or ""),
        ref.get("start_line") if isinstance(ref.get("start_line"), int) else None,
        ref.get("end_line") if isinstance(ref.get("end_line"), int) else None,
        "full_file" if ref.get("full_file") else "",
    )


def _capsule_type_b_source_excerpt_affordance_applies_to_path(path: str) -> bool:
    clean = _capsule_public_trace_path(path)
    return any(
        clean == prefix.rstrip("/") or clean.startswith(prefix)
        for prefix in TRACE_CAPSULE_TYPE_B_SOURCE_AFFORDANCE_PATH_PREFIXES
    )


def _capsule_type_b_source_excerpt_affordance(
    changed_paths: list[str],
    source_excerpt_stats: dict[str, Any],
) -> dict[str, Any]:
    trigger_paths = [
        _capsule_public_trace_path(path)
        for path in changed_paths
        if _capsule_type_b_source_excerpt_affordance_applies_to_path(path)
    ]
    agent_requested_seen = int(source_excerpt_stats.get("agent_requested_seen_refs") or 0)
    agent_requested_refs = int(source_excerpt_stats.get("agent_requested_refs") or 0)
    agent_requested_omitted = int(source_excerpt_stats.get("agent_requested_omitted_refs") or 0)
    if not trigger_paths:
        status = "not_relevant"
        affordance_id = ""
        suggested = False
    elif agent_requested_seen > 0:
        status = "used"
        affordance_id = ""
        suggested = False
    else:
        status = "available"
        affordance_id = TRACE_CAPSULE_TYPE_B_SOURCE_AFFORDANCE_ID
        suggested = True
    return {
        "schema_version": "type_b_source_excerpt_affordance_v1",
        "status": status,
        "suggested": suggested,
        "mandatory": False,
        "copy_readiness_effect": "none",
        "affordance_id": affordance_id,
        "agent_requested_seen_refs": agent_requested_seen,
        "agent_requested_refs": agent_requested_refs,
        "agent_requested_omitted_refs": agent_requested_omitted,
        "trigger_paths": trigger_paths,
        "trigger_path_count": len(trigger_paths),
        "policy": (
            "optional_until_source_context_demand"
        ),
    }


def _capsule_source_context_language_id(path: str) -> str:
    suffix = Path(str(path or "")).suffix.lower()
    return {
        ".py": "python",
        ".mjs": "javascript",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".swift": "swift",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
    }.get(suffix, "text")


def _capsule_source_context_anchor_for_path(path: str) -> str:
    name = Path(str(path or "")).name
    if name == "cli_prompt_trace.py":
        return "symbol:_capsule_source_context_abi"
    if name == "test_cli_prompt_trace_capsule.py":
        return "symbol:test_trace_capsule_source_context_abi"
    if name == "parser.mjs":
        return "symbol:buildTraceCapsuleSourceContextReceipts"
    if name == "parser.test.mjs":
        return "symbol:projects_trace_capsule_source_context_receipts"
    if name == "trace_capsule_unit_test.py":
        return "symbol:trace_capsule_section_order"
    if name.endswith((".md", ".json")):
        return "document:owned_projection"
    return "file:changed_surface"


def _capsule_final_delta_hunk_starts(final_delta: dict[str, Any]) -> dict[str, list[int]]:
    """Map changed paths to new-file hunk starts from the attached final delta."""
    if not final_delta.get("attached"):
        return {}
    out: dict[str, list[int]] = {}
    current_path = ""
    for raw_line in final_delta.get("lines") or []:
        line = str(raw_line or "")
        if line.startswith("+++ "):
            marker_path = line[4:].strip()
            if marker_path.startswith("b/"):
                marker_path = marker_path[2:]
            current_path = _capsule_public_trace_path(marker_path)
            continue
        if not current_path:
            continue
        match = re.match(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?", line)
        if not match:
            continue
        out.setdefault(current_path, []).append(int(match.group(1)))
    return out


def _capsule_hunk_context_line_range(
    *,
    cwd: Path,
    path: str,
    final_delta: dict[str, Any],
    max_lines: int,
) -> tuple[int, int, str] | None:
    """Choose an exact source range anchored to the first changed hunk."""
    public_path = _capsule_public_trace_path(path)
    hunk_starts = _capsule_final_delta_hunk_starts(final_delta).get(public_path) or []
    if not hunk_starts:
        return None
    try:
        resolved = _resolve_type_b_source_path(public_path, cwd)
        raw_text = resolved.read_text(encoding="utf-8", errors="replace")
    except (OSError, SystemExit):
        return None
    lines = raw_text.splitlines()
    if not lines:
        return None
    hunk_start = max(1, min(hunk_starts[0], len(lines)))
    scan_start = max(1, hunk_start - 120)
    context_start = max(1, hunk_start - 20)
    language = _capsule_source_context_language_id(public_path)
    anchor_label = "hunk_context"
    if language in {"javascript", "typescript"}:
        test_pattern = re.compile(r"^\s*(?:test|it|describe)\s*\(\s*([`'\"])(.+?)\1")
        decl_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function|const|let|var|class)\s+([A-Za-z_$][\w$]*)\b")
        for index in range(hunk_start - 1, scan_start - 2, -1):
            row = lines[index].rstrip()
            match = test_pattern.search(row)
            if match:
                context_start = index + 1
                anchor_label = "nearest_js_test"
                break
            match = decl_pattern.search(row)
            if match and anchor_label == "hunk_context":
                context_start = index + 1
                anchor_label = "nearest_js_declaration"
    elif language == "python":
        def_pattern = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
        class_pattern = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
        for index in range(hunk_start - 1, scan_start - 2, -1):
            row = lines[index].rstrip()
            match = def_pattern.search(row) or class_pattern.search(row)
            if match:
                context_start = index + 1
                anchor_label = "nearest_python_symbol"
                break
    end = min(len(lines), context_start + max(1, max_lines) - 1)
    return (context_start, end, anchor_label)


def _capsule_source_context_budget_class(path: str, anchor: str) -> str:
    name = Path(str(path or "")).name.lower()
    if "test" in name:
        return "contract_test"
    if anchor.startswith("symbol:"):
        return "symbol_body"
    if name.endswith((".md", ".json")):
        return "standard_owned_projection"
    return "path_line_shard"


def _capsule_source_context_abi() -> dict[str, Any]:
    """Registry anchor for the Trace Capsule source-context carrier contract."""
    return {
        "schema_version": "trace_capsule_source_context_abi_v1",
        "demand": "_capsule_source_context_demand",
        "requests": "_capsule_source_slice_requests",
        "decision_bundle": "_capsule_type_b_decision_bundle",
        "manifest": "_capsule_source_slice_manifest",
        "deficit": "_capsule_source_context_deficit",
        "readiness": "_capsule_source_context_readiness",
        "quality_gate": "_capsule_source_slice_quality_satisfies_request",
        "sections": (
            "TYPE_B_DECISION_BUNDLE",
            "SOURCE_CONTEXT_DEMAND",
            "SOURCE_SLICE_REQUESTS",
            "SOURCE_SLICE_MANIFEST",
            "SOURCE_CONTEXT_DEFICIT",
            "SOURCE_CONTEXT_READINESS",
            "TYPE_B_SOURCE_CLOSEOUT_LINT",
        ),
    }


TRACE_CAPSULE_SOURCE_SLICE_QUALITY_LADDER = (
    "exact_symbol",
    "exact_line_range",
    "document_full_untruncated",
    "document_prefix_truncated",
    "symbol_miss_untruncated",
    "symbol_miss_truncated",
    "delta_only",
)


def _capsule_source_slice_quality(selector: str, *, truncated: bool, anchor: str = "") -> str:
    selector_text = str(selector or "").strip()
    if selector_text.startswith("symbol_miss_fallback"):
        return "symbol_miss_truncated" if truncated else "symbol_miss_untruncated"
    if selector_text in {"python_symbol", "symbol"} or anchor.startswith("symbol:"):
        return "exact_symbol"
    if selector_text in {"line_range", "path_line_shard", "hunk_context_line_range"}:
        return "exact_line_range"
    if selector_text in {"full_file", "document", "owned_projection", "document:owned_projection"}:
        return "document_full_untruncated" if not truncated else "document_prefix_truncated"
    if selector_text in {"auto_full_file", "prompt_file_ref", "trace_read_output"}:
        return "document_full_untruncated" if not truncated else "document_prefix_truncated"
    if selector_text in {"final_delta", "diff_hunk", "fallback_delta_only"}:
        return "delta_only"
    return "document_full_untruncated" if not truncated else "document_prefix_truncated"


def _capsule_source_slice_quality_satisfies_request(
    request: dict[str, Any],
    quality: str,
) -> tuple[bool, str]:
    normalized_quality = str(quality or "").strip()
    if not normalized_quality or normalized_quality == "none":
        return False, "source_slice_missing"
    priority = str(request.get("priority") or "")
    budget_class = str(request.get("budget_class") or "")
    if priority == "critical" and budget_class in {"symbol_body", "contract_test"}:
        if normalized_quality not in {"exact_symbol", "exact_line_range", "document_full_untruncated"}:
            return False, "critical_symbol_or_contract_test_requires_exact_symbol_line_or_untruncated_body"
    return True, ""


def _capsule_source_slice_missing_quality(
    request: dict[str, Any],
) -> tuple[str, bool, str]:
    quality = "delta_only" if str(request.get("carrier_kind") or "") == "fallback_delta_only" else "none"
    satisfies, warning = _capsule_source_slice_quality_satisfies_request(request, quality)
    return quality, satisfies, warning


def _capsule_final_delta_satisfies_changed_contract(
    *,
    source_context_demand: dict[str, Any],
    final_delta: dict[str, Any],
    path: str,
    budget_class: str,
) -> bool:
    """Return true only when exact final delta is enough for a bounded claim."""
    if str(source_context_demand.get("state") or "") != "required_by_claim":
        return False
    if str(source_context_demand.get("demand_scope") or "") != "changed_symbols_and_contract_tests":
        return False
    if not final_delta.get("attached") or int(final_delta.get("omitted_lines") or 0) > 0:
        return False
    final_delta_paths = set(
        _capsule_source_context_public_paths([str(item) for item in final_delta.get("paths") or []])
    )
    if _capsule_public_trace_path(path) not in final_delta_paths:
        return False
    return budget_class in {"contract_test", "symbol_body", "path_line_shard"}


def _capsule_source_context_public_paths(paths: list[str]) -> list[str]:
    out: list[str] = []
    for raw_path in paths:
        path = _capsule_public_trace_path(str(raw_path or ""))
        if not path or not _capsule_source_path_allowed(path):
            continue
        if path not in out:
            out.append(path)
    return out


def _capsule_source_context_trigger_paths(
    *,
    changed_paths: list[str],
    final_delta: dict[str, Any],
    type_b_source_excerpt_affordance: dict[str, Any],
) -> list[str]:
    paths: list[str] = []
    paths.extend(type_b_source_excerpt_affordance.get("trigger_paths") or [])
    paths.extend(changed_paths)
    if final_delta.get("attached"):
        paths.extend(str(path) for path in final_delta.get("paths") or [])
    return _capsule_source_context_public_paths(paths)


def _capsule_source_context_demand(
    *,
    prompt_text: str,
    final_assistant_text: str,
    changed_paths: list[str],
    final_delta: dict[str, Any],
    type_b_source_excerpt_affordance: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
) -> dict[str, Any]:
    trigger_paths = _capsule_source_context_trigger_paths(
        changed_paths=changed_paths,
        final_delta=final_delta,
        type_b_source_excerpt_affordance=type_b_source_excerpt_affordance,
    )
    combined_text = "\n".join([prompt_text or "", final_assistant_text or ""])
    type_b_marker = bool(re.search(
        r"\b(type\s*b|handoff|continue|latest response bundle|trace capsule|source context)\b",
        combined_text,
        re.I,
    ))
    exact_source_marker = bool(re.search(
        r"\b(exact|source|code|function|symbol|implementation|current function|current code|line(?:s)?|path(?:s)?)\b",
        combined_text,
        re.I,
    ))
    implementation_claims_present = bool(
        changed_paths
        or final_delta.get("attached")
        or re.search(r"\b(fixed|implemented|patched|changed|updated|committed|landed)\b", final_assistant_text or "", re.I)
    )
    reasons: list[str] = []
    if type_b_marker and exact_source_marker:
        reasons.append("operator_requested_exact_code")
    if trigger_paths and type_b_marker:
        reasons.append("private_repo_inaccessible_to_type_b")
    if trigger_paths and type_b_source_excerpt_affordance.get("status") == "available":
        reasons.append("trace_affordance_underuse")
    if implementation_claims_present:
        reasons.append("implementation_claims_present")
    if int(source_excerpt_stats.get("agent_requested_seen_refs") or 0):
        reasons.append("explicit_source_request_seen")

    if not trigger_paths and not implementation_claims_present:
        state = "none"
        scope = "none"
    elif type_b_marker and exact_source_marker:
        state = "required_by_type_b_decision"
        scope = "changed_symbols_and_contract_tests"
    elif implementation_claims_present and trigger_paths:
        state = "required_by_claim"
        scope = "changed_symbols_and_contract_tests"
    elif trigger_paths:
        state = "recommended"
        scope = "trigger_paths"
    else:
        state = "optional"
        scope = "claim_mentions_without_trigger_paths"

    return {
        "schema_version": "agent_trace_source_context_demand_v1",
        "state": state,
        "satisfaction": "pending_slice_requests" if state not in {"none", "optional"} else state,
        "consumer": "type_b_continue",
        "reasons": reasons,
        "trigger_paths": trigger_paths,
        "trigger_path_count": len(trigger_paths),
        "demand_scope": scope,
        "readiness_effect": "amber_if_unsatisfied" if state.startswith("required") else "none",
        "explicit_requests": int(source_excerpt_stats.get("agent_requested_seen_refs") or 0),
    }


def _capsule_source_slice_requests(
    *,
    source_context_demand: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
    final_delta: dict[str, Any],
) -> dict[str, Any]:
    demand_state = str(source_context_demand.get("state") or "none")
    trigger_paths = _capsule_source_context_public_paths(
        [str(path) for path in source_context_demand.get("trigger_paths") or []]
    )
    if demand_state in {"none", "optional"}:
        trigger_paths = []
    elif demand_state == "required_by_type_b_decision" and not trigger_paths:
        trigger_paths = ["tools/agent_trace_structurer/parser.test.mjs"]

    source_rows_by_path: dict[str, list[dict[str, Any]]] = {}
    for row in source_excerpt_stats.get("rows") or []:
        if not isinstance(row, dict):
            continue
        path = _capsule_public_trace_path(str(row.get("path") or ""))
        if path:
            source_rows_by_path.setdefault(path, []).append(row)

    final_delta_paths = (
        set(_capsule_source_context_public_paths([str(path) for path in final_delta.get("paths") or []]))
        if final_delta.get("attached")
        else set()
    )
    rows: list[dict[str, Any]] = []
    required = demand_state.startswith("required")
    for index, path in enumerate(trigger_paths[:TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT], start=1):
        matching_source_rows = source_rows_by_path.get(path) or []
        anchor = _capsule_source_context_anchor_for_path(path)
        budget_class = _capsule_source_context_budget_class(path, anchor)
        status = "deficit"
        carrier = ""
        carrier_kind = ""
        if matching_source_rows:
            first = matching_source_rows[0]
            status = "emitted"
            carrier = str(first.get("row_id") or "")
            carrier_kind = str(first.get("kind") or "source_excerpt")
        elif _capsule_final_delta_satisfies_changed_contract(
            source_context_demand=source_context_demand,
            final_delta=final_delta,
            path=path,
            budget_class=budget_class,
        ):
            status = "delta_satisfied_for_changed_contract"
            carrier = "FINAL_DELTA"
            carrier_kind = "final_delta_changed_contract"
        elif path in final_delta_paths and not required:
            status = "satisfied_by_final_delta"
            carrier = "FINAL_DELTA"
            carrier_kind = "diff_hunk"
        elif path in final_delta_paths:
            carrier = "FINAL_DELTA"
            carrier_kind = "fallback_delta_only"
        row = {
            "request_id": f"SSR{index:03d}",
            "path": path,
            "anchor": anchor,
            "why": (
                "type_b_decision_needs_exact_current_source"
                if demand_state == "required_by_type_b_decision"
                else (
                    "source_dependent_claim_needs_current_source"
                    if demand_state == "required_by_claim"
                    else "recommended_source_context_for_handoff"
                )
            ),
            "priority": "critical" if required else "high",
            "budget_class": budget_class,
            "status": status,
            "carrier": carrier,
            "carrier_kind": carrier_kind,
        }
        if status == "deficit":
            quality, satisfies, warning = _capsule_source_slice_missing_quality(row)
            row["slice_quality"] = quality
            row["quality_satisfies_request"] = satisfies
            row["quality_warning"] = warning
        rows.append(row)
    return {
        "schema_version": "agent_trace_source_slice_requests_v1",
        "rows": rows,
        "row_count": len(rows),
        "explicit_request_count": int(source_excerpt_stats.get("agent_requested_seen_refs") or 0),
        "synthesized_request_count": len(rows),
    }


def _capsule_source_slice_manifest(
    *,
    source_slice_requests: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
    repo_head: str,
    type_b_decision_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requests_by_path = {
        str(row.get("path") or ""): row
        for row in source_slice_requests.get("rows") or []
        if isinstance(row, dict)
    }
    slices: list[dict[str, Any]] = []
    for row in source_excerpt_stats.get("rows") or []:
        if not isinstance(row, dict):
            continue
        path = _capsule_public_trace_path(str(row.get("path") or ""))
        if not path:
            continue
        request = requests_by_path.get(path)
        anchor = str(row.get("selector") or "line_range")
        if row.get("symbol"):
            anchor = f"symbol:{row.get('symbol')}"
        elif row.get("range"):
            anchor = f"{anchor}:{row.get('range')}"
        truncated = (
            int(row.get("line_count") or 0) >= TRACE_CAPSULE_SOURCE_EXCERPT_LINES
            or int(row.get("bytes") or 0) >= TRACE_CAPSULE_SOURCE_EXCERPT_BYTES
        )
        quality = _capsule_source_slice_quality(str(row.get("selector") or ""), truncated=truncated, anchor=anchor)
        slices.append({
            "slice_id": str(row.get("row_id") or f"S{len(slices) + 1:03d}"),
            "request_id": str((request or {}).get("request_id") or "unrequested"),
            "artifact_uri": f"file:{path}" if path.startswith("/") else f"repo:/{path}",
            "repo_head": repo_head,
            "language_id": _capsule_source_context_language_id(path),
            "anchor": anchor,
            "selector": str(row.get("selector") or ""),
            "range": str(row.get("range") or ""),
            "path_sha16": _sha16(path),
            "text_sha16": str(row.get("sha16") or ""),
            "carrier": str(row.get("row_id") or ""),
            "carrier_command": str(row.get("command_id") or ""),
            "line_count": int(row.get("line_count") or 0),
            "bytes": int(row.get("bytes") or 0),
            "truncated": truncated,
            "slice_quality": quality,
            "linked_claims": ["CLM.source_context"],
        })
    if type_b_decision_bundle:
        for row in type_b_decision_bundle.get("slices") or []:
            if not isinstance(row, dict):
                continue
            path = _capsule_public_trace_path(str(row.get("path") or ""))
            if not path:
                continue
            slices.append({
                "slice_id": str(row.get("slice_id") or f"DBS{len(slices) + 1:03d}"),
                "request_id": str(row.get("request_id") or "unrequested"),
                "artifact_uri": f"file:{path}" if path.startswith("/") else f"repo:/{path}",
                "repo_head": repo_head,
                "language_id": _capsule_source_context_language_id(path),
                "anchor": str(row.get("anchor") or ""),
                "selector": str(row.get("selector") or ""),
                "range": str(row.get("range") or ""),
                "path_sha16": _sha16(path),
                "text_sha16": str(row.get("text_sha16") or ""),
                "carrier": str(row.get("slice_id") or ""),
                "carrier_command": "type_b_decision_bundle_auto_source_slice",
                "line_count": int(row.get("line_count") or 0),
                "bytes": int(row.get("bytes") or 0),
                "source_bytes": int(row.get("source_bytes") or row.get("bytes") or 0),
                "omitted_bytes": int(row.get("omitted_bytes") or 0),
                "byte_budget": int(row.get("byte_budget") or 0),
                "byte_truncated": bool(row.get("byte_truncated")),
                "truncated": bool(row.get("truncated")),
                "slice_quality": str(row.get("slice_quality") or ""),
                "quality_satisfies_request": bool(row.get("quality_satisfies_request", True)),
                "quality_warning": str(row.get("quality_warning") or ""),
                "linked_claims": ["CLM.source_context", "CLM.budget_sufficiency"],
            })
    quality_warning_count = sum(
        1
        for row in slices
        if row.get("quality_warning") or str(row.get("slice_quality") or "") == "symbol_miss_truncated"
    )
    blocking_quality_warning_count = sum(
        1 for row in slices if row.get("quality_satisfies_request") is False
    )
    return {
        "schema_version": "agent_trace_source_slice_manifest_v1",
        "slice_count": len(slices),
        "slice_quality_ladder": list(TRACE_CAPSULE_SOURCE_SLICE_QUALITY_LADDER),
        "slice_quality_warning_count": quality_warning_count,
        "blocking_quality_warning_count": blocking_quality_warning_count,
        "slices": slices,
    }


def _capsule_type_b_decision_bundle(
    *,
    source_context_demand: dict[str, Any],
    source_slice_requests: dict[str, Any],
    cwd: Path,
    final_delta: dict[str, Any],
    child_execution_bundle: dict[str, Any],
) -> dict[str, Any]:
    demand_state = str(source_context_demand.get("state") or "none")
    required = demand_state.startswith("required")
    request_rows = [
        row
        for row in source_slice_requests.get("rows") or []
        if isinstance(row, dict)
    ]
    slices: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    source_slice_bytes = 0
    source_slice_omitted_bytes = 0
    if required:
        for request in request_rows:
            if request.get("status") != "deficit":
                continue
            path = _capsule_public_trace_path(str(request.get("path") or ""))
            if not path or not _capsule_source_path_allowed(path):
                blocked.append({
                    "request_id": str(request.get("request_id") or ""),
                    "path": path,
                    "reason": "source_path_not_allowed",
                })
                continue
            anchor = str(request.get("anchor") or "")
            symbol = anchor.split(":", 1)[1] if anchor.startswith("symbol:") else None
            try:
                line_range = None
                if not symbol:
                    hunk_range = _capsule_hunk_context_line_range(
                        cwd=cwd,
                        path=path,
                        final_delta=final_delta,
                        max_lines=TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
                    )
                    if hunk_range:
                        start_line, end_line, anchor_label = hunk_range
                        line_range = f"{start_line}-{end_line}"
                        request["resolved_anchor"] = f"line_range:{line_range}"
                        request["anchor_derivation"] = f"final_delta_hunk_context:{anchor_label}"
                row = _select_type_b_source_excerpt(
                    cwd=cwd,
                    source_path=path,
                    line_range=line_range,
                    symbol=None if line_range else symbol,
                    full_file=False,
                    max_lines=TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
                )
                if line_range:
                    row["selection"] = "hunk_context_line_range"
                    row["selection_warning"] = f"resolved_from_final_delta_hunk:{anchor_label}"
            except SystemExit as exc:
                if not symbol:
                    blocked.append({
                        "request_id": str(request.get("request_id") or ""),
                        "path": path,
                        "anchor": anchor,
                        "reason": _compact_one_line(str(exc), limit=180),
                    })
                    continue
                try:
                    hunk_range = _capsule_hunk_context_line_range(
                        cwd=cwd,
                        path=path,
                        final_delta=final_delta,
                        max_lines=TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
                    )
                    if not hunk_range:
                        raise SystemExit("no final-delta hunk range available for source slice fallback")
                    start_line, end_line, anchor_label = hunk_range
                    row = _select_type_b_source_excerpt(
                        cwd=cwd,
                        source_path=path,
                        line_range=f"{start_line}-{end_line}",
                        symbol=None,
                        full_file=False,
                        max_lines=TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
                    )
                    row["selection"] = "hunk_context_line_range"
                    row["symbol"] = symbol
                    row["selection_warning"] = (
                        f"{_compact_one_line(str(exc), limit=140)}; "
                        f"resolved_from_final_delta_hunk:{anchor_label}"
                    )
                    request["resolved_anchor"] = f"line_range:{start_line}-{end_line}"
                    request["anchor_derivation"] = f"final_delta_hunk_context:{anchor_label}"
                except SystemExit as fallback_exc:
                    blocked.append({
                        "request_id": str(request.get("request_id") or ""),
                        "path": path,
                        "anchor": anchor,
                        "reason": _compact_one_line(str(fallback_exc), limit=180),
                    })
                    continue
            emitted = row.get("emitted_range") or {}
            start = int(emitted.get("start") or 0)
            end = int(emitted.get("end") or start)
            numbered = [str(line) for line in row.get("lines") or []]
            remaining_budget = max(0, TRACE_CAPSULE_DECISION_BUNDLE_TOTAL_SOURCE_BYTES - source_slice_bytes)
            if remaining_budget <= 0:
                blocked.append({
                    "request_id": str(request.get("request_id") or ""),
                    "path": path,
                    "anchor": anchor,
                    "reason": "decision_bundle_total_source_byte_budget_exhausted",
                })
                continue
            numbered, bundle_clip = _capsule_clip_numbered_lines_by_byte_budget(
                numbered,
                max_bytes=min(TRACE_CAPSULE_DECISION_BUNDLE_SOURCE_SLICE_BYTES, remaining_budget),
                max_line_bytes=TRACE_CAPSULE_SOURCE_EXCERPT_LINE_BYTES,
                marker_label="type_b_decision_bundle",
            )
            body = "\n".join(numbered)
            slice_id = f"DBS{len(slices) + 1:03d}"
            byte_truncated = bool(row.get("byte_truncated")) or bool(bundle_clip.get("byte_truncated"))
            omitted_line_count = int(row.get("omitted_line_count") or 0) + int(bundle_clip.get("omitted_line_count") or 0)
            omitted_byte_count = int(row.get("omitted_byte_count") or 0) + int(bundle_clip.get("omitted_byte_count") or 0)
            source_byte_count = int(row.get("source_byte_count") or bundle_clip.get("source_byte_count") or 0)
            emitted_byte_count = len(body.encode("utf-8"))
            source_slice_bytes += emitted_byte_count
            source_slice_omitted_bytes += omitted_byte_count
            truncated = bool(omitted_line_count or byte_truncated)
            selector = str(row.get("selection") or "")
            quality_anchor = str(request.get("resolved_anchor") or anchor)
            quality = _capsule_source_slice_quality(selector, truncated=truncated, anchor=quality_anchor)
            quality_satisfies, quality_warning = _capsule_source_slice_quality_satisfies_request(
                request,
                quality,
            )
            if byte_truncated and not quality_warning:
                quality_warning = "source_slice_byte_truncated"
            request["status"] = (
                "rendered_by_decision_bundle"
                if quality_satisfies
                else "rendered_by_decision_bundle_insufficient"
            )
            request["carrier"] = slice_id
            request["carrier_kind"] = (
                "type_b_decision_bundle_auto_source_slice"
                if quality_satisfies
                else "type_b_decision_bundle_auto_source_slice_insufficient"
            )
            request["slice_quality"] = quality
            request["quality_satisfies_request"] = quality_satisfies
            request["quality_warning"] = quality_warning
            slices.append({
                "slice_id": slice_id,
                "request_id": str(request.get("request_id") or ""),
                "path": path,
                "anchor": str(request.get("resolved_anchor") or anchor),
                "selector": str(row.get("selection") or ""),
                "symbol": str(row.get("symbol") or ""),
                "anchor_derivation": str(request.get("anchor_derivation") or "requested_anchor"),
                "range": f"{start}-{end}",
                "line_count": len(numbered),
                "bytes": emitted_byte_count,
                "source_bytes": source_byte_count,
                "omitted_bytes": omitted_byte_count,
                "byte_budget": int(bundle_clip.get("byte_budget") or TRACE_CAPSULE_DECISION_BUNDLE_SOURCE_SLICE_BYTES),
                "byte_truncated": byte_truncated,
                "line_byte_truncated_count": int(row.get("line_byte_truncated_count") or 0) + int(bundle_clip.get("line_byte_truncated_count") or 0),
                "text_sha16": _sha16(body),
                "truncated": truncated,
                "slice_quality": quality,
                "quality_satisfies_request": quality_satisfies,
                "quality_warning": quality_warning,
                "selection_warning": str(row.get("selection_warning") or ""),
                "lines": numbered,
            })

    aggregate_bytes = 0
    for row in child_execution_bundle.get("rows") or []:
        if isinstance(row, dict):
            aggregate = row.get("aggregate_output") or {}
            if isinstance(aggregate, dict):
                aggregate_bytes += int(aggregate.get("bytes") or 0)

    return {
        "schema_version": "agent_trace_type_b_decision_bundle_v1",
        "consumer": "type_b_continue",
        "profile": "decision_bundle",
        "demand_state": demand_state,
        "practical_budget": "~150KB",
        "source_slice_policy": "decisive_source_slices_before_aggregate_workflow_output",
        "local_no_limit_bundle": "CHILD_EXECUTION_BUNDLE",
        "auto_render_attempted": required,
        "auto_rendered_slice_count": len(slices),
        "render_blocked_count": len(blocked),
        "source_slice_bytes": source_slice_bytes,
        "source_slice_omitted_bytes": source_slice_omitted_bytes,
        "source_slice_total_byte_budget": TRACE_CAPSULE_DECISION_BUNDLE_TOTAL_SOURCE_BYTES,
        "source_slice_per_slice_byte_budget": TRACE_CAPSULE_DECISION_BUNDLE_SOURCE_SLICE_BYTES,
        "source_slice_quality_ladder": list(TRACE_CAPSULE_SOURCE_SLICE_QUALITY_LADDER),
        "source_slice_quality_warning_count": sum(1 for row in slices if row.get("quality_warning")),
        "blocking_quality_warning_count": sum(1 for row in slices if row.get("quality_satisfies_request") is False),
        "aggregate_output_bytes_pointer": aggregate_bytes,
        "child_execution_bytes_pointer": int(child_execution_bundle.get("bytes") or 0),
        "workflow_count": int(child_execution_bundle.get("workflow_count") or 0),
        "workflow_worker_count": int(child_execution_bundle.get("workflow_worker_count") or 0),
        "embedded_workflow_trace_count": int(child_execution_bundle.get("embedded_workflow_trace_count") or 0),
        "slices": slices,
        "blocked": blocked,
    }


def _capsule_source_context_deficit(
    *,
    source_slice_requests: dict[str, Any],
    final_delta: dict[str, Any],
    include_raw_sidecar: bool,
) -> dict[str, Any]:
    final_delta_paths = (
        set(_capsule_source_context_public_paths([str(path) for path in final_delta.get("paths") or []]))
        if final_delta.get("attached")
        else set()
    )
    deficits: list[dict[str, Any]] = []
    deficit_statuses = {"deficit", "rendered_by_decision_bundle_insufficient"}
    for request in source_slice_requests.get("rows") or []:
        if not isinstance(request, dict) or request.get("status") not in deficit_statuses:
            continue
        path = str(request.get("path") or "")
        if request.get("status") == "rendered_by_decision_bundle_insufficient":
            fallback = f"insufficient_source_slice:{request.get('slice_quality') or 'unknown_quality'}"
        elif path in final_delta_paths:
            fallback = "FINAL_DELTA_current_hunks_only"
        elif include_raw_sidecar:
            fallback = "raw_sidecar_not_type_b_portable"
        else:
            fallback = "none"
        deficits.append({
            "deficit_id": f"SCD{len(deficits) + 1:03d}",
            "request_id": str(request.get("request_id") or ""),
            "missing_path": path,
            "missing_anchor": str(request.get("anchor") or ""),
            "why_needed": str(request.get("why") or "source_context_required"),
            "fallback_used": fallback,
            "slice_quality": str(request.get("slice_quality") or ""),
            "carrier": str(request.get("carrier") or ""),
            "quality_warning": str(request.get("quality_warning") or ""),
            "next_best_slice": (
                f"./repo-python tools/meta/observability/cli_prompt_trace.py "
                f"--type-b-source-excerpt --source-path {path}"
            ),
            "max_context": "120_lines_or_24000_bytes",
        })
    return {
        "schema_version": "agent_trace_source_context_deficit_v1",
        "row_count": len(deficits),
        "active_count": len(deficits),
        "rows": deficits,
    }


def _capsule_source_context_readiness(
    *,
    source_context_demand: dict[str, Any],
    source_slice_requests: dict[str, Any],
    source_context_deficit: dict[str, Any],
    source_slice_manifest: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
) -> dict[str, Any]:
    request_rows = [row for row in source_slice_requests.get("rows") or [] if isinstance(row, dict)]
    demand_state = str(source_context_demand.get("state") or "none")
    required = demand_state.startswith("required")
    deficit_rows = [row for row in source_context_deficit.get("rows") or [] if isinstance(row, dict)]
    satisfying_statuses = {
        "emitted",
        "rendered_by_decision_bundle",
        "satisfied_by_final_delta",
        "delta_satisfied_for_changed_contract",
    }
    insufficient_statuses = {"rendered_by_decision_bundle_insufficient"}
    high_regret_missing = sum(
        1
        for row in request_rows
        if row.get("status") in {"deficit", *insufficient_statuses} and row.get("priority") == "critical"
    )
    emitted = sum(1 for row in request_rows if row.get("status") in {"emitted", "rendered_by_decision_bundle"})
    rendered_insufficient = sum(1 for row in request_rows if row.get("status") in insufficient_statuses)
    delta_satisfied_for_changed_contract = sum(
        1 for row in request_rows if row.get("status") == "delta_satisfied_for_changed_contract"
    )
    satisfied_by_final_delta = sum(
        1
        for row in request_rows
        if row.get("status") in satisfying_statuses
    )
    if demand_state in {"none", "optional"}:
        overall = "green"
    elif required and high_regret_missing:
        overall = "amber"
    elif deficit_rows:
        overall = "amber"
    else:
        overall = "green"
    copy_effect = "amber_source_insufficient" if overall == "amber" and required else "none"
    satisfaction = (
        "delta_satisfied_for_changed_contract"
        if overall == "green" and required and delta_satisfied_for_changed_contract
        else "satisfied"
        if overall == "green" and demand_state not in {"none", "optional"}
        else ("unsatisfied" if overall == "amber" and required else demand_state)
    )
    source_context_demand["satisfaction"] = satisfaction
    return {
        "schema_version": "agent_trace_source_context_readiness_v1",
        "overall": overall,
        "demand": demand_state,
        "satisfaction": satisfaction,
        "explicit_requests": int(source_excerpt_stats.get("agent_requested_seen_refs") or 0),
        "synthesized_requests": len(request_rows),
        "emitted": emitted,
        "satisfied_by_final_delta": satisfied_by_final_delta,
        "delta_satisfied_for_changed_contract": delta_satisfied_for_changed_contract,
        "manifest_slices": int(source_slice_manifest.get("slice_count") or 0),
        "omitted": len(deficit_rows),
        "high_regret_missing": high_regret_missing,
        "rendered_insufficient": rendered_insufficient,
        "slice_quality_warning_count": int(source_slice_manifest.get("slice_quality_warning_count") or 0),
        "blocking_quality_warning_count": int(source_slice_manifest.get("blocking_quality_warning_count") or 0),
        "copy_readiness_effect": copy_effect,
    }


def _capsule_type_b_source_closeout_lint(
    *,
    source_context_demand: dict[str, Any],
    source_context_readiness: dict[str, Any],
) -> dict[str, Any]:
    required = str(source_context_demand.get("state") or "").startswith("required")
    high_regret_missing = int(source_context_readiness.get("high_regret_missing") or 0)
    if required and high_regret_missing:
        result = "warn"
    else:
        result = "pass"
    return {
        "schema_version": "agent_trace_type_b_source_closeout_lint_v1",
        "result": result,
        "demand_state": source_context_demand.get("state") or "none",
        "readiness": source_context_readiness.get("overall") or "green",
        "high_regret_missing": high_regret_missing,
        "rule": "source_dependent_type_b_handoff_requires_decisive_source_slice_or_deficit",
    }


def _capsule_closeout_claims_requested_source_excerpts(final_assistant_text: str) -> bool:
    text = final_assistant_text or ""
    if not text:
        return False
    patterns = [
        r"\bused the affordance\b",
        r"\bselected exact source\b",
        r"\bselected .*?\bsource excerpts?\b",
        r"\bsource excerpts? (?:will|should|are) (?:be )?(?:available|included|present)\b",
        r"\blatest (?:response )?bundle (?:will|should) include\b.*\bSOURCE_EXCERPTS\b",
        r"\bSOURCE_EXCERPTS\b.*\b(?:will|should) include\b",
    ]
    return any(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def _capsule_path_mentions(text: str) -> list[str]:
    pattern = re.compile(
        r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
        r"\.(?:py|md|json|jsonl|txt|tsx|ts|js|swift|mjs|yml|yaml|toml))"
    )
    paths: list[str] = []
    for match in pattern.finditer(text or ""):
        path = _capsule_public_trace_path(match.group("path"))
        if path and _capsule_source_path_allowed(path) and path not in paths:
            paths.append(path)
    return paths


def _capsule_evidence_manifest(
    *,
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    edit_rows: list[dict[str, Any]],
    source_excerpt_stats: dict[str, Any],
    check_rows: list[CapsuleEvidenceClassification],
    governance_rows: list[CapsuleEvidenceClassification],
    final_assistant_text: str,
    final_delta: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}

    def row_for(path: str) -> dict[str, Any]:
        public_path = _capsule_public_trace_path(path)
        row = by_path.get(public_path)
        if row is None:
            row = {
                "path": public_path,
                "carried_as": [],
                "sufficient_for": [],
                "insufficient_for": [],
            }
            by_path[public_path] = row
        return row

    def add(row: dict[str, Any], key: str, value: str) -> None:
        values = row[key]
        if value and value not in values:
            values.append(value)

    for index, edit in enumerate(edit_rows, start=1):
        path = str(edit.get("path") or "")
        if not path:
            continue
        row = row_for(path)
        add(row, "carried_as", f"edit_event_hunk:E{index:03d}")
        add(row, "sufficient_for", "edit_attempt_chronology")
        add(row, "insufficient_for", "final_substrate_state")

    if final_delta and final_delta.get("attached"):
        for path in final_delta.get("paths", []) or ["final_delta"]:
            row = row_for(str(path))
            add(row, "carried_as", "diff_hunk:FINAL_DELTA")
            add(row, "sufficient_for", "final_substrate_delta_review")
            add(row, "insufficient_for", "full_context_review")

    for path in source_excerpt_stats.get("paths", []) or []:
        row = row_for(str(path))
        add(row, "carried_as", "source_excerpt")
        add(row, "sufficient_for", "source_range_review")

    for source_row in source_excerpt_stats.get("agent_requested_rows", []) or []:
        path = str(source_row.get("path") or "")
        if not path:
            continue
        row = row_for(path)
        row_id = str(source_row.get("row_id") or "")
        add(row, "carried_as", f"requested_source_excerpt:{row_id}" if row_id else "requested_source_excerpt")
        add(row, "sufficient_for", "selected_source_review")
        if "full_context_review" in row["insufficient_for"]:
            row["insufficient_for"].remove("full_context_review")

    for idx, wrapped in enumerate(renderable, start=1):
        ev, output_text, _exit_code, _is_error = wrapped
        if not output_text or output_text.startswith("[no ") or _capsule_output_is_nested_trace(output_text):
            continue
        command = _capsule_clean_text(_capsule_command(ev))
        ref = _capsule_source_read_ref(command)
        if not ref:
            continue
        path = str(ref.get("path") or "")
        if not path:
            continue
        row = row_for(path)
        add(row, "carried_as", f"command_return:C{idx:03d}")
        add(row, "sufficient_for", "command_output_review")
        if not any(str(item).startswith(("requested_source_excerpt", "source_excerpt", "diff_hunk")) for item in row["carried_as"]):
            add(row, "insufficient_for", "source_authority_by_itself")

    for path in _capsule_path_mentions(final_assistant_text):
        row = row_for(path)
        if not row["carried_as"]:
            add(row, "carried_as", "passive_mention")
            add(row, "sufficient_for", "none")
            add(row, "insufficient_for", "evidence_not_carried")

    if check_rows:
        row = row_for("validation_receipts")
        add(row, "carried_as", f"command_return:validation:{len(check_rows)}")
        add(row, "sufficient_for", "validation_status")
        add(row, "insufficient_for", "source_context_review")

    if governance_rows:
        row = row_for("governance_receipts")
        add(row, "carried_as", f"receipt:{len(governance_rows)}")
        add(row, "sufficient_for", "governance_status")
        add(row, "insufficient_for", "source_context_review")

    def priority(row: dict[str, Any]) -> tuple[int, str]:
        carriers = ",".join(row["carried_as"])
        if "requested_source_excerpt" in carriers:
            bucket = 0
        elif "source_excerpt" in carriers:
            bucket = 1
        elif "diff_hunk" in carriers:
            bucket = 2
        elif "edit_event_hunk" in carriers:
            bucket = 3
        elif "command_return" in carriers:
            bucket = 4
        elif "receipt" in carriers:
            bucket = 5
        else:
            bucket = 6
        return (bucket, row["path"])

    rows = sorted(by_path.values(), key=priority)
    class_counts: dict[str, int] = {
        "requested_source_excerpt": 0,
        "source_excerpt": 0,
        "diff_hunk": 0,
        "edit_event_hunk": 0,
        "command_return": 0,
        "receipt": 0,
        "passive_mention": 0,
    }
    for row in rows:
        for carrier in row["carried_as"]:
            key = carrier.split(":", 1)[0]
            if key in class_counts:
                class_counts[key] += 1

    section = ["EVIDENCE_MANIFEST"]
    section.append(
        "evidence_manifest_summary: "
        f"rows={len(rows)} paths={sum(1 for row in rows if '/' in row['path'])} "
        f"requested_source_excerpt={class_counts['requested_source_excerpt']} "
        f"source_excerpt={class_counts['source_excerpt']} "
        f"diff_hunk={class_counts['diff_hunk']} "
        f"edit_event_hunk={class_counts['edit_event_hunk']} "
        f"command_return={class_counts['command_return']} "
        f"receipt={class_counts['receipt']} "
        f"passive_mention={class_counts['passive_mention']}"
    )
    section.append(
        "evidence_manifest_rule: "
        "passive_mention_is_not_evidence diff_hunk_proves_final_delta_not_full_context "
        "edit_event_hunk_is_chronology_not_final_state "
        "requested_source_excerpt_carries_selected_source"
    )
    for index, row in enumerate(rows[:16], start=1):
        section.append(
            "evidence_manifest_row: "
            f"row_id=M{index:03d} path={row['path']} "
            f"carried_as={','.join(row['carried_as']) or 'none'} "
            f"sufficient_for={','.join(row['sufficient_for']) or 'none'} "
            f"insufficient_for={','.join(row['insufficient_for']) or 'none'}"
        )
    if len(rows) > 16:
        section.append(f"evidence_manifest_omitted: rows={len(rows) - 16} reason=manifest_row_limit")
    return section, {
        "schema_version": "agent_trace_evidence_manifest_v1",
        "row_count": len(rows),
        "class_counts": class_counts,
        "rows": rows,
    }


def _capsule_source_excerpt_sections(
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    *,
    source_sha16: str,
    prompt_text: str = "",
) -> tuple[list[str], dict[str, Any]]:
    rows: list[str] = ["SOURCE_EXCERPTS"]
    candidates: list[tuple[int, int, str, str, dict[str, Any], list[str], str]] = []
    excerpts: list[tuple[str, str, dict[str, Any], list[str], str]] = []
    omitted = 0
    prompt_file_ref_seen_count = 0
    agent_requested_seen_count = 0
    omission_reason_counts: dict[str, int] = {}
    agent_requested_drop_rows: list[dict[str, Any]] = []

    def record_omission(
        ref: dict[str, Any],
        reason: str,
        *,
        command_id: str = "",
        command: str = "",
    ) -> None:
        nonlocal omitted
        omitted += 1
        omission_reason_counts[reason] = omission_reason_counts.get(reason, 0) + 1
        if ref.get("kind") == "agent_requested_source_excerpt":
            agent_requested_drop_rows.append({
                "command_id": command_id,
                "path": str(ref.get("path") or ""),
                "reason": reason,
                "command": str(ref.get("command") or command or ""),
            })

    def excerpt_range_label(ref: dict[str, Any], numbered: list[str]) -> str:
        start = ref.get("start_line")
        end = ref.get("end_line")
        numbered_line_numbers = _capsule_numbered_line_numbers(numbered)
        if numbered_line_numbers:
            return f"{numbered_line_numbers[0]}-{numbered_line_numbers[-1]}"
        if isinstance(start, int) and isinstance(end, int):
            return f"{start}-{end}"
        if isinstance(start, int):
            return f"{start}-{start + len(numbered) - 1}"
        return "output_line_numbers_or_unknown"

    def excerpt_selector(ref: dict[str, Any]) -> str:
        if ref.get("full_file"):
            return "full_file"
        if ref.get("symbol"):
            return "symbol"
        if isinstance(ref.get("start_line"), int) or isinstance(ref.get("end_line"), int):
            return "line_range"
        return "trace_output"

    for raw_path in _capsule_prompt_file_ref_paths(prompt_text):
        prompt_excerpt = _capsule_prompt_file_excerpt(raw_path)
        if not prompt_excerpt:
            continue
        numbered, public_path, byte_count = prompt_excerpt
        prompt_file_ref_seen_count += 1
        candidates.append((
            20,
            prompt_file_ref_seen_count,
            f"P{prompt_file_ref_seen_count:03d}",
            f"prompt_file_ref {public_path}",
            {
                "kind": "prompt_file_ref",
                "command": "prompt_file_ref",
                "path": public_path,
                "start_line": 1,
                "end_line": len(numbered),
            },
            numbered,
            f"{public_path}\nbytes_read={byte_count}\n" + "\n".join(numbered),
        ))
    for idx, wrapped in enumerate(renderable, start=1):
        ev, output_text, _exit_code, _is_error = wrapped
        command = _capsule_clean_text(_capsule_command(ev))
        ref = _capsule_source_read_ref(command)
        if not ref:
            continue
        command_id = f"C{idx:03d}"
        is_agent_requested = ref.get("kind") == "agent_requested_source_excerpt"
        if is_agent_requested:
            agent_requested_seen_count += 1
        output = output_text or ""
        if not output or output.startswith("[no ") or _capsule_output_is_nested_trace(output):
            if is_agent_requested:
                record_omission(ref, "requested_excerpt_output_missing", command_id=command_id, command=command)
            continue
        if is_agent_requested and "type_b_source_excerpt_carrier:" in output:
            numbered, output, sidecar_reason = _capsule_type_b_source_excerpt_from_carrier(output, ref)
            if sidecar_reason:
                record_omission(ref, sidecar_reason, command_id=command_id, command=command)
                continue
            candidates.append((
                100,
                idx,
                command_id,
                command,
                ref,
                numbered,
                output,
            ))
            continue
        display_lines, _redaction_hits = _capsule_command_return_text(output)
        if not display_lines:
            if is_agent_requested:
                record_omission(ref, "requested_excerpt_output_empty", command_id=command_id, command=command)
            continue
        numbered = _capsule_numbered_source_lines(display_lines, ref)
        if not numbered:
            if is_agent_requested:
                numbered, output, sidecar_reason = _capsule_type_b_source_excerpt_from_carrier(output, ref)
                if sidecar_reason:
                    reason = (
                        "requested_excerpt_no_numbered_lines"
                        if sidecar_reason == "requested_excerpt_sidecar_receipt_absent"
                        else sidecar_reason
                    )
                    record_omission(ref, reason, command_id=command_id, command=command)
                    continue
            else:
                continue
        if not numbered:
            continue
        candidates.append((
            100 if is_agent_requested else 10,
            idx,
            command_id,
            command,
            ref,
            numbered,
            output,
        ))

    excerpt_keys: set[tuple[str, str, int | None, int | None, str]] = set()
    for _priority, _sequence, command_id, command, ref, numbered, output in sorted(
        candidates,
        key=lambda row: (-row[0], row[1]),
    ):
        ref_key = _capsule_source_ref_key(ref)
        if ref_key in excerpt_keys:
            record_omission(ref, "duplicate_ref", command_id=command_id, command=command)
            continue
        if len(excerpts) >= TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT:
            reason = (
                "requested_excerpt_dropped_limit_exceeded"
                if ref.get("kind") == "agent_requested_source_excerpt"
                else "limit_exceeded"
            )
            record_omission(ref, reason, command_id=command_id, command=command)
            continue
        excerpts.append((command_id, command, ref, numbered, output))
        excerpt_keys.add(ref_key)

    paths: list[str] = []
    line_count = 0
    byte_count = 0
    for _command_id, _command, ref, numbered, _output in excerpts:
        path = str(ref.get("path") or "")
        if path and path not in paths:
            paths.append(path)
        line_count += len(numbered)
        byte_count += sum(len(line.encode("utf-8")) for line in numbered)
    prompt_file_ref_count = sum(1 for _id, _command, ref, _numbered, _output in excerpts if ref.get("kind") == "prompt_file_ref")
    agent_requested_ref_count = sum(
        1 for _id, _command, ref, _numbered, _output in excerpts
        if ref.get("kind") == "agent_requested_source_excerpt"
    )
    agent_requested_omitted_count = len(agent_requested_drop_rows)
    if agent_requested_seen_count == 0:
        requested_survival_status = "none_seen"
    elif agent_requested_omitted_count == 0:
        requested_survival_status = "all_emitted"
    else:
        requested_survival_status = "dropped_with_reasons"
    source_excerpt_rows: list[dict[str, Any]] = []
    for section_index, (command_id, command, ref, numbered, output) in enumerate(excerpts, start=1):
        row_id = f"S{section_index:03d}"
        path = str(ref.get("path") or "")
        body = "\n".join(numbered)
        source_excerpt_rows.append({
            "row_id": row_id,
            "command_id": command_id,
            "path": path,
            "range": excerpt_range_label(ref, numbered),
            "selector": excerpt_selector(ref),
            "symbol": str(ref.get("symbol") or ""),
            "full_file": bool(ref.get("full_file")),
            "kind": str(ref.get("kind") or ""),
            "command": str(ref.get("command") or command or ""),
            "line_count": len(numbered),
            "bytes": len(body.encode("utf-8")),
            "sha16": _sha16(output),
        })
    agent_requested_rows: list[dict[str, Any]] = []
    agent_requested_path_index: dict[str, dict[str, Any]] = {}
    for row in source_excerpt_rows:
        if row.get("kind") != "agent_requested_source_excerpt":
            continue
        row = {
            "row_id": row["row_id"],
            "command_id": row["command_id"],
            "path": row["path"],
            "range": row["range"],
            "selector": row["selector"],
            "symbol": row["symbol"],
            "full_file": row["full_file"],
        }
        agent_requested_rows.append(row)
        path = str(row.get("path") or "")
        if path not in agent_requested_path_index:
            agent_requested_path_index[path] = {
                "path": path,
                "row_ids": [],
                "ranges": [],
                "selectors": [],
                "emitted_count": 0,
        }
        path_row = agent_requested_path_index[path]
        path_row["row_ids"].append(str(row["row_id"]))
        path_row["ranges"].append(row["range"])
        path_row["selectors"].append(row["selector"])
        path_row["emitted_count"] += 1
    agent_requested_path_rows = list(agent_requested_path_index.values())
    stats = {
        "count": len(excerpts),
        "lines": line_count,
        "bytes": byte_count,
        "paths": paths,
        "omitted": omitted,
        "prompt_file_refs": prompt_file_ref_count,
        "prompt_file_seen_refs": prompt_file_ref_seen_count,
        "agent_requested_refs": agent_requested_ref_count,
        "agent_requested_seen_refs": agent_requested_seen_count,
        "agent_requested_emitted_refs": agent_requested_ref_count,
        "agent_requested_omitted_refs": agent_requested_omitted_count,
        "agent_requested_drop_reasons": agent_requested_drop_rows,
        "agent_requested_rows": agent_requested_rows,
        "agent_requested_path_rows": agent_requested_path_rows,
        "agent_requested_paths": [row["path"] for row in agent_requested_path_rows],
        "agent_requested_path_count": len(agent_requested_path_rows),
        "rows": source_excerpt_rows,
        "omission_reasons": omission_reason_counts,
        "requested_excerpt_survival_status": requested_survival_status,
    }
    omission_reason_summary = ",".join(
        f"{reason}:{count}" for reason, count in sorted(omission_reason_counts.items())
    ) or "none"
    requested_path_summary = ";".join(
        f"{row['path']}=>{','.join(row['row_ids'])}"
        for row in agent_requested_path_rows[:8]
    )
    if len(agent_requested_path_rows) > 8:
        requested_path_summary = (
            f"{requested_path_summary};+{len(agent_requested_path_rows) - 8}_more"
            if requested_path_summary
            else f"+{len(agent_requested_path_rows) - 8}_more"
        )
    if not requested_path_summary:
        requested_path_summary = "none"
    rows.append(
        "source_excerpt_summary: "
        f"count={stats['count']} lines={stats['lines']} paths={len(paths)} omitted={omitted} "
        f"agent_requested_refs={agent_requested_ref_count} prompt_file_refs={prompt_file_ref_count} "
        f"source=agent_requested_or_prompt_file_refs_or_trace_read_outputs policy=bounded_redacted_line_ranges limit={TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT} "
        f"agent_requested_seen={agent_requested_seen_count} agent_requested_emitted={agent_requested_ref_count} "
        f"agent_requested_omitted={agent_requested_omitted_count} omission_reasons={omission_reason_summary}"
    )
    rows.append(
        "requested_excerpt_survival: "
        f"status={requested_survival_status} seen={agent_requested_seen_count} "
        f"emitted={agent_requested_ref_count} omitted={agent_requested_omitted_count} "
        "rule=explicit_type_b_source_excerpt_must_emit_or_explain"
    )
    rows.append(
        "requested_excerpt_paths: "
        f"path_count={len(agent_requested_path_rows)} emitted={agent_requested_ref_count} "
        f"omitted={agent_requested_omitted_count} rows={requested_path_summary}"
    )
    for row in agent_requested_rows[:12]:
        rows.append(
            "requested_excerpt_row: "
            f"row_id={row['row_id']} command_id={row['command_id']} "
            f"path={row['path'] or 'unknown'} range={row['range']} selector={row['selector']}"
        )
    for drop in agent_requested_drop_rows[:6]:
        rows.append(
            "requested_excerpt_dropped: "
            f"command_id={drop.get('command_id') or 'unknown'} "
            f"path={drop.get('path') or 'unknown'} "
            f"reason={drop.get('reason') or 'unknown'} "
            f"command={drop.get('command') or 'unknown'}"
        )
    if not excerpts:
        rows.append("none captured")
        return rows, stats

    for section_index, (command_id, command, ref, numbered, output) in enumerate(excerpts, start=1):
        range_label = excerpt_range_label(ref, numbered)
        body = "\n".join(numbered)
        rows.append(
            f"S{section_index:03d} {command_id} path={ref.get('path')} range={range_label} "
            f"command={ref.get('command')} lines={len(numbered)} "
            f"bytes={len(body.encode('utf-8'))} sha16={_sha16(output)}"
        )
        rows.extend(_capsule_command_display_lines(command)[:2])
        rows.extend(numbered)
    rows.append(f"raw_sidecar_source: trace_read_outputs sha16={source_sha16}")
    return rows, stats


def _capsule_command_surface_lines(command: str) -> list[str]:
    clean = (command or "").strip()
    if clean.startswith("$ "):
        clean = clean[2:].strip()
    lines: list[str] = []
    heredoc_delim = ""
    for raw in clean.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if heredoc_delim:
            if stripped == heredoc_delim:
                heredoc_delim = ""
            continue
        line = stripped[:-1].rstrip() if stripped.endswith("\\") else stripped
        lines.append(line)
        m = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_-]*)['\"]?", stripped)
        if m:
            heredoc_delim = m.group(1)
    return lines


def _capsule_argv_from_shell_line(line: str) -> list[str]:
    first_line = re.split(r"\s+(?:&&|\|\||;|\|)\s+", (line or "").strip(), maxsplit=1)[0].strip()
    if not first_line:
        return []
    try:
        argv = shlex.split(first_line)
    except ValueError:
        argv = first_line.split()
    if not argv:
        return []

    trimmed: list[str] = []
    for token in argv:
        if token in {">", ">>", "2>", "2>>", "2>&1", "|", "&&", "||", ";"}:
            break
        if token.startswith(">") or token.startswith("2>"):
            break
        trimmed.append(token)
    argv = trimmed or argv

    while argv and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
        argv = argv[1:]
    if argv and Path(argv[0]).name == "env":
        argv = argv[1:]
        while argv and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
            argv = argv[1:]
    return argv


def _capsule_command_surface_argvs(command: str) -> list[list[str]]:
    out: list[list[str]] = []
    for line in _capsule_command_surface_lines(command):
        argv = _capsule_argv_from_shell_line(line)
        if not argv:
            continue
        if argv[0].startswith("-") or argv[0] in {"do", "done", "then", "fi", "else"}:
            continue
        out.append(argv)
    return out


def _capsule_command_head_argv(command: str) -> list[str]:
    """Return argv for the actually executed shell head, excluding heredoc body text."""
    candidates = _capsule_command_surface_argvs(command)
    return candidates[0] if candidates else []


def _capsule_command_display_lines(command: str) -> list[str]:
    clean = _capsule_clean_text(command or "")
    display = clean if clean.startswith("$ ") else f"$ {clean}"
    line_count = max(1, len(display.splitlines()))
    byte_len = len(display.encode("utf-8"))
    if line_count <= 8 and byte_len <= 1400:
        return display.splitlines()

    surface_lines = _capsule_command_surface_lines(clean)
    primary = ""
    for token_group in (
        ("scoped_commit.py", "task_ledger_apply.py", "work_ledger.py", "closeout_executor.py", "git_state_snapshot.py"),
        ("repo-pytest", "repo-python", "kernel.py"),
        ("git ",),
    ):
        primary = next(
            (
                line
                for line in surface_lines
                if not line.startswith("-") and any(token in line for token in token_group)
            ),
            "",
        )
        if primary:
            break
    if not primary:
        primary = surface_lines[0] if surface_lines else display.splitlines()[0]
    primary = primary if primary.startswith("$ ") else f"$ {primary}"
    return [
        _capsule_clean_text(primary),
        f"[command body summarized; lines={line_count} bytes={byte_len} "
        f"sha16={_sha16(display)}; raw_sidecar=available]",
    ]


def _capsule_script_surface(argv: list[str]) -> tuple[str, list[str], str]:
    if not argv:
        return ("", [], "")
    exe = Path(argv[0]).name
    if exe in {"repo-python", "python", "python3"}:
        if len(argv) >= 3 and argv[1] == "-m":
            return (argv[2], argv[3:], "module")
        if len(argv) >= 2:
            return (argv[1], argv[2:], "python_arg")
    return (argv[0], argv[1:], "exec")


def _capsule_compact_label(script: str, args: list[str], *, max_args: int = 2) -> str:
    base = Path(script).name if script else "command"
    flags_with_values = {
        "--path", "--message", "--session", "--provider", "--turn", "--context-budget",
        "--max-actions", "--ids", "--band", "--variant", "--session-prefix", "--output",
        "-o", "--support-dir", "--min-commands", "--min-edit-paths",
    }
    visible_args: list[str] = []
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in {">", ">>", "2>", "2>>", "2>&1"}:
            break
        if arg.startswith("-"):
            if arg in flags_with_values and "=" not in arg:
                skip_next = True
            continue
        visible_args.append(arg)
        if len(visible_args) >= max_args:
            break
    return " ".join([base] + visible_args).strip()


_CAPSULE_SUBSTRATE_SUBSTITUTION_LEDGER_MODULE = (
    "microcosm_core.validators.substrate_substitution_ledger"
)


def _capsule_flag_value(args: list[str], flag: str) -> str:
    for index, arg in enumerate(args):
        if arg == flag and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith(f"{flag}="):
            return arg.split("=", 1)[1]
    return ""


def _capsule_command_bucket_and_label_from_argv(argv: list[str], role: str) -> tuple[str | None, str, str]:
    if not argv:
        return (None, "", "")

    exe = Path(argv[0]).name
    script, script_args, script_kind = _capsule_script_surface(argv)
    script_base = Path(script).name
    lower_script = script.lower()
    lower_args = [arg.lower() for arg in script_args]
    joined_args = " ".join(lower_args)

    if script_kind == "python_arg" and script in {"-", "-c"}:
        return ("diagnostic", f"{exe} {script}", f"{exe} {script}")

    if script_base == "closeout_executor.py":
        label = _capsule_compact_label(script, script_args)
        return ("governance", label, f"gov:{label}")
    if script_base == "mission_transaction_preflight.py":
        label = _capsule_compact_label(script, script_args)
        return ("governance", label, f"gov:{label}")
    if script_base == "git_state_snapshot.py" and "--closeout-conditions" in lower_args:
        label = "git_state_snapshot closeout-conditions"
        return ("governance", label, f"gov:{label}")
    if script_base == "run_git.py" and "audit" in lower_args and "push" in lower_args:
        label = "run_git audit push"
        return ("governance", label, f"gov:{label}")
    if script_base == "scoped_commit.py":
        label = _capsule_compact_label(script, script_args, max_args=1)
        return ("governance", label, "gov:scoped_commit")
    if script_base == "work_ledger.py" and "session-finalize" in lower_args:
        label = "work_ledger session-finalize"
        return ("governance", label, f"gov:{label}")
    if script_base == "task_ledger_apply.py" and any(
        action in lower_args for action in (
            "quick-capture",
            "capture",
            "note",
            "transition",
            "sign-off",
            "execution-receipt",
            "record-execution-receipt",
            "enqueue-execution-receipt",
            "drain-intake",
            "intake-status",
        )
    ):
        label = _capsule_compact_label(script, script_args, max_args=1)
        return ("governance", label, f"gov:{label}")

    if exe in {"pytest", "repo-pytest"}:
        label = _capsule_compact_label(argv[0], argv[1:])
        return ("check", label, f"check:{label}")
    if exe == "node" and any(arg in lower_args for arg in ("--check", "--test")):
        label = _capsule_compact_label(argv[0], argv[1:])
        return ("check", label, f"check:{label}")
    if exe in {"swiftc", "swift"} and (
        "-parse" in lower_args or "test" in lower_args or "build" in lower_args
    ):
        label = _capsule_compact_label(argv[0], argv[1:])
        return ("check", label, f"check:{label}")
    if exe == "npm" and any(arg in lower_args for arg in ("test", "build")):
        label = _capsule_compact_label(argv[0], argv[1:])
        return ("check", label, f"check:{label}")
    if exe == "make" and any(arg in lower_args for arg in ("ci", "smoke", "package-smoke", "test", "package-test")):
        label = _capsule_compact_label(argv[0], argv[1:])
        return ("check", label, f"check:{label}")

    if script_kind == "module" and lower_script == "py_compile":
        label = _capsule_compact_label("py_compile", script_args)
        return ("check", label, f"check:{label}")
    if script_kind == "module" and lower_script == "microcosm_core.cli" and "crown-jewel-demo" in lower_args and "run" in lower_args:
        label = _capsule_compact_label(script, script_args)
        return ("check", label, f"check:{label}")
    if script_kind == "module" and lower_script == "microcosm_core.projections.organ_surface_contract":
        label = _capsule_compact_label(script, script_args)
        return ("check", label, f"check:{label}")
    if (
        script_kind == "module"
        and lower_script == _CAPSULE_SUBSTRATE_SUBSTITUTION_LEDGER_MODULE
        and any(arg in lower_args for arg in ("--check", "--write", "--drift-report"))
    ):
        action = "write" if "--write" in lower_args else (
            "drift-report" if "--drift-report" in lower_args else "check"
        )
        write_scope = _capsule_flag_value(script_args, "--write-scope")
        label = " ".join(
            part for part in ("substrate_substitution_ledger", action, write_scope) if part
        )
        return ("check", label, f"check:{label}")
    if script_base == "task_ledger_apply.py" and "validate" in lower_args:
        label = "task_ledger validate"
        return ("check", label, f"check:{label}")
    if script_base.startswith("check_") or "--check" in lower_args:
        label = _capsule_compact_label(script, script_args)
        return ("check", label, f"check:{label}")
    if (
        script_base.endswith("_test.py")
        or script_base.startswith("test_")
        or script_base in {"trace_variant_smoke.py", "trace_size_smoke.py", "trace_capsule_unit_test.py"}
    ):
        label = _capsule_compact_label(script, script_args)
        return ("check", label, f"check:{label}")
    if script_base == "frontend_vitest.py" and "--help" not in lower_args:
        label = _capsule_compact_label(script, script_args)
        return ("check", label, f"check:{label}")
    if "pytest" in lower_script:
        label = _capsule_compact_label(script, script_args)
        return ("check", label, f"check:{label}")

    if script_base in {"kernel.py", "rg", "grep", "sed", "head", "tail", "wc", "git", "jq"} or role in {"boot", "read", "srch"}:
        label = _capsule_compact_label(script, script_args)
        return ("diagnostic", label, f"diag:{label}")
    if exe in {"repo-python", "python", "python3", "node"} and script_kind == "python_arg":
        label = _capsule_compact_label(script, script_args)
        return ("diagnostic", label, f"diag:{label}")
    if "smoke" in lower_script:
        label = _capsule_compact_label(script, script_args)
        return ("diagnostic", label, f"diag:{label}")
    if role in {"cmd", "boot", "srch", "read"} and any(arg in joined_args for arg in ("status", "diff", "log", "show")):
        label = _capsule_compact_label(script, script_args)
        return ("diagnostic", label, f"diag:{label}")
    return (None, "", "")


def _capsule_command_bucket_and_label(command: str, role: str) -> tuple[str | None, str, str]:
    publication_kind = _capsule_publication_check_kind(command)
    if publication_kind:
        label = publication_kind.replace("_", " ")
        return ("check", label, f"check:{label}")
    candidates = _capsule_command_surface_argvs(command)
    if not candidates:
        if role in {"boot", "read", "srch", "diag"}:
            return ("diagnostic", role, role)
        return (None, "", "")
    for argv in candidates:
        bucket, label, identity = _capsule_command_bucket_and_label_from_argv(argv, role)
        if bucket:
            return (bucket, label, identity)
    if role in {"boot", "read", "srch", "diag"}:
        return ("diagnostic", role, role)
    return (None, "", "")


def _capsule_evidence_result(bucket: str, exit_code: int | None, is_error: bool, output_text: str = "") -> str:
    output_lower = (output_text or "").lower()
    if bucket == "governance" and (
        '"status": "blocked"' in output_lower
        or '"stop_reason":' in output_lower
        or '"direct_push_allowed": false' in output_lower
    ):
        return "other" if exit_code == 0 and not is_error else "fail"
    if exit_code is not None:
        return "pass" if exit_code == 0 else "fail"
    return "fail" if is_error else "other"


_CAPSULE_RESIDUAL_ID_RE = re.compile(r"\bcap_[A-Za-z0-9][A-Za-z0-9_.:-]*")
_CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE: dict[str, dict] | None = None
_CAPSULE_CLOSED_RESIDUAL_STATES = {
    "done",
    "closed",
    "retired",
    "satisfied",
    "superseded",
    "accepted",
    "signoff",
    "signed_off",
}
_CAPSULE_PROJECTION_ARTIFACT_SUFFIXES = (
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".txt",
    ".csv",
)
_CAPSULE_KNOWN_RESIDUAL_IDS = (
    "microcosm_dogfood_paper_module_sidecar_claim",
    "microcosm_cold_entry_real_trace_comparison_absent",
    "microcosm_first_screen_output_size",
    "microcosm_dogfood_sandbox_idempotence",
    "root_readme_audience_layer_commit_blocker",
)


def _capsule_suppresses_broad_residual_scan(command: str, output_text: str) -> bool:
    command_lower = (command or "").lower()
    output_lower = (output_text or "").lower()
    if (
        "task_ledger_apply.py" in command_lower
        and "validate" in command_lower
        and any(marker in output_lower for marker in (
            "validation_status",
            "warning_count",
            "error_count",
            "warning_classes",
            "state/task_ledger/views",
        ))
    ):
        return True
    return False


def _capsule_task_ledger_work_items() -> dict[str, dict]:
    global _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE
    if _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE is not None:
        return _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE
    ledger_path = REPO_ROOT / "state" / "task_ledger" / "ledger.json"
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE = {}
        return _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE
    items = data.get("work_items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE = {}
        return _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE
    _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE = {
        str(item.get("id")): item
        for item in items
        if isinstance(item, dict) and item.get("id")
    }
    return _CAPSULE_TASK_LEDGER_WORK_ITEMS_CACHE


def _capsule_ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return tuple(out)


def _capsule_residual_ids(command: str, output_text: str) -> tuple[str, ...]:
    if _capsule_suppresses_broad_residual_scan(command, output_text):
        return ()
    text = f"{command}\n{output_text}"
    residual_ids: list[str] = []
    for residual_id in _CAPSULE_KNOWN_RESIDUAL_IDS:
        if residual_id in text:
            residual_ids.append(residual_id)
    lowered = text.lower()
    if "sidecar_residual" in lowered and "open" in lowered:
        residual_ids.append("microcosm_dogfood_paper_module_sidecar_claim")
    for match in _CAPSULE_RESIDUAL_ID_RE.finditer(text):
        token = match.group(0).strip(".,;:'\"")
        if token != "cap_id":
            residual_ids.append(token)
    return _capsule_ordered_unique(residual_ids)


def _capsule_residual_id(command: str, output_text: str) -> str:
    residual_ids = _capsule_residual_ids(command, output_text)
    return residual_ids[0] if residual_ids else ""


def _capsule_publication_blocker_receipt_from_text(text: str) -> dict[str, Any]:
    lowered = (text or "").lower()
    has_publication_blocker_shape = any(marker in lowered for marker in (
        "publication blocker",
        "publication_blocker_receipt",
        "publication_blocker_event",
        "clean publication prepare",
        "clean-base replay",
        "clean_base_replay",
        "safe_path_snapshot=false",
        "source_owner_overlap_blocks_auto_snapshot=true",
        "publication_lane publish",
        "prerequisite trace-source commits",
        "prerequisite_trace_source_commits",
    ))
    cap_ids = _capsule_residual_ids("", text or "")
    explicit_receipt_ids = [
        match.group(1).strip("`'\".,;:")
        for match in re.finditer(r"\bpublication_blocker_receipt:\s*`?([A-Za-z0-9_.:-]+)`?", text or "")
        if match.group(1).strip("`'\".,;:")
    ]
    publication_cap_ids = [
        cap_id
        for cap_id in [*explicit_receipt_ids, *cap_ids]
        if "publication" in cap_id.lower()
        or "trace_capsule_evidence_scope" in cap_id.lower()
        or "clean_publication" in lowered
        or cap_id in explicit_receipt_ids
    ]
    if not has_publication_blocker_shape or not publication_cap_ids:
        return {
            "status": "none",
            "receipt": "",
            "event": "",
            "event_type": "",
            "receipt_scope": "none",
            "receipt_source_command": "",
            "receipt_subject_id": "",
            "receipt_event_id": "",
            "receipt_event_type": "",
            "receipt_surface": "legacy_text_scan",
            "receipt_payload_commit": "",
            "receipt_supersedes_or_replaces": "",
            "reentry_condition": "",
        }
    event_match = re.search(r"\b(wie_\d{8}T\d{6}Z_[A-Za-z0-9]+)\b", text or "")
    reentry_condition = ""
    if any(marker in lowered for marker in (
        "replay/merge prerequisite",
        "replay_or_merge_prerequisite",
        "fresh clean-base patch",
        "fresh_clean_base_patch",
        "prerequisite trace-source commits",
    )):
        reentry_condition = "replay_or_merge_prerequisite_trace_source_commits_or_build_fresh_clean_base_patch"
    return {
        "status": "publication_blocker_observed_not_current",
        "receipt": "",
        "event": "",
        "event_type": "",
        "receipt_scope": "none",
        "receipt_source_command": "",
        "receipt_subject_id": "",
        "receipt_event_id": "",
        "receipt_event_type": "",
        "receipt_surface": "legacy_text_scan",
        "receipt_payload_commit": "",
        "receipt_supersedes_or_replaces": "",
        "reentry_condition": reentry_condition,
        "authority_evidence": "legacy_text_observation_only",
        "observed": {
            "subject": publication_cap_ids[0],
            "event": event_match.group(1) if event_match else "",
            "event_type": "",
            "observation_scope": "legacy_text_scan",
            "authority_status": "observed_not_current_receipt",
            "surface": "legacy_text_scan",
            "source_command": "",
            "payload_commit": "",
        },
    }


_CAPSULE_CURRENT_BLOCKER_RECEIPT_SCOPES = {
    "current_task_ledger_authority_receipt",
    "current_task_ledger_authority_query_receipt",
    "current_publication_plan_receipt",
    "current_publication_prepare_receipt",
    "current_publication_publish_receipt",
}


def _capsule_is_current_publication_receipt_scope(evidence_scope: str) -> bool:
    return evidence_scope in _CAPSULE_CURRENT_BLOCKER_RECEIPT_SCOPES


def _capsule_publication_observed_blocker(candidate: Mapping[str, Any]) -> dict[str, str]:
    return {
        "subject": str(candidate.get("receipt") or candidate.get("receipt_subject_id") or ""),
        "event": str(candidate.get("event") or candidate.get("receipt_event_id") or ""),
        "event_type": str(candidate.get("event_type") or candidate.get("receipt_event_type") or ""),
        "observation_scope": str(candidate.get("receipt_scope") or "passive_mention"),
        "authority_status": "observed_not_current_receipt",
        "surface": str(candidate.get("receipt_surface") or "unknown"),
        "source_command": str(candidate.get("receipt_source_command") or ""),
        "payload_commit": str(candidate.get("receipt_payload_commit") or ""),
    }


def _capsule_empty_publication_blocker_receipt(
    *,
    observed: Mapping[str, Any] | None = None,
    reentry_condition: str = "",
) -> dict[str, Any]:
    return {
        "status": "none",
        "receipt": "",
        "event": "",
        "event_type": "",
        "receipt_scope": "none",
        "receipt_source_command": "",
        "receipt_subject_id": "",
        "receipt_event_id": "",
        "receipt_event_type": "",
        "receipt_surface": "none",
        "receipt_payload_commit": "",
        "receipt_supersedes_or_replaces": "",
        "reentry_condition": reentry_condition,
        "authority_evidence": "none",
        "observed": dict(observed or {}),
    }


def _capsule_publication_blocker_receipt_from_payload(
    payload: Mapping[str, Any],
    *,
    command: str,
    evidence_scope: str,
    source_index: int,
) -> dict[str, Any] | None:
    schema = str(payload.get("schema") or payload.get("kind") or "").strip()
    event = payload.get("event") if isinstance(payload.get("event"), Mapping) else {}
    quick_capture = payload.get("quick_capture") if isinstance(payload.get("quick_capture"), Mapping) else {}
    event_payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    direct_payload = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
    receipt_payload: Mapping[str, Any] = event_payload or direct_payload or payload
    subject_id = str(
        event.get("subject_id")
        or payload.get("subject_id")
        or quick_capture.get("subject_id")
        or ""
    ).strip()
    event_id = str(event.get("event_id") or payload.get("event_id") or "").strip()
    event_type = str(event.get("event_type") or payload.get("event_type") or "").strip()
    if not subject_id:
        return None
    haystack = json.dumps(payload, sort_keys=True, default=str).lower() + "\n" + command.lower()
    has_publication_shape = any(marker in haystack for marker in (
        "publication_blocker",
        "publication blocker",
        "publication_lane_plan_v2",
        "clean publication",
        "clean-base replay",
        "clean_base_replay",
        "prerequisite_unpublished_commits_missing",
        "rerun publication_lane prepare",
        "fresh clean-base patch",
    ))
    if not has_publication_shape:
        return None
    score = 0
    if evidence_scope == "current_task_ledger_authority_receipt":
        score += 1000
    elif evidence_scope.startswith("current_"):
        score += 500
    if "quick-capture" in command.lower():
        score += 100
    if schema == "task_ledger_quick_capture_compact_v1":
        score += 50
    if event_id:
        score += 10
    reentry_condition = str(receipt_payload.get("reentry_condition") or "").strip()
    if "include-prerequisite-chain" in reentry_condition or "fresh clean-base patch" in reentry_condition:
        reentry_condition = "rerun_publication_lane_prepare_with_include_prerequisite_chain_or_build_fresh_clean_base_patch"
    payload_commit = str(receipt_payload.get("commit") or receipt_payload.get("source_commit") or "").strip()
    is_current_scope = _capsule_is_current_publication_receipt_scope(evidence_scope)
    authority_status = "current_authority_receipt" if is_current_scope else "observed_not_current_receipt"
    return {
        "status": "publication_blocker_captured" if is_current_scope else "publication_blocker_observed_not_current",
        "receipt": subject_id,
        "event": event_id,
        "event_type": event_type,
        "receipt_scope": evidence_scope,
        "receipt_source_command": f"C{source_index:03d}",
        "receipt_subject_id": subject_id,
        "receipt_event_id": event_id,
        "receipt_event_type": event_type,
        "receipt_surface": schema or "task_ledger_apply",
        "receipt_payload_commit": payload_commit,
        "receipt_supersedes_or_replaces": "",
        "reentry_condition": reentry_condition,
        "authority_evidence": authority_status,
        "authority_status": authority_status,
        "_score": score,
        "_source_index": source_index,
    }


def _capsule_publication_blocker_receipt(
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    final_assistant_text: str,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    observed_candidates: list[dict[str, Any]] = []
    product_state_parts: list[str] = []
    for ev, output_text, _, _ in renderable:
        command = _capsule_clean_text(_capsule_command(ev))
        product_state_parts.append("\n".join(part for part in (command, output_text or "") if part))
        evidence_scope = _capsule_current_evidence_scope(command)
        for payload in _capsule_json_dict_candidates(output_text or ""):
            candidate = _capsule_publication_blocker_receipt_from_payload(
                payload,
                command=command,
                evidence_scope=evidence_scope,
                source_index=ev.index,
            )
            if candidate:
                if _capsule_is_current_publication_receipt_scope(str(candidate.get("receipt_scope") or "")):
                    candidates.append(candidate)
                else:
                    observed_candidates.append(candidate)
    fallback = _capsule_publication_blocker_receipt_from_text(
        "\n".join(part for part in (*product_state_parts, final_assistant_text) if part)
    )
    observed_from_fallback = fallback.get("observed") if isinstance(fallback.get("observed"), Mapping) else {}
    if observed_from_fallback:
        observed_candidates.append({
            "receipt": observed_from_fallback.get("subject") or "",
            "event": observed_from_fallback.get("event") or "",
            "event_type": observed_from_fallback.get("event_type") or "",
            "receipt_scope": observed_from_fallback.get("observation_scope") or "legacy_text_scan",
            "receipt_source_command": observed_from_fallback.get("source_command") or "",
            "receipt_subject_id": observed_from_fallback.get("subject") or "",
            "receipt_event_id": observed_from_fallback.get("event") or "",
            "receipt_event_type": observed_from_fallback.get("event_type") or "",
            "receipt_surface": observed_from_fallback.get("surface") or "legacy_text_scan",
            "receipt_payload_commit": observed_from_fallback.get("payload_commit") or "",
            "status": "publication_blocker_observed_not_current",
            "reentry_condition": fallback.get("reentry_condition") or "",
            "_score": 0,
            "_source_index": -1,
        })
    selected_observed: dict[str, str] = {}
    if observed_candidates:
        observed_selected = dict(max(
            observed_candidates,
            key=lambda row: (int(row.get("_score") or 0), int(row.get("_source_index") or 0)),
        ))
        observed_selected.pop("_score", None)
        observed_selected.pop("_source_index", None)
        selected_observed = _capsule_publication_observed_blocker(observed_selected)
    if candidates:
        selected = dict(max(candidates, key=lambda row: (int(row.get("_score") or 0), int(row.get("_source_index") or 0))))
        selected.pop("_score", None)
        selected.pop("_source_index", None)
        observed_receipt = str(selected_observed.get("subject") or "")
        if observed_receipt and observed_receipt != selected.get("receipt"):
            selected["receipt_supersedes_or_replaces"] = observed_receipt
        if not selected.get("reentry_condition") and fallback.get("reentry_condition"):
            selected["reentry_condition"] = fallback.get("reentry_condition")
        if selected_observed:
            selected["observed"] = selected_observed
        return selected
    return _capsule_empty_publication_blocker_receipt(
        observed=selected_observed,
        reentry_condition=str(fallback.get("reentry_condition") or ""),
    )


def _capsule_nested_string(value: Any, keys: set[str]) -> str:
    stack: list[Any] = [value]
    while stack:
        current = stack.pop(0)
        if isinstance(current, Mapping):
            for key, nested_value in current.items():
                if str(key) in keys and nested_value not in (None, ""):
                    return str(nested_value)
                if isinstance(nested_value, (Mapping, list)):
                    stack.append(nested_value)
        elif isinstance(current, list):
            stack.extend(item for item in current if isinstance(item, (Mapping, list)))
    return ""


def _capsule_work_landing_receipt(
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    final_assistant_text: str,
) -> dict[str, Any]:
    status = "none"
    transaction_id = ""
    task_ledger_receipt = ""
    local_commit = ""
    td_id = ""
    session_id = ""
    owned_paths: list[str] = []
    evidence_rows: list[dict[str, str]] = []
    main_dirty_paths: list[str] = []
    final_lower = (final_assistant_text or "").lower()

    def absorb_payload(payload: Mapping[str, Any], *, evidence_scope: str, source_index: int) -> None:
        nonlocal status, transaction_id, task_ledger_receipt, local_commit, td_id, session_id, owned_paths
        schema = str(payload.get("schema") or payload.get("kind") or "").strip()
        if schema not in {"work_landing_reconcile_cli_compact_v0", "work_landing_status_v0"}:
            return
        evidence_rows.append({
            "schema": schema,
            "evidence_scope": evidence_scope,
            "source_command": f"C{source_index:03d}",
        })
        transaction = payload.get("transaction") if isinstance(payload.get("transaction"), Mapping) else {}
        convergence = payload.get("convergence") if isinstance(payload.get("convergence"), Mapping) else {}
        authority_overlay = (
            payload.get("authority_receipt_overlay")
            if isinstance(payload.get("authority_receipt_overlay"), Mapping)
            else {}
        )
        apply_result = payload.get("apply_result") if isinstance(payload.get("apply_result"), Mapping) else {}

        payload_status = str(
            apply_result.get("status")
            or payload.get("status")
            or convergence.get("status")
            or transaction.get("status")
            or ""
        ).strip()
        if schema == "work_landing_status_v0" and str(convergence.get("status") or "") == "clear":
            status = "converged"
        elif payload_status in {"land_scoped_commit_completed", "closeout_completed", "already_done"}:
            if status != "converged":
                status = "landed"

        transaction_id = transaction_id or str(
            payload.get("transaction_id")
            or apply_result.get("transaction_id")
            or transaction.get("transaction_id")
            or ""
        ).strip()
        local_commit = local_commit or _capsule_nested_string(payload, {"commit_hash", "commit"})
        td_id = td_id or _capsule_nested_string(payload, {"td_id"})
        session_id = session_id or str(
            payload.get("session_id")
            or apply_result.get("session_id")
            or transaction.get("work_ledger_session_id")
            or ""
        ).strip()
        task_ledger_receipt = task_ledger_receipt or _capsule_nested_string(
            payload,
            {"task_ledger_receipt_event_id", "receipt_event_id", "event_id"},
        )
        if not task_ledger_receipt:
            event_ids = authority_overlay.get("event_ids")
            if isinstance(event_ids, list):
                task_ledger_receipt = next((str(item) for item in event_ids if str(item)), "")
        for path in payload.get("owned_paths") or []:
            path_text = str(path).strip()
            if path_text and path_text not in owned_paths:
                owned_paths.append(path_text)

    for ev, output_text, _, _ in renderable:
        command = _capsule_clean_text(_capsule_command(ev))
        evidence_scope = _capsule_current_evidence_scope(command)
        if evidence_scope == "current_main_worktree_status":
            main_dirty_paths = _capsule_git_status_dirty_paths(output_text or "")
        if evidence_scope in {
            "historical_trace_render",
            "historical_source_artifact",
            "historical_git_observation",
            "untrusted_command_output",
        }:
            continue
        for payload in _capsule_json_dict_candidates(output_text or ""):
            absorb_payload(payload, evidence_scope=evidence_scope, source_index=ev.index)

    if status == "none" and "work landing converged" in final_lower:
        status = "converged"
        evidence_rows.append({
            "schema": "final_closeout_text",
            "evidence_scope": "assistant_closeout",
            "source_command": "assistant",
        })
    if not transaction_id:
        match = re.search(r"\b(mtx_[A-Za-z0-9_]+)", final_assistant_text or "")
        if match:
            transaction_id = match.group(1).rstrip(".,;:")
    if not task_ledger_receipt:
        match = re.search(r"\b(wie_[0-9TZ_]+[0-9a-f]{6,})\b", final_assistant_text or "")
        if match:
            task_ledger_receipt = match.group(1).rstrip(".,;:")

    ledger_dirty_paths = [
        path for path in main_dirty_paths
        if path.startswith("codex/ledger/") or path.startswith("state/task_ledger/")
    ]
    if not main_dirty_paths:
        local_authority_dirt = "none"
    elif ledger_dirty_paths and len(ledger_dirty_paths) == len(main_dirty_paths):
        local_authority_dirt = (
            "authority_receipt_local_only"
            if status != "none" or "receipt" in final_lower
            else "authority_receipt_pending"
        )
    elif ledger_dirty_paths:
        local_authority_dirt = "mixed_authority_receipt_tail"
    else:
        local_authority_dirt = "unresolved"

    return {
        "schema_version": "agent_trace_work_landing_receipt_v1",
        "status": status,
        "transaction_id": transaction_id or "",
        "task_ledger_receipt": task_ledger_receipt or "",
        "local_commit": local_commit or "",
        "td_id": td_id or "",
        "session_id": session_id or "",
        "owned_paths": owned_paths,
        "local_authority_dirt": local_authority_dirt,
        "main_dirty_paths": main_dirty_paths,
        "ledger_dirty_paths": ledger_dirty_paths,
        "evidence_rows": evidence_rows,
    }


def _capsule_closeout_reentry_condition_from_text(text: str) -> str:
    lowered = (text or "").lower()
    if "re-entry condition" not in lowered and "reentry condition" not in lowered and "re-entry" not in lowered:
        return ""
    if "selected publication" in lowered and "path-snapshot" in lowered:
        return "selected_publication_path_snapshot_for_clean_commits"
    if "selected-clean" in lowered and "publication" in lowered:
        return "selected_publication_lane_for_divergent_main"
    if "direct broad push unsafe" in lowered or "divergent main" in lowered:
        return "selected_publication_lane_for_divergent_main"
    return ""


def _capsule_session_closeout_receipt(
    *,
    work_landing_receipt: Mapping[str, Any],
    git_publication_trace: Mapping[str, Any],
    local_landed_commit: str,
    source_landing_state: str,
    source_residual_ids: list[str],
    publication_residual_ids: list[str],
    reentry_condition: str,
) -> dict[str, Any]:
    git_remote_publication = str(git_publication_trace.get("git_remote_publication") or "none")
    remote_commit = str(git_publication_trace.get("remote_published_commit") or "")
    target_ref = str(git_publication_trace.get("target_ref") or "")
    replay_relation = git_publication_trace.get("publication_replay_relation")
    replay_mode = ""
    if isinstance(replay_relation, Mapping):
        replay_mode = str(replay_relation.get("replay_mode") or "")
    publication_status = (
        "remote_published"
        if git_remote_publication.startswith("pushed")
        else (
            "selected_publication_required"
            if str(git_publication_trace.get("publication_worktree_state") or "none") == "prepared"
            else ("held" if publication_residual_ids else "none")
        )
    )
    local_authority_dirt = str(work_landing_receipt.get("local_authority_dirt") or "none")
    dirty_state_status = (
        "clean"
        if local_authority_dirt == "none"
        else (
            "owner_routed_or_benign_tail"
            if local_authority_dirt in {"authority_receipt_local_only", "authority_receipt_pending"}
            else "ambiguous"
        )
    )
    dirty_paths = [str(path) for path in work_landing_receipt.get("main_dirty_paths") or [] if str(path)]
    residual_status = (
        "held_with_reentry"
        if reentry_condition
        else ("none" if not source_residual_ids and not publication_residual_ids else "operator_required")
    )
    trace_summary_ready = bool(
        work_landing_receipt.get("status") != "none"
        or publication_status != "none"
        or reentry_condition
    )
    return {
        "schema_version": "session_closeout_receipt_v0",
        "owned_source": {
            "status": "landed" if local_landed_commit else ("clean" if source_landing_state == "source_scope_passed" else "unknown"),
            "local_commit": local_landed_commit or "",
            "owned_paths": list(work_landing_receipt.get("owned_paths") or []),
            "validation_refs": [],
        },
        "dirty_state": {
            "status": dirty_state_status,
            "attention_key": _sha16("\n".join(dirty_paths)) if dirty_paths else "",
            "emitted_to_model": dirty_state_status == "ambiguous",
            "receipt_ref": str(work_landing_receipt.get("task_ledger_receipt") or ""),
            "local_authority_dirt": local_authority_dirt,
        },
        "publication": {
            "status": publication_status,
            "remote_ref": target_ref or "none",
            "remote_commit": remote_commit or "",
            "replay_relation": replay_mode or ("direct_fast_forward" if publication_status == "remote_published" else "none"),
        },
        "work_landing": {
            "status": str(work_landing_receipt.get("status") or "none"),
            "transaction_id": str(work_landing_receipt.get("transaction_id") or ""),
            "task_ledger_receipt": str(work_landing_receipt.get("task_ledger_receipt") or ""),
            "local_authority_dirt": local_authority_dirt,
        },
        "residual": {
            "status": residual_status,
            "reentry_condition": reentry_condition or "",
        },
        "projection": {
            "trace_summary_ready": trace_summary_ready,
            "producer_summary_ready": trace_summary_ready,
            "portable_type_b_ready": None,
            "parser_roundtrip_ready": None,
            "stale_fields": [],
        },
    }


def _capsule_update_session_closeout_projection(
    receipt: dict[str, Any],
    *,
    source_context_readiness: Mapping[str, Any],
    trace_self_parse_receipt: Mapping[str, Any] | None = None,
) -> None:
    projection = receipt.setdefault("projection", {})
    if not isinstance(projection, dict):
        projection = {}
        receipt["projection"] = projection
    producer_summary_ready = bool(projection.get("producer_summary_ready", projection.get("trace_summary_ready")))
    source_context_green = str(source_context_readiness.get("overall") or "green") == "green"
    parser_ready: bool | None = None
    if trace_self_parse_receipt is not None:
        parser_ready = _capsule_parser_roundtrip_readiness(trace_self_parse_receipt) == "green"
    stale_fields: list[str] = []
    if not source_context_green:
        stale_fields.append("portable_type_b_ready")
    if parser_ready is False:
        stale_fields.append("parser_roundtrip_ready")
    projection.update({
        "trace_summary_ready": producer_summary_ready,
        "producer_summary_ready": producer_summary_ready,
        "portable_type_b_ready": source_context_green,
        "parser_roundtrip_ready": parser_ready,
        "stale_fields": stale_fields,
    })


def _capsule_session_closeout_receipt_summary(receipt: Mapping[str, Any]) -> str:
    owned_source = receipt.get("owned_source") if isinstance(receipt.get("owned_source"), Mapping) else {}
    work_landing = receipt.get("work_landing") if isinstance(receipt.get("work_landing"), Mapping) else {}
    publication = receipt.get("publication") if isinstance(receipt.get("publication"), Mapping) else {}
    dirty_state = receipt.get("dirty_state") if isinstance(receipt.get("dirty_state"), Mapping) else {}
    residual = receipt.get("residual") if isinstance(receipt.get("residual"), Mapping) else {}
    projection = receipt.get("projection") if isinstance(receipt.get("projection"), Mapping) else {}
    return (
        f"schema={receipt.get('schema_version') or 'session_closeout_receipt_v0'} "
        f"owned_source={owned_source.get('status') or 'unknown'} "
        f"work_landing={work_landing.get('status') or 'none'} "
        f"publication={publication.get('status') or 'none'} "
        f"dirty_state={dirty_state.get('status') or 'unknown'} "
        f"local_authority_dirt={work_landing.get('local_authority_dirt') or 'none'} "
        f"residual={residual.get('status') or 'none'} "
        f"trace_summary_ready={projection.get('trace_summary_ready')} "
        f"producer_summary_ready={projection.get('producer_summary_ready')} "
        f"portable_type_b_ready={projection.get('portable_type_b_ready')} "
        f"parser_roundtrip_ready={projection.get('parser_roundtrip_ready')}"
    )


def _capsule_residual_is_projection_artifact(residual_id: str) -> bool:
    if not residual_id:
        return False
    lowered = residual_id.lower()
    return lowered.endswith(_CAPSULE_PROJECTION_ARTIFACT_SUFFIXES)


def _capsule_residual_is_validation_process(residual_id: str, item: dict | None) -> bool:
    fields = [residual_id]
    if isinstance(item, dict):
        fields.extend(str(value) for value in (
            item.get("title"),
            item.get("state"),
            item.get("work_item_type"),
            item.get("candidate_work_item_type"),
        ) if value)
        tags = item.get("tags")
        if isinstance(tags, list):
            fields.extend(str(tag) for tag in tags)
    text = " ".join(fields).lower()
    return any(token in text for token in (
        "validation_process",
        "pytest_wrapper",
        "wrapper_hung",
        "wrapper hung",
        "self_error",
        "process",
        "serial_mutation",
        "validation runner",
    ))


def _capsule_residual_is_external_observation_blocker(item: dict | None) -> bool:
    if not isinstance(item, dict):
        return False
    if str(item.get("state") or item.get("status") or "").lower() != "blocked":
        return False

    fields: list[str] = []
    for key in (
        "id",
        "title",
        "statement",
        "problem",
        "impact",
        "acceptance",
        "blocked_reason",
        "blocking_condition",
    ):
        value = item.get(key)
        if value:
            fields.append(str(value))
    tags = item.get("tags")
    if isinstance(tags, list):
        fields.extend(str(tag) for tag in tags if tag)
    satisfaction_contract = item.get("satisfaction_contract")
    if isinstance(satisfaction_contract, dict):
        for key in ("reentry_condition", "definition_of_done"):
            value = satisfaction_contract.get(key)
            if isinstance(value, list):
                fields.extend(str(part) for part in value if part)
            elif value:
                fields.append(str(value))
    provenance = item.get("provenance")
    if isinstance(provenance, dict):
        value = provenance.get("source_kind")
        if value:
            fields.append(str(value))

    text = " ".join(fields).lower()
    has_observation_shape = any(token in text for token in (
        "residual_observation",
        "natural market",
        "market-fire",
        "market fire",
        "wall-clock",
        "clock tick",
        "next eligible",
        "next natural",
    ))
    has_external_wait = any(token in text for token in (
        "blocked on",
        "reentry_condition",
        "next eligible",
        "wall-clock",
        "clock tick",
        "future natural",
        "after the first natural",
        "next natural",
    ))
    return has_observation_shape and has_external_wait


def _capsule_residual_taxonomy(rows: Iterable[CapsuleEvidenceClassification]) -> CapsuleResidualTaxonomy:
    buckets: dict[str, set[str]] = {
        "open_product_residuals": set(),
        "open_validation_process_residuals": set(),
        "closed_residuals_seen": set(),
        "blocked_external_observation_residuals": set(),
        "projection_or_view_artifacts_seen": set(),
        "unresolved_residual_mentions": set(),
        "passive_residual_mentions_observed": set(),
    }
    ledger_items = _capsule_task_ledger_work_items()
    for row in rows:
        residual_ids = row.residual_ids or ((row.residual_id,) if row.residual_id else ())
        if row.evidence_scope in {
            "historical_trace_render",
            "historical_source_artifact",
            "historical_git_observation",
            "untrusted_command_output",
        } or row.workspace_role == "historical_trace_artifact":
            buckets["passive_residual_mentions_observed"].update(residual_ids)
            continue
        if row.bucket == "diagnostic":
            continue
        for residual_id in residual_ids:
            if _capsule_residual_is_projection_artifact(residual_id):
                buckets["projection_or_view_artifacts_seen"].add(residual_id)
                continue
            item = ledger_items.get(residual_id)
            state = str(item.get("state") or "").lower() if isinstance(item, dict) else ""
            if state in _CAPSULE_CLOSED_RESIDUAL_STATES:
                buckets["closed_residuals_seen"].add(residual_id)
            elif isinstance(item, dict):
                if _capsule_residual_is_validation_process(residual_id, item):
                    buckets["open_validation_process_residuals"].add(residual_id)
                elif _capsule_residual_is_external_observation_blocker(item):
                    buckets["blocked_external_observation_residuals"].add(residual_id)
                else:
                    buckets["open_product_residuals"].add(residual_id)
            elif residual_id in _CAPSULE_KNOWN_RESIDUAL_IDS:
                buckets["open_product_residuals"].add(residual_id)
            else:
                buckets["unresolved_residual_mentions"].add(residual_id)
    return CapsuleResidualTaxonomy(
        open_product_residuals=tuple(sorted(buckets["open_product_residuals"])),
        open_validation_process_residuals=tuple(sorted(buckets["open_validation_process_residuals"])),
        closed_residuals_seen=tuple(sorted(buckets["closed_residuals_seen"])),
        blocked_external_observation_residuals=tuple(sorted(buckets["blocked_external_observation_residuals"])),
        projection_or_view_artifacts_seen=tuple(sorted(buckets["projection_or_view_artifacts_seen"])),
        unresolved_residual_mentions=tuple(sorted(buckets["unresolved_residual_mentions"])),
        passive_residual_mentions_observed=tuple(sorted(buckets["passive_residual_mentions_observed"])),
    )


def _capsule_passive_residual_mentions(
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    *,
    prompt_text: str,
) -> tuple[str, ...]:
    passive: list[str] = list(_capsule_residual_ids("", prompt_text or ""))
    for ev, output_text, _, _ in renderable:
        command = _capsule_clean_text(_capsule_command(ev))
        evidence_scope = _capsule_current_evidence_scope(command)
        if evidence_scope in {
            "historical_trace_render",
            "historical_source_artifact",
            "historical_git_observation",
            "untrusted_command_output",
        }:
            passive.extend(_capsule_residual_ids(command, output_text or ""))
    return _capsule_ordered_unique(passive)


def _capsule_selected_window_unresolved_residual_ids(text: str) -> tuple[str, ...]:
    markers = (
        "unresolved",
        "still open",
        "remains open",
        "remaining residual",
        "open residual",
        "not closed",
    )
    residual_ids: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        normalized = re.sub(r"^\s*(?:[+\-]\s*)?(?:[|>]\s*)+", "", stripped).strip()
        projection_key = re.match(r"^([A-Za-z0-9_.-]+)\s*(?::|=|==)\s*", normalized)
        if projection_key and any(
            token in projection_key.group(1).lower()
            for token in (
                "residual",
                "validation",
                "publication",
                "release",
                "receipt",
                "source_landing",
                "taxonomy",
            )
        ):
            continue
        if normalized.startswith((
            "$ ",
            "assert ",
            "CSM",
            "N",
            "L",
            "CapsuleEvidenceClassification(",
            "taxonomy ",
            "item ",
        )):
            continue
        lowered = normalized.lower()
        if not any(marker in lowered for marker in markers):
            continue
        residual_ids.extend(_capsule_residual_ids("", normalized))
    return _capsule_ordered_unique(residual_ids)


def _capsule_pytest_wrapper_passed_then_failed(command: str, output_text: str) -> bool:
    text = f"{command}\n{output_text}".lower()
    if "pytest" not in text:
        return False
    if not re.search(r"\b\d+\s+passed\b", text):
        return False
    if re.search(r"\b\d+\s+failed\b|\bfailures?\b", text):
        return False
    return any(marker in text for marker in (
        "wrapper hung",
        "hung after printing pass",
        "process running with session id",
        "timed out",
        "timeout",
        "killed",
        "interrupted",
        "exit code -1",
    ))


def _capsule_validation_process_tempfail(command: str, output_text: str) -> bool:
    text = f"{command}\n{output_text}".lower()
    if (
        ("admission_consumer" in text or "host_pressure" in text)
        and any(marker in text for marker in (
            "frontend_vitest_host_pressure_admission_blocked",
            "host_pressure_queue_until_pressure_clears",
            "queue_validation_until_host_pressure_clears",
            '"tempfail_exit_code": 75',
            '"new_work_admitted": false',
        ))
    ):
        return True
    validation_command = any(marker in text for marker in (
        "pytest",
        "repo-pytest",
        "npm run test",
        "node --test",
        "vitest",
        "swift test",
        "make ci",
        "make test",
    ))
    closed_stdin_transport = any(marker in text for marker in (
        "write_stdin failed",
        "failed to write to stdin",
        "stdin closed",
        "stdin is closed",
        "stdin was closed",
    ))
    return validation_command and closed_stdin_transport


def _capsule_expected_mcp_owner_fan_in_refusal(command: str, output_text: str) -> bool:
    text = f"{command}\n{output_text}".lower()
    if "mutation_control_owner_fan_in_required" not in text:
        return False
    if not any(marker in text for marker in (
        "scoped_commit.py",
        "scoped-commit",
        "scoped_commit_mutation_control_refusal_v0",
        "mutation_control_refusal_json",
    )):
        return False
    return any(marker in text for marker in (
        "fan_in_or_watch",
        "owner_fan_in_required",
        "owner_fan_in_packet_v0",
        "work ledger active claim overlap",
    ))


def _capsule_expected_guarded_refusal(command: str, output_text: str) -> bool:
    if _capsule_expected_mcp_owner_fan_in_refusal(command, output_text):
        return True
    text = f"{command}\n{output_text}".lower()
    if (
        _CAPSULE_SUBSTRATE_SUBSTITUTION_LEDGER_MODULE not in text
        and "substrate_substitution_ledger" not in text
    ):
        return False
    if not any(status in text for status in (
        "blocked_unrelated_rebuild_drift",
        "blocked_unconfirmed_rebuild_drift",
    )):
        return False
    if not any(schema in text for schema in (
        "microcosm_substrate_substitution_write_result_v1",
        "microcosm_substrate_substitution_writer_drift_v1",
    )):
        return False
    if "microcosm_substrate_substitution_write_result_v1" in text:
        write_refused = any(marker in text for marker in (
            '"write_performed": false',
            '"write_performed":false',
            "'write_performed': false",
            "write_performed=false",
        ))
        if not write_refused:
            return False
    return "writer_guard" in text or "writer_drift" in text


def _capsule_ambient_warning_class(command: str, output_text: str) -> str:
    text = f"{command}\n{output_text}"
    lowered = text.lower()
    if (
        ("build_paper_module_index.py" in lowered or "paper_module_index" in lowered)
        and any(marker in lowered for marker in (
            "source_coupling",
            "source coupling",
            "clean_source_inputs_and_artifacts",
            "source_inputs_clean",
        ))
        and any(marker in lowered for marker in (
            "generated surfaces",
            "generated_surfaces",
            "projection_freshness",
            "freshness_status",
            "in_sync",
        ))
        and any(marker in lowered for marker in (
            "ambient",
            "corpus queue",
            "corpus_queue",
            "queued",
            "queue_count",
        ))
    ):
        return "paper_module_ambient_corpus_debt"
    if (
        ("git_gc_maintenance.py" in lowered or "git_gc_maintenance_v0" in lowered)
        and "git_gc_maintenance_v0" in lowered
        and "repair_reentry" in lowered
        and any(marker in lowered for marker in (
            "blocked_git_lockfile_or_process",
            "blocked_recent_tmp_objects",
            "blocked_insufficient_scratch",
            '"maintenance_admission": "blocked',
            '"maintenance_admission":"blocked',
            '"repair_status": "blocked_',
            '"repair_status":"blocked_',
            '"ready_to_repair": false',
            '"ready_to_repair":false',
        ))
    ):
        return "git_maintenance_admission_residual"
    if "task_ledger_apply.py" not in lowered or "validate" not in lowered:
        return ""
    if "valid_with_warnings" not in lowered:
        return ""
    zero_error_markers = (
        '"error_count": 0',
        '"errors": 0',
        "error_count=0",
        "errors=0",
        "0 errors",
    )
    if not any(marker in lowered for marker in zero_error_markers):
        return ""
    if (
        "historical_evidence_durability_backlog" in lowered
        or ("evidence" in lowered and "durability" in lowered)
    ):
        return "historical_evidence_durability_backlog"
    return "external_validation_warning"


_CAPSULE_PROJECTION_ASSIMILATION_SUMMARY_CLASSES = {
    "task_ledger_projection_deferred_queued": "projection_deferred_queued",
    "task_ledger_projection_rebuild_failed": "projection_rebuild_failed",
    "task_ledger_projection_checked": "projection_checked",
    "task_ledger_projection_not_rebuilt": "projection_not_rebuilt",
    "task_ledger_projection_assimilation_observed": "projection_observed",
}


def _capsule_projection_assimilation_class(command: str, output_text: str) -> str:
    text = f"{command}\n{output_text}"
    lowered = text.lower()
    if "task_ledger_apply.py" not in lowered:
        return ""
    if "projection_assimilation_state" not in lowered:
        return ""
    if "task_ledger_projection_assimilation_state_v1" not in lowered:
        return ""
    if (
        "projection_rebuild_deferred" in lowered
        or "authority_appended_projection_rebuild_deferred" in lowered
        or '"queued": true' in lowered
        or '"queued":true' in lowered
        or '"status": "queued"' in lowered
        or '"status":"queued"' in lowered
    ):
        return "task_ledger_projection_deferred_queued"
    if (
        "projection_rebuild_failed" in lowered
        or '"status": "failed"' in lowered
        or '"status":"failed"' in lowered
        or '"projection_rebuild_status": "failed"' in lowered
        or '"projection_rebuild_status":"failed"' in lowered
    ):
        return "task_ledger_projection_rebuild_failed"
    if (
        "projection_rebuild_checked" in lowered
        or "projection_checked" in lowered
        or '"status": "checked"' in lowered
        or '"status":"checked"' in lowered
    ):
        return "task_ledger_projection_checked"
    if (
        "projection_not_rebuilt" in lowered
        or "not_rebuilt" in lowered
        or '"rebuilt": false' in lowered
        or '"rebuilt":false' in lowered
    ):
        return "task_ledger_projection_not_rebuilt"
    return "task_ledger_projection_assimilation_observed"


def _capsule_projection_assimilation_summary(rows: Iterable[CapsuleEvidenceClassification]) -> str:
    for class_name in _CAPSULE_PROJECTION_ASSIMILATION_SUMMARY_CLASSES:
        if any(row.validation_class == class_name for row in rows):
            return _CAPSULE_PROJECTION_ASSIMILATION_SUMMARY_CLASSES[class_name]
    return ""


def _capsule_governance_validation_class(command: str, output_text: str) -> str:
    text = f"{command}\n{output_text}"
    lowered = text.lower()
    if _capsule_expected_mcp_owner_fan_in_refusal(command, output_text):
        return "expected_guarded_refusal"
    if "run_git.py" in lowered and "audit" in lowered and "push" in lowered and (
        '"direct_push_allowed": false' in lowered
        or '"direct_push_allowed":false' in lowered
        or '"status": "watch"' in lowered
        or '"status":"watch"' in lowered
        or "direct_push_allowed=false" in lowered
        or "next_safe_command=null" in lowered
        or '"next_safe_command": null' in lowered
        or '"next_safe_command":null' in lowered
    ):
        return "publication_hold"
    if "task_ledger_apply.py" in lowered:
        projection_class = _capsule_projection_assimilation_class(command, output_text)
        if projection_class:
            return projection_class
        if "enqueue-execution-receipt" in lowered or "intake-status" in lowered:
            if (
                '"_intake_status": "pending"' in lowered
                or '"_intake_status":"pending"' in lowered
                or '"state": "pending"' in lowered
                or '"state":"pending"' in lowered
                or '"status": "intake_replaced_pending"' in lowered
                or '"status":"intake_replaced_pending"' in lowered
                or '"status": "intake_queued_pending"' in lowered
                or '"status":"intake_queued_pending"' in lowered
                or '"pending": 1' in lowered
                or '"pending":1' in lowered
            ):
                return "receipt_intake_pending"
        if "drain-intake" in lowered or "intake-status" in lowered:
            if (
                '"_intake_status": "applied"' in lowered
                or '"_intake_status":"applied"' in lowered
                or '"state": "applied"' in lowered
                or '"state":"applied"' in lowered
            ):
                return "receipt_intake_applied"
    return ""


def _capsule_publication_check_kind(command: str, output_text: str = "") -> str:
    text = f"{command}\n{output_text}".lower()
    if "deploy_plectis_site.py" in text or (
        "gh-pages" in text and "deploy" in text and any(marker in text for marker in ("commit", "published", "built"))
    ):
        return "publication_deploy_receipt"
    if "wcook04.github.io/plectis" in text or (
        "plectis" in text and "host verification" in text
    ):
        return "publication_host_verification"
    if any(marker in text for marker in ("gh api", "gh run", "github pages")) and any(
        marker in text
        for marker in (
            "pages",
            "deployment",
            "deployments",
            "pages/builds",
            "actions/runs",
            "gh-pages",
            "pages build",
        )
    ):
        return "publication_status_poll"
    return ""


_CAPSULE_PUBLICATION_WORKTREE_RE = re.compile(
    r"(?P<path>/(?:private/)?tmp/aiw-publication-[^\s\"'`,;)]+)",
)


def _capsule_publication_worktree_path(command: str, output_text: str = "") -> str:
    text = f"{command}\n{output_text}"
    match = _CAPSULE_PUBLICATION_WORKTREE_RE.search(text)
    if not match:
        return ""
    return match.group("path").rstrip(".,;:")


def _capsule_validation_workspace_role(bucket: str, command: str, output_text: str = "") -> str:
    text = f"{command}\n{output_text}"
    lowered = text.lower()
    publication_worktree = _capsule_publication_worktree_path(command, output_text)
    if publication_worktree:
        if any(marker in lowered for marker in (
            "conflict_paths",
            "selected_commits_do_not_apply_cleanly",
            "retained_conflict",
            "retained worktree",
            "worktree_retained",
            "\nuu ",
        )):
            return "retained_conflict_worktree"
        return "detached_publication_worktree"
    if _capsule_output_is_nested_trace(output_text):
        return "historical_trace_artifact"
    if "task_ledger_apply.py" in lowered or "state/task_ledger/" in lowered:
        return "sidecar_source"
    if bucket in {"check", "governance"}:
        return "main_worktree"
    return "none"


def _capsule_validation_subject(
    command: str,
    output_text: str,
    *,
    workspace_role: str,
) -> str:
    publication_worktree = _capsule_publication_worktree_path(command, output_text)
    if publication_worktree:
        return f"worktree:{publication_worktree}"
    text = f"{command}\n{output_text}"
    target_match = re.search(r"--target-ref\s+([^\s]+)|\"target_ref\"\s*:\s*\"([^\"]+)\"", text)
    if target_match:
        return f"target_ref:{(target_match.group(1) or target_match.group(2) or '').strip()}"
    commit_match = re.search(
        r"(?:--commit|new_commit|replay_source_commit|pushed_commit|prepared_commit)\"?\s*(?:[:=]\s*)?\"?([0-9a-f]{7,40})",
        text,
        re.I,
    )
    if commit_match:
        return f"commit:{commit_match.group(1)}"
    if workspace_role == "main_worktree":
        return "worktree:main"
    return "unknown"


def _capsule_validation_domain(
    *,
    bucket: str,
    validation_class: str,
    command: str,
    output_text: str,
    workspace_role: str,
) -> str:
    text = f"{command}\n{output_text}".lower()
    if workspace_role in {"detached_publication_worktree", "retained_conflict_worktree"}:
        return "publication_candidate"
    if "publication_lane.py" in text and "prepare" in text:
        return "publication_candidate"
    if "publication_lane.py" in text and "publish" in text:
        return "git_remote_publication"
    if "run_git.py" in text and "push" in text:
        return "git_remote_publication"
    if validation_class in {"publication_deploy_receipt", "publication_host_verification", "publication_status_poll"}:
        return "external_public_release"
    if validation_class == "ambient_validation_warning":
        return "ambient_diagnostic"
    if validation_class == "validation_process_warning":
        return "command_sanity"
    if validation_class == "expected_guarded_refusal":
        return "command_sanity"
    if bucket == "diagnostic":
        return "ambient_diagnostic"
    if bucket == "check":
        return "source_landing"
    if bucket == "governance":
        return "source_landing"
    return "unknown"


def _capsule_validation_gate_effect(
    *,
    result: str,
    validation_domain: str,
    validation_class: str,
) -> str:
    if validation_class == "expected_guarded_refusal":
        return "expected_refusal"
    if validation_domain in {"ambient_diagnostic", "command_sanity"}:
        return "nonblocking_diagnostic"
    if result != "fail":
        return "ambient"
    if validation_domain in {"source_landing", "source_context_bundle"}:
        return "blocks_source_landing"
    if validation_domain in {"publication_candidate", "git_remote_publication"}:
        return "blocks_git_remote_publication"
    if validation_domain == "external_public_release":
        return "blocks_external_release"
    return "ambient"


def _capsule_validation_class(
    bucket: str,
    result: str,
    command: str,
    output_text: str,
    ambient_warning_class: str = "",
) -> str:
    text = f"{command}\n{output_text}".lower()
    if ambient_warning_class:
        return "ambient_validation_warning"
    if bucket == "governance":
        governance_class = _capsule_governance_validation_class(command, output_text)
        if governance_class:
            return governance_class
        if "task_ledger_apply.py" in text and any(token in text for token in ("quick-capture", " capture", "cap_")):
            return "captured_residual"
        return "governance_actuator_result"
    if bucket == "diagnostic":
        return "exploratory_diagnostic_failure" if result == "fail" else "exploratory_diagnostic"
    if bucket != "check":
        return "unclassified"
    publication_kind = _capsule_publication_check_kind(command, output_text)
    if publication_kind:
        return publication_kind
    if result != "fail":
        return "scoped_validation_pass" if result == "pass" else "scoped_validation_other"
    if _capsule_expected_guarded_refusal(command, output_text):
        return "expected_guarded_refusal"
    if _capsule_validation_process_tempfail(command, output_text):
        return "validation_process_warning"
    if _capsule_pytest_aggregate_collection_conflict(command, output_text):
        return "aggregate_selector_conflict"
    stale_selector_markers = (
        "not found:",
        "no tests ran",
        "collected 0 items",
        "file or directory not found",
        "error: not found",
        "empty suite",
    )
    if any(marker in text for marker in stale_selector_markers):
        return "stale_selector_retry"
    if "build_standard_skill_map.py" in text or "standard_skill_map" in text:
        return "out_of_scope_discoverability_failure"
    if _capsule_pytest_wrapper_passed_then_failed(command, output_text):
        return "validation_process_warning"
    return "scoped_validation_failure"


_CAPSULE_RELEASE_AUTHORIZED_TRUE_RE = re.compile(
    r"\brelease_authorized\b[`'\"\s:=_-]*true\b",
    re.I,
)


def _capsule_has_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _capsule_public_release_blocked_by_github_pvr(text: str) -> bool:
    lowered = (text or "").lower()
    has_pvr_gate = _capsule_has_any_marker(
        lowered,
        (
            "github_private_vulnerability_reporting",
            "github private vulnerability reporting",
            "private-vulnerability-reporting",
        ),
    )
    has_pvr_blocker = _capsule_has_any_marker(
        lowered,
        (
            "public_repository_absent",
            "public_repository_required",
            "github_pvr_not_enabled",
            "github_pvr_enable_failed",
            "github_private_vulnerability_reporting_not_green",
            "not yet green for the public microcosm repository",
            "blocks_public_release_until_public_repo_exists_and_github_pvr_is_enabled",
        ),
    )
    target_is_microcosm = _capsule_has_any_marker(
        lowered,
        (
            "wcook04/microcosm-substrate",
            "repos/wcook04/microcosm-substrate/private-vulnerability-reporting",
            "github.com/wcook04/microcosm-substrate",
        ),
    )
    return has_pvr_gate and has_pvr_blocker and target_is_microcosm


def _capsule_release_candidate_gate_decision(text: str) -> str:
    lowered = (text or "").lower()
    if _capsule_public_release_blocked_by_github_pvr(lowered):
        return "public_release_blocked"
    if "ready_pending_operator_authorization" not in lowered:
        return ""
    if _CAPSULE_RELEASE_AUTHORIZED_TRUE_RE.search(text or ""):
        return ""

    release_authority_false = any(
        marker in lowered
        for marker in (
            '"release_authorized": false',
            "'release_authorized': false",
            "release_authorized=false",
            "release_authorized remains false",
            "release_authorized` remains false",
        )
    )
    clean_source = any(
        marker in lowered
        for marker in (
            '"source_tree_state": "git_head_clean"',
            '"source_tree_state_kind": "git_head_clean"',
            "source_tree_state=git_head_clean",
            "clean git head",
            "clean-source",
            "clean source",
        )
    )
    dirty_count_zero = any(
        marker in lowered
        for marker in (
            '"dirty_source_path_count": 0',
            "'dirty_source_path_count': 0",
            "dirty_source_path_count=0",
            "dirty source count `0`",
            "dirty source count 0",
        )
    )
    projection_pass = any(
        marker in lowered
        for marker in (
            '"projection_freshness_status": "pass"',
            "'projection_freshness_status': 'pass'",
            '"projection_freshness": "pass"',
            "projection freshness `pass`",
            "projection freshness pass",
            "projection_freshness_status=pass",
        )
    )
    if release_authority_false and clean_source and dirty_count_zero and projection_pass:
        internal_authorization_satisfied = _capsule_has_any_marker(
            lowered,
            (
                "internal authorization satisfied",
                "internal authorization settlement",
                "standing internal authorization",
                "standing private/internal authorization",
                "private/internal authorization",
                "private/internal default yes",
                "default yes for private/internal",
                "private/local/internal",
                "internal/private work",
                "private lane",
                "systembar_slice_internal_authorization_satisfied_public_blocked",
            ),
        )
        public_release_blocked = _capsule_has_any_marker(
            lowered,
            (
                "public release remains blocked",
                "public release blocked",
                "public_blocked",
                "public blocked",
                "public release still explicitly not authorized",
                "public release remains explicitly not authorized",
                "public_release_authorization: not_authorized_by_operator",
                "not_authorized_by_operator",
                "no public push",
                "no public deploy",
                "no public release toggle",
                "no public action was taken",
            ),
        )
        if internal_authorization_satisfied and public_release_blocked:
            return "not_authorized_by_operator"
        return "ready_pending_operator_authorization"
    return ""


def _capsule_evidence_classification(
    command: str,
    role: str,
    exit_code: int | None,
    is_error: bool,
    output_text: str = "",
) -> CapsuleEvidenceClassification | None:
    bucket, label, identity = _capsule_command_bucket_and_label(command, role)
    if not bucket:
        return None
    result = _capsule_evidence_result(bucket, exit_code, is_error, output_text)
    ambient_warning_class = _capsule_ambient_warning_class(command, output_text)
    residual_ids = _capsule_residual_ids(command, output_text)
    validation_obligation_ids = _capsule_pytest_node_ids(command, output_text)
    validation_file_selectors = _capsule_pytest_file_selectors(command)
    validation_class = _capsule_validation_class(
        bucket,
        result,
        command,
        output_text,
        ambient_warning_class,
    )
    workspace_role = _capsule_validation_workspace_role(bucket, command, output_text)
    validation_subject = _capsule_validation_subject(
        command,
        output_text,
        workspace_role=workspace_role,
    )
    validation_domain = _capsule_validation_domain(
        bucket=bucket,
        validation_class=validation_class,
        command=command,
        output_text=output_text,
        workspace_role=workspace_role,
    )
    gate_effect = _capsule_validation_gate_effect(
        result=result,
        validation_domain=validation_domain,
        validation_class=validation_class,
    )
    evidence_scope = _capsule_current_evidence_scope(command)
    return CapsuleEvidenceClassification(
        bucket=bucket,
        result=result,
        label=label,
        identity=identity,
        evidence_scope=evidence_scope,
        validation_class=validation_class,
        residual_id=residual_ids[0] if residual_ids else "",
        residual_ids=residual_ids,
        ambient_warning_class=ambient_warning_class,
        validation_obligation_ids=validation_obligation_ids,
        validation_file_selectors=validation_file_selectors,
        validation_domain=validation_domain,
        validation_subject=validation_subject,
        workspace_role=workspace_role,
        gate_effect=gate_effect,
    )


def _capsule_result_counts(rows: list[CapsuleEvidenceClassification]) -> tuple[int, int, int]:
    pass_count = sum(1 for row in rows if row.result == "pass")
    fail_count = sum(1 for row in rows if row.result == "fail")
    other_count = max(0, len(rows) - pass_count - fail_count)
    return pass_count, fail_count, other_count


def _capsule_terminal_rows(rows: list[CapsuleEvidenceClassification]) -> list[CapsuleEvidenceClassification]:
    by_identity: dict[str, CapsuleEvidenceClassification] = {}
    for row in rows:
        by_identity[row.identity] = row
    return list(by_identity.values())


_CAPSULE_AGGREGATE_VALIDATION_PROOF_MARKERS = (
    "make ci",
    "make smoke",
    "make package-smoke",
    "microcosm_core.cli crown-jewel-demo run",
    "microcosm_core.projections.organ_surface_contract",
    "build_organ_atlas.py",
)

_CAPSULE_PYTEST_NODE_ID_RE = re.compile(
    r"(?P<node>(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.py::[^\s]+)"
)
_CAPSULE_PYTEST_PARTIAL_SELECTION_FLAGS = {
    "-k",
    "-m",
    "--lf",
    "--last-failed",
    "--failed-first",
    "--deselect",
    "--ignore",
    "--ignore-glob",
    "--collect-only",
}


def _capsule_normalize_test_path(path: str) -> str:
    return re.sub(r"^\./+", "", path.strip())


def _capsule_pytest_surface_argvs(command: str) -> list[list[str]]:
    surfaces: list[list[str]] = []
    for argv in _capsule_command_surface_argvs(command):
        if not argv:
            continue
        exe = Path(argv[0]).name
        script, script_args, _ = _capsule_script_surface(argv)
        script_base = Path(script).name
        if exe in {"pytest", "repo-pytest"}:
            surfaces.append(argv)
        elif "pytest" in script_base:
            surfaces.append([script, *script_args])
    return surfaces


def _capsule_pytest_node_ids(command: str, output_text: str) -> tuple[str, ...]:
    text = "\n".join(part for part in (command, output_text) if part)
    nodes = {
        _capsule_normalize_test_path(match.group("node").rstrip(".,;:"))
        for match in _CAPSULE_PYTEST_NODE_ID_RE.finditer(text)
    }
    return tuple(sorted(nodes))


def _capsule_pytest_file_selectors(command: str) -> tuple[str, ...]:
    selectors: set[str] = set()
    for argv in _capsule_pytest_surface_argvs(command):
        args = argv[1:]
        lowered = {arg.lower().split("=", 1)[0] for arg in args}
        if any(flag in lowered for flag in _CAPSULE_PYTEST_PARTIAL_SELECTION_FLAGS):
            continue
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg in {">", ">>", "2>", "2>>", "2>&1"}:
                break
            if arg.startswith("-"):
                if arg in {"--rootdir", "--basetemp", "--confcutdir"} and "=" not in arg:
                    skip_next = True
                continue
            candidate = arg.split("::", 1)[0]
            if candidate.endswith(".py") and "::" not in arg:
                selectors.add(_capsule_normalize_test_path(candidate))
    return tuple(sorted(selectors))


_CAPSULE_PYTEST_AGGREGATE_COLLECTION_CONFLICT_MARKERS = (
    "import file mismatch",
    "importmismatcherror",
    "imported module",
    "has this __file__ attribute",
    "which is not the same as the test file we want to collect",
    "collection failure",
    "error collecting",
)


def _capsule_pytest_aggregate_collection_conflict(command: str, output_text: str) -> bool:
    if len(_capsule_pytest_file_selectors(command)) < 2:
        return False
    text = f"{command}\n{output_text}".lower()
    if "pytest" not in text:
        return False
    return any(
        marker in text
        for marker in _CAPSULE_PYTEST_AGGREGATE_COLLECTION_CONFLICT_MARKERS
    )


def _capsule_is_aggregate_validation_proof(row: CapsuleEvidenceClassification) -> bool:
    if row.bucket != "check" or row.result != "pass":
        return False
    text = f"{row.identity} {row.label}".lower()
    return any(marker in text for marker in _CAPSULE_AGGREGATE_VALIDATION_PROOF_MARKERS)


def _capsule_later_aggregate_recovery_failures(
    check_rows: list[CapsuleEvidenceClassification],
    terminal_failures: list[CapsuleEvidenceClassification],
) -> list[CapsuleEvidenceClassification]:
    stale: list[CapsuleEvidenceClassification] = []
    for failure in terminal_failures:
        failure_index = -1
        for index, row in enumerate(check_rows):
            if row.identity == failure.identity:
                failure_index = index
        if failure_index < 0:
            continue
        later_proof = any(
            _capsule_is_aggregate_validation_proof(row)
            for row in check_rows[failure_index + 1:]
        )
        if later_proof:
            stale.append(failure)
    return stale


def _capsule_later_selector_recovery_failures(
    check_rows: list[CapsuleEvidenceClassification],
    terminal_failures: list[CapsuleEvidenceClassification],
) -> list[CapsuleEvidenceClassification]:
    recovered: list[CapsuleEvidenceClassification] = []
    for failure in terminal_failures:
        failure_index = -1
        for index, row in enumerate(check_rows):
            if row.identity == failure.identity:
                failure_index = index
        if failure_index < 0:
            continue

        failure_nodes = set(failure.validation_obligation_ids)
        failure_paths = {
            node.split("::", 1)[0]
            for node in failure_nodes
            if "::" in node
        }
        failure_paths.update(failure.validation_file_selectors)
        if not failure_nodes and not failure_paths:
            continue

        for proof in check_rows[failure_index + 1:]:
            if proof.bucket != "check" or proof.result != "pass":
                continue
            proof_nodes = set(proof.validation_obligation_ids)
            proof_file_selectors = set(proof.validation_file_selectors)
            if failure_nodes and failure_nodes.intersection(proof_nodes):
                recovered.append(failure)
                break
            if failure_paths and failure_paths.issubset(proof_file_selectors):
                recovered.append(failure)
                break
    return recovered


def _capsule_later_split_selector_recovery_failures(
    check_rows: list[CapsuleEvidenceClassification],
    terminal_failures: list[CapsuleEvidenceClassification],
) -> list[CapsuleEvidenceClassification]:
    recovered: list[CapsuleEvidenceClassification] = []
    for failure in terminal_failures:
        if failure.validation_class != "aggregate_selector_conflict":
            continue
        failure_paths = set(failure.validation_file_selectors)
        if len(failure_paths) < 2:
            continue
        failure_index = -1
        for index, row in enumerate(check_rows):
            if row.identity == failure.identity:
                failure_index = index
        if failure_index < 0:
            continue

        covered_paths: set[str] = set()
        for proof in check_rows[failure_index + 1:]:
            if proof.bucket != "check" or proof.result != "pass":
                continue
            proof_paths = set(proof.validation_file_selectors)
            if not proof_paths:
                continue
            covered_paths.update(failure_paths.intersection(proof_paths))
            if failure_paths.issubset(covered_paths):
                recovered.append(failure)
                break
    return recovered


def _capsule_later_publication_poll_recovery_failures(
    check_rows: list[CapsuleEvidenceClassification],
    terminal_failures: list[CapsuleEvidenceClassification],
) -> list[CapsuleEvidenceClassification]:
    recovered: list[CapsuleEvidenceClassification] = []
    for failure in terminal_failures:
        if failure.validation_class != "publication_status_poll":
            continue
        failure_index = -1
        for index, row in enumerate(check_rows):
            if row.identity == failure.identity:
                failure_index = index
        if failure_index < 0:
            continue
        later_same_intent_pass = any(
            row.result == "pass" and row.validation_class == "publication_status_poll"
            for row in check_rows[failure_index + 1:]
        )
        if later_same_intent_pass:
            recovered.append(failure)
    return recovered


def _capsule_closeout_claims_green_validation(final_assistant_text: str) -> bool:
    lowered = (final_assistant_text or "").lower()
    if not lowered:
        return False
    return (
        any(marker in lowered for marker in (
            "make ci",
            "crown-jewel demo",
            "crown jewel demo",
            "organ surface contract",
            "package-smoke",
            "package smoke",
            "smoke",
        ))
        and any(marker in lowered for marker in (
            "pass",
            "passed",
            "green",
            "no blockers",
            "delivery blockers: none",
        ))
    )


def _capsule_clean_text(value: str) -> str:
    text = value or ""
    text = text.replace(str(REPO_ROOT), "repo:")
    text = text.replace(str(HOME), "~")
    return text


def _capsule_commit_title_from_command(command: str) -> str:
    text = command or ""
    m = re.search(r"--message\s+['\"]?\$\(cat\s+<<['\"]?EOF['\"]?\n(.+?)\nEOF\n?\)['\"]?", text, re.S)
    if m:
        first_line = next((line.strip() for line in m.group(1).splitlines() if line.strip()), "")
        if first_line:
            return _capsule_clean_text(first_line)
    m = re.search(r"--message\s+['\"]([^'\"]+)['\"]", text, re.S)
    if m:
        return _capsule_clean_text(" ".join(m.group(1).split()))
    return "scoped commit"


def _capsule_json_dict_candidates(text: str, *, limit: int = 48) -> list[dict[str, Any]]:
    source = (text or "").strip()
    if not source:
        return []
    decoder = json.JSONDecoder()
    candidates: list[Any] = []

    def add_candidate(obj: Any) -> None:
        if len(candidates) >= limit:
            return
        if isinstance(obj, dict):
            candidates.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                add_candidate(item)

    try:
        add_candidate(json.loads(source))
    except json.JSONDecodeError:
        pass

    for match in re.finditer(r"[\{\[]", source):
        if len(candidates) >= limit:
            break
        try:
            obj, _ = decoder.raw_decode(source[match.start():])
        except json.JSONDecodeError:
            continue
        add_candidate(obj)

    expanded: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    def walk(obj: Any) -> None:
        if len(expanded) >= limit:
            return
        if isinstance(obj, dict):
            obj_id = id(obj)
            if obj_id in seen_ids:
                return
            seen_ids.add(obj_id)
            expanded.append(obj)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
        elif isinstance(obj, str):
            stripped = obj.strip()
            if not stripped or len(stripped) > 200_000 or stripped[0] not in "{[":
                return
            try:
                walk(json.loads(stripped))
            except json.JSONDecodeError:
                return

    for candidate in candidates:
        walk(candidate)
    return expanded


def _capsule_closeout_commit_refs(text: str) -> dict[str, tuple[str, str]]:
    refs: dict[str, tuple[str, str]] = {}
    patterns = (
        (
            "local_checkpoint",
            r"Local\s+(?:bankruptcy\s+)?checkpoint:\s*`?([0-9a-f]{7,40})`?(?:\s*\(`([^`]+)`\))?",
            "local checkpoint",
        ),
        (
            "remote_published",
            r"Published\s+remote\s+commit:\s*`?([0-9a-f]{7,40})`?(?:\s*\(`([^`]+)`\))?",
            "published remote commit",
        ),
    )
    for key, pattern, fallback_title in patterns:
        match = re.search(pattern, text or "", re.I)
        if not match:
            continue
        commit_hash = match.group(1).strip()
        title = _capsule_clean_text((match.group(2) or fallback_title).strip())
        refs[key] = (commit_hash, _capsule_normalize_commit_title(commit_hash, title))
    return refs


def _capsule_insert_commit_ref_before(
    rows: list[tuple[str, str]],
    ref: tuple[str, str],
    *,
    before_hash: str = "",
) -> None:
    commit_hash, title = ref
    if not commit_hash:
        return
    if any(
        existing_hash == commit_hash
        or existing_hash.startswith(commit_hash)
        or commit_hash.startswith(existing_hash)
        for existing_hash, _ in rows
    ):
        return
    if before_hash:
        for index, (existing_hash, _) in enumerate(rows):
            if (
                existing_hash == before_hash
                or existing_hash.startswith(before_hash)
                or before_hash.startswith(existing_hash)
            ):
                rows.insert(index, (commit_hash, title))
                return
    rows.append((commit_hash, title))


def _capsule_output_commit_title(output: str, commit_hash: str, *, fallback: str) -> str:
    if not commit_hash:
        return fallback
    escaped = re.escape(commit_hash)
    short = re.escape(commit_hash[:12])
    patterns = (
        rf'"prepared_commit"\s*:\s*"{escaped}"[\s\S]{{0,800}}"message"\s*:\s*"([^"]+)"',
        rf'"new_commit"\s*:\s*"{escaped}"[\s\S]{{0,800}}"message"\s*:\s*"([^"]+)"',
        rf"{short}\s+([^\n]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, output or "", re.I)
        if match:
            return _capsule_normalize_commit_title(commit_hash, match.group(1).strip())
    return _capsule_normalize_commit_title(commit_hash, fallback)


def _capsule_normalize_commit_title(commit_hash: str, title: str) -> str:
    text = _capsule_clean_text(" ".join((title or "").split()))
    text = re.sub(r"^(?:\([^)]*\)\s+)+", "", text)
    if commit_hash:
        m = re.match(r"^([0-9a-f]{7,40})\s+(.+)$", text)
        if m:
            repeated = m.group(1)
            if repeated.startswith(commit_hash) or commit_hash.startswith(repeated):
                text = m.group(2).strip()
    return text


def _capsule_commit_evidence_kind(command: str) -> str:
    candidates = _capsule_command_surface_argvs(command)
    if not candidates:
        return "none"
    for argv in candidates:
        exe = Path(argv[0]).name
        script, script_args, _ = _capsule_script_surface(argv)
        script_base = Path(script).name
        lower_args = [arg.lower() for arg in script_args]
        if script_base == "scoped_commit.py":
            return "produced"
        if script_base == "publication_lane.py" and "prepare" in lower_args:
            return "produced"
        if script_base == "checkpoint" or (argv and Path(argv[0]).name == "checkpoint"):
            return "produced"
        if exe in {"git", "repo-git"}:
            if "commit" in lower_args:
                return "produced"
            if any(arg in lower_args for arg in ("log", "show")):
                return "observed"
    return "none"


def _capsule_commit_evidence_allowed(command: str) -> bool:
    return _capsule_commit_evidence_kind(command) == "produced"


def _capsule_commit_from_output(output: str, command: str = "") -> tuple[str, str]:
    if not _capsule_commit_evidence_allowed(command):
        return ("", "")
    m = re.search(r'"new_commit"\s*:\s*"([0-9a-f]{7,40})"', output or "")
    if m:
        commit_hash = m.group(1)
        return (
            commit_hash,
            _capsule_output_commit_title(
                output,
                commit_hash,
                fallback=_capsule_commit_title_from_command(command),
            ),
        )
    m = re.search(r'"prepared_commit"\s*:\s*"([0-9a-f]{7,40})"', output or "")
    if m:
        commit_hash = m.group(1)
        return (
            commit_hash,
            _capsule_output_commit_title(
                output,
                commit_hash,
                fallback=_capsule_commit_title_from_command(command),
            ),
        )
    for line in (output or "").splitlines():
        m = re.match(r"^\[[^\]]+\s+([0-9a-f]{7,40})\]\s+(.+)$", line.strip(), re.IGNORECASE)
        if m:
            commit_hash = m.group(1)
            return (commit_hash, _capsule_normalize_commit_title(commit_hash, m.group(2).strip()))
        m = re.match(r"^commit\s+([0-9a-f]{7,40})\b(?:\s+(.+))?$", line.strip(), re.IGNORECASE)
        if m:
            commit_hash = m.group(1)
            title = (m.group(2) or _capsule_commit_title_from_command(command)).strip()
            return (commit_hash, _capsule_normalize_commit_title(commit_hash, title))
        m = re.match(r"^([0-9a-f]{7,16})\s+(.+)$", line.strip())
        if m:
            commit_hash = m.group(1)
            return (commit_hash, _capsule_normalize_commit_title(commit_hash, m.group(2).strip()))
    return ("", "")


def _capsule_git_status_topology(text: str) -> dict[str, Any]:
    matches = re.findall(
        r"(?m)^##\s+(?P<branch>\S+?)(?:\.\.\.(?P<upstream>\S+))?(?:\s+\[(?P<tracking>[^\]]+)\])?$",
        text or "",
    )
    if not matches:
        return {
            "state": "unknown",
            "ahead": None,
            "behind": None,
            "branch": "",
            "upstream": "",
        }
    branch, upstream, tracking = matches[-1]
    ahead_match = re.search(r"\bahead\s+(\d+)", tracking or "")
    behind_match = re.search(r"\bbehind\s+(\d+)", tracking or "")
    ahead = int(ahead_match.group(1)) if ahead_match else 0
    behind = int(behind_match.group(1)) if behind_match else 0
    if ahead and behind:
        state = "diverged"
    elif ahead:
        state = "ahead"
    elif behind:
        state = "behind"
    elif upstream:
        state = "converged"
    else:
        state = "unknown"
    return {
        "state": state,
        "ahead": ahead,
        "behind": behind,
        "branch": branch,
        "upstream": upstream,
    }


def _capsule_git_status_dirty_paths(text: str) -> list[str]:
    paths: list[str] = []
    for line in (text or "").splitlines():
        if not line.strip() or line.startswith("##"):
            continue
        body = line[3:].strip() if len(line) > 3 else line.strip()
        if " -> " in body:
            body = body.split(" -> ")[-1].strip()
        path = _capsule_public_trace_path(body)
        if path and path not in paths:
            paths.append(path)
    return paths


def _capsule_current_evidence_scope(command: str) -> str:
    candidates = _capsule_command_surface_argvs(command)
    for argv in candidates:
        exe = Path(argv[0]).name
        script, script_args, _ = _capsule_script_surface(argv)
        script_base = Path(script).name
        script_lower = script.lower()
        lower_args = [arg.lower() for arg in script_args]
        if (
            script_base == "github_private_vulnerability_reporting_receipt.py"
            or script_lower == "microcosm_core.release_export"
            or script_base == "microcosm_release_candidate_gate.py"
        ):
            return "current_public_release_gate_receipt"
        if script_base == "task_ledger_apply.py":
            return "current_task_ledger_authority_receipt"
        if script_base == "publication_lane.py" and "plan" in lower_args:
            return "current_publication_plan_receipt"
        if script_base == "publication_lane.py" and "prepare" in lower_args:
            return "current_publication_prepare_receipt"
        if script_base == "publication_lane.py" and "publish" in lower_args:
            return "current_publication_publish_receipt"
        if script_base == "work_landing.py" and "reconcile" in lower_args:
            return "current_work_landing_reconcile_receipt"
        if script_base == "work_landing.py" and "status" in lower_args:
            return "current_work_landing_status_receipt"
        if script_base == "run_git.py" and {"audit", "push"}.issubset(set(lower_args)) and "--json" in lower_args:
            return "current_push_audit_receipt"
        if script_base == "scoped_commit.py":
            return "current_scoped_commit_receipt"
        if script_base == "checkpoint" or exe == "checkpoint":
            return "current_checkpoint_receipt"
        if exe in {"git", "repo-git"} and "status" in lower_args and "--short" in lower_args and "--branch" in lower_args:
            if "-c" in lower_args:
                try:
                    c_value = argv[lower_args.index("-c") + 1]
                except IndexError:
                    c_value = ""
                if c_value and "publication" in c_value and c_value not in {".", str(REPO_ROOT)}:
                    return "current_publication_worktree_status"
            return "current_main_worktree_status"
        if exe in {"repo-pytest", "pytest"}:
            return "current_validation_command"
        if exe in {"node", "npm", "pnpm", "yarn"} and any(
            arg in {"--test", "test"} for arg in lower_args
        ):
            return "current_validation_command"
        if exe in {"repo-python", "python", "python3"} and any(
            arg in {"py_compile", "pytest"} for arg in lower_args
        ):
            return "current_validation_command"
        if exe == "make" and any(arg in {"ci", "test", "check"} for arg in lower_args):
            return "current_validation_command"
        if script_base == "cli_prompt_trace.py":
            return "historical_trace_render"
        if exe in {"rg", "sed", "cat", "less", "head", "tail"}:
            return "historical_source_artifact"
        if exe == "git" and any(arg in lower_args for arg in ("show", "log")):
            return "historical_git_observation"
    return "untrusted_command_output"


def _capsule_selected_commits_from_prepare(payload: Mapping[str, Any]) -> list[str]:
    selected: list[str] = []
    for row in payload.get("selected_commits") or []:
        if not isinstance(row, Mapping):
            continue
        commit = str(row.get("commit") or "").strip()
        if commit and commit not in selected:
            selected.append(commit)
    replay_source = str(payload.get("replay_source_commit") or "").strip()
    if replay_source and replay_source not in selected:
        selected.append(replay_source)
    return selected


def _capsule_publication_reentry_plan_from_payload(
    payload: Mapping[str, Any],
    *,
    evidence_scope: str,
    source_index: int,
    command: str,
) -> dict[str, Any] | None:
    schema = str(payload.get("schema") or "").strip()
    if schema != "publication_lane_plan_v2":
        return None
    candidate_wave = payload.get("candidate_publication_wave")
    if not isinstance(candidate_wave, Mapping):
        candidate_wave = {}
    selected_commits = [
        str(row.get("commit") or "").strip()
        for row in payload.get("selected_commits") or []
        if isinstance(row, Mapping) and str(row.get("commit") or "").strip()
    ]
    source_commit = str(
        candidate_wave.get("terminal_local_commit")
        or payload.get("replay_source_commit")
        or (selected_commits[-1] if selected_commits else "")
        or ""
    ).strip()
    selected_paths = [
        str(path)
        for path in (
            candidate_wave.get("selected_path_union")
            if candidate_wave.get("selected_path_union")
            else payload.get("selected_paths")
        ) or []
        if str(path)
    ]
    required_count = int(candidate_wave.get("required_local_prerequisite_commit_count") or 0)
    selected_path_count = int(
        candidate_wave.get("selected_path_union_count")
        or len(selected_paths)
        or len(payload.get("selected_paths") or [])
        or 0
    )
    plan_basis = {
        "status": payload.get("status"),
        "source_commit": source_commit,
        "base_ref": payload.get("base_ref"),
        "target_ref": payload.get("target_ref"),
        "selected_commits": selected_commits,
        "selected_paths": selected_paths,
        "include_prerequisite_chain": payload.get("include_prerequisite_chain"),
        "recommended_next_mode": payload.get("recommended_next_mode")
        or candidate_wave.get("recommended_next_mode"),
    }
    plan_fingerprint = hashlib.sha256(
        json.dumps(plan_basis, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "schema": "publication_reentry_plan_v1",
        "status": str(payload.get("status") or "unknown"),
        "source_commit": source_commit,
        "base_ref": str(payload.get("base_ref") or candidate_wave.get("base_ref") or ""),
        "target_ref": str(payload.get("target_ref") or ""),
        "selected_commit_count": int(payload.get("selected_commit_count") or len(selected_commits) or 0),
        "operator_selected_commit_count": int(payload.get("operator_selected_commit_count") or 0),
        "required_local_prerequisite_commit_count": required_count,
        "selected_path_count": selected_path_count,
        "recommended_next_mode": str(
            payload.get("recommended_next_mode")
            or candidate_wave.get("recommended_next_mode")
            or ""
        ),
        "plan_fingerprint": f"sha256:{plan_fingerprint}",
        "action_state": "not_attempted",
        "receipt_scope": evidence_scope,
        "receipt_source_command": f"C{source_index:03d}",
        "prepare_command": next(
            (
                str(command_text)
                for command_text in payload.get("actuator_commands") or []
                if "publication_lane.py prepare" in str(command_text)
            ),
            "",
        ),
        "blocker_class": str(
            candidate_wave.get("publication_blocker_class")
            or ("prerequisite_unpublished_commits_missing" if required_count else "none")
        ),
        "reentry_condition": str(candidate_wave.get("reentry_condition") or ""),
        "source_command": command,
    }


def _capsule_int_field_from_text(text: str, field: str) -> int | None:
    match = re.search(rf"\b{re.escape(field)}\b\s*[:=]\s*(\d+)", text or "")
    if not match:
        return None
    return int(match.group(1))


def _capsule_publication_reentry_plan_from_text(
    text: str,
    *,
    existing_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    source = text or ""
    if "publication_lane.py prepare" not in source and "selected_commit_count" not in source:
        return None
    selected_count = _capsule_int_field_from_text(source, "selected_commit_count")
    required_count = _capsule_int_field_from_text(source, "required_local_prerequisite_commit_count")
    selected_path_count = _capsule_int_field_from_text(source, "selected_path_count")
    if selected_count is None and required_count is None and selected_path_count is None:
        return None
    prepare_line = next(
        (
            line.strip()
            for line in source.splitlines()
            if "publication_lane.py prepare" in line
        ),
        "",
    )
    commit_matches = re.findall(r"--commit\s+([0-9a-f]{7,40})", prepare_line)
    existing_source_commit = str((existing_plan or {}).get("source_commit") or "").strip()
    source_commit = existing_source_commit or (commit_matches[-1] if commit_matches else "")
    recommended_match = re.search(r"\brecommended_next_mode\b\s*[:=]\s*([A-Za-z0-9_.:-]+)", source)
    status_match = re.search(r"\bstatus\b\s*[:=]\s*([A-Za-z0-9_.:-]+)", source)
    plan_basis = {
        "status": status_match.group(1) if status_match else "plan_ready",
        "source_commit": source_commit,
        "selected_commit_count": selected_count,
        "required_local_prerequisite_commit_count": required_count,
        "selected_path_count": selected_path_count,
        "recommended_next_mode": recommended_match.group(1) if recommended_match else "",
        "prepare_command": prepare_line,
    }
    plan_fingerprint = hashlib.sha256(
        json.dumps(plan_basis, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    action_state = "not_attempted_plan_blocked" if (required_count or 0) > 0 else "not_attempted"
    return {
        "schema": "publication_reentry_plan_v1",
        "status": status_match.group(1) if status_match else "plan_ready",
        "source_commit": source_commit,
        "base_ref": str((existing_plan or {}).get("base_ref") or "origin/main"),
        "target_ref": str((existing_plan or {}).get("target_ref") or "refs/heads/main"),
        "selected_commit_count": selected_count if selected_count is not None else int((existing_plan or {}).get("selected_commit_count") or 0),
        "operator_selected_commit_count": _capsule_int_field_from_text(source, "operator_selected_commit_count")
        if _capsule_int_field_from_text(source, "operator_selected_commit_count") is not None
        else int((existing_plan or {}).get("operator_selected_commit_count") or 0),
        "required_local_prerequisite_commit_count": required_count if required_count is not None else int((existing_plan or {}).get("required_local_prerequisite_commit_count") or 0),
        "selected_path_count": selected_path_count if selected_path_count is not None else int((existing_plan or {}).get("selected_path_count") or 0),
        "recommended_next_mode": recommended_match.group(1) if recommended_match else str((existing_plan or {}).get("recommended_next_mode") or ""),
        "plan_fingerprint": f"sha256:{plan_fingerprint}",
        "action_state": action_state,
        "receipt_scope": "assistant_closeout_publication_plan",
        "receipt_source_command": "assistant_final",
        "prepare_command": prepare_line,
        "blocker_class": "prerequisite_unpublished_commits_missing" if (required_count or 0) > 0 else "none",
        "reentry_condition": str((existing_plan or {}).get("reentry_condition") or ""),
        "source_command": "final_assistant_text",
    }


def _capsule_git_publication_trace(
    renderable: list[tuple[ToolEvent, str, int | None, bool]],
    final_assistant_text: str,
) -> dict[str, Any]:
    local_checkpoint_commit = ""
    local_checkpoint_title = ""
    local_source_commit = ""
    local_source_title = ""
    remote_published_commit = ""
    remote_published_title = ""
    prepared_commit = ""
    prepared_commit_title = ""
    replay_source_commit = ""
    replay_mode = ""
    selected_paths: list[str] = []
    target_ref = ""
    target_refspec = ""
    post_push_remote_sha = ""
    remote_verified = False
    guarded_push_seen = False
    path_snapshot_status = ""
    path_snapshot_replay_mode = ""
    conflict_fallback_status = ""
    conflict_paths: list[str] = []
    publication_worktree_dir = ""
    publication_worktree_state = "none"
    publication_worktree_removed = False
    publication_worktree_removed_paths: list[str] = []
    selected_path_count = 0
    safe_path_snapshot: bool | None = None
    source_owner_overlap_blocks_auto_snapshot: bool | None = None
    selected_vs_remote_overlap_paths: list[str] = []
    publication_worktree_pending_files: int | None = None
    main_worktree_pending_files: int | None = None
    main_worktree_dirty_paths: list[str] = []
    evidence_scope_rows: list[dict[str, Any]] = []
    nested_observed_validation = "none"
    publication_reentry_plan: dict[str, Any] | None = None

    closeout_refs = _capsule_closeout_commit_refs(final_assistant_text)
    if "local_checkpoint" in closeout_refs:
        local_checkpoint_commit, local_checkpoint_title = closeout_refs["local_checkpoint"]
        local_source_commit = local_checkpoint_commit
        local_source_title = local_checkpoint_title
    if "remote_published" in closeout_refs:
        remote_published_commit, remote_published_title = closeout_refs["remote_published"]

    def apply_guarded_push_receipt(receipt: Mapping[str, Any]) -> None:
        nonlocal remote_published_commit, target_ref, target_refspec, post_push_remote_sha
        nonlocal remote_verified, guarded_push_seen
        if not isinstance(receipt, Mapping):
            return
        receipt_status = str(receipt.get("status") or "").strip()
        if receipt_status != "pushed":
            return
        guarded_push_seen = True
        pushed_commit = str(
            receipt.get("pushed_commit")
            or receipt.get("expected_source_sha")
            or receipt.get("current_source_sha")
            or ""
        ).strip()
        if pushed_commit:
            remote_published_commit = pushed_commit
        target_ref = str(receipt.get("target_ref") or target_ref or "").strip()
        target_refspec = str(receipt.get("push_refspec") or target_refspec or "").strip()
        post_push_remote_sha = str(receipt.get("post_push_remote_sha") or post_push_remote_sha or "").strip()
        remote_verified = bool(receipt.get("remote_verified")) or (
            bool(remote_published_commit) and post_push_remote_sha == remote_published_commit
        )

    for ev, output_text, _, _ in renderable:
        command = _capsule_clean_text(_capsule_command(ev))
        evidence_scope = _capsule_current_evidence_scope(command)
        command_lower = command.lower()
        if "worktree" in command_lower and "remove" in command_lower and not ev.exit_code:
            publication_worktree_removed = True
            for match in re.finditer(r"(/(?:private/)?tmp/[^\s'\"`]+)", command):
                removed_path = match.group(1).rstrip(".,;:")
                if removed_path and removed_path not in publication_worktree_removed_paths:
                    publication_worktree_removed_paths.append(removed_path)
        if evidence_scope in {
            "historical_trace_render",
            "historical_source_artifact",
            "historical_git_observation",
            "untrusted_command_output",
        }:
            if (
                nested_observed_validation == "none"
                and (
                    (
                        re.search(r"\bNo test suite was run\b", output_text or "", re.I)
                        and "checkpoint/publication operation" in (output_text or "")
                    )
                    or "tests: not_run_checkpoint_publication_operation" in (output_text or "")
                )
            ):
                nested_observed_validation = "specimen_not_run_checkpoint_publication_operation"
            continue
        if evidence_scope == "current_main_worktree_status":
            main_worktree_dirty_paths = _capsule_git_status_dirty_paths(output_text or "")
            main_worktree_pending_files = len(main_worktree_dirty_paths)
            evidence_scope_rows.append({
                "evidence_scope": evidence_scope,
                "schema": "git_status_short_branch",
                "summary_driver": True,
            })
            continue
        if evidence_scope == "current_publication_worktree_status":
            publication_worktree_pending_files = len(_capsule_git_status_dirty_paths(output_text or ""))
            evidence_scope_rows.append({
                "evidence_scope": evidence_scope,
                "schema": "git_status_short_branch",
                "summary_driver": True,
            })
            continue
        for payload in _capsule_json_dict_candidates(output_text or ""):
            schema = str(payload.get("schema") or payload.get("kind") or "").strip()
            if schema:
                evidence_scope_rows.append({
                    "evidence_scope": evidence_scope,
                    "schema": schema,
                    "summary_driver": evidence_scope.startswith("current_"),
                })
            plan = _capsule_publication_reentry_plan_from_payload(
                payload,
                evidence_scope=evidence_scope,
                source_index=ev.index,
                command=command,
            )
            if plan:
                publication_reentry_plan = plan
                if plan.get("source_commit") and not local_source_commit:
                    local_source_commit = str(plan.get("source_commit") or "")
                    local_source_title = "publication reentry source commit"
                target_ref = str(plan.get("target_ref") or target_ref or "").strip()
                selected_path_count = int(plan.get("selected_path_count") or selected_path_count or 0)
            if schema == "push_audit_status_v1":
                audited_head = str(payload.get("head") or payload.get("audited_source_sha") or "").strip()
                if local_checkpoint_commit and audited_head and audited_head.startswith(local_checkpoint_commit):
                    local_checkpoint_commit = audited_head
                    if local_source_commit and audited_head.startswith(local_source_commit):
                        local_source_commit = audited_head
                if audited_head and not local_source_commit:
                    local_source_commit = audited_head
                    local_source_title = "audited source commit"
                elif local_source_commit and audited_head and audited_head.startswith(local_source_commit):
                    local_source_commit = audited_head
            if schema == "publication_lane_prepare_v1":
                publication_worktree_dir = str(payload.get("worktree_dir") or publication_worktree_dir or "").strip()
                prepared = str(payload.get("prepared_commit") or "").strip()
                if prepared:
                    prepared_commit = prepared
                    prepared_commit_title = _capsule_commit_title_from_command(command)
                    if not remote_published_commit:
                        remote_published_commit = prepared
                replay_mode = str(payload.get("replay_mode") or replay_mode or "").strip()
                selected_paths = [str(path) for path in payload.get("selected_paths") or [] if str(path)]
                selected_path_count = len(selected_paths)
                selected_commits = _capsule_selected_commits_from_prepare(payload)
                if selected_commits:
                    replay_source_commit = selected_commits[-1]
                    if not local_source_commit:
                        local_source_commit = replay_source_commit
                        local_source_title = "publication replay source commit"
                target_ref = str(payload.get("target_ref") or target_ref or "").strip()
                path_snapshot = payload.get("path_snapshot")
                if isinstance(path_snapshot, Mapping):
                    path_snapshot_replay_mode = str(payload.get("replay_mode") or "").strip()
                    path_snapshot_status = "ok" if path_snapshot.get("ok") else "failed"
                fallback = payload.get("path_snapshot_fallback")
                if isinstance(fallback, Mapping):
                    conflict_fallback_status = str(fallback.get("status") or "").strip()
                    if "safe_path_snapshot" in fallback:
                        safe_path_snapshot = bool(fallback.get("safe_path_snapshot"))
                    if "source_owner_overlap_blocks_auto_snapshot" in fallback:
                        source_owner_overlap_blocks_auto_snapshot = bool(
                            fallback.get("source_owner_overlap_blocks_auto_snapshot")
                        )
                    selected_vs_remote_overlap_paths = [
                        str(path)
                        for path in fallback.get("selected_vs_remote_overlap_paths") or []
                        if str(path)
                    ]
                conflicts = payload.get("conflict_paths")
                if isinstance(conflicts, list):
                    conflict_paths = [str(path) for path in conflicts if str(path)]
                status = str(payload.get("status") or "").strip()
                if status == "conflict" or conflict_paths:
                    publication_worktree_state = "retained_conflict_or_inconsistent_replay"
                elif status in {"ready_to_push", "prepared"}:
                    publication_worktree_state = "prepared"
            elif schema == "publication_lane_publish_v1":
                publication_worktree_dir = str(payload.get("repo_root") or publication_worktree_dir or "").strip()
                target_ref = str(payload.get("target_ref") or target_ref or "").strip()
                target_refspec = str(payload.get("target_refspec") or target_refspec or "").strip()
                topology = payload.get("post_publish_topology_receipt")
                if isinstance(topology, Mapping):
                    pending = topology.get("worktree_pending_file_count")
                    if isinstance(pending, int):
                        publication_worktree_pending_files = pending
                    if topology.get("remote_published_commit"):
                        remote_published_commit = str(topology.get("remote_published_commit") or "").strip()
                    if topology.get("post_push_remote_sha"):
                        post_push_remote_sha = str(topology.get("post_push_remote_sha") or "").strip()
                    remote_verified = remote_verified or bool(topology.get("remote_verified"))
                receipt = payload.get("guarded_push_receipt")
                if isinstance(receipt, Mapping):
                    apply_guarded_push_receipt(receipt)
            if schema in {"guarded_push_receipt_v1", "guarded_push_receipt"}:
                apply_guarded_push_receipt(payload)

    if not post_push_remote_sha:
        match = re.search(
            r"origin/main\s+now\s+resolves\s+to\s+`?([0-9a-f]{7,40})`?",
            final_assistant_text or "",
            re.I,
        )
        if match:
            post_push_remote_sha = match.group(1)
    if remote_published_commit and post_push_remote_sha:
        remote_verified = remote_verified or post_push_remote_sha.startswith(remote_published_commit) or remote_published_commit.startswith(post_push_remote_sha)
    if remote_published_commit and not remote_published_title:
        remote_published_title = prepared_commit_title or "published remote commit"
    retained_match = _CAPSULE_PUBLICATION_WORKTREE_RE.search(final_assistant_text or "")
    if retained_match and not publication_worktree_dir:
        publication_worktree_dir = retained_match.group("path").rstrip(".,;:")
    if publication_worktree_dir and publication_worktree_state == "none":
        publication_worktree_state = "retained_conflict_or_inconsistent_replay"
    text_plan = (
        _capsule_publication_reentry_plan_from_text(
            final_assistant_text,
            existing_plan=publication_reentry_plan,
        )
        if publication_reentry_plan
        else None
    )
    if text_plan:
        current_selected_count = int((publication_reentry_plan or {}).get("selected_commit_count") or 0)
        text_selected_count = int(text_plan.get("selected_commit_count") or 0)
        current_prepare = str((publication_reentry_plan or {}).get("prepare_command") or "")
        text_prepare = str(text_plan.get("prepare_command") or "")
        same_source = (
            not publication_reentry_plan
            or not text_plan.get("source_commit")
            or not publication_reentry_plan.get("source_commit")
            or text_plan.get("source_commit") == publication_reentry_plan.get("source_commit")
        )
        if same_source and (
            not publication_reentry_plan
            or text_selected_count > current_selected_count
            or ("--include-prerequisite-chain" in text_prepare and "--include-prerequisite-chain" not in current_prepare)
        ):
            publication_reentry_plan = text_plan
    if publication_reentry_plan:
        if remote_published_commit and remote_verified:
            publication_reentry_plan["action_state"] = "pushed_verified"
        elif publication_worktree_state == "prepared":
            publication_reentry_plan["action_state"] = "prepared_ready_to_push"
        elif publication_worktree_state != "none" or conflict_paths:
            publication_reentry_plan["action_state"] = "prepare_attempted_conflict_retained"
        elif int(publication_reentry_plan.get("required_local_prerequisite_commit_count") or 0) > 0:
            publication_reentry_plan["action_state"] = "not_attempted_plan_blocked"
        else:
            publication_reentry_plan["action_state"] = "not_attempted"

    if local_checkpoint_commit and remote_published_commit and remote_published_commit != local_checkpoint_commit:
        operation_kind = "checkpoint_publication_path_snapshot"
    elif local_checkpoint_commit:
        operation_kind = "checkpoint_publication"
    elif local_source_commit and (prepared_commit or remote_published_commit or publication_worktree_dir):
        operation_kind = "source_publication"
    else:
        operation_kind = "none"
    main_status_outputs = [
        output_text or ""
        for ev, output_text, _, _ in renderable
        if _capsule_current_evidence_scope(_capsule_clean_text(_capsule_command(ev))) == "current_main_worktree_status"
    ]
    topology = _capsule_git_status_topology(main_status_outputs[-1] if main_status_outputs else "")
    topology_state = str(topology.get("state") or "unknown")
    if (
        topology_state == "diverged"
        and local_checkpoint_commit
        and remote_published_commit
        and remote_published_commit != local_checkpoint_commit
    ):
        topology_state = "diverged_after_clean_path_snapshot"

    git_remote_publication = "none"
    if remote_published_commit and remote_verified:
        git_remote_publication = "pushed_verified"
    elif remote_published_commit and guarded_push_seen:
        git_remote_publication = "pushed_unverified"
    elif remote_published_commit:
        git_remote_publication = "observed"
    if publication_worktree_removed and (
        not publication_worktree_dir or not publication_worktree_removed_paths or publication_worktree_dir in publication_worktree_removed_paths
    ):
        publication_worktree_state = "removed_after_publish" if git_remote_publication.startswith("pushed") else "removed"
    elif git_remote_publication.startswith("pushed") and publication_worktree_state == "prepared":
        publication_worktree_state = "published_remote_verified"

    publication_replay_relation: dict[str, Any] | None = None
    if local_source_commit and remote_published_commit and remote_published_commit != local_source_commit:
        publication_replay_relation = {
            "schema_version": "agent_trace_publication_replay_relation_v1",
            "relation": "remote_publication_commit_replays_local_source_commit",
            "local_source_commit": local_source_commit,
            "remote_publication_commit": remote_published_commit,
            "replay_source_commit": replay_source_commit or local_source_commit,
            "replay_mode": replay_mode or path_snapshot_replay_mode or "unknown",
            "selected_path_count": len(selected_paths),
            "selected_paths": selected_paths,
            "diff_basis": "publication_lane_prepare_selected_paths",
            "evidence_scope": "current_publication_prepare_receipt",
        }
    worktree_pending_files = (
        main_worktree_pending_files
        if main_worktree_pending_files is not None
        else publication_worktree_pending_files
    )

    return {
        "schema_version": "agent_trace_git_publication_trace_v1",
        "evidence_scope_rows": evidence_scope_rows,
        "local_checkpoint_commit": local_checkpoint_commit,
        "local_checkpoint_title": local_checkpoint_title,
        "local_source_commit": local_source_commit,
        "local_source_title": local_source_title,
        "prepared_commit": prepared_commit,
        "remote_published_commit": remote_published_commit,
        "remote_published_title": remote_published_title,
        "target_ref": target_ref,
        "target_refspec": target_refspec,
        "post_push_remote_sha": post_push_remote_sha,
        "git_remote_publication": git_remote_publication,
        "remote_verified": remote_verified,
        "path_snapshot_status": path_snapshot_status,
        "path_snapshot_replay_mode": path_snapshot_replay_mode,
        "conflict_fallback_status": conflict_fallback_status,
        "conflict_paths": conflict_paths,
        "publication_worktree_dir": publication_worktree_dir,
        "publication_worktree_state": publication_worktree_state,
        "publication_worktree_removed": publication_worktree_removed,
        "publication_worktree_removed_paths": publication_worktree_removed_paths,
        "selected_path_count": selected_path_count,
        "safe_path_snapshot": safe_path_snapshot,
        "source_owner_overlap_blocks_auto_snapshot": source_owner_overlap_blocks_auto_snapshot,
        "selected_vs_remote_overlap_paths": selected_vs_remote_overlap_paths,
        "publication_replay_relation": publication_replay_relation,
        "publication_reentry_plan": publication_reentry_plan,
        "local_branch_topology": topology_state,
        "local_branch_ahead": topology.get("ahead"),
        "local_branch_behind": topology.get("behind"),
        "local_branch_name": topology.get("branch") or "",
        "local_branch_upstream": topology.get("upstream") or "",
        "main_worktree_pending_files": main_worktree_pending_files,
        "main_worktree_dirty_paths": main_worktree_dirty_paths,
        "publication_worktree_pending_files": publication_worktree_pending_files,
        "worktree_pending_files": worktree_pending_files,
        "operation_kind": operation_kind,
        "nested_observed_validation": nested_observed_validation,
    }


def _capsule_current_tests_state(
    *,
    terminal_check_pass_count: int,
    terminal_check_fail_count: int,
    terminal_check_other_count: int,
    source_check_pass_count: int = 0,
    source_check_fail_count: int = 0,
    source_check_other_count: int = 0,
    publication_candidate_pass_count: int = 0,
    publication_candidate_fail_count: int = 0,
    publication_candidate_other_count: int = 0,
    check_pass_count: int,
    check_fail_count: int,
    check_other_count: int,
    operation_kind: str,
    final_assistant_text: str,
) -> str:
    if (
        source_check_pass_count
        or source_check_fail_count
        or source_check_other_count
        or publication_candidate_pass_count
        or publication_candidate_fail_count
        or publication_candidate_other_count
    ) and (
        publication_candidate_pass_count
        or publication_candidate_fail_count
        or publication_candidate_other_count
    ):
        return (
            "source_current_checks("
            f"pass={source_check_pass_count} "
            f"fail={source_check_fail_count} "
            f"other={source_check_other_count}); "
            "publication_candidate_checks("
            f"pass={publication_candidate_pass_count} "
            f"fail={publication_candidate_fail_count} "
            f"other={publication_candidate_other_count})"
        )
    if terminal_check_pass_count or terminal_check_fail_count or terminal_check_other_count:
        return (
            "current_terminal_checks("
            f"pass={terminal_check_pass_count} "
            f"fail={terminal_check_fail_count} "
            f"other={terminal_check_other_count})"
        )
    if check_pass_count or check_fail_count or check_other_count:
        return (
            "current_checks("
            f"pass={check_pass_count} "
            f"fail={check_fail_count} "
            f"other={check_other_count})"
        )
    if (
        str(operation_kind or "").startswith("checkpoint_publication")
        and re.search(r"\bNo test suite was run\b", final_assistant_text or "", re.I)
        and "checkpoint/publication operation" in (final_assistant_text or "")
    ):
        return "not_run_checkpoint_publication_operation"
    return "not_established"


def _capsule_final_assistant_text(turn: Turn) -> str:
    for ev in reversed(turn.assistant_events or []):
        text = (ev.text or "").strip()
        if text:
            return text
    for block in reversed(re.split(r"\n\s*\n", turn.assistant_text or "")):
        text = block.strip()
        if text:
            # Merged multi-turn assistant_text prefixes blocks with [turn N].
            return re.sub(r"^\[turn\s+\d+\]\s*", "", text).strip()
    return ""


def _capsule_single_line_excerpt(text: str, *, max_chars: int) -> str:
    clean = _capsule_clean_text(" ".join((text or "").strip().split()))
    if len(clean) <= max_chars:
        return clean
    head_len = max(120, int(max_chars * 0.62))
    tail_len = max(80, int(max_chars * 0.28))
    head = clean[:head_len].rstrip()
    tail = clean[-tail_len:].lstrip()
    omitted = max(0, len(clean) - len(head) - len(tail))
    return f"{head} [closeout omitted {omitted} chars; sha16={_sha16(clean)}] {tail}"


def _capsule_result_summary(turn: Turn, commit_title: str) -> str:
    text = _capsule_final_assistant_text(turn)
    if text:
        first = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))[0]
        return _capsule_clean_text(first[:180])
    if commit_title:
        return _capsule_clean_text(commit_title)
    return "trace captured so far"


_REASONING_PREFIX_BY_CATEGORY = {
    "diagnosis": "D",
    "plan": "P",
    "discovery": "I",
    "pivot": "X",
    "validation_intent": "V",
    "route_decision": "Q",
    "decision": "J",
    "closeout": "R",
    "note": "N",
}


def _capsule_reasoning_category(text: str) -> str:
    stripped_lower = (text or "").strip().lower()
    lower = f" {text.lower()} "
    explicit_pivot = any(token in lower for token in (
        " pivot", "pivoting", " pivoted", " changing course", " changing direction",
        " switch to", " switching to", " course-correct"
    ))
    closeout_signal = (
        stripped_lower.startswith(("closeout", "## closeout", "fixed and committed", "implemented "))
        or any(token in lower for token in (
            " committed", " implemented", " scoped commit landed", " landed as", " landed `",
            " what changed", " result:", " final ", " finalized", " dropped from", " reduced to",
            " done.", " complete.", " completed "
        ))
    )
    if closeout_signal and not explicit_pivot:
        return "closeout"
    if any(token in lower for token in (
        " defect", " bug", " problem", " failure mode", " misleading",
        " misclassif", " bloat", " gap", " culprit", " issue is"
    )):
        return "diagnosis"
    if any(token in lower for token in (
        " claim is clean", " work ledger", " scoped commit", " private-index",
        " owned path", " owned files", " path list", " same-path", " live same-path",
        " leaving", " leave ", " not touching", " unrelated", " excluded path",
        " excluded files", " excluded dirt",
        " keeping this scoped", " commit path", " pathscope", " path scope",
        " treating ", " historical precursor", " historical/imported"
    )):
        return "route_decision"
    if any(token in lower for token in (
        " pivot", " instead", " treating that as", " rerunning with", " tightening", " changing course",
        " one more concrete issue", " adjacent false-positive"
    )):
        return "pivot"
    if any(token in lower for token in (
        " running the", " running focused", " replaying", " smoke", " validation", " validations",
        " checks", " tests", " py_compile", " swiftc", " node --check"
    )):
        return "validation_intent"
    if any(token in lower for token in (
        " specimen shows", " specimen shape", " pasted capsule shows"
    )):
        return "diagnosis"
    if any(token in lower for token in (
        " i'm going to", " i’m going to", " i will", " i'll", " i’ll", " next ",
        " using ", " because ", " applying edits", " patch", " claim", " inspect",
        " opening", " sampling", " reading ", " launching ", " authoring ", " direct_local"
    )):
        return "plan"
    if any(token in lower for token in (
        " only ", " scope ", " committing only", " keeping ", " decision"
    )):
        return "decision"
    if any(token in lower for token in (
        " i found", " found the", " showed up", " exposed", " caught", " confirms",
        " confirm", " live state", " current rendered", " now has", " shows"
    )):
        return "discovery"
    return "note"


def _capsule_reasoning_excerpt(text: str, *, max_chars: int = 210) -> str:
    clean = _capsule_clean_text(" ".join((text or "").strip().split()))
    if len(clean) <= max_chars:
        return clean
    hash_suffix = f" [sha16={_sha16(clean)}]"
    limit = max(40, max_chars - len(hash_suffix))
    clauses = re.split(r"(?<=[.!?;])\s+|\s+[—–-]\s+", clean)
    out = ""
    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        candidate = f"{out} {clause}".strip() if out else clause
        if len(candidate) <= limit:
            out = candidate
            continue
        break
    if not out:
        prefix = clean[:limit].rstrip()
        boundary = max(prefix.rfind(". "), prefix.rfind("; "), prefix.rfind(", "), prefix.rfind(" "))
        if boundary >= 48:
            prefix = prefix[:boundary].rstrip(" ,;.")
        out = prefix.rstrip(" ,;.")
    return f"{out}{hash_suffix}"


def _capsule_reasoning_digest_events(
    events: list[CapsuleReasoningEvent],
    *,
    max_rows: int = 7,
) -> list[CapsuleReasoningEvent]:
    selected: list[CapsuleReasoningEvent] = []
    seen_categories: set[str] = set()
    for event in events:
        if event.category == "note" or event.category in seen_categories:
            continue
        selected.append(event)
        seen_categories.add(event.category)
        if len(selected) >= max_rows:
            return selected
    if len(selected) < max_rows:
        for event in events:
            if event.category != "note":
                continue
            selected.append(event)
            if len(selected) >= max_rows:
                return selected
    if events and events[-1].category == "closeout" and events[-1] not in selected:
        if len(selected) >= max_rows:
            selected[-1] = events[-1]
        else:
            selected.append(events[-1])
    return selected


def _capsule_reasoning_digest_lines(events: list[CapsuleReasoningEvent]) -> list[str]:
    selected = _capsule_reasoning_digest_events(events)
    if not selected:
        return ["reasoning_digest: none"]
    lines = ["reasoning_digest:"]
    counters: dict[str, int] = {}
    for event in selected:
        prefix = _REASONING_PREFIX_BY_CATEGORY.get(event.category, "N")
        counters[prefix] = counters.get(prefix, 0) + 1
        digest_id = f"{prefix}{counters[prefix]:03d}"
        lines.append(f"- {digest_id} {event.category} {event.note_id} {_capsule_reasoning_excerpt(event.text)}")
    return lines


def _capsule_visible_progress_section_lines(events: list[CapsuleReasoningEvent]) -> list[str]:
    lines = [
        "VISIBLE_PROGRESS",
        f"source=app_visible_assistant_messages notes={len(events)}",
        "server_hidden_reasoning: not_included",
    ]
    if not events:
        lines.append("none captured")
        return lines
    for event in events:
        lines.append(f"{event.note_id} {event.category} {event.text}")
    return lines


def _capsule_compact_id_list(ids: list[str], *, max_items: int = 7) -> str:
    ordered = list(dict.fromkeys([value for value in ids if value]))
    if not ordered:
        return "none"
    ranges: list[str] = []
    i = 0
    while i < len(ordered):
        m = re.match(r"^([A-Z]+)(\d{3})$", ordered[i])
        if not m:
            ranges.append(ordered[i])
            i += 1
            continue
        prefix = m.group(1)
        start = int(m.group(2))
        end = start
        j = i + 1
        while j < len(ordered):
            n = re.match(r"^([A-Z]+)(\d{3})$", ordered[j])
            if not n or n.group(1) != prefix or int(n.group(2)) != end + 1:
                break
            end = int(n.group(2))
            j += 1
        if end > start:
            ranges.append(f"{prefix}{start:03d}-{prefix}{end:03d}")
        else:
            ranges.append(f"{prefix}{start:03d}")
        i = j
    visible = ranges[:max_items]
    if len(ranges) > max_items:
        visible.append(f"+{len(ranges) - max_items} more")
    return ",".join(visible)


def _capsule_episode_label(event: CapsuleReasoningEvent) -> str:
    return event.category if event.category != "note" else "note"


def _capsule_episode_check_summary(
    check_rows: list[CapsuleEpisodeEvidence],
    terminal_check_by_identity: dict[str, CapsuleEvidenceClassification],
) -> str:
    passed = sum(1 for row in check_rows if row.result == "pass")
    failed = sum(1 for row in check_rows if row.result == "fail")
    other = max(0, len(check_rows) - passed - failed)
    recovered = sum(
        1
        for row in check_rows
        if row.result == "fail"
        and row.identity
        and terminal_check_by_identity.get(row.identity) is not None
        and terminal_check_by_identity[row.identity].result == "pass"
    )
    parts = [str(len(check_rows)), f"pass={passed}", f"fail={failed}"]
    if other:
        parts.append(f"other={other}")
    parts.append(f"recovered={recovered}")
    return "(" + " ".join(parts) + ")"


def _capsule_episode_result(
    evidence: list[CapsuleEpisodeEvidence],
    notes: list[CapsuleReasoningEvent],
    terminal_check_by_identity: dict[str, CapsuleEvidenceClassification],
) -> str:
    commits = [row for row in evidence if row.kind == "commit"]
    if commits:
        return f"commit {_capsule_compact_id_list([row.row_id for row in commits])}"
    check_rows = [row for row in evidence if row.kind == "check"]
    if check_rows:
        passed = sum(1 for row in check_rows if row.result == "pass")
        failed = sum(1 for row in check_rows if row.result == "fail")
        other = max(0, len(check_rows) - passed - failed)
        recovered = sum(
            1
            for row in check_rows
            if row.result == "fail"
            and row.identity
            and terminal_check_by_identity.get(row.identity) is not None
            and terminal_check_by_identity[row.identity].result == "pass"
        )
        return f"checks pass={passed} fail={failed} other={other} recovered={recovered}"
    governance_rows = [row for row in evidence if row.kind == "governance"]
    if governance_rows:
        passed = sum(1 for row in governance_rows if row.result == "pass")
        failed = sum(1 for row in governance_rows if row.result == "fail")
        other = max(0, len(governance_rows) - passed - failed)
        return f"governance pass={passed} fail={failed} other={other}"
    edit_rows = [row for row in evidence if row.kind == "edit"]
    if edit_rows:
        return f"edits={len(edit_rows)}"
    command_rows = [row for row in evidence if row.kind == "command"]
    if command_rows:
        return f"commands={len(command_rows)}"
    for note in reversed(notes):
        if note.category in {"closeout", "discovery", "decision"}:
            return _capsule_reasoning_excerpt(note.text, max_chars=120)
    return "note_only"


def _capsule_episode_lines(
    reasoning_events: list[CapsuleReasoningEvent],
    evidence_events: list[CapsuleEpisodeEvidence],
    terminal_check_by_identity: dict[str, CapsuleEvidenceClassification] | None = None,
    *,
    max_episodes: int = 6,
) -> tuple[list[str], int]:
    if not reasoning_events:
        return (["episodes: count=0 source=assistant_visible_only+timeline evidence_linked=false"], 0)
    terminal_check_by_identity = terminal_check_by_identity or {}

    start_categories = {"diagnosis", "plan", "pivot", "validation_intent", "route_decision", "decision", "closeout"}
    starts: list[CapsuleReasoningEvent] = []
    previous_start: CapsuleReasoningEvent | None = None
    for event in reasoning_events:
        if previous_start is None:
            starts.append(event)
            previous_start = event
            continue
        if event.category in start_categories:
            prior_evidence = [
                row for row in evidence_events
                if row.source_index >= previous_start.source_index and row.source_index < event.source_index
            ]
            if prior_evidence and len(starts) < max_episodes:
                starts.append(event)
                previous_start = event

    episodes: list[tuple[CapsuleReasoningEvent, list[CapsuleReasoningEvent], list[CapsuleEpisodeEvidence]]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].source_index if index + 1 < len(starts) else 10**12
        notes = [event for event in reasoning_events if event.source_index >= start.source_index and event.source_index < end]
        evidence = [row for row in evidence_events if row.source_index >= start.source_index and row.source_index < end]
        episodes.append((start, notes, evidence))

    lines = [f"episodes: count={len(episodes)} source=assistant_visible_only+timeline evidence_linked=true"]
    for index, (start, notes, evidence) in enumerate(episodes, start=1):
        note_ids = _capsule_compact_id_list([note.note_id for note in notes], max_items=4)
        command_ids = _capsule_compact_id_list([row.row_id for row in evidence if row.kind == "command"], max_items=4)
        edit_ids = _capsule_compact_id_list([row.row_id for row in evidence if row.kind == "edit"], max_items=3)
        check_rows = [row for row in evidence if row.kind == "check"]
        check_ids = _capsule_compact_id_list([row.row_id for row in check_rows], max_items=4)
        governance_ids = _capsule_compact_id_list([row.row_id for row in evidence if row.kind == "governance"], max_items=4)
        commit_ids = _capsule_compact_id_list([row.row_id for row in evidence if row.kind == "commit"], max_items=2)
        evidence_parts = [f"notes={note_ids}"]
        if command_ids != "none":
            evidence_parts.append(f"evidence={command_ids}")
        if edit_ids != "none":
            evidence_parts.append(f"edits={edit_ids}")
        if check_ids != "none":
            evidence_parts.append(
                f"checks={check_ids}{_capsule_episode_check_summary(check_rows, terminal_check_by_identity)}"
            )
        if governance_ids != "none":
            evidence_parts.append(f"governance={governance_ids}")
        if commit_ids != "none":
            evidence_parts.append(f"commit={commit_ids}")
        why = _capsule_reasoning_excerpt(start.text, max_chars=135)
        result = _capsule_episode_result(evidence, notes, terminal_check_by_identity)
        lines.append(
            f"W{index:03d} {_capsule_episode_label(start)} why={start.note_id} {why}; "
            f"{' '.join(evidence_parts)} result={result}"
        )
    return (lines, len(episodes))


def _write_variant_index_entry(session_id: str, variant: str, artifact: dict) -> None:
    index: dict[str, Any] = {"schema": "agent_trace_variant_artifact_index_v1", "sessions": {}}
    if TRACE_STRUCTURER_VARIANT_INDEX.exists():
        try:
            loaded = json.loads(TRACE_STRUCTURER_VARIANT_INDEX.read_text() or "{}")
            if isinstance(loaded, dict):
                index = loaded
        except Exception:
            pass
    sessions = index.setdefault("sessions", {})
    session_artifacts = sessions.get(session_id)
    if not isinstance(session_artifacts, dict):
        session_artifacts = {}
    session_artifacts[variant] = artifact
    identity_key = artifact.get("identity_key")
    if identity_key:
        by_identity = session_artifacts.get("by_source_identity")
        if not isinstance(by_identity, dict):
            by_identity = {}
        identity_artifacts = by_identity.get(identity_key)
        if not isinstance(identity_artifacts, dict):
            identity_artifacts = {}
        identity_artifacts[variant] = artifact
        by_identity[identity_key] = identity_artifacts
        session_artifacts["by_source_identity"] = by_identity
    sessions[session_id] = session_artifacts
    index["schema"] = "agent_trace_variant_artifact_index_v1"
    index["sessions"] = sessions
    index["updated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
    tmp = TRACE_STRUCTURER_VARIANT_INDEX.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(TRACE_STRUCTURER_VARIANT_INDEX)


def _load_variant_artifact_index() -> dict[str, Any]:
    if not TRACE_STRUCTURER_VARIANT_INDEX.exists():
        return {}
    try:
        loaded = json.loads(TRACE_STRUCTURER_VARIANT_INDEX.read_text() or "{}")
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _variant_identity_key(session_id: str, source_window: str, turn: dict | None, variant: str) -> str:
    if not isinstance(turn, dict):
        return ""
    prompt_sha16 = str(turn.get("prompt_sha16") or "")
    turn_index = turn.get("turn_index")
    if not session_id or not source_window or not prompt_sha16 or turn_index is None:
        return ""
    return f"session={session_id}|window={source_window}|prompt={prompt_sha16}|turn={turn_index}|variant={variant}"


def _variant_artifacts_for_turn(
    variant_index: dict[str, Any],
    session_id: str,
    turn: dict | None,
) -> dict[str, Any]:
    sessions = variant_index.get("sessions") if isinstance(variant_index, dict) else {}
    session_artifacts = (sessions or {}).get(session_id) if isinstance(sessions, dict) else None
    if not isinstance(session_artifacts, dict):
        return {}
    selected: dict[str, Any] = {}
    selected_by_identity: dict[str, Any] = {}
    by_identity = session_artifacts.get("by_source_identity")
    if isinstance(by_identity, dict):
        for source_window in ("latest_prompt_cycle", "selected_turn", "full_thread"):
            for variant in ("trace_capsule", "closeout_report"):
                key = _variant_identity_key(session_id, source_window, turn, variant)
                if not key:
                    continue
                identity_artifacts = by_identity.get(key)
                if not isinstance(identity_artifacts, dict):
                    continue
                selected_by_identity[key] = identity_artifacts
                if variant in identity_artifacts:
                    selected.setdefault(variant, identity_artifacts[variant])
    for variant in ("trace_capsule", "closeout_report", "packet", "denoised", "compact_json"):
        artifact = session_artifacts.get(variant)
        if isinstance(artifact, dict):
            selected.setdefault(variant, artifact)
    if selected_by_identity:
        selected["by_source_identity"] = selected_by_identity
    return selected


def _trace_window_header(turn: Turn, source_window: str) -> str:
    trace_window = (turn.source_ref or {}).get("trace_window")
    if not isinstance(trace_window, dict):
        return f"window: {source_window} turns={turn.turn_index}-{turn.turn_index} count=1 mode={source_window}"
    count = int(trace_window.get("turn_count") or 1)
    start = trace_window.get("start_turn_index") or turn.turn_index
    end = trace_window.get("end_turn_index") or turn.turn_index
    mode = trace_window.get("mode") or source_window
    display_source_window = source_window
    if mode == "single_turn":
        mode = "selected_turn"
    if source_window == "latest_prompt_cycle" and mode == "selected_turn":
        mode = "latest_prompt_cycle"
    return f"window: {display_source_window} turns={start}-{end} count={count} mode={mode}"


def _trace_display_source_window(turn: Turn, source_window: str) -> str:
    return source_window


def _trace_thread_totality(source_window: str) -> str:
    if source_window == "full_thread":
        return "full_thread_detailed"
    if source_window == "full_thread_concise":
        return "full_thread_compact_summary"
    if source_window == "selected_turn":
        return "selected_turn_only"
    if source_window == "latest_prompt_cycle":
        return "latest_response_bundle_only"
    return "unknown"


def _trace_full_thread_available(turn: Turn, display_source_window: str) -> bool:
    trace_window = (turn.source_ref or {}).get("trace_window")
    full_thread = (turn.source_ref or {}).get("full_thread_trace_window") or (turn.source_ref or {}).get("full_thread")
    if display_source_window in {"full_thread", "full_thread_concise"}:
        return True
    if isinstance(full_thread, dict) and int(full_thread.get("turn_count") or 0) > 1:
        return True
    if isinstance(trace_window, dict) and int(trace_window.get("full_thread_turn_count") or 0) > 1:
        return True
    return False


def _trace_window_bounds(turn: Turn) -> dict[str, int | str]:
    trace_window = (turn.source_ref or {}).get("trace_window") or {}
    if not isinstance(trace_window, dict):
        return {
            "mode": "selected_turn",
            "start_turn_index": int(turn.turn_index or 0),
            "end_turn_index": int(turn.turn_index or 0),
            "turn_count": 1,
        }
    return {
        "mode": str(trace_window.get("mode") or "selected_turn"),
        "start_turn_index": int(trace_window.get("start_turn_index") or turn.turn_index or 0),
        "end_turn_index": int(trace_window.get("end_turn_index") or turn.turn_index or 0),
        "turn_count": int(trace_window.get("turn_count") or 1),
    }


def _trace_full_thread_bounds(turn: Turn) -> dict[str, int | str]:
    full_thread = (turn.source_ref or {}).get("full_thread_trace_window") or (turn.source_ref or {}).get("full_thread") or {}
    if not isinstance(full_thread, dict):
        return _trace_window_bounds(turn)
    return {
        "mode": str(full_thread.get("mode") or "full_thread"),
        "start_turn_index": int(full_thread.get("start_turn_index") or turn.turn_index or 0),
        "end_turn_index": int(full_thread.get("end_turn_index") or turn.turn_index or 0),
        "turn_count": int(full_thread.get("turn_count") or 1),
    }


def _file_line_count(path: Path) -> int | None:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def _capsule_scope_integrity(
    *,
    turn: Turn,
    display_source_window: str,
    source_sha16: str,
    source_watermark: dict[str, Any],
    include_raw_sidecar: bool,
    raw_sidecar_bytes: int,
    trace_capsule_bytes: int,
) -> dict[str, Any]:
    source_path = Path(turn.session_file) if turn.session_file else Path()
    source_ref = turn.source_ref or {}
    source_bytes = int(
        source_watermark.get("size_bytes")
        or source_ref.get("session_file_size_bytes")
        or (source_path.stat().st_size if source_path.exists() else 0)
        or 0
    )
    source_line_count = _file_line_count(source_path) if source_path.exists() else None
    selected_bounds = _trace_window_bounds(turn)
    full_bounds = _trace_full_thread_bounds(turn)
    source_records = len(set(int(i) for i in turn.source_record_indices if isinstance(i, int)))
    if source_records <= 0:
        source_records = int(source_ref.get("record_count_in_turn") or 0)
    projection_ratio = None
    if source_bytes > 0 and trace_capsule_bytes > 0:
        projection_ratio = round(trace_capsule_bytes / source_bytes, 4)
    warnings: list[str] = []
    if display_source_window == "full_thread" and source_bytes > 0 and trace_capsule_bytes > 0 and trace_capsule_bytes < source_bytes:
        warnings.append("full_thread_detailed_is_projection_not_provider_byte_lossless")
    if include_raw_sidecar and raw_sidecar_bytes <= 0:
        warnings.append("raw_sidecar_declared_but_empty")
    status = "full_provider_session_window_projected"
    if display_source_window in {"selected_turn", "latest_prompt_cycle"}:
        status = "selected_provider_window_projected"
    elif display_source_window == "full_thread_concise":
        status = "full_provider_session_compact_projected"
    return {
        "schema_version": "agent_trace_scope_integrity_v1",
        "status": status,
        "copy_scope": display_source_window,
        "thread_totality": _trace_thread_totality(display_source_window),
        "scope_unit": "provider_session_turn_window",
        "provider_byte_lossless": False,
        "copied_source_lossless": True,
        "provider_forensic_available": bool(turn.session_file and source_path.exists()),
        "source_truth_boundary": "trace capsule is a projection; provider byte replay requires the provider session JSONL",
        "warnings": warnings,
        "provider_session": {
            "provider": turn.provider,
            "session_id": turn.session_id,
            "session_file": turn.session_file,
            "source_file_bytes": source_bytes,
            "source_file_line_count": source_line_count,
            "source_records_in_window": source_records,
            "source_watermark_id": source_watermark.get("watermark_id") or "",
            "source_tail_sha16": source_watermark.get("tail_sha16") or "",
            "selected_turn_index": turn.turn_index,
            "selected_bounds": selected_bounds,
            "full_thread_bounds": full_bounds,
        },
        "projection": {
            "artifact_kind": "trace_capsule_text",
            "density_tier": 1,
            "bytes": trace_capsule_bytes,
            "source_sha16": source_sha16,
            "artifact_to_provider_source_ratio": projection_ratio,
            "event_stream_omitted": True,
            "large_bodies_omitted": True,
        },
        "raw_sidecar": {
            "kind": "inline_trace_paste",
            "available": include_raw_sidecar,
            "bytes": raw_sidecar_bytes if include_raw_sidecar else 0,
            "sha16": source_sha16 if include_raw_sidecar else "",
            "provider_byte_lossless": False,
            "copied_source_lossless": include_raw_sidecar,
        },
    }


def _capsule_scope_integrity_section_lines(receipt: dict[str, Any]) -> list[str]:
    provider = receipt.get("provider_session") or {}
    projection = receipt.get("projection") or {}
    raw_sidecar = receipt.get("raw_sidecar") or {}
    selected = provider.get("selected_bounds") or {}
    full = provider.get("full_thread_bounds") or {}
    warnings = ",".join(receipt.get("warnings") or []) or "none"
    line_count = provider.get("source_file_line_count")
    source_lines = line_count if line_count is not None else "unknown"
    ratio = projection.get("artifact_to_provider_source_ratio")
    ratio_text = f"{float(ratio):.4f}" if isinstance(ratio, (int, float)) else str(ratio or "none")
    return [
        "SCOPE_INTEGRITY",
        (
            f"scope_integrity: status={receipt.get('status') or ''} "
            f"copy_scope={receipt.get('copy_scope') or ''} "
            f"thread_totality={receipt.get('thread_totality') or ''} "
            f"scope_unit={receipt.get('scope_unit') or ''} "
            f"provider_byte_lossless={'true' if receipt.get('provider_byte_lossless') else 'false'} "
            f"copied_source_lossless={'true' if receipt.get('copied_source_lossless') else 'false'} "
            f"warnings={warnings}"
        ),
        (
            f"provider_source: provider={provider.get('provider') or ''} "
            f"session={_short_session_tag(str(provider.get('session_id') or ''))} "
            f"bytes={provider.get('source_file_bytes') or 0} "
            f"lines={source_lines} "
            f"records_in_window={provider.get('source_records_in_window') or 0} "
            f"selected_window={selected.get('start_turn_index')}-{selected.get('end_turn_index')} "
            f"full_thread={full.get('start_turn_index')}-{full.get('end_turn_index')} "
            f"full_count={full.get('turn_count') or 0}"
        ),
        (
            f"projection_source: trace_capsule_bytes={projection.get('bytes') or 0} "
            f"artifact_to_provider_source_ratio={ratio_text} "
            f"event_stream_omitted={'true' if projection.get('event_stream_omitted') else 'false'} "
            f"large_bodies_omitted={'true' if projection.get('large_bodies_omitted') else 'false'}"
        ),
        (
            f"raw_sidecar_source: available={'true' if raw_sidecar.get('available') else 'false'} "
            f"kind={raw_sidecar.get('kind') or ''} "
            f"bytes={raw_sidecar.get('bytes') or 0} "
            f"provider_byte_lossless={'true' if raw_sidecar.get('provider_byte_lossless') else 'false'} "
            f"copied_source_lossless={'true' if raw_sidecar.get('copied_source_lossless') else 'false'}"
        ),
    ]


def _capsule_repo_cut_plane() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--verify", "HEAD"],
            text=True,
            capture_output=True,
            timeout=2,
        )
    except Exception as exc:
        return {"schema_version": "agent_trace_repo_cut_plane_v1", "head": "", "state": f"unavailable:{type(exc).__name__}"}
    head = proc.stdout.strip() if proc.returncode == 0 else ""
    return {
        "schema_version": "agent_trace_repo_cut_plane_v1",
        "head": head,
        "head_short": head[:12],
        "state": "captured" if head else "unavailable",
    }


def _capsule_status_label(status_text: str, display_source_window: str) -> str:
    if status_text != "complete":
        return status_text
    if display_source_window == "full_thread":
        return "full_thread_complete"
    if display_source_window == "full_thread_concise":
        return "full_thread_concise_complete"
    if display_source_window == "latest_prompt_cycle":
        return "latest_prompt_cycle_complete"
    return "selected_turn_complete"


def _capsule_scope_semantics(
    *,
    status_text: str,
    display_source_window: str,
    full_thread_available: bool,
    selected_window_only: bool,
    no_edit_claim_allowed: bool,
) -> dict[str, Any]:
    global_none_claims_allowed = not selected_window_only
    completion_scope = (
        "full_thread"
        if display_source_window in {"full_thread", "full_thread_concise"}
        else display_source_window
    )
    return {
        "schema_version": "agent_trace_scope_semantics_v1",
        "status_raw": status_text,
        "status_label": _capsule_status_label(status_text, display_source_window),
        "completion_scope": completion_scope,
        "absence_scope": "full_thread" if global_none_claims_allowed else "selected_window",
        "none_scope": "full_thread" if global_none_claims_allowed else "selected_window",
        "copy_scope": display_source_window,
        "full_thread_available": full_thread_available,
        "selected_window_only": selected_window_only,
        "global_none_claims_allowed": global_none_claims_allowed,
        "unsafe_global_none_claims_blocked": not global_none_claims_allowed,
        "no_edit_claim_allowed": no_edit_claim_allowed,
        "full_thread_absence_claim": "allowed" if global_none_claims_allowed else "not_claimed_in_selected_window_bundle",
    }


def _capsule_scoped_absence_lines(key: str, summary: str, scope_semantics: dict[str, Any]) -> list[str]:
    if summary != "none":
        return [f"{key}: {summary}"]
    if scope_semantics.get("global_none_claims_allowed"):
        return [f"{key}: none"]
    return [
        f"{key}_selected_window: none",
        f"{key}_global: not_claimed",
    ]


def _capsule_scoped_absence_value(summary: str, scope_semantics: dict[str, Any]) -> str:
    if summary != "none":
        return summary
    if scope_semantics.get("global_none_claims_allowed"):
        return "none"
    return "selected_window_none/global_not_claimed"


def _capsule_open_claim_lines(turn: Turn, scope_semantics: dict[str, Any]) -> list[str]:
    if not turn.is_complete:
        return [turn.partial_reason or "trace still in progress"]
    if scope_semantics.get("global_none_claims_allowed"):
        return ["open: none captured"]
    return [
        "open_selected_window: none captured",
        "open_global: not_claimed",
    ]


def _capsule_trace_cut_receipt(
    *,
    turn: Turn,
    requested_source_window: str,
    display_source_window: str,
    recommended_scope: str,
    source_sha16: str,
    source_watermark: dict[str, Any],
    full_thread_available: bool,
    selected_window_only: bool,
    final_delta: dict[str, Any],
    include_raw_sidecar: bool,
    scope_semantics: dict[str, Any],
) -> dict[str, Any]:
    selected_bounds = _trace_window_bounds(turn)
    full_bounds = _trace_full_thread_bounds(turn)
    selected_end = int(selected_bounds.get("end_turn_index") or turn.turn_index or 0)
    full_end = int(full_bounds.get("end_turn_index") or selected_end)
    tail_state = "at_thread_tail"
    if full_thread_available and selected_window_only and selected_end < full_end:
        tail_state = "not_thread_tail"
    consistency = "consistent_cut"
    if tail_state == "not_thread_tail":
        consistency = "stale_selected_window_not_latest_thread_turn"
    elif full_thread_available and selected_window_only:
        consistency = "scope_deficit_full_thread_available"
    provider_plane = {
        "provider": turn.provider,
        "session_id": turn.session_id,
        "session_file": turn.session_file,
        "source_watermark_id": source_watermark.get("watermark_id") or "",
        "selected_prompt_sha16": turn.prompt_sha256_16,
        "selected_turn_index": turn.turn_index,
        "selected_bounds": selected_bounds,
        "full_thread_bounds": full_bounds,
        "tail_state": tail_state,
    }
    repo_plane = _capsule_repo_cut_plane()
    cut_material = {
        "provider": provider_plane,
        "repo": repo_plane,
        "source_sha16": source_sha16,
        "requested_source_window": requested_source_window,
        "display_source_window": display_source_window,
        "recommended_scope": recommended_scope,
        "final_delta_state": final_delta.get("state") or "",
        "final_delta_commit": final_delta.get("commit") or "",
    }
    return {
        "schema_version": "agent_trace_cut_receipt_v1",
        "cut_id": _sha16(json.dumps(cut_material, sort_keys=True, ensure_ascii=False)),
        "requested_source_window": requested_source_window,
        "resolved_copy_scope": display_source_window,
        "recommended_scope": recommended_scope,
        "selected_window_only": selected_window_only,
        "full_thread_available": full_thread_available,
        "cut_consistency": consistency,
        "provider_plane": provider_plane,
        "repo_plane": repo_plane,
        "source_sha16": source_sha16,
        "raw_sidecar_available_to_type_a": include_raw_sidecar,
        "raw_sidecar_available_to_type_b": False,
        "unsafe_global_none_claims_blocked": bool(scope_semantics.get("unsafe_global_none_claims_blocked")),
    }


def _capsule_trace_provenance_attestation(
    *,
    turn: Turn,
    trace_cut_receipt: dict[str, Any],
    final_delta: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
    include_raw_sidecar: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "agent_trace_provenance_attestation_v1",
        "subject": {
            "kind": "trace_capsule_text",
            "schema_version": TRACE_CAPSULE_SCHEMA_VERSION,
            "sha16": "artifact_envelope_subject",
            "hash_mode": "artifact_envelope_after_write",
        },
        "builder": {
            "tool": "tools/meta/observability/cli_prompt_trace.py",
            "repo_head": (trace_cut_receipt.get("repo_plane") or {}).get("head") or "",
            "schema_version": TRACE_CAPSULE_SCHEMA_VERSION,
        },
        "invocation": {
            "provider": turn.provider,
            "session_id": turn.session_id,
            "turn_index": turn.turn_index,
            "requested_source_window": trace_cut_receipt.get("requested_source_window") or "",
            "resolved_copy_scope": trace_cut_receipt.get("resolved_copy_scope") or "",
        },
        "materials": [
            {
                "id": "provider_session",
                "kind": "session_jsonl_watermark",
                "watermark_id": (trace_cut_receipt.get("provider_plane") or {}).get("source_watermark_id") or "",
            },
            {
                "id": "raw_sidecar",
                "kind": "inline_trace_paste" if include_raw_sidecar else "not_materialized",
                "sha16": trace_cut_receipt.get("source_sha16") or "",
            },
            {
                "id": "final_delta",
                "kind": final_delta.get("state") or "not_captured",
                "authority": final_delta.get("authority") or "",
                "commit": final_delta.get("commit") or "",
            },
            {
                "id": "source_excerpts",
                "kind": "bounded_source_excerpts",
                "count": int(source_excerpt_stats.get("count") or 0),
                "omitted": int(source_excerpt_stats.get("omitted") or 0),
            },
        ],
        "attestation": "materials_named_subject_hash_bound_in_artifact_envelope",
    }


def _capsule_latest_selection_receipt(
    *,
    turn: Turn,
    trace_cut_receipt: dict[str, Any],
    source_watermark: dict[str, Any],
) -> dict[str, Any]:
    provider = trace_cut_receipt.get("provider_plane") or {}
    selected_bounds = provider.get("selected_bounds") or {}
    full_bounds = provider.get("full_thread_bounds") or selected_bounds
    selected_turn = int(provider.get("selected_turn_index") or turn.turn_index or 0)
    selected_end = int(selected_bounds.get("end_turn_index") or selected_turn)
    full_end = int(full_bounds.get("end_turn_index") or selected_end)
    selected_is_thread_tail = selected_end >= full_end and str(provider.get("tail_state") or "") != "not_thread_tail"
    selected_is_latest_completed_response = bool(selected_is_thread_tail and turn.is_complete)
    active_defeaters: list[str] = []
    if not selected_is_thread_tail:
        active_defeaters.append("not_thread_tail")
    if not turn.is_complete:
        active_defeaters.append("response_in_progress")
    candidate_count = int(full_bounds.get("turn_count") or selected_bounds.get("turn_count") or 1)
    candidate_source = (
        "full_thread_trace_window"
        if trace_cut_receipt.get("full_thread_available")
        else "selected_trace_window"
    )
    return {
        "schema_version": "agent_trace_latest_selection_receipt_v1",
        "selected_turn_index": selected_turn,
        "selected_window": {
            "start_turn_index": int(selected_bounds.get("start_turn_index") or selected_turn),
            "end_turn_index": selected_end,
            "turn_count": int(selected_bounds.get("turn_count") or 1),
        },
        "candidate_set": {
            "source": candidate_source,
            "start_turn_index": int(full_bounds.get("start_turn_index") or selected_turn),
            "end_turn_index": full_end,
            "turn_count": candidate_count,
            "completed_response_count": candidate_count if turn.is_complete else max(0, candidate_count - 1),
        },
        "ordering_keys": ["session_jsonl_order", "turn_index", "completed_at"],
        "selected_is_thread_tail": selected_is_thread_tail,
        "selected_is_latest_completed_response": selected_is_latest_completed_response,
        "latest_prompt_pending_response": not turn.is_complete,
        "ambiguity_override_used": False,
        "reparse_before_copy": bool(source_watermark.get("watermark_id")),
        "watermark_id": source_watermark.get("watermark_id") or "",
        "defeaters": active_defeaters,
    }


_CAPSULE_EVIDENCE_LOCATOR_MAP = {
    "turn.is_complete": "EV.turn_completion_state",
    "copy_scope": "EV.trace_scope",
    "final_assistant_text_or_commit_title": "EV.final_assistant_or_commit",
    "edit_rows": "EV.edit_event_log",
    "final_delta": "EV.final_delta",
    "classified_terminal_checks": "EV.terminal_checks",
    "owner_scope_terminal_checks": "EV.owner_terminal_checks",
    "governance_receipts": "EV.governance_receipts",
    "commit_and_dirty_residual_classification": "EV.final_delta",
    "task_ledger_and_projection_receipts": "EV.governance_receipts",
    "ambient_terminal_rows": "EV.terminal_checks",
    "ambient_warning_classifier": "EV.terminal_checks",
    "residual_classifier": "EV.residual_register",
    "validation_process_residual_classifier": "EV.validation_process_residual_register",
    "task_ledger_receipts": "EV.governance_receipts",
    "release_candidate_classifier": "EV.governance_receipts",
    "terminal_check_ordering": "EV.terminal_checks",
    "guarded_refusal_classifier": "EV.terminal_checks",
    "projection_artifact_classifier": "EV.projection_artifacts",
    "residual_mention_classifier": "EV.residual_register",
    "release_authority_classifier": "EV.governance_receipts",
    "classified_checks": "EV.terminal_checks",
    "terminal_checks": "EV.terminal_checks",
    "owner_terminal_checks": "EV.owner_terminal_checks",
    "validation_classifier": "EV.terminal_checks",
    "terminal_governance_rows": "EV.governance_receipts",
    "diagnostic_rows": "EV.command_returns",
    "assistant_visible_messages": "EV.assistant_visible_messages",
    "turn.completion_state": "EV.turn_completion_state",
    "producer_state": "EV.producer_derived_summary",
}


def _capsule_claim_evidence_locator(label: str) -> str:
    parts = [part.strip() for part in re.split(r"[+,]", str(label or "")) if part.strip()]
    locators: list[str] = []
    for part in parts or ["producer_state"]:
        locator = _CAPSULE_EVIDENCE_LOCATOR_MAP.get(part)
        if not locator:
            locator = _CAPSULE_EVIDENCE_LOCATOR_MAP.get(part.split(":", 1)[0], "EV.producer_derived_summary")
        if locator not in locators:
            locators.append(locator)
    return ",".join(locators)


def _capsule_claim_source_map(summary_claims: list[dict[str, str]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, claim in enumerate(summary_claims, start=1):
        row = dict(claim)
        row["row_id"] = f"CSM{index:03d}"
        row.setdefault("scope", "selected_window")
        raw_evidence = str(row.get("evidence") or "producer_state")
        row["source_evidence_label"] = raw_evidence
        row["evidence"] = _capsule_claim_evidence_locator(raw_evidence)
        row.setdefault("cannot_prove", "none")
        row.setdefault("render_policy", "verbatim_if_evidence_scope_matches")
        rows.append(row)
    return {
        "schema_version": "agent_trace_claim_source_map_v1",
        "row_count": len(rows),
        "covered_summary_claims": [row.get("claim", "") for row in rows],
        "uncovered_summary_claims": [],
        "rows": rows,
    }


def _capsule_claim_value(value: Any) -> str:
    text = _capsule_clean_text(" ".join(str(value or "").split()))
    if len(text) > 180:
        text = f"{text[:150].rstrip()}...sha16={_sha16(text)}"
    return text.replace('"', "'")


def _capsule_copy_readiness_vector(
    *,
    copy_readiness_state: str,
    copy_readiness_blockers: list[str],
    copy_readiness_warnings: list[str],
    scope_semantics: dict[str, Any],
    final_delta_attached: bool,
    diff_reconciler_status: str,
    claim_source_map: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
    source_context_readiness: dict[str, Any],
    latest_selection_receipt: dict[str, Any],
) -> dict[str, Any]:
    scope_state = "amber" if scope_semantics.get("selected_window_only") and scope_semantics.get("full_thread_available") else "green"
    final_delta_state = "green" if final_delta_attached else ("amber" if diff_reconciler_status == "no_edits_captured_in_scoped_window" else "red")
    claim_map_state = "green" if not claim_source_map.get("uncovered_summary_claims") else "red"
    source_context_budget_deficit = (
        str(source_context_readiness.get("demand") or "") == "required_by_type_b_decision"
        and int(source_context_readiness.get("high_regret_missing") or 0) > 0
    )
    budget_state = (
        "amber"
        if source_context_budget_deficit or int(source_excerpt_stats.get("omitted") or 0) > 0
        else "green"
    )
    latest_state = "green" if latest_selection_receipt.get("selected_is_latest_completed_response") else (
        "amber" if latest_selection_receipt.get("latest_prompt_pending_response") else "red"
    )
    return {
        "schema_version": "agent_trace_epistemic_readiness_vector_v1",
        "overall": copy_readiness_state,
        "scope": scope_state,
        "final_delta": final_delta_state,
        "latest_selection": latest_state,
        "claim_source_map": claim_map_state,
        "sidecar_portability": "amber",
        "global_none_claims": "green",
        "budget": budget_state,
        "portable_type_b": "green" if str(source_context_readiness.get("overall") or "green") == "green" else "amber",
        "parser_roundtrip": "pending",
        "blockers": copy_readiness_blockers,
        "warnings": copy_readiness_warnings,
    }


def _capsule_parser_roundtrip_readiness(trace_self_parse_receipt: Mapping[str, Any]) -> str:
    downstream_status = str(trace_self_parse_receipt.get("downstream_parser_mjs_roundtrip") or "")
    round_trip_status = str(trace_self_parse_receipt.get("round_trip_status") or "")
    if downstream_status == "pass" and round_trip_status == "pass":
        return "green"
    if downstream_status in {"", "pending_artifact_write", "unavailable", "not_run"}:
        return "amber"
    return "red"


def _capsule_trace_contract_validation(trace_self_parse_receipt: Mapping[str, Any]) -> str:
    readiness = _capsule_parser_roundtrip_readiness(trace_self_parse_receipt)
    if readiness == "green":
        return "pass"
    if readiness == "red":
        return "fail"
    return "blocked"


def _capsule_trace_contract_final_validation(
    final_validation: str,
    *,
    trace_contract_validation: str,
    source_validation: str,
    publication_candidate_execution_state: str,
) -> str:
    if trace_contract_validation != "fail":
        return final_validation
    if source_validation.startswith("pass"):
        if publication_candidate_execution_state not in {"none", ""}:
            return "source_pass_trace_contract_failed_publication_held"
        return "source_pass_trace_contract_failed"
    return "trace_contract_failed"


def _capsule_update_claim_source_map_value(
    claim_source_map: dict[str, Any],
    claim: str,
    value: Any,
) -> None:
    rows = claim_source_map.get("rows")
    if not isinstance(rows, list):
        return
    for row in rows:
        if isinstance(row, dict) and row.get("claim") == claim:
            row["value"] = str(value)
            return


def _capsule_copy_readiness_vector_line(vector: Mapping[str, Any]) -> str:
    return (
        f"copy_readiness_vector: overall={vector.get('overall')} "
        f"scope={vector.get('scope')} "
        f"final_delta={vector.get('final_delta')} "
        f"latest_selection={vector.get('latest_selection')} "
        f"claim_source_map={vector.get('claim_source_map')} "
        f"sidecar_portability={vector.get('sidecar_portability')} "
        f"global_none_claims={vector.get('global_none_claims')} "
        f"budget={vector.get('budget')} "
        f"portable_type_b={vector.get('portable_type_b')} "
        f"parser_roundtrip={vector.get('parser_roundtrip')}"
    )


def _capsule_trace_self_parse_receipt(
    *,
    trace_cut_receipt: dict[str, Any],
    scope_semantics: dict[str, Any],
    claim_source_map: dict[str, Any],
    final_delta_attached: bool,
    edit_event_log_attached: bool,
) -> dict[str, Any]:
    producer_status = "pass" if not claim_source_map.get("uncovered_summary_claims") else "fail"
    return {
        "schema_version": "agent_trace_self_parse_receipt_v1",
        "parser": "producer_structural_self_check+downstream_contract",
        "producer_structural_self_check": producer_status,
        "downstream_parser_mjs_roundtrip": "pending_artifact_write",
        "ui_ingest_contract_parse": "not_run",
        "native_receipt_parse": "pending_parser_projection",
        "round_trip_status": "producer_pass_downstream_pending" if producer_status == "pass" else "producer_fail",
        "cut_id": trace_cut_receipt.get("cut_id") or "",
        "parsed_scope": scope_semantics.get("copy_scope") or "",
        "parsed_status_label": scope_semantics.get("status_label") or "",
        "parsed_final_delta_attached": final_delta_attached,
        "parsed_edit_event_log_attached": edit_event_log_attached,
        "summary_absence_claims_unqualified": 0 if scope_semantics.get("unsafe_global_none_claims_blocked") else "not_applicable",
        "claim_source_map_complete": not bool(claim_source_map.get("uncovered_summary_claims")),
    }


def _capsule_budget_solver_receipt(
    source_excerpt_stats: dict[str, Any],
    *,
    source_context_demand: dict[str, Any] | None = None,
    source_context_deficit: dict[str, Any] | None = None,
    source_context_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    omitted = int(source_excerpt_stats.get("omitted") or 0)
    agent_requested_omitted = int(source_excerpt_stats.get("agent_requested_omitted_refs") or 0)
    prompt_refs = int(source_excerpt_stats.get("prompt_file_refs") or 0)
    emitted = int(source_excerpt_stats.get("count") or 0)
    source_context_demand = source_context_demand or {}
    source_context_deficit = source_context_deficit or {}
    source_context_readiness = source_context_readiness or {}
    demand_state = str(source_context_demand.get("state") or "none")
    deficit_rows = [row for row in source_context_deficit.get("rows") or [] if isinstance(row, dict)]
    decision_required = demand_state == "required_by_type_b_decision"
    decision_deficit_rows = [
        row
        for row in deficit_rows
        if decision_required or "type_b_decision" in str(row.get("why_needed") or "")
    ]
    source_context_high_regret_missing = max(
        len(decision_deficit_rows),
        int(source_context_readiness.get("high_regret_missing") or 0) if decision_required else 0,
    )
    dropped_requested_paths = {
        _capsule_public_trace_path(str(row.get("path") or ""))
        for row in source_excerpt_stats.get("agent_requested_drop_reasons", []) or []
        if isinstance(row, dict) and row.get("path")
    }
    overlap_count = sum(
        1
        for row in decision_deficit_rows
        if _capsule_public_trace_path(str(row.get("missing_path") or "")) in dropped_requested_paths
    )
    source_context_high_without_requested_overlap = max(0, source_context_high_regret_missing - overlap_count)
    source_context_medium_missing = max(0, len(deficit_rows) - len(decision_deficit_rows))

    def source_context_ref(row: dict[str, Any]) -> str:
        deficit_id = str(row.get("deficit_id") or "SCD")
        path = _capsule_public_trace_path(str(row.get("missing_path") or "unknown"))
        anchor = str(row.get("missing_anchor") or "unknown_anchor")
        return f"{deficit_id}:{path}#{anchor}"

    top_omitted_refs: list[str] = []
    for row in decision_deficit_rows:
        top_omitted_refs.append(source_context_ref(row))
    for row in source_excerpt_stats.get("agent_requested_drop_reasons", []) or []:
        if isinstance(row, dict):
            command_id = str(row.get("command_id") or row.get("row_id") or "unknown")
            reason = str(row.get("reason") or "omitted")
            top_omitted_refs.append(f"{command_id}:{reason}")
        elif row:
            top_omitted_refs.append(str(row))
    if max(0, omitted - agent_requested_omitted):
        top_omitted_refs.append("source_excerpt_budget:non_requested_omissions")
    return {
        "schema_version": "agent_trace_budget_solver_receipt_v1",
        "proof_set_before_route_context": True,
        "minimum_proof_set": [
            "TRACE_CUT_RECEIPT",
            "TRACE_PROVENANCE_ATTESTATION",
            "CLAIM_SOURCE_MAP",
            "FINAL_DELTA",
            "EDIT_EVENT_LOG",
            "EVIDENCE_MANIFEST",
            "SOURCE_CONTEXT_DEMAND",
            "SOURCE_SLICE_REQUESTS",
            "SOURCE_CONTEXT_DEFICIT",
        ],
        "proof_obligations_total": 11,
        "proof_obligations_embedded": 11,
        "proof_obligations_sidecar_only": 0,
        "proof_obligations_missing": 0,
        "source_excerpt_count": emitted,
        "source_excerpt_omitted": omitted,
        "agent_requested_omitted": agent_requested_omitted,
        "source_context_demand_state": demand_state,
        "source_context_active_deficit": bool(decision_required and source_context_high_regret_missing),
        "source_context_high_regret_missing": source_context_high_regret_missing,
        "source_context_deficit_count": len(deficit_rows),
        "budget_regret_high": agent_requested_omitted + source_context_high_without_requested_overlap,
        "budget_regret_medium": max(0, omitted - agent_requested_omitted) + source_context_medium_missing,
        "budget_regret_low": max(0, prompt_refs - emitted - omitted),
        "top_omitted_decision_refs": top_omitted_refs[:5],
        "practical_budget": "~150KB",
    }


def _capsule_trace_context_ids(
    *,
    turn: Turn,
    trace_cut_receipt: dict[str, Any],
    source_sha16: str,
) -> dict[str, str]:
    trace_context_id = _sha16("|".join([
        str(turn.provider),
        str(turn.session_id),
        str(turn.turn_index),
        str(turn.prompt_sha256_16),
        str(trace_cut_receipt.get("cut_id") or ""),
        source_sha16,
    ]))
    return {
        "schema_version": "agent_trace_context_ids_v1",
        "trace_context_id": trace_context_id,
        "cut_id": str(trace_cut_receipt.get("cut_id") or ""),
        "session_tag": _short_session_tag(turn.session_id),
        "prompt_sha16": turn.prompt_sha256_16,
        "source_sha16": source_sha16,
    }


def _capsule_title_authority_warning(title: str) -> str:
    stripped = str(title or "").strip()
    if re.fullmatch(r"\d+(?:\s*[,/ -]\s*\d+)?", stripped):
        return f"ordinal_title_not_semantic raw={_capsule_clean_text(stripped)} source=title_numeric_token"
    start, end, source = _mission_ordinal(title)
    if start is None or end is None:
        return "none"
    return f"ordinal_title_not_semantic ordinal={start},{end} source={source}"


def _capsule_title_authority(
    title: str,
    *,
    turn: Turn,
    commit_title: str = "",
) -> dict[str, Any]:
    raw_title = _capsule_clean_text(str(title or "").strip())
    warning = _capsule_title_authority_warning(raw_title)
    prompt_fallback = _prompt_title_from_text(turn.prompt_text, limit=120)
    display_title = raw_title
    display_source = "session_title"
    confidence = "high"
    if warning != "none":
        display_title = _capsule_clean_text(commit_title or prompt_fallback or f"{turn.provider} turn {turn.turn_index}")
        display_source = "commit_title" if commit_title else ("current_turn_prompt_title" if prompt_fallback else "turn_identity")
        confidence = "medium"
    if not display_title:
        display_title = f"{turn.provider} turn {turn.turn_index}"
        display_source = "turn_identity"
        confidence = "low"
    return {
        "schema_version": "agent_trace_title_authority_v1",
        "raw_title": raw_title,
        "display_title": display_title,
        "display_title_source": display_source,
        "warning": warning,
        "title_confidence": confidence,
    }


def _capsule_evidence_node_graph(
    *,
    trace_cut_receipt: dict[str, Any],
    latest_selection_receipt: dict[str, Any],
    title_authority: dict[str, Any],
    trace_provenance_attestation: dict[str, Any],
    claim_source_map: dict[str, Any],
    final_delta: dict[str, Any],
    final_delta_attached: bool,
    edit_event_log_attached: bool,
    terminal_check_count: int,
    owner_terminal_check_count: int,
    evidence_manifest: dict[str, Any],
    source_excerpt_stats: dict[str, Any],
    include_raw_sidecar: bool,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []

    def add(
        node_id: str,
        *,
        kind: str,
        locator: str,
        sufficient_for: list[str],
        insufficient_for: list[str] | None = None,
        status: str = "present",
    ) -> None:
        nodes.append({
            "id": node_id,
            "kind": kind,
            "locator": locator,
            "status": status,
            "sufficient_for": sufficient_for,
            "insufficient_for": insufficient_for or [],
        })

    add(
        "EV.trace_cut_receipt",
        kind="receipt",
        locator=f"TRACE_CUT_RECEIPT cut_id={trace_cut_receipt.get('cut_id') or ''}",
        sufficient_for=["cut_identity", "scope_boundary"],
    )
    add(
        "EV.latest_selection_receipt",
        kind="receipt",
        locator=(
            "LATEST_SELECTION_RECEIPT "
            f"selected_turn={latest_selection_receipt.get('selected_turn_index') or ''}"
        ),
        sufficient_for=["latest_identity"],
        insufficient_for=["full_thread_context"] if trace_cut_receipt.get("selected_window_only") else [],
    )
    add(
        "EV.trace_scope",
        kind="scope_fact",
        locator=(
            "TRACE_CUT_RECEIPT/trace_scope "
            f"resolved={trace_cut_receipt.get('resolved_copy_scope') or ''}"
        ),
        sufficient_for=["declared_scope"],
        insufficient_for=["global_absence"] if trace_cut_receipt.get("selected_window_only") else [],
    )
    add(
        "EV.turn_completion_state",
        kind="provider_fact",
        locator=(
            "LATEST_SELECTION_RECEIPT "
            f"latest_completed={latest_selection_receipt.get('selected_is_latest_completed_response')}"
        ),
        sufficient_for=["completion_state"],
    )
    add(
        "EV.title_authority",
        kind="producer_fact",
        locator=f"TITLE_AUTHORITY warning={title_authority.get('warning') or 'none'}",
        sufficient_for=["display_title"],
        insufficient_for=["semantic_title_authority"] if title_authority.get("warning") != "none" else [],
    )
    add(
        "EV.provenance_attestation",
        kind="attestation",
        locator=(
            "TRACE_PROVENANCE_ATTESTATION "
            f"subject_hash_mode={((trace_provenance_attestation.get('subject') or {}).get('hash_mode') or '')}"
        ),
        sufficient_for=["builder_materials"],
        insufficient_for=["provider_byte_replay"],
    )
    add(
        "EV.claim_source_map",
        kind="receipt",
        locator=f"CLAIM_SOURCE_MAP rows={claim_source_map.get('row_count') or 0}",
        sufficient_for=["summary_claim_traceability"],
    )
    add(
        "EV.final_delta",
        kind="diff_receipt",
        locator=f"FINAL_DELTA attached={final_delta_attached} state={final_delta.get('state') or 'not_captured'}",
        sufficient_for=["final_substrate_delta"] if final_delta_attached else [],
        insufficient_for=[] if final_delta_attached else ["final_substrate_delta"],
        status="present" if final_delta_attached else "absent",
    )
    add(
        "EV.edit_event_log",
        kind="edit_chronology",
        locator=f"EDIT_EVENT_LOG attached={edit_event_log_attached}",
        sufficient_for=["edit_attempt_chronology"] if edit_event_log_attached else [],
        insufficient_for=["final_substrate_delta"],
        status="present" if edit_event_log_attached else "absent",
    )
    add(
        "EV.terminal_checks",
        kind="validation_receipt",
        locator=f"SUMMARY/terminal_checks total={terminal_check_count}",
        sufficient_for=["validation_status"] if terminal_check_count else [],
        status="present" if terminal_check_count else "absent",
    )
    add(
        "EV.owner_terminal_checks",
        kind="validation_receipt",
        locator=f"SUMMARY/owner_scope_terminal_checks total={owner_terminal_check_count}",
        sufficient_for=["owner_scope_validation"] if owner_terminal_check_count else [],
        status="present" if owner_terminal_check_count else "absent",
    )
    add(
        "EV.governance_receipts",
        kind="receipt",
        locator="SUMMARY/governance_receipts",
        sufficient_for=["governance_status"],
    )
    add(
        "EV.residual_register",
        kind="classifier_output",
        locator="SUMMARY/open_*_residuals",
        sufficient_for=["residual_claims"],
    )
    add(
        "EV.validation_process_residual_register",
        kind="classifier_output",
        locator="SUMMARY/open_validation_process_residuals",
        sufficient_for=["validation_process_claims"],
    )
    add(
        "EV.evidence_manifest",
        kind="manifest",
        locator=f"EVIDENCE_MANIFEST rows={evidence_manifest.get('row_count') or 0}",
        sufficient_for=["evidence_carrier_inventory"],
    )
    add(
        "EV.source_excerpts",
        kind="bounded_source",
        locator=(
            "SOURCE_EXCERPTS "
            f"count={source_excerpt_stats.get('count') or 0} omitted={source_excerpt_stats.get('omitted') or 0}"
        ),
        sufficient_for=["selected_source_review"] if source_excerpt_stats.get("count") else [],
        insufficient_for=["full_source_review"] if source_excerpt_stats.get("omitted") else [],
        status="present" if source_excerpt_stats.get("count") else "absent",
    )
    add(
        "EV.raw_sidecar",
        kind="sidecar",
        locator="RAW_SIDECAR_MANIFEST inline_trace_paste" if include_raw_sidecar else "RAW_SIDECAR_MANIFEST not_materialized",
        sufficient_for=["copied_source_review"] if include_raw_sidecar else [],
        insufficient_for=["type_b_portability"] if include_raw_sidecar else ["raw_source_review"],
        status="present" if include_raw_sidecar else "absent",
    )
    add(
        "EV.command_returns",
        kind="command_return_index",
        locator="COMMAND_RETURNS",
        sufficient_for=["command_output_review"],
    )
    add(
        "EV.assistant_visible_messages",
        kind="message_excerpt",
        locator="VISIBLE_PROGRESS",
        sufficient_for=["visible_progress_claims"],
    )
    add(
        "EV.producer_derived_summary",
        kind="producer_projection",
        locator="SUMMARY",
        sufficient_for=["derived_summary_claims"],
        insufficient_for=["source_authority_without_ground_receipts"],
    )
    return {
        "schema_version": "agent_trace_evidence_node_graph_v1",
        "node_count": len(nodes),
        "nodes": nodes,
        "locator_rule": "locators_name_trace_sections_or_receipts; query_regex_never_goes_in_path_field",
    }


def _capsule_defeater_register(
    *,
    scope_semantics: dict[str, Any],
    latest_selection_receipt: dict[str, Any],
    title_authority: dict[str, Any],
    trace_self_parse_receipt: dict[str, Any],
    budget_solver_receipt: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    downstream_status = str(trace_self_parse_receipt.get("downstream_parser_mjs_roundtrip") or "")
    round_trip_status = str(trace_self_parse_receipt.get("round_trip_status") or "")
    downstream_failed = (
        downstream_status not in {"", "pass", "pending_artifact_write", "unavailable", "not_run"}
        or round_trip_status == "fail"
    )

    def add(
        defeater_id: str,
        *,
        status: str,
        threatens: list[str],
        evidence: list[str],
        mitigation: str,
    ) -> None:
        rows.append({
            "id": defeater_id,
            "status": status,
            "threatens": threatens,
            "evidence": evidence,
            "mitigation": mitigation,
        })

    add(
        "DTR.scope_deficit",
        status="active" if scope_semantics.get("selected_window_only") and scope_semantics.get("full_thread_available") else "refuted",
        threatens=["CLM.global_absence_guard", "CLM.full_context"],
        evidence=["EV.trace_scope", "EV.trace_cut_receipt"],
        mitigation="global_none_claims_blocked_and_reader_context_action_emitted",
    )
    add(
        "DTR.latest_not_tail",
        status="active" if not latest_selection_receipt.get("selected_is_thread_tail") else "refuted",
        threatens=["CLM.latest_selection"],
        evidence=["EV.latest_selection_receipt"],
        mitigation="request_latest_response_bundle_or_full_thread_tail",
    )
    add(
        "DTR.response_in_progress",
        status="active" if latest_selection_receipt.get("latest_prompt_pending_response") else "refuted",
        threatens=["CLM.latest_selection", "CLM.completion_state"],
        evidence=["EV.turn_completion_state"],
        mitigation="wait_for_completed_response_or_select_completed_turn",
    )
    add(
        "DTR.title_authority",
        status="active" if title_authority.get("warning") != "none" else "refuted",
        threatens=["CLM.title_authority"],
        evidence=["EV.title_authority"],
        mitigation="display_title_falls_back_to_prompt_or_commit_title",
    )
    add(
        "DTR.provenance_placeholder",
        status="refuted",
        threatens=["CLM.provenance"],
        evidence=["EV.provenance_attestation"],
        mitigation="rendered_text_uses_envelope_hash_mode_not_self_hash_placeholder",
    )
    add(
        "DTR.downstream_parser_pending",
        status="active" if downstream_status == "pending_artifact_write" else "refuted",
        threatens=["CLM.self_parse"],
        evidence=["EV.claim_source_map"],
        mitigation="artifact_writer_runs_parser_roundtrip_and_records_metadata_receipt",
    )
    add(
        "DTR.downstream_parser_failed",
        status="active" if downstream_failed else "refuted",
        threatens=["CLM.self_parse"],
        evidence=["TRACE_SELF_PARSE_RECEIPT"],
        mitigation="repair_parser_roundtrip_or_emit_typed_parser_blocker_before_treating_carrier_as_ready",
    )
    add(
        "DTR.source_context_critical_deficit",
        status="active" if budget_solver_receipt.get("source_context_active_deficit") else "refuted",
        threatens=["CLM.source_context", "CLM.budget_sufficiency"],
        evidence=["SOURCE_CONTEXT_DEFICIT", "SOURCE_CONTEXT_READINESS", "BUDGET_SOLVER_PROOF_SET"],
        mitigation="emit_or_request_smallest_decision_changing_source_slice_before_relying_on_budget_sufficiency",
    )
    add(
        "DTR.budget_high_regret_omission",
        status="active" if int(budget_solver_receipt.get("budget_regret_high") or 0) else "refuted",
        threatens=["CLM.budget_sufficiency"],
        evidence=["EV.source_excerpts"],
        mitigation="top_omitted_decision_refs_names_smallest_missing_slice",
    )
    active = [row["id"] for row in rows if row.get("status") == "active"]
    return {
        "schema_version": "agent_trace_defeater_register_v1",
        "row_count": len(rows),
        "active_count": len(active),
        "active_defeaters": active,
        "rows": rows,
    }


def _capsule_assurance_case_graph(
    *,
    latest_selection_receipt: dict[str, Any],
    title_authority: dict[str, Any],
    trace_self_parse_receipt: dict[str, Any],
    budget_solver_receipt: dict[str, Any],
    defeater_register: dict[str, Any],
) -> dict[str, Any]:
    active_by_claim: dict[str, list[str]] = {}
    for row in defeater_register.get("rows") or []:
        if not isinstance(row, dict) or row.get("status") != "active":
            continue
        for claim_id in row.get("threatens") or []:
            active_by_claim.setdefault(str(claim_id), []).append(str(row.get("id") or ""))

    claims: list[dict[str, Any]] = []

    def add(
        claim_id: str,
        *,
        claim: str,
        grounds: list[str],
        warrant: str,
        backing: list[str],
        status: str | None = None,
    ) -> None:
        active = active_by_claim.get(claim_id, [])
        resolved_status = status or ("supported_with_defeater" if active else "supported")
        claims.append({
            "id": claim_id,
            "claim": claim,
            "grounds": grounds,
            "warrant": warrant,
            "backing": backing,
            "defeaters": active,
            "portable": True,
            "status": resolved_status,
        })

    add(
        "CLM.latest_selection",
        claim=(
            "selected response is latest completed tail response"
            if latest_selection_receipt.get("selected_is_latest_completed_response")
            else "selected response is not proven latest completed tail response"
        ),
        grounds=["EV.latest_selection_receipt", "EV.turn_completion_state"],
        warrant="session ordering keys and tail-state determine latest identity independently of context scope",
        backing=["TRACE_CUT_RECEIPT", "LATEST_SELECTION_RECEIPT"],
    )
    add(
        "CLM.global_absence_guard",
        claim="global absence claims are blocked when only selected window is bundled",
        grounds=["EV.trace_scope", "EV.claim_source_map"],
        warrant="selected-window evidence cannot prove full-thread absence",
        backing=["TRACE_CUT_RECEIPT", "CLAIM_SOURCE_MAP"],
    )
    add(
        "CLM.title_authority",
        claim=f"display title source is {title_authority.get('display_title_source') or ''}",
        grounds=["EV.title_authority"],
        warrant="weak numeric titles require semantic display fallback",
        backing=["TITLE_AUTHORITY"],
    )
    add(
        "CLM.provenance",
        claim="trace capsule materials and subject are envelope-bound without rendered self-hash placeholder",
        grounds=["EV.provenance_attestation", "EV.trace_cut_receipt"],
        warrant="subject hash is finalized by artifact writer after bytes exist",
        backing=["TRACE_PROVENANCE_ATTESTATION"],
    )
    add(
        "CLM.summary_claim_traceability",
        claim="summary claims carry evidence-node locators",
        grounds=["EV.claim_source_map", "EV.evidence_manifest"],
        warrant="claim rows cite EV nodes rather than classifier labels as terminal authority",
        backing=["CLAIM_SOURCE_MAP", "EVIDENCE_NODE_GRAPH"],
    )
    add(
        "CLM.self_parse",
        claim=f"self parse status is {trace_self_parse_receipt.get('round_trip_status') or ''}",
        grounds=["EV.claim_source_map"],
        warrant="producer structural check is separated from downstream parser roundtrip",
        backing=["TRACE_SELF_PARSE_RECEIPT"],
    )
    add(
        "CLM.source_context",
        claim=(
            "decision-critical source context is incomplete"
            if budget_solver_receipt.get("source_context_active_deficit")
            else "decision-critical source context is complete or not demanded"
        ),
        grounds=["SOURCE_CONTEXT_DEMAND", "SOURCE_SLICE_REQUESTS", "SOURCE_CONTEXT_DEFICIT", "SOURCE_CONTEXT_READINESS"],
        warrant="a Type B decision demand is satisfied only by emitted decisive slices or an explicit active deficit",
        backing=["SOURCE_SLICE_MANIFEST", "TYPE_B_SOURCE_CLOSEOUT_LINT"],
    )
    add(
        "CLM.budget_sufficiency",
        claim=(
            "high-regret source omissions absent"
            if int(budget_solver_receipt.get("budget_regret_high") or 0) == 0
            else "high-regret source omissions present"
        ),
        grounds=["EV.source_excerpts"],
        warrant="agent-requested omissions are higher regret than opportunistic prompt-file omissions",
        backing=["BUDGET_SOLVER_PROOF_SET"],
    )
    return {
        "schema_version": "agent_trace_assurance_case_graph_v1",
        "claim_count": len(claims),
        "claims": claims,
        "warrant_model": "toulmin_lightweight_claim_ground_warrant_backing_defeater",
    }


def _capsule_trace_cut_receipt_section_lines(receipt: dict[str, Any]) -> list[str]:
    provider = receipt.get("provider_plane") or {}
    selected_bounds = provider.get("selected_bounds") or {}
    full_bounds = provider.get("full_thread_bounds") or {}
    return [
        "TRACE_CUT_RECEIPT",
        (
            f"trace_cut_receipt_summary: cut_id={receipt.get('cut_id') or ''} "
            f"requested={receipt.get('requested_source_window') or ''} "
            f"resolved={receipt.get('resolved_copy_scope') or ''} "
            f"recommended_scope={receipt.get('recommended_scope') or ''} "
            f"consistency={receipt.get('cut_consistency') or ''} "
            f"full_thread_available={'true' if receipt.get('full_thread_available') else 'false'} "
            f"selected_window_only={'true' if receipt.get('selected_window_only') else 'false'}"
        ),
        (
            f"provider_plane: session={_short_session_tag(str(provider.get('session_id') or ''))} "
            f"selected_turn={provider.get('selected_turn_index') or ''} "
            f"selected_window={selected_bounds.get('start_turn_index')}-{selected_bounds.get('end_turn_index')} "
            f"selected_count={selected_bounds.get('turn_count')} "
            f"full_thread={full_bounds.get('start_turn_index')}-{full_bounds.get('end_turn_index')} "
            f"full_count={full_bounds.get('turn_count')} "
            f"tail_state={provider.get('tail_state') or ''} "
            f"watermark={provider.get('source_watermark_id') or ''}"
        ),
        (
            f"repo_plane: state={(receipt.get('repo_plane') or {}).get('state') or ''} "
            f"head={(receipt.get('repo_plane') or {}).get('head_short') or ''}"
        ),
        (
            f"global_absence_guard: unsafe_global_none_claims_blocked="
            f"{'true' if receipt.get('unsafe_global_none_claims_blocked') else 'false'}"
        ),
    ]


def _capsule_trace_provenance_attestation_section_lines(attestation: dict[str, Any]) -> list[str]:
    materials = attestation.get("materials") or []
    material_ids = ",".join(str(row.get("id") or "") for row in materials if isinstance(row, dict)) or "none"
    subject = attestation.get("subject") or {}
    return [
        "TRACE_PROVENANCE_ATTESTATION",
        (
            f"trace_provenance_attestation_summary: subject={(subject.get('kind') or '')} "
            f"schema={(subject.get('schema_version') or '')} "
            f"subject_sha16={(subject.get('sha16') or '')} "
            f"subject_hash_mode={(subject.get('hash_mode') or '')} "
            f"builder={((attestation.get('builder') or {}).get('tool') or '')} "
            f"repo_head={((attestation.get('builder') or {}).get('repo_head') or '')[:12]} "
            f"materials={material_ids}"
        ),
        (
            f"builder_invocation: provider={((attestation.get('invocation') or {}).get('provider') or '')} "
            f"turn={((attestation.get('invocation') or {}).get('turn_index') or '')} "
            f"requested_source_window={((attestation.get('invocation') or {}).get('requested_source_window') or '')} "
            f"resolved_copy_scope={((attestation.get('invocation') or {}).get('resolved_copy_scope') or '')}"
        ),
    ]


def _capsule_latest_selection_receipt_section_lines(receipt: dict[str, Any]) -> list[str]:
    selected = receipt.get("selected_window") or {}
    candidates = receipt.get("candidate_set") or {}
    return [
        "LATEST_SELECTION_RECEIPT",
        (
            f"latest_selection_receipt_summary: selected_turn={receipt.get('selected_turn_index') or ''} "
            f"selected_window={selected.get('start_turn_index')}-{selected.get('end_turn_index')} "
            f"selected_count={selected.get('turn_count') or 0} "
            f"candidate_set_source={candidates.get('source') or ''} "
            f"candidate_set={candidates.get('start_turn_index')}-{candidates.get('end_turn_index')} "
            f"candidate_count={candidates.get('turn_count') or 0} "
            f"selected_is_thread_tail={'true' if receipt.get('selected_is_thread_tail') else 'false'} "
            f"selected_is_latest_completed_response={'true' if receipt.get('selected_is_latest_completed_response') else 'false'}"
        ),
        (
            f"latest_selection_ordering: keys={','.join(receipt.get('ordering_keys') or [])} "
            f"ambiguity_override_used={'true' if receipt.get('ambiguity_override_used') else 'false'} "
            f"reparse_before_copy={'true' if receipt.get('reparse_before_copy') else 'false'} "
            f"watermark={receipt.get('watermark_id') or ''}"
        ),
        (
            f"latest_selection_defeaters: active={','.join(receipt.get('defeaters') or []) or 'none'} "
            f"latest_prompt_pending_response={'true' if receipt.get('latest_prompt_pending_response') else 'false'}"
        ),
    ]


def _capsule_title_authority_section_lines(title_authority: dict[str, Any]) -> list[str]:
    return [
        "TITLE_AUTHORITY",
        (
            f"title_authority: raw_title=\"{_capsule_claim_value(title_authority.get('raw_title'))}\" "
            f"display_title=\"{_capsule_claim_value(title_authority.get('display_title'))}\" "
            f"display_title_source={title_authority.get('display_title_source') or ''} "
            f"warning={title_authority.get('warning') or 'none'} "
            f"title_confidence={title_authority.get('title_confidence') or ''}"
        ),
    ]


def _capsule_claim_source_map_section_lines(claim_source_map: dict[str, Any]) -> list[str]:
    rows = claim_source_map.get("rows") or []
    covered = ",".join(claim_source_map.get("covered_summary_claims") or []) or "none"
    lines = [
        "CLAIM_SOURCE_MAP",
        (
            f"claim_source_map_summary: rows={claim_source_map.get('row_count') or 0} "
            f"covered_summary_claims={covered} uncovered=none"
        ),
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"{row.get('row_id')} claim={row.get('claim')} value=\"{_capsule_claim_value(row.get('value'))}\" "
            f"scope={row.get('scope')} evidence={row.get('evidence')} "
            f"cannot_prove={row.get('cannot_prove')} render_policy={row.get('render_policy')}"
        )
    return lines


def _capsule_evidence_node_graph_section_lines(graph: dict[str, Any]) -> list[str]:
    lines = [
        "EVIDENCE_NODE_GRAPH",
        (
            f"evidence_node_graph_summary: nodes={graph.get('node_count') or 0} "
            f"locator_rule=\"{_capsule_claim_value(graph.get('locator_rule'))}\""
        ),
    ]
    for node in (graph.get("nodes") or [])[:24]:
        if not isinstance(node, dict):
            continue
        lines.append(
            f"{node.get('id')} kind={node.get('kind')} status={node.get('status')} "
            f"locator=\"{_capsule_claim_value(node.get('locator'))}\" "
            f"sufficient_for={','.join(node.get('sufficient_for') or []) or 'none'} "
            f"insufficient_for={','.join(node.get('insufficient_for') or []) or 'none'}"
        )
    if int(graph.get("node_count") or 0) > 24:
        lines.append(f"evidence_node_graph_omitted: nodes={int(graph.get('node_count') or 0) - 24} reason=node_row_limit")
    return lines


def _capsule_defeater_register_section_lines(register: dict[str, Any]) -> list[str]:
    lines = [
        "DEFEATER_REGISTER",
        (
            f"defeater_register_summary: rows={register.get('row_count') or 0} "
            f"active={register.get('active_count') or 0} "
            f"active_defeaters={','.join(register.get('active_defeaters') or []) or 'none'}"
        ),
    ]
    for row in register.get("rows") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"{row.get('id')} status={row.get('status')} "
            f"threatens={','.join(row.get('threatens') or []) or 'none'} "
            f"evidence={','.join(row.get('evidence') or []) or 'none'} "
            f"mitigation=\"{_capsule_claim_value(row.get('mitigation'))}\""
        )
    return lines


def _capsule_assurance_case_graph_section_lines(graph: dict[str, Any]) -> list[str]:
    lines = [
        "ASSURANCE_CASE_GRAPH",
        (
            f"assurance_case_graph_summary: claims={graph.get('claim_count') or 0} "
            f"warrant_model={graph.get('warrant_model') or ''}"
        ),
    ]
    for claim in graph.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        lines.append(
            f"{claim.get('id')} status={claim.get('status')} portable={'true' if claim.get('portable') else 'false'} "
            f"claim=\"{_capsule_claim_value(claim.get('claim'))}\" "
            f"grounds={','.join(claim.get('grounds') or []) or 'none'} "
            f"backing={','.join(claim.get('backing') or []) or 'none'} "
            f"defeaters={','.join(claim.get('defeaters') or []) or 'none'} "
            f"warrant=\"{_capsule_claim_value(claim.get('warrant'))}\""
        )
    return lines


def _capsule_trace_self_parse_receipt_section_lines(receipt: dict[str, Any]) -> list[str]:
    return [
        "TRACE_SELF_PARSE_RECEIPT",
        (
            f"trace_self_parse_receipt_summary: status={receipt.get('round_trip_status') or ''} "
            f"parser={receipt.get('parser') or ''} "
            f"producer_structural_self_check={receipt.get('producer_structural_self_check') or ''} "
            f"downstream_parser_mjs_roundtrip={receipt.get('downstream_parser_mjs_roundtrip') or ''} "
            f"ui_ingest_contract_parse={receipt.get('ui_ingest_contract_parse') or ''} "
            f"native_receipt_parse={receipt.get('native_receipt_parse') or ''} "
            f"scope={receipt.get('parsed_scope') or ''} "
            f"status_label={receipt.get('parsed_status_label') or ''} "
            f"final_delta_attached={'true' if receipt.get('parsed_final_delta_attached') else 'false'} "
            f"edit_event_log_attached={'true' if receipt.get('parsed_edit_event_log_attached') else 'false'} "
            f"claim_source_map_complete={'true' if receipt.get('claim_source_map_complete') else 'false'}"
        ),
    ]


def _capsule_budget_solver_receipt_section_lines(receipt: dict[str, Any]) -> list[str]:
    return [
        "BUDGET_SOLVER_PROOF_SET",
        (
            f"budget_solver_summary: proof_set_before_route_context="
            f"{'true' if receipt.get('proof_set_before_route_context') else 'false'} "
            f"minimum_proofs={','.join(receipt.get('minimum_proof_set') or [])} "
            f"proof_obligations_total={receipt.get('proof_obligations_total') or 0} "
            f"proof_obligations_embedded={receipt.get('proof_obligations_embedded') or 0} "
            f"proof_obligations_sidecar_only={receipt.get('proof_obligations_sidecar_only') or 0} "
            f"proof_obligations_missing={receipt.get('proof_obligations_missing') or 0} "
            f"source_excerpts={receipt.get('source_excerpt_count') or 0} "
            f"omitted={receipt.get('source_excerpt_omitted') or 0} "
            f"source_context_demand={receipt.get('source_context_demand_state') or 'none'} "
            f"source_context_active_deficit={'true' if receipt.get('source_context_active_deficit') else 'false'} "
            f"source_context_high_regret_missing={receipt.get('source_context_high_regret_missing') or 0} "
            f"budget_regret_high={receipt.get('budget_regret_high') or 0} "
            f"budget_regret_medium={receipt.get('budget_regret_medium') or 0} "
            f"top_omitted_decision_refs={','.join(receipt.get('top_omitted_decision_refs') or []) or 'none'} "
            f"practical_budget={receipt.get('practical_budget') or ''}"
        ),
    ]


def _capsule_type_b_decision_bundle_section_lines(
    bundle: dict[str, Any],
    *,
    source_context_readiness: dict[str, Any],
) -> list[str]:
    lines = [
        "TYPE_B_DECISION_BUNDLE",
        (
            f"type_b_decision_bundle_summary: schema={bundle.get('schema_version') or ''} "
            f"consumer={bundle.get('consumer') or 'type_b_continue'} "
            f"profile={bundle.get('profile') or 'decision_bundle'} "
            f"practical_budget={bundle.get('practical_budget') or '~150KB'} "
            f"source_slice_policy={bundle.get('source_slice_policy') or ''} "
            f"local_no_limit_bundle={bundle.get('local_no_limit_bundle') or 'CHILD_EXECUTION_BUNDLE'} "
            f"demand_state={bundle.get('demand_state') or 'none'} "
            f"source_context_readiness={source_context_readiness.get('overall') or 'green'} "
            f"satisfaction={source_context_readiness.get('satisfaction') or ''} "
            f"auto_rendered_slices={bundle.get('auto_rendered_slice_count') or 0} "
            f"render_blocked={bundle.get('render_blocked_count') or 0} "
            f"source_slice_quality_warning_count={bundle.get('source_slice_quality_warning_count') or 0} "
            f"blocking_quality_warning_count={bundle.get('blocking_quality_warning_count') or 0} "
            f"high_regret_missing_after_render={source_context_readiness.get('high_regret_missing') or 0} "
            f"source_slice_bytes={bundle.get('source_slice_bytes') or 0} "
            f"source_slice_omitted_bytes={bundle.get('source_slice_omitted_bytes') or 0} "
            f"source_slice_budget={bundle.get('source_slice_total_byte_budget') or TRACE_CAPSULE_DECISION_BUNDLE_TOTAL_SOURCE_BYTES} "
            f"child_execution_bytes_pointer={bundle.get('child_execution_bytes_pointer') or 0} "
            f"aggregate_output_bytes_pointer={bundle.get('aggregate_output_bytes_pointer') or 0} "
            f"workflow_trace_coverage={bundle.get('embedded_workflow_trace_count') or 0}/{bundle.get('workflow_worker_count') or 0}"
        ),
    ]
    for row in bundle.get("slices") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            "type_b_decision_source_slice: "
            f"slice_id={row.get('slice_id') or ''} "
            f"request_id={row.get('request_id') or ''} "
            f"path={row.get('path') or ''} "
            f"anchor={row.get('anchor') or ''} "
            f"anchor_derivation={row.get('anchor_derivation') or 'requested_anchor'} "
            f"range={row.get('range') or ''} "
            f"selector={row.get('selector') or ''} "
            f"lines={row.get('line_count') or 0} "
            f"bytes={row.get('bytes') or 0} "
            f"source_bytes={row.get('source_bytes') or row.get('bytes') or 0} "
            f"omitted_bytes={row.get('omitted_bytes') or 0} "
            f"byte_budget={row.get('byte_budget') or bundle.get('source_slice_per_slice_byte_budget') or TRACE_CAPSULE_DECISION_BUNDLE_SOURCE_SLICE_BYTES} "
            f"text_sha16={row.get('text_sha16') or ''} "
            f"truncated={'true' if row.get('truncated') else 'false'} "
            f"byte_truncated={'true' if row.get('byte_truncated') else 'false'} "
            f"slice_quality={row.get('slice_quality') or ''} "
            f"quality_satisfies_request={'true' if row.get('quality_satisfies_request', True) else 'false'} "
            f"quality_warning={row.get('quality_warning') or 'none'} "
            f"selection_warning=\"{_capsule_claim_value(row.get('selection_warning'))}\""
        )
        lines.append(f"BEGIN_TYPE_B_DECISION_SOURCE_SLICE {row.get('slice_id') or ''}")
        display_lines, _display_clip = _capsule_clip_numbered_lines_by_byte_budget(
            [str(line) for line in row.get("lines") or []],
            max_bytes=TRACE_CAPSULE_DECISION_BUNDLE_SOURCE_SLICE_BYTES,
            max_line_bytes=TRACE_CAPSULE_SOURCE_EXCERPT_LINE_BYTES,
            marker_label="type_b_decision_bundle_render",
        )
        lines.extend(display_lines)
        lines.append(f"END_TYPE_B_DECISION_SOURCE_SLICE {row.get('slice_id') or ''}")
    for row in bundle.get("blocked") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            "SOURCE_CONTEXT_RENDER_BLOCKED "
            f"request_id={row.get('request_id') or ''} "
            f"path={row.get('path') or ''} "
            f"anchor={row.get('anchor') or ''} "
            f"reason=\"{_capsule_claim_value(row.get('reason'))}\""
        )
    return lines


def _capsule_source_context_demand_section_lines(demand: dict[str, Any]) -> list[str]:
    trigger_paths = ",".join(Path(str(path)).name for path in demand.get("trigger_paths") or []) or "none"
    return [
        "SOURCE_CONTEXT_DEMAND",
        (
            f"source_context_demand_summary: state={demand.get('state') or 'none'} "
            f"satisfaction={demand.get('satisfaction') or ''} "
            f"consumer={demand.get('consumer') or 'type_b_continue'} "
            f"reasons={','.join(demand.get('reasons') or []) or 'none'} "
            f"trigger_paths={trigger_paths} "
            f"trigger_path_count={demand.get('trigger_path_count') or 0} "
            f"demand_scope={demand.get('demand_scope') or 'none'} "
            f"explicit_requests={demand.get('explicit_requests') or 0} "
            f"readiness_effect={demand.get('readiness_effect') or 'none'}"
        ),
    ]


def _capsule_source_slice_requests_section_lines(source_slice_requests: dict[str, Any]) -> list[str]:
    rows = [row for row in source_slice_requests.get("rows") or [] if isinstance(row, dict)]
    emitted = sum(1 for row in rows if row.get("status") in {"emitted", "rendered_by_decision_bundle"})
    delta_contract = sum(
        1 for row in rows if row.get("status") == "delta_satisfied_for_changed_contract"
    )
    final_delta = sum(
        1
        for row in rows
        if row.get("status") in {
            "emitted",
            "rendered_by_decision_bundle",
            "satisfied_by_final_delta",
            "delta_satisfied_for_changed_contract",
        }
    )
    deficits = sum(1 for row in rows if row.get("status") in {"deficit", "rendered_by_decision_bundle_insufficient"})
    rendered_insufficient = sum(1 for row in rows if row.get("status") == "rendered_by_decision_bundle_insufficient")
    quality_warnings = sum(1 for row in rows if row.get("quality_warning"))
    critical = sum(1 for row in rows if row.get("priority") == "critical")
    lines = [
        "SOURCE_SLICE_REQUESTS",
        (
            f"source_slice_requests_summary: rows={len(rows)} "
            f"explicit={source_slice_requests.get('explicit_request_count') or 0} "
            f"synthesized={source_slice_requests.get('synthesized_request_count') or 0} "
            f"critical={critical} emitted={emitted} "
            f"rendered_insufficient={rendered_insufficient} "
            f"quality_warnings={quality_warnings} "
            f"satisfied_by_final_delta={final_delta} "
            f"delta_satisfied_for_changed_contract={delta_contract} deficits={deficits}"
        ),
    ]
    for row in rows[:TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT]:
        lines.append(
            "source_slice_request: "
            f"request_id={row.get('request_id') or ''} "
            f"path={row.get('path') or ''} "
            f"anchor={row.get('anchor') or ''} "
            f"resolved_anchor={row.get('resolved_anchor') or row.get('anchor') or ''} "
            f"anchor_derivation={row.get('anchor_derivation') or 'requested_anchor'} "
            f"why={row.get('why') or ''} "
            f"priority={row.get('priority') or ''} "
            f"budget_class={row.get('budget_class') or ''} "
            f"status={row.get('status') or ''} "
            f"carrier={row.get('carrier') or 'none'} "
            f"carrier_kind={row.get('carrier_kind') or 'none'} "
            f"slice_quality={row.get('slice_quality') or 'none'} "
            f"quality_satisfies_request={'true' if row.get('quality_satisfies_request', True) else 'false'} "
            f"quality_warning={row.get('quality_warning') or 'none'}"
        )
    return lines


def _capsule_source_slice_manifest_section_lines(manifest: dict[str, Any]) -> list[str]:
    slices = [row for row in manifest.get("slices") or [] if isinstance(row, dict)]
    lines = [
        "SOURCE_SLICE_MANIFEST",
        (
            f"source_slice_manifest_summary: slices={len(slices)} repo_bound={'true' if slices else 'false'} "
            f"slice_quality_warning_count={manifest.get('slice_quality_warning_count') or 0} "
            f"blocking_quality_warning_count={manifest.get('blocking_quality_warning_count') or 0}"
        ),
    ]
    for row in slices[:TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT]:
        lines.append(
            "source_slice_manifest_row: "
            f"slice_id={row.get('slice_id') or ''} "
            f"request_id={row.get('request_id') or ''} "
            f"artifact_uri={row.get('artifact_uri') or ''} "
            f"repo_head={str(row.get('repo_head') or '')[:12]} "
            f"language_id={row.get('language_id') or ''} "
            f"anchor={row.get('anchor') or ''} "
            f"text_sha16={row.get('text_sha16') or ''} "
            f"carrier={row.get('carrier') or ''} "
            f"line_count={row.get('line_count') or 0} "
            f"bytes={row.get('bytes') or 0} "
            f"source_bytes={row.get('source_bytes') or row.get('bytes') or 0} "
            f"omitted_bytes={row.get('omitted_bytes') or 0} "
            f"byte_budget={row.get('byte_budget') or 0} "
            f"truncated={'true' if row.get('truncated') else 'false'} "
            f"byte_truncated={'true' if row.get('byte_truncated') else 'false'} "
            f"slice_quality={row.get('slice_quality') or 'none'} "
            f"quality_satisfies_request={'true' if row.get('quality_satisfies_request', True) else 'false'} "
            f"linked_claims={','.join(row.get('linked_claims') or []) or 'none'}"
        )
    return lines


def _capsule_source_context_deficit_section_lines(deficit: dict[str, Any]) -> list[str]:
    rows = [row for row in deficit.get("rows") or [] if isinstance(row, dict)]
    lines = [
        "SOURCE_CONTEXT_DEFICIT",
        (
            f"source_context_deficit_summary: rows={deficit.get('row_count') or 0} "
            f"active={deficit.get('active_count') or 0}"
        ),
    ]
    for row in rows[:TRACE_CAPSULE_SOURCE_EXCERPT_LIMIT]:
        lines.append(
            "source_context_deficit_row: "
            f"deficit_id={row.get('deficit_id') or ''} "
            f"request_id={row.get('request_id') or ''} "
            f"missing_path={row.get('missing_path') or ''} "
            f"missing_anchor={row.get('missing_anchor') or ''} "
            f"why_needed={row.get('why_needed') or ''} "
            f"fallback_used={row.get('fallback_used') or 'none'} "
            f"slice_quality={row.get('slice_quality') or 'none'} "
            f"carrier={row.get('carrier') or 'none'} "
            f"quality_warning={row.get('quality_warning') or 'none'} "
            f"next_best_slice=\"{_capsule_claim_value(row.get('next_best_slice'))}\" "
            f"max_context={row.get('max_context') or ''}"
        )
    return lines


def _capsule_source_context_readiness_section_lines(readiness: dict[str, Any]) -> list[str]:
    return [
        "SOURCE_CONTEXT_READINESS",
        (
            f"source_context_readiness: overall={readiness.get('overall') or 'green'} "
            f"demand={readiness.get('demand') or 'none'} "
            f"satisfaction={readiness.get('satisfaction') or ''} "
            f"explicit_requests={readiness.get('explicit_requests') or 0} "
            f"synthesized_requests={readiness.get('synthesized_requests') or 0} "
            f"emitted={readiness.get('emitted') or 0} "
            f"satisfied_by_final_delta={readiness.get('satisfied_by_final_delta') or 0} "
            f"delta_satisfied_for_changed_contract={readiness.get('delta_satisfied_for_changed_contract') or 0} "
            f"manifest_slices={readiness.get('manifest_slices') or 0} "
            f"omitted={readiness.get('omitted') or 0} "
            f"high_regret_missing={readiness.get('high_regret_missing') or 0} "
            f"rendered_insufficient={readiness.get('rendered_insufficient') or 0} "
            f"slice_quality_warning_count={readiness.get('slice_quality_warning_count') or 0} "
            f"blocking_quality_warning_count={readiness.get('blocking_quality_warning_count') or 0} "
            f"copy_readiness_effect={readiness.get('copy_readiness_effect') or 'none'}"
        ),
    ]


def _capsule_type_b_source_closeout_lint_section_lines(lint: dict[str, Any]) -> list[str]:
    return [
        "TYPE_B_SOURCE_CLOSEOUT_LINT",
        (
            f"type_b_source_closeout_lint: result={lint.get('result') or 'pass'} "
            f"demand_state={lint.get('demand_state') or 'none'} "
            f"readiness={lint.get('readiness') or 'green'} "
            f"high_regret_missing={lint.get('high_regret_missing') or 0} "
            f"rule={lint.get('rule') or ''}"
        ),
    ]


_TRACE_CAPSULE_REPLACEABLE_SECTION_TITLES = {
    "TRACE_CUT_RECEIPT",
    "LATEST_SELECTION_RECEIPT",
    "TRACE_PROVENANCE_ATTESTATION",
    "TITLE_AUTHORITY",
    "CLAIM_SOURCE_MAP",
    "EVIDENCE_NODE_GRAPH",
    "DEFEATER_REGISTER",
    "ASSURANCE_CASE_GRAPH",
    "TRACE_SELF_PARSE_RECEIPT",
    "BUDGET_SOLVER_PROOF_SET",
    "TYPE_B_DECISION_BUNDLE",
    "SOURCE_CONTEXT_DEMAND",
    "SOURCE_SLICE_REQUESTS",
    "SOURCE_SLICE_MANIFEST",
    "SOURCE_CONTEXT_DEFICIT",
    "SOURCE_CONTEXT_READINESS",
    "TYPE_B_SOURCE_CLOSEOUT_LINT",
    "EVIDENCE_MANIFEST",
    "CHILD_EXECUTION_BUNDLE",
    "LANDED_COMMIT_SEQUENCE",
    "FINAL_DELTA",
    "EDIT_EVENT_LOG",
    "COMMAND_RETURNS",
    "SOURCE_EXCERPTS",
    "SIDECAR_MANIFEST",
    "VISIBLE_PROGRESS",
    "PROMPT",
    "TIMELINE",
    "OMISSIONS",
    "SCOPE_INTEGRITY",
}


def _capsule_replace_section(lines: list[str], title: str, replacement: list[str]) -> list[str]:
    try:
        start = lines.index(title)
    except ValueError:
        return lines
    end = start + 1
    while end < len(lines):
        value = lines[end].strip()
        if value in _TRACE_CAPSULE_REPLACEABLE_SECTION_TITLES and value != title:
            break
        end += 1
    return [*lines[:start], *replacement, *lines[end:]]


def _capsule_replace_prefixed_line(lines: list[str], prefix: str, replacement: str) -> list[str]:
    out = list(lines)
    for index, line in enumerate(out):
        if line.startswith(prefix):
            out[index] = replacement
            break
    return out


def _capsule_apply_downstream_parse_receipt(
    receipt: dict[str, Any],
    downstream_parse_receipt: dict[str, Any],
) -> None:
    status = downstream_parse_receipt.get("status") or "unknown"
    receipt["downstream_parser_mjs_roundtrip"] = status
    receipt["downstream_parser_receipt"] = downstream_parse_receipt
    if status == "pass":
        receipt["native_receipt_parse"] = "pass"
        receipt["round_trip_status"] = (
            "pass"
            if receipt.get("producer_structural_self_check") == "pass"
            else "producer_fail_downstream_pass"
        )
    elif status in {"unavailable", "not_run"}:
        receipt["native_receipt_parse"] = "blocked"
        receipt["round_trip_status"] = "downstream_parser_blocked"
    else:
        receipt["native_receipt_parse"] = "fail"
        receipt["round_trip_status"] = "fail"


def render_trace_capsule_text(
    turn: Turn,
    *,
    title: str,
    source_window: str = "latest_prompt_cycle",
    intern_repeated_prompts: bool = False,
    include_raw_sidecar: bool = True,
    include_prompt_body: bool = True,
    embed_subagent_traces: bool = True,
    embed_child_executions: bool = True,
    _subagent_depth: int = 0,
    _subagent_visited: set[str] | None = None,
    _child_execution_depth: int = 0,
    _child_execution_visited: set[str] | None = None,
) -> tuple[str, dict]:
    renderable = _renderable_trace_tool_events(turn.tool_events)
    if include_raw_sidecar:
        raw_sidecar_text = render_trace_paste(
            turn,
            include_prompt=include_prompt_body,
            intern_repeated_prompts=intern_repeated_prompts,
        )
        source_sha16 = _sha16(raw_sidecar_text)
    else:
        raw_sidecar_text = ""
        source_sha16 = _trace_source_fingerprint(turn)
    status_text = "complete" if turn.is_complete else "in_progress"
    worked_for = _duration_label(turn.started_at, turn.completed_at)
    commands_with_outputs = 0
    truncated_outputs = 0
    edit_rows: list[dict[str, Any]] = []
    check_rows: list[CapsuleEvidenceClassification] = []
    governance_rows: list[CapsuleEvidenceClassification] = []
    diagnostic_rows: list[CapsuleEvidenceClassification] = []
    commit_hash = ""
    commit_title = ""
    commit_rows: list[tuple[str, str]] = []
    reasoning_events: list[CapsuleReasoningEvent] = []
    episode_evidence: list[CapsuleEpisodeEvidence] = []
    timeline: list[str] = []

    note_index = 1
    emitted_notes: set[str] = set()
    timeline_items: list[tuple[int, int, str, Any]] = []
    for idx, wrapped in enumerate(renderable, start=1):
        ev = wrapped[0]
        source_index = (ev.source_record_indices or [ev.index])[0]
        timeline_items.append((source_index, 1, "tool", (idx, wrapped)))
    for ev in turn.assistant_events:
        if (ev.text or "").strip():
            timeline_items.append((ev.source_record_index, 0, "note", ev))
    timeline_items.sort(key=lambda row: (row[0], row[1]))

    for _, _, item_kind, item_payload in timeline_items:
        if item_kind == "note":
            ev = item_payload
            text = _capsule_clean_text(" ".join((ev.text or "").strip().split()))
            if not text or text in emitted_notes:
                continue
            emitted_notes.add(text)
            if len(text) > TRACE_CAPSULE_VISIBLE_NOTE_MAX_CHARS:
                text = (
                    text[:TRACE_CAPSULE_VISIBLE_NOTE_MAX_CHARS].rstrip()
                    + f" [visible note truncated; sha16={_sha16(text)}]"
                )
            note_id = f"N{note_index:03d}"
            category = _capsule_reasoning_category(text)
            reasoning_events.append(CapsuleReasoningEvent(
                note_id=note_id,
                category=category,
                text=text,
                source_index=ev.source_record_index,
            ))
            timeline.append(f"{note_id} {category} {text}")
            timeline.append("")
            note_index += 1
            continue

        idx, wrapped = item_payload
        ev, output_text, exit_code, is_error = wrapped
        command = _capsule_clean_text(_capsule_command(ev))
        role = _capsule_role(ev, command)
        status = _capsule_status(exit_code, is_error)
        out_lines, truncated = _capsule_output_lines(output_text, role=role, status=status)
        if out_lines != ["no captured output"]:
            commands_with_outputs += 1
        if truncated:
            truncated_outputs += 1
        exit_part = f" exit={exit_code}" if exit_code is not None else ""
        command_id = f"C{idx:03d}"
        timeline.append(f"{command_id} {status} {role}{exit_part}")
        source_index = (ev.source_record_indices or [ev.index])[0]
        episode_evidence.append(CapsuleEpisodeEvidence(
            source_index=source_index,
            row_id=command_id,
            kind="command",
            result=status,
        ))
        timeline.extend(_capsule_command_display_lines(command))
        timeline.append("")
        timeline.extend(out_lines)
        if status == "pass":
            timeline.append("Success")
        elif exit_code is not None:
            timeline.append(f"Exit code {exit_code}")
        else:
            timeline.append("Status: fail")

        evidence = _capsule_evidence_classification(command, role, exit_code, is_error, output_text)
        if evidence and evidence.bucket == "check":
            check_rows.append(evidence)
            prefix = "F" if evidence.result == "fail" else "V"
            evidence_id = f"{prefix}{len(check_rows):03d}"
            timeline.append(f"{evidence_id} {evidence.result} {command_id} {evidence.label}")
            episode_evidence.append(CapsuleEpisodeEvidence(
                source_index=source_index,
                row_id=evidence_id,
                kind="check",
                result=evidence.result,
                identity=evidence.identity,
            ))
        elif evidence and evidence.bucket == "governance":
            governance_rows.append(evidence)
            evidence_id = f"G{len(governance_rows):03d}"
            timeline.append(f"{evidence_id} {evidence.result} {command_id} {evidence.label}")
            episode_evidence.append(CapsuleEpisodeEvidence(
                source_index=source_index,
                row_id=evidence_id,
                kind="governance",
                result=evidence.result,
            ))
        elif evidence and evidence.bucket == "diagnostic":
            diagnostic_rows.append(evidence)

        for delta in _capsule_tool_edit_deltas(ev):
            edit_rows.append(delta)
            edit_id = f"E{len(edit_rows):03d}"
            timeline.append(f"{edit_id} {_capsule_clean_text(str(delta.get('path', '')))} +{delta.get('additions', 0)} -{delta.get('deletions', 0)}")
            episode_evidence.append(CapsuleEpisodeEvidence(
                source_index=source_index,
                row_id=edit_id,
                kind="edit",
                result="",
            ))
            for line in (delta.get("lines") or [])[:32]:
                if line.startswith(("+", "-", "@@")) and not line.startswith(("+++", "---")):
                    if "[reasoning note omitted" in line:
                        timeline.append(
                            f"[legacy reasoning omission marker edit line omitted; chars={len(line)}; sha16={_sha16(line)}]"
                        )
                    else:
                        timeline.append(line[:360])

        detected_commit = _capsule_commit_from_output(output_text, command)
        if detected_commit[0] or detected_commit[1]:
            commit_rows.append(detected_commit)
        timeline.append("")

    final_assistant_text = _capsule_final_assistant_text(turn)
    git_publication_trace = _capsule_git_publication_trace(renderable, final_assistant_text)
    closeout_commit_refs = _capsule_closeout_commit_refs(final_assistant_text)
    remote_closeout_ref = closeout_commit_refs.get("remote_published")
    local_closeout_ref = closeout_commit_refs.get("local_checkpoint")
    if local_closeout_ref and git_publication_trace.get("local_checkpoint_commit"):
        local_closeout_ref = (
            str(git_publication_trace.get("local_checkpoint_commit") or ""),
            local_closeout_ref[1],
        )
    if remote_closeout_ref and git_publication_trace.get("remote_published_commit"):
        remote_closeout_ref = (
            str(git_publication_trace.get("remote_published_commit") or ""),
            remote_closeout_ref[1],
        )
    if local_closeout_ref:
        _capsule_insert_commit_ref_before(
            commit_rows,
            local_closeout_ref,
            before_hash=(remote_closeout_ref or ("", ""))[0],
        )
    if remote_closeout_ref:
        _capsule_insert_commit_ref_before(commit_rows, remote_closeout_ref)

    if commit_rows:
        commit_hash, commit_title = commit_rows[-1]
    commit_count = len(commit_rows)
    commit_summary = _capsule_clean_text(" ".join(x for x in [commit_hash, commit_title] if x))
    if commit_summary and commit_count > 1:
        commit_summary = f"{commit_summary} (+{commit_count - 1} earlier)"

    check_pass_count, check_fail_count, check_other_count = _capsule_result_counts(check_rows)
    governance_pass_count, governance_fail_count, governance_other_count = _capsule_result_counts(governance_rows)
    diagnostic_fail_count = sum(1 for row in diagnostic_rows if row.result == "fail")
    terminal_check_rows = _capsule_terminal_rows(check_rows)
    terminal_governance_rows = _capsule_terminal_rows(governance_rows)
    terminal_check_by_identity = {row.identity: row for row in terminal_check_rows}
    publication_poll_identity_recovered_failure_rows = [
        row
        for row in check_rows
        if row.result == "fail"
        and row.validation_class == "publication_status_poll"
        and terminal_check_by_identity.get(row.identity) is not None
        and terminal_check_by_identity[row.identity].result == "pass"
    ]
    recovered_failures = sum(
        1
        for row in check_rows
        if row.result == "fail"
        and terminal_check_by_identity.get(row.identity) is not None
        and terminal_check_by_identity[row.identity].result == "pass"
    )
    final_validation_basis = "terminal_checks" if terminal_check_rows else "no_checks"
    evidence_summary = CapsuleEvidenceSummary(
        checks=tuple(check_rows),
        terminal_checks=tuple(terminal_check_rows),
        governance_receipts=tuple(governance_rows),
        terminal_governance=tuple(terminal_governance_rows),
        diagnostics=tuple(diagnostic_rows),
        recovered_failures=recovered_failures,
        final_validation_basis=final_validation_basis,
    )
    check_pass_count, check_fail_count, check_other_count = evidence_summary.check_counts
    terminal_check_pass_count, terminal_check_fail_count, terminal_check_other_count = evidence_summary.terminal_check_counts
    governance_pass_count, governance_fail_count, governance_other_count = evidence_summary.governance_counts
    terminal_governance_pass_count, terminal_governance_fail_count, terminal_governance_other_count = evidence_summary.terminal_governance_counts
    diagnostic_fail_count = evidence_summary.diagnostic_fail_count
    residual_taxonomy = _capsule_residual_taxonomy([*check_rows, *governance_rows, *diagnostic_rows])
    captured_residual_ids = list(residual_taxonomy.all_residual_mentions)
    open_product_residuals = list(residual_taxonomy.open_product_residuals)
    open_validation_process_residuals = list(residual_taxonomy.open_validation_process_residuals)
    closed_residuals_seen = list(residual_taxonomy.closed_residuals_seen)
    blocked_external_observation_residuals = list(residual_taxonomy.blocked_external_observation_residuals)
    projection_or_view_artifacts_seen = list(residual_taxonomy.projection_or_view_artifacts_seen)
    unresolved_residual_mentions = list(residual_taxonomy.unresolved_residual_mentions)
    passive_residual_mentions_observed = list(residual_taxonomy.passive_residual_mentions_observed)
    ambient_validation_rows = [
        row
        for row in [*check_rows, *governance_rows, *diagnostic_rows]
        if row.validation_class == "ambient_validation_warning"
    ]
    ambient_terminal_warning_rows = [
        row for row in terminal_check_rows if row.validation_class == "ambient_validation_warning"
    ]
    validation_process_terminal_rows = [
        row for row in terminal_check_rows if row.validation_class == "validation_process_warning"
    ]
    expected_guard_refusal_rows = [
        row
        for row in [*terminal_check_rows, *terminal_governance_rows]
        if row.validation_class == "expected_guarded_refusal"
    ]
    expected_guard_refusal_count = len(expected_guard_refusal_rows)
    publication_hold_rows = [
        row for row in governance_rows if row.validation_class == "publication_hold"
    ]
    receipt_pending_rows = [
        row for row in governance_rows if row.validation_class == "receipt_intake_pending"
    ]
    receipt_applied_rows = [
        row for row in governance_rows if row.validation_class == "receipt_intake_applied"
    ]
    projection_assimilation_rows = [
        row
        for row in governance_rows
        if row.validation_class in _CAPSULE_PROJECTION_ASSIMILATION_SUMMARY_CLASSES
    ]
    ambient_warning_classes = sorted(
        {row.ambient_warning_class or "external_validation_warning" for row in ambient_validation_rows}
    )
    source_domain_terminal_rows = [
        row
        for row in terminal_check_rows
        if row.validation_domain in {"source_landing", "source_context_bundle"}
        and row.workspace_role == "main_worktree"
    ]
    publication_candidate_terminal_rows = [
        row
        for row in terminal_check_rows
        if row.validation_domain == "publication_candidate"
        or row.workspace_role in {"detached_publication_worktree", "retained_conflict_worktree"}
    ]
    source_domain_pass_count, source_domain_fail_count, source_domain_other_count = _capsule_result_counts(
        source_domain_terminal_rows
    )
    publication_candidate_pass_count, publication_candidate_fail_count, publication_candidate_other_count = (
        _capsule_result_counts(publication_candidate_terminal_rows)
    )
    owner_terminal_check_rows = [
        row
        for row in source_domain_terminal_rows
        if row.validation_class not in {"ambient_validation_warning", "validation_process_warning"}
    ]
    owner_terminal_pass_count, owner_terminal_fail_count, owner_terminal_other_count = _capsule_result_counts(
        owner_terminal_check_rows
    )
    paper_module_ambient_owner_scope_pass_rows = [
        row
        for row in ambient_terminal_warning_rows
        if row.ambient_warning_class == "paper_module_ambient_corpus_debt"
    ]
    owner_scope_pass_evidence_count = owner_terminal_pass_count + len(paper_module_ambient_owner_scope_pass_rows)
    nonblocking_failure_classes = {
        "stale_selector_retry",
        "out_of_scope_discoverability_failure",
        "exploratory_diagnostic_failure",
        "ambient_validation_warning",
        "validation_process_warning",
        "expected_guarded_refusal",
    }
    blocking_terminal_failures = [
        row
        for row in owner_terminal_check_rows
        if row.result == "fail" and row.validation_class not in nonblocking_failure_classes
    ]
    nonblocking_terminal_failures = [
        row
        for row in terminal_check_rows
        if row.result == "fail" and row.validation_class in nonblocking_failure_classes
    ]
    final_assistant_text = _capsule_final_assistant_text(turn)
    product_state_parts: list[str] = []
    current_authority_product_state_parts: list[str] = []
    historical_product_state_parts: list[str] = []
    current_release_gate_product_state_parts: list[str] = []
    observed_release_gate_product_state_parts: list[str] = []
    for ev, output_text, _, _ in renderable:
        command = _capsule_clean_text(_capsule_command(ev))
        scope = _capsule_current_evidence_scope(command)
        state_part = "\n".join(part for part in (command, output_text or "") if part)
        product_state_parts.append(state_part)
        if scope.startswith("current_"):
            current_authority_product_state_parts.append(state_part)
            if scope in {
                "current_public_release_gate_receipt",
                "current_task_ledger_authority_receipt",
                "current_work_landing_reconcile_receipt",
                "current_work_landing_status_receipt",
            }:
                current_release_gate_product_state_parts.append(state_part)
            elif scope == "current_validation_command":
                observed_release_gate_product_state_parts.append(state_part)
        elif scope in {
            "historical_trace_render",
            "historical_source_artifact",
            "historical_git_observation",
            "untrusted_command_output",
        }:
            historical_product_state_parts.append(state_part)
            observed_release_gate_product_state_parts.append(state_part)
    product_state_text = "\n".join(product_state_parts)
    current_authority_product_state_text = "\n".join(current_authority_product_state_parts)
    historical_product_state_text = "\n".join(historical_product_state_parts)
    current_release_gate_product_state_text = "\n".join(current_release_gate_product_state_parts)
    observed_release_gate_product_state_text = "\n".join(observed_release_gate_product_state_parts)
    passive_residual_mentions_observed.extend(
        _capsule_passive_residual_mentions(renderable, prompt_text=turn.prompt_text)
    )
    selected_window_unresolved_residual_mentions = list(
        _capsule_selected_window_unresolved_residual_ids(final_assistant_text)
    )
    unresolved_residual_mentions.extend(selected_window_unresolved_residual_mentions)
    passive_residual_mentions_observed = list(_capsule_ordered_unique(passive_residual_mentions_observed))
    unresolved_residual_mentions = list(_capsule_ordered_unique(unresolved_residual_mentions))
    selected_window_unresolved_residual_mentions = list(_capsule_ordered_unique(selected_window_unresolved_residual_mentions))
    publication_blocker_receipt = _capsule_publication_blocker_receipt(
        renderable,
        final_assistant_text,
    )
    work_landing_receipt = _capsule_work_landing_receipt(
        renderable,
        final_assistant_text,
    )
    publication_blocker_receipt_id = str(publication_blocker_receipt.get("receipt") or "")
    publication_blocker_observed = (
        publication_blocker_receipt.get("observed")
        if isinstance(publication_blocker_receipt.get("observed"), Mapping)
        else {}
    )
    publication_blocker_observed_id = str(publication_blocker_observed.get("subject") or "")
    publication_blocker_observed_event = str(publication_blocker_observed.get("event") or "")
    if publication_blocker_receipt_id:
        open_product_residuals = [item for item in open_product_residuals if item != publication_blocker_receipt_id]
        unresolved_residual_mentions = [
            item for item in unresolved_residual_mentions if item != publication_blocker_receipt_id
        ]
        selected_window_unresolved_residual_mentions = [
            item for item in selected_window_unresolved_residual_mentions if item != publication_blocker_receipt_id
        ]
        if "publication_blocked_by_clean_base_replay_dependency" not in open_validation_process_residuals:
            open_validation_process_residuals.append("publication_blocked_by_clean_base_replay_dependency")
    if publication_blocker_observed_id:
        open_product_residuals = [item for item in open_product_residuals if item != publication_blocker_observed_id]
        unresolved_residual_mentions = [
            item for item in unresolved_residual_mentions if item != publication_blocker_observed_id
        ]
        selected_window_unresolved_residual_mentions = [
            item for item in selected_window_unresolved_residual_mentions if item != publication_blocker_observed_id
        ]
    release_candidate_gate_decision = _capsule_release_candidate_gate_decision(
        current_release_gate_product_state_text
    )
    historical_release_candidate_gate_decision = _capsule_release_candidate_gate_decision(
        observed_release_gate_product_state_text
    )
    release_candidate_gate_ready = release_candidate_gate_decision == "ready_pending_operator_authorization"
    public_release_blocked = release_candidate_gate_decision == "public_release_blocked"
    public_release_not_authorized = release_candidate_gate_decision == "not_authorized_by_operator"
    release_candidate_gate_nonblocking = release_candidate_gate_ready or public_release_blocked or public_release_not_authorized
    release_gate_kind = "none"
    if public_release_blocked:
        release_gate_kind = "current_release_attempt_failed"
    elif public_release_not_authorized or release_candidate_gate_ready:
        release_gate_kind = "authorization_absent"
    elif historical_release_candidate_gate_decision:
        release_gate_kind = "pvr_or_host_gate_observed"
    internal_authorization = "satisfied" if (public_release_blocked or public_release_not_authorized) else (
        "pending_operator_authorization" if release_candidate_gate_ready else "none"
    )
    if public_release_blocked:
        public_release_authorization = "blocked_by_public_release_gate"
    elif public_release_not_authorized:
        public_release_authorization = "not_authorized_by_operator"
    elif release_candidate_gate_ready:
        public_release_authorization = "pending_operator_authorization"
    else:
        public_release_authorization = "none"
    stale_window_failure_rows = _capsule_later_aggregate_recovery_failures(
        check_rows,
        blocking_terminal_failures,
    )
    selector_recovered_failure_rows = _capsule_later_selector_recovery_failures(
        check_rows,
        blocking_terminal_failures,
    )
    split_selector_recovered_failure_rows = _capsule_later_split_selector_recovery_failures(
        check_rows,
        blocking_terminal_failures,
    )
    publication_poll_terminal_recovered_failure_rows = _capsule_later_publication_poll_recovery_failures(
        check_rows,
        blocking_terminal_failures,
    )
    publication_poll_recovered_failure_rows = [
        *publication_poll_identity_recovered_failure_rows,
        *publication_poll_terminal_recovered_failure_rows,
    ]
    stale_window_failure_identities = {row.identity for row in stale_window_failure_rows}
    selector_recovered_failure_identities = {
        row.identity for row in selector_recovered_failure_rows
    }
    split_selector_recovered_failure_identities = {
        row.identity for row in split_selector_recovered_failure_rows
    }
    publication_poll_recovered_failure_identities = {
        row.identity for row in publication_poll_recovered_failure_rows
    }
    superseded_failure_identities = (
        stale_window_failure_identities
        | selector_recovered_failure_identities
        | split_selector_recovered_failure_identities
        | publication_poll_recovered_failure_identities
    )
    current_terminal_failure_rows = [
        row for row in blocking_terminal_failures if row.identity not in superseded_failure_identities
    ]
    if split_selector_recovered_failure_rows:
        final_validation_basis = "terminal_checks_plus_later_split_selector_coverage"
    elif selector_recovered_failure_rows:
        final_validation_basis = "terminal_checks_plus_later_selector_coverage"
    elif publication_poll_recovered_failure_rows:
        final_validation_basis = "terminal_checks_plus_later_publication_poll"
    elif stale_window_failure_rows:
        final_validation_basis = "terminal_checks_plus_later_aggregate_proof"
    selector_recovered_failure_count = len(selector_recovered_failure_rows)
    split_selector_recovered_failure_count = len(split_selector_recovered_failure_rows)
    publication_poll_recovered_failure_count = len(publication_poll_recovered_failure_rows)
    recovered_failures += (
        selector_recovered_failure_count
        + split_selector_recovered_failure_count
        + len(publication_poll_terminal_recovered_failure_rows)
    )
    closeout_green_claim_without_command_proof = (
        bool(current_terminal_failure_rows)
        and _capsule_closeout_claims_green_validation(final_assistant_text)
        and not release_candidate_gate_nonblocking
    )
    release_gate_superseded_failure_count = (
        len(blocking_terminal_failures) if release_candidate_gate_nonblocking else 0
    )
    historical_terminal_failures_superseded = (
        release_gate_superseded_failure_count
        if release_candidate_gate_nonblocking
        else (
            len(stale_window_failure_rows)
            + selector_recovered_failure_count
            + split_selector_recovered_failure_count
            + publication_poll_recovered_failure_count
        )
    )
    effective_blocking_terminal_failures = (
        [] if release_candidate_gate_nonblocking else current_terminal_failure_rows
    )
    current_terminal_failure_count = len(effective_blocking_terminal_failures)
    stale_window_failure_count = len(stale_window_failure_rows)
    not_validated_count = 1 if closeout_green_claim_without_command_proof else 0
    contradictory_closeout_count = 1 if closeout_green_claim_without_command_proof else 0
    owner_scope_validation = "unknown"
    if effective_blocking_terminal_failures:
        owner_scope_validation = "needs_review"
    elif release_candidate_gate_nonblocking:
        owner_scope_validation = "pass"
    elif expected_guard_refusal_count:
        owner_scope_validation = "pass_with_guarded_refusal_receipt"
    elif owner_scope_pass_evidence_count > 0:
        owner_scope_validation = "pass"
    elif owner_terminal_fail_count > 0:
        owner_scope_validation = "needs_review"
    ambient_validation = "valid_with_warnings" if ambient_validation_rows else "none"
    ambient_warning_class_summary = ",".join(ambient_warning_classes) if ambient_warning_classes else "none"
    ambient_validation_warning_summary = ambient_warning_class_summary
    publication_blocker_validation_residual = "publication_blocked_by_clean_base_replay_dependency"
    source_landing_validation_process_residuals = [
        residual
        for residual in open_validation_process_residuals
        if residual != publication_blocker_validation_residual
    ]
    validation_process = (
        "needs_review"
        if validation_process_terminal_rows or source_landing_validation_process_residuals
        else (
            "publication_blocked"
            if publication_blocker_validation_residual in open_validation_process_residuals
            else "none"
        )
    )
    has_source_validation_process_warning = (
        "needs_review"
        if validation_process_terminal_rows or source_landing_validation_process_residuals
        else "none"
    )
    has_validation_process_warning = has_source_validation_process_warning != "none"
    publication_deploy_receipt_rows = [
        row
        for row in [*check_rows, *governance_rows]
        if row.result == "pass" and row.validation_class == "publication_deploy_receipt"
    ]
    publication_host_verification_rows = [
        row
        for row in check_rows
        if row.result == "pass" and row.validation_class == "publication_host_verification"
    ]
    publication_state = (
        "published"
        if publication_deploy_receipt_rows and publication_host_verification_rows
        else ("held" if publication_hold_rows else "none")
    )
    if publication_deploy_receipt_rows and publication_host_verification_rows:
        public_release_state = "released_verified"
    elif public_release_blocked:
        public_release_state = "requested_and_blocked"
    elif public_release_not_authorized:
        public_release_state = "not_authorized_by_operator"
    elif release_candidate_gate_ready:
        public_release_state = "not_authorized_by_operator"
    elif historical_release_candidate_gate_decision:
        public_release_state = "gate_blocked_non_goal"
    else:
        public_release_state = "not_requested"
    git_remote_publication = str(git_publication_trace.get("git_remote_publication") or "none")
    publication_reentry_plan = dict(git_publication_trace.get("publication_reentry_plan") or {})
    local_checkpoint_commit = str(git_publication_trace.get("local_checkpoint_commit") or "none")
    local_source_commit = str(git_publication_trace.get("local_source_commit") or commit_hash or "none")
    local_landed_commit = commit_hash or (local_source_commit if local_source_commit != "none" else "")
    remote_published_commit = str(git_publication_trace.get("remote_published_commit") or "none")
    legacy_publication_state = publication_state
    local_branch_topology = str(git_publication_trace.get("local_branch_topology") or "unknown")
    local_branch_ahead = git_publication_trace.get("local_branch_ahead")
    local_branch_behind = git_publication_trace.get("local_branch_behind")
    main_worktree_pending_files = git_publication_trace.get("main_worktree_pending_files")
    publication_worktree_pending_files = git_publication_trace.get("publication_worktree_pending_files")
    owned_changed_paths_pending_files: int | None = None
    worktree_pending_files = git_publication_trace.get("worktree_pending_files")
    publication_worktree_state_value = str(git_publication_trace.get("publication_worktree_state") or "none")
    publication_worktree_state_is_active_hold = publication_worktree_state_value in {
        "prepared",
        "retained_conflict_or_inconsistent_replay",
    } and not git_remote_publication.startswith("pushed")
    publication_prepare_attempted_conflict_or_retained = bool(
        git_publication_trace.get("conflict_paths")
        or publication_worktree_state_is_active_hold
    )
    publication_plan_not_attempted_blocked = bool(
        publication_reentry_plan
        and publication_reentry_plan.get("action_state") == "not_attempted_plan_blocked"
    )
    publication_blocker_observed_not_current = bool(publication_blocker_observed_id and not publication_blocker_receipt_id)
    publication_candidate_blocked = bool(
        publication_candidate_fail_count
        or publication_prepare_attempted_conflict_or_retained
        or publication_plan_not_attempted_blocked
        or publication_blocker_receipt_id
        or publication_blocker_observed_not_current
        or git_publication_trace.get("safe_path_snapshot") is False
    )
    if publication_candidate_blocked and publication_state == "none" and git_remote_publication == "none":
        publication_state = "blocked_or_held_by_publication_candidate"
        legacy_publication_state = publication_state
    source_validation = owner_scope_validation
    publication_candidate_execution_state = (
        "pushed_verified"
        if git_remote_publication == "pushed_verified"
        else (
            "pushed_unverified"
            if git_remote_publication == "pushed_unverified"
            else (
                "prepared_ready_to_push"
                if str(git_publication_trace.get("publication_worktree_state") or "none") == "prepared"
                else (
                    "prepare_attempted_conflict_retained"
                    if publication_prepare_attempted_conflict_or_retained
                    else (
                        "not_attempted_plan_blocked"
                        if publication_plan_not_attempted_blocked
                        else (
                            (
                                "authority_held"
                                if publication_blocker_receipt_id
                                else (
                                    "authority_held_no_current_plan"
                                    if publication_blocker_observed_not_current and not publication_reentry_plan
                                    else "none"
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    if publication_candidate_execution_state == "not_attempted_plan_blocked":
        publication_candidate_validation = "not_run_plan_blocked"
    elif publication_candidate_execution_state == "authority_held_no_current_plan":
        publication_candidate_validation = "not_run_no_current_plan"
    elif publication_candidate_fail_count or publication_prepare_attempted_conflict_or_retained:
        publication_candidate_validation = "failed"
    elif publication_candidate_pass_count and not publication_candidate_fail_count:
        publication_candidate_validation = "pass"
    else:
        publication_candidate_validation = "none"
    publication_blocker_classes: list[str] = []
    if git_publication_trace.get("source_owner_overlap_blocks_auto_snapshot") is True:
        publication_blocker_classes.append("source_owner_overlap")
    blocker_text = "\n".join(part for part in (product_state_text, final_assistant_text) if part).lower()
    if any(marker in blocker_text for marker in (
        "depends on unpublished",
        "prerequisite trace-source commits",
        "prerequisite_trace_source_commits",
        "missing prior source state",
    )) or re.search(r"required_local_prerequisite_commit_count['\"]?\s*[:=]\s*[1-9]", blocker_text):
        publication_blocker_classes.append("prerequisite_unpublished_commits_missing")
    if git_publication_trace.get("conflict_paths") or publication_prepare_attempted_conflict_or_retained:
        publication_blocker_classes.append("inconsistent_clean_base_replay")
    if publication_candidate_fail_count:
        publication_blocker_classes.append("retained_worktree_validation_failed")
    publication_blocker_classes = sorted(set(publication_blocker_classes))
    publication_blocker_class = ",".join(publication_blocker_classes) if publication_blocker_classes else "none"
    publication_blocker_class_source = (
        "current_receipt"
        if publication_blocker_receipt_id
        else (
            "current_publication_plan"
            if publication_reentry_plan
            else (
                "historical_observation"
                if publication_blocker_observed_id
                else "none"
            )
        )
    )
    publication_blocker = (
        "clean_base_replay_requires_prerequisite_trace_source_commits"
        if "prerequisite_unpublished_commits_missing" in publication_blocker_classes
        else (
            "publication_candidate_blocked"
            if publication_candidate_blocked
            else "none"
        )
    )
    tests_state = _capsule_current_tests_state(
        terminal_check_pass_count=terminal_check_pass_count,
        terminal_check_fail_count=terminal_check_fail_count,
        terminal_check_other_count=terminal_check_other_count,
        source_check_pass_count=source_domain_pass_count,
        source_check_fail_count=source_domain_fail_count,
        source_check_other_count=source_domain_other_count,
        publication_candidate_pass_count=publication_candidate_pass_count,
        publication_candidate_fail_count=publication_candidate_fail_count,
        publication_candidate_other_count=publication_candidate_other_count,
        check_pass_count=check_pass_count,
        check_fail_count=check_fail_count,
        check_other_count=check_other_count,
        operation_kind=str(git_publication_trace.get("operation_kind") or ""),
        final_assistant_text=final_assistant_text,
    )
    receipt_assimilation = (
        "pending_or_claim_blocked"
        if receipt_pending_rows
        else (
            "applied"
            if receipt_applied_rows
            else (_capsule_projection_assimilation_summary(projection_assimilation_rows) or "none")
        )
    )
    work_landing_receipt_status = str(work_landing_receipt.get("status") or "none")
    if receipt_assimilation == "none" and work_landing_receipt_status != "none":
        receipt_assimilation = (
            "work_landing_and_publication_receipts_consumed"
            if git_remote_publication.startswith("pushed")
            else "work_landing_receipt_consumed"
        )
    if publication_blocker_receipt_id:
        receipt_assimilation = str(
            publication_blocker_receipt.get("status") or "publication_blocker_captured"
        )
    elif publication_blocker_observed_id and receipt_assimilation == "none":
        receipt_assimilation = "publication_blocker_observed_not_current"
    source_landing_has_residuals = bool(
        open_product_residuals
        or expected_guard_refusal_count
    )
    guarded_refusal_residuals = (
        ["classified_rebuild_drift_pending_settlement"]
        if expected_guard_refusal_count
        else []
    )
    guarded_refusal_residual_summary = (
        ",".join(guarded_refusal_residuals) if guarded_refusal_residuals else "none"
    )
    if commit_hash:
        source_landing_state = (
            "source_scope_landed_with_validation_residuals"
            if effective_blocking_terminal_failures
            else (
                "source_scope_landed_with_guarded_residual"
                if expected_guard_refusal_count
                else (
                    "source_scope_landed_with_residuals"
                    if source_landing_has_residuals
                    else "source_scope_landed"
                )
            )
        )
    else:
        source_landing_state = (
            "source_scope_failed"
            if effective_blocking_terminal_failures
            else (
                "source_scope_guarded_refusal_receipt"
                if expected_guard_refusal_count
                else ("source_scope_passed" if owner_scope_pass_evidence_count > 0 else "source_scope_unknown")
            )
        )
    source_residual_ids = list(_capsule_ordered_unique([
        *open_product_residuals,
        *guarded_refusal_residuals,
    ]))
    source_residual_ids = list(_capsule_ordered_unique(source_residual_ids))
    publication_residual_ids = []
    if publication_candidate_blocked:
        publication_residual_ids.append(publication_blocker_validation_residual)
    if publication_blocker_receipt_id:
        publication_residual_ids.append(f"receipt:{publication_blocker_receipt_id}")
    elif publication_blocker_observed_id:
        publication_residual_ids.append(f"observed:{publication_blocker_observed_id}")
    publication_residual_ids = list(_capsule_ordered_unique(publication_residual_ids))
    source_residuals_summary = ",".join(source_residual_ids) if source_residual_ids else "none"
    publication_residuals_summary = (
        ",".join(publication_residual_ids) if publication_residual_ids else "none"
    )
    source_landing_residual_domain = (
        "source"
        if source_residual_ids
        else ("publication_only" if publication_residual_ids else "none")
    )
    if publication_reentry_plan:
        publication_reentry_plan["blocker_receipt"] = publication_blocker_receipt_id or "none"
        publication_reentry_plan["blocker_event"] = publication_blocker_receipt.get("event") or "none"
    publication_reentry_plan_absent_current = bool(
        publication_candidate_blocked
        and not publication_reentry_plan
        and (publication_blocker_observed_id or publication_blocker_classes)
    )
    reentry_condition = (
        str(publication_blocker_receipt.get("reentry_condition") or "").strip()
        or str(publication_reentry_plan.get("reentry_condition") or "").strip()
        or _capsule_closeout_reentry_condition_from_text(final_assistant_text)
    )
    session_closeout_receipt = _capsule_session_closeout_receipt(
        work_landing_receipt=work_landing_receipt,
        git_publication_trace=git_publication_trace,
        local_landed_commit=local_landed_commit,
        source_landing_state=source_landing_state,
        source_residual_ids=source_residual_ids,
        publication_residual_ids=publication_residual_ids,
        reentry_condition=reentry_condition,
    )
    trace_contract_validation = "pending"
    final_validation = "unknown"
    if public_release_blocked:
        final_validation = "pass_with_public_release_blocked"
    elif release_candidate_gate_ready:
        final_validation = release_candidate_gate_decision
    elif effective_blocking_terminal_failures:
        final_validation = "needs_review"
    elif owner_scope_pass_evidence_count > 0 and publication_candidate_blocked:
        final_validation = "source_pass_publication_blocked"
    elif owner_scope_pass_evidence_count > 0 and public_release_not_authorized:
        final_validation = "pass_with_public_release_not_authorized"
    elif owner_scope_pass_evidence_count > 0 and publication_hold_rows and receipt_pending_rows:
        final_validation = "pass_with_publication_held_and_receipt_pending"
    elif owner_scope_pass_evidence_count > 0 and receipt_pending_rows:
        final_validation = "pass_with_receipt_pending"
    elif owner_scope_pass_evidence_count > 0 and publication_hold_rows:
        final_validation = "pass_with_publication_held"
    elif (
        publication_state == "published"
        and terminal_check_pass_count > 0
        and not ambient_terminal_warning_rows
        and not has_validation_process_warning
        and not expected_guard_refusal_count
    ):
        final_validation = "passed"
    elif expected_guard_refusal_count and (ambient_terminal_warning_rows or has_validation_process_warning):
        final_validation = "pass_with_guarded_refusal_receipt_and_warnings"
    elif expected_guard_refusal_count:
        final_validation = "pass_with_guarded_refusal_receipt"
    elif owner_scope_pass_evidence_count > 0 and ambient_terminal_warning_rows and has_validation_process_warning:
        final_validation = "pass_with_external_and_validation_process_warnings"
    elif owner_scope_pass_evidence_count > 0 and ambient_terminal_warning_rows:
        final_validation = "pass_with_external_warnings"
    elif owner_scope_pass_evidence_count > 0 and has_validation_process_warning:
        final_validation = "pass_with_validation_process_warnings"
    elif owner_scope_pass_evidence_count > 0:
        final_validation = "passed"
    elif terminal_check_fail_count:
        final_validation = "needs_review"
    repo_mutation_authority = (
        "owner_scope_pass"
        if owner_scope_validation.startswith("pass")
        else ("owner_scope_needs_review" if owner_scope_validation == "needs_review" else "not_established")
    )
    internal_public_safe_import_authority = (
        "satisfied"
        if internal_authorization == "satisfied"
        else (
            "pending_operator_authorization"
            if internal_authorization == "pending_operator_authorization"
            else "not_established_by_trace"
        )
    )
    external_publication_authority = public_release_authorization
    if public_release_authorization == "not_authorized_by_operator":
        operator_release_disposition = "public_release_not_authorized"
    elif public_release_authorization == "blocked_by_public_release_gate":
        operator_release_disposition = "public_release_blocked"
    elif public_release_authorization == "pending_operator_authorization":
        operator_release_disposition = "pending_operator_authorization"
    else:
        operator_release_disposition = "not_requested"
    repo_mutation_authorization = (
        "operator_task_authorized"
        if commit_hash or owner_scope_validation.startswith("pass")
        else "not_established"
    )
    git_remote_publication_authorization = (
        "authorized_and_published"
        if git_remote_publication.startswith("pushed")
        else (
            "not_established_or_blocked"
            if publication_candidate_blocked or git_remote_publication == "none"
            else "not_established"
        )
    )
    external_public_release_authorization = (
        "not_requested"
        if public_release_state == "not_requested"
        else public_release_authorization
    )
    authority_registers = {
        "schema_version": "agent_trace_authority_registers_v1",
        "repo_mutation_authority": repo_mutation_authority,
        "internal_public_safe_import_authority": internal_public_safe_import_authority,
        "external_publication_authority": external_publication_authority,
        "operator_release_disposition": operator_release_disposition,
        "repo_mutation_authorization": repo_mutation_authorization,
        "git_remote_publication_authorization": git_remote_publication_authorization,
        "external_public_release_authorization": external_public_release_authorization,
        "owner_scope_pass_evidence_count": owner_scope_pass_evidence_count,
        "ambient_owner_scope_pass_evidence_count": len(paper_module_ambient_owner_scope_pass_rows),
    }
    continuation_genealogy = {
        "schema_version": "agent_trace_continuation_genealogy_v1",
        "previous_trace_deficits": "unknown_without_prior_capsule",
        "new_commit": commit_hash or "none",
        "closed_deficits": 0,
        "remaining_deficits": 0,
        "basis": "current_capsule_source_context_and_commit_rows",
    }
    validation_class_counts: dict[str, int] = {}
    for row in [*check_rows, *governance_rows, *diagnostic_rows]:
        key = row.validation_class or "unclassified"
        validation_class_counts[key] = validation_class_counts.get(key, 0) + 1
    validation_class_summary = " ".join(
        f"{key}={value}" for key, value in sorted(validation_class_counts.items())
    ) or "none=0"
    terminal_failure_class_summary = (
        f"current_terminal_failure={current_terminal_failure_count} "
        f"publication_candidate_failure={publication_candidate_fail_count} "
        f"recovered_failure={recovered_failures} "
        f"stale_window_failure={stale_window_failure_count} "
        f"not_validated={not_validated_count} "
        f"contradictory_closeout={contradictory_closeout_count} "
        f"expected_guard_refusal={expected_guard_refusal_count}"
    )
    validation_domain_counts: dict[str, int] = {}
    workspace_role_counts: dict[str, int] = {}
    for row in [*check_rows, *governance_rows, *diagnostic_rows]:
        domain_key = row.validation_domain or "unclassified"
        workspace_key = row.workspace_role or "none"
        validation_domain_counts[domain_key] = validation_domain_counts.get(domain_key, 0) + 1
        workspace_role_counts[workspace_key] = workspace_role_counts.get(workspace_key, 0) + 1
    residual_summary = ",".join(open_product_residuals) if open_product_residuals else "none"
    validation_process_residual_summary = (
        ",".join(open_validation_process_residuals) if open_validation_process_residuals else "none"
    )
    closed_residuals_seen_summary = ",".join(closed_residuals_seen) if closed_residuals_seen else "none"
    blocked_external_observation_residuals_summary = (
        ",".join(blocked_external_observation_residuals)
        if blocked_external_observation_residuals
        else "none"
    )
    projection_or_view_artifacts_seen_summary = (
        ",".join(projection_or_view_artifacts_seen) if projection_or_view_artifacts_seen else "none"
    )
    unresolved_residual_mentions_summary = (
        ",".join(unresolved_residual_mentions) if unresolved_residual_mentions else "none"
    )
    selected_window_unresolved_residual_mentions_summary = (
        ",".join(selected_window_unresolved_residual_mentions)
        if selected_window_unresolved_residual_mentions
        else "none"
    )
    passive_residual_mentions_observed_summary = (
        ",".join(passive_residual_mentions_observed) if passive_residual_mentions_observed else "none"
    )
    passive_residual_mentions_scope = (
        "prompt_file_or_historical_excerpt" if passive_residual_mentions_observed else "none"
    )
    publication_reentry_plan_summary = (
        "absent_current_plan"
        if publication_reentry_plan_absent_current
        else "none"
        if not publication_reentry_plan
        else (
            f"schema={publication_reentry_plan.get('schema')} "
            f"status={publication_reentry_plan.get('status')} "
            f"action_state={publication_reentry_plan.get('action_state')} "
            f"source_commit={publication_reentry_plan.get('source_commit') or 'none'} "
            f"selected_commit_count={publication_reentry_plan.get('selected_commit_count') or 0} "
            f"operator_selected_commit_count={publication_reentry_plan.get('operator_selected_commit_count') or 0} "
            "required_local_prerequisite_commit_count="
            f"{publication_reentry_plan.get('required_local_prerequisite_commit_count') or 0} "
            f"selected_path_count={publication_reentry_plan.get('selected_path_count') or 0} "
            f"recommended_next_mode={publication_reentry_plan.get('recommended_next_mode') or 'none'} "
            f"plan_fingerprint={publication_reentry_plan.get('plan_fingerprint') or 'none'} "
            f"blocker_receipt={publication_reentry_plan.get('blocker_receipt') or 'none'} "
            f"blocker_event={publication_reentry_plan.get('blocker_event') or 'none'}"
        )
    )
    captured_residual_summary = ",".join(captured_residual_ids) if captured_residual_ids else "none"
    closeout_present = bool(final_assistant_text or commit_hash)
    edit_event_paths = sorted({str(row.get("path") or "") for row in edit_rows if row.get("path")})
    commit_changed_paths = _capsule_commit_changed_paths(commit_hash=commit_hash, cwd=turn.cwd) if commit_hash else []
    changed_path_classes = _capsule_changed_path_classes(
        commit_changed_paths=commit_changed_paths,
        edit_event_paths=edit_event_paths,
    )
    changed_paths = list(changed_path_classes["all_changed_paths"])
    main_dirty_paths = [
        _capsule_public_trace_path(str(path))
        for path in (git_publication_trace.get("main_worktree_dirty_paths") or [])
        if _capsule_public_trace_path(str(path))
    ]
    if main_dirty_paths:
        owned_changed_paths_pending_files = len(set(main_dirty_paths) & set(changed_paths))
    elif main_worktree_pending_files is not None:
        owned_changed_paths_pending_files = 0
    changed = "none captured"
    if changed_paths:
        changed = _capsule_changed_summary(changed_path_classes)
    final_delta = _capsule_final_delta_for_trace(
        commit_hash=commit_hash,
        changed_paths=changed_paths,
        cwd=turn.cwd or str(REPO_ROOT),
    )
    final_delta_attached = bool(final_delta.get("attached"))
    landed_commit_validation_refs = _capsule_landed_commit_validation_refs(
        terminal_check_rows=terminal_check_rows,
        terminal_governance_rows=terminal_governance_rows,
    )
    landed_commit_sequence = _capsule_landed_commit_sequence(
        commit_rows=commit_rows,
        cwd=turn.cwd,
        terminal_commit_hash=commit_hash,
        final_delta=final_delta,
        publication_state=publication_state,
        git_publication_trace=git_publication_trace,
        validation_refs=landed_commit_validation_refs,
    )
    edit_event_log_attached = bool(edit_rows)
    source_excerpt_lines, source_excerpt_stats = _capsule_source_excerpt_sections(
        renderable,
        source_sha16=source_sha16,
        prompt_text=turn.prompt_text,
    )
    type_b_source_excerpt_affordance = _capsule_type_b_source_excerpt_affordance(
        changed_paths,
        source_excerpt_stats,
    )
    requested_source_claim_missing = (
        _capsule_closeout_claims_requested_source_excerpts(final_assistant_text)
        and int(source_excerpt_stats.get("agent_requested_emitted_refs") or source_excerpt_stats.get("agent_requested_refs") or 0) == 0
    )
    requested_source_omitted = int(source_excerpt_stats.get("agent_requested_omitted_refs") or 0)
    source_excerpt_lint_warnings: list[str] = []
    if requested_source_omitted:
        source_excerpt_lint_warnings.append("requested_excerpt_dropped")
    if requested_source_claim_missing:
        source_excerpt_lint_warnings.append("contradictory_closeout_requested_source_missing")
    evidence_manifest_lines, evidence_manifest = _capsule_evidence_manifest(
        renderable=renderable,
        edit_rows=edit_rows,
        final_delta=final_delta,
        source_excerpt_stats=source_excerpt_stats,
        check_rows=check_rows,
        governance_rows=governance_rows,
        final_assistant_text=final_assistant_text,
    )
    if evidence_manifest.get("class_counts", {}).get("passive_mention"):
        source_excerpt_lint_warnings.append("passive_mentions_without_evidence")
    result_summary = _capsule_result_summary(turn, commit_title)
    subagent_packet = _subagent_packet_for_turn_window(turn, limit=None)
    subagent_count = int(subagent_packet.get("count") or 0)
    linked_subagent_trace_count = int(subagent_packet.get("linked_trace_count") or 0)
    visible_subagent_count = int(subagent_packet.get("visible_count") or 0)
    subagent_visited = set(_subagent_visited or set())
    if turn.provider and turn.session_id:
        subagent_visited.add(f"{turn.provider}:{turn.session_id}")
    if embed_subagent_traces:
        subagent_trace_bundle_lines, subagent_trace_bundle = _capsule_subagent_trace_bundle(
            subagent_packet,
            include_prompt_body=include_prompt_body,
            intern_repeated_prompts=intern_repeated_prompts,
            depth=_subagent_depth,
            visited=subagent_visited,
        )
    else:
        subagent_trace_bundle_lines = []
        subagent_trace_bundle = {
            "schema_version": "agent_trace_subagent_embedded_bundle_v1",
            "mode": "disabled",
            "count": 0,
            "rendered_count": 0,
            "omitted_count": 0,
            "bytes": 0,
            "depth": _subagent_depth,
            "rows": [],
        }
    child_execution_visited = set(_child_execution_visited or set())
    if embed_child_executions:
        child_execution_bundle_lines, child_execution_bundle = _capsule_child_execution_bundle(
            turn,
            subagent_packet=subagent_packet,
            subagent_trace_bundle=subagent_trace_bundle,
            include_prompt_body=include_prompt_body,
            intern_repeated_prompts=intern_repeated_prompts,
            depth=_child_execution_depth,
            visited=child_execution_visited,
        )
    else:
        child_execution_bundle_lines = []
        child_execution_bundle = {
            "schema_version": "agent_trace_child_execution_bundle_v1",
            "mode": "disabled",
            "native_subagent_count": subagent_count,
            "subagent_embedded_count": subagent_trace_bundle.get("rendered_count", 0),
            "workflow_count": 0,
            "workflow_worker_count": 0,
            "workflow_worker_outline_count": 0,
            "embedded_trace_count": 0,
            "embedded_workflow_trace_count": 0,
            "aggregate_output_count": 0,
            "aggregate_only_count": 0,
            "omitted_count": 0,
            "bytes": 0,
            "depth": _child_execution_depth,
            "rows": [],
        }
    display_source_window = _trace_display_source_window(turn, source_window)
    selected_window_only = display_source_window in {"selected_turn", "latest_prompt_cycle"}
    full_thread_available = _trace_full_thread_available(turn, display_source_window)
    substrate_diff_required = display_source_window != "full_thread_concise"
    substrate_diff_state = "exact_hunks_attached" if final_delta_attached else (
        "edit_event_log_only" if edit_rows else "no_diff_evidence_captured"
    )
    commit_diff_missing = bool(commit_summary and substrate_diff_required and not final_delta_attached)
    if commit_diff_missing:
        substrate_diff_state = "missing_exact_plus_minus"
    no_edit_claim_allowed = (
        display_source_window == "full_thread"
        and not edit_rows
        and not commit_summary
    )
    thread_total_edits = (
        "has_edit_or_commit_evidence"
        if edit_rows or commit_summary
        else ("not_proven_absent" if display_source_window == "full_thread" else "unknown_not_full_thread")
    )
    copy_scope_warning = "LATEST ONLY - not full thread" if selected_window_only else ""
    recommended_scope = "full_thread" if selected_window_only and full_thread_available else display_source_window
    operator_intervention_full_count = None if selected_window_only and full_thread_available else 0
    scope_semantics = _capsule_scope_semantics(
        status_text=status_text,
        display_source_window=display_source_window,
        full_thread_available=full_thread_available,
        selected_window_only=selected_window_only,
        no_edit_claim_allowed=no_edit_claim_allowed,
    )
    status_label = str(scope_semantics["status_label"])
    ui_diff_only = False
    exact_diff_required = substrate_diff_required and bool(edit_rows or commit_summary)
    diff_reconciler_reasons: list[str] = []
    if display_source_window == "full_thread_concise":
        diff_reconciler_status = "summary_only_allowed"
        diff_reconciler_severity = "green"
        diff_reconciler_reasons.append("full_thread_concise_summary_exception")
    elif final_delta_attached:
        diff_reconciler_status = "aligned_exact_substrate_diff"
        diff_reconciler_severity = "green"
    elif commit_diff_missing:
        diff_reconciler_status = "commit_without_exact_diff"
        diff_reconciler_severity = "red"
        diff_reconciler_reasons.append("commit_seen_without_git_show_patch")
    elif edit_rows:
        diff_reconciler_status = "edit_event_log_without_final_delta"
        diff_reconciler_severity = "amber"
        diff_reconciler_reasons.append("tool_edit_events_are_chronology_not_final_substrate_delta")
    elif exact_diff_required:
        diff_reconciler_status = "missing_exact_substrate_diff"
        diff_reconciler_severity = "red"
        diff_reconciler_reasons.append("edit_or_commit_evidence_requires_plus_minus_hunks")
    elif no_edit_claim_allowed:
        diff_reconciler_status = "no_edits_proven_for_full_thread_scope"
        diff_reconciler_severity = "green"
    else:
        diff_reconciler_status = "no_edits_captured_in_scoped_window"
        diff_reconciler_severity = "amber"
        diff_reconciler_reasons.append("zero_edit_count_is_window_local")
    source_context_demand = _capsule_source_context_demand(
        prompt_text=turn.prompt_text,
        final_assistant_text=final_assistant_text,
        changed_paths=changed_paths,
        final_delta=final_delta,
        type_b_source_excerpt_affordance=type_b_source_excerpt_affordance,
        source_excerpt_stats=source_excerpt_stats,
    )
    source_slice_requests = _capsule_source_slice_requests(
        source_context_demand=source_context_demand,
        source_excerpt_stats=source_excerpt_stats,
        final_delta=final_delta,
    )
    type_b_decision_bundle = _capsule_type_b_decision_bundle(
        source_context_demand=source_context_demand,
        source_slice_requests=source_slice_requests,
        cwd=Path(turn.cwd or REPO_ROOT),
        final_delta=final_delta,
        child_execution_bundle=child_execution_bundle,
    )
    source_slice_manifest = _capsule_source_slice_manifest(
        source_slice_requests=source_slice_requests,
        source_excerpt_stats=source_excerpt_stats,
        repo_head=str(_capsule_repo_cut_plane().get("head") or ""),
        type_b_decision_bundle=type_b_decision_bundle,
    )
    source_context_deficit = _capsule_source_context_deficit(
        source_slice_requests=source_slice_requests,
        final_delta=final_delta,
        include_raw_sidecar=include_raw_sidecar,
    )
    source_context_readiness = _capsule_source_context_readiness(
        source_context_demand=source_context_demand,
        source_slice_requests=source_slice_requests,
        source_context_deficit=source_context_deficit,
        source_slice_manifest=source_slice_manifest,
        source_excerpt_stats=source_excerpt_stats,
    )
    continuation_genealogy["remaining_deficits"] = int(source_context_deficit.get("active_count") or 0)
    if (
        str(source_context_demand.get("state") or "").startswith("required")
        and source_context_readiness.get("overall") == "green"
    ):
        continuation_genealogy["closed_deficits"] = 1
    type_b_source_closeout_lint = _capsule_type_b_source_closeout_lint(
        source_context_demand=source_context_demand,
        source_context_readiness=source_context_readiness,
    )
    type_b_source_excerpt_affordance["policy"] = "optional_until_source_context_demand"
    type_b_source_excerpt_affordance["demand_state"] = source_context_demand.get("state") or "none"
    type_b_source_excerpt_affordance["source_context_satisfaction"] = (
        source_context_demand.get("satisfaction") or ""
    )
    type_b_source_excerpt_affordance["copy_readiness_effect"] = (
        source_context_readiness.get("copy_readiness_effect") or "none"
    )
    copy_readiness_blockers: list[str] = []
    copy_readiness_warnings: list[str] = []
    if diff_reconciler_severity == "red":
        copy_readiness_blockers.append(diff_reconciler_status)
    if diff_reconciler_severity == "amber":
        copy_readiness_warnings.append(diff_reconciler_status)
    if selected_window_only and full_thread_available:
        copy_readiness_warnings.append("selected_window_only_full_thread_available")
    copy_readiness_warnings.extend(source_excerpt_lint_warnings)
    if type_b_source_closeout_lint.get("result") == "warn":
        copy_readiness_warnings.append("source_context_deficit")
    copy_readiness_state = (
        "red" if copy_readiness_blockers
        else ("amber" if copy_readiness_warnings else "green")
    )
    type_b_lint_result = "block" if copy_readiness_blockers else ("warn" if copy_readiness_warnings else "pass")
    type_b_no_edit_language = (
        "no edits were made in the covered full thread"
        if no_edit_claim_allowed
        else "no edits captured in this source window"
    )
    if not changed_paths:
        changed = type_b_no_edit_language
    evidence_tier = {
        "schema_version": "agent_trace_evidence_tier_v1",
        "selected_tier": "tier_1_trace_capsule_projection",
        "provider_forensic_available": bool(source_sha16),
        "provider_byte_lossless": False,
        "visible_clip_lossless_for_copied_source": True,
        "source_truth_boundary": "copied-source-lossless; provider byte losslessness requires raw provider source",
    }
    terminal_validation_state = (
        "terminal_failures_present" if current_terminal_failure_count
        else (
            "terminal_recovered_failures_present" if (stale_window_failure_count or recovered_failures)
            else (
                "terminal_expected_guarded_refusal_present"
                if expected_guard_refusal_count
                else (
                    "terminal_pass_present"
                    if terminal_check_pass_count
                    else ("non_terminal_validation_only" if check_rows else "not_captured")
                )
            )
        )
    )
    stats_source_label = (
        f"capsule_turn=#{turn.turn_index} source_window={display_source_window} "
        f"prompt_sha16={turn.prompt_sha256_16} source_sha16={source_sha16}"
    )
    requested_excerpt_path_summary = ";".join(
        f"{row.get('path', '')}=>{','.join(row.get('row_ids', []))}"
        for row in source_excerpt_stats.get("agent_requested_path_rows", [])[:8]
    ) or "none"
    visible_note_count = max(0, note_index - 1)
    pivot_count = sum(1 for event in reasoning_events if event.category == "pivot")
    route_decision_count = sum(1 for event in reasoning_events if event.category == "route_decision")
    decision_count = sum(1 for event in reasoning_events if event.category == "decision")
    validation_intent_count = sum(1 for event in reasoning_events if event.category == "validation_intent")
    reasoning_phase_count = len(_capsule_reasoning_digest_events(reasoning_events))
    source_watermark = _source_watermark_for_turn(turn)
    trace_cut_receipt = _capsule_trace_cut_receipt(
        turn=turn,
        requested_source_window=source_window,
        display_source_window=display_source_window,
        recommended_scope=recommended_scope,
        source_sha16=source_sha16,
        source_watermark=source_watermark,
        full_thread_available=full_thread_available,
        selected_window_only=selected_window_only,
        final_delta=final_delta,
        include_raw_sidecar=include_raw_sidecar,
        scope_semantics=scope_semantics,
    )
    latest_selection_receipt = _capsule_latest_selection_receipt(
        turn=turn,
        trace_cut_receipt=trace_cut_receipt,
        source_watermark=source_watermark,
    )
    trace_provenance_attestation = _capsule_trace_provenance_attestation(
        turn=turn,
        trace_cut_receipt=trace_cut_receipt,
        final_delta=final_delta,
        source_excerpt_stats=source_excerpt_stats,
        include_raw_sidecar=include_raw_sidecar,
    )
    open_product_residual_lines = _capsule_scoped_absence_lines(
        "open_product_residuals",
        residual_summary,
        scope_semantics,
    )
    open_validation_process_residual_lines = _capsule_scoped_absence_lines(
        "open_validation_process_residuals",
        validation_process_residual_summary,
        scope_semantics,
    )
    open_product_residual_semantics = _capsule_scoped_absence_value(residual_summary, scope_semantics)
    open_validation_process_residual_semantics = _capsule_scoped_absence_value(
        validation_process_residual_summary,
        scope_semantics,
    )
    publication_worktree_dir = str(git_publication_trace.get("publication_worktree_dir") or "none")
    publication_worktree_state = str(git_publication_trace.get("publication_worktree_state") or "none")
    retained_conflict_paths = [
        str(path)
        for path in git_publication_trace.get("conflict_paths") or []
        if str(path)
    ]
    retained_publication_worktree_summary = (
        f"path={publication_worktree_dir} "
        f"state={publication_worktree_state} "
        f"unmerged_paths={','.join(retained_conflict_paths) or 'none'} "
        f"selected_paths={git_publication_trace.get('selected_path_count') or 0} "
        "source_owner_overlap_blocks_auto_snapshot="
        f"{git_publication_trace.get('source_owner_overlap_blocks_auto_snapshot') if git_publication_trace.get('source_owner_overlap_blocks_auto_snapshot') is not None else 'unknown'} "
        "safe_path_snapshot="
        f"{git_publication_trace.get('safe_path_snapshot') if git_publication_trace.get('safe_path_snapshot') is not None else 'unknown'}"
    )
    open_claim_lines = _capsule_open_claim_lines(turn, scope_semantics)
    summary_claims: list[dict[str, str]] = []

    def add_summary_claim(
        claim: str,
        value: Any,
        *,
        scope: str = display_source_window,
        evidence: str = "producer_state",
        cannot_prove: str = "none",
        render_policy: str = "scope_qualified",
    ) -> None:
        summary_claims.append({
            "claim": claim,
            "value": str(value),
            "scope": scope,
            "evidence": evidence,
            "cannot_prove": cannot_prove,
            "render_policy": render_policy,
        })

    add_summary_claim("status", status_label, evidence="turn.is_complete+copy_scope")
    add_summary_claim("result", result_summary, evidence="final_assistant_text_or_commit_title")
    add_summary_claim("changed", changed, evidence="commit_changed_paths+edit_rows+final_delta")
    add_summary_claim("landed_commit_sequence", _capsule_landed_commit_sequence_summary(landed_commit_sequence), evidence="produced_commit_outputs+git_commit_path_scan")
    add_summary_claim("commit_changed_paths", _capsule_path_list_summary(changed_path_classes["commit_changed_paths"]), evidence="git_commit_path_scan")
    add_summary_claim("source_owner_paths_changed", _capsule_path_list_summary(changed_path_classes["source_owner_paths"]), evidence="edit_rows+path_classifier")
    add_summary_claim("generated_projection_paths", _capsule_path_list_summary(changed_path_classes["generated_projection_paths"]), evidence="commit_path_classifier")
    add_summary_claim("test_paths_changed", _capsule_path_list_summary(changed_path_classes["test_paths"]), evidence="commit_path_classifier")
    add_summary_claim("final_validation", final_validation, evidence="classified_terminal_checks")
    add_summary_claim("owner_scope_validation", owner_scope_validation, evidence="owner_scope_terminal_checks")
    add_summary_claim("trace_contract_validation", trace_contract_validation, evidence="trace_self_parse_receipt")
    add_summary_claim("internal_authorization", internal_authorization, evidence="governance_receipts")
    add_summary_claim("public_release_authorization", public_release_authorization, evidence="governance_receipts")
    add_summary_claim("source_landing", source_landing_state, evidence="commit_and_dirty_residual_classification")
    add_summary_claim("source_residuals", source_residuals_summary, evidence="source_residual_domain_classifier")
    add_summary_claim("publication_residuals", publication_residuals_summary, evidence="publication_residual_domain_classifier")
    add_summary_claim("source_landing_residual_domain", source_landing_residual_domain, evidence="residual_domain_splitter")
    add_summary_claim("source_validation", source_validation, evidence="source_domain_terminal_checks")
    add_summary_claim("publication_candidate_execution_state", publication_candidate_execution_state, evidence="publication_execution_receipts")
    add_summary_claim("publication_candidate_validation", publication_candidate_validation, evidence="publication_candidate_terminal_checks")
    add_summary_claim("legacy_publication_state", legacy_publication_state, evidence="governance_receipts")
    add_summary_claim("publication_state", publication_state, evidence="legacy_compatibility_field")
    add_summary_claim("publication_blocker", publication_blocker, evidence="publication_candidate_receipts")
    add_summary_claim("publication_blocker_class", publication_blocker_class, evidence="publication_candidate_receipts")
    add_summary_claim("publication_blocker_class_source", publication_blocker_class_source, evidence="publication_candidate_receipts")
    add_summary_claim("git_remote_publication", git_remote_publication, evidence="guarded_push_receipt")
    add_summary_claim("local_landed_commit", local_landed_commit or "none", evidence="scoped_commit_or_landed_commit_sequence")
    add_summary_claim("local_source_commit", local_source_commit, evidence="publication_source_or_landed_commit")
    add_summary_claim("local_checkpoint_commit", local_checkpoint_commit, evidence="checkpoint_closeout_or_command_receipt")
    add_summary_claim("remote_published_commit", remote_published_commit, evidence="publication_lane_or_guarded_push_receipt")
    add_summary_claim("external_public_release_state", public_release_state, evidence="release_gate_and_publication_receipts")
    add_summary_claim("public_release_state", public_release_state, evidence="legacy_compatibility_field")
    add_summary_claim("release_gate_kind", release_gate_kind, evidence="release_gate")
    add_summary_claim("repo_mutation_authorization", repo_mutation_authorization, evidence="operator_task_and_owner_scope")
    add_summary_claim("git_remote_publication_authorization", git_remote_publication_authorization, evidence="publication_gate")
    add_summary_claim("external_public_release_authorization", external_public_release_authorization, evidence="release_gate")
    add_summary_claim("local_branch_topology", local_branch_topology, evidence="git_status_branch_receipts")
    add_summary_claim("worktree_state", "see_worktree_state_line", evidence="current_git_status_and_publication_receipts")
    add_summary_claim("evidence_scope", "current_receipt_surfaces_only", evidence="command_surface_filter")
    add_summary_claim("publication_replay_relation", "see_publication_replay_relation_line", evidence="current_publication_prepare_receipt")
    add_summary_claim("retained_publication_worktree", "see_retained_publication_worktree_line", evidence="publication_candidate_receipts")
    add_summary_claim("tests", tests_state, evidence="terminal_checks_or_closeout_validation_semantics")
    add_summary_claim("receipt_assimilation", receipt_assimilation, evidence="task_ledger_and_projection_receipts")
    add_summary_claim("session_closeout_receipt", _capsule_session_closeout_receipt_summary(session_closeout_receipt), evidence="work_landing_publication_and_dirty_state_receipts")
    add_summary_claim("publication_blocker_receipt", publication_blocker_receipt_id or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("publication_blocker_event", publication_blocker_receipt.get("event") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_scope", publication_blocker_receipt.get("receipt_scope") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_source_command", publication_blocker_receipt.get("receipt_source_command") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_subject_id", publication_blocker_receipt.get("receipt_subject_id") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_event_id", publication_blocker_receipt.get("receipt_event_id") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_event_type", publication_blocker_receipt.get("receipt_event_type") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_surface", publication_blocker_receipt.get("receipt_surface") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_payload_commit", publication_blocker_receipt.get("receipt_payload_commit") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("receipt_supersedes_or_replaces", publication_blocker_receipt.get("receipt_supersedes_or_replaces") or "none", evidence="task_ledger_authority_journal")
    add_summary_claim("publication_blocker_observed", "see_publication_blocker_observed_line", evidence="publication_blocker_observation")
    add_summary_claim("reentry_condition", reentry_condition or "none", evidence="receipt_plane_or_closeout_reentry")
    add_summary_claim("publication_reentry_plan", "see_publication_reentry_plan_line", evidence="current_publication_plan_receipt")
    add_summary_claim("ambient_validation", ambient_validation, evidence="ambient_terminal_rows")
    add_summary_claim("ambient_warning_class", ambient_warning_class_summary, evidence="ambient_warning_classifier")
    add_summary_claim("continuation_genealogy", "see_continuation_genealogy_line", evidence="current_capsule_source_context")
    for line in open_product_residual_lines:
        key, _, value = line.partition(": ")
        add_summary_claim(key, value, scope=str(scope_semantics["absence_scope"]), evidence="residual_classifier", cannot_prove="full_thread_absence" if selected_window_only else "none")
    for line in open_validation_process_residual_lines:
        key, _, value = line.partition(": ")
        add_summary_claim(key, value, scope=str(scope_semantics["absence_scope"]), evidence="validation_process_residual_classifier", cannot_prove="full_thread_absence" if selected_window_only else "none")
    add_summary_claim("closed_residuals_seen", closed_residuals_seen_summary, evidence="task_ledger_receipts")
    add_summary_claim("blocked_external_observation_residuals", blocked_external_observation_residuals_summary, evidence="task_ledger_receipts")
    add_summary_claim("ambient_validation_warnings", ambient_validation_warning_summary, evidence="ambient_warning_classifier")
    add_summary_claim("release_candidate_gate", release_candidate_gate_decision or "none", evidence="release_candidate_classifier")
    add_summary_claim("historical_terminal_failures_superseded", historical_terminal_failures_superseded, evidence="terminal_check_ordering")
    add_summary_claim("expected_guard_refusals", expected_guard_refusal_count, evidence="guarded_refusal_classifier")
    add_summary_claim("guarded_refusal_residuals", guarded_refusal_residual_summary, evidence="guarded_refusal_classifier")
    add_summary_claim("projection_or_view_artifacts_seen", projection_or_view_artifacts_seen_summary, evidence="projection_artifact_classifier")
    add_summary_claim("unresolved_residual_mentions", unresolved_residual_mentions_summary, evidence="residual_mention_classifier")
    add_summary_claim("unresolved_residual_mentions_selected_window", selected_window_unresolved_residual_mentions_summary, evidence="current_closeout_residual_classifier")
    add_summary_claim("passive_residual_mentions_observed", passive_residual_mentions_observed_summary, evidence="passive_mention_classifier")
    add_summary_claim("passive_residual_mentions_scope", passive_residual_mentions_scope, evidence="passive_mention_classifier")
    add_summary_claim("release_authority", "none", evidence="release_authority_classifier")
    add_summary_claim("authority_registers", "see_authority_registers_line", evidence="authority_register_splitter")
    add_summary_claim("checks", f"pass={check_pass_count} fail={check_fail_count} other={check_other_count} total={len(check_rows)}", evidence="classified_checks")
    add_summary_claim("terminal_checks", f"pass={terminal_check_pass_count} fail={terminal_check_fail_count} other={terminal_check_other_count} total={len(terminal_check_rows)}", evidence="terminal_checks")
    add_summary_claim("owner_scope_terminal_checks", f"pass={owner_terminal_pass_count} fail={owner_terminal_fail_count} other={owner_terminal_other_count} total={len(owner_terminal_check_rows)}", evidence="owner_terminal_checks")
    add_summary_claim("source_domain_terminal_checks", f"pass={source_domain_pass_count} fail={source_domain_fail_count} other={source_domain_other_count} total={len(source_domain_terminal_rows)}", evidence="validation_domains")
    add_summary_claim("publication_candidate_terminal_checks", f"pass={publication_candidate_pass_count} fail={publication_candidate_fail_count} other={publication_candidate_other_count} total={len(publication_candidate_terminal_rows)}", evidence="validation_domains")
    add_summary_claim("validation_progress", "see_validation_semantics", evidence="classified_checks")
    add_summary_claim("terminal_failure_classes", terminal_failure_class_summary, evidence="terminal_failure_classifier")
    add_summary_claim("validation_semantics", "see_validation_semantics_line", evidence="validation_classifier")
    add_summary_claim("governance_receipts", f"pass={governance_pass_count} fail={governance_fail_count} other={governance_other_count} total={len(governance_rows)}", evidence="governance_receipts")
    add_summary_claim("terminal_governance", f"pass={terminal_governance_pass_count} fail={terminal_governance_fail_count} other={terminal_governance_other_count} total={len(terminal_governance_rows)}", evidence="terminal_governance_rows")
    add_summary_claim("diagnostics", f"total={len(diagnostic_rows)} fail={diagnostic_fail_count}", evidence="diagnostic_rows")
    add_summary_claim("visible_progress", f"notes={visible_note_count} source=assistant_visible_only", evidence="assistant_visible_messages")
    add_summary_claim("thinking", f"source=app_visible_assistant_messages notes={visible_note_count}", evidence="assistant_visible_messages")
    for line in open_claim_lines:
        key, _, value = line.partition(": ")
        add_summary_claim(key or "open", value or line, scope=str(scope_semantics["absence_scope"]), evidence="turn.completion_state", cannot_prove="full_thread_open_state" if selected_window_only else "none")
    claim_source_map = _capsule_claim_source_map(summary_claims)
    budget_solver_receipt = _capsule_budget_solver_receipt(
        source_excerpt_stats,
        source_context_demand=source_context_demand,
        source_context_deficit=source_context_deficit,
        source_context_readiness=source_context_readiness,
    )
    copy_readiness_vector = _capsule_copy_readiness_vector(
        copy_readiness_state=copy_readiness_state,
        copy_readiness_blockers=copy_readiness_blockers,
        copy_readiness_warnings=copy_readiness_warnings,
        scope_semantics=scope_semantics,
        final_delta_attached=final_delta_attached,
        diff_reconciler_status=diff_reconciler_status,
        claim_source_map=claim_source_map,
        source_excerpt_stats=source_excerpt_stats,
        source_context_readiness=source_context_readiness,
        latest_selection_receipt=latest_selection_receipt,
    )
    trace_self_parse_receipt = _capsule_trace_self_parse_receipt(
        trace_cut_receipt=trace_cut_receipt,
        scope_semantics=scope_semantics,
        claim_source_map=claim_source_map,
        final_delta_attached=final_delta_attached,
        edit_event_log_attached=edit_event_log_attached,
    )
    copy_readiness_vector["parser_roundtrip"] = _capsule_parser_roundtrip_readiness(trace_self_parse_receipt)
    _capsule_update_session_closeout_projection(
        session_closeout_receipt,
        source_context_readiness=source_context_readiness,
        trace_self_parse_receipt=trace_self_parse_receipt,
    )
    trace_context_ids = _capsule_trace_context_ids(
        turn=turn,
        trace_cut_receipt=trace_cut_receipt,
        source_sha16=source_sha16,
    )
    title_authority = _capsule_title_authority(title, turn=turn, commit_title=commit_title)
    title_authority_warning = str(title_authority.get("warning") or "none")
    evidence_node_graph = _capsule_evidence_node_graph(
        trace_cut_receipt=trace_cut_receipt,
        latest_selection_receipt=latest_selection_receipt,
        title_authority=title_authority,
        trace_provenance_attestation=trace_provenance_attestation,
        claim_source_map=claim_source_map,
        final_delta=final_delta,
        final_delta_attached=final_delta_attached,
        edit_event_log_attached=edit_event_log_attached,
        terminal_check_count=len(terminal_check_rows),
        owner_terminal_check_count=len(owner_terminal_check_rows),
        evidence_manifest=evidence_manifest,
        source_excerpt_stats=source_excerpt_stats,
        include_raw_sidecar=include_raw_sidecar,
    )
    defeater_register = _capsule_defeater_register(
        scope_semantics=scope_semantics,
        latest_selection_receipt=latest_selection_receipt,
        title_authority=title_authority,
        trace_self_parse_receipt=trace_self_parse_receipt,
        budget_solver_receipt=budget_solver_receipt,
    )
    assurance_case_graph = _capsule_assurance_case_graph(
        latest_selection_receipt=latest_selection_receipt,
        title_authority=title_authority,
        trace_self_parse_receipt=trace_self_parse_receipt,
        budget_solver_receipt=budget_solver_receipt,
        defeater_register=defeater_register,
    )
    reader_latest_state = (
        "latest_completed_response"
        if latest_selection_receipt.get("selected_is_latest_completed_response")
        else (
            "response_in_progress"
            if latest_selection_receipt.get("latest_prompt_pending_response")
            else "not_thread_tail"
        )
    )
    reader_context_state = (
        "decision_source_context_deficit"
        if budget_solver_receipt.get("source_context_active_deficit")
        else (
            "selected_window_only_context_deficit"
            if selected_window_only and full_thread_available
            else "declared_scope_context_available"
        )
    )
    if reader_context_state == "decision_source_context_deficit":
        missing_ref = (budget_solver_receipt.get("top_omitted_decision_refs") or ["source_context_deficit"])[0]
        reader_next_action = f"request_smallest_decision_changing_source_slice:{missing_ref}"
    elif reader_latest_state == "latest_completed_response" and reader_context_state == "selected_window_only_context_deficit":
        reader_next_action = "use_bundle_for_latest_tail_claims; request_full_thread_only_for_global_absence_or_context"
    elif reader_latest_state == "latest_completed_response":
        reader_next_action = "use_bundle_for_declared_scope"
    elif reader_latest_state == "response_in_progress":
        reader_next_action = "wait_for_completed_response_or_select_latest_completed_turn"
    else:
        reader_next_action = "request_latest_response_bundle_or_full_thread_tail"
    if (
        publication_candidate_execution_state == "authority_held_no_current_plan"
        and reader_context_state != "decision_source_context_deficit"
    ):
        reader_next_action = "rerun_publication_planner_only_if_git_remote_publication_is_in_scope"

    def refresh_trace_contract_state() -> None:
        nonlocal trace_contract_validation, final_validation, copy_readiness_state
        nonlocal reader_next_action, type_b_lint_result
        trace_contract_validation = _capsule_trace_contract_validation(trace_self_parse_receipt)
        final_validation = _capsule_trace_contract_final_validation(
            final_validation,
            trace_contract_validation=trace_contract_validation,
            source_validation=source_validation,
            publication_candidate_execution_state=publication_candidate_execution_state,
        )
        copy_readiness_vector["parser_roundtrip"] = _capsule_parser_roundtrip_readiness(trace_self_parse_receipt)
        if trace_contract_validation == "fail":
            if "self_parse_failure" not in copy_readiness_blockers:
                copy_readiness_blockers.append("self_parse_failure")
            copy_readiness_state = "red"
            copy_readiness_vector["overall"] = "red"
            reader_next_action = "repair_trace_capsule_parser_or_render_contract_before_continuation"
        elif trace_contract_validation == "blocked":
            if "self_parse_blocked" not in copy_readiness_warnings:
                copy_readiness_warnings.append("self_parse_blocked")
            if copy_readiness_state == "green":
                copy_readiness_state = "amber"
            if copy_readiness_vector.get("overall") == "green":
                copy_readiness_vector["overall"] = "amber"
            reader_next_action = "repair_trace_capsule_parser_runtime_before_continuation"
        type_b_lint_result = "block" if copy_readiness_blockers else ("warn" if copy_readiness_warnings else "pass")
        _capsule_update_claim_source_map_value(claim_source_map, "final_validation", final_validation)
        _capsule_update_claim_source_map_value(claim_source_map, "trace_contract_validation", trace_contract_validation)
        _capsule_update_session_closeout_projection(
            session_closeout_receipt,
            source_context_readiness=source_context_readiness,
            trace_self_parse_receipt=trace_self_parse_receipt,
        )

    display_title = _capsule_clean_text(str(title_authority.get("display_title") or "")[:180]) or "Trace Capsule"
    title_first_header = (
        [f"# {display_title}"]
        if _subagent_depth == 0 and _child_execution_depth == 0
        else []
    )
    header = [
        *title_first_header,
        "TRACE CAPSULE v3",
        f"title: {display_title}",
        f"raw_title: {_capsule_clean_text(str(title_authority.get('raw_title') or '')[:180])}",
        f"title_authority_warning: {title_authority_warning}",
        f"provider: {turn.provider}",
        f"session: {_short_session_tag(turn.session_id)}",
        f"turn: {turn.turn_index}",
        _trace_window_header(turn, source_window),
        f"trace_scope: copy_scope={display_source_window} thread_totality={_trace_thread_totality(display_source_window)} full_thread_available={'true' if full_thread_available else 'false'} selected_window_only={'true' if selected_window_only else 'false'}",
        f"latest_selection: selected_turn={latest_selection_receipt['selected_turn_index']} selected_is_thread_tail={'true' if latest_selection_receipt['selected_is_thread_tail'] else 'false'} selected_is_latest_completed_response={'true' if latest_selection_receipt['selected_is_latest_completed_response'] else 'false'} latest_prompt_pending_response={'true' if latest_selection_receipt['latest_prompt_pending_response'] else 'false'}",
        f"trace_context: trace_context_id={trace_context_ids['trace_context_id']} cut_id={trace_context_ids['cut_id']} prompt={trace_context_ids['prompt_sha16']} source={trace_context_ids['source_sha16']}",
        f"scope_semantics: status_label={status_label} completion_scope={scope_semantics['completion_scope']} none_scope={scope_semantics['none_scope']} global_none_claims_allowed={'true' if scope_semantics['global_none_claims_allowed'] else 'false'} unsafe_global_none_claims_blocked={'true' if scope_semantics['unsafe_global_none_claims_blocked'] else 'false'}",
        f"copy_policy: consumer=type_b_continue selected_scope={display_source_window} recommended_scope={recommended_scope} warning={copy_scope_warning or 'none'}",
        f"stats_source: {stats_source_label}",
        f"operator_interventions: selected_window_count=0 full_thread_count={operator_intervention_full_count if operator_intervention_full_count is not None else 'unknown'} full_thread_available={'true' if full_thread_available else 'false'} scope_note={'selected_window_only' if selected_window_only else 'full_thread'}",
        f"diff_contract: substrate_diff={substrate_diff_state} substrate_diff_required={'true' if substrate_diff_required else 'false'} commit_diff_missing={'true' if commit_diff_missing else 'false'} final_delta_attached={'true' if final_delta_attached else 'false'} edit_event_log_attached={'true' if edit_event_log_attached else 'false'} patch_attempts_are_not_final_state=true",
        f"copy_readiness: state={copy_readiness_state} blockers={','.join(copy_readiness_blockers) or 'none'} warnings={','.join(copy_readiness_warnings) or 'none'}",
        _capsule_copy_readiness_vector_line(copy_readiness_vector),
        f"diff_reconciler: status={diff_reconciler_status} severity={diff_reconciler_severity} ui_review_card={'ui_diff_only' if ui_diff_only else 'not_detected'} final_delta={'attached' if final_delta_attached else 'not_attached'} parser_artifact_delta={substrate_diff_state} edit_event_log={'attached' if edit_event_log_attached else 'not_attached'} git_commit_or_worktree={'commit_without_patch' if commit_diff_missing else ('commit_seen' if commit_summary else ('worktree_delta_seen' if final_delta.get('source') == 'git_diff_worktree' else 'not_detected'))}",
        "changed_path_classes: "
        f"authority={changed_path_classes['authority']} "
        f"commit_changed_paths={len(changed_path_classes['commit_changed_paths'])} "
        f"edit_event_paths={len(changed_path_classes['edit_event_paths'])} "
        f"source_owner_paths={len(changed_path_classes['source_owner_paths'])} "
        f"generated_projection_paths={len(changed_path_classes['generated_projection_paths'])} "
        f"test_paths={len(changed_path_classes['test_paths'])} "
        f"unclassified_commit_paths={len(changed_path_classes['unclassified_commit_paths'])}",
        f"evidence_tier: selected={evidence_tier['selected_tier']} provider_byte_lossless=false visible_clip_lossless_for_copied_source=true provider_forensic_available={'true' if evidence_tier['provider_forensic_available'] else 'false'}",
        "type_b_source_excerpt_affordance: "
        f"status={type_b_source_excerpt_affordance['status']} "
        f"suggested={'true' if type_b_source_excerpt_affordance['suggested'] else 'false'} "
        f"mandatory={'true' if type_b_source_excerpt_affordance['mandatory'] else 'false'} "
        f"policy={type_b_source_excerpt_affordance.get('policy') or 'optional_until_source_context_demand'} "
        f"demand_state={type_b_source_excerpt_affordance.get('demand_state') or 'none'} "
        f"source_context_satisfaction={type_b_source_excerpt_affordance.get('source_context_satisfaction') or ''} "
        f"copy_readiness_effect={type_b_source_excerpt_affordance['copy_readiness_effect']} "
        f"agent_requested_refs={type_b_source_excerpt_affordance['agent_requested_refs']} "
        f"agent_requested_seen={type_b_source_excerpt_affordance['agent_requested_seen_refs']} "
        f"agent_requested_omitted={type_b_source_excerpt_affordance['agent_requested_omitted_refs']} "
        f"trigger_paths={','.join(Path(path).name for path in type_b_source_excerpt_affordance['trigger_paths'][:4]) or 'none'} "
        f"affordance={type_b_source_excerpt_affordance['affordance_id'] or 'none'}",
        "source_context_readiness: "
        f"overall={source_context_readiness['overall']} "
        f"demand={source_context_readiness['demand']} "
        f"satisfaction={source_context_readiness['satisfaction']} "
        f"explicit_requests={source_context_readiness['explicit_requests']} "
        f"synthesized_requests={source_context_readiness['synthesized_requests']} "
        f"emitted={source_context_readiness['emitted']} "
        f"satisfied_by_final_delta={source_context_readiness['satisfied_by_final_delta']} "
        f"delta_satisfied_for_changed_contract={source_context_readiness['delta_satisfied_for_changed_contract']} "
        f"omitted={source_context_readiness['omitted']} "
        f"high_regret_missing={source_context_readiness['high_regret_missing']} "
        f"rendered_insufficient={source_context_readiness['rendered_insufficient']} "
        f"slice_quality_warning_count={source_context_readiness['slice_quality_warning_count']} "
        f"blocking_quality_warning_count={source_context_readiness['blocking_quality_warning_count']} "
        f"copy_readiness_effect={source_context_readiness['copy_readiness_effect']}",
        "type_b_source_closeout_lint: "
        f"result={type_b_source_closeout_lint['result']} "
        f"demand_state={type_b_source_closeout_lint['demand_state']} "
        f"readiness={type_b_source_closeout_lint['readiness']} "
        f"high_regret_missing={type_b_source_closeout_lint['high_regret_missing']}",
        "requested_context_survival: "
        f"status={source_excerpt_stats.get('requested_excerpt_survival_status', 'unknown')} "
        f"seen={source_excerpt_stats.get('agent_requested_seen_refs', 0)} "
        f"emitted={source_excerpt_stats.get('agent_requested_emitted_refs', source_excerpt_stats.get('agent_requested_refs', 0))} "
        f"omitted={source_excerpt_stats.get('agent_requested_omitted_refs', 0)} "
        f"warnings={','.join(source_excerpt_lint_warnings) or 'none'}",
        "requested_excerpt_paths: "
        f"path_count={source_excerpt_stats.get('agent_requested_path_count', 0)} "
        f"emitted={source_excerpt_stats.get('agent_requested_emitted_refs', source_excerpt_stats.get('agent_requested_refs', 0))} "
        f"omitted={source_excerpt_stats.get('agent_requested_omitted_refs', 0)} "
        f"rows={requested_excerpt_path_summary}",
        "evidence_manifest: "
        f"rows={evidence_manifest['row_count']} "
        f"requested_source_excerpt={evidence_manifest['class_counts']['requested_source_excerpt']} "
        f"diff_hunk={evidence_manifest['class_counts']['diff_hunk']} "
        f"edit_event_hunk={evidence_manifest['class_counts']['edit_event_hunk']} "
        f"command_return={evidence_manifest['class_counts']['command_return']} "
        f"receipt={evidence_manifest['class_counts']['receipt']} "
        f"passive_mention={evidence_manifest['class_counts']['passive_mention']} "
        "rule=passive_mention_is_not_evidence",
        f"type_b_handoff_lint: result={type_b_lint_result} no_edits_sentence_allowed={'true' if no_edit_claim_allowed else 'false'} required_no_edit_language=\"{type_b_no_edit_language}\"",
        f"terminal_validation_priority: state={terminal_validation_state} terminal_checks={len(terminal_check_rows)} owner_scope_terminal_checks={len(owner_terminal_check_rows)}",
        "embedded_subagent_traces: "
        f"count={subagent_trace_bundle['rendered_count']} "
        f"omitted={subagent_trace_bundle['omitted_count']} "
        f"bytes={subagent_trace_bundle['bytes']} "
        f"mode={subagent_trace_bundle['mode']} "
        "size_policy=no_limit_operator_requested",
        "child_executions: "
        f"workflows={child_execution_bundle['workflow_count']} "
        f"workers={child_execution_bundle['workflow_worker_count']} "
        f"worker_outlines={child_execution_bundle.get('workflow_worker_outline_count') or 0} "
        f"embedded={child_execution_bundle['embedded_trace_count']} "
        f"aggregate_outputs={child_execution_bundle['aggregate_output_count']} "
        f"aggregate_only={child_execution_bundle['aggregate_only_count']} "
        f"omitted={child_execution_bundle['omitted_count']} "
        f"bytes={child_execution_bundle['bytes']} "
        f"mode={child_execution_bundle['mode']} "
        "size_policy=no_limit_operator_requested",
        f"type_b_rule: no_unqualified_no_edits_unless_full_thread_coverage_and_no_edit_claim_allowed; otherwise say no edits captured in this source window",
        f"status: {status_label}",
    ]
    if worked_for:
        header.append(f"worked_for: {worked_for}")
    visible_note_count = max(0, note_index - 1)
    pivot_count = sum(1 for event in reasoning_events if event.category == "pivot")
    route_decision_count = sum(1 for event in reasoning_events if event.category == "route_decision")
    decision_count = sum(1 for event in reasoning_events if event.category == "decision")
    validation_intent_count = sum(1 for event in reasoning_events if event.category == "validation_intent")
    reasoning_phase_count = len(_capsule_reasoning_digest_events(reasoning_events))
    if commit_summary:
        commit_source_index = max((row.source_index for row in episode_evidence), default=10**9) + 1
        episode_evidence.append(CapsuleEpisodeEvidence(
            source_index=commit_source_index,
            row_id="K001",
            kind="commit",
            result="",
        ))
    episode_lines, episode_count = _capsule_episode_lines(
        reasoning_events,
        episode_evidence,
        evidence_summary.terminal_check_by_identity,
    )
    goal_mode_seen = bool(re.search(
        r"\b(goal mode|goal_context|thread_goals|active goal|token_budget|current_telos)\b",
        "\n".join([turn.prompt_text or "", final_assistant_text or ""]),
        re.I,
    ))
    goal_rollup = {
        "schema_version": "agent_trace_goal_rollup_v1",
        "status": "captured_goal_mode" if goal_mode_seen else "not_detected",
        "pass_count": 1 if goal_mode_seen else 0,
        "passes": ([{"kind": "goal_mode_marker", "scope": display_source_window}] if goal_mode_seen else []),
    }
    agent_episode_graph = {
        "schema_version": "agent_episode_graph_v1",
        "composition_root": "agent_episode_graph",
        "provider_thread": {
            "provider": turn.provider,
            "session_id": turn.session_id,
            "selected_turn_index": turn.turn_index,
            "selected_source_window": display_source_window,
            "thread_totality": _trace_thread_totality(display_source_window),
        },
        "nodes": [
            {"id": "e001", "kind": "turn_selected", "turn_index": turn.turn_index, "source_window": display_source_window},
            *([{"id": "e002", "kind": "implementation_episode", "edit_path_count": len(edit_rows), "diff_status": diff_reconciler_status}] if edit_rows or commit_summary else []),
            *([{"id": "e003", "kind": "validation_episode", "terminal_state": terminal_validation_state}] if check_rows or terminal_check_rows else []),
            *([{"id": "e004", "kind": "commit_evidence", "commit_diff_missing": commit_diff_missing}] if commit_summary else []),
            *([{
                "id": "e005",
                "kind": "child_execution_bundle",
                "workflow_count": child_execution_bundle.get("workflow_count", 0),
                "workflow_worker_count": child_execution_bundle.get("workflow_worker_count", 0),
                "embedded_trace_count": child_execution_bundle.get("embedded_trace_count", 0),
                "omitted_count": child_execution_bundle.get("omitted_count", 0),
            }] if (
                child_execution_bundle.get("workflow_count")
                or child_execution_bundle.get("embedded_trace_count")
                or child_execution_bundle.get("omitted_count")
            ) else []),
        ],
        "invariants": {
            "edits_zero_always_scoped": True,
            "exact_diff_required_unless_full_thread_compact": display_source_window != "full_thread_concise",
            "provider_bytes_not_claimed_lossless": True,
        },
    }
    command_return_lines, sidecar_manifest_lines, command_return_stats = _capsule_command_return_sections(
        renderable,
        source_sha16=source_sha16,
        raw_sidecar_available=include_raw_sidecar,
    )
    header.extend([
        f"prompt: {turn.prompt_sha256_16}",
        f"source: {source_sha16}",
        f"coverage: commands={len(renderable)} outputs={commands_with_outputs} edits={len(edit_rows)} checks={len(check_rows)} governance={len(governance_rows)} diagnostics={len(diagnostic_rows)} notes={visible_note_count} edit_scope=captured_window thread_total_edits={thread_total_edits} no_edit_claim_allowed={'true' if no_edit_claim_allowed else 'false'} substrate_diff={substrate_diff_state} substrate_diff_required={'true' if substrate_diff_required else 'false'} commit_diff_missing={'true' if commit_diff_missing else 'false'} final_delta_attached={'true' if final_delta_attached else 'false'} edit_event_log_attached={'true' if edit_event_log_attached else 'false'} truncated_outputs={truncated_outputs} raw_sidecar={'available' if include_raw_sidecar else 'not_materialized'}",
        "source_excerpts: "
        f"count={source_excerpt_stats['count']} lines={source_excerpt_stats['lines']} "
        f"paths={len(source_excerpt_stats['paths'])} omitted={source_excerpt_stats['omitted']} "
        "source=agent_requested_or_prompt_file_refs_or_trace_read_outputs policy=bounded_redacted_line_ranges "
        "carrier=saved_latest_response_bundle practical_budget=~150KB "
        "reference_modes=message_text|full_small_bodies|path_line_shards|standard_projections "
        f"agent_requested_refs={source_excerpt_stats.get('agent_requested_refs', 0)} "
        f"agent_requested_seen={source_excerpt_stats.get('agent_requested_seen_refs', 0)} "
        f"agent_requested_emitted={source_excerpt_stats.get('agent_requested_emitted_refs', source_excerpt_stats.get('agent_requested_refs', 0))} "
        f"agent_requested_omitted={source_excerpt_stats.get('agent_requested_omitted_refs', 0)} "
        f"prompt_file_refs={source_excerpt_stats.get('prompt_file_refs', 0)}",
        f"subagents: count={subagent_count} linked={linked_subagent_trace_count} visible={visible_subagent_count} collapsed_under_parent=true",
        "child_executions: "
        f"workflows={child_execution_bundle['workflow_count']} "
        f"workers={child_execution_bundle['workflow_worker_count']} "
        f"worker_outlines={child_execution_bundle.get('workflow_worker_outline_count') or 0} "
        f"embedded={child_execution_bundle['embedded_trace_count']} "
        f"aggregate_outputs={child_execution_bundle['aggregate_output_count']} "
        f"aggregate_only={child_execution_bundle['aggregate_only_count']} "
        f"omitted={child_execution_bundle['omitted_count']} "
        f"bytes={child_execution_bundle['bytes']} "
        "size_policy=no_limit_operator_requested",
        f"episode_graph: schema=agent_episode_graph_v1 composition_root=agent_episode_graph nodes={len(agent_episode_graph['nodes'])} episodes={episode_count}",
        "",
        "READER_DECISION_CARD",
        f"reader_scope: status={status_label} copy_scope={display_source_window} recommended_scope={recommended_scope} full_thread_available={'true' if full_thread_available else 'false'} cut_consistency={trace_cut_receipt['cut_consistency']}",
        f"reader_latest: status={reader_latest_state} candidate_count={(latest_selection_receipt.get('candidate_set') or {}).get('turn_count') or 0} selected_is_thread_tail={'true' if latest_selection_receipt.get('selected_is_thread_tail') else 'false'}",
        f"reader_context: status={reader_context_state} global_none_claims_allowed={'true' if scope_semantics['global_none_claims_allowed'] else 'false'}",
        f"reader_trust: copy_readiness={copy_readiness_state} diff_reconciler={diff_reconciler_status} claim_source_map={'complete' if not claim_source_map['uncovered_summary_claims'] else 'incomplete'} assurance_active_defeaters={defeater_register['active_count']} final_delta={'attached' if final_delta_attached else 'not_attached'}",
        f"reader_next_action: {reader_next_action}",
        "",
        "SUMMARY",
        f"status: {status_label}",
        f"result: {result_summary}",
        f"changed: {changed}",
        f"landed_commit_sequence: {_capsule_landed_commit_sequence_summary(landed_commit_sequence)}",
        f"commit_changed_paths: {_capsule_path_list_summary(changed_path_classes['commit_changed_paths'])}",
        f"source_owner_paths_changed: {_capsule_path_list_summary(changed_path_classes['source_owner_paths'])}",
        f"generated_projection_paths: {_capsule_path_list_summary(changed_path_classes['generated_projection_paths'])}",
        f"test_paths_changed: {_capsule_path_list_summary(changed_path_classes['test_paths'])}",
        f"final_validation: {final_validation}",
        f"owner_scope_validation: {owner_scope_validation}",
        f"source_validation: {source_validation}",
        f"trace_contract_validation: {trace_contract_validation}",
        f"publication_candidate_validation: {publication_candidate_validation}",
        f"internal_authorization: {internal_authorization}",
        f"public_release_authorization: {public_release_authorization}",
        f"source_landing: {source_landing_state}",
        f"source_residuals: {source_residuals_summary}",
        f"publication_residuals: {publication_residuals_summary}",
        f"source_landing_residual_domain: {source_landing_residual_domain}",
        f"publication_candidate_execution_state: {publication_candidate_execution_state}",
        f"legacy_publication_state: {legacy_publication_state}",
        f"publication_state: {publication_state}",
        f"publication_blocker: {publication_blocker}",
        f"publication_blocker_class: {publication_blocker_class}",
        f"publication_blocker_class_source: {publication_blocker_class_source}",
        f"git_remote_publication: {git_remote_publication}",
        f"local_landed_commit: {local_landed_commit or 'none'}",
        f"local_source_commit: {local_source_commit}",
        f"local_checkpoint_commit: {local_checkpoint_commit}",
        f"remote_published_commit: {remote_published_commit}",
        f"external_public_release_state: {public_release_state}",
        f"public_release_state: {public_release_state}",
        f"release_gate_kind: {release_gate_kind}",
        f"repo_mutation_authorization: {repo_mutation_authorization}",
        f"git_remote_publication_authorization: {git_remote_publication_authorization}",
        f"external_public_release_authorization: {external_public_release_authorization}",
        (
            "local_branch_topology: "
            f"{local_branch_topology} "
            f"ahead={local_branch_ahead if local_branch_ahead is not None else 'unknown'} "
            f"behind={local_branch_behind if local_branch_behind is not None else 'unknown'} "
            f"worktree_pending_files={worktree_pending_files if worktree_pending_files is not None else 'unknown'}"
        ),
        (
            "worktree_state: "
            f"main_worktree_pending_files={main_worktree_pending_files if main_worktree_pending_files is not None else 'unknown'} "
            f"publication_worktree_pending_files={publication_worktree_pending_files if publication_worktree_pending_files is not None else 'unknown'} "
            f"owned_changed_paths_pending_files={owned_changed_paths_pending_files if owned_changed_paths_pending_files is not None else 'unknown'}"
        ),
        "evidence_scope: summary_drivers=current_receipt_surfaces_only historical_trace_outputs=observations_only",
        (
            "publication_replay_relation: "
            f"relation={(git_publication_trace.get('publication_replay_relation') or {}).get('relation') or 'none'} "
            f"local_source_commit={(git_publication_trace.get('publication_replay_relation') or {}).get('local_source_commit') or 'none'} "
            f"remote_publication_commit={(git_publication_trace.get('publication_replay_relation') or {}).get('remote_publication_commit') or 'none'} "
            f"replay_mode={(git_publication_trace.get('publication_replay_relation') or {}).get('replay_mode') or 'none'} "
            f"selected_path_count={(git_publication_trace.get('publication_replay_relation') or {}).get('selected_path_count') or 0} "
            f"diff_basis={(git_publication_trace.get('publication_replay_relation') or {}).get('diff_basis') or 'none'}"
        ),
        f"retained_publication_worktree: {retained_publication_worktree_summary}",
        f"tests: {tests_state}",
        f"receipt_assimilation: {receipt_assimilation}",
        f"session_closeout_receipt: {_capsule_session_closeout_receipt_summary(session_closeout_receipt)}",
        f"publication_blocker_receipt: {publication_blocker_receipt_id or 'none'}",
        f"publication_blocker_event: {publication_blocker_receipt.get('event') or 'none'}",
        f"receipt_scope: {publication_blocker_receipt.get('receipt_scope') or 'none'}",
        f"receipt_source_command: {publication_blocker_receipt.get('receipt_source_command') or 'none'}",
        f"receipt_subject_id: {publication_blocker_receipt.get('receipt_subject_id') or 'none'}",
        f"receipt_event_id: {publication_blocker_receipt.get('receipt_event_id') or 'none'}",
        f"receipt_event_type: {publication_blocker_receipt.get('receipt_event_type') or 'none'}",
        f"receipt_surface: {publication_blocker_receipt.get('receipt_surface') or 'none'}",
        f"receipt_payload_commit: {publication_blocker_receipt.get('receipt_payload_commit') or 'none'}",
        f"receipt_supersedes_or_replaces: {publication_blocker_receipt.get('receipt_supersedes_or_replaces') or 'none'}",
        (
            "publication_blocker_observed: "
            f"subject={publication_blocker_observed_id or 'none'} "
            f"event={publication_blocker_observed_event or 'none'} "
            f"observation_scope={publication_blocker_observed.get('observation_scope') or 'none'} "
            f"authority_status={publication_blocker_observed.get('authority_status') or 'none'}"
        ),
        f"reentry_condition: {reentry_condition or 'none'}",
        f"publication_reentry_plan: {publication_reentry_plan_summary}",
        f"ambient_validation: {ambient_validation}",
        f"ambient_warning_class: {ambient_warning_class_summary}",
        (
            "continuation_genealogy: "
            f"schema={continuation_genealogy['schema_version']} "
            f"previous_trace_deficits={continuation_genealogy['previous_trace_deficits']} "
            f"new_commit={continuation_genealogy['new_commit']} "
            f"closed_deficits={continuation_genealogy['closed_deficits']} "
            f"remaining_deficits={continuation_genealogy['remaining_deficits']} "
            f"basis={continuation_genealogy['basis']}"
        ),
        *open_product_residual_lines,
        *open_validation_process_residual_lines,
        f"closed_residuals_seen: {closed_residuals_seen_summary}",
        f"blocked_external_observation_residuals: {blocked_external_observation_residuals_summary}",
        f"ambient_validation_warnings: {ambient_validation_warning_summary}",
        f"release_candidate_gate: {release_candidate_gate_decision or 'none'}",
        f"historical_terminal_failures_superseded: {historical_terminal_failures_superseded}",
        f"expected_guard_refusals: {expected_guard_refusal_count}",
        f"guarded_refusal_residuals: {guarded_refusal_residual_summary}",
        f"projection_or_view_artifacts_seen: {projection_or_view_artifacts_seen_summary}",
        f"unresolved_residual_mentions: {unresolved_residual_mentions_summary}",
        f"unresolved_residual_mentions_selected_window: {selected_window_unresolved_residual_mentions_summary}",
        f"passive_residual_mentions_observed: {passive_residual_mentions_observed_summary}",
        f"passive_residual_mentions_scope: {passive_residual_mentions_scope}",
        "release_authority: none",
        (
            "authority_registers: "
            f"repo_mutation_authority={repo_mutation_authority} "
            f"internal_public_safe_import_authority={internal_public_safe_import_authority} "
            f"external_publication_authority={external_publication_authority} "
            f"operator_release_disposition={operator_release_disposition} "
            f"repo_mutation_authorization={repo_mutation_authorization} "
            f"git_remote_publication_authorization={git_remote_publication_authorization} "
            f"external_public_release_authorization={external_public_release_authorization}"
        ),
        f"checks: pass={check_pass_count} fail={check_fail_count} other={check_other_count} total={len(check_rows)}",
        f"terminal_checks: pass={terminal_check_pass_count} fail={terminal_check_fail_count} other={terminal_check_other_count} total={len(terminal_check_rows)}",
        f"owner_scope_terminal_checks: pass={owner_terminal_pass_count} fail={owner_terminal_fail_count} other={owner_terminal_other_count} total={len(owner_terminal_check_rows)}",
        f"source_domain_terminal_checks: pass={source_domain_pass_count} fail={source_domain_fail_count} other={source_domain_other_count} total={len(source_domain_terminal_rows)}",
        f"publication_candidate_terminal_checks: pass={publication_candidate_pass_count} fail={publication_candidate_fail_count} other={publication_candidate_other_count} total={len(publication_candidate_terminal_rows)}",
        f"validation_progress: iterative_checks(pass={check_pass_count} fail={check_fail_count} other={check_other_count} total={len(check_rows)}) terminal_checks(pass={terminal_check_pass_count} fail={terminal_check_fail_count} other={terminal_check_other_count} total={len(terminal_check_rows)}) owner_scope_terminal_checks(pass={owner_terminal_pass_count} fail={owner_terminal_fail_count} other={owner_terminal_other_count} total={len(owner_terminal_check_rows)}) source_domain_terminal_checks(pass={source_domain_pass_count} fail={source_domain_fail_count} other={source_domain_other_count} total={len(source_domain_terminal_rows)}) publication_candidate_terminal_checks(pass={publication_candidate_pass_count} fail={publication_candidate_fail_count} other={publication_candidate_other_count} total={len(publication_candidate_terminal_rows)}) recovered_failures={recovered_failures} final_validation_basis={final_validation_basis}",
        f"terminal_failure_classes: {terminal_failure_class_summary}",
        f"validation_supersession_edges: selector_coverage_recovered_failures={selector_recovered_failure_count} split_selector_recovered_failures={split_selector_recovered_failure_count} aggregate_recovered_failures={stale_window_failure_count} release_gate_superseded_failures={release_gate_superseded_failure_count}",
        f"publication_validation_supersession_edges: read_only_publication_poll_recovered_failures={publication_poll_recovered_failure_count}",
        f"validation_semantics: owner_scope_validation={owner_scope_validation} source_validation={source_validation} trace_contract_validation={trace_contract_validation} publication_candidate_validation={publication_candidate_validation} publication_candidate_execution_state={publication_candidate_execution_state} source_landing={source_landing_state} source_residuals={source_residuals_summary} publication_residuals={publication_residuals_summary} source_landing_residual_domain={source_landing_residual_domain} legacy_publication_state={legacy_publication_state} publication_state={publication_state} publication_blocker={publication_blocker} publication_blocker_class={publication_blocker_class} publication_blocker_class_source={publication_blocker_class_source} git_remote_publication={git_remote_publication} external_public_release_state={public_release_state} public_release_state={public_release_state} release_gate_kind={release_gate_kind} local_branch_topology={local_branch_topology} main_worktree_pending_files={main_worktree_pending_files if main_worktree_pending_files is not None else 'unknown'} publication_worktree_pending_files={publication_worktree_pending_files if publication_worktree_pending_files is not None else 'unknown'} owned_changed_paths_pending_files={owned_changed_paths_pending_files if owned_changed_paths_pending_files is not None else 'unknown'} tests={tests_state} evidence_scope=current_receipt_surfaces_only receipt_assimilation={receipt_assimilation} validation_process={validation_process} ambient_validation={ambient_validation} internal_authorization={internal_authorization} public_release_authorization={public_release_authorization} repo_mutation_authorization={repo_mutation_authorization} git_remote_publication_authorization={git_remote_publication_authorization} external_public_release_authorization={external_public_release_authorization} release_candidate_gate={release_candidate_gate_decision or 'none'} scoped_failures={len(effective_blocking_terminal_failures)} source_current_terminal_failures={source_domain_fail_count} publication_candidate_failures={publication_candidate_fail_count} historical_terminal_failures_superseded={historical_terminal_failures_superseded} current_terminal_failures={current_terminal_failure_count} stale_window_failures={stale_window_failure_count} contradictory_closeouts={contradictory_closeout_count} expected_guard_refusals={expected_guard_refusal_count} guarded_refusal_residuals={guarded_refusal_residual_summary} nonblocking_terminal_failures={len(nonblocking_terminal_failures)} external_terminal_warnings={len(ambient_terminal_warning_rows)} open_product_residuals={open_product_residual_semantics} open_validation_process_residuals={open_validation_process_residual_semantics} blocked_external_observation_residuals={blocked_external_observation_residuals_summary} captured_residuals={captured_residual_summary} classes={validation_class_summary}",
        f"governance_receipts: pass={governance_pass_count} fail={governance_fail_count} other={governance_other_count} total={len(governance_rows)}",
        f"terminal_governance: pass={terminal_governance_pass_count} fail={terminal_governance_fail_count} other={terminal_governance_other_count} total={len(terminal_governance_rows)}",
        f"diagnostics: total={len(diagnostic_rows)} fail={diagnostic_fail_count}",
        f"visible_progress: notes={visible_note_count} source=assistant_visible_only",
        f"thinking: source=app_visible_assistant_messages notes={visible_note_count} phases={reasoning_phase_count} pivots={pivot_count} route_decisions={route_decision_count} decisions={decision_count} validation_intents={validation_intent_count}",
    ])
    header.extend(_capsule_reasoning_digest_lines(reasoning_events))
    header.extend(episode_lines)
    if commit_summary:
        header.append(f"commit: {commit_summary}")
    header.extend(open_claim_lines)
    header.extend(["", *_capsule_trace_cut_receipt_section_lines(trace_cut_receipt)])
    header.extend(["", *_capsule_latest_selection_receipt_section_lines(latest_selection_receipt)])
    header.extend(["", *_capsule_trace_provenance_attestation_section_lines(trace_provenance_attestation)])
    header.extend(["", *_capsule_title_authority_section_lines(title_authority)])
    header.extend(["", *_capsule_claim_source_map_section_lines(claim_source_map)])
    header.extend(["", *_capsule_evidence_node_graph_section_lines(evidence_node_graph)])
    header.extend(["", *_capsule_defeater_register_section_lines(defeater_register)])
    header.extend(["", *_capsule_assurance_case_graph_section_lines(assurance_case_graph)])
    header.extend(["", *_capsule_trace_self_parse_receipt_section_lines(trace_self_parse_receipt)])
    header.extend(["", *_capsule_budget_solver_receipt_section_lines(budget_solver_receipt)])
    header.extend(["", *_capsule_type_b_decision_bundle_section_lines(type_b_decision_bundle, source_context_readiness=source_context_readiness)])
    header.extend(["", *_capsule_source_context_demand_section_lines(source_context_demand)])
    header.extend(["", *_capsule_source_slice_requests_section_lines(source_slice_requests)])
    header.extend(["", *_capsule_source_slice_manifest_section_lines(source_slice_manifest)])
    header.extend(["", *_capsule_source_context_deficit_section_lines(source_context_deficit)])
    header.extend(["", *_capsule_source_context_readiness_section_lines(source_context_readiness)])
    header.extend(["", *_capsule_type_b_source_closeout_lint_section_lines(type_b_source_closeout_lint)])
    header.extend(["", *evidence_manifest_lines])
    header.extend(child_execution_bundle_lines)
    header.extend(subagent_trace_bundle_lines)
    header.extend(["", *_capsule_landed_commit_sequence_section_lines(landed_commit_sequence)])
    header.extend(["", *_capsule_final_delta_section_lines(final_delta)])
    header.extend(["", *_capsule_diff_section_lines(edit_rows)])
    header.extend(["", *command_return_lines])
    header.extend(["", *source_excerpt_lines])
    header.extend(["", *sidecar_manifest_lines])
    header.extend(_capsule_subagent_section_lines(subagent_packet))
    header.extend(["", *_capsule_visible_progress_section_lines(reasoning_events)])
    prompt_body_included = include_prompt_body and bool((turn.prompt_text or "").strip())
    if prompt_body_included:
        header.extend(["", "PROMPT"])
        if intern_repeated_prompts:
            header.extend(_render_prompt_with_interns(turn.prompt_text))
        else:
            header.append(turn.prompt_text)
    header.extend(["", "TIMELINE"])
    lines = header + timeline
    if commit_summary:
        lines.append(f"K001 commit {commit_summary}")
    if closeout_present:
        closeout = _capsule_single_line_excerpt(final_assistant_text, max_chars=TRACE_CAPSULE_CLOSEOUT_CHARS)
        if closeout:
            key_id = "K002" if (commit_hash or commit_title) else "K001"
            lines.append(f"{key_id} closeout {closeout}")
    lines.extend([
        "",
        "OMISSIONS",
        f"raw_sidecar: {'inline_trace_paste' if include_raw_sidecar else 'not_materialized'}",
        f"raw_sidecar_coverage: {'complete' if command_return_stats['lost'] == 0 else 'partial'}",
        f"command_output_loss: outputs_total={command_return_stats['outputs']} accounted={command_return_stats['accounted']} lost_outputs={command_return_stats['lost']}",
        f"source_excerpts: captured={source_excerpt_stats['count']} omitted={source_excerpt_stats['omitted']} source=agent_requested_or_prompt_file_refs_or_trace_read_outputs policy=bounded_redacted_line_ranges carrier=saved_latest_response_bundle practical_budget=~150KB reference_modes=message_text|full_small_bodies|path_line_shards|standard_projections",
        f"truncated_outputs: {truncated_outputs}",
        "not_included: server_hidden_reasoning, omitted_provider_bytes_without_sidecar",
        "included: app_visible_thinking_progress",
        f"source_window: {display_source_window}",
        f"thread_totality: {_trace_thread_totality(display_source_window)}",
        f"no_edit_claim_allowed: {'true' if no_edit_claim_allowed else 'false'}",
        f"substrate_diff: {substrate_diff_state}",
        f"final_delta_attached: {'true' if final_delta_attached else 'false'}",
        f"edit_event_log_attached: {'true' if edit_event_log_attached else 'false'}",
        f"embedded_subagent_traces: rendered={subagent_trace_bundle['rendered_count']} omitted={subagent_trace_bundle['omitted_count']} bytes={subagent_trace_bundle['bytes']} size_policy=no_limit_operator_requested",
        f"child_executions: workflows={child_execution_bundle['workflow_count']} workers={child_execution_bundle['workflow_worker_count']} worker_outlines={child_execution_bundle.get('workflow_worker_outline_count') or 0} embedded={child_execution_bundle['embedded_trace_count']} aggregate_outputs={child_execution_bundle['aggregate_output_count']} aggregate_only={child_execution_bundle['aggregate_only_count']} omitted={child_execution_bundle['omitted_count']} bytes={child_execution_bundle['bytes']} size_policy=no_limit_operator_requested",
    ])
    if not prompt_body_included:
        lines.append("prompt_body: omitted_by_request")
    prompt_intern_summary = _prompt_intern_summary_line(turn.prompt_text) if intern_repeated_prompts else None
    if prompt_intern_summary:
        lines.append(prompt_intern_summary.replace("# ", ""))
    raw_sidecar_bytes = len(raw_sidecar_text.encode("utf-8")) if include_raw_sidecar else 0

    def materialize_with_scope(current_base_lines: list[str]) -> tuple[list[str], dict[str, Any], str]:
        current_integrity = _capsule_scope_integrity(
            turn=turn,
            display_source_window=display_source_window,
            source_sha16=source_sha16,
            source_watermark=source_watermark,
            include_raw_sidecar=include_raw_sidecar,
            raw_sidecar_bytes=raw_sidecar_bytes,
            trace_capsule_bytes=0,
        )
        for _ in range(4):
            draft_lines = current_base_lines + ["", *_capsule_scope_integrity_section_lines(current_integrity)]
            draft_text = "\n".join(draft_lines).rstrip() + "\n"
            next_integrity = _capsule_scope_integrity(
                turn=turn,
                display_source_window=display_source_window,
                source_sha16=source_sha16,
                source_watermark=source_watermark,
                include_raw_sidecar=include_raw_sidecar,
                raw_sidecar_bytes=raw_sidecar_bytes,
                trace_capsule_bytes=len(draft_text.encode("utf-8")),
            )
            if (
                next_integrity.get("projection", {}).get("bytes")
                == current_integrity.get("projection", {}).get("bytes")
            ):
                break
            current_integrity = next_integrity
        current_lines = current_base_lines + ["", *_capsule_scope_integrity_section_lines(current_integrity)]
        current_text = "\n".join(current_lines).rstrip() + "\n"
        for _ in range(8):
            actual_rendered_bytes = len(current_text.encode("utf-8"))
            if actual_rendered_bytes == current_integrity.get("projection", {}).get("bytes"):
                break
            current_integrity = _capsule_scope_integrity(
                turn=turn,
                display_source_window=display_source_window,
                source_sha16=source_sha16,
                source_watermark=source_watermark,
                include_raw_sidecar=include_raw_sidecar,
                raw_sidecar_bytes=raw_sidecar_bytes,
                trace_capsule_bytes=actual_rendered_bytes,
            )
            current_lines = current_base_lines + ["", *_capsule_scope_integrity_section_lines(current_integrity)]
            current_text = "\n".join(current_lines).rstrip() + "\n"
        return current_lines, current_integrity, current_text

    base_lines = list(lines)
    lines, scope_integrity, rendered_text = materialize_with_scope(base_lines)
    inline_parse_receipt = _trace_capsule_downstream_parser_roundtrip_text(rendered_text)
    _capsule_apply_downstream_parse_receipt(trace_self_parse_receipt, inline_parse_receipt)
    refresh_trace_contract_state()
    defeater_register = _capsule_defeater_register(
        scope_semantics=scope_semantics,
        latest_selection_receipt=latest_selection_receipt,
        title_authority=title_authority,
        trace_self_parse_receipt=trace_self_parse_receipt,
        budget_solver_receipt=budget_solver_receipt,
    )
    assurance_case_graph = _capsule_assurance_case_graph(
        latest_selection_receipt=latest_selection_receipt,
        title_authority=title_authority,
        trace_self_parse_receipt=trace_self_parse_receipt,
        budget_solver_receipt=budget_solver_receipt,
        defeater_register=defeater_register,
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "reader_trust:",
        (
            f"reader_trust: copy_readiness={copy_readiness_state} "
            f"diff_reconciler={diff_reconciler_status} "
            f"claim_source_map={'complete' if not claim_source_map['uncovered_summary_claims'] else 'incomplete'} "
            f"assurance_active_defeaters={defeater_register['active_count']} "
            f"final_delta={'attached' if final_delta_attached else 'not_attached'}"
        ),
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "reader_next_action:",
        f"reader_next_action: {reader_next_action}",
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "copy_readiness:",
        f"copy_readiness: state={copy_readiness_state} blockers={','.join(copy_readiness_blockers) or 'none'} warnings={','.join(copy_readiness_warnings) or 'none'}",
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "final_validation:",
        f"final_validation: {final_validation}",
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "trace_contract_validation:",
        f"trace_contract_validation: {trace_contract_validation}",
    )
    base_lines = _capsule_replace_section(
        base_lines,
        "CLAIM_SOURCE_MAP",
        _capsule_claim_source_map_section_lines(claim_source_map),
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "copy_readiness_vector:",
        _capsule_copy_readiness_vector_line(copy_readiness_vector),
    )
    base_lines = _capsule_replace_prefixed_line(
        base_lines,
        "session_closeout_receipt:",
        f"session_closeout_receipt: {_capsule_session_closeout_receipt_summary(session_closeout_receipt)}",
    )
    base_lines = _capsule_replace_section(
        base_lines,
        "DEFEATER_REGISTER",
        _capsule_defeater_register_section_lines(defeater_register),
    )
    base_lines = _capsule_replace_section(
        base_lines,
        "ASSURANCE_CASE_GRAPH",
        _capsule_assurance_case_graph_section_lines(assurance_case_graph),
    )
    base_lines = _capsule_replace_section(
        base_lines,
        "TRACE_SELF_PARSE_RECEIPT",
        _capsule_trace_self_parse_receipt_section_lines(trace_self_parse_receipt),
    )
    lines, scope_integrity, rendered_text = materialize_with_scope(base_lines)
    final_parse_receipt = _trace_capsule_downstream_parser_roundtrip_text(
        rendered_text,
        artifact_name="trace_capsule_final_self_parse.txt",
    )
    if final_parse_receipt.get("status") != inline_parse_receipt.get("status"):
        _capsule_apply_downstream_parse_receipt(trace_self_parse_receipt, final_parse_receipt)
        refresh_trace_contract_state()
        defeater_register = _capsule_defeater_register(
            scope_semantics=scope_semantics,
            latest_selection_receipt=latest_selection_receipt,
            title_authority=title_authority,
            trace_self_parse_receipt=trace_self_parse_receipt,
            budget_solver_receipt=budget_solver_receipt,
        )
        assurance_case_graph = _capsule_assurance_case_graph(
            latest_selection_receipt=latest_selection_receipt,
            title_authority=title_authority,
            trace_self_parse_receipt=trace_self_parse_receipt,
            budget_solver_receipt=budget_solver_receipt,
            defeater_register=defeater_register,
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "reader_trust:",
            (
                f"reader_trust: copy_readiness={copy_readiness_state} "
                f"diff_reconciler={diff_reconciler_status} "
                f"claim_source_map={'complete' if not claim_source_map['uncovered_summary_claims'] else 'incomplete'} "
                f"assurance_active_defeaters={defeater_register['active_count']} "
                f"final_delta={'attached' if final_delta_attached else 'not_attached'}"
            ),
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "reader_next_action:",
            f"reader_next_action: {reader_next_action}",
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "copy_readiness:",
            f"copy_readiness: state={copy_readiness_state} blockers={','.join(copy_readiness_blockers) or 'none'} warnings={','.join(copy_readiness_warnings) or 'none'}",
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "final_validation:",
            f"final_validation: {final_validation}",
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "trace_contract_validation:",
            f"trace_contract_validation: {trace_contract_validation}",
        )
        base_lines = _capsule_replace_section(
            base_lines,
            "CLAIM_SOURCE_MAP",
            _capsule_claim_source_map_section_lines(claim_source_map),
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "copy_readiness_vector:",
            _capsule_copy_readiness_vector_line(copy_readiness_vector),
        )
        base_lines = _capsule_replace_prefixed_line(
            base_lines,
            "session_closeout_receipt:",
            f"session_closeout_receipt: {_capsule_session_closeout_receipt_summary(session_closeout_receipt)}",
        )
        base_lines = _capsule_replace_section(
            base_lines,
            "DEFEATER_REGISTER",
            _capsule_defeater_register_section_lines(defeater_register),
        )
        base_lines = _capsule_replace_section(
            base_lines,
            "ASSURANCE_CASE_GRAPH",
            _capsule_assurance_case_graph_section_lines(assurance_case_graph),
        )
        base_lines = _capsule_replace_section(
            base_lines,
            "TRACE_SELF_PARSE_RECEIPT",
            _capsule_trace_self_parse_receipt_section_lines(trace_self_parse_receipt),
        )
        lines, scope_integrity, rendered_text = materialize_with_scope(base_lines)
    meta = {
        "source_sha16": source_sha16,
        "status": status_label,
        "raw_status": status_text,
        "scope_semantics": scope_semantics,
        "scope_integrity": scope_integrity,
        "trace_context_ids": trace_context_ids,
        "trace_cut_receipt": trace_cut_receipt,
        "latest_selection_receipt": latest_selection_receipt,
        "trace_provenance_attestation": trace_provenance_attestation,
        "title_authority": title_authority,
        "claim_source_map": claim_source_map,
        "evidence_node_graph": evidence_node_graph,
        "defeater_register": defeater_register,
        "assurance_case_graph": assurance_case_graph,
        "copy_readiness_vector": copy_readiness_vector,
        "trace_self_parse_receipt": trace_self_parse_receipt,
        "budget_solver_receipt": budget_solver_receipt,
        "title_authority_warning": title_authority_warning,
        "command_count": len(renderable),
        "commands_with_outputs": commands_with_outputs,
        "edit_count": len(edit_rows),
        "validation_count": len(check_rows),
        "check_count": len(check_rows),
        "check_fail_count": check_fail_count,
        "terminal_validation_count": len(terminal_check_rows),
        "terminal_validation_pass_count": terminal_check_pass_count,
        "terminal_validation_fail_count": terminal_check_fail_count,
        "governance_receipt_count": len(governance_rows),
        "governance_receipt_fail_count": governance_fail_count,
        "terminal_governance_receipt_count": len(terminal_governance_rows),
        "diagnostic_count": len(diagnostic_rows),
        "diagnostic_fail_count": diagnostic_fail_count,
        "visible_progress_note_count": visible_note_count,
        "reasoning_phase_count": reasoning_phase_count,
        "reasoning_pivot_count": pivot_count,
        "reasoning_route_decision_count": route_decision_count,
        "reasoning_decision_count": decision_count,
        "reasoning_validation_intent_count": validation_intent_count,
        "episode_count": episode_count,
        "recovered_check_failures": recovered_failures,
        "final_validation_basis": final_validation_basis,
        "final_validation": final_validation,
        "owner_scope_validation": owner_scope_validation,
        "source_validation": source_validation,
        "trace_contract_validation": trace_contract_validation,
        "publication_candidate_validation": publication_candidate_validation,
        "internal_authorization": internal_authorization,
        "public_release_authorization": public_release_authorization,
        "source_landing": source_landing_state,
        "source_residuals": source_residual_ids,
        "publication_residuals": publication_residual_ids,
        "source_landing_residual_domain": source_landing_residual_domain,
        "legacy_publication_state": legacy_publication_state,
        "publication_state": publication_state,
        "publication_candidate_execution_state": publication_candidate_execution_state,
        "publication_blocker": publication_blocker,
        "publication_blocker_class": publication_blocker_class,
        "publication_blocker_class_source": publication_blocker_class_source,
        "git_remote_publication": git_remote_publication,
        "local_landed_commit": local_landed_commit or "none",
        "local_source_commit": local_source_commit,
        "local_checkpoint_commit": local_checkpoint_commit,
        "remote_published_commit": remote_published_commit,
        "public_release_state": public_release_state,
        "external_public_release_state": public_release_state,
        "release_gate_kind": release_gate_kind,
        "repo_mutation_authorization": repo_mutation_authorization,
        "git_remote_publication_authorization": git_remote_publication_authorization,
        "external_public_release_authorization": external_public_release_authorization,
        "local_branch_topology": local_branch_topology,
        "local_branch_ahead": local_branch_ahead,
        "local_branch_behind": local_branch_behind,
        "main_worktree_pending_files": main_worktree_pending_files,
        "publication_worktree_pending_files": publication_worktree_pending_files,
        "owned_changed_paths_pending_files": owned_changed_paths_pending_files,
        "worktree_pending_files": worktree_pending_files,
        "tests_state": tests_state,
        "evidence_scope": "current_receipt_surfaces_only",
        "evidence_scope_rows": git_publication_trace.get("evidence_scope_rows") or [],
        "publication_replay_relation": git_publication_trace.get("publication_replay_relation"),
        "publication_reentry_plan": publication_reentry_plan or (
            "absent_current_plan" if publication_reentry_plan_absent_current else None
        ),
        "publication_reentry_plan_status": (
            "absent_current_plan"
            if publication_reentry_plan_absent_current
            else (str(publication_reentry_plan.get("status") or "none") if publication_reentry_plan else "none")
        ),
        "retained_publication_worktree": {
            "path": publication_worktree_dir,
            "state": publication_worktree_state,
            "unmerged_paths": retained_conflict_paths,
            "selected_path_count": git_publication_trace.get("selected_path_count") or 0,
            "source_owner_overlap_blocks_auto_snapshot": git_publication_trace.get("source_owner_overlap_blocks_auto_snapshot"),
            "safe_path_snapshot": git_publication_trace.get("safe_path_snapshot"),
            "selected_vs_remote_overlap_paths": git_publication_trace.get("selected_vs_remote_overlap_paths") or [],
        },
        "nested_observed_validation": git_publication_trace.get("nested_observed_validation") or "none",
        "git_publication_trace": git_publication_trace,
        "receipt_assimilation": receipt_assimilation,
        "work_landing_receipt": work_landing_receipt,
        "session_closeout_receipt": session_closeout_receipt,
        "publication_blocker_receipt": publication_blocker_receipt_id or "none",
        "publication_blocker_event": publication_blocker_receipt.get("event") or "none",
        "publication_blocker_observed": dict(publication_blocker_observed or {}),
        "receipt_scope": publication_blocker_receipt.get("receipt_scope") or "none",
        "receipt_source_command": publication_blocker_receipt.get("receipt_source_command") or "none",
        "receipt_subject_id": publication_blocker_receipt.get("receipt_subject_id") or "none",
        "receipt_event_id": publication_blocker_receipt.get("receipt_event_id") or "none",
        "receipt_event_type": publication_blocker_receipt.get("receipt_event_type") or "none",
        "receipt_surface": publication_blocker_receipt.get("receipt_surface") or "none",
        "receipt_payload_commit": publication_blocker_receipt.get("receipt_payload_commit") or "none",
        "receipt_supersedes_or_replaces": publication_blocker_receipt.get("receipt_supersedes_or_replaces") or "none",
        "reentry_condition": reentry_condition or "none",
        "ambient_validation": ambient_validation,
        "ambient_warning_classes": ambient_warning_classes,
        "ambient_validation_warnings": ambient_warning_classes,
        "continuation_genealogy": continuation_genealogy,
        "validation_process": validation_process,
        "release_candidate_gate_decision": release_candidate_gate_decision,
        "historical_terminal_failures_superseded": historical_terminal_failures_superseded,
        "selector_coverage_recovered_failure_count": selector_recovered_failure_count,
        "split_selector_recovered_failure_count": split_selector_recovered_failure_count,
        "publication_poll_recovered_failure_count": publication_poll_recovered_failure_count,
        "release_gate_superseded_failure_count": release_gate_superseded_failure_count,
        "validation_supersession_edges": {
            "selector_coverage_recovered_failures": selector_recovered_failure_count,
            "split_selector_recovered_failures": split_selector_recovered_failure_count,
            "aggregate_recovered_failures": stale_window_failure_count,
            "release_gate_superseded_failures": release_gate_superseded_failure_count,
            "read_only_publication_poll_recovered_failures": publication_poll_recovered_failure_count,
        },
        "expected_guard_refusal_count": expected_guard_refusal_count,
        "guarded_refusal_residuals": guarded_refusal_residuals,
        "external_terminal_warning_count": len(ambient_terminal_warning_rows),
        "validation_process_terminal_warning_count": len(validation_process_terminal_rows),
        "owner_scope_terminal_validation_count": len(owner_terminal_check_rows),
        "owner_scope_terminal_validation_pass_count": owner_terminal_pass_count,
        "owner_scope_terminal_validation_fail_count": owner_terminal_fail_count,
        "source_domain_terminal_validation_count": len(source_domain_terminal_rows),
        "source_domain_terminal_validation_pass_count": source_domain_pass_count,
        "source_domain_terminal_validation_fail_count": source_domain_fail_count,
        "publication_candidate_terminal_validation_count": len(publication_candidate_terminal_rows),
        "publication_candidate_pass_count": publication_candidate_pass_count,
        "publication_candidate_failure_count": publication_candidate_fail_count,
        "open_product_residuals": open_product_residuals,
        "open_validation_process_residuals": open_validation_process_residuals,
        "closed_residuals_seen": closed_residuals_seen,
        "blocked_external_observation_residuals": blocked_external_observation_residuals,
        "projection_or_view_artifacts_seen": projection_or_view_artifacts_seen,
        "unresolved_residual_mentions": unresolved_residual_mentions,
        "unresolved_residual_mentions_selected_window": selected_window_unresolved_residual_mentions,
        "passive_residual_mentions_observed": passive_residual_mentions_observed,
        "passive_residual_mentions_scope": passive_residual_mentions_scope,
        "release_authority": "none",
        "authority_registers": authority_registers,
        "validation_class_counts": validation_class_counts,
        "validation_domain_counts": validation_domain_counts,
        "validation_workspace_role_counts": workspace_role_counts,
        "captured_residual_ids": captured_residual_ids,
        "blocking_terminal_failure_count": len(effective_blocking_terminal_failures),
        "raw_blocking_terminal_failure_count": len(blocking_terminal_failures),
        "current_terminal_failure_count": current_terminal_failure_count,
        "stale_window_failure_count": stale_window_failure_count,
        "not_validated_failure_count": not_validated_count,
        "contradictory_closeout_count": contradictory_closeout_count,
        "terminal_failure_classes": {
            "current_terminal_failure": current_terminal_failure_count,
            "publication_candidate_failure": publication_candidate_fail_count,
            "recovered_failure": recovered_failures,
            "stale_window_failure": stale_window_failure_count,
            "not_validated": not_validated_count,
            "contradictory_closeout": contradictory_closeout_count,
            "expected_guard_refusal": expected_guard_refusal_count,
        },
        "nonblocking_terminal_failure_count": len(nonblocking_terminal_failures),
        "commit_count": commit_count,
        "landed_commit_sequence": landed_commit_sequence,
        "landed_commit_sequence_count": len(landed_commit_sequence),
        "landed_commit_validation_refs": landed_commit_validation_refs,
        "changed_path_classes": changed_path_classes,
        "changed_paths": changed_paths,
        "commit_changed_paths": changed_path_classes["commit_changed_paths"],
        "source_owner_paths_changed": changed_path_classes["source_owner_paths"],
        "generated_projection_paths": changed_path_classes["generated_projection_paths"],
        "test_paths_changed": changed_path_classes["test_paths"],
        "closeout_present": closeout_present,
        "copy_readiness": {
            "schema_version": "agent_trace_copy_readiness_gate_v1",
            "state": copy_readiness_state,
            "blockers": copy_readiness_blockers,
            "warnings": copy_readiness_warnings,
            "normal_copy_allowed": copy_readiness_state != "red",
            "type_b_no_edits_claim_allowed": no_edit_claim_allowed,
            "required_type_b_no_edit_language": type_b_no_edit_language,
        },
        "diff_reconciler": {
            "schema_version": "agent_trace_diff_reconciler_v1",
            "status": diff_reconciler_status,
            "severity": diff_reconciler_severity,
            "reasons": diff_reconciler_reasons,
            "exact_diff_required": exact_diff_required,
            "ui_review_card": {"state": "ui_diff_only" if ui_diff_only else "not_detected"},
            "final_delta": {
                "state": final_delta.get("state") or "not_captured",
                "attached": final_delta_attached,
                "source": final_delta.get("source") or "none",
                "authority": final_delta.get("authority") or "edit_event_log_only",
                "commit": final_delta.get("commit") or "",
                "path_count": len(final_delta.get("paths") or []),
                "line_count": int(final_delta.get("line_count") or 0),
                "omitted_lines": int(final_delta.get("omitted_lines") or 0),
                "reason": final_delta.get("reason") or "",
            },
            "parser_artifact_delta": {
                "state": substrate_diff_state,
                "edit_path_count": len(edit_event_paths),
                "commit_path_count": len(changed_path_classes["commit_changed_paths"]),
                "attempt_log_only": bool(edit_rows) and not final_delta_attached,
                "patch_attempts_are_not_final_state": True,
            },
            "edit_event_log": {
                "state": "attached" if edit_event_log_attached else "not_attached",
                "row_count": len(edit_rows),
                "patch_attempts_are_not_final_state": True,
            },
            "git_commit_or_worktree": {
                "state": (
                    "commit_without_patch"
                    if commit_diff_missing
                    else (
                        "commit_seen"
                        if commit_summary
                        else ("worktree_delta_seen" if final_delta.get("source") == "git_diff_worktree" else "not_detected")
                    )
                ),
                "commit_diff_missing": commit_diff_missing,
            },
            "edit_claim": {
                "edits": len(edit_rows),
                "edits_zero_scope": _trace_thread_totality(display_source_window) if not edit_rows else "",
                "unqualified_no_edits_allowed": no_edit_claim_allowed,
                "type_b_phrase": type_b_no_edit_language,
            },
        },
        "agent_episode_graph": agent_episode_graph,
        "goal_rollup": goal_rollup,
        "evidence_tier": evidence_tier,
        "type_b_handoff_lint": {
            "schema_version": "agent_trace_type_b_handoff_lint_v1",
            "result": type_b_lint_result,
            "blockers": copy_readiness_blockers,
            "warnings": copy_readiness_warnings,
            "no_edits_sentence_allowed": no_edit_claim_allowed,
            "required_no_edit_language": type_b_no_edit_language,
            "refusal_rule": "refuse unqualified no-edit claims unless full-thread coverage and no-edit evidence prove it",
            "evidence_manifest": evidence_manifest,
            "source_excerpt_affordance": type_b_source_excerpt_affordance,
            "source_excerpt_survival": {
                "schema_version": "agent_trace_requested_source_survival_v1",
                "status": source_excerpt_stats.get("requested_excerpt_survival_status", "unknown"),
                "agent_requested_seen_count": source_excerpt_stats.get("agent_requested_seen_refs", 0),
                "agent_requested_emitted_count": source_excerpt_stats.get(
                    "agent_requested_emitted_refs",
                    source_excerpt_stats.get("agent_requested_refs", 0),
                ),
                "agent_requested_omitted_count": source_excerpt_stats.get("agent_requested_omitted_refs", 0),
                "agent_requested_path_count": source_excerpt_stats.get("agent_requested_path_count", 0),
                "emitted_rows": source_excerpt_stats.get("agent_requested_rows", []),
                "emitted_paths": source_excerpt_stats.get("agent_requested_path_rows", []),
                "drop_reasons": source_excerpt_stats.get("agent_requested_drop_reasons", []),
                "warnings": source_excerpt_lint_warnings,
                "contradictory_closeout_requested_source_missing": requested_source_claim_missing,
            },
        },
        "source_context_demand": source_context_demand,
        "source_slice_requests": source_slice_requests,
        "source_slice_manifest": source_slice_manifest,
        "source_context_deficit": source_context_deficit,
        "source_context_readiness": source_context_readiness,
        "type_b_decision_bundle": type_b_decision_bundle,
        "type_b_source_closeout_lint": type_b_source_closeout_lint,
        "terminal_validation": {
            "schema_version": "agent_trace_terminal_validation_v1",
            "state": terminal_validation_state,
            "terminal_validation_count": len(terminal_check_rows),
            "terminal_pass_count": terminal_check_pass_count,
            "terminal_fail_count": terminal_check_fail_count,
        },
        "display_source_window": display_source_window,
        "copy_scope": display_source_window,
        "thread_totality": _trace_thread_totality(display_source_window),
        "full_thread_available": full_thread_available,
        "selected_window_only": selected_window_only,
        "copy_scope_warning": copy_scope_warning,
        "recommended_scope": recommended_scope,
        "operator_intervention_selected_window_count": 0,
        "operator_intervention_full_thread_count": operator_intervention_full_count,
        "artifact_stats_source": {
            "label": stats_source_label,
            "capsule_turn_index": turn.turn_index,
            "source_window": display_source_window,
            "prompt_sha16": turn.prompt_sha256_16,
            "source_sha16": source_sha16,
        },
        "thread_total_edits": thread_total_edits,
        "no_edit_claim_allowed": no_edit_claim_allowed,
        "substrate_diff": substrate_diff_state,
        "diff_state": substrate_diff_state,
        "substrate_diff_required": substrate_diff_required,
        "commit_diff_missing": commit_diff_missing,
        "final_delta": final_delta,
        "final_delta_attached": final_delta_attached,
        "edit_event_log": {
            "schema_version": "agent_trace_edit_event_log_v1",
            "state": "attached" if edit_event_log_attached else "not_attached",
            "row_count": len(edit_rows),
            "patch_attempts_are_not_final_state": True,
        },
        "edit_event_log_attached": edit_event_log_attached,
        "truncated_outputs": truncated_outputs,
        "command_return_count": command_return_stats["outputs"],
        "command_return_inline_count": command_return_stats["inline"],
        "command_return_sidecar_count": command_return_stats["sidecar"],
        "command_return_redacted_count": command_return_stats["redacted"],
        "command_return_no_output_count": command_return_stats["no_output"],
        "command_return_lost_count": command_return_stats["lost"],
        "source_excerpt_count": source_excerpt_stats["count"],
        "source_excerpt_line_count": source_excerpt_stats["lines"],
        "source_excerpt_paths": source_excerpt_stats["paths"],
        "source_excerpt_omitted_count": source_excerpt_stats["omitted"],
        "source_excerpt_agent_requested_count": source_excerpt_stats.get("agent_requested_refs", 0),
        "source_excerpt_agent_requested_seen_count": source_excerpt_stats.get("agent_requested_seen_refs", 0),
        "source_excerpt_agent_requested_emitted_count": source_excerpt_stats.get(
            "agent_requested_emitted_refs",
            source_excerpt_stats.get("agent_requested_refs", 0),
        ),
        "source_excerpt_agent_requested_omitted_count": source_excerpt_stats.get("agent_requested_omitted_refs", 0),
        "source_excerpt_agent_requested_path_count": source_excerpt_stats.get("agent_requested_path_count", 0),
        "source_excerpt_agent_requested_paths": source_excerpt_stats.get("agent_requested_path_rows", []),
        "source_excerpt_agent_requested_rows": source_excerpt_stats.get("agent_requested_rows", []),
        "source_excerpt_agent_requested_drop_reasons": source_excerpt_stats.get("agent_requested_drop_reasons", []),
        "source_excerpt_omission_reasons": source_excerpt_stats.get("omission_reasons", {}),
        "requested_excerpt_survival_status": source_excerpt_stats.get("requested_excerpt_survival_status", "unknown"),
        "contradictory_closeout_requested_source_missing": requested_source_claim_missing,
        "source_excerpt_lint_warnings": source_excerpt_lint_warnings,
        "evidence_manifest": evidence_manifest,
        "source_excerpt_prompt_file_ref_count": source_excerpt_stats.get("prompt_file_refs", 0),
        "type_b_source_excerpt_affordance": type_b_source_excerpt_affordance,
        "raw_sidecar_text": raw_sidecar_text,
        "raw_sidecar_materialized": include_raw_sidecar,
        "prompt_body_included": prompt_body_included,
        "subagent_count": subagent_count,
        "linked_subagent_trace_count": linked_subagent_trace_count,
        "visible_subagent_count": visible_subagent_count,
        "subagent_deployments": subagent_packet.get("deployments") or [],
        "embedded_subagent_trace_count": subagent_trace_bundle.get("rendered_count", 0),
        "embedded_subagent_trace_omitted_count": subagent_trace_bundle.get("omitted_count", 0),
        "embedded_subagent_trace_bytes": subagent_trace_bundle.get("bytes", 0),
        "embedded_subagent_trace_bundle": subagent_trace_bundle,
        "child_execution_count": child_execution_bundle.get("workflow_count", 0)
        + int(child_execution_bundle.get("native_subagent_count") or 0),
        "workflow_execution_count": child_execution_bundle.get("workflow_count", 0),
        "workflow_worker_count": child_execution_bundle.get("workflow_worker_count", 0),
        "workflow_worker_outline_count": child_execution_bundle.get("workflow_worker_outline_count", 0),
        "embedded_child_trace_count": child_execution_bundle.get("embedded_trace_count", 0),
        "embedded_workflow_trace_count": child_execution_bundle.get("embedded_workflow_trace_count", 0),
        "child_execution_omitted_count": child_execution_bundle.get("omitted_count", 0),
        "child_execution_bytes": child_execution_bundle.get("bytes", 0),
        "workflow_aggregate_output_count": child_execution_bundle.get("aggregate_output_count", 0),
        "workflow_aggregate_only_count": child_execution_bundle.get("aggregate_only_count", 0),
        "child_execution_bundle": child_execution_bundle,
    }
    if prompt_intern_summary:
        meta["prompt_interning"] = _prompt_intern_manifest(turn.prompt_text)
    return (rendered_text, meta)


def _trace_capsule_downstream_parser_roundtrip(path: Path) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": "agent_trace_downstream_parser_roundtrip_v1",
        "parser": str(STRUCTURER_PARSER_PATH),
        "artifact_path": str(path),
        "status": "not_run",
        "required_missing": [],
    }
    if not STRUCTURER_PARSER_PATH.is_file():
        receipt["status"] = "unavailable"
        receipt["error"] = "parser_not_found"
        return receipt
    node_resolution = _trace_structurer_node_resolution()
    receipt["node_resolution"] = node_resolution
    node_executable = str(node_resolution.get("executable") or "")
    if not node_executable:
        receipt["status"] = "unavailable"
        receipt["error"] = "node_not_found"
        return receipt
    script = f"""
import fs from 'node:fs';
const {{ parseAgentTrace }} = await import({json.dumps(STRUCTURER_PARSER_PATH.as_uri())});
const text = fs.readFileSync({json.dumps(str(path))}, 'utf8');
const packet = parseAgentTrace(text, {json.dumps(path.name)}, new Date().toISOString());
const receipts = packet.handoff_view?.assurance_receipts || {{}};
const required = [
  'TRACE_CUT_RECEIPT',
  'LATEST_SELECTION_RECEIPT',
  'TRACE_PROVENANCE_ATTESTATION',
  'TITLE_AUTHORITY',
  'CLAIM_SOURCE_MAP',
  'EVIDENCE_NODE_GRAPH',
  'DEFEATER_REGISTER',
  'ASSURANCE_CASE_GRAPH',
  'TRACE_SELF_PARSE_RECEIPT',
  'BUDGET_SOLVER_PROOF_SET',
  'TYPE_B_DECISION_BUNDLE',
  'SOURCE_CONTEXT_DEMAND',
  'SOURCE_SLICE_REQUESTS',
  'SOURCE_SLICE_MANIFEST',
  'SOURCE_CONTEXT_DEFICIT',
  'SOURCE_CONTEXT_READINESS',
  'TYPE_B_SOURCE_CLOSEOUT_LINT'
];
const present = new Set(receipts.sections_present || []);
const missing = required.filter((name) => !present.has(name));
console.log(JSON.stringify({{
  schema_version: 'agent_trace_downstream_parser_roundtrip_v1',
  status: missing.length ? 'fail' : 'pass',
  required_missing: missing,
  parser_schema: receipts.schema_version || '',
  latest_selection_status: receipts.latest_selection?.selected_is_latest_completed_response ?? null,
  assurance_claim_count: receipts.assurance_case?.claim_count ?? 0,
  defeater_active_count: receipts.defeater_register?.active_count ?? 0
}}));
"""
    try:
        proc = subprocess.run(
            [node_executable, "--input-type=module", "-e", script],
            text=True,
            capture_output=True,
            timeout=8,
            env=_trace_structurer_node_env(),
        )
    except FileNotFoundError:
        receipt["status"] = "unavailable"
        receipt["error"] = "node_not_found"
        return receipt
    except Exception as exc:
        receipt["status"] = "error"
        receipt["error"] = type(exc).__name__
        return receipt
    if proc.returncode != 0:
        receipt["status"] = "fail"
        receipt["stderr"] = (proc.stderr or "").strip()[:1000]
        return receipt
    try:
        parsed = json.loads(proc.stdout.strip() or "{}")
    except Exception:
        receipt["status"] = "fail"
        receipt["stdout"] = (proc.stdout or "").strip()[:1000]
        return receipt
    receipt.update(parsed)
    return receipt


def _trace_capsule_downstream_parser_roundtrip_text(
    text: str,
    *,
    artifact_name: str = "trace_capsule_inline_self_parse.txt",
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=f"-{_fs_safe_token(artifact_name)}",
        delete=False,
    ) as handle:
        handle.write(text)
        path = Path(handle.name)
    try:
        return _trace_capsule_downstream_parser_roundtrip(path)
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def write_trace_capsule_artifact(
    turn: Turn,
    *,
    source_window: str = "latest_prompt_cycle",
    intern_repeated_prompts: bool = False,
    include_prompt_body: bool = True,
) -> dict:
    title, title_source = _resolve_session_title(
        turn.provider, turn.session_id, Path(turn.session_file),
        codex_thread_names=_load_codex_thread_names(),
        title_aliases=_load_title_aliases(),
        claude_desktop_titles=_load_claude_desktop_titles(),
    )
    if not title:
        title = _prompt_title_from_text(turn.prompt_text)
        title_source = "current_turn_prompt_title" if title else "current_turn_prompt_preview"
    if not title:
        first_line = next((line.strip() for line in (turn.prompt_text or "").splitlines() if line.strip()), "")
        title = first_line[:120] or f"{turn.provider} turn {turn.turn_index}"

    text, meta = render_trace_capsule_text(
        turn,
        title=title,
        source_window=source_window,
        intern_repeated_prompts=intern_repeated_prompts,
        include_prompt_body=include_prompt_body,
    )
    data = text.encode("utf-8")
    sha16 = hashlib.sha256(data).hexdigest()[:16]
    if isinstance(meta.get("trace_provenance_attestation"), dict):
        subject = meta["trace_provenance_attestation"].setdefault("subject", {})
        if isinstance(subject, dict):
            subject["sha16"] = sha16
            subject["bytes"] = len(data)
    prompt_tag = (turn.prompt_sha256_16 or "noprompt")[:8]
    session_tag = _short_session_tag(turn.session_id)
    out_name = _fs_safe_token(f"{turn.provider}-{session_tag}-{prompt_tag}-trace_capsule-{sha16}.txt")
    out_path = TRACE_STRUCTURER_VARIANT_ARTIFACTS / out_name
    raw_name = _fs_safe_token(f"{turn.provider}-{session_tag}-{prompt_tag}-trace_capsule-{meta['source_sha16']}.raw.txt")
    raw_path = TRACE_STRUCTURER_RAW / raw_name
    TRACE_STRUCTURER_VARIANT_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    TRACE_STRUCTURER_RAW.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    raw_path.write_text(str(meta.get("raw_sidecar_text") or ""), encoding="utf-8")
    if isinstance(meta.get("scope_integrity"), dict):
        raw_receipt = meta["scope_integrity"].setdefault("raw_sidecar", {})
        if isinstance(raw_receipt, dict):
            raw_receipt["path"] = str(raw_path)
            raw_receipt["filename"] = raw_path.name
            raw_receipt["bytes"] = raw_path.stat().st_size if raw_path.exists() else int(raw_receipt.get("bytes") or 0)
    downstream_parse_receipt = _trace_capsule_downstream_parser_roundtrip(out_path)
    if isinstance(meta.get("trace_self_parse_receipt"), dict):
        _capsule_apply_downstream_parse_receipt(meta["trace_self_parse_receipt"], downstream_parse_receipt)

    identity_key = f"session={turn.session_id}|window={source_window}|prompt={turn.prompt_sha256_16}|turn={turn.turn_index}|variant=trace_capsule"
    source_watermark = _source_watermark_for_turn(turn)
    artifact = {
        "schema": "agent_trace_variant_materialization_receipt_v0",
        "artifact_kind": "agent_trace",
        "artifact_role": "trace_capsule",
        "variant": "trace_capsule",
        "density_tier": 1,
        "contract_state": "defined",
        "materialization_state": "ready_for_handoff",
        "replay_state": "blocked_without_lossless_sources",
        "promotion_gate": "handoff_ready_not_replay_ready",
        "schema_version": TRACE_CAPSULE_SCHEMA_VERSION,
        "slice_label": TRACE_CAPSULE_SCHEMA_VERSION,
        "provider": turn.provider,
        "session_id": turn.session_id,
        "title": title,
        "display_title": (meta.get("title_authority") or {}).get("display_title") or title,
        "title_authority": meta.get("title_authority"),
        "path": str(out_path),
        "artifact_path": str(out_path),
        "bytes": len(data),
        "sha16": sha16,
        "size_contract": {"bytes": len(data), "status": "not_applicable", "variant": "trace_capsule"},
        "trace_counts": {
            "schema": "agent_trace_variant_content_counts_v1",
            "variant": "trace_capsule",
            "schema_version": TRACE_CAPSULE_SCHEMA_VERSION,
            "command_count": meta["command_count"],
            "edit_path_count": meta["edit_count"],
            "validation_count": meta["validation_count"],
            "final_validation": meta["final_validation"],
            "owner_scope_validation": meta["owner_scope_validation"],
            "source_validation": meta["source_validation"],
            "source_landing": meta["source_landing"],
            "source_residuals": meta["source_residuals"],
            "publication_residuals": meta["publication_residuals"],
            "source_landing_residual_domain": meta["source_landing_residual_domain"],
            "publication_candidate_validation": meta["publication_candidate_validation"],
            "publication_candidate_execution_state": meta["publication_candidate_execution_state"],
            "source_domain_terminal_validation_count": meta["source_domain_terminal_validation_count"],
            "source_domain_terminal_validation_fail_count": meta["source_domain_terminal_validation_fail_count"],
            "publication_candidate_terminal_validation_count": meta["publication_candidate_terminal_validation_count"],
            "publication_candidate_failure_count": meta["publication_candidate_failure_count"],
            "publication_blocker": meta["publication_blocker"],
            "publication_blocker_class": meta["publication_blocker_class"],
            "publication_blocker_receipt": meta["publication_blocker_receipt"],
            "publication_blocker_event": meta["publication_blocker_event"],
            "public_release_state": meta["public_release_state"],
            "external_public_release_state": meta["external_public_release_state"],
            "receipt_scope": meta["receipt_scope"],
            "receipt_source_command": meta["receipt_source_command"],
            "receipt_subject_id": meta["receipt_subject_id"],
            "receipt_event_id": meta["receipt_event_id"],
            "receipt_event_type": meta["receipt_event_type"],
            "receipt_surface": meta["receipt_surface"],
            "receipt_payload_commit": meta["receipt_payload_commit"],
            "receipt_supersedes_or_replaces": meta["receipt_supersedes_or_replaces"],
            "reentry_condition": meta["reentry_condition"],
            "publication_reentry_plan": meta["publication_reentry_plan"],
            "closeout_present": meta["closeout_present"],
            "copy_scope": meta["copy_scope"],
            "thread_totality": meta["thread_totality"],
            "scope_integrity": meta["scope_integrity"],
            "full_thread_available": meta["full_thread_available"],
            "selected_window_only": meta["selected_window_only"],
            "copy_scope_warning": meta["copy_scope_warning"],
            "recommended_scope": meta["recommended_scope"],
            "thread_total_edits": meta["thread_total_edits"],
            "no_edit_claim_allowed": meta["no_edit_claim_allowed"],
            "substrate_diff": meta["substrate_diff"],
            "diff_state": meta["diff_state"],
            "substrate_diff_required": meta["substrate_diff_required"],
            "commit_diff_missing": meta["commit_diff_missing"],
            "final_delta": meta["final_delta"],
            "final_delta_attached": meta["final_delta_attached"],
            "edit_event_log": meta["edit_event_log"],
            "edit_event_log_attached": meta["edit_event_log_attached"],
            "copy_readiness": meta["copy_readiness"],
            "copy_readiness_state": meta["copy_readiness"]["state"],
            "copy_readiness_vector": meta["copy_readiness_vector"],
            "diff_reconciler": meta["diff_reconciler"],
            "diff_reconciler_status": meta["diff_reconciler"]["status"],
            "scope_semantics": meta["scope_semantics"],
            "trace_context_ids": meta["trace_context_ids"],
            "trace_cut_receipt": meta["trace_cut_receipt"],
            "latest_selection_receipt": meta["latest_selection_receipt"],
            "trace_provenance_attestation": meta["trace_provenance_attestation"],
            "title_authority": meta["title_authority"],
            "claim_source_map": meta["claim_source_map"],
            "evidence_node_graph": meta["evidence_node_graph"],
            "defeater_register": meta["defeater_register"],
            "assurance_case_graph": meta["assurance_case_graph"],
            "trace_self_parse_receipt": meta["trace_self_parse_receipt"],
            "downstream_parse_receipt": downstream_parse_receipt,
            "budget_solver_receipt": meta["budget_solver_receipt"],
            "source_context_demand": meta["source_context_demand"],
            "source_slice_requests": meta["source_slice_requests"],
            "source_slice_manifest": meta["source_slice_manifest"],
            "source_context_deficit": meta["source_context_deficit"],
            "source_context_readiness": meta["source_context_readiness"],
            "type_b_decision_bundle": meta["type_b_decision_bundle"],
            "type_b_source_closeout_lint": meta["type_b_source_closeout_lint"],
            "agent_episode_graph": meta["agent_episode_graph"],
            "goal_rollup": meta["goal_rollup"],
            "evidence_tier": meta["evidence_tier"],
            "type_b_handoff_lint": meta["type_b_handoff_lint"],
            "terminal_validation": meta["terminal_validation"],
            "authority_registers": meta["authority_registers"],
            "validation_domain_counts": meta["validation_domain_counts"],
            "validation_workspace_role_counts": meta["validation_workspace_role_counts"],
            "unresolved_residual_mentions_selected_window": meta["unresolved_residual_mentions_selected_window"],
            "passive_residual_mentions_observed": meta["passive_residual_mentions_observed"],
            "passive_residual_mentions_scope": meta["passive_residual_mentions_scope"],
            "retained_publication_worktree": meta["retained_publication_worktree"],
            "subagent_count": meta["subagent_count"],
            "linked_subagent_trace_count": meta["linked_subagent_trace_count"],
            "visible_subagent_count": meta["visible_subagent_count"],
            "embedded_subagent_trace_count": meta["embedded_subagent_trace_count"],
            "embedded_subagent_trace_omitted_count": meta["embedded_subagent_trace_omitted_count"],
            "embedded_subagent_trace_bytes": meta["embedded_subagent_trace_bytes"],
            "embedded_subagent_trace_bundle": meta["embedded_subagent_trace_bundle"],
            "child_execution_count": meta["child_execution_count"],
            "workflow_execution_count": meta["workflow_execution_count"],
            "workflow_worker_count": meta["workflow_worker_count"],
            "workflow_worker_outline_count": meta["workflow_worker_outline_count"],
            "embedded_child_trace_count": meta["embedded_child_trace_count"],
            "embedded_workflow_trace_count": meta["embedded_workflow_trace_count"],
            "child_execution_omitted_count": meta["child_execution_omitted_count"],
            "child_execution_bytes": meta["child_execution_bytes"],
            "workflow_aggregate_output_count": meta["workflow_aggregate_output_count"],
            "workflow_aggregate_only_count": meta["workflow_aggregate_only_count"],
            "child_execution_bundle": meta["child_execution_bundle"],
            "operator_intervention_count": meta["operator_intervention_selected_window_count"],
            "operator_intervention_selected_window_count": meta["operator_intervention_selected_window_count"],
            "operator_intervention_full_thread_count": meta["operator_intervention_full_thread_count"],
            "artifact_stats_source": meta["artifact_stats_source"],
        },
        "source_clip_path": str(raw_path),
        "clip_path": str(raw_path),
        "scope_integrity": meta["scope_integrity"],
        "source_window": source_window,
        "source_sha16": meta["source_sha16"],
        "source_watermark": source_watermark,
        "copied_source_watermark": source_watermark,
        "identity_key": identity_key,
        "prompt_sha16": turn.prompt_sha256_16,
        "turn_index": turn.turn_index,
        "freshness": "captured_now",
        "standalone": True,
        "capabilities": {"standalone_for": ["read_trace", "continue_work", "debug_changes", "inspect_commands_outputs_edits_tests"]},
        "not_standalone_for": ["replay", "byte_reconstruction", "raw_source_reconstruction"],
        "requires_for": {"replay": ["provider_session_jsonl_source_v1"]},
        "omitted": {"event_stream": True, "large_bodies": True},
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_anchor": {
            "session_id": turn.session_id,
            "prompt_sha16": turn.prompt_sha256_16,
            "turn_index": turn.turn_index,
            "source_window": source_window,
            "source_sha16": meta["source_sha16"],
            "source_clip_path": str(raw_path),
            "source_watermark_id": source_watermark.get("watermark_id") or "",
        },
    }
    trace_window = (turn.source_ref or {}).get("trace_window") or (turn.source_ref or {}).get("prompt_cycle")
    if isinstance(trace_window, dict):
        artifact["trace_window"] = trace_window
        artifact["window_anchor"]["trace_window"] = trace_window
    if "prompt_interning" in meta:
        artifact["prompt_interning"] = {
            key: value
            for key, value in meta["prompt_interning"].items()
            if key != "pool"
        }
    _write_variant_index_entry(turn.session_id, "trace_capsule", artifact)
    return {
        "ok": True,
        "kind": "cli_prompt_trace.trace_capsule_artifact_written",
        "provider": turn.provider,
        "session_id": turn.session_id,
        "turn_id": turn.turn_id,
        "turn_index": turn.turn_index,
        "title": title,
        "title_source": title_source,
        "prompt_sha16": turn.prompt_sha256_16,
        "prompt_char_count": turn.prompt_char_count,
        "trace_window": trace_window if isinstance(trace_window, dict) else None,
        "source_window": source_window,
        "source_sha16": meta["source_sha16"],
        "source_watermark": source_watermark,
        "copied_source_watermark": source_watermark,
        "scope_integrity": meta["scope_integrity"],
        "source_clip_path": str(raw_path),
        "clip_path": str(raw_path),
        "artifact_path": str(out_path),
        "copied_bytes": len(data),
        "bytes": {"artifact": len(data), "raw": raw_path.stat().st_size if raw_path.exists() else 0},
        "subagent_count": meta["subagent_count"],
        "embedded_subagent_trace_count": meta["embedded_subagent_trace_count"],
        "embedded_subagent_trace_omitted_count": meta["embedded_subagent_trace_omitted_count"],
        "embedded_subagent_trace_bytes": meta["embedded_subagent_trace_bytes"],
        "child_execution_count": meta["child_execution_count"],
        "workflow_execution_count": meta["workflow_execution_count"],
        "workflow_worker_count": meta["workflow_worker_count"],
        "embedded_child_trace_count": meta["embedded_child_trace_count"],
        "embedded_workflow_trace_count": meta["embedded_workflow_trace_count"],
        "child_execution_omitted_count": meta["child_execution_omitted_count"],
        "child_execution_bytes": meta["child_execution_bytes"],
        "workflow_aggregate_output_count": meta["workflow_aggregate_output_count"],
        "workflow_aggregate_only_count": meta["workflow_aggregate_only_count"],
        "variant": "trace_capsule",
        "slice_label": TRACE_CAPSULE_SCHEMA_VERSION,
        "variant_artifact": artifact,
        "content_summary": {
            "command_count": meta["command_count"],
            "output_count": meta["commands_with_outputs"],
            "edit_path_count": meta["edit_count"],
            "validation_count": meta["validation_count"],
            "final_validation": meta["final_validation"],
            "owner_scope_validation": meta["owner_scope_validation"],
            "source_validation": meta["source_validation"],
            "publication_candidate_validation": meta["publication_candidate_validation"],
            "publication_blocker": meta["publication_blocker"],
            "publication_blocker_class": meta["publication_blocker_class"],
            "publication_blocker_receipt": meta["publication_blocker_receipt"],
            "publication_blocker_event": meta["publication_blocker_event"],
            "reentry_condition": meta["reentry_condition"],
            "closeout_present": meta["closeout_present"],
            "copy_scope": meta["copy_scope"],
            "thread_totality": meta["thread_totality"],
            "scope_integrity": meta["scope_integrity"],
            "thread_total_edits": meta["thread_total_edits"],
            "substrate_diff": meta["substrate_diff"],
            "diff_state": meta["diff_state"],
            "commit_diff_missing": meta["commit_diff_missing"],
            "final_delta": meta["final_delta"],
            "final_delta_attached": meta["final_delta_attached"],
            "edit_event_log": meta["edit_event_log"],
            "edit_event_log_attached": meta["edit_event_log_attached"],
            "copy_readiness": meta["copy_readiness"],
            "copy_readiness_state": meta["copy_readiness"]["state"],
            "copy_readiness_vector": meta["copy_readiness_vector"],
            "diff_reconciler": meta["diff_reconciler"],
            "diff_reconciler_status": meta["diff_reconciler"]["status"],
            "scope_semantics": meta["scope_semantics"],
            "trace_context_ids": meta["trace_context_ids"],
            "trace_cut_receipt": meta["trace_cut_receipt"],
            "trace_provenance_attestation": meta["trace_provenance_attestation"],
            "claim_source_map": meta["claim_source_map"],
            "trace_self_parse_receipt": meta["trace_self_parse_receipt"],
            "budget_solver_receipt": meta["budget_solver_receipt"],
            "source_context_demand": meta["source_context_demand"],
            "source_slice_requests": meta["source_slice_requests"],
            "source_slice_manifest": meta["source_slice_manifest"],
            "source_context_deficit": meta["source_context_deficit"],
            "source_context_readiness": meta["source_context_readiness"],
            "type_b_decision_bundle": meta["type_b_decision_bundle"],
            "type_b_source_closeout_lint": meta["type_b_source_closeout_lint"],
            "agent_episode_graph": meta["agent_episode_graph"],
            "goal_rollup": meta["goal_rollup"],
            "evidence_tier": meta["evidence_tier"],
            "type_b_handoff_lint": meta["type_b_handoff_lint"],
            "terminal_validation": meta["terminal_validation"],
            "authority_registers": meta["authority_registers"],
            "validation_domain_counts": meta["validation_domain_counts"],
            "retained_publication_worktree": meta["retained_publication_worktree"],
            "child_execution_count": meta["child_execution_count"],
            "workflow_execution_count": meta["workflow_execution_count"],
            "workflow_worker_count": meta["workflow_worker_count"],
            "workflow_worker_outline_count": meta["workflow_worker_outline_count"],
            "embedded_child_trace_count": meta["embedded_child_trace_count"],
            "embedded_workflow_trace_count": meta["embedded_workflow_trace_count"],
            "child_execution_omitted_count": meta["child_execution_omitted_count"],
            "child_execution_bytes": meta["child_execution_bytes"],
            "workflow_aggregate_output_count": meta["workflow_aggregate_output_count"],
            "workflow_aggregate_only_count": meta["workflow_aggregate_only_count"],
            "child_execution_bundle": meta["child_execution_bundle"],
            "copy_scope_warning": meta["copy_scope_warning"],
            "recommended_scope": meta["recommended_scope"],
            "operator_intervention_count": meta["operator_intervention_selected_window_count"],
            "operator_intervention_full_thread_count": meta["operator_intervention_full_thread_count"],
            "artifact_stats_source": meta["artifact_stats_source"],
            "truncated_output_count": meta["truncated_outputs"],
            "prompt_sha16": turn.prompt_sha256_16,
            "turn_index": turn.turn_index,
            "prompt_interning": artifact.get("prompt_interning"),
        },
    }


def write_closeout_report_artifact(
    turn: Turn,
    *,
    source_window: str = "latest_prompt_cycle",
    intern_repeated_prompts: bool = False,
    command_limit: int = TRACE_CLOSEOUT_COMMAND_LIMIT,
) -> dict:
    title, title_source = _resolve_session_title(
        turn.provider, turn.session_id, Path(turn.session_file),
        codex_thread_names=_load_codex_thread_names(),
        title_aliases=_load_title_aliases(),
        claude_desktop_titles=_load_claude_desktop_titles(),
    )
    if not title:
        title = _prompt_title_from_text(turn.prompt_text)
        title_source = "current_turn_prompt_title" if title else "current_turn_prompt_preview"
    if not title:
        first_line = next((line.strip() for line in (turn.prompt_text or "").splitlines() if line.strip()), "")
        title = first_line[:120] or f"{turn.provider} turn {turn.turn_index}"

    text = render_thread_closeout_report(
        turn,
        title=title,
        intern_repeated_prompts=intern_repeated_prompts,
        command_limit=command_limit,
    )
    raw_sidecar_text = render_trace_paste(
        turn,
        include_prompt=False,
        intern_repeated_prompts=intern_repeated_prompts,
    )
    meta = _closeout_report_meta(
        turn,
        command_limit=command_limit,
        source_sha16=_sha16(raw_sidecar_text),
    )
    data = text.encode("utf-8")
    sha16 = hashlib.sha256(data).hexdigest()[:16]
    prompt_tag = (turn.prompt_sha256_16 or "noprompt")[:8]
    session_tag = _short_session_tag(turn.session_id)
    out_name = _fs_safe_token(f"{turn.provider}-{session_tag}-{prompt_tag}-closeout_report-{sha16}.md")
    out_path = TRACE_STRUCTURER_VARIANT_ARTIFACTS / out_name
    raw_name = _fs_safe_token(f"{turn.provider}-{session_tag}-{prompt_tag}-closeout_report-{meta['source_sha16']}.raw.txt")
    raw_path = TRACE_STRUCTURER_RAW / raw_name
    TRACE_STRUCTURER_VARIANT_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    TRACE_STRUCTURER_RAW.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    raw_path.write_text(raw_sidecar_text, encoding="utf-8")

    identity_key = f"session={turn.session_id}|window={source_window}|prompt={turn.prompt_sha256_16}|turn={turn.turn_index}|variant=closeout_report"
    artifact = {
        "schema": "agent_trace_variant_materialization_receipt_v0",
        "artifact_kind": "agent_trace",
        "artifact_role": "closeout_report",
        "variant": "closeout_report",
        "density_tier": 0,
        "contract_state": "defined",
        "materialization_state": "ready_for_handoff",
        "replay_state": "blocked_without_lossless_sources",
        "promotion_gate": "closeout_handoff_ready_not_replay_ready",
        "schema_version": TRACE_CLOSEOUT_REPORT_SCHEMA_VERSION,
        "slice_label": TRACE_CLOSEOUT_REPORT_SCHEMA_VERSION,
        "provider": turn.provider,
        "session_id": turn.session_id,
        "title": title,
        "path": str(out_path),
        "artifact_path": str(out_path),
        "bytes": len(data),
        "sha16": sha16,
        "size_contract": {"bytes": len(data), "status": "not_applicable", "variant": "closeout_report"},
        "trace_counts": {
            "schema": "agent_trace_variant_content_counts_v1",
            "variant": "closeout_report",
            "schema_version": TRACE_CLOSEOUT_REPORT_SCHEMA_VERSION,
            "command_count": meta["tool_event_count"],
            "edit_path_count": meta["changed_file_count"],
            "validation_count": 0,
            "closeout_present": meta["closeout_count"] > 0,
            "closeout_count": meta["closeout_count"],
            "top_command_limit": command_limit,
        },
        "closeout_report_meta": {
            key: value
            for key, value in meta.items()
            if key not in {"changed_files", "command_summary_rows"}
        },
        "source_clip_path": str(raw_path),
        "clip_path": str(raw_path),
        "source_window": source_window,
        "source_sha16": meta["source_sha16"],
        "identity_key": identity_key,
        "prompt_sha16": turn.prompt_sha256_16,
        "turn_index": turn.turn_index,
        "freshness": "captured_now",
        "standalone": True,
        "capabilities": {
            "standalone_for": [
                "read_final_closeout",
                "inspect_changed_files",
                "inspect_top_commands_without_tool_bodies",
                "choose_raw_trace_drilldown",
            ]
        },
        "not_standalone_for": ["replay", "byte_reconstruction", "raw_tool_output_inspection"],
        "requires_for": {"tool_body_replay": ["provider_session_jsonl_source_v1", "trace_capsule_or_lossless_clip"]},
        "omitted": {"event_stream": True, "tool_bodies": True, "raw_prompts": True},
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_anchor": {
            "session_id": turn.session_id,
            "prompt_sha16": turn.prompt_sha256_16,
            "turn_index": turn.turn_index,
            "source_window": source_window,
            "source_sha16": meta["source_sha16"],
            "source_clip_path": str(raw_path),
        },
    }
    trace_window = (turn.source_ref or {}).get("trace_window") or (turn.source_ref or {}).get("prompt_cycle")
    if isinstance(trace_window, dict):
        artifact["trace_window"] = trace_window
        artifact["window_anchor"]["trace_window"] = trace_window
    if intern_repeated_prompts:
        artifact["prompt_interning"] = {
            key: value
            for key, value in _prompt_intern_manifest(turn.prompt_text).items()
            if key != "pool"
        }
    _write_variant_index_entry(turn.session_id, "closeout_report", artifact)
    return {
        "ok": True,
        "kind": "cli_prompt_trace.closeout_report_artifact_written",
        "provider": turn.provider,
        "session_id": turn.session_id,
        "turn_id": turn.turn_id,
        "turn_index": turn.turn_index,
        "title": title,
        "title_source": title_source,
        "prompt_sha16": turn.prompt_sha256_16,
        "prompt_char_count": turn.prompt_char_count,
        "trace_window": trace_window if isinstance(trace_window, dict) else None,
        "source_window": source_window,
        "source_sha16": meta["source_sha16"],
        "source_clip_path": str(raw_path),
        "clip_path": str(raw_path),
        "artifact_path": str(out_path),
        "copied_bytes": len(data),
        "bytes": {"artifact": len(data), "raw": raw_path.stat().st_size if raw_path.exists() else 0},
        "variant": "closeout_report",
        "slice_label": TRACE_CLOSEOUT_REPORT_SCHEMA_VERSION,
        "variant_artifact": artifact,
        "content_summary": {
            "command_count": meta["tool_event_count"],
            "top_command_limit": command_limit,
            "edit_path_count": meta["changed_file_count"],
            "closeout_count": meta["closeout_count"],
            "closeout_present": meta["closeout_count"] > 0,
            "prompt_sha16": turn.prompt_sha256_16,
            "turn_index": turn.turn_index,
            "prompt_interning": artifact.get("prompt_interning"),
        },
    }


def _variant_estimate_row(
    *,
    variant: str,
    source_window: str,
    text: str,
    exact: bool = True,
    source: str = "renderer_no_write",
) -> dict[str, Any]:
    data = text.encode("utf-8")
    return {
        "variant": variant,
        "source_window": source_window,
        "bytes": len(data),
        "sha16": hashlib.sha256(data).hexdigest()[:16],
        "exact": exact,
        "source": source,
    }


def _trace_variant_size_estimates(
    turn: Turn,
    *,
    cycle_turn: Turn,
    full_turn: Turn,
    title: str,
    include_prompt_body: bool = True,
    materialize_trace_sidecar_for_exact_size: bool = False,
) -> dict[str, Any]:
    """Return UI byte estimates using the same renderers as copy/save."""
    estimates: dict[str, Any] = {
        "schema": "agent_trace_variant_size_estimates_v1",
        "status": "renderer_exact_no_write" if materialize_trace_sidecar_for_exact_size else "renderer_estimate_no_write",
        "trace_capsule": {},
        "closeout_report": {},
    }
    generated_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def add(
        variant: str,
        source_window: str,
        text: str,
        *,
        exact: bool = True,
        source: str = "renderer_no_write",
    ) -> None:
        estimates.setdefault(variant, {})[source_window] = _variant_estimate_row(
            variant=variant,
            source_window=source_window,
            text=text,
            exact=exact,
            source=source,
        )

    for source_window, source_turn in (
        ("selected_turn", turn),
        ("latest_prompt_cycle", cycle_turn),
        ("full_thread", full_turn),
    ):
        try:
            text, _meta = render_trace_capsule_text(
                source_turn,
                title=title,
                source_window=source_window,
                intern_repeated_prompts=True,
                include_raw_sidecar=materialize_trace_sidecar_for_exact_size,
                include_prompt_body=include_prompt_body,
            )
            add(
                "trace_capsule",
                source_window,
                text,
                exact=materialize_trace_sidecar_for_exact_size,
                source="renderer_no_write_current" if materialize_trace_sidecar_for_exact_size else "renderer_no_write_estimate",
            )
        except Exception as exc:
            estimates["trace_capsule"][source_window] = {
                "variant": "trace_capsule",
                "source_window": source_window,
                "bytes": 0,
                "exact": False,
                "source": "renderer_no_write",
                "error": str(exc)[:160],
            }
        try:
            text = render_thread_closeout_report(
                source_turn,
                title=title,
                intern_repeated_prompts=True,
                command_limit=TRACE_CLOSEOUT_COMMAND_LIMIT,
                generated_at=generated_at,
            )
            add("closeout_report", source_window, text)
        except Exception as exc:
            estimates["closeout_report"][source_window] = {
                "variant": "closeout_report",
                "source_window": source_window,
                "bytes": 0,
                "exact": False,
                "source": "renderer_no_write",
                "error": str(exc)[:160],
            }
    return estimates


def measure_trace_variant_sizes(
    turn: Turn,
    *,
    turns: list[Turn],
    title: str,
    selected_source_window: str = "latest_prompt_cycle",
    variant: str = "all",
    include_prompt_body: bool = True,
) -> dict[str, Any]:
    cycle_turn = merge_prompt_cycle(
        prompt_cycle_turns(
            turns,
            turn,
            threshold_words=SHORT_PROMPT_CHAIN_WORD_THRESHOLD,
        ),
        threshold_words=SHORT_PROMPT_CHAIN_WORD_THRESHOLD,
    )
    full_turn = merge_full_thread(full_thread_turns(turns, turn))
    estimates = _trace_variant_size_estimates(
        turn,
        cycle_turn=cycle_turn,
        full_turn=full_turn,
        title=title,
        include_prompt_body=include_prompt_body,
        materialize_trace_sidecar_for_exact_size=True,
    )
    if variant != "all":
        estimates = {
            "schema": estimates["schema"],
            "status": estimates["status"],
            variant: estimates.get(variant, {}),
        }
    selected_window = selected_source_window
    if selected_source_window == "full_thread_concise":
        selected_window = "full_thread"
    selected_variant = "closeout_report" if selected_source_window == "full_thread_concise" else (
        "trace_capsule" if variant == "all" else variant
    )
    selected = (estimates.get(selected_variant) or {}).get(selected_window) or {}
    return {
        "ok": True,
        "schema": "agent_trace_variant_size_measurement_v1",
        "status": "measured_current_no_write",
        "provider": turn.provider,
        "session_id": turn.session_id,
        "title": title,
        "turn_index": turn.turn_index,
        "turn_id": turn.turn_id,
        "prompt_sha16": turn.prompt_sha256_16,
        "source_window": selected_window,
        "requested_source_window": selected_source_window,
        "variant": selected_variant,
        "bytes": selected.get("bytes"),
        "sha16": selected.get("sha16"),
        "exact": True,
        "source": "renderer_no_write_current",
        "trace_window": (turn.source_ref or {}).get("trace_window") or {},
        "measurements": estimates,
    }


def render_json(
    turn: Turn,
    *,
    tier: str,
    selection_reason: str | None = None,
    selection_ambiguous_peers: int = 0,
) -> str:
    """Render JSON envelope at the requested output tier.

    tier:
      - "manifest" (default): no raw outputs; output_text replaced with null; chars+sha16 retained.
      - "preview": redacted 240-char prefix with secret-pattern scrubbing applied.
      - "raw": full raw outputs verbatim (explicit local-private opt-in).
    """
    if tier not in ("manifest", "preview", "raw"):
        raise SystemExit(f"unknown json tier {tier!r}")
    d = asdict(turn)
    d["schema"] = SCHEMA_VERSION
    d["trace_id"] = turn.turn_id
    sid = turn.session_id or ""
    d["source_stream_id"] = f"{turn.provider}:{sid}" if sid else turn.provider
    d["source_ref_policy"] = "transcript_tail"
    d["raw_output_included"] = (tier == "raw")
    d["output_tier"] = tier
    d["local_private"] = True
    if selection_reason:
        d["selection_reason"] = selection_reason
    d["selection_ambiguous_peer_count"] = selection_ambiguous_peers
    redaction_hits_total = 0
    for ev in d.get("tool_events", []):
        full = ev.get("output_text", "")
        if tier == "manifest":
            ev["output_text"] = None
        elif tier == "preview":
            preview = full[:JSON_REDACTED_OUTPUT_PREVIEW_CHARS]
            redacted, hits = _redact_secrets(preview)
            redaction_hits_total += len(hits)
            ev["output_text"] = (
                redacted
                + (f"... [truncated; sha16={_sha16(full)}, chars={len(full)}]"
                   if len(full) > JSON_REDACTED_OUTPUT_PREVIEW_CHARS else "")
            )
            if hits:
                ev["redaction_hits"] = hits
        # raw tier leaves output_text unchanged
    d["redaction_hits_total"] = redaction_hits_total
    return json.dumps(d, indent=2, ensure_ascii=False)


def list_turns(turns: list[Turn]) -> str:
    lines = [f"{len(turns)} turn(s):"]
    for t in turns:
        first_line = ""
        for raw in (t.prompt_text or "").splitlines():
            stripped = raw.strip()
            if stripped:
                first_line = stripped
                break
        preview = first_line[:90]
        status = "complete" if t.is_complete else "partial "
        n_err = sum(1 for e in t.tool_events if e.is_error)
        err = f"  err={n_err}" if n_err else ""
        lines.append(
            f"  {t.turn_index:>3}. [{t.started_at or '?':<28}] {status}  tools={len(t.tool_events):>2}{err}  {preview}"
        )
    return "\n".join(lines)


def _load_claude_desktop_titles() -> dict[str, dict]:
    """Map ~/.claude/projects/<slug>/<cli_uuid>.jsonl -> Claude desktop metadata.

    Returns {cli_session_id: {title, title_source, is_archived, last_activity_at,
    completed_turns, cwd, desktop_session_id}}.

    Source: Claude desktop persists operator-edited session titles in
    `~/Library/Application Support/Claude/claude-code-sessions/<ws>/<win>/local_<uuid>.json`.
    The `cliSessionId` field on each record points at the CLI JSONL.
    """
    out: dict[str, dict] = {}
    if not CLAUDE_DESKTOP_SESSIONS.is_dir():
        return out
    try:
        for path in CLAUDE_DESKTOP_SESSIONS.rglob("local_*.json"):
            try:
                d = json.loads(path.read_text())
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            cli_id = d.get("cliSessionId")
            if not cli_id:
                continue
            out[str(cli_id)] = {
                "title": d.get("title") or "",
                "title_source": d.get("titleSource") or "",
                "is_archived": bool(d.get("isArchived")),
                "last_activity_at": d.get("lastActivityAt") or "",
                "completed_turns": d.get("completedTurns") or 0,
                "cwd": d.get("cwd") or "",
                "desktop_session_id": d.get("sessionId") or "",
                "model": d.get("model") or "",
                "metadata_path": str(path),
            }
    except Exception:
        pass
    return out


def _load_codex_thread_title_records() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not CODEX_SESSION_INDEX.is_file():
        return out
    try:
        with CODEX_SESSION_INDEX.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                sid = rec.get("id")
                tn = rec.get("thread_name")
                if sid and tn:
                    out[str(sid)] = {
                        "thread_name": str(tn),
                        "updated_at": rec.get("updated_at") or "",
                    }
    except Exception:
        pass
    return out


def _load_codex_thread_names() -> dict[str, str]:
    return {
        sid: str(rec.get("thread_name") or "")
        for sid, rec in _load_codex_thread_title_records().items()
        if rec.get("thread_name")
    }


def _iso_from_epoch_ms(value: int | float | None) -> str:
    if value is None:
        return ""
    try:
        return _dt.datetime.fromtimestamp(float(value) / 1000, _dt.timezone.utc).isoformat()
    except Exception:
        return ""


def _objective_preview(value: str, *, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _load_codex_thread_goals(db_path: Path | None = None) -> dict[str, dict]:
    """Read Codex app goal state keyed by thread/session id.

    The Structurer mission index is already local-private. Still, keep the row
    bounded: objective text is represented as a preview plus hash so the
    mission rail can show goal-bearing threads without becoming another raw
    goal transcript store.
    """
    db_path = db_path or CODEX_GOALS_DB
    if not db_path.is_file():
        return {}
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            select thread_id, goal_id, objective, status, token_budget,
                   tokens_used, time_used_seconds, created_at_ms, updated_at_ms
            from thread_goals
            """
        ).fetchall()
    except Exception:
        return {}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    out: dict[str, dict] = {}
    for row in rows:
        try:
            objective = str(row["objective"] or "")
            thread_id = str(row["thread_id"] or "")
            if not thread_id:
                continue
            out[thread_id] = {
                "schema": "codex_thread_goal_v1",
                "thread_id": thread_id,
                "goal_id": str(row["goal_id"] or ""),
                "status": str(row["status"] or ""),
                "objective_preview": _objective_preview(objective),
                "objective_sha16": _sha16(objective) if objective else "",
                "token_budget": row["token_budget"],
                "tokens_used": int(row["tokens_used"] or 0),
                "time_used_seconds": int(row["time_used_seconds"] or 0),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
                "created_at": _iso_from_epoch_ms(row["created_at_ms"]),
                "updated_at": _iso_from_epoch_ms(row["updated_at_ms"]),
            }
        except Exception:
            continue
    return out


def _goal_sort_priority(goal: dict | None) -> int:
    if not isinstance(goal, dict):
        return 0
    return {
        "active": 40,
        "usage_limited": 30,
        "budget_limited": 30,
        "paused": 20,
        "blocked": 10,
        "complete": 0,
    }.get(str(goal.get("status") or "").lower(), 0)


_GOAL_AUTHORITY_CONTENT_SIGNATURE_VERSION = "codex_thread_goal_roster_v1"
_GOAL_AUTHORITY_CONTENT_SIGNATURE_FIELDS = (
    "thread_id",
    "goal_id",
    "status",
    "objective_sha16",
    "token_budget",
    "created_at_ms",
)


def _goal_authority_content_sha16(goals: dict[str, dict]) -> str:
    rows: list[dict[str, Any]] = []
    for thread_id in sorted(goals):
        goal = goals.get(thread_id) if isinstance(goals.get(thread_id), dict) else {}
        rows.append({
            field: (thread_id if field == "thread_id" else goal.get(field))
            for field in _GOAL_AUTHORITY_CONTENT_SIGNATURE_FIELDS
        })
    return _sha16(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


def _sqlite_authority_paths(path: Path) -> list[Path]:
    return [path, Path(f"{path}-wal"), Path(f"{path}-shm")]


def _goal_authority_sources(goals: dict[str, dict]) -> dict:
    source_paths = [
        {"path": str(path), "mtime_ms": mtime_ms}
        for path in _sqlite_authority_paths(CODEX_GOALS_DB)
        for mtime_ms in [_path_mtime_ms(path)]
        if mtime_ms is not None
    ]
    mtime_ms = max((int(row["mtime_ms"]) for row in source_paths), default=None)
    status_counts: dict[str, int] = {}
    for goal in goals.values():
        status = str((goal or {}).get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    payload: dict[str, Any] = {
        "schema": "codex_thread_goal_authority_v1",
        "path": str(CODEX_GOALS_DB),
        "available": CODEX_GOALS_DB.is_file(),
        "row_count": len(goals),
        "status_counts": status_counts,
        "content_signature_version": _GOAL_AUTHORITY_CONTENT_SIGNATURE_VERSION,
        "content_sha16": _goal_authority_content_sha16(goals),
        "source_paths": source_paths,
    }
    if mtime_ms is not None:
        payload["mtime_ms"] = mtime_ms
        payload["mtime"] = _iso_from_epoch_ms(mtime_ms)
    return payload


def _coerce_epoch_ms(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def _goal_authority_refresh_lag(index: dict, current_authority: dict) -> dict:
    cached_authority = (
        index.get("goal_authority")
        if isinstance(index.get("goal_authority"), dict)
        else {}
    )
    previous_mtime_ms = _coerce_epoch_ms(cached_authority.get("mtime_ms")) if cached_authority else None
    current_mtime_ms = _coerce_epoch_ms(current_authority.get("mtime_ms"))
    stale_before_refresh = False
    lag_ms: int | None = None
    if current_mtime_ms is not None and previous_mtime_ms is None:
        stale_before_refresh = True
    elif current_mtime_ms is not None and previous_mtime_ms is not None:
        lag_ms = max(0, current_mtime_ms - previous_mtime_ms)
        stale_before_refresh = lag_ms > 0

    receipt: dict[str, Any] = {
        "goal_authority_stale_before_refresh": stale_before_refresh,
    }
    if previous_mtime_ms is not None:
        receipt["previous_goal_authority_mtime_ms"] = previous_mtime_ms
        receipt["previous_goal_authority_mtime"] = _iso_from_epoch_ms(previous_mtime_ms)
    if current_mtime_ms is not None:
        receipt["current_goal_authority_mtime_ms"] = current_mtime_ms
        receipt["current_goal_authority_mtime"] = _iso_from_epoch_ms(current_mtime_ms)
    if lag_ms is not None:
        receipt["goal_authority_lag_ms"] = lag_ms
    return receipt


_GOAL_TITLE_PLACEHOLDERS = {
    "",
    "<goal_context>",
    "goal_context",
    "goal context",
    "<goal>",
    "goal",
}


def _goal_fleet_control(goal: dict | None, mission_state: str) -> dict:
    status = str((goal or {}).get("status") or "").lower()
    if status == "active":
        observed_status = "active"
        next_allowed_action = "leave_alone"
        restart_policy = "do_not_reprompt_active_thread"
        decision_label = "leave active goal alone"
    elif status == "complete":
        observed_status = "idle_complete"
        next_allowed_action = "fan_in_or_reprompt_with_terminal_evidence"
        restart_policy = "reprompt_only_with_latest_terminal_evidence"
        decision_label = "fan in before restart"
    elif status in {"blocked", "usage_limited", "budget_limited"}:
        observed_status = "idle_blocked"
        next_allowed_action = "capture_or_reroute_blocker"
        restart_policy = "do_not_blind_reprompt_capture_blocker_first"
        decision_label = "capture blocker before reprompt"
    elif status == "paused":
        observed_status = "operator_owned"
        next_allowed_action = "ask_operator"
        restart_policy = "operator_instruction_required"
        decision_label = "operator instruction required"
    else:
        observed_status = "stale_unknown"
        next_allowed_action = "read_more"
        restart_policy = "read_thread_before_action"
        decision_label = "read thread before action"

    mission_state = str(mission_state or "unknown")
    return {
        "schema": "goal_fleet_control_v1",
        "mode": "goal_thread",
        "observed_status": observed_status,
        "next_allowed_action": next_allowed_action,
        "restart_policy": restart_policy,
        "decision_label": decision_label,
        "fan_in_needed": observed_status in {"idle_complete", "idle_blocked"},
        "classification_basis": {
            "goal_status": status or "unknown",
            "mission_index_state": mission_state,
            "has_recent_mission_row": mission_state in {"active_row", "inactive_row"},
        },
    }


def _goal_fleet_preview_ids(goal_threads: list[dict], action: str, *, limit: int = 20) -> tuple[list[str], int]:
    ids = [
        str(row.get("thread_id") or "")
        for row in goal_threads
        if (row.get("goal_fleet_control") or {}).get("next_allowed_action") == action
    ]
    ids = [value for value in ids if value]
    return ids[:limit], max(0, len(ids) - limit)


def _goal_fleet_state(goal_threads: list[dict], goal_authority: dict | None = None) -> dict:
    status_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    compact_threads: list[dict] = []
    for row in goal_threads:
        control = row.get("goal_fleet_control") or {}
        observed_status = str(control.get("observed_status") or "stale_unknown")
        next_allowed_action = str(control.get("next_allowed_action") or "read_more")
        status_counts[observed_status] = status_counts.get(observed_status, 0) + 1
        decision_counts[next_allowed_action] = decision_counts.get(next_allowed_action, 0) + 1
        mission_index = row.get("mission_index") or {}
        compact_threads.append({
            "thread_id": row.get("thread_id") or "",
            "goal_id": row.get("goal_id") or "",
            "mode": "goal",
            "goal_status": row.get("status") or "",
            "observed_status": observed_status,
            "next_allowed_action": next_allowed_action,
            "restart_policy": control.get("restart_policy") or "",
            "fan_in_needed": bool(control.get("fan_in_needed")),
            "current_goal_digest": row.get("objective_sha16") or "",
            "title_or_alias": mission_index.get("title") or row.get("objective_preview") or "",
            "mission_index_state": mission_index.get("state") or "unknown",
            "updated_at_ms": row.get("updated_at_ms") or 0,
        })

    left_alone, left_alone_omitted = _goal_fleet_preview_ids(goal_threads, "leave_alone")
    fan_in, fan_in_omitted = _goal_fleet_preview_ids(
        goal_threads,
        "fan_in_or_reprompt_with_terminal_evidence",
    )
    blocked, blocked_omitted = _goal_fleet_preview_ids(goal_threads, "capture_or_reroute_blocker")

    return {
        "schema": "goal_fleet_state_v1",
        "mode": "projection_from_codex_goal_roster",
        "authority": "codex_thread_goal_authority_v1 + prompt_trace_mission_index_v3",
        "goal_authority_content_sha16": (goal_authority or {}).get("content_sha16") or "",
        "thread_count": len(goal_threads),
        "status_counts": status_counts,
        "decision_counts": decision_counts,
        "fan_in_needed_count": sum(1 for row in compact_threads if row.get("fan_in_needed")),
        "threads": compact_threads,
        "controller_decision_receipt": {
            "schema": "goal_fleet_controller_decision_receipt_v1",
            "mode": "state_projection_no_prompt_sent",
            "classification_basis": "codex_goal_status_plus_mission_index_linkage",
            "observed_threads": len(goal_threads),
            "active_threads_left_alone": left_alone,
            "active_threads_left_alone_omitted": left_alone_omitted,
            "idle_threads_needing_fan_in": fan_in,
            "idle_threads_needing_fan_in_omitted": fan_in_omitted,
            "blocked_threads_needing_capture": blocked,
            "blocked_threads_needing_capture_omitted": blocked_omitted,
            "prompts_sent_digest": "none_projection_only",
            "validation_or_reason_no_validation": (
                "Projection classifies safe controller actions; create/send validation "
                "belongs to the later thread-management receipt."
            ),
        },
    }


def _goal_fleet_receipt_summary(state: dict | None) -> dict:
    state = state if isinstance(state, dict) else {}
    return {
        "schema": "goal_fleet_state_receipt_summary_v1",
        "thread_count": state.get("thread_count", 0),
        "status_counts": state.get("status_counts") or {},
        "decision_counts": state.get("decision_counts") or {},
        "fan_in_needed_count": state.get("fan_in_needed_count", 0),
    }


def _goal_roster_title_candidate(value: Any) -> str:
    title = str(value or "").strip()
    if title.lower() in _GOAL_TITLE_PLACEHOLDERS:
        return ""
    return title


def _goal_roster_mission_title(row: dict, title_record: dict, goal: dict) -> str:
    for candidate in (
        row.get("display_title"),
        row.get("title"),
        title_record.get("thread_name"),
        goal.get("objective_preview"),
    ):
        title = _goal_roster_title_candidate(candidate)
        if title:
            return title
    return ""


def _goal_thread_roster(
    goals: dict[str, dict],
    rows: list[dict],
    codex_thread_records: dict[str, dict],
) -> list[dict]:
    """Return all known Codex goal threads with bounded mission-row linkage."""
    mission_rows = {
        str(r.get("session_id") or ""): r
        for r in rows
        if r.get("provider") == "codex" and r.get("session_id")
    }
    out: list[dict] = []
    for thread_id, goal in goals.items():
        if not isinstance(goal, dict):
            continue
        row = mission_rows.get(thread_id) or {}
        title_record = codex_thread_records.get(thread_id) or {}
        mission_state = "missing_from_recent_window"
        if row:
            mission_state = "inactive_row" if row.get("inactive_reason") else "active_row"
        goal_fleet_control = _goal_fleet_control(goal, mission_state)
        out.append({
            "schema": "codex_goal_thread_roster_row_v1",
            "thread_id": thread_id,
            "goal_id": goal.get("goal_id") or "",
            "status": goal.get("status") or "",
            "objective_preview": goal.get("objective_preview") or "",
            "objective_sha16": goal.get("objective_sha16") or "",
            "token_budget": goal.get("token_budget"),
            "tokens_used": int(goal.get("tokens_used") or 0),
            "time_used_seconds": int(goal.get("time_used_seconds") or 0),
            "created_at_ms": int(goal.get("created_at_ms") or 0),
            "updated_at_ms": int(goal.get("updated_at_ms") or 0),
            "created_at": goal.get("created_at") or "",
            "updated_at": goal.get("updated_at") or "",
            "goal_sort_priority": _goal_sort_priority(goal),
            "goal_fleet_control": goal_fleet_control,
            "mission_index": {
                "state": mission_state,
                "provider": row.get("provider") or "codex",
                "session_id": thread_id,
                "mission_key": f"codex:{thread_id}",
                "title": _goal_roster_mission_title(row, title_record, goal),
                "short_label": row.get("short_label") or "",
                "inactive_reason": row.get("inactive_reason") or "",
                "row_present": bool(row),
            },
        })
    out.sort(
        key=lambda g: (
            int(g.get("goal_sort_priority") or 0),
            int(g.get("updated_at_ms") or 0),
            int(g.get("tokens_used") or 0),
        ),
        reverse=True,
    )
    return out


def _dedupe_mission_goal_rows(rows: Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = (str(row.get("provider") or ""), str(row.get("session_id") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _refresh_goal_fields_on_rows(rows: Iterable[dict], goals: dict[str, dict]) -> None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        goal = None
        if row.get("provider") == "codex":
            goal = goals.get(str(row.get("session_id") or ""))
        row["has_goal"] = bool(goal)
        row["goal"] = goal or {}
        row["goal_status"] = (goal or {}).get("status") or ""
        row["goal_sort_priority"] = _goal_sort_priority(goal)
        mission_state = "inactive_row" if row.get("inactive_reason") else "active_row"
        row["goal_fleet_control"] = _goal_fleet_control(goal, mission_state) if goal else {}


def _refresh_mission_index_goal_roster(index: dict, *, cwd: Path | None = None) -> dict:
    """Overlay current Codex goal state onto a cached mission index.

    This keeps goal-thread schema fresh without reparsing large session logs.
    The mission rows stay as originally generated; only goal fields, the
    top-level goal roster, and an explicit refresh receipt are updated.
    """
    started_perf = time.perf_counter()
    if not isinstance(index, dict):
        index = {}
    index.setdefault("schema", "prompt_trace_mission_index_v3")
    index.setdefault("generated_at", "")
    index.setdefault("cwd", str(cwd or Path.cwd()))
    for key in ("active_rows", "inactive_rows", "rows"):
        if not isinstance(index.get(key), list):
            index[key] = []

    codex_thread_records = _load_codex_thread_title_records()
    codex_thread_goals = _load_codex_thread_goals()
    for key in ("active_rows", "inactive_rows", "rows"):
        _refresh_goal_fields_on_rows(index.get(key) or [], codex_thread_goals)

    roster_source_rows = index.get("rows") or [
        *(index.get("active_rows") or []),
        *(index.get("inactive_rows") or []),
    ]
    rows = _dedupe_mission_goal_rows(roster_source_rows)
    goal_threads = _goal_thread_roster(codex_thread_goals, rows, codex_thread_records)
    active_goal_thread_count = sum(1 for g in goal_threads if g.get("status") == "active")
    mission_goal_count = sum(1 for r in rows if r.get("has_goal"))
    active_mission_goal_count = sum(
        1
        for r in rows
        if (r.get("goal") or {}).get("status") == "active"
    )

    goal_authority = _goal_authority_sources(codex_thread_goals)
    goal_fleet_state = _goal_fleet_state(goal_threads, goal_authority)
    goal_authority_lag = _goal_authority_refresh_lag(index, goal_authority)
    index["goal_authority"] = goal_authority
    index["goal_threads"] = goal_threads
    index["goal_fleet_state"] = goal_fleet_state
    index["goal_thread_count"] = len(goal_threads)
    index["active_goal_thread_count"] = active_goal_thread_count
    index["mission_goal_count"] = mission_goal_count
    index["active_mission_goal_count"] = active_mission_goal_count
    index["goal_count"] = len(goal_threads)
    index["active_goal_count"] = active_goal_thread_count
    index["goal_roster_refresh"] = {
        "schema": "prompt_trace_mission_index_goal_roster_refresh_v1",
        "mode": "cached_mission_index_overlay",
        "refreshed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "duration_ms": int((time.perf_counter() - started_perf) * 1000),
        "source_row_count": len(rows),
        "goal_row_count": len(codex_thread_goals),
        "codex_session_title_count": len(codex_thread_records),
        "preserved_generated_at": index.get("generated_at") or "",
        **goal_authority_lag,
    }
    return index


def _goal_roster_refresh_receipt(index: dict) -> dict:
    refresh = (
        index.get("goal_roster_refresh")
        if isinstance(index.get("goal_roster_refresh"), dict)
        else {}
    )
    authority = (
        index.get("goal_authority")
        if isinstance(index.get("goal_authority"), dict)
        else {}
    )
    return {
        "schema": "prompt_trace_mission_index_goal_roster_refresh_receipt_v1",
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mission_index_path": str(TRACE_STRUCTURER_MISSION_INDEX),
        "mission_index_generated_at": index.get("generated_at") or "",
        "refresh": refresh,
        "goal_authority": authority,
        "goal_fleet_state": _goal_fleet_receipt_summary(index.get("goal_fleet_state")),
        "goal_thread_count": index.get("goal_thread_count", 0),
        "active_goal_thread_count": index.get("active_goal_thread_count", 0),
        "mission_goal_count": index.get("mission_goal_count", 0),
        "active_mission_goal_count": index.get("active_mission_goal_count", 0),
    }


def _write_goal_roster_refresh_receipt(index: dict) -> dict:
    receipt = _goal_roster_refresh_receipt(index)
    TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
    body = json.dumps(receipt, indent=2, ensure_ascii=False)
    tmp = TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT.with_suffix(".json.tmp")
    tmp.write_text(body + "\n", encoding="utf-8")
    tmp.replace(TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT)
    return receipt


_GOAL_FLEET_ACTION_ORDER = (
    "capture_or_reroute_blocker",
    "fan_in_or_reprompt_with_terminal_evidence",
    "read_more",
    "ask_operator",
    "leave_alone",
)
_GOAL_FLEET_SIDE_EFFECT_FREE_ACTIONS = {"leave_alone", "ask_operator"}
_GOAL_FLEET_ACTION_THREAD_LIMIT = 50
_GOAL_FLEET_ACTION_STOP_POLICIES = {
    "leave_alone": "stop_now_do_not_reprompt_active_thread",
    "ask_operator": "stop_until_operator_instruction",
    "read_more": "read_thread_before_action",
    "fan_in_or_reprompt_with_terminal_evidence": (
        "fan_in_terminal_evidence_before_reprompt"
    ),
    "capture_or_reroute_blocker": "capture_or_reroute_blocker_before_reprompt",
}
_GOAL_FLEET_THREAD_IMPACT_CARD_FIELDS = (
    "actual_target_or_gate",
    "claimed_paths_or_claim_ref",
    "proof_landed_or_validation_ref",
    "proof_missing_or_next_validation",
    "launch_shape",
    "fan_in_or_reentry_condition",
)


def _goal_fleet_action_sort_key(action: str) -> tuple[int, str]:
    try:
        return (_GOAL_FLEET_ACTION_ORDER.index(action), action)
    except ValueError:
        return (len(_GOAL_FLEET_ACTION_ORDER), action)


def _compact_goal_fleet_action_thread(row: dict) -> dict:
    return {
        "thread_id": row.get("thread_id") or "",
        "goal_id": row.get("goal_id") or "",
        "goal_status": row.get("goal_status") or "",
        "observed_status": row.get("observed_status") or "",
        "next_allowed_action": row.get("next_allowed_action") or "",
        "restart_policy": row.get("restart_policy") or "",
        "current_goal_digest": row.get("current_goal_digest") or "",
        "title_or_alias": row.get("title_or_alias") or "",
        "mission_index_state": row.get("mission_index_state") or "",
        "updated_at_ms": row.get("updated_at_ms") or 0,
    }


def _goal_fleet_action_group(action: str, rows: list[dict]) -> dict:
    selected = [_compact_goal_fleet_action_thread(row) for row in rows]
    side_effect_free = action in _GOAL_FLEET_SIDE_EFFECT_FREE_ACTIONS
    return {
        "schema": "goal_fleet_action_group_v1",
        "action": action,
        "selected_thread_count": len(selected),
        "selected_threads": selected[:_GOAL_FLEET_ACTION_THREAD_LIMIT],
        "selected_threads_omitted": max(0, len(selected) - _GOAL_FLEET_ACTION_THREAD_LIMIT),
        "collision_check_ref": (
            "not_required_no_provider_thread_mutation"
            if side_effect_free
            else "required_before_provider_thread_mutation"
        ),
        "prompt_digest_or_none": None,
        "provider_thread_receipt": (
            "not_required_no_prompt_sent"
            if side_effect_free
            else "missing_required_before_side_effecting_action"
        ),
        "uptake_confirmed": (
            "not_applicable_no_prompt_sent"
            if side_effect_free
            else "pending_provider_thread_receipt"
        ),
        "fan_in_due_at_or_stop_policy": _GOAL_FLEET_ACTION_STOP_POLICIES.get(
            action,
            "read_thread_before_action",
        ),
        "thread_impact_card_floor": {
            "schema": "goal_fleet_thread_impact_card_floor_v1",
            "status": (
                "not_required_for_non_mutating_controller_decision"
                if side_effect_free
                else "required_before_provider_thread_mutation"
            ),
            "required_fields": list(_GOAL_FLEET_THREAD_IMPACT_CARD_FIELDS),
            "projection_limitation": (
                "Goal roster status alone cannot prove path ownership, proof state, "
                "host admission, or fan-in readiness."
            ),
        },
    }


def _goal_fleet_controller_mode_hint(actions: list[str], *, side_effect_required: bool) -> dict:
    if not actions:
        mode = "idle_no_goal_threads_observed"
        allowed_next_action = "none"
        reason = "No Codex goal threads were projected into the roster."
    elif side_effect_required:
        mode = "watch_or_fan_in_before_mutation"
        allowed_next_action = "collect_impact_cards_then_record_provider_receipt"
        reason = (
            "At least one projected thread needs read, fan-in, blocker capture, "
            "or operator action before a controller can safely mutate provider threads."
        )
    else:
        mode = "projection_no_send"
        allowed_next_action = "stop_or_refresh_roster_before_new_provider_action"
        reason = "All projected actions are side-effect-free controller decisions."
    return {
        "schema": "goal_fleet_controller_mode_hint_v1",
        "mode": mode,
        "allowed_next_action": allowed_next_action,
        "reason": reason,
        "action_count": len(actions),
        "side_effect_required": side_effect_required,
    }


def _goal_fleet_admission_guard(
    actions: list[str],
    *,
    side_effect_required: bool,
    collision_check_ref: str,
) -> dict:
    if not actions:
        status = "no_action_needed"
    elif side_effect_required:
        status = "blocked_until_live_admission_packet"
    else:
        status = "non_mutating_projection_only"
    return {
        "schema": "goal_fleet_admission_guard_v1",
        "status": status,
        "collision_check_ref": collision_check_ref or (
            "required_before_provider_thread_mutation"
            if side_effect_required
            else "not_required_no_provider_thread_mutation"
        ),
        "requires_before_provider_thread_mutation": [
            "fresh target-thread readback",
            "fresh Work Ledger session/claim collision check",
            "host/resource pressure admission check for host-heavy lanes",
            "ThreadImpactCard fields for each steered thread",
            "provider-thread receipt for read/send/create/archive/title/pin actions",
        ],
        "non_overfit_boundary": (
            "This guard is independent of domain names, stale counts, and old trace prompts; "
            "live claim, host, and thread evidence decide whether to watch, fan in, or mutate."
        ),
    }


def _goal_fleet_work_ledger_capacity_snapshot(repo_root: Path) -> dict:
    command = [
        str(repo_root / "repo-python"),
        "tools/meta/factory/work_ledger.py",
        "session-status",
        "--seed-speed",
        "--limit",
        "12",
        "--json",
    ]
    try:
        proc = subprocess.run(
            command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except Exception as exc:
        return {
            "schema": "work_ledger_capacity_snapshot_v1",
            "status": "not_available",
            "source_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
            "error_class": type(exc).__name__,
            "authority_boundary": (
                "Goal roster projection cannot prove claim-effective work; rerun the source "
                "command before provider-thread mutation."
            ),
        }
    if proc.returncode != 0:
        return {
            "schema": "work_ledger_capacity_snapshot_v1",
            "status": "not_available",
            "source_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
            "returncode": proc.returncode,
            "stderr_preview": (proc.stderr or "")[:500],
            "authority_boundary": (
                "Goal roster projection cannot prove claim-effective work; rerun the source "
                "command before provider-thread mutation."
            ),
        }
    try:
        packet = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {
            "schema": "work_ledger_capacity_snapshot_v1",
            "status": "not_available",
            "source_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
            "error_class": type(exc).__name__,
            "stdout_preview": (proc.stdout or "")[:500],
            "authority_boundary": (
                "Goal roster projection cannot prove claim-effective work; rerun the source "
                "command before provider-thread mutation."
            ),
        }
    counts = packet.get("counts") if isinstance(packet.get("counts"), dict) else {}
    risk = packet.get("risk") if isinstance(packet.get("risk"), dict) else {}
    return {
        "schema": "work_ledger_capacity_snapshot_v1",
        "status": "available",
        "source_schema": packet.get("schema"),
        "source_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
        "generated_at": packet.get("generated_at") or "",
        "effective_active_sessions": int(counts.get("effective_active_sessions") or 0),
        "active_claims": int(counts.get("active_claims") or 0),
        "active_claim_session_count": int(counts.get("active_claim_session_count") or 0),
        "claim_collisions": int(counts.get("claim_collisions") or 0),
        "heartbeat_gap_count": int(counts.get("claim_session_heartbeat_gap_count") or 0),
        "orphaned_active_sessions": int(counts.get("orphaned_active_sessions") or 0),
        "unclaimed_touched_sessions": int(counts.get("unclaimed_touched_sessions") or 0),
        "risk_level": risk.get("risk_level") or "unknown",
        "risk_signals": list(risk.get("signals") or []),
        "first_action_kind": packet.get("first_action_kind") or "",
        "first_action_command": packet.get("first_action_command") or "",
        "count_semantics": packet.get("count_semantics") or {},
        "authority_boundary": (
            "Work Ledger is the live claim-effective authority; goal roster counts are app/goal "
            "projection and must not be treated as live agent capacity."
        ),
    }


def _goal_fleet_host_pressure_snapshot(repo_root: Path) -> dict:
    try:
        from system.lib import resource_pressure

        compact = resource_pressure.compact_host_resource_pressure_packet(
            resource_pressure.build_host_resource_pressure_packet(repo_root)
        )
    except Exception as exc:
        return {
            "schema": "host_resource_pressure_packet_v0",
            "status": "not_available",
            "source_command": "./repo-python -m system.lib.resource_pressure --compact",
            "error_class": type(exc).__name__,
            "authority_boundary": (
                "Host pressure was not available; run the source command before starting "
                "host-heavy provider, builder, verifier, or projection work."
            ),
        }
    return {
        **compact,
        "source_command": "./repo-python -m system.lib.resource_pressure --compact",
        "authority_boundary": (
            "Host pressure gates launch order and host-heavy work; pressure-aware work may "
            "continue only when it is disjoint and does not worsen the primary pressure class."
        ),
    }


def _goal_fleet_fleet_admission_status(
    *,
    host_pressure: dict,
    work_ledger_capacity: dict,
) -> str:
    host_status = str(host_pressure.get("status") or "unknown")
    normal_work_allowed = host_pressure.get("normal_work_allowed")
    claim_collisions = int(work_ledger_capacity.get("claim_collisions") or 0)
    heartbeat_gap_count = int(work_ledger_capacity.get("heartbeat_gap_count") or 0)
    risk_level = str(work_ledger_capacity.get("risk_level") or "unknown")
    if normal_work_allowed is False or host_status == "critical":
        return "pressure_blocked_except_repair_or_authorized_override"
    if claim_collisions > 0:
        return "watch_claim_collision"
    if heartbeat_gap_count > 0:
        return "watch_heartbeat_gap"
    if risk_level not in {"", "ok", "clear", "none"}:
        return "watch_capacity_pressure"
    if host_status in {"attention", "watch", "unknown", "not_available"}:
        return "pressure_aware"
    return "normal"


def _goal_fleet_default_fleet_admission_snapshot() -> dict:
    return {
        "schema": "fleet_admission_snapshot_v1",
        "status": "not_supplied",
        "host_pressure": {
            "schema": "host_resource_pressure_packet_v0",
            "status": "not_supplied",
            "source_command": "./repo-python -m system.lib.resource_pressure --compact",
        },
        "work_ledger_capacity": {
            "schema": "work_ledger_capacity_snapshot_v1",
            "status": "not_supplied",
            "source_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
        },
        "authority_boundary": (
            "Direct unit construction did not read live host/claim state; live CLI receipts "
            "populate this from resource_pressure and Work Ledger."
        ),
    }


def _goal_fleet_spawn_admission(
    *,
    work_ledger_capacity: dict,
    host_pressure: dict,
    fleet_admission_status: str,
) -> dict:
    """Echo the goal_fleet_governance Operator Concurrency-Pressure Admission gate.

    Operator throughput pressure ("spawn more", "10x", "use N subagents", "don't
    stop") is admission-gated input, not a launch authorization. This computes the
    objective session/collision/host gate so a cold conductor can read the
    strike-vs-fan-in decision straight from the receipt; conditions the runtime
    cannot observe stay listed under conductor_must_still_confirm so a
    strike_eligible verdict never greenwashes a raw spawn.
    """
    cap_status = str(work_ledger_capacity.get("status") or "unknown")
    effective_sessions = int(work_ledger_capacity.get("effective_active_sessions") or 0)
    claim_collisions = int(work_ledger_capacity.get("claim_collisions") or 0)
    host_status = str(host_pressure.get("status") or "unknown")
    normal_work_allowed = host_pressure.get("normal_work_allowed")

    blocking_reasons: list[str] = []
    if cap_status != "available":
        blocking_reasons.append("work_ledger_capacity_not_live_rerun_seed_speed")
    if effective_sessions > 8:
        blocking_reasons.append("effective_active_sessions_over_saturation_ceiling_8")
    if claim_collisions > 0:
        blocking_reasons.append("active_claim_collisions")
    if normal_work_allowed is False or host_status == "critical":
        blocking_reasons.append("host_pressure_blocks_normal_work")
    if fleet_admission_status not in {"normal", "pressure_aware"}:
        blocking_reasons.append(f"fleet_admission_status_{fleet_admission_status}")

    if blocking_reasons:
        verdict = "spawn_blocked_fan_in_or_watch"
    elif effective_sessions <= 6 and claim_collisions == 0:
        verdict = "strike_eligible_pending_disjoint_proof_lane"
    else:
        verdict = "watch_until_admission_clear"

    return {
        "schema": "goal_fleet_spawn_admission_v1",
        "verdict": verdict,
        "operator_pressure_is_admission_gated": True,
        "effective_active_sessions": effective_sessions,
        "saturation_ceiling": 8,
        "strike_reentry_ceiling": 6,
        "claim_collisions": claim_collisions,
        "blocking_reasons": blocking_reasons,
        "conductor_must_still_confirm": [
            "at least one clean unclaimed proof lane with disjoint write scope",
            "named proof consumer and fan-in consumer for each new lane",
            "no idle validated-claim-holder backlog",
            "no saturated generated/rerank/verifier owner already covering the target class",
        ],
        "doctrine_ref": (
            "codex/doctrine/skills/doctrine/goal_fleet_governance.md"
            "#operator-concurrency-pressure-admission"
        ),
        "authority_boundary": (
            "Objective session/collision/host gate only; operator concurrency pressure "
            "('spawn more', '10x', 'use N subagents') raises ambition, not the ceiling. "
            "A strike_eligible verdict still requires the conductor_must_still_confirm "
            "conditions before any provider-thread or subagent spawn."
        ),
    }


def _goal_fleet_fleet_admission_snapshot(repo_root: Path) -> dict:
    host_pressure = _goal_fleet_host_pressure_snapshot(repo_root)
    work_ledger_capacity = _goal_fleet_work_ledger_capacity_snapshot(repo_root)
    fleet_admission_status = _goal_fleet_fleet_admission_status(
        host_pressure=host_pressure,
        work_ledger_capacity=work_ledger_capacity,
    )
    return {
        "schema": "fleet_admission_snapshot_v1",
        "status": fleet_admission_status,
        "host_pressure": host_pressure,
        "work_ledger_capacity": work_ledger_capacity,
        "spawn_admission": _goal_fleet_spawn_admission(
            work_ledger_capacity=work_ledger_capacity,
            host_pressure=host_pressure,
            fleet_admission_status=fleet_admission_status,
        ),
        "spawn_or_provider_mutation_policy": (
            "Do not create or reprompt provider threads from goal-roster status alone. "
            "Under watch/pressure states, prefer fan-in, closeout, owner-visible messages, "
            "or disjoint low-weight support work until fresh admission is clear."
        ),
        "source_commands": [
            "./repo-python -m system.lib.resource_pressure --compact",
            "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12 --json",
        ],
        "authority_boundary": (
            "Fleet admission composes host/resource pressure with Work Ledger claim-effective "
            "capacity; pasted trace counts and goal-roster counts are advisory only."
        ),
    }


def _goal_fleet_observed_state_ref(
    index: dict,
    state: dict,
    status: dict,
    authority: dict,
) -> dict:
    staleness = status.get("staleness") if isinstance(status.get("staleness"), dict) else {}
    return {
        "schema": "observed_goal_fleet_state_ref_v1",
        "mission_index_path": str(TRACE_STRUCTURER_MISSION_INDEX),
        "mission_index_mtime_ms": _path_mtime_ms(TRACE_STRUCTURER_MISSION_INDEX),
        "mission_index_generated_at": index.get("generated_at") or "",
        "goal_authority_path": authority.get("path") or str(CODEX_GOALS_DB),
        "goal_authority_content_sha16": state.get("goal_authority_content_sha16") or "",
        "goal_authority_mtime_ms": authority.get("mtime_ms"),
        "goal_authority_mtime": authority.get("mtime") or "",
        "goal_thread_count": state.get("thread_count", 0),
        "status_counts": state.get("status_counts") or {},
        "decision_counts": state.get("decision_counts") or {},
        "fan_in_needed_count": state.get("fan_in_needed_count", 0),
        "goal_roster_staleness": {
            "status": staleness.get("status") or "unknown",
            "kind": staleness.get("kind") or "unknown",
            "refresh_recommended": bool(staleness.get("refresh_recommended")),
        },
    }


def _goal_fleet_action_receipt_from_state(
    state: dict,
    *,
    observed_goal_fleet_state_ref: dict | None = None,
    collision_check_ref: str = "",
    workitem_refs: list[str] | None = None,
    fleet_admission_snapshot: dict | None = None,
) -> dict:
    threads = state.get("threads") if isinstance(state.get("threads"), list) else []
    grouped: dict[str, list[dict]] = {}
    for row in threads:
        if not isinstance(row, dict):
            continue
        action = str(row.get("next_allowed_action") or "read_more")
        grouped.setdefault(action, []).append(row)

    action_groups = [
        _goal_fleet_action_group(action, grouped[action])
        for action in sorted(grouped, key=_goal_fleet_action_sort_key)
    ]
    actions = [group["action"] for group in action_groups]
    selected = [
        _compact_goal_fleet_action_thread(row)
        for action in sorted(grouped, key=_goal_fleet_action_sort_key)
        for row in grouped[action]
    ]
    side_effect_required = any(
        action not in _GOAL_FLEET_SIDE_EFFECT_FREE_ACTIONS
        for action in actions
    )
    if not actions:
        action_label = "none_no_goal_threads_observed"
    elif len(actions) == 1:
        action_label = actions[0]
    else:
        action_label = "mixed:" + ",".join(actions)

    admission_guard = _goal_fleet_admission_guard(
        actions,
        side_effect_required=side_effect_required,
        collision_check_ref=collision_check_ref,
    )
    if side_effect_required:
        provider_status = "missing_required_before_side_effecting_action"
        uptake = "pending_provider_thread_receipt"
        policy = "read_or_fan_in_required_before_provider_thread_mutation"
        next_gate = "read_thread_or_capture_blocker_then_record_provider_receipt"
    else:
        provider_status = "not_required_no_prompt_sent"
        uptake = "not_applicable_no_prompt_sent"
        policy = "stop_after_non_mutating_controller_decision"
        next_gate = "provider_thread_action_requires_fresh_read_and_collision_check"

    return {
        "schema": "goal_fleet_action_receipt_v1",
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": "controller_action_receipt",
        "observed_goal_fleet_state_ref": observed_goal_fleet_state_ref or {
            "schema": "observed_goal_fleet_state_ref_v1",
            "goal_thread_count": state.get("thread_count", 0),
            "status_counts": state.get("status_counts") or {},
            "decision_counts": state.get("decision_counts") or {},
            "fan_in_needed_count": state.get("fan_in_needed_count", 0),
        },
        "selected_threads": selected[:_GOAL_FLEET_ACTION_THREAD_LIMIT],
        "selected_threads_omitted": max(0, len(selected) - _GOAL_FLEET_ACTION_THREAD_LIMIT),
        "action": action_label,
        "action_groups": action_groups,
        "fleet_admission_snapshot": (
            fleet_admission_snapshot
            if isinstance(fleet_admission_snapshot, dict)
            else _goal_fleet_default_fleet_admission_snapshot()
        ),
        "controller_mode_hint": _goal_fleet_controller_mode_hint(
            actions,
            side_effect_required=side_effect_required,
        ),
        "admission_guard": admission_guard,
        "collision_check_ref": collision_check_ref or (
            "not_required_no_provider_thread_mutation"
            if not side_effect_required
            else "required_before_provider_thread_mutation"
        ),
        "prompt_digest_or_none": None,
        "provider_thread_receipt": {
            "schema": "goal_fleet_provider_thread_receipt_v1",
            "status": provider_status,
            "read_thread_count": 0,
            "send_message_count": 0,
            "create_thread_count": 0,
            "provider_receipts": [],
            "reason": (
                "This receipt records controller classification only; "
                "side-effecting read/send/create actions need their own "
                "provider-thread receipts."
            ),
        },
        "uptake_confirmed": uptake,
        "fan_in_due_at_or_stop_policy": policy,
        "workitem_refs_touched": list(workitem_refs or []),
        "side_effecting_thread_action_taken": False,
        "next_side_effect_gate": next_gate,
    }


def _goal_fleet_action_receipt(
    *,
    cwd: Path | None = None,
    collision_check_ref: str = "",
    workitem_refs: list[str] | None = None,
) -> dict:
    index = _load_json_dict(TRACE_STRUCTURER_MISSION_INDEX)
    rows = _dedupe_mission_goal_rows(
        index.get("rows") or [
            *(index.get("active_rows") or []),
            *(index.get("inactive_rows") or []),
        ]
    )
    goals = _load_codex_thread_goals()
    authority = _goal_authority_sources(goals)
    roster = _goal_thread_roster(goals, rows, _load_codex_thread_title_records())
    state = _goal_fleet_state(roster, authority)
    status = _goal_roster_status(cwd=cwd)
    return _goal_fleet_action_receipt_from_state(
        state,
        observed_goal_fleet_state_ref=_goal_fleet_observed_state_ref(
            index,
            state,
            status,
            authority,
        ),
        collision_check_ref=collision_check_ref,
        workitem_refs=workitem_refs,
        fleet_admission_snapshot=_goal_fleet_fleet_admission_snapshot(REPO_ROOT),
    )


def _write_goal_fleet_action_receipt(receipt: dict) -> dict:
    TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
    body = json.dumps(receipt, indent=2, ensure_ascii=False)
    tmp = TRACE_STRUCTURER_GOAL_FLEET_ACTION_RECEIPT.with_suffix(".json.tmp")
    tmp.write_text(body + "\n", encoding="utf-8")
    tmp.replace(TRACE_STRUCTURER_GOAL_FLEET_ACTION_RECEIPT)
    return receipt


def _load_json_dict(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _goal_roster_projection_source(index: dict, receipt: dict, current: dict) -> dict:
    current_count = int(current.get("goal_thread_count") or 0)
    current_active_count = int(current.get("active_goal_thread_count") or 0)
    return {
        "current_goal_thread_count": current_count,
        "current_active_goal_thread_count": current_active_count,
        "mission_index_goal_thread_count": int(index.get("goal_thread_count") or 0),
        "mission_index_active_goal_thread_count": int(index.get("active_goal_thread_count") or 0),
        "receipt_goal_thread_count": int(receipt.get("goal_thread_count") or 0),
        "receipt_active_goal_thread_count": int(receipt.get("active_goal_thread_count") or 0),
    }


def _goal_roster_status(cwd: Path | None = None) -> dict:
    """Summarize whether the cached Structurer goal roster trails Codex goals."""
    index = _load_json_dict(TRACE_STRUCTURER_MISSION_INDEX)
    receipt = _load_json_dict(TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT)
    goals = _load_codex_thread_goals()
    current_authority = _goal_authority_sources(goals)
    current_goal_fleet_state = _goal_fleet_state(
        _goal_thread_roster(goals, [], {}),
        current_authority,
    )
    current = {
        "goal_authority": current_authority,
        "goal_fleet_state": _goal_fleet_receipt_summary(current_goal_fleet_state),
        "goal_thread_count": len(goals),
        "active_goal_thread_count": sum(
            1 for goal in goals.values() if (goal or {}).get("status") == "active"
        ),
    }
    counts = _goal_roster_projection_source(index, receipt, current)

    index_authority = index.get("goal_authority") if isinstance(index.get("goal_authority"), dict) else {}
    receipt_authority = (
        receipt.get("goal_authority") if isinstance(receipt.get("goal_authority"), dict) else {}
    )
    current_mtime_ms = _coerce_epoch_ms(current_authority.get("mtime_ms"))
    index_authority_mtime_ms = _coerce_epoch_ms(index_authority.get("mtime_ms"))
    receipt_authority_mtime_ms = _coerce_epoch_ms(receipt_authority.get("mtime_ms"))
    projected_authorities = [
        authority
        for authority in (index_authority, receipt_authority)
        if isinstance(authority, dict) and authority
    ]
    projected_mtimes = [
        value
        for value in (index_authority_mtime_ms, receipt_authority_mtime_ms)
        if value is not None
    ]
    latest_projected_mtime_ms = max(projected_mtimes) if projected_mtimes else None
    latest_projected_authority = max(
        projected_authorities,
        key=lambda authority: _coerce_epoch_ms(authority.get("mtime_ms")) or 0,
        default={},
    )
    current_content_sha16 = str(current_authority.get("content_sha16") or "")
    latest_projected_content_sha16 = str(latest_projected_authority.get("content_sha16") or "")
    content_signature_version = str(
        current_authority.get("content_signature_version")
        or _GOAL_AUTHORITY_CONTENT_SIGNATURE_VERSION
    )
    projected_content_signature_version = str(
        latest_projected_authority.get("content_signature_version") or ""
    )
    content_signature_comparable = bool(
        current_content_sha16
        and latest_projected_content_sha16
        and projected_content_signature_version == content_signature_version
    )
    content_signature_version_lag = bool(
        current_content_sha16
        and latest_projected_content_sha16
        and projected_content_signature_version
        and projected_content_signature_version != content_signature_version
    )
    content_delta_present = bool(
        content_signature_comparable
        and current_content_sha16 != latest_projected_content_sha16
    )
    mtime_lag_without_content_delta = bool(
        content_signature_comparable
        and not content_delta_present
        and current_mtime_ms is not None
        and latest_projected_mtime_ms is not None
        and current_mtime_ms > latest_projected_mtime_ms
    )

    reasons: list[str] = []
    if not TRACE_STRUCTURER_MISSION_INDEX.is_file():
        reasons.append("mission_index_missing")
    if not TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT.is_file():
        reasons.append("refresh_receipt_missing")
    if not current_authority.get("available"):
        reasons.append("goal_authority_unavailable")
    elif current_mtime_ms is not None and latest_projected_mtime_ms is None:
        reasons.append("goal_authority_not_projected")
    elif (
        current_mtime_ms is not None
        and latest_projected_mtime_ms is not None
        and current_mtime_ms > latest_projected_mtime_ms
        and not mtime_lag_without_content_delta
    ):
        reasons.append("goal_authority_mtime_lag")
    if content_signature_version_lag:
        reasons.append("goal_authority_content_signature_version_lag")
    if content_delta_present:
        reasons.append("goal_authority_content_lag")
    if counts["current_goal_thread_count"] != counts["mission_index_goal_thread_count"]:
        reasons.append("mission_index_goal_thread_count_delta")
    if counts["current_active_goal_thread_count"] != counts["mission_index_active_goal_thread_count"]:
        reasons.append("mission_index_active_goal_thread_count_delta")
    if counts["current_goal_thread_count"] != counts["receipt_goal_thread_count"]:
        reasons.append("receipt_goal_thread_count_delta")
    if counts["current_active_goal_thread_count"] != counts["receipt_active_goal_thread_count"]:
        reasons.append("receipt_active_goal_thread_count_delta")

    lag_ms = None
    if current_mtime_ms is not None and latest_projected_mtime_ms is not None:
        lag_ms = max(0, current_mtime_ms - latest_projected_mtime_ms)

    count_delta_reason_ids = {
        "mission_index_goal_thread_count_delta",
        "mission_index_active_goal_thread_count_delta",
        "receipt_goal_thread_count_delta",
        "receipt_active_goal_thread_count_delta",
    }
    content_delta_reason_ids = {
        "goal_authority_content_lag",
        "goal_authority_content_signature_version_lag",
    }
    availability_reason_ids = {
        "mission_index_missing",
        "refresh_receipt_missing",
        "goal_authority_unavailable",
        "goal_authority_not_projected",
    }
    reason_set = set(reasons)
    count_delta_present = bool(reason_set & count_delta_reason_ids)
    roster_content_delta_present = bool(reason_set & content_delta_reason_ids)
    availability_issue_present = bool(reason_set & availability_reason_ids)
    metadata_lag_only = reason_set == {"goal_authority_mtime_lag"}
    if not reasons:
        staleness_kind = "fresh"
    elif count_delta_present:
        staleness_kind = "roster_count_delta"
    elif roster_content_delta_present:
        staleness_kind = "roster_content_delta"
    elif availability_issue_present:
        staleness_kind = "source_unavailable"
    elif metadata_lag_only:
        staleness_kind = "metadata_lag"
    else:
        staleness_kind = "mixed"

    counts_aligned = not count_delta_present and not availability_issue_present
    projection_missing_present = bool(reason_set & {
        "mission_index_missing",
        "refresh_receipt_missing",
        "goal_authority_not_projected",
    })
    goal_authority_unavailable = "goal_authority_unavailable" in reason_set
    if not reasons:
        refresh_priority = "none"
        refresh_action = "none"
        refresh_reason = "goal roster projection is current"
    elif goal_authority_unavailable:
        refresh_priority = "blocked"
        refresh_action = "repair_goal_authority"
        refresh_reason = "current Codex goal authority is unavailable"
    elif count_delta_present or roster_content_delta_present or projection_missing_present:
        refresh_priority = "high"
        refresh_action = "refresh_now"
        refresh_reason = "goal roster counts, content, or projection anchors are stale"
    elif metadata_lag_only:
        refresh_priority = "low"
        refresh_action = "refresh_when_metadata_freshness_matters"
        refresh_reason = "goal roster counts are aligned; only authority metadata mtime lags"
    else:
        refresh_priority = "normal"
        refresh_action = "inspect_then_refresh"
        refresh_reason = "mixed goal roster staleness reasons require inspection"

    staleness: dict[str, Any] = {
        "status": "stale" if reasons else "fresh",
        "kind": staleness_kind,
        "refresh_recommended": bool(reasons),
        "refresh_action": refresh_action,
        "refresh_priority": refresh_priority,
        "reasons": reasons,
        "metadata_lag_only": metadata_lag_only,
        "count_delta_present": count_delta_present,
        "content_delta_present": roster_content_delta_present,
        "mtime_lag_without_content_delta": mtime_lag_without_content_delta,
        "availability_issue_present": availability_issue_present,
        "counts_aligned": counts_aligned,
        "full_mission_index_rewrite_required_for_count_accuracy": count_delta_present,
        "refresh_recommendation": {
            "action": refresh_action,
            "priority": refresh_priority,
            "reason": refresh_reason,
            "counts_aligned": counts_aligned,
            "metadata_lag_only": metadata_lag_only,
            "content_delta_present": roster_content_delta_present,
            "full_mission_index_rewrite_required_for_count_accuracy": count_delta_present,
        },
        **counts,
        "goal_thread_count_delta": counts["current_goal_thread_count"] - counts["mission_index_goal_thread_count"],
        "active_goal_thread_count_delta": (
            counts["current_active_goal_thread_count"]
            - counts["mission_index_active_goal_thread_count"]
        ),
        "receipt_goal_thread_count_delta": (
            counts["current_goal_thread_count"] - counts["receipt_goal_thread_count"]
        ),
        "receipt_active_goal_thread_count_delta": (
            counts["current_active_goal_thread_count"]
            - counts["receipt_active_goal_thread_count"]
        ),
        "current_goal_authority_mtime_ms": current_mtime_ms,
        "mission_index_goal_authority_mtime_ms": index_authority_mtime_ms,
        "receipt_goal_authority_mtime_ms": receipt_authority_mtime_ms,
        "latest_projected_goal_authority_mtime_ms": latest_projected_mtime_ms,
        "goal_authority_content_signature_version": content_signature_version,
        "latest_projected_goal_authority_content_signature_version": projected_content_signature_version,
        "current_goal_authority_content_sha16": current_content_sha16,
        "latest_projected_goal_authority_content_sha16": latest_projected_content_sha16,
        "goal_authority_content_signature_comparable": content_signature_comparable,
        "goal_authority_content_signature_version_lag": content_signature_version_lag,
    }
    if lag_ms is not None:
        staleness["goal_authority_lag_ms"] = lag_ms

    return {
        "schema": "prompt_trace_mission_index_goal_roster_status_v1",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "cwd": str(cwd or Path.cwd()),
        "mission_index": {
            "path": str(TRACE_STRUCTURER_MISSION_INDEX),
            "available": TRACE_STRUCTURER_MISSION_INDEX.is_file(),
            "mtime_ms": _path_mtime_ms(TRACE_STRUCTURER_MISSION_INDEX),
            "generated_at": index.get("generated_at") or "",
            "goal_authority": index_authority,
            "goal_fleet_state": _goal_fleet_receipt_summary(index.get("goal_fleet_state")),
            "goal_thread_count": counts["mission_index_goal_thread_count"],
            "active_goal_thread_count": counts["mission_index_active_goal_thread_count"],
        },
        "refresh_receipt": {
            "path": str(TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT),
            "available": TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT.is_file(),
            "mtime_ms": _path_mtime_ms(TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT),
            "recorded_at": receipt.get("recorded_at") or "",
            "goal_authority": receipt_authority,
            "goal_fleet_state": _goal_fleet_receipt_summary(receipt.get("goal_fleet_state")),
            "goal_thread_count": counts["receipt_goal_thread_count"],
            "active_goal_thread_count": counts["receipt_active_goal_thread_count"],
        },
        "current": current,
        "goal_fleet_state": current["goal_fleet_state"],
        "staleness": staleness,
        "refresh_command": (
            "./repo-python tools/meta/observability/cli_prompt_trace.py "
            "--mission-index-goal-roster-refresh"
        ),
    }


def _load_title_aliases() -> dict[str, str]:
    if not TRACE_STRUCTURER_TITLE_ALIASES.is_file():
        return {}
    try:
        data = json.loads(TRACE_STRUCTURER_TITLE_ALIASES.read_text())
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _path_mtime_ms(path: Path) -> int | None:
    try:
        return int(path.stat().st_mtime * 1000)
    except Exception:
        return None


def _iso_mtime_ms(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return int(_dt.datetime.fromisoformat(text).timestamp() * 1000)
    except Exception:
        return None


def _title_authority_sources(claude_desktop_titles: dict[str, dict]) -> dict:
    sources: list[dict] = []
    for source_id, path in (
        ("codex_session_index", CODEX_SESSION_INDEX),
        ("agent_trace_title_aliases", TRACE_STRUCTURER_TITLE_ALIASES),
    ):
        mtime_ms = _path_mtime_ms(path)
        if mtime_ms is not None:
            sources.append({"id": source_id, "path": str(path), "mtime_ms": mtime_ms})
    claude_paths = [
        str(row.get("metadata_path") or "")
        for row in (claude_desktop_titles or {}).values()
        if row.get("metadata_path")
    ]
    claude_mtimes = [
        mtime_ms
        for mtime_ms in (_path_mtime_ms(Path(path)) for path in claude_paths)
        if mtime_ms is not None
    ]
    if claude_mtimes:
        sources.append({
            "id": "claude_desktop_sessions",
            "path": str(CLAUDE_DESKTOP_SESSIONS),
            "mtime_ms": max(claude_mtimes),
            "file_count": len(claude_mtimes),
        })
    latest = max((int(s["mtime_ms"]) for s in sources), default=None)
    return {
        "schema": "agent_trace_title_authority_v1",
        "latest_mtime_ms": latest,
        "source_count": len(sources),
        "sources": sources,
    }


def _peek_claude_first_prompt(path: Path, *, max_chars: int = 200) -> str:
    """Cheap scan: return the first real user-prompt preview without full parse."""
    try:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not _is_real_claude_prompt(rec):
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content")
                text = _flatten_claude_content(content)
                if not text:
                    continue
                for raw in text.splitlines():
                    stripped = raw.strip()
                    if stripped and not stripped.startswith("["):
                        return stripped[:max_chars]
                return text.strip()[:max_chars]
    except Exception:
        pass
    return ""


def _resolve_session_title(
    provider: str,
    session_id: str,
    session_file: Path,
    *,
    codex_thread_names: dict[str, str],
    title_aliases: dict[str, str],
    claude_desktop_titles: dict[str, dict] | None = None,
) -> tuple[str, str]:
    """Returns (title, title_source)."""
    alias_key = f"{provider}:{session_id}"
    if provider == "codex":
        if session_id in codex_thread_names:
            return codex_thread_names[session_id], "codex_thread_name"
    if provider == "claude_code":
        desktop = (claude_desktop_titles or {}).get(session_id) or {}
        title = (desktop.get("title") or "").strip()
        if title:
            source = "claude_desktop_user_title" if desktop.get("title_source") == "user" else "claude_desktop_title"
            return title, source
        preview = _peek_claude_first_prompt(session_file)
        if preview:
            return preview, "claude_first_prompt_preview"
    if alias_key in title_aliases:
        return title_aliases[alias_key], "operator_alias"
    return "", "no_title_resolved"


MISSION_ORDINAL_RE = re.compile(r"^\s*(?:old\s+)?(\d+)\s*[, ]\s*(\d+)\b")
OPERATOR_OLD_TITLE_PREFIX_RE = re.compile(r"^\s*old(?:$|[^a-z0-9])", re.I)


def _has_operator_old_title_prefix(title: str) -> bool:
    return bool(OPERATOR_OLD_TITLE_PREFIX_RE.search(str(title or "")))


def _operator_old_title_marker(source_title: str, operator_alias: str) -> str:
    return "old_prefix" if _has_operator_old_title_prefix(source_title or operator_alias or "") else "none"


def _mission_ordinal(title: str) -> tuple[int | None, int | None, str | None]:
    """Extract numeric pair from operator titles like '17, 18 traces' or '5,6 microcosm'.

    Returns (start, end, source_tag) or (None, None, None)."""
    if not title:
        return (None, None, None)
    m = MISSION_ORDINAL_RE.match(title)
    if not m:
        return (None, None, None)
    try:
        return (int(m.group(1)), int(m.group(2)), "title_numeric_pair")
    except Exception:
        return (None, None, None)


def _row_title_authority_fact(
    *,
    provider: str,
    session_id: str,
    session_file: Path,
    title: str,
    title_source: str,
    title_aliases: dict[str, str],
    codex_thread_records: dict[str, dict],
    claude_desktop_titles: dict[str, dict],
    prompt_preview: str,
) -> dict:
    alias_key = f"{provider}:{session_id}"
    operator_alias = title_aliases.get(alias_key, "")
    source_title = ""
    source_version_ms: int | None = None
    authority = title_source
    if provider == "codex":
        rec = codex_thread_records.get(session_id) or {}
        source_title = str(rec.get("thread_name") or "")
        source_version_ms = _iso_mtime_ms(str(rec.get("updated_at") or "")) or _path_mtime_ms(CODEX_SESSION_INDEX)
    elif provider == "claude_code":
        desktop = (claude_desktop_titles or {}).get(session_id) or {}
        desktop_title = str(desktop.get("title") or "").strip()
        if desktop_title:
            source_title = desktop_title
            metadata_path = str(desktop.get("metadata_path") or "")
            source_version_ms = _path_mtime_ms(Path(metadata_path)) if metadata_path else None
        else:
            source_version_ms = _path_mtime_ms(session_file)
    if not source_title and title_source in ("codex_thread_name", "claude_desktop_title", "claude_desktop_user_title"):
        source_title = title
    if title_source == "operator_alias":
        source_version_ms = _path_mtime_ms(TRACE_STRUCTURER_TITLE_ALIASES) or source_version_ms
    if title_source in ("trace_prompt_title", "claude_first_prompt_preview", "current_turn_prompt_title", "current_turn_prompt_preview"):
        source_version_ms = _path_mtime_ms(session_file) or source_version_ms
    display_title = source_title or operator_alias or title or prompt_preview or session_id[:6]
    title_marker = _operator_old_title_marker(source_title, operator_alias)
    return {
        "title_authority": authority,
        "source_title": source_title,
        "operator_alias": operator_alias,
        "display_title": display_title,
        "prompt_preview": prompt_preview,
        "title_marker": title_marker,
        "source_title_version_ms": source_version_ms,
    }


def _latest_completed_turn_summary(provider: str, session_file: Path) -> dict | None:
    """Parse the session JSONL and return a compact summary of the latest
    completed turn. Returns None if no completed turn exists. Expensive — only
    call from the feeder, not the render path."""
    try:
        if provider == "claude_code":
            turns = parse_claude_session(session_file)
        elif provider == "codex":
            turns = parse_codex_session(session_file)
        else:
            return None
    except Exception:
        return None
    latest_completed = None
    latest_active = None
    for t in turns:
        if t.is_complete:
            latest_completed = t
        else:
            latest_active = t
    def _summarize_trace_turn(turn: Turn, *, complete_override: bool | None = None) -> dict:
        cycle_turn = merge_prompt_cycle(
            prompt_cycle_turns(
                turns,
                turn,
                threshold_words=SHORT_PROMPT_CHAIN_WORD_THRESHOLD,
            ),
            threshold_words=SHORT_PROMPT_CHAIN_WORD_THRESHOLD,
        )
        full_turn = merge_full_thread(full_thread_turns(turns, turn))
        trace_window = (cycle_turn.source_ref or {}).get("trace_window") or (cycle_turn.source_ref or {}).get("prompt_cycle") or {}
        full_thread_window = (full_turn.source_ref or {}).get("trace_window") or (full_turn.source_ref or {}).get("full_thread") or {}
        is_complete = turn.is_complete if complete_override is None else complete_override
        subagent_deployments = _subagent_deployments_for_turn(turn, limit=6)
        estimate_title = _prompt_title_from_text(turn.prompt_text) or f"{turn.provider} turn {turn.turn_index}"
        summary = {
            "turn_index": turn.turn_index,
            "turn_id": turn.turn_id,
            "completed_at": turn.completed_at,
            "started_at": turn.started_at,
            "last_event_at": _turn_last_event_at(turn),
            "tool_count": len(turn.tool_events),
            "error_count": sum(1 for e in turn.tool_events if e.is_error),
            "prompt_sha16": turn.prompt_sha256_16,
            "prompt_char_count": turn.prompt_char_count,
            "prompt_word_count": _prompt_word_count(turn.prompt_text),
            "prompt_title": _prompt_title_from_text(turn.prompt_text),
            "prompt_preview": (turn.prompt_text or "").strip()[:90],
            "subagent_count": len(subagent_deployments),
            "subagent_deployments": subagent_deployments,
            "trace_window": trace_window,
            "trace_window_prompt_sha16": trace_window.get("prompt_sha16") or turn.prompt_sha256_16,
            "trace_window_turn_count": trace_window.get("turn_count") or 1,
            "trace_window_tool_count": len(cycle_turn.tool_events),
            "trace_window_error_count": sum(1 for e in cycle_turn.tool_events if e.is_error),
            "full_thread_trace_window": full_thread_window,
            "full_thread_prompt_sha16": full_thread_window.get("prompt_sha16") or turn.prompt_sha256_16,
            "full_thread_turn_count": full_thread_window.get("turn_count") or 1,
            "full_thread_tool_count": len(full_turn.tool_events),
            "full_thread_error_count": sum(1 for e in full_turn.tool_events if e.is_error),
            "trace_variant_size_estimates": _trace_variant_size_estimates(
                turn,
                cycle_turn=cycle_turn,
                full_turn=full_turn,
                title=estimate_title,
                include_prompt_body=True,
            ),
            "is_complete": bool(is_complete),
        }
        if not is_complete:
            summary["status"] = "in_flight"
            summary["partial_reason"] = turn.partial_reason or "turn in progress"
        return summary

    out: dict = {}
    if latest_completed is not None:
        out["latest_completed_turn"] = _summarize_trace_turn(latest_completed, complete_override=True)
    completed_summary = out.get("latest_completed_turn") or {}
    active_summary: dict = {}
    if latest_active is not None and latest_active is not latest_completed:
        active_summary = _summarize_trace_turn(latest_active, complete_override=False)
    if _active_turn_is_preferred(active_summary, completed_summary):
        out["active_turn"] = active_summary
        out["preferred_trace_turn"] = active_summary
    elif completed_summary:
        if active_summary:
            out["stale_active_turn"] = active_summary
            out["active_turn_stale"] = True
        out["preferred_trace_turn"] = completed_summary
    elif active_summary:
        out["active_turn"] = active_summary
        out["preferred_trace_turn"] = active_summary
    if provider == "claude_code":
        sidechains = _claude_subagent_sidechain_summaries(session_file)
    elif provider == "codex":
        parent_session_id = turns[0].session_id if turns else _peek_codex_session_id(session_file)
        sidechains = _codex_subagent_sidechain_summaries(parent_session_id)
    else:
        sidechains = []
    subagent_packet = _subagent_deployment_packet(turns, sidechains=sidechains)
    if subagent_packet.get("count"):
        out["subagent_deployments"] = subagent_packet["deployments"]
        out["subagent_summary"] = {
            "count": subagent_packet["count"],
            "latest_label": subagent_packet.get("latest_label") or "",
            "models": subagent_packet.get("models") or [],
            "linked_trace_count": subagent_packet.get("linked_trace_count") or 0,
            "visible_count": subagent_packet.get("visible_count") or len(subagent_packet["deployments"]),
        }
    if sidechains:
        out["subagent_sidechains"] = sidechains[:24]
    out["turn_count"] = len(turns)
    out["completed_turn_count"] = sum(1 for turn in turns if turn.is_complete)
    out["active_turn_count"] = sum(1 for turn in turns if not turn.is_complete)
    out["latest_turn_index"] = turns[-1].turn_index if turns else None
    out["latest_turn_is_complete"] = bool(turns[-1].is_complete) if turns else None
    out["source_last_event_at"] = _summary_last_activity_at(out)
    return out or None


def _turn_activity_sort_value(turn: dict | None) -> tuple[str, int]:
    if not turn:
        return ("", -1)
    timestamp = str(turn.get("completed_at") or turn.get("started_at") or "")
    try:
        turn_index = int(turn.get("turn_index") or -1)
    except (TypeError, ValueError):
        turn_index = -1
    return (timestamp, turn_index)


def _active_turn_is_preferred(active_turn: dict | None, completed_turn: dict | None) -> bool:
    """Choose an active partial only when it is the newest meaningful episode."""
    if not active_turn:
        return False
    if int(active_turn.get("trace_window_tool_count") or active_turn.get("tool_count") or 0) <= 0:
        return False
    if not completed_turn:
        return True
    return _turn_activity_sort_value(active_turn) > _turn_activity_sort_value(completed_turn)


def _turn_last_event_at(turn: Turn) -> str:
    values: list[object] = [turn.started_at, turn.completed_at]
    values.extend(event.started_at for event in turn.tool_events)
    values.extend(event.completed_at for event in turn.tool_events)
    values.extend(event.timestamp for event in turn.assistant_events)
    return _latest_iso_timestamp(*values)


def _summary_last_activity_at(summary: dict | None) -> str:
    if not isinstance(summary, dict):
        return ""
    values: list[object] = []
    for key in ("active_turn", "stale_active_turn", "preferred_trace_turn", "latest_completed_turn"):
        turn = summary.get(key)
        if not isinstance(turn, dict):
            continue
        values.extend([
            turn.get("last_event_at"),
            turn.get("completed_at"),
            turn.get("started_at"),
        ])
    return _latest_iso_timestamp(*values)


MISSION_SUMMARY_CACHE_SCHEMA = "agent_trace_structurer_mission_summary_cache_v7"
MISSION_SUMMARY_CACHE_LEGACY_SCHEMAS = (
    "agent_trace_structurer_mission_summary_cache_v6",
    "agent_trace_structurer_mission_summary_cache_v5",
    "agent_trace_structurer_mission_summary_cache_v4",
    "agent_trace_structurer_mission_summary_cache_v3",
    "agent_trace_structurer_mission_summary_cache_v2",
)
MISSION_INDEX_DEFAULT_LIMIT = 120
MISSION_INDEX_CODEX_TITLE_RECORD_SCAN_LIMIT = 240
MISSION_INDEX_STALE_REPARSE_BUDGET = 8
MISSION_INDEX_RECENT_STALE_OVERSIZE_REPARSE_BUDGET = 2
MISSION_INDEX_WORKBAR_STALE_REPARSE_BUDGET = 0
MISSION_INDEX_WORKBAR_RECENT_STALE_OVERSIZE_REPARSE_BUDGET = 0
MISSION_INDEX_RECENT_STALE_REPARSE_SECONDS = 25 * 60
MISSION_INDEX_STALE_REPARSE_MAX_BYTES = 2 * 1024 * 1024
MISSION_INDEX_RECENT_STALE_REPARSE_MAX_BYTES = 32 * 1024 * 1024


def _mission_summary_cache_key(provider: str, session_id: str, session_file: Path) -> str:
    return f"{MISSION_SUMMARY_CACHE_SCHEMA}:{provider}:{session_id}:{_sha16(str(session_file))}"


def _mission_summary_cache_candidate_keys(provider: str, session_id: str, session_file: Path) -> list[str]:
    file_hash = _sha16(str(session_file))
    keys = [_mission_summary_cache_key(provider, session_id, session_file)]
    keys.extend(f"{schema}:{provider}:{session_id}:{file_hash}" for schema in MISSION_SUMMARY_CACHE_LEGACY_SCHEMAS)
    keys.append(f"{provider}:{session_id}:{file_hash}")
    return keys


def _session_file_meta(provider: str, session_id: str, session_file: Path, row: dict | None = None) -> dict:
    row = row or {}
    mtime_ns = row.get("mtime_ns")
    size_bytes = row.get("size_bytes")
    mtime_epoch = row.get("mtime_epoch")
    tail_sha16 = row.get("tail_sha16")
    if mtime_ns is None or size_bytes is None or mtime_epoch is None:
        try:
            stat = session_file.stat()
            if mtime_ns is None:
                mtime_ns = stat.st_mtime_ns
            if size_bytes is None:
                size_bytes = stat.st_size
            if mtime_epoch is None:
                mtime_epoch = stat.st_mtime
        except Exception:
            pass
    if tail_sha16 is None and session_file.exists():
        tail_sha16 = _file_tail_sha16(session_file)
    return {
        "provider": provider,
        "session_id": session_id,
        "session_file": str(session_file),
        "mtime_ns": int(mtime_ns or 0),
        "mtime_epoch": float(mtime_epoch or 0),
        "size_bytes": int(size_bytes or 0),
        "tail_sha16": str(tail_sha16 or ""),
    }


def _source_watermark_from_meta(meta: dict, *, summary: dict | None = None) -> dict:
    session_file = str(meta.get("session_file") or "")
    mtime_ns = int(meta.get("mtime_ns") or 0)
    size_bytes = int(meta.get("size_bytes") or 0)
    try:
        mtime_epoch = float(meta.get("mtime_epoch") or 0)
    except (TypeError, ValueError):
        mtime_epoch = 0.0
    tail_sha16 = str(meta.get("tail_sha16") or "")
    if not tail_sha16 and session_file:
        tail_sha16 = _file_tail_sha16(Path(session_file))
    mtime_ms = int(mtime_ns / 1_000_000) if mtime_ns > 0 else None
    watermark = {
        "schema_version": "agent_trace_source_watermark_v1",
        "provider": str(meta.get("provider") or ""),
        "session_id": str(meta.get("session_id") or ""),
        "session_file": session_file,
        "path_exists": bool(session_file and Path(session_file).exists()),
        "mtime_ns": mtime_ns,
        "mtime_ms": mtime_ms,
        "mtime_utc": _iso_from_epoch(mtime_epoch) if mtime_epoch > 0 else "",
        "size_bytes": size_bytes,
        "tail_sha16": tail_sha16,
    }
    fingerprint_parts = [
        watermark["provider"],
        watermark["session_id"],
        session_file,
        str(mtime_ns),
        str(size_bytes),
        tail_sha16,
    ]
    watermark["watermark_id"] = _sha16("|".join(fingerprint_parts))
    if isinstance(summary, dict):
        latest_turn_index = summary.get("latest_turn_index") or _mission_summary_latest_turn_index(summary)
        if latest_turn_index is not None:
            watermark["latest_turn_index"] = latest_turn_index
        completed_turn_count = summary.get("completed_turn_count")
        if completed_turn_count is not None:
            watermark["completed_turn_count"] = completed_turn_count
        turn_count = summary.get("turn_count")
        if turn_count is not None:
            watermark["turn_count"] = turn_count
    return watermark


def _source_watermark_for_turn(turn: Turn) -> dict:
    meta = _session_file_meta(turn.provider, turn.session_id, Path(turn.session_file))
    summary = {
        "latest_turn_index": turn.turn_index,
        "turn_count": turn.turn_index,
        "completed_turn_count": turn.turn_index if turn.is_complete else max(0, turn.turn_index - 1),
    }
    watermark = _source_watermark_from_meta(meta, summary=summary)
    watermark["selected_turn_index"] = turn.turn_index
    watermark["selected_prompt_sha16"] = turn.prompt_sha256_16
    watermark["selected_turn_complete"] = bool(turn.is_complete)
    if turn.completed_at:
        watermark["selected_completed_at"] = turn.completed_at
    return watermark


def _mission_source_recently_changed(meta: dict, *, now_epoch: float | None = None) -> bool:
    try:
        mtime_epoch = float(meta.get("mtime_epoch") or 0)
    except (TypeError, ValueError):
        return False
    if mtime_epoch <= 0:
        return False
    now = time.time() if now_epoch is None else now_epoch
    return 0 <= now - mtime_epoch <= MISSION_INDEX_RECENT_STALE_REPARSE_SECONDS


def _load_mission_summary_cache() -> dict:
    if not TRACE_STRUCTURER_MISSION_SUMMARY_CACHE.is_file():
        return {"schema": MISSION_SUMMARY_CACHE_SCHEMA, "entries": {}}
    try:
        data = json.loads(TRACE_STRUCTURER_MISSION_SUMMARY_CACHE.read_text() or "{}")
        if isinstance(data, dict):
            entries = data.get("entries")
            if isinstance(entries, dict):
                return {"schema": MISSION_SUMMARY_CACHE_SCHEMA, "entries": entries}
    except Exception:
        pass
    return {"schema": MISSION_SUMMARY_CACHE_SCHEMA, "entries": {}}


def _mission_summary_cache_lookup(
    cache: dict,
    meta: dict,
    *,
    allow_stale_summary: bool = False,
) -> tuple[dict | None, str]:
    entries = cache.get("entries") or {}
    current_key = _mission_summary_cache_key(meta["provider"], meta["session_id"], Path(meta["session_file"]))
    stale_seen = False
    for key in _mission_summary_cache_candidate_keys(meta["provider"], meta["session_id"], Path(meta["session_file"])):
        entry = entries.get(key)
        if not isinstance(entry, dict):
            continue
        source = entry.get("source") or {}
        same = (
            source.get("provider") == meta["provider"]
            and source.get("session_id") == meta["session_id"]
            and source.get("session_file") == meta["session_file"]
            and int(source.get("mtime_ns") or 0) == int(meta.get("mtime_ns") or 0)
            and int(source.get("size_bytes") or 0) == int(meta.get("size_bytes") or 0)
        )
        if not same:
            summary = entry.get("summary")
            same_identity = (
                source.get("provider") == meta["provider"]
                and source.get("session_id") == meta["session_id"]
                and source.get("session_file") == meta["session_file"]
            )
            if allow_stale_summary and same_identity and isinstance(summary, dict):
                stale_summary = json.loads(json.dumps(summary))
                stale_summary["cache_state"] = "soft_stale"
                stale_summary["cache_source_mtime_ns"] = source.get("mtime_ns")
                stale_summary["cache_source_mtime_epoch"] = source.get("mtime_epoch")
                stale_summary["cache_source_size_bytes"] = source.get("size_bytes")
                stale_summary["cache_source_tail_sha16"] = source.get("tail_sha16") or ""
                stale_summary["cache_source_watermark"] = _source_watermark_from_meta(source, summary=summary)
                stale_summary["cache_current_mtime_ns"] = meta.get("mtime_ns")
                stale_summary["cache_current_size_bytes"] = meta.get("size_bytes")
                return stale_summary, "soft_stale_hit"
            stale_seen = True
            continue
        summary = entry.get("summary")
        if isinstance(summary, dict):
            now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            entry["last_used_at"] = now
            if key != current_key:
                entries[current_key] = {
                    "source": meta,
                    "summary": summary,
                    "updated_at": entry.get("updated_at") or now,
                    "last_used_at": now,
                    "migrated_from": key,
                }
                return summary, "legacy_hit"
            return summary, "hit"
    if stale_seen:
        return None, "stale"
    return None, "miss"


def _mission_summary_cache_store(cache: dict, meta: dict, summary: dict) -> None:
    entries = cache.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        cache["entries"] = entries
    key = _mission_summary_cache_key(meta["provider"], meta["session_id"], Path(meta["session_file"]))
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    entries[key] = {
        "source": meta,
        "summary": summary,
        "updated_at": now,
        "last_used_at": now,
    }


def _summary_turn_is_active(turn: dict | None) -> bool:
    if not isinstance(turn, dict):
        return False
    return turn.get("status") == "in_flight" or turn.get("is_complete") is False


def _mission_summary_has_active_turn(summary: dict | None) -> bool:
    if not isinstance(summary, dict):
        return False
    return _summary_turn_is_active(summary.get("active_turn")) or _summary_turn_is_active(summary.get("preferred_trace_turn"))


def _downgrade_soft_stale_active_summary(summary: dict) -> dict:
    """Keep stale completed metadata, but never project stale active_turn as live."""
    downgraded = json.loads(json.dumps(summary))
    active_turn = downgraded.pop("active_turn", None)
    preferred = downgraded.get("preferred_trace_turn")
    stale_turn = active_turn if _summary_turn_is_active(active_turn) else preferred
    if stale_turn:
        downgraded["stale_active_turn"] = stale_turn
    latest_completed = downgraded.get("latest_completed_turn")
    if _summary_turn_is_active(preferred):
        if latest_completed:
            downgraded["preferred_trace_turn"] = latest_completed
        else:
            downgraded.pop("preferred_trace_turn", None)
    downgraded["active_turn_stale"] = True
    downgraded["cache_state"] = "soft_stale_active_downgraded"
    return downgraded


def _mission_summary_turn_count_hint(summary: dict | None) -> int | None:
    if not isinstance(summary, dict):
        return None
    values: list[object] = [
        summary.get("turn_count"),
        summary.get("completed_turn_count"),
    ]
    for key in ("preferred_trace_turn", "latest_completed_turn", "active_turn", "stale_active_turn"):
        turn = summary.get(key)
        if not isinstance(turn, dict):
            continue
        values.extend([
            turn.get("full_thread_turn_count"),
            (turn.get("full_thread_trace_window") or {}).get("turn_count") if isinstance(turn.get("full_thread_trace_window"), dict) else None,
            (turn.get("trace_window") or {}).get("turn_count") if isinstance(turn.get("trace_window"), dict) else None,
            turn.get("turn_index"),
        ])
    counts: list[int] = []
    for value in values:
        try:
            n = int(value or 0)
        except (TypeError, ValueError):
            continue
        if n > 0:
            counts.append(n)
    return max(counts) if counts else None


def _mission_summary_latest_turn_index(summary: dict | None) -> int | None:
    if not isinstance(summary, dict):
        return None
    values: list[object] = [summary.get("latest_turn_index")]
    for key in ("preferred_trace_turn", "latest_completed_turn", "active_turn", "stale_active_turn"):
        turn = summary.get(key)
        if isinstance(turn, dict):
            values.append(turn.get("turn_index"))
            window = turn.get("full_thread_trace_window")
            if isinstance(window, dict):
                values.append(window.get("end_turn_index"))
    indices: list[int] = []
    for value in values:
        try:
            n = int(value or 0)
        except (TypeError, ValueError):
            continue
        if n > 0:
            indices.append(n)
    return max(indices) if indices else None


def _mission_source_freshness_fact(meta: dict, summary: dict | None, cache_state: str) -> dict:
    summary = summary or {}
    cache_state = str(summary.get("cache_state") or cache_state or "unknown")
    stale_cache = (
        cache_state in {"stale", "soft_stale", "soft_stale_hit", "recent_stale_deferred"}
        or cache_state.startswith("soft_stale_")
        or cache_state.endswith("_deferred")
    )
    current_mtime_ns = int(meta.get("mtime_ns") or 0)
    current_size = int(meta.get("size_bytes") or 0)
    try:
        current_mtime_epoch = float(meta.get("mtime_epoch") or 0)
    except (TypeError, ValueError):
        current_mtime_epoch = 0.0
    current_mtime_utc = _iso_from_epoch(current_mtime_epoch) if current_mtime_epoch > 0 else ""
    current_mtime_ms = int(current_mtime_ns / 1_000_000) if current_mtime_ns > 0 else None
    index_mtime_ns = int(summary.get("cache_source_mtime_ns") or current_mtime_ns)
    try:
        index_mtime_epoch = float(summary.get("cache_source_mtime_epoch") or current_mtime_epoch)
    except (TypeError, ValueError):
        index_mtime_epoch = current_mtime_epoch
    index_size = int(summary.get("cache_source_size_bytes") or current_size)
    index_tail_sha16 = str(summary.get("cache_source_tail_sha16") or meta.get("tail_sha16") or "")
    state = "source_newer_than_index" if stale_cache else "current"
    if meta.get("session_file") and not Path(str(meta.get("session_file"))).exists():
        state = "source_missing"
    current_watermark = _source_watermark_from_meta(meta, summary=None if stale_cache else summary)
    index_watermark = summary.get("cache_source_watermark")
    if not isinstance(index_watermark, dict):
        index_meta = {
            **meta,
            "mtime_ns": index_mtime_ns,
            "mtime_epoch": index_mtime_epoch,
            "size_bytes": index_size,
            "tail_sha16": index_tail_sha16,
        }
        index_watermark = _source_watermark_from_meta(index_meta, summary=summary)
    summary_turn_count = _mission_summary_turn_count_hint(summary)
    current_turn_count = None if stale_cache else summary_turn_count
    current_completed_turn_count = None if stale_cache else (summary.get("completed_turn_count") or summary_turn_count)
    current_latest_turn_index = None if stale_cache else (summary.get("latest_turn_index") or _mission_summary_latest_turn_index(summary))
    summary_last_event_at = summary.get("source_last_event_at") or _summary_last_activity_at(summary)
    source_last_event_at = (
        _latest_iso_timestamp(summary_last_event_at, current_mtime_utc)
        if stale_cache
        else summary_last_event_at
    )
    return {
        "schema_version": "agent_trace_mission_source_freshness_v1",
        "state": state,
        "reason": cache_state,
        "cache_state": cache_state,
        "current_mtime_ns": current_mtime_ns,
        "current_mtime_ms": current_mtime_ms,
        "current_mtime_utc": current_mtime_utc,
        "index_mtime_ns": index_mtime_ns,
        "current_size_bytes": current_size,
        "index_size_bytes": index_size,
        "source_watermark": current_watermark,
        "current_source_watermark": current_watermark,
        "index_source_watermark": index_watermark,
        "current_turn_count": current_turn_count,
        "current_completed_turn_count": current_completed_turn_count,
        "current_latest_turn_index": current_latest_turn_index,
        "index_turn_count": summary.get("cache_turn_count") or summary_turn_count,
        "source_last_event_at": source_last_event_at,
        "requires_refresh_before_copy": state in {"source_newer_than_index", "source_size_changed", "source_missing"},
    }


def _write_mission_summary_cache(cache: dict, *, max_entries: int = 200) -> None:
    try:
        entries = cache.get("entries") or {}
        if isinstance(entries, dict) and len(entries) > max_entries:
            ranked = sorted(
                entries.items(),
                key=lambda item: str((item[1] or {}).get("last_used_at") or (item[1] or {}).get("updated_at") or ""),
                reverse=True,
            )
            cache["entries"] = dict(ranked[:max_entries])
        cache["schema"] = MISSION_SUMMARY_CACHE_SCHEMA
        TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
        tmp = TRACE_STRUCTURER_MISSION_SUMMARY_CACHE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(TRACE_STRUCTURER_MISSION_SUMMARY_CACHE)
    except Exception:
        pass


def _source_watermark_id(watermark: dict | None) -> str:
    if not isinstance(watermark, dict):
        return ""
    explicit = str(watermark.get("watermark_id") or "")
    if explicit:
        return explicit
    parts = [
        str(watermark.get("provider") or ""),
        str(watermark.get("session_id") or ""),
        str(watermark.get("session_file") or ""),
        str(watermark.get("mtime_ns") or ""),
        str(watermark.get("size_bytes") or ""),
        str(watermark.get("tail_sha16") or ""),
    ]
    if not any(parts):
        return ""
    return _sha16("|".join(parts))


def _classify_artifact_freshness(
    latest_completed_turn: dict | None,
    latest_clip_meta: dict,
    source_freshness: dict | None = None,
) -> dict:
    """Compare the latest completed turn against the most recent
    cli_prompt_trace clip for this session.

    Returns {state: current|stale|missing|partial_only, reason: ...}."""
    if latest_completed_turn is None:
        return {"state": "partial_only", "reason": "no_completed_turn_in_session"}
    if not latest_clip_meta:
        return {"state": "missing", "reason": "no_artifact"}
    clip_watermark = latest_clip_meta.get("source_watermark") if isinstance(latest_clip_meta, dict) else None
    current_watermark = None
    if isinstance(source_freshness, dict):
        current_watermark = (
            source_freshness.get("current_source_watermark")
            or source_freshness.get("source_watermark")
        )
    clip_watermark_id = _source_watermark_id(clip_watermark)
    current_watermark_id = _source_watermark_id(current_watermark)
    if clip_watermark_id and current_watermark_id and clip_watermark_id != current_watermark_id:
        return {
            "state": "stale",
            "reason": "source_watermark_mismatch",
            "clip_source_watermark_id": clip_watermark_id,
            "current_source_watermark_id": current_watermark_id,
        }
    clip_sha = latest_clip_meta.get("prompt_sha16") or ""
    completed_sha = latest_completed_turn.get("prompt_sha16") or ""
    clip_turn = latest_clip_meta.get("turn_index")
    completed_turn = latest_completed_turn.get("turn_index")
    if clip_sha and completed_sha and clip_sha == completed_sha and clip_turn == completed_turn:
        return {"state": "current", "reason": "artifact_turn_matches_latest_completed"}
    if clip_turn is not None and completed_turn is not None and clip_turn < completed_turn:
        return {"state": "stale", "reason": "artifact_turn_older_than_latest"}
    if clip_sha and completed_sha and clip_sha != completed_sha:
        return {"state": "stale", "reason": "prompt_hash_mismatch"}
    return {"state": "stale", "reason": "artifact_metadata_incomplete"}


def _short_label_for(title: str, provider: str, session_id: str) -> str:
    """Compact chip label: numeric pair prefix when present, else first words."""
    t = (title or "").strip()
    if not t:
        return (session_id[:6] if session_id else (provider or "?")[:6])
    m = re.match(r"^\s*(\d+\s*[,/]\s*\d+)\b", t)
    if m:
        return m.group(1).replace(" ", "")
    words = re.findall(r"[A-Za-z0-9]+", t)
    if words:
        return " ".join(words[:2])[:12]
    return t[:12]


def _latest_clipboard_entry_for(session_id: str) -> dict | None:
    """Find the most recent clipboard_history row produced by cli_prompt_trace
    for the given session id, by scanning the entries directly. Used to expose
    artifact_refs to the System Bar without re-running the trace compiler."""
    if not TRACE_STRUCTURER_HISTORY.is_file():
        return None
    try:
        data = json.loads(TRACE_STRUCTURER_HISTORY.read_text() or "[]")
        if not isinstance(data, list):
            return None
    except Exception:
        return None
    for row in data:
        if not isinstance(row, dict):
            continue
        cpt = row.get("cli_prompt_trace") or {}
        if cpt.get("session_id") == session_id:
            return row
    return None


def _mission_index_timestamp_ms(value: object) -> int | None:
    if isinstance(value, (int, float)):
        # Desktop metadata can be epoch-ms; tolerate epoch-seconds as well.
        return int(value if value > 10_000_000_000 else value * 1000)
    return _iso_timestamp_ms(value)


def _mission_index_activity_time(row: dict) -> int:
    """Sort timestamp for the mission cockpit.

    Active turn recency and finished-turn recency are the primary row order.
    Goal priority is a tie-breaker only; it must not hide a newer active or
    finished thread behind an older goal row.
    """
    primary_values = [
        (row.get("active_turn") or {}).get("started_at"),
        (row.get("latest_completed_turn") or {}).get("completed_at"),
        row.get("last_activity_at"),
    ]
    primary_timestamps = [_mission_index_timestamp_ms(value) for value in primary_values]
    primary = max((ts for ts in primary_timestamps if ts is not None), default=None)
    if primary is not None:
        return primary
    return _mission_index_timestamp_ms(row.get("mtime_utc")) or 0


def _mission_index_row_is_active(row: dict) -> bool:
    if str(row.get("goal_status") or "").lower() == "active":
        return True
    goal = row.get("goal") if isinstance(row.get("goal"), dict) else {}
    if str(goal.get("status") or "").lower() == "active":
        return True
    return _summary_turn_is_active(row.get("active_turn")) or _summary_turn_is_active(row.get("preferred_trace_turn"))


def _mission_index_goal_priority(row: dict) -> int:
    try:
        return int(row.get("goal_sort_priority") or 0)
    except Exception:
        return 0


def _mission_index_ordinal(row: dict) -> int:
    try:
        return int(row.get("mission_ordinal_key") or 0)
    except Exception:
        return 0


def _sort_mission_index_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: (
            1 if _mission_index_row_is_active(r) else 0,
            _mission_index_activity_time(r),
            _mission_index_goal_priority(r),
            _mission_index_ordinal(r),
        ),
        reverse=True,
    )


def _codex_session_candidate_for_thread_id(thread_id: str, *, cwd: Path | None = None) -> dict | None:
    if not thread_id or not CODEX_SESSIONS_ROOT.is_dir():
        return None
    try:
        matches = sorted(
            CODEX_SESSIONS_ROOT.glob(f"**/*{thread_id}*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return None
    for path in matches:
        try:
            stat = path.stat()
        except Exception:
            continue
        meta = _peek_codex_session_meta(path)
        if cwd is not None:
            meta_cwd = str(meta.get("cwd") or "")
            if meta_cwd and meta_cwd != str(cwd):
                continue
        return {
            "provider": "codex",
            "session_file": str(path),
            "session_id": str(meta.get("id") or thread_id),
            "thread_source": meta.get("thread_source") or "",
            "forked_from_id": meta.get("forked_from_id") or "",
            "parent_thread_id": meta.get("parent_thread_id") or "",
            "agent_nickname": meta.get("agent_nickname") or "",
            "agent_role": meta.get("agent_role") or "",
            "mtime_epoch": stat.st_mtime,
            "mtime_ns": stat.st_mtime_ns,
            "mtime_utc": _iso_from_epoch(stat.st_mtime),
            "size_bytes": stat.st_size,
        }
    return None


def _codex_goal_session_candidate(thread_id: str) -> dict | None:
    candidate = _codex_session_candidate_for_thread_id(thread_id)
    if candidate:
        candidate["mission_index_forced_goal_thread"] = True
    return candidate


def _ensure_active_goal_candidates(candidates: list[dict], goals: dict[str, dict]) -> list[dict]:
    """Keep active Codex goal threads in the mission list even outside recency."""
    seen = {
        str(row.get("session_id") or "")
        for row in candidates
        if row.get("provider") == "codex" and row.get("session_id")
    }
    forced: list[dict] = []
    for thread_id, goal in goals.items():
        if str((goal or {}).get("status") or "").lower() != "active":
            continue
        if thread_id in seen:
            continue
        candidate = _codex_goal_session_candidate(thread_id)
        if not candidate:
            continue
        forced.append(candidate)
        seen.add(thread_id)
    return forced + candidates


def _ensure_codex_title_record_candidates(
    candidates: list[dict],
    codex_thread_records: dict[str, dict],
    *,
    cwd: Path,
    scan_limit: int = MISSION_INDEX_CODEX_TITLE_RECORD_SCAN_LIMIT,
) -> list[dict]:
    """Keep Codex-sidebar-visible titled threads reachable in the mission list.

    Normal mission rows are sourced from provider rollout files. Codex also
    maintains a title authority sidecar, and the sidebar can show a thread title
    whose rollout file missed the bounded recent-session scan. Backfill only
    title records that can be joined back to a local Codex rollout file, so the
    row remains a real provider-thread row rather than a free-floating title.
    """
    seen = {
        str(row.get("session_id") or "")
        for row in candidates
        if row.get("provider") == "codex" and row.get("session_id")
    }
    records = sorted(
        [
            (str(thread_id), rec)
            for thread_id, rec in (codex_thread_records or {}).items()
            if thread_id and isinstance(rec, dict) and str(rec.get("thread_name") or "").strip()
        ],
        key=lambda item: _iso_mtime_ms(str((item[1] or {}).get("updated_at") or "")) or 0,
        reverse=True,
    )
    forced: list[dict] = []
    for thread_id, rec in records[: max(0, scan_limit)]:
        if thread_id in seen:
            continue
        candidate = _codex_session_candidate_for_thread_id(thread_id, cwd=cwd)
        if not candidate:
            continue
        candidate["mission_index_forced_codex_title_record"] = True
        title_updated_at = str(rec.get("updated_at") or "")
        candidate["title_record_updated_at"] = title_updated_at
        title_updated_ms = _iso_mtime_ms(title_updated_at)
        if (
            title_updated_ms is not None
            and (title_updated_ms / 1000.0) > float(candidate.get("mtime_epoch") or 0)
        ):
            candidate["mtime_epoch"] = title_updated_ms / 1000.0
            candidate["mtime_utc"] = _iso_from_epoch_ms(title_updated_ms)
        forced.append(candidate)
        seen.add(thread_id)
    return sorted(
        forced + candidates,
        key=lambda row: float(row.get("mtime_epoch") or 0),
        reverse=True,
    )


def _candidate_parent_session_id(candidate: dict) -> str:
    return str(
        candidate.get("parent_thread_id")
        or candidate.get("forked_from_id")
        or ""
    ).strip()


def _thread_title_for_session(
    provider: str,
    session_id: str,
    *,
    codex_thread_records: dict[str, dict],
    title_aliases: dict[str, str],
    claude_desktop_titles: dict[str, dict],
) -> str:
    alias = title_aliases.get(f"{provider}:{session_id}", "")
    if alias:
        return str(alias)
    if provider == "codex":
        return str((codex_thread_records.get(session_id) or {}).get("thread_name") or "")
    if provider == "claude_code":
        return str((claude_desktop_titles.get(session_id) or {}).get("title") or "")
    return ""


def _candidate_thread_relationship_fact(
    candidate: dict,
    *,
    codex_thread_records: dict[str, dict],
    title_aliases: dict[str, str],
    claude_desktop_titles: dict[str, dict],
) -> dict:
    provider = str(candidate.get("provider") or "")
    parent_session_id = _candidate_parent_session_id(candidate)
    thread_source = str(candidate.get("thread_source") or "")
    if not parent_session_id:
        return {
            "schema": "agent_trace_thread_relationship_v1",
            "kind": "standalone_thread",
            "thread_source": thread_source or "direct",
            "parent_session_id": "",
            "parent_title": "",
            "selectable_child_trace": False,
        }
    child_kind = "codex_child_thread" if provider == "codex" else "child_thread"
    parent_title = _thread_title_for_session(
        provider,
        parent_session_id,
        codex_thread_records=codex_thread_records,
        title_aliases=title_aliases,
        claude_desktop_titles=claude_desktop_titles,
    )
    return {
        "schema": "agent_trace_thread_relationship_v1",
        "kind": child_kind,
        "thread_source": thread_source or "child",
        "parent_session_id": parent_session_id,
        "parent_thread_id": parent_session_id,
        "parent_title": parent_title,
        "selectable_child_trace": True,
    }


def build_mission_index(
    *,
    cwd: Path | None = None,
    limit: int = MISSION_INDEX_DEFAULT_LIMIT,
    embed_variant_artifacts: bool = False,
    stale_reparse_budget: int | None = None,
    recent_stale_oversize_reparse_budget: int | None = None,
) -> dict:
    """Enumerate recent Claude + Codex sessions with title + status + artifact refs.

    Lightweight: resolves titles via the title ladder (operator_alias ->
    codex thread_name -> Claude desktop user title -> first-prompt preview),
    pulls last-activity from Claude desktop metadata when present, and joins
    the most recent matching clipboard_history row for artifact_refs. Full turn
    summaries are cached by session file identity so warm refreshes do not
    reparse unchanged multi-megabyte JSONL sessions.
    """
    started_perf = time.perf_counter()
    codex_thread_records = _load_codex_thread_title_records()
    codex_thread_names = {
        sid: str(rec.get("thread_name") or "")
        for sid, rec in codex_thread_records.items()
        if rec.get("thread_name")
    }
    title_aliases = _load_title_aliases()
    claude_desktop_titles = _load_claude_desktop_titles()
    codex_thread_goals = _load_codex_thread_goals()
    variant_index = _load_variant_artifact_index() if embed_variant_artifacts else {}
    title_authority = _title_authority_sources(claude_desktop_titles)
    goal_authority = _goal_authority_sources(codex_thread_goals)
    summary_cache = _load_mission_summary_cache()
    cache_stats = {
        "hits": 0,
        "legacy_hits": 0,
        "soft_stale_hits": 0,
        "misses": 0,
        "stale": 0,
        "recent_stale_forced": 0,
        "legacy_active_forced": 0,
        "skipped_archived": 0,
        "collapsed_codex_subagent_children": 0,
        "indexed_codex_subagent_children": 0,
        "forced_codex_title_records": 0,
        "stored": 0,
    }
    cache_dirty = False
    if stale_reparse_budget is None:
        stale_reparse_budget = MISSION_INDEX_STALE_REPARSE_BUDGET
    if recent_stale_oversize_reparse_budget is None:
        recent_stale_oversize_reparse_budget = MISSION_INDEX_RECENT_STALE_OVERSIZE_REPARSE_BUDGET
    stale_reparse_remaining = max(0, int(stale_reparse_budget))
    oversize_reparse_remaining = max(0, int(recent_stale_oversize_reparse_budget))
    rows: list[dict] = []
    candidates = _ensure_active_goal_candidates(
        _enumerate_candidates("auto", cwd or Path.cwd()),
        codex_thread_goals,
    )
    candidates = _ensure_codex_title_record_candidates(
        candidates,
        codex_thread_records,
        cwd=cwd or Path.cwd(),
    )
    for c in candidates:
        if len(rows) >= limit:
            break
        if c.get("mission_index_forced_codex_title_record"):
            cache_stats["forced_codex_title_records"] += 1
        if c.get("provider") == "codex" and (
            c.get("thread_source") == "subagent"
            or c.get("forked_from_id")
            or c.get("parent_thread_id")
        ):
            cache_stats["indexed_codex_subagent_children"] += 1
        title, title_source = _resolve_session_title(
            c["provider"], c["session_id"], Path(c["session_file"]),
            codex_thread_names=codex_thread_names,
            title_aliases=title_aliases,
            claude_desktop_titles=claude_desktop_titles,
        )
        short_label = _short_label_for(title, c["provider"], c["session_id"])
        last_clip = _latest_clipboard_entry_for(c["session_id"])
        artifact_refs: dict = {}
        last_clip_meta: dict = {}
        if last_clip:
            artifact_refs = {
                "compressed": last_clip.get("clip_store_path") or "",
                "full": last_clip.get("raw_path") or "",
                "parsed": last_clip.get("stored_path") or "",
                "export": last_clip.get("path") or last_clip.get("download_path") or "",
            }
            cpt = last_clip.get("cli_prompt_trace") or {}
            last_clip_meta = {
                "captured_at": last_clip.get("captured_at") or "",
                "turn_index": cpt.get("turn_index"),
                "tool_count": cpt.get("tool_count") or last_clip.get("commands") or 0,
                "error_count": cpt.get("error_count") or 0,
                "is_complete": cpt.get("is_complete"),
                "trace_id": cpt.get("trace_id") or "",
                "source_watermark": (
                    cpt.get("copied_source_watermark")
                    or cpt.get("source_watermark")
                    or last_clip.get("copied_source_watermark")
                    or last_clip.get("source_watermark")
                    or {}
                ),
            }
        desktop = (claude_desktop_titles or {}).get(c["session_id"]) or {}
        # Parse session lazily — skip for archived rows (won't render anyway).
        completed_active: dict = {}
        session_path = Path(c["session_file"])
        source_meta = _session_file_meta(c["provider"], c["session_id"], session_path, c)
        source_freshness: dict = {}
        summary_cache_state = "skipped_archived" if desktop.get("is_archived") else "unknown"
        if not desktop.get("is_archived"):
            cached_summary, cache_state = _mission_summary_cache_lookup(summary_cache, source_meta)
            defer_stale_reparse = False
            if cache_state == "stale" and _mission_source_recently_changed(source_meta):
                source_size = int(source_meta.get("size_bytes") or 0)
                oversize_source = source_size > MISSION_INDEX_STALE_REPARSE_MAX_BYTES
                oversize_budget_available = (
                    not oversize_source or oversize_reparse_remaining > 0
                )
                if (
                    stale_reparse_remaining > 0
                    and source_size <= MISSION_INDEX_RECENT_STALE_REPARSE_MAX_BYTES
                    and oversize_budget_available
                ):
                    cache_stats["recent_stale_forced"] += 1
                    if oversize_source:
                        cache_stats["recent_stale_oversize_forced"] = cache_stats.get("recent_stale_oversize_forced", 0) + 1
                        oversize_reparse_remaining = max(0, oversize_reparse_remaining - 1)
                    stale_reparse_remaining = max(0, stale_reparse_remaining - 1)
                    cache_state = "recent_stale_forced"
                else:
                    cache_stats["recent_stale_deferred"] = cache_stats.get("recent_stale_deferred", 0) + 1
                    if source_size > MISSION_INDEX_RECENT_STALE_REPARSE_MAX_BYTES:
                        cache_stats["oversize_stale_deferred"] = cache_stats.get("oversize_stale_deferred", 0) + 1
                    elif oversize_source and oversize_reparse_remaining <= 0:
                        cache_stats["oversize_stale_deferred_budget"] = cache_stats.get("oversize_stale_deferred_budget", 0) + 1
                    defer_stale_reparse = True
            if cache_state == "stale" and (defer_stale_reparse or stale_reparse_remaining <= 0):
                soft_summary, soft_state = _mission_summary_cache_lookup(
                    summary_cache,
                    source_meta,
                    allow_stale_summary=True,
                )
                if soft_summary is not None:
                    cached_summary, cache_state = soft_summary, soft_state
            if cache_state == "hit":
                cache_stats["hits"] += 1
            elif cache_state == "legacy_hit":
                cache_dirty = True
                if _mission_summary_has_active_turn(cached_summary) or (cached_summary or {}).get("stale_active_turn"):
                    cached_summary = None
                    cache_state = "legacy_active_forced"
                    cache_stats["legacy_active_forced"] += 1
                else:
                    cache_stats["hits"] += 1
                    cache_stats["legacy_hits"] += 1
            elif cache_state == "soft_stale_hit":
                cache_stats["hits"] += 1
                cache_stats["soft_stale_hits"] += 1
                if _mission_summary_has_active_turn(cached_summary):
                    cached_summary = _downgrade_soft_stale_active_summary(cached_summary)
                    cache_stats["soft_stale_active_downgraded"] = cache_stats.get("soft_stale_active_downgraded", 0) + 1
            elif cache_state in ("stale", "recent_stale_forced", "legacy_active_forced"):
                cache_stats["stale"] += 1
                if cache_state == "stale":
                    stale_reparse_remaining = max(0, stale_reparse_remaining - 1)
            else:
                cache_stats["misses"] += 1
            if cached_summary is not None:
                completed_active = cached_summary
            else:
                completed_active = _latest_completed_turn_summary(
                    c["provider"], session_path
                ) or {}
                _mission_summary_cache_store(summary_cache, source_meta, completed_active)
                cache_stats["stored"] += 1
                cache_dirty = True
                if cache_state == "stale":
                    cache_state = "refreshed_stale"
                elif cache_state == "recent_stale_forced":
                    cache_state = "refreshed_recent_stale"
                elif cache_state == "legacy_active_forced":
                    cache_state = "refreshed_legacy_active"
                elif cache_state == "miss":
                    cache_state = "stored_miss"
            summary_cache_state = cache_state
        else:
            cache_stats["skipped_archived"] += 1
        source_freshness = _mission_source_freshness_fact(source_meta, completed_active, summary_cache_state)
        latest_completed = completed_active.get("latest_completed_turn")
        active_turn = completed_active.get("active_turn")
        stale_active_turn = completed_active.get("stale_active_turn")
        preferred_trace_turn = completed_active.get("preferred_trace_turn")
        trace_last_activity_at = _summary_last_activity_at(completed_active)
        desktop_last_activity_at = desktop.get("last_activity_at") or ""
        last_activity_at = _latest_iso_timestamp(
            trace_last_activity_at,
            desktop_last_activity_at,
            source_freshness.get("source_last_event_at") or "",
            c["mtime_utc"],
        )
        prompt_preview = ""
        for preview_turn in (preferred_trace_turn, active_turn, latest_completed):
            if isinstance(preview_turn, dict) and preview_turn.get("prompt_preview"):
                prompt_preview = str(preview_turn.get("prompt_preview") or "").strip()[:180]
                break
        if not title:
            for title_source_turn in (preferred_trace_turn, active_turn, latest_completed):
                if not isinstance(title_source_turn, dict):
                    continue
                fallback_title = (
                    title_source_turn.get("prompt_title")
                    or _prompt_title_from_text(str(title_source_turn.get("prompt_preview") or ""))
                )
                if fallback_title:
                    title = fallback_title
                    title_source = "trace_prompt_title"
                    break
        goal = codex_thread_goals.get(c["session_id"]) if c["provider"] == "codex" else None
        if goal and str(title or "").strip().lower() in _GOAL_TITLE_PLACEHOLDERS:
            goal_title = _compact_one_line(
                goal.get("objective_preview") or goal.get("objective") or "",
                limit=90,
            )
            if goal_title:
                title = goal_title
                title_source = "codex_goal_objective_preview"
        title_fact = _row_title_authority_fact(
            provider=c["provider"],
            session_id=c["session_id"],
            session_file=Path(c["session_file"]),
            title=title,
            title_source=title_source,
            title_aliases=title_aliases,
            codex_thread_records=codex_thread_records,
            claude_desktop_titles=claude_desktop_titles,
            prompt_preview=prompt_preview,
        )
        short_label = _short_label_for(title, c["provider"], c["session_id"])
        ord_start, ord_end, ord_source = _mission_ordinal(title)
        thread_relationship = _candidate_thread_relationship_fact(
            c,
            codex_thread_records=codex_thread_records,
            title_aliases=title_aliases,
            claude_desktop_titles=claude_desktop_titles,
        )
        # Enrich latest_clip_meta with prompt_sha16 from full row if present
        if last_clip:
            cpt_full = last_clip.get("cli_prompt_trace") or {}
            if "prompt_sha16" not in last_clip_meta and cpt_full.get("prompt_sha16"):
                last_clip_meta["prompt_sha16"] = cpt_full["prompt_sha16"]
            if "prompt_char_count" not in last_clip_meta and cpt_full.get("prompt_char_count"):
                last_clip_meta["prompt_char_count"] = cpt_full["prompt_char_count"]
        selected_trace_turn = preferred_trace_turn or latest_completed or stale_active_turn
        variant_artifacts = (
            _variant_artifacts_for_turn(
                variant_index,
                c["session_id"],
                selected_trace_turn,
            )
            if embed_variant_artifacts
            else {}
        )
        variant_trace_artifact = variant_artifacts.get("trace_capsule") if isinstance(variant_artifacts, dict) else {}
        variant_clip_meta: dict = {}
        if isinstance(variant_trace_artifact, dict) and variant_trace_artifact:
            variant_clip_meta = {
                "captured_at": variant_trace_artifact.get("generated_at") or "",
                "turn_index": variant_trace_artifact.get("turn_index"),
                "tool_count": (variant_trace_artifact.get("trace_counts") or {}).get("command_count") or 0,
                "error_count": (variant_trace_artifact.get("trace_window") or {}).get("error_count") or 0,
                "is_complete": True,
                "trace_id": variant_trace_artifact.get("sha16") or "",
                "source_watermark": (
                    variant_trace_artifact.get("copied_source_watermark")
                    or variant_trace_artifact.get("source_watermark")
                    or {}
                ),
                "prompt_sha16": variant_trace_artifact.get("prompt_sha16") or "",
                "prompt_char_count": variant_trace_artifact.get("prompt_char_count") or None,
            }
            artifact_refs.setdefault("trace_capsule", variant_trace_artifact.get("path") or "")
            artifact_refs.setdefault("trace_capsule_source", variant_trace_artifact.get("source_clip_path") or variant_trace_artifact.get("clip_path") or "")
        artifact_freshness = _classify_artifact_freshness(
            selected_trace_turn,
            variant_clip_meta or last_clip_meta,
            source_freshness,
        )
        goal_priority = _goal_sort_priority(goal)
        rows.append({
            "provider": c["provider"],
            "session_id": c["session_id"],
            "session_file": c["session_file"],
            "thread_source": c.get("thread_source") or "",
            "forked_from_id": c.get("forked_from_id") or "",
            "parent_thread_id": c.get("parent_thread_id") or "",
            "mission_index_forced_codex_title_record": bool(c.get("mission_index_forced_codex_title_record")),
            "mission_index_forced_goal_thread": bool(c.get("mission_index_forced_goal_thread")),
            "parent_session_id": thread_relationship.get("parent_session_id") or "",
            "agent_nickname": c.get("agent_nickname") or "",
            "agent_role": c.get("agent_role") or "",
            "thread_relationship": thread_relationship,
            "title": title,
            "display_title": title_fact["display_title"],
            "source_title": title_fact["source_title"],
            "operator_alias": title_fact["operator_alias"],
            "prompt_preview": title_fact["prompt_preview"],
            "title_authority": title_fact["title_authority"],
            "title_marker": title_fact["title_marker"],
            "source_title_version_ms": title_fact["source_title_version_ms"],
            "short_label": short_label,
            "title_source": title_source,
            "mtime_utc": c["mtime_utc"],
            "size_bytes": c["size_bytes"],
            "last_activity_at": last_activity_at,
            "completed_turns_hint": desktop.get("completed_turns") or 0,
            "turn_count_hint": _mission_summary_turn_count_hint(completed_active) or desktop.get("completed_turns") or 0,
            "completed_turn_count": completed_active.get("completed_turn_count") or _mission_summary_turn_count_hint(completed_active) or 0,
            "latest_turn_index": completed_active.get("latest_turn_index") or _mission_summary_latest_turn_index(completed_active),
            "source_last_event_at": completed_active.get("source_last_event_at") or "",
            "source_freshness": source_freshness,
            "is_archived": bool(desktop.get("is_archived")),
            "model": desktop.get("model") or "",
            "mission_ordinal_start": ord_start,
            "mission_ordinal_end": ord_end,
            "mission_ordinal_key": ord_end if ord_end is not None else (ord_start if ord_start is not None else None),
            "mission_sort_source": ord_source or "no_ordinal",
            "artifact_refs": artifact_refs,
            "variant_artifacts": variant_artifacts or None,
            "latest_clip": last_clip_meta,
            "latest_completed_turn": latest_completed,
            "active_turn": active_turn,
            "stale_active_turn": stale_active_turn,
            "active_turn_stale": bool(completed_active.get("active_turn_stale")),
            "preferred_trace_turn": preferred_trace_turn,
            "subagent_deployments": completed_active.get("subagent_deployments") or [],
            "subagent_summary": completed_active.get("subagent_summary") or {},
            "subagent_sidechains": completed_active.get("subagent_sidechains") or [],
            "artifact_freshness": artifact_freshness,
            "has_goal": bool(goal),
            "goal": goal or {},
            "goal_status": (goal or {}).get("status") or "",
            "goal_sort_priority": goal_priority,
            "goal_fleet_control": _goal_fleet_control(goal, "row_pending_activity_split") if goal else {},
            "trace_summary_cache_state": completed_active.get("cache_state") or summary_cache_state,
            "status": "archived" if desktop.get("is_archived") else "live",
        })
    # Operator rule: titles starting with "old" mark inactive missions. Split
    # so the chip rail can render active by default and keep history queryable.
    active_rows: list[dict] = []
    inactive_rows: list[dict] = []
    for r in rows:
        reason = None
        if r.get("is_archived"):
            reason = "archived"
        elif r.get("title_marker") == "old_prefix":
            reason = "operator_old_title_marker"
        elif not r.get("title"):
            reason = "no_title_resolved"
        if reason:
            r["inactive_reason"] = reason
            if reason == "operator_old_title_marker":
                retired_at_ms = r.get("source_title_version_ms") or _path_mtime_ms(Path(r.get("session_file") or ""))
                r["retirement"] = {
                    "retired_cause": "old_prefix",
                    "retired_at_ms": retired_at_ms,
                    "retired_title_version_ms": retired_at_ms,
                    "title_marker": "old_prefix",
                }
            inactive_rows.append(r)
        else:
            active_rows.append(r)
    _refresh_goal_fields_on_rows(rows, codex_thread_goals)
    active_rows = _sort_mission_index_rows(active_rows)
    inactive_rows = _sort_mission_index_rows(inactive_rows)
    mission_goal_count = sum(1 for r in rows if r.get("has_goal"))
    active_mission_goal_count = sum(1 for r in rows if (r.get("goal") or {}).get("status") == "active")
    goal_threads = _goal_thread_roster(codex_thread_goals, rows, codex_thread_records)
    active_goal_thread_count = sum(1 for g in goal_threads if g.get("status") == "active")
    goal_fleet_state = _goal_fleet_state(goal_threads, goal_authority)
    if cache_dirty:
        _write_mission_summary_cache(summary_cache)
    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    return {
        "schema": "prompt_trace_mission_index_v3",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "cwd": str(cwd or Path.cwd()),
        "row_count": len(rows),
        "active_count": len(active_rows),
        "inactive_count": len(inactive_rows),
        "hidden_old_count": sum(1 for r in inactive_rows if r.get("inactive_reason") == "operator_old_title_marker"),
        "ambiguity_window_seconds": SESSION_AMBIGUITY_WINDOW_SECONDS,
        "sort_mode": "review_first",
        "perf": {
            "duration_ms": duration_ms,
            "candidate_count": len(candidates),
            "summary_cache": cache_stats,
            "summary_cache_path": str(TRACE_STRUCTURER_MISSION_SUMMARY_CACHE),
            "stale_reparse_budget": max(0, int(stale_reparse_budget)),
            "recent_stale_oversize_reparse_budget": max(0, int(recent_stale_oversize_reparse_budget)),
            "variant_artifacts": {
                "embedding": "embedded" if embed_variant_artifacts else "omitted_for_workbar_latency",
                "index_path": str(TRACE_STRUCTURER_VARIANT_INDEX),
            },
        },
        "variant_artifact_embedding": "embedded" if embed_variant_artifacts else "omitted_for_workbar_latency",
        "variant_artifact_index_path": str(TRACE_STRUCTURER_VARIANT_INDEX),
        "title_authority": title_authority,
        "goal_authority": goal_authority,
        "goal_threads": goal_threads,
        "goal_fleet_state": goal_fleet_state,
        "goal_thread_count": len(goal_threads),
        "active_goal_thread_count": active_goal_thread_count,
        "mission_goal_count": mission_goal_count,
        "active_mission_goal_count": active_mission_goal_count,
        "goal_count": len(goal_threads),
        "active_goal_count": active_goal_thread_count,
        "active_rows": active_rows,
        "inactive_rows": inactive_rows,
        # Backwards compat: existing consumers reading 'rows' still work.
        "rows": rows,
    }


def _build_thin_clip_via_node(raw_path: Path, packet_path: Path, thin_path: Path) -> dict:
    """Spawn node to compute buildAttachmentClip(parseAgentTrace(raw)) and write thin_path."""
    node_resolution = _trace_structurer_node_resolution()
    node_executable = str(node_resolution.get("executable") or "")
    if not node_executable:
        return {
            "ok": False,
            "error": "node_not_found",
            "node_resolution": node_resolution,
        }
    parser_import = STRUCTURER_PARSER_PATH.as_posix()
    helper = (
        f"import {{ parseAgentTrace, buildAttachmentClip }} from {json.dumps(parser_import)};\n"
        f"import {{ readFileSync, writeFileSync, statSync }} from 'node:fs';\n"
        f"const text = readFileSync({json.dumps(str(raw_path))}, 'utf8');\n"
        f"const pkt = parseAgentTrace(text, {json.dumps(packet_path.name)}, "
        f"{json.dumps(_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))});\n"
        f"writeFileSync({json.dumps(str(packet_path))}, JSON.stringify(pkt, null, 2));\n"
        f"const thin = buildAttachmentClip(pkt, {{ raw_path: {json.dumps(str(raw_path))}, "
        f"packet_path: {json.dumps(str(packet_path))} }});\n"
        f"writeFileSync({json.dumps(str(thin_path))}, JSON.stringify(thin, null, 2));\n"
        f"const out = {{\n"
        f"  detected_trace_format: pkt.source_profile?.detected_trace_format,\n"
        f"  provider_family: pkt.continuation_view?.provider_reading_mode?.provider_family,\n"
        f"  source_text_complete: pkt.lossless_source?.source_text_complete,\n"
        f"  input_chars: pkt.source?.input_chars,\n"
        f"  input_lines: pkt.source?.input_lines,\n"
        f"  source_chunks: pkt.summary?.source_chunks ?? 0,\n"
        f"  trace_blocks: pkt.trace_blocks?.length ?? 0,\n"
        f"  artifacts: pkt.summary?.artifacts ?? 0,\n"
        f"  entities: pkt.summary?.entities ?? 0,\n"
        f"  sections: pkt.summary?.sections ?? 0,\n"
        f"  classified_kind: pkt.classified_kind ?? null,\n"
        f"  packet_bytes: statSync({json.dumps(str(packet_path))}).size,\n"
        f"  thin_clip_bytes: statSync({json.dumps(str(thin_path))}).size,\n"
        f"  raw_bytes: statSync({json.dumps(str(raw_path))}).size,\n"
        f"}};\n"
        f"process.stdout.write(JSON.stringify(out));\n"
    )
    try:
        proc = subprocess.run(
            [node_executable, "--input-type=module", "-e", helper],
            capture_output=True,
            text=True,
            timeout=60,
            env=_trace_structurer_node_env(),
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "node_not_found",
            "node_resolution": node_resolution,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "error": f"parser.mjs timed out after {e.timeout}s while building Structurer clip",
            "stdout": (e.stdout or "")[-500:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-500:] if isinstance(e.stderr, str) else "",
            "node_resolution": node_resolution,
        }
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"parser.mjs failed: {proc.stderr[:500]}",
            "node_resolution": node_resolution,
        }
    try:
        return {"ok": True, "node_resolution": node_resolution, **json.loads(proc.stdout or "{}")}
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": f"parser output not JSON: {e}",
            "node_resolution": node_resolution,
        }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract per-prompt tool traces from Claude Code / Codex CLI sessions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--provider", choices=["auto", "claude", "codex"], default="auto",
                    help="Provider to read from (default: auto = most recently updated session)")
    ap.add_argument("--session", help="Session id fragment to match (default: most recent)")
    ap.add_argument("--cwd", help="Cwd for slug lookup (default: current cwd)")

    sel = ap.add_mutually_exclusive_group()
    sel.add_argument("--latest", action="store_true", help="Latest completed turn (default)")
    sel.add_argument("--latest-active", action="store_true", dest="latest_active",
                     help="Latest turn regardless of completion (may be partial)")
    sel.add_argument("--turn", type=int, help="Turn index: positive=1-based, negative=from end")
    sel.add_argument("--list", action="store_true", dest="list_mode",
                     help="List all turns of the selected session with status, tool count, and previews")
    sel.add_argument("--sessions", action="store_true", dest="sessions_mode",
                     help="List candidate sessions across providers for selection")
    sel.add_argument("--mission-index", action="store_true", dest="mission_index_mode",
                     help="Emit mission index JSON for recent Claude+Codex sessions (titles, mtimes, providers) and update the canonical Structurer mission_index.json. Uses cached turn summaries and a bounded live-stale reparse budget for active sessions.")
    sel.add_argument("--mission-index-goal-roster-refresh", action="store_true",
                     dest="mission_index_goal_roster_refresh_mode",
                     help="Refresh Codex goal roster fields in the cached Structurer mission_index.json without reparsing session transcripts.")
    sel.add_argument("--mission-index-goal-roster-status", action="store_true",
                     dest="mission_index_goal_roster_status_mode",
                     help="Emit read-only staleness status for the cached Structurer goal roster versus current Codex goals.")
    sel.add_argument("--goal-fleet-action-receipt", action="store_true",
                     dest="goal_fleet_action_receipt_mode",
                     help="Emit a controller action receipt for the current Codex goal fleet without sending prompts.")
    sel.add_argument("--type-b-source-excerpt", action="store_true",
                     dest="type_b_source_excerpt_mode",
                     help="Print numbered source lines for the Trace Capsule SOURCE_EXCERPTS block. Use before closeout when Type B needs exact file/range/symbol context in the latest response bundle.")
    sel.add_argument("--check", action="store_true", help="Parseability probe; exits 0/1 with JSON status")

    ap.add_argument("--format", choices=["compact", "full", "trace-paste", "json", "thread-closeouts"], default="compact",
                    help="thread-closeouts emits session metadata, prompt refs, and exact final closeout messages without tool bodies; trace-paste emits Agent Trace Structurer parser-compatible markers (Bash/Read/Ran/Success...)")
    ap.add_argument("--mission-index-embed-variant-artifacts", action="store_true",
                    dest="mission_index_embed_variant_artifacts",
                    help="With --mission-index, embed full per-row variant artifact receipts. Off by default so the workbar refresh path stays compact.")
    ap.add_argument("--mission-index-stale-reparse-budget", type=int,
                    default=MISSION_INDEX_WORKBAR_STALE_REPARSE_BUDGET,
                    help="With --mission-index, max stale cached session summaries to reparse. Default 0 keeps workbar refresh latency bounded; raise for eager diagnostics.")
    ap.add_argument("--mission-index-oversize-stale-reparse-budget", type=int,
                    default=MISSION_INDEX_WORKBAR_RECENT_STALE_OVERSIZE_REPARSE_BUDGET,
                    help="With --mission-index, max oversize stale summaries to reparse. Default 0 keeps large active transcripts off the hot path.")
    tier_grp = ap.add_mutually_exclusive_group()
    tier_grp.add_argument("--include-preview", action="store_true", dest="include_preview",
                          help="--format json: include redacted 240-char output previews")
    tier_grp.add_argument("--include-raw", action="store_true", dest="include_raw",
                          help="--format json: include raw tool outputs (explicit local-private opt-in)")
    ap.add_argument("--without-prompt", action="store_true", dest="without_prompt",
                    help="Omit the user prompt body from trace-paste renders and Structurer clips. The prompt char-count + sha16 are still emitted as a metadata line. Default for the mission-rail 'latest trace' action where the operator wants tool/assistant activity, not the instructions.")
    ap.add_argument("--prompt-cycle", action="store_true", dest="prompt_cycle",
                    help="If the selected prompt is short, include previous turns back through the nearest prompt with at least --short-prompt-threshold-words words.")
    ap.add_argument("--short-prompt-threshold-words", type=int, default=SHORT_PROMPT_CHAIN_WORD_THRESHOLD,
                    help=f"Word threshold used by --prompt-cycle. Default: {SHORT_PROMPT_CHAIN_WORD_THRESHOLD}.")
    ap.add_argument("--full-thread", action="store_true", dest="full_thread",
                    help="Include every parsed turn in the selected session through the selected turn. Explicit large-window mode.")
    ap.add_argument("--intern-repeated-prompts", action="store_true", dest="intern_repeated_prompts",
                    help="When rendering a multi-turn/full-thread prompt body, store identical prompt text once in a prompt_### pool and replace repeated turn prompts with prompt_ref lines. Changed prompts remain inline.")
    ap.add_argument("--allow-partial", action="store_true", dest="allow_partial",
                    help="Allow rendering partial/in-progress turns without warning")
    ap.add_argument("--allow-ambiguous", action="store_true", dest="allow_ambiguous",
                    help="Silently pick most-recent session even when multiple cwd peers were updated within the ambiguity window")
    ap.add_argument("--write-structurer-clip", action="store_true", dest="write_structurer_clip",
                    help="Render trace-paste, run tools/agent_trace_structurer/parser.mjs, "
                         "and write into ~/Library/Application Support/Agent Trace Structurer/ "
                         "(Raw Sources/, Captures/, clipboard_history.json). stdout becomes the receipt JSON.")
    ap.add_argument("--write-trace-capsule-artifact", action="store_true", dest="write_trace_capsule_artifact",
                    help="Fast path: render Trace Capsule v3 directly from the selected turn and update the Variant Artifacts index without building the full parser packet.")
    ap.add_argument("--write-closeout-report-artifact", action="store_true", dest="write_closeout_report_artifact",
                    help="Fast path: render the closeout report variant from the selected window and update the Variant Artifacts index without copying tool bodies.")
    ap.add_argument("--measure-trace-variant", choices=["all", "trace_capsule", "closeout_report"], dest="measure_trace_variant",
                    help="Measure exact current renderer bytes for trace variants without writing artifacts or touching the clipboard.")
    ap.add_argument("--closeout-command-limit", type=int, default=TRACE_CLOSEOUT_COMMAND_LIMIT,
                    help=f"Top command rows to include in --format thread-closeouts / closeout report artifacts. Default: {TRACE_CLOSEOUT_COMMAND_LIMIT}.")
    ap.add_argument("--copy", action="store_true", dest="copy_to_clipboard",
                    help="Copy stdout payload to the macOS clipboard via pbcopy")
    ap.add_argument("--copy-path", action="store_true", dest="copy_clip_path",
                    help="With --write-structurer-clip: copy the written clip path to the clipboard instead of the receipt JSON")
    ap.add_argument("-o", "--output", help="Write output to file instead of stdout")
    ap.add_argument("--write-goal-fleet-action-receipt", action="store_true",
                    dest="write_goal_fleet_action_receipt",
                    help="With --goal-fleet-action-receipt, also write the canonical action receipt sidecar.")
    ap.add_argument("--goal-fleet-action-collision-check-ref",
                    dest="goal_fleet_action_collision_check_ref", default="",
                    help="Optional Work Ledger or collision-check ref to bind into the action receipt.")
    ap.add_argument("--goal-fleet-action-workitem-ref", action="append",
                    dest="goal_fleet_action_workitem_refs", default=[],
                    help="WorkItem/CAP ref touched by --goal-fleet-action-receipt. May be repeated.")
    ap.add_argument("--source-path",
                    help="With --type-b-source-excerpt: repo-relative or absolute file path to include in SOURCE_EXCERPTS.")
    ap.add_argument("--line-range",
                    help="With --type-b-source-excerpt: 1-based inclusive line range, for example 10-40.")
    ap.add_argument("--symbol",
                    help="With --type-b-source-excerpt: function/class/symbol name to include. Python uses ast; JS/TS-style files use a bounded declaration scan.")
    ap.add_argument("--full-file", action="store_true",
                    help="With --type-b-source-excerpt: include the file from line 1, bounded by --excerpt-lines.")
    ap.add_argument("--excerpt-lines", type=int, default=TRACE_CAPSULE_SOURCE_EXCERPT_LINES,
                    help=f"With --type-b-source-excerpt: max lines to print. Default: {TRACE_CAPSULE_SOURCE_EXCERPT_LINES}; hard cap: 240.")
    ap.add_argument("--trace-carrier", action="store_true", dest="type_b_trace_carrier",
                    help="With --type-b-source-excerpt: write the bounded excerpt to the managed trace carrier and print only a compact receipt; Trace Capsule promotes the sidecar into SOURCE_EXCERPTS.")

    args = ap.parse_args()

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()

    if args.type_b_source_excerpt_mode:
        if args.type_b_trace_carrier:
            text, _meta, _sidecar_path = _type_b_source_excerpt_trace_carrier_receipt(
                cwd=cwd,
                source_path=args.source_path or "",
                line_range=args.line_range,
                symbol=args.symbol,
                full_file=args.full_file,
                max_lines=args.excerpt_lines,
            )
        else:
            text, _meta = render_type_b_source_excerpt(
                cwd=cwd,
                source_path=args.source_path or "",
                line_range=args.line_range,
                symbol=args.symbol,
                full_file=args.full_file,
                max_lines=args.excerpt_lines,
            )
        if args.output:
            Path(args.output).write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
            sys.stderr.write(f"wrote {len(text)} chars to {args.output}\n")
        else:
            print(text)
        if args.copy_to_clipboard:
            clipboard = subprocess.run(["pbcopy"], input=text, text=True)
            if clipboard.returncode != 0:
                raise SystemExit("pbcopy failed")
        return 0

    if args.sessions_mode:
        print(list_session_candidates(args.provider, cwd))
        return 0

    if args.mission_index_mode:
        index = build_mission_index(
            cwd=cwd,
            embed_variant_artifacts=args.mission_index_embed_variant_artifacts,
            stale_reparse_budget=args.mission_index_stale_reparse_budget,
            recent_stale_oversize_reparse_budget=args.mission_index_oversize_stale_reparse_budget,
        )
        body = json.dumps(index, indent=2, ensure_ascii=False)
        try:
            TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
            tmp = TRACE_STRUCTURER_MISSION_INDEX.with_suffix(".json.tmp")
            tmp.write_text(body, encoding="utf-8")
            tmp.replace(TRACE_STRUCTURER_MISSION_INDEX)
            artifact_mode = index.get("variant_artifact_embedding") or "unknown"
            sys.stderr.write(
                f"# wrote mission_index ({index['row_count']} rows, variant_artifacts={artifact_mode}) to {TRACE_STRUCTURER_MISSION_INDEX}\n"
            )
        except Exception as e:
            sys.stderr.write(f"# warning: could not update canonical mission index: {e}\n")
        if args.output:
            Path(args.output).write_text(body + ("" if body.endswith("\n") else "\n"))
            sys.stderr.write(f"wrote {len(body)} chars to {args.output}\n")
        else:
            print(body)
        return 0

    if args.mission_index_goal_roster_refresh_mode:
        try:
            index = json.loads(TRACE_STRUCTURER_MISSION_INDEX.read_text(encoding="utf-8"))
            if not isinstance(index, dict):
                index = {}
        except Exception:
            index = {}
        index = _refresh_mission_index_goal_roster(index, cwd=cwd)
        body = json.dumps(index, indent=2, ensure_ascii=False)
        try:
            TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
            tmp = TRACE_STRUCTURER_MISSION_INDEX.with_suffix(".json.tmp")
            tmp.write_text(body, encoding="utf-8")
            tmp.replace(TRACE_STRUCTURER_MISSION_INDEX)
            _write_goal_roster_refresh_receipt(index)
            sys.stderr.write(
                "# refreshed mission_index goal roster "
                f"({index.get('goal_thread_count', 0)} goal threads) "
                f"at {TRACE_STRUCTURER_MISSION_INDEX}\n"
            )
            sys.stderr.write(
                "# wrote goal roster refresh receipt to "
                f"{TRACE_STRUCTURER_GOAL_ROSTER_REFRESH_RECEIPT}\n"
            )
        except Exception as e:
            sys.stderr.write(f"# warning: could not update canonical mission index: {e}\n")
        if args.output:
            Path(args.output).write_text(body + ("" if body.endswith("\n") else "\n"))
            sys.stderr.write(f"wrote {len(body)} chars to {args.output}\n")
        else:
            print(body)
        return 0

    if args.mission_index_goal_roster_status_mode:
        status = _goal_roster_status(cwd=cwd)
        body = json.dumps(status, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(body + ("" if body.endswith("\n") else "\n"))
            sys.stderr.write(f"wrote {len(body)} chars to {args.output}\n")
        else:
            print(body)
        return 0

    if args.goal_fleet_action_receipt_mode:
        receipt = _goal_fleet_action_receipt(
            cwd=cwd,
            collision_check_ref=args.goal_fleet_action_collision_check_ref,
            workitem_refs=args.goal_fleet_action_workitem_refs,
        )
        if args.write_goal_fleet_action_receipt:
            _write_goal_fleet_action_receipt(receipt)
            sys.stderr.write(
                "# wrote goal fleet action receipt to "
                f"{TRACE_STRUCTURER_GOAL_FLEET_ACTION_RECEIPT}\n"
            )
        body = json.dumps(receipt, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(body + ("" if body.endswith("\n") else "\n"))
            sys.stderr.write(f"wrote {len(body)} chars to {args.output}\n")
        else:
            print(body)
        return 0

    try:
        provider, path, selection_reason, ambiguous_peers = discover_session(
            args.provider, cwd, args.session, allow_ambiguous=args.allow_ambiguous,
        )
    except SystemExit as e:
        if args.check:
            print(json.dumps({"ok": False, "error": str(e)}))
            return 1
        raise

    try:
        turns = load_turns(provider, path)
    except Exception as e:
        if args.check:
            print(json.dumps({"ok": False, "error": f"parse: {e}", "session_file": str(path)}))
            return 1
        raise

    if args.check:
        completed = [t for t in turns if t.is_complete]
        latest_completed_idx = completed[-1].turn_index if completed else None
        print(json.dumps({
            "ok": True,
            "provider": provider,
            "session_file": str(path),
            "selection_reason": selection_reason,
            "selection_ambiguous_peer_count": len(ambiguous_peers),
            "turn_count": len(turns),
            "completed_turn_count": len(completed),
            "latest_completed_turn_index": latest_completed_idx,
            "latest_turn_tools": len(turns[-1].tool_events) if turns else 0,
            "latest_turn_is_complete": turns[-1].is_complete if turns else None,
            "latest_turn_partial_reason": turns[-1].partial_reason if turns else None,
            "latest_turn_started_at": turns[-1].started_at if turns else None,
        }))
        return 0

    clipboard_content: str | None = None
    if args.list_mode:
        text = list_turns(turns)
        sys.stderr.write(
            f"# selected session: provider={provider}  reason={selection_reason}  "
            f"file={path}\n"
        )
    else:
        turn = select_trace_window(
            turns,
            turn_arg=args.turn,
            active=args.latest_active,
            allow_partial=args.allow_partial,
            prompt_cycle=args.prompt_cycle,
            full_thread=args.full_thread,
            threshold_words=args.short_prompt_threshold_words,
        )
        if args.write_trace_capsule_artifact:
            if args.full_thread:
                source_window = "full_thread"
            elif args.prompt_cycle:
                source_window = "latest_prompt_cycle"
            else:
                source_window = "selected_turn"
            receipt = write_trace_capsule_artifact(
                turn,
                source_window=source_window,
                intern_repeated_prompts=args.intern_repeated_prompts,
                include_prompt_body=not args.without_prompt,
            )
            text = json.dumps(receipt, indent=2, ensure_ascii=False)
            if args.copy_to_clipboard:
                clipboard_content = Path(str(receipt.get("artifact_path") or "")).read_text(encoding="utf-8")
        elif args.measure_trace_variant:
            base_turn = select_turn(
                turns,
                turn_arg=args.turn,
                active=args.latest_active,
                allow_partial=args.allow_partial,
            )
            if args.full_thread:
                source_window = "full_thread"
            elif args.prompt_cycle:
                source_window = "latest_prompt_cycle"
            else:
                source_window = "selected_turn"
            title, _title_source = _resolve_session_title(
                base_turn.provider, base_turn.session_id, Path(base_turn.session_file),
                codex_thread_names=_load_codex_thread_names(),
                title_aliases=_load_title_aliases(),
                claude_desktop_titles=_load_claude_desktop_titles(),
            )
            if not title:
                title = _prompt_title_from_text(base_turn.prompt_text) or f"{base_turn.provider} turn {base_turn.turn_index}"
            receipt = measure_trace_variant_sizes(
                base_turn,
                turns=turns,
                title=title,
                selected_source_window=source_window,
                variant=args.measure_trace_variant,
                include_prompt_body=not args.without_prompt,
            )
            text = json.dumps(receipt, indent=2, ensure_ascii=False)
            if args.copy_to_clipboard:
                clipboard_content = text
        elif args.write_closeout_report_artifact:
            if args.full_thread:
                source_window = "full_thread"
            elif args.prompt_cycle:
                source_window = "latest_prompt_cycle"
            else:
                source_window = "selected_turn"
            receipt = write_closeout_report_artifact(
                turn,
                source_window=source_window,
                intern_repeated_prompts=args.intern_repeated_prompts,
                command_limit=args.closeout_command_limit,
            )
            text = json.dumps(receipt, indent=2, ensure_ascii=False)
            if args.copy_to_clipboard:
                clipboard_content = Path(str(receipt.get("artifact_path") or "")).read_text(encoding="utf-8")
        elif args.write_structurer_clip:
            receipt = write_structurer_clip(
                turn,
                include_prompt=not args.without_prompt,
                intern_repeated_prompts=args.intern_repeated_prompts,
            )
            text = json.dumps(receipt, indent=2, ensure_ascii=False)
            if args.copy_clip_path:
                clip_path = str(receipt.get("clip_store_path") or receipt.get("clip_path") or "")
                if clip_path:
                    clipboard_content = clip_path
            elif args.copy_to_clipboard:
                clipboard_content = text
        elif args.format == "trace-paste":
            text = render_trace_paste(
                turn,
                include_prompt=not args.without_prompt,
                intern_repeated_prompts=args.intern_repeated_prompts,
            )
            if args.copy_to_clipboard:
                clipboard_content = text
        elif args.format == "json":
            if args.include_raw:
                tier = "raw"
            elif args.include_preview:
                tier = "preview"
            else:
                tier = "manifest"
            text = render_json(
                turn, tier=tier,
                selection_reason=selection_reason,
                selection_ambiguous_peers=len(ambiguous_peers),
            )
            if args.copy_to_clipboard:
                clipboard_content = text
        elif args.format == "thread-closeouts":
            title, _title_source = _resolve_session_title(
                turn.provider, turn.session_id, Path(turn.session_file),
                codex_thread_names=_load_codex_thread_names(),
                title_aliases=_load_title_aliases(),
                claude_desktop_titles=_load_claude_desktop_titles(),
            )
            text = render_thread_closeout_report(
                turn,
                title=title,
                intern_repeated_prompts=args.intern_repeated_prompts,
                command_limit=args.closeout_command_limit,
            )
            if args.copy_to_clipboard:
                clipboard_content = text
        elif args.format == "full":
            text = render_full(turn, intern_repeated_prompts=args.intern_repeated_prompts)
            if args.copy_to_clipboard:
                clipboard_content = text
        else:
            text = render_compact(turn)
            if args.copy_to_clipboard:
                clipboard_content = text

    if args.output:
        Path(args.output).write_text(text + ("" if text.endswith("\n") else "\n"))
        sys.stderr.write(f"wrote {len(text)} chars to {args.output}\n")
    else:
        print(text)

    if clipboard_content is not None:
        if _copy_to_macos_clipboard(clipboard_content):
            sys.stderr.write(f"# copied {len(clipboard_content)} chars to clipboard\n")
        else:
            sys.stderr.write("# warning: pbcopy failed; clipboard not updated\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
