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
import datetime as _dt
import difflib
import hashlib
import html
import json
import re
import shlex
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict, replace
from pathlib import Path
from typing import Any, Iterable

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
TRACE_STRUCTURER_MISSION_SUMMARY_CACHE = TRACE_STRUCTURER_BASE / "mission_summary_cache.json"
TRACE_STRUCTURER_TITLE_ALIASES = TRACE_STRUCTURER_BASE / "title_aliases.json"
TRACE_STRUCTURER_VARIANT_ARTIFACTS = TRACE_STRUCTURER_BASE / "Variant Artifacts"
TRACE_STRUCTURER_VARIANT_INDEX = TRACE_STRUCTURER_BASE / "variant_artifact_index.json"
STRUCTURER_PARSER_PATH = REPO_ROOT / "tools" / "agent_trace_structurer" / "parser.mjs"
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


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


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
                    sid = (rec.get("payload") or {}).get("id")
                    if sid:
                        return str(sid)
                    return ""
                if rec.get("type"):
                    return ""
    except Exception:
        pass
    return ""


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
            sid = _peek_codex_session_id(p) or p.stem
            rows.append({
                "provider": "codex",
                "session_file": str(p),
                "session_id": sid,
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
            with path.open() as f:
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


def _relationship_for_subagent_child(sidechain: dict | None) -> dict:
    if sidechain:
        return {
            "schema": "agent_trace_subagent_relationship_v1",
            "kind": "linked_sidechain",
            "parent_signal": "tool_use:Agent",
            "child_signal": "claude_sidechain_jsonl",
            "confidence": "high",
            "match_rule": "same_parent_session_and_prompt_sha16",
        }
    return {
        "schema": "agent_trace_subagent_relationship_v1",
        "kind": "deployment_only",
        "parent_signal": "tool_use:Agent",
        "child_signal": "not_found",
        "confidence": "medium",
        "match_rule": "parent_tool_use_only",
    }


def _attach_sidechain_to_deployment(dep: dict, sidechain: dict | None) -> dict:
    out = dict(dep)
    out["relationship"] = _relationship_for_subagent_child(sidechain)
    out["relationship_kind"] = out["relationship"]["kind"]
    out["relationship_confidence"] = out["relationship"]["confidence"]
    out["linked_child_trace"] = bool(sidechain)
    if sidechain:
        child_trace = {
            key: sidechain.get(key)
            for key in (
                "schema",
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
    return {
        "schema": "agent_trace_subagent_deployment_v1",
        "deployment_index": deployment_index,
        "provider": "claude_code",
        "session_id": sidechain.get("parent_session_id") or "",
        "turn_index": None,
        "turn_id": "",
        "tool_index": None,
        "tool_name": "Agent",
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
            "parent_signal": "missing_or_uncached_tool_use",
            "child_signal": "claude_sidechain_jsonl",
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
    has_subagent_shape = any(k in input_obj for k in ("subagent_type", "description", "prompt"))
    if lower_name not in {"agent", "task"} and not input_obj.get("subagent_type"):
        return None
    if lower_name == "task" and not has_subagent_shape:
        return None

    description = _compact_one_line(input_obj.get("description") or "", limit=90)
    prompt_text = str(input_obj.get("prompt") or "")
    prompt_title = _prompt_title_from_text(prompt_text, limit=90)
    subagent_type = _compact_one_line(input_obj.get("subagent_type") or "", limit=40)
    model = _compact_one_line(input_obj.get("model") or "", limit=40)
    label = description or prompt_title or subagent_type or tool_name or "Sub-agent"
    status = "failed" if ev.is_error else ("completed" if ev.completed_at else "running")
    prompt_preview = _compact_one_line(prompt_text, limit=180)
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
        "relationship": _relationship_for_subagent_child(None),
        "relationship_kind": "deployment_only",
        "relationship_confidence": "medium",
        "linked_child_trace": False,
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


def _subagent_deployment_packet(turns: list[Turn], *, sidechains: list[dict] | None = None, limit: int = 24) -> dict:
    deployments: list[dict] = []
    for turn in turns:
        deployments.extend(_subagent_deployments_for_turn(turn))
    sidechain_rows = list(sidechains or [])
    sidechains_by_prompt: dict[str, list[dict]] = {}
    for sc in sidechain_rows:
        prompt_sha = str(sc.get("prompt_sha16") or "")
        if prompt_sha:
            sidechains_by_prompt.setdefault(prompt_sha, []).append(sc)
    matched_sidechain_ids: set[str] = set()
    enriched: list[dict] = []
    for dep in deployments:
        prompt_sha = str(dep.get("prompt_sha16") or "")
        match = None
        if prompt_sha and sidechains_by_prompt.get(prompt_sha):
            match = sidechains_by_prompt[prompt_sha].pop(0)
            if match.get("agent_id"):
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
    recent = deployments[: max(1, limit)]
    return {
        "count": len(deployments),
        "deployments": recent,
        "latest_label": str(recent[0].get("label") or ""),
        "models": models,
        "linked_trace_count": linked_trace_count,
        "visible_count": len(recent),
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
        return selected
    return merge_prompt_cycle(
        prompt_cycle_turns(turns, selected, threshold_words=threshold_words),
        threshold_words=threshold_words,
    )


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
    lines = ["DIFFS"]
    if not edit_rows:
        lines.append("none captured")
        return lines

    path_count = len({str(row.get("path") or "") for row in edit_rows if row.get("path")})
    additions = sum(int(row.get("additions") or 0) for row in edit_rows)
    deletions = sum(int(row.get("deletions") or 0) for row in edit_rows)
    lines.append(
        f"edited_files_summary: files={path_count} additions=+{additions} deletions=-{deletions} source=edit_delta"
    )
    lines.append(
        f"diff_summary: files={path_count} rows={len(edit_rows)} additions=+{additions} deletions=-{deletions}"
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
    validation_class: str = ""
    residual_id: str = ""
    residual_ids: tuple[str, ...] = ()
    ambient_warning_class: str = ""


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
        action in lower_args for action in ("quick-capture", "capture", "note", "transition", "sign-off", "execution-receipt")
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

    if script_kind == "module" and lower_script == "py_compile":
        label = _capsule_compact_label("py_compile", script_args)
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
        "process",
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
    }
    ledger_items = _capsule_task_ledger_work_items()
    for row in rows:
        residual_ids = row.residual_ids or ((row.residual_id,) if row.residual_id else ())
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
    )


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


def _capsule_ambient_warning_class(command: str, output_text: str) -> str:
    text = f"{command}\n{output_text}"
    lowered = text.lower()
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
        if "task_ledger_apply.py" in text and any(token in text for token in ("quick-capture", " capture", "cap_")):
            return "captured_residual"
        return "governance_actuator_result"
    if bucket == "diagnostic":
        return "exploratory_diagnostic_failure" if result == "fail" else "exploratory_diagnostic"
    if bucket != "check":
        return "unclassified"
    if result != "fail":
        return "scoped_validation_pass" if result == "pass" else "scoped_validation_other"
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


def _capsule_release_candidate_gate_decision(text: str) -> str:
    lowered = (text or "").lower()
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
            return "public_release_blocked"
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
    return CapsuleEvidenceClassification(
        bucket=bucket,
        result=result,
        label=label,
        identity=identity,
        validation_class=_capsule_validation_class(
            bucket,
            result,
            command,
            output_text,
            ambient_warning_class,
        ),
        residual_id=residual_ids[0] if residual_ids else "",
        residual_ids=residual_ids,
        ambient_warning_class=ambient_warning_class,
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


def _capsule_commit_evidence_allowed(command: str) -> bool:
    candidates = _capsule_command_surface_argvs(command)
    if not candidates:
        return False
    for argv in candidates:
        exe = Path(argv[0]).name
        script, script_args, _ = _capsule_script_surface(argv)
        script_base = Path(script).name
        lower_args = [arg.lower() for arg in script_args]
        if script_base == "scoped_commit.py":
            return True
        if script_base == "checkpoint" or (argv and Path(argv[0]).name == "checkpoint"):
            return True
        if exe in {"git", "repo-git"} and any(arg in lower_args for arg in ("commit", "log", "show")):
            return True
    return False


def _capsule_commit_from_output(output: str, command: str = "") -> tuple[str, str]:
    if not _capsule_commit_evidence_allowed(command):
        return ("", "")
    m = re.search(r'"new_commit"\s*:\s*"([0-9a-f]{7,40})"', output or "")
    if m:
        commit_hash = m.group(1)
        return (commit_hash, _capsule_normalize_commit_title(commit_hash, _capsule_commit_title_from_command(command)))
    for line in (output or "").splitlines():
        m = re.match(r"^([0-9a-f]{7,16})\s+(.+)$", line.strip())
        if m:
            commit_hash = m.group(1)
            return (commit_hash, _capsule_normalize_commit_title(commit_hash, m.group(2).strip()))
    return ("", "")


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


def _trace_window_header(turn: Turn, source_window: str) -> str:
    trace_window = (turn.source_ref or {}).get("trace_window")
    if not isinstance(trace_window, dict):
        display_source_window = "selected_turn" if source_window == "latest_prompt_cycle" else source_window
        return f"window: {display_source_window} turns={turn.turn_index}-{turn.turn_index} count=1 mode=selected_turn"
    count = int(trace_window.get("turn_count") or 1)
    start = trace_window.get("start_turn_index") or turn.turn_index
    end = trace_window.get("end_turn_index") or turn.turn_index
    mode = trace_window.get("mode") or source_window
    display_source_window = "selected_turn" if source_window == "latest_prompt_cycle" and count == 1 else source_window
    if mode == "single_turn":
        mode = "selected_turn"
    return f"window: {display_source_window} turns={start}-{end} count={count} mode={mode}"


def render_trace_capsule_text(
    turn: Turn,
    *,
    title: str,
    source_window: str = "latest_prompt_cycle",
    intern_repeated_prompts: bool = False,
    include_raw_sidecar: bool = True,
    include_prompt_body: bool = True,
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
    ambient_warning_classes = sorted(
        {row.ambient_warning_class or "external_validation_warning" for row in ambient_validation_rows}
    )
    owner_terminal_check_rows = [
        row
        for row in terminal_check_rows
        if row.validation_class not in {"ambient_validation_warning", "validation_process_warning"}
    ]
    owner_terminal_pass_count, owner_terminal_fail_count, owner_terminal_other_count = _capsule_result_counts(
        owner_terminal_check_rows
    )
    nonblocking_failure_classes = {
        "stale_selector_retry",
        "out_of_scope_discoverability_failure",
        "exploratory_diagnostic_failure",
        "ambient_validation_warning",
        "validation_process_warning",
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
    product_state_text = "\n".join(
        "\n".join(part for part in (command, ev.output_text or "") if part)
        for ev, command, _, _ in renderable
    )
    release_candidate_gate_decision = _capsule_release_candidate_gate_decision(
        "\n".join(part for part in (product_state_text, final_assistant_text) if part)
    )
    release_candidate_gate_ready = release_candidate_gate_decision == "ready_pending_operator_authorization"
    public_release_blocked = release_candidate_gate_decision == "public_release_blocked"
    release_candidate_gate_nonblocking = release_candidate_gate_ready or public_release_blocked
    internal_authorization = "satisfied" if public_release_blocked else (
        "pending_operator_authorization" if release_candidate_gate_ready else "none"
    )
    public_release_authorization = "not_authorized_by_operator" if public_release_blocked else (
        "pending_operator_authorization" if release_candidate_gate_ready else "none"
    )
    historical_terminal_failures_superseded = (
        len(blocking_terminal_failures) if release_candidate_gate_nonblocking else 0
    )
    effective_blocking_terminal_failures = (
        [] if release_candidate_gate_nonblocking else blocking_terminal_failures
    )
    owner_scope_validation = "unknown"
    if effective_blocking_terminal_failures:
        owner_scope_validation = "needs_review"
    elif release_candidate_gate_nonblocking:
        owner_scope_validation = "pass"
    elif owner_terminal_pass_count > 0:
        owner_scope_validation = "pass"
    elif owner_terminal_fail_count > 0:
        owner_scope_validation = "needs_review"
    ambient_validation = "valid_with_warnings" if ambient_validation_rows else "none"
    ambient_warning_class_summary = ",".join(ambient_warning_classes) if ambient_warning_classes else "none"
    ambient_validation_warning_summary = ambient_warning_class_summary
    validation_process = (
        "needs_review"
        if validation_process_terminal_rows or open_validation_process_residuals
        else "none"
    )
    has_validation_process_warning = validation_process != "none"
    final_validation = "unknown"
    if public_release_blocked:
        final_validation = "pass_with_public_release_blocked"
    elif release_candidate_gate_ready:
        final_validation = release_candidate_gate_decision
    elif effective_blocking_terminal_failures:
        final_validation = "needs_review"
    elif owner_terminal_pass_count > 0 and ambient_terminal_warning_rows and has_validation_process_warning:
        final_validation = "pass_with_external_and_validation_process_warnings"
    elif owner_terminal_pass_count > 0 and ambient_terminal_warning_rows:
        final_validation = "pass_with_external_warnings"
    elif owner_terminal_pass_count > 0 and has_validation_process_warning:
        final_validation = "pass_with_validation_process_warnings"
    elif owner_terminal_pass_count > 0:
        final_validation = "passed"
    elif terminal_check_fail_count:
        final_validation = "needs_review"
    validation_class_counts: dict[str, int] = {}
    for row in [*check_rows, *governance_rows, *diagnostic_rows]:
        key = row.validation_class or "unclassified"
        validation_class_counts[key] = validation_class_counts.get(key, 0) + 1
    validation_class_summary = " ".join(
        f"{key}={value}" for key, value in sorted(validation_class_counts.items())
    ) or "none=0"
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
    captured_residual_summary = ",".join(captured_residual_ids) if captured_residual_ids else "none"
    closeout_present = bool(final_assistant_text or commit_hash)
    changed_paths = sorted({str(row.get("path") or "") for row in edit_rows if row.get("path")})
    changed = "none captured"
    if changed_paths:
        names = [Path(path).name for path in changed_paths[:8]]
        changed = _capsule_clean_text(f"{len(changed_paths)} files: {', '.join(names)}")
        if len(changed_paths) > 8:
            changed += f", +{len(changed_paths) - 8} more"
    result_summary = _capsule_result_summary(turn, commit_title)

    header = [
        "TRACE CAPSULE v3",
        f"title: {_capsule_clean_text(title[:180])}",
        f"provider: {turn.provider}",
        f"session: {_short_session_tag(turn.session_id)}",
        f"turn: {turn.turn_index}",
        _trace_window_header(turn, source_window),
        f"status: {status_text}",
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
    command_return_lines, sidecar_manifest_lines, command_return_stats = _capsule_command_return_sections(
        renderable,
        source_sha16=source_sha16,
        raw_sidecar_available=include_raw_sidecar,
    )
    header.extend([
        f"prompt: {turn.prompt_sha256_16}",
        f"source: {source_sha16}",
        f"coverage: commands={len(renderable)} outputs={commands_with_outputs} edits={len(edit_rows)} checks={len(check_rows)} governance={len(governance_rows)} diagnostics={len(diagnostic_rows)} notes={visible_note_count} truncated_outputs={truncated_outputs} raw_sidecar={'available' if include_raw_sidecar else 'not_materialized'}",
        "",
        "SUMMARY",
        f"status: {status_text}",
        f"result: {result_summary}",
        f"changed: {changed}",
        f"final_validation: {final_validation}",
        f"owner_scope_validation: {owner_scope_validation}",
        f"internal_authorization: {internal_authorization}",
        f"public_release_authorization: {public_release_authorization}",
        f"ambient_validation: {ambient_validation}",
        f"ambient_warning_class: {ambient_warning_class_summary}",
        f"open_product_residuals: {residual_summary}",
        f"open_validation_process_residuals: {validation_process_residual_summary}",
        f"closed_residuals_seen: {closed_residuals_seen_summary}",
        f"blocked_external_observation_residuals: {blocked_external_observation_residuals_summary}",
        f"ambient_validation_warnings: {ambient_validation_warning_summary}",
        f"release_candidate_gate: {release_candidate_gate_decision or 'none'}",
        f"historical_terminal_failures_superseded: {historical_terminal_failures_superseded}",
        f"projection_or_view_artifacts_seen: {projection_or_view_artifacts_seen_summary}",
        f"unresolved_residual_mentions: {unresolved_residual_mentions_summary}",
        "release_authority: none",
        f"checks: pass={check_pass_count} fail={check_fail_count} other={check_other_count} total={len(check_rows)}",
        f"terminal_checks: pass={terminal_check_pass_count} fail={terminal_check_fail_count} other={terminal_check_other_count} total={len(terminal_check_rows)}",
        f"owner_scope_terminal_checks: pass={owner_terminal_pass_count} fail={owner_terminal_fail_count} other={owner_terminal_other_count} total={len(owner_terminal_check_rows)}",
        f"validation_progress: iterative_checks(pass={check_pass_count} fail={check_fail_count} other={check_other_count} total={len(check_rows)}) terminal_checks(pass={terminal_check_pass_count} fail={terminal_check_fail_count} other={terminal_check_other_count} total={len(terminal_check_rows)}) owner_scope_terminal_checks(pass={owner_terminal_pass_count} fail={owner_terminal_fail_count} other={owner_terminal_other_count} total={len(owner_terminal_check_rows)}) recovered_failures={recovered_failures} final_validation_basis={final_validation_basis}",
        f"validation_semantics: owner_scope_validation={owner_scope_validation} validation_process={validation_process} ambient_validation={ambient_validation} internal_authorization={internal_authorization} public_release_authorization={public_release_authorization} release_candidate_gate={release_candidate_gate_decision or 'none'} scoped_failures={len(effective_blocking_terminal_failures)} historical_terminal_failures_superseded={historical_terminal_failures_superseded} nonblocking_terminal_failures={len(nonblocking_terminal_failures)} external_terminal_warnings={len(ambient_terminal_warning_rows)} open_product_residuals={residual_summary} blocked_external_observation_residuals={blocked_external_observation_residuals_summary} captured_residuals={captured_residual_summary} classes={validation_class_summary}",
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
    header.append("open: none captured" if turn.is_complete else (turn.partial_reason or "trace still in progress"))
    header.extend(["", *_capsule_diff_section_lines(edit_rows)])
    header.extend(["", *command_return_lines])
    header.extend(["", *sidecar_manifest_lines])
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
        f"truncated_outputs: {truncated_outputs}",
        "not_included: server_hidden_reasoning, omitted_provider_bytes_without_sidecar",
        "included: app_visible_thinking_progress",
        f"source_window: {'selected_turn' if source_window == 'latest_prompt_cycle' and int(((turn.source_ref or {}).get('trace_window') or {}).get('turn_count') or 1) == 1 else source_window}",
    ])
    if not prompt_body_included:
        lines.append("prompt_body: omitted_by_request")
    prompt_intern_summary = _prompt_intern_summary_line(turn.prompt_text) if intern_repeated_prompts else None
    if prompt_intern_summary:
        lines.append(prompt_intern_summary.replace("# ", ""))
    meta = {
        "source_sha16": source_sha16,
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
        "internal_authorization": internal_authorization,
        "public_release_authorization": public_release_authorization,
        "ambient_validation": ambient_validation,
        "ambient_warning_classes": ambient_warning_classes,
        "ambient_validation_warnings": ambient_warning_classes,
        "validation_process": validation_process,
        "release_candidate_gate_decision": release_candidate_gate_decision,
        "historical_terminal_failures_superseded": historical_terminal_failures_superseded,
        "external_terminal_warning_count": len(ambient_terminal_warning_rows),
        "validation_process_terminal_warning_count": len(validation_process_terminal_rows),
        "owner_scope_terminal_validation_count": len(owner_terminal_check_rows),
        "owner_scope_terminal_validation_pass_count": owner_terminal_pass_count,
        "owner_scope_terminal_validation_fail_count": owner_terminal_fail_count,
        "open_product_residuals": open_product_residuals,
        "open_validation_process_residuals": open_validation_process_residuals,
        "closed_residuals_seen": closed_residuals_seen,
        "blocked_external_observation_residuals": blocked_external_observation_residuals,
        "projection_or_view_artifacts_seen": projection_or_view_artifacts_seen,
        "unresolved_residual_mentions": unresolved_residual_mentions,
        "release_authority": "none",
        "validation_class_counts": validation_class_counts,
        "captured_residual_ids": captured_residual_ids,
        "blocking_terminal_failure_count": len(effective_blocking_terminal_failures),
        "raw_blocking_terminal_failure_count": len(blocking_terminal_failures),
        "nonblocking_terminal_failure_count": len(nonblocking_terminal_failures),
        "commit_count": commit_count,
        "closeout_present": closeout_present,
        "truncated_outputs": truncated_outputs,
        "command_return_count": command_return_stats["outputs"],
        "command_return_inline_count": command_return_stats["inline"],
        "command_return_sidecar_count": command_return_stats["sidecar"],
        "command_return_redacted_count": command_return_stats["redacted"],
        "command_return_no_output_count": command_return_stats["no_output"],
        "command_return_lost_count": command_return_stats["lost"],
        "raw_sidecar_text": raw_sidecar_text,
        "raw_sidecar_materialized": include_raw_sidecar,
        "prompt_body_included": prompt_body_included,
    }
    if prompt_intern_summary:
        meta["prompt_interning"] = _prompt_intern_manifest(turn.prompt_text)
    return ("\n".join(lines).rstrip() + "\n", meta)


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

    identity_key = f"session={turn.session_id}|window={source_window}|prompt={turn.prompt_sha256_16}|turn={turn.turn_index}|variant=trace_capsule"
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
            "closeout_present": meta["closeout_present"],
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
        "source_clip_path": str(raw_path),
        "clip_path": str(raw_path),
        "artifact_path": str(out_path),
        "copied_bytes": len(data),
        "bytes": {"artifact": len(data), "raw": raw_path.stat().st_size if raw_path.exists() else 0},
        "variant": "trace_capsule",
        "slice_label": TRACE_CAPSULE_SCHEMA_VERSION,
        "variant_artifact": artifact,
        "content_summary": {
            "command_count": meta["command_count"],
            "output_count": meta["commands_with_outputs"],
            "edit_path_count": meta["edit_count"],
            "validation_count": meta["validation_count"],
            "closeout_present": meta["closeout_present"],
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


def _load_codex_thread_goals(db_path: Path = CODEX_GOALS_DB) -> dict[str, dict]:
    """Read Codex app goal state keyed by thread/session id.

    The Structurer mission index is already local-private. Still, keep the row
    bounded: objective text is represented as a preview plus hash so the
    mission rail can show goal-bearing threads without becoming another raw
    goal transcript store.
    """
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


def _goal_authority_sources(goals: dict[str, dict]) -> dict:
    mtime_ms = _path_mtime_ms(CODEX_GOALS_DB)
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
    }
    if mtime_ms is not None:
        payload["mtime_ms"] = mtime_ms
        payload["mtime"] = _iso_from_epoch_ms(mtime_ms)
    return payload


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
            "mission_index": {
                "state": mission_state,
                "provider": row.get("provider") or "codex",
                "session_id": thread_id,
                "mission_key": f"codex:{thread_id}",
                "title": (
                    row.get("display_title")
                    or row.get("title")
                    or title_record.get("thread_name")
                    or ""
                ),
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
    title_marker = "old_prefix" if _has_operator_old_title_prefix(source_title or operator_alias or title or "") else "none"
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
    sidechains = _claude_subagent_sidechain_summaries(session_file) if provider == "claude_code" else []
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


MISSION_SUMMARY_CACHE_SCHEMA = "agent_trace_structurer_mission_summary_cache_v7"
MISSION_SUMMARY_CACHE_LEGACY_SCHEMAS = (
    "agent_trace_structurer_mission_summary_cache_v6",
    "agent_trace_structurer_mission_summary_cache_v5",
    "agent_trace_structurer_mission_summary_cache_v4",
    "agent_trace_structurer_mission_summary_cache_v3",
    "agent_trace_structurer_mission_summary_cache_v2",
)
MISSION_INDEX_STALE_REPARSE_BUDGET = 1
MISSION_INDEX_RECENT_STALE_REPARSE_SECONDS = 25 * 60


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
    return {
        "provider": provider,
        "session_id": session_id,
        "session_file": str(session_file),
        "mtime_ns": int(mtime_ns or 0),
        "mtime_epoch": float(mtime_epoch or 0),
        "size_bytes": int(size_bytes or 0),
    }


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
                stale_summary["cache_current_mtime_ns"] = meta.get("mtime_ns")
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


def _classify_artifact_freshness(
    latest_completed_turn: dict | None,
    latest_clip_meta: dict,
) -> dict:
    """Compare the latest completed turn against the most recent
    cli_prompt_trace clip for this session.

    Returns {state: current|stale|missing|partial_only, reason: ...}."""
    if latest_completed_turn is None:
        return {"state": "partial_only", "reason": "no_completed_turn_in_session"}
    if not latest_clip_meta:
        return {"state": "missing", "reason": "no_artifact"}
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


def build_mission_index(*, cwd: Path | None = None, limit: int = 30) -> dict:
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
        "stored": 0,
    }
    cache_dirty = False
    stale_reparse_remaining = MISSION_INDEX_STALE_REPARSE_BUDGET
    rows: list[dict] = []
    candidates = _enumerate_candidates("auto", cwd or Path.cwd())
    for c in candidates[:limit]:
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
            }
        desktop = (claude_desktop_titles or {}).get(c["session_id"]) or {}
        # Parse session lazily — skip for archived rows (won't render anyway).
        completed_active: dict = {}
        summary_cache_state = "skipped_archived" if desktop.get("is_archived") else "unknown"
        if not desktop.get("is_archived"):
            session_path = Path(c["session_file"])
            source_meta = _session_file_meta(c["provider"], c["session_id"], session_path, c)
            cached_summary, cache_state = _mission_summary_cache_lookup(summary_cache, source_meta)
            if cache_state == "stale" and _mission_source_recently_changed(source_meta):
                cache_stats["recent_stale_forced"] += 1
                cache_state = "recent_stale_forced"
            if cache_state == "stale" and stale_reparse_remaining <= 0:
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
        latest_completed = completed_active.get("latest_completed_turn")
        active_turn = completed_active.get("active_turn")
        preferred_trace_turn = completed_active.get("preferred_trace_turn")
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
        # Enrich latest_clip_meta with prompt_sha16 from full row if present
        if last_clip:
            cpt_full = last_clip.get("cli_prompt_trace") or {}
            if "prompt_sha16" not in last_clip_meta and cpt_full.get("prompt_sha16"):
                last_clip_meta["prompt_sha16"] = cpt_full["prompt_sha16"]
            if "prompt_char_count" not in last_clip_meta and cpt_full.get("prompt_char_count"):
                last_clip_meta["prompt_char_count"] = cpt_full["prompt_char_count"]
        artifact_freshness = _classify_artifact_freshness(preferred_trace_turn or latest_completed, last_clip_meta)
        goal = codex_thread_goals.get(c["session_id"]) if c["provider"] == "codex" else None
        goal_priority = _goal_sort_priority(goal)
        rows.append({
            "provider": c["provider"],
            "session_id": c["session_id"],
            "session_file": c["session_file"],
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
            "last_activity_at": desktop.get("last_activity_at") or c["mtime_utc"],
            "completed_turns_hint": desktop.get("completed_turns") or 0,
            "is_archived": bool(desktop.get("is_archived")),
            "model": desktop.get("model") or "",
            "mission_ordinal_start": ord_start,
            "mission_ordinal_end": ord_end,
            "mission_ordinal_key": ord_end if ord_end is not None else (ord_start if ord_start is not None else None),
            "mission_sort_source": ord_source or "no_ordinal",
            "artifact_refs": artifact_refs,
            "latest_clip": last_clip_meta,
            "latest_completed_turn": latest_completed,
            "active_turn": active_turn,
            "stale_active_turn": completed_active.get("stale_active_turn"),
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
        elif _has_operator_old_title_prefix(r.get("source_title") or r.get("operator_alias") or r.get("title") or r.get("short_label") or ""):
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
    # Default sort: most-recently-finished trace first. Operator wants the latest
    # completed work surfaced first; mission number is metadata for display, not
    # the primary order. Ordinal sort remains available via mission_ordinal_key
    # for an alternate sort mode in the UI.
    def _sort_key(r: dict) -> tuple:
        # Prefer latest_completed_turn.completed_at, fall back to active_turn
        # started_at, then last_activity_at, then mtime_utc.
        completed_at = ""
        lct = r.get("latest_completed_turn") or {}
        if lct.get("completed_at"):
            completed_at = lct["completed_at"]
        elif (r.get("active_turn") or {}).get("started_at"):
            completed_at = (r["active_turn"] or {})["started_at"]
        last = r.get("last_activity_at") or r.get("mtime_utc") or ""
        if isinstance(last, (int, float)):
            try:
                last = _dt.datetime.fromtimestamp(last / 1000, _dt.timezone.utc).isoformat()
            except Exception:
                last = ""
        # Negative sort: empty strings sort earlier, so flip: rows WITH a
        # completed_at first (descending), then by last_activity desc.
        return (
            0 if completed_at else 1,
            # Negate via reverse=True at sort call; tuples sort lexically.
            completed_at,
            last,
        )
    active_rows.sort(key=_sort_key, reverse=True)
    # Re-sort: above gives most-recent first within "have completed_at" group, but
    # _sort_key tuple's first element (0 vs 1) needs the WITH-COMPLETED rows to
    # appear first when sorted descending. After reverse=True they actually fall
    # last. Fix by separating groups explicitly.
    def _activity_key(r: dict) -> str:
        """Normalize last_activity to ISO string (Claude desktop stores epoch-ms ints)."""
        v = r.get("last_activity_at") or r.get("mtime_utc") or ""
        if isinstance(v, (int, float)):
            try:
                return _dt.datetime.fromtimestamp(v / 1000, _dt.timezone.utc).isoformat()
            except Exception:
                return ""
        return str(v)
    with_completed = [r for r in active_rows if (r.get("latest_completed_turn") or {}).get("completed_at")]
    without_completed = [r for r in active_rows if not (r.get("latest_completed_turn") or {}).get("completed_at")]
    with_completed.sort(
        key=lambda r: (int(r.get("goal_sort_priority") or 0), str(r["latest_completed_turn"]["completed_at"])),
        reverse=True,
    )
    without_completed.sort(key=lambda r: (int(r.get("goal_sort_priority") or 0), _activity_key(r)), reverse=True)
    active_rows = with_completed + without_completed
    mission_goal_count = sum(1 for r in rows if r.get("has_goal"))
    active_mission_goal_count = sum(1 for r in rows if (r.get("goal") or {}).get("status") == "active")
    goal_threads = _goal_thread_roster(codex_thread_goals, rows, codex_thread_records)
    active_goal_thread_count = sum(1 for g in goal_threads if g.get("status") == "active")
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
        "sort_mode": "finished_at_desc",
        "perf": {
            "duration_ms": duration_ms,
            "candidate_count": len(candidates),
            "summary_cache": cache_stats,
            "summary_cache_path": str(TRACE_STRUCTURER_MISSION_SUMMARY_CACHE),
        },
        "title_authority": title_authority,
        "goal_authority": goal_authority,
        "goal_threads": goal_threads,
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
            ["node", "--input-type=module", "-e", helper],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        return {"ok": False, "error": "node binary not on PATH"}
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "error": f"parser.mjs timed out after {e.timeout}s while building Structurer clip",
            "stdout": (e.stdout or "")[-500:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-500:] if isinstance(e.stderr, str) else "",
        }
    if proc.returncode != 0:
        return {"ok": False, "error": f"parser.mjs failed: {proc.stderr[:500]}"}
    try:
        return {"ok": True, **json.loads(proc.stdout or "{}")}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"parser output not JSON: {e}"}


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
    sel.add_argument("--check", action="store_true", help="Parseability probe; exits 0/1 with JSON status")

    ap.add_argument("--format", choices=["compact", "full", "trace-paste", "json", "thread-closeouts"], default="compact",
                    help="thread-closeouts emits session metadata, prompt refs, and exact final closeout messages without tool bodies; trace-paste emits Agent Trace Structurer parser-compatible markers (Bash/Read/Ran/Success...)")
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

    args = ap.parse_args()

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()

    if args.sessions_mode:
        print(list_session_candidates(args.provider, cwd))
        return 0

    if args.mission_index_mode:
        index = build_mission_index(cwd=cwd)
        body = json.dumps(index, indent=2, ensure_ascii=False)
        try:
            TRACE_STRUCTURER_BASE.mkdir(parents=True, exist_ok=True)
            tmp = TRACE_STRUCTURER_MISSION_INDEX.with_suffix(".json.tmp")
            tmp.write_text(body, encoding="utf-8")
            tmp.replace(TRACE_STRUCTURER_MISSION_INDEX)
            sys.stderr.write(
                f"# wrote mission_index ({index['row_count']} rows) to {TRACE_STRUCTURER_MISSION_INDEX}\n"
            )
        except Exception as e:
            sys.stderr.write(f"# warning: could not update canonical mission index: {e}\n")
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
