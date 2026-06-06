#!/usr/bin/env python3
"""Session analyzer — multi-lens diagnostics over out-of-repo agent session storage.

The navigation plane prescribes what the agent *should* do. This analyzer reads
what past agents *actually* did from the two local stores and emits structured
diagnostics. The delta is the training signal for the next nav refinement.

Stores (verified 2026-04-21):
  - ~/.claude/projects/<project-slug>/<session-uuid>.jsonl
  - ~/.codex/session_index.jsonl + ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl

Lenses emit structured findings; each lens names the nav-refinement shape it
suggests so the operator can route directly to the right skill or standard.

Usage:
  ./repo-python tools/meta/observability/session_analyzer.py --lens all --last 20
  ./repo-python tools/meta/observability/session_analyzer.py --lens all --last 20 --summary
  ./repo-python tools/meta/observability/session_analyzer.py --lens ladder-skip --last 50
  ./repo-python tools/meta/observability/session_analyzer.py --lens route-misses --last 20 --write-route-miss-candidates state/session_diagnostics/route_miss_candidates.json
  ./repo-python tools/meta/observability/session_analyzer.py --lens hotspots --last 20 --write-context-pressure-hotspots state/session_diagnostics/context_pressure_hotspots.json
  ./repo-python tools/meta/observability/session_analyzer.py --lens latency --store codex --after 2026-04-20

Paired skill: codex/doctrine/skills/kernel/agent_session_diagnostics.md
Paired paper module: codex/doctrine/paper_modules/unified_navigation_layer.md
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shlex
import sys
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator

from system.lib.work_ledger_commands import (
    WORK_LEDGER_CLAIM_CARDS_COMMAND,
    WORK_LEDGER_SEED_SPEED_COMMAND,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
CODEX_ROOT = HOME / ".codex"
TRACE_OBSERVATORY_DEFAULT_PATH = "state/session_diagnostics/trace_observatory_projection.json"
TRACE_OBSERVATORY_EMIT_LIMIT = 5
TRACE_IMPROVEMENT_SUMMARY_ROW_LIMIT = 5
COMMAND_EFFICIENCY_ACTION_EMIT_LIMIT = 3
TRACE_OBSERVATORY_SUMMARY_RATIO_LIMIT = 1.0
CODEX_SUMMARY_SCAN_MAX_BYTES = 4 * 1024 * 1024
CODEX_SUMMARY_SCAN_HEAD_BYTES = 128 * 1024
PROCESS_SUMMARY_EXPLICIT_SESSION_LOOKUP_LIMIT = 80
TRACE_SUMMARY_COMPACT_PRESERVED_CONTRACT_KEYS = (
    "context_pressure_summary_first_contract",
    "typed_route_replacement_contract",
    "dominant_shell_shape_contract",
    "command_usage_error_contract",
    "command_contract_boundary_contract",
    "route_discoverability_resolution_contract",
    "claim_contention_boundary_contract",
    "experience_family_boundary_contracts",
    "runtime_readiness_contract",
    "paper_module_compression_contract",
)
TRACE_SUMMARY_SUPPORTING_DRILLDOWN_PREVIEW_LIMIT = 3
_TRACE_BOARD_REQUIRED_ROW_FIELDS = (
    "row_id",
    "symptom_family",
    "mode",
    "evidence_refs",
    "recurrence",
    "impact",
    "candidate_owner",
    "candidate_mutation",
    "disconfirming_check",
    "next_command",
    "receipt_needed",
)
_TRACE_BOARD_RAW_BODY_FIELD_KEYS = {
    "content",
    "hidden_reasoning",
    "message_body",
    "operator_text",
    "prompt",
    "prompt_body",
    "raw_body",
    "raw_trace",
    "stderr",
    "stdout",
    "tool_output",
    "tool_stderr",
    "tool_stdout",
    "transcript",
}

# Native-tool verbs that should not be run as bash shell-outs in this repo.
# When a session's Bash first-word is in this set, it's a ladder-skip signal:
# the agent should have reached for Glob/Grep/Read instead.
BASH_VERBS_SHOULD_BE_NATIVE = {
    "ls", "find", "cat", "head", "tail", "grep", "rg",
    "wc", "awk", "sed", "echo",
}

# Bash verbs that correctly invoke kernel / repo tooling (not ladder-skip).
BASH_VERBS_REPO_TOOLING = {
    "repo-python", "repo-pytest", "repo-env", "repo-bun", "repo-node",
    "python3", "pytest", "git", "jq", "sqlite3",
}
LADDER_SKIP_TYPED_ROUTE_REPLACEMENT = (
    './repo-python kernel.py --context-pack "<task>" --context-budget 12000'
)
LADDER_SKIP_COMMAND_CARD_DEBUG = (
    './repo-python kernel.py --command-card "shell discovery before typed route" --debug'
)


@dataclass
class ClaudeSessionFacts:
    path: Path
    session_id: str
    records: int = 0
    first_ts: str | None = None
    last_ts: str | None = None
    first_user: str | None = None
    user_interrupted: bool = False
    tool_histogram: collections.Counter[str] = field(default_factory=collections.Counter)
    bash_verbs: collections.Counter[str] = field(default_factory=collections.Counter)
    bad_bash: collections.Counter[str] = field(default_factory=collections.Counter)
    good_bash: collections.Counter[str] = field(default_factory=collections.Counter)
    kernel_nav_calls: collections.Counter[str] = field(default_factory=collections.Counter)
    reads: collections.Counter[str] = field(default_factory=collections.Counter)
    edits: collections.Counter[str] = field(default_factory=collections.Counter)
    grep_before_nav: int = 0
    rereads: list[dict[str, Any]] = field(default_factory=list)
    user_messages: list[tuple[str, str]] = field(default_factory=list)
    tool_error_lines: collections.Counter[str] = field(default_factory=collections.Counter)

    @property
    def wallclock_s(self) -> float | None:
        return _ts_diff(self.first_ts, self.last_ts)


@dataclass
class CodexSessionFacts:
    path: Path
    records: int = 0
    function_calls: int = 0
    turns: int = 0
    compactions: int = 0
    first_ts: str | None = None
    last_ts: str | None = None
    user_messages: list[tuple[str, str]] = field(default_factory=list)
    scan_mode: str = "full"
    file_size_bytes: int = 0
    bytes_scanned: int = 0
    scan_truncated: bool = False

    @property
    def wallclock_s(self) -> float | None:
        return _ts_diff(self.first_ts, self.last_ts)


@dataclass
class SessionDiagnosticsFacts:
    claude: list[ClaudeSessionFacts]
    codex: list[CodexSessionFacts]


# ---------------------------------------------------------------------------
# Store discovery


def project_slug_for_cwd(cwd: Path) -> str:
    """Claude Code replaces both `/` and `_` with `-` in the project slug."""
    return str(cwd).replace("/", "-").replace("_", "-")


def resolve_claude_project_dir(project_slug: str | None = None) -> Path:
    """Resolve the Claude Code project directory without dropping the leading dash."""
    raw_slug = project_slug or project_slug_for_cwd(REPO_ROOT)
    candidates: list[Path] = []
    for slug in (
        raw_slug,
        raw_slug if raw_slug.startswith("-") else f"-{raw_slug}",
        raw_slug.lstrip("-"),
    ):
        path = CLAUDE_PROJECTS / slug
        if path not in candidates:
            candidates.append(path)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def claude_session_files(project_slug: str | None = None) -> list[Path]:
    base = resolve_claude_project_dir(project_slug)
    if not base.exists():
        return []
    return _existing_files_by_mtime(base.glob("*.jsonl"))


def codex_session_index() -> list[dict[str, Any]]:
    idx = CODEX_ROOT / "session_index.jsonl"
    if not idx.exists():
        return []
    rows = []
    with idx.open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return sorted(rows, key=lambda r: r.get("updated_at", ""), reverse=True)


def codex_rollout_files() -> list[Path]:
    base = CODEX_ROOT / "sessions"
    if not base.exists():
        return []
    return _existing_files_by_mtime(base.rglob("rollout-*.jsonl"))


def _existing_files_by_mtime(paths: Iterable[Path]) -> list[Path]:
    rows: list[tuple[float, Path]] = []
    for path in paths:
        try:
            rows.append((path.stat().st_mtime, path))
        except FileNotFoundError:
            continue
    return [path for _, path in sorted(rows, key=lambda row: row[0], reverse=True)]


def filter_by_window(files: list[Path], after: str | None, before: str | None) -> list[Path]:
    def in_win(mtime: float) -> bool:
        t = datetime.fromtimestamp(mtime, timezone.utc)
        if after:
            a = datetime.fromisoformat(after.replace("Z", "+00:00"))
            if a.tzinfo is None:
                a = a.replace(tzinfo=timezone.utc)
            if t < a:
                return False
        if before:
            b = datetime.fromisoformat(before.replace("Z", "+00:00"))
            if b.tzinfo is None:
                b = b.replace(tzinfo=timezone.utc)
            if t > b:
                return False
        return True
    selected: list[Path] = []
    for f in files:
        try:
            mtime = f.stat().st_mtime
        except FileNotFoundError:
            continue
        if in_win(mtime):
            selected.append(f)
    return selected


# ---------------------------------------------------------------------------
# Claude session parsing


@lru_cache(maxsize=2048)
def _records_for_path(path_str: str) -> tuple[dict, ...]:
    """Parse a JSONL session file once per build_report invocation.

    Cached at module scope so multi-lens runs reuse parsed records instead of
    re-walking the same file 8+ times. build_report / build_summary_report
    call cache_clear() at entry to keep cached state scoped to a single
    invocation (test isolation; long-lived in-process callers always get a
    fresh parse for the current invocation).
    """
    try:
        stream = open(path_str)
    except FileNotFoundError:
        return ()
    records: list[dict] = []
    with stream as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return tuple(records)


def _iter_jsonl(path: Path) -> Iterator[dict]:
    yield from _records_for_path(str(path))


def claude_tool_uses(path: Path) -> Iterator[tuple[str, dict]]:
    for d in _iter_jsonl(path):
        m = d.get("message")
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for item in c:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                yield item.get("name", "?"), item.get("input") or {}


def claude_session_meta(path: Path) -> dict[str, Any]:
    first_ts, last_ts = None, None
    n_rec = 0
    first_user_text = None
    interrupted = False
    for d in _iter_jsonl(path):
        n_rec += 1
        ts = d.get("timestamp")
        if ts:
            if first_ts is None:
                first_ts = ts
            last_ts = ts
        if first_user_text is None and d.get("type") == "user":
            m = d.get("message", {})
            c = m.get("content") if isinstance(m, dict) else None
            if isinstance(c, list):
                for it in c:
                    if isinstance(it, dict) and it.get("type") == "text":
                        txt = it.get("text") or ""
                        first_user_text = txt[:300]
                        if "[Request interrupted by user" in txt:
                            interrupted = True
                        break
            elif isinstance(c, str):
                first_user_text = c[:300]
        if d.get("type") == "user":
            m = d.get("message", {})
            c = m.get("content") if isinstance(m, dict) else None
            if isinstance(c, list):
                for it in c:
                    if isinstance(it, dict) and "[Request interrupted" in (it.get("text") or ""):
                        interrupted = True
    return {
        "path": str(path),
        "session_id": path.stem,
        "records": n_rec,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "wallclock_s": _ts_diff(first_ts, last_ts),
        "first_user": first_user_text,
        "user_interrupted": interrupted,
    }


def _ts_diff(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    try:
        da = datetime.fromisoformat(a.replace("Z", "+00:00"))
        db = datetime.fromisoformat(b.replace("Z", "+00:00"))
        return (db - da).total_seconds()
    except Exception:
        return None


def _bash_first_word(command: str) -> str:
    parts = command.strip().split()
    if not parts:
        return ""
    first = parts[0]
    if first in {"env", "sudo"} and len(parts) > 1:
        first = parts[1]
    if first.startswith("./"):
        first = first.split("/")[-1]
    return first


def _timestamp_from_line(line: str) -> str | None:
    key = '"timestamp"'
    idx = line.find(key)
    if idx < 0:
        return None
    colon = line.find(":", idx + len(key))
    if colon < 0:
        return None
    start = line.find('"', colon + 1)
    if start < 0:
        return None
    end = line.find('"', start + 1)
    if end < 0:
        return None
    return line[start + 1:end]


def _timestamp_from_bytes_at(data: bytes, idx: int) -> str | None:
    key = b'"timestamp"'
    if idx < 0:
        return None
    colon = data.find(b":", idx + len(key))
    if colon < 0:
        return None
    start = data.find(b'"', colon + 1)
    if start < 0:
        return None
    end = data.find(b'"', start + 1)
    if end < 0:
        return None
    try:
        return data[start + 1:end].decode("utf-8")
    except UnicodeDecodeError:
        return None


def _first_timestamp_from_bytes(data: bytes) -> str | None:
    return _timestamp_from_bytes_at(data, data.find(b'"timestamp"'))


def _last_timestamp_from_bytes(data: bytes) -> str | None:
    return _timestamp_from_bytes_at(data, data.rfind(b'"timestamp"'))


def _jsonl_record_count(data: bytes) -> int:
    if not data:
        return 0
    records = data.count(b"\n")
    if not data.endswith(b"\n"):
        records += 1
    return records


_CODEX_MARKER_BYTES_RE = re.compile(
    rb'(?<!\\)"type"\s*:\s*(?<!\\)"(function_call|compacted|task_started)"'
)


def _codex_marker_counts(data: bytes) -> collections.Counter[bytes]:
    return collections.Counter(match.group(1) for match in _CODEX_MARKER_BYTES_RE.finditer(data))


def _json_line_has_string_field(line: str, field: str, value: str) -> bool:
    if f'"{field}":"{value}"' in line or f'"{field}": "{value}"' in line:
        return True
    if f'"{field}"' not in line or f'"{value}"' not in line:
        return False
    return re.search(
        rf'"{re.escape(field)}"\s*:\s*"{re.escape(value)}"',
        line,
    ) is not None


def _codex_user_texts_from_line(line: str) -> list[str]:
    if '"response_item"' not in line or '"user"' not in line:
        return []
    if not _json_line_has_string_field(line, "type", "response_item"):
        return []
    if not _json_line_has_string_field(line, "role", "user"):
        return []
    if '"input_text"' not in line and '"text"' not in line:
        return []
    try:
        record = json.loads(line)
    except Exception:
        return []
    payload = record.get("payload") or {}
    if payload.get("type") != "message" or payload.get("role") != "user":
        return []
    content = payload.get("content") or []
    if not isinstance(content, list):
        return []
    texts: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") not in ("input_text", "text"):
            continue
        text = str(item.get("text") or "")
        if text:
            texts.append(text)
    return texts


def _codex_assistant_texts_from_line(line: str) -> list[str]:
    if '"response_item"' not in line or '"assistant"' not in line:
        return []
    if not _json_line_has_string_field(line, "type", "response_item"):
        return []
    if not _json_line_has_string_field(line, "role", "assistant"):
        return []
    if '"output_text"' not in line and '"text"' not in line:
        return []
    try:
        record = json.loads(line)
    except Exception:
        return []
    payload = record.get("payload") or {}
    if payload.get("type") != "message" or payload.get("role") != "assistant":
        return []
    content = payload.get("content") or []
    if not isinstance(content, list):
        return []
    texts: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") not in ("output_text", "text"):
            continue
        text = str(item.get("text") or "")
        if text:
            texts.append(text)
    return texts


def _codex_session_facts_fast(
    path: Path,
    *,
    experience_buckets: dict[str, list[dict[str, Any]]] | None = None,
    max_scan_bytes: int | None = None,
) -> CodexSessionFacts:
    facts = CodexSessionFacts(path=path)
    try:
        stat = path.stat()
    except FileNotFoundError:
        return facts
    facts.file_size_bytes = int(stat.st_size)
    if max_scan_bytes is not None and stat.st_size > max_scan_bytes:
        head_bytes = min(CODEX_SUMMARY_SCAN_HEAD_BYTES, max(max_scan_bytes // 4, 0))
        tail_bytes = max(max_scan_bytes - head_bytes, 0)
        try:
            with path.open("rb") as stream:
                head = stream.read(head_bytes)
                if tail_bytes:
                    stream.seek(max(0, stat.st_size - tail_bytes))
                    tail = stream.read(tail_bytes)
                else:
                    tail = b""
        except FileNotFoundError:
            return facts
        data = head + (b"\n" + tail if tail else b"")
        facts.scan_mode = "head_tail_sample"
        facts.scan_truncated = True
    else:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return facts
        facts.scan_mode = "full"
        facts.scan_truncated = False
    facts.bytes_scanned = len(data)
    facts.records = _jsonl_record_count(data)
    facts.first_ts = _first_timestamp_from_bytes(data)
    facts.last_ts = _last_timestamp_from_bytes(data)
    marker_counts = _codex_marker_counts(data)
    facts.function_calls = marker_counts[b"function_call"]
    facts.compactions = marker_counts[b"compacted"]
    facts.turns = marker_counts[b"task_started"]
    needs_user_texts = b'"response_item"' in data and b'"user"' in data
    needs_assistant_texts = (
        experience_buckets is not None
        and b'"response_item"' in data
        and b'"assistant"' in data
    )
    if needs_user_texts or needs_assistant_texts:
        session_label = path.name[:55]
        for raw_line in data.splitlines():
            if b'"response_item"' not in raw_line:
                continue
            line: str | None = None
            ts = ""
            if needs_user_texts and b'"user"' in raw_line:
                line = raw_line.decode("utf-8", errors="replace")
                ts = _timestamp_from_line(line) or ""
                for text in _codex_user_texts_from_line(line):
                    facts.user_messages.append((ts, text))
            if needs_assistant_texts and b'"assistant"' in raw_line:
                if line is None:
                    line = raw_line.decode("utf-8", errors="replace")
                    ts = _timestamp_from_line(line) or ""
                for text in _codex_assistant_texts_from_line(line):
                    _record_experience_friction_text(
                        experience_buckets,
                        source="codex",
                        session=session_label,
                        ts=ts,
                        text=text,
                    )
    return facts


def _claude_summary_record_may_need_parse(line: str) -> bool:
    if '"tool_use"' in line and _json_line_has_string_field(line, "type", "tool_use"):
        return True
    if '"user"' in line and _json_line_has_string_field(line, "type", "user"):
        return True
    if '"assistant"' not in line or not _json_line_has_string_field(line, "type", "assistant"):
        return False
    return _line_may_hold_experience_friction(line)


def _claude_summary_facts_fast(
    path: Path,
    *,
    experience_buckets: dict[str, list[dict[str, Any]]] | None = None,
) -> ClaudeSessionFacts:
    """Raw-line Claude summary scan that parses only rows used by summary lenses."""
    facts = ClaudeSessionFacts(path=path, session_id=path.stem[:12])
    per_read = collections.Counter()
    nav_seen = False
    try:
        stream = path.open("r", encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return facts
    with stream as f:
        last_timestamp_line: str | None = None
        for line in f:
            if not line or line == "\n":
                continue
            facts.records += 1
            if '"timestamp"' in line:
                if facts.first_ts is None:
                    facts.first_ts = _timestamp_from_line(line)
                last_timestamp_line = line
            if not _claude_summary_record_may_need_parse(line):
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            ts = str(record.get("timestamp") or "")

            record_type = record.get("type")
            message = record.get("message") if isinstance(record.get("message"), dict) else {}
            content = message.get("content") if isinstance(message, dict) else None

            if record_type == "user":
                text_items: list[str] = []
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "text":
                            text = str(item.get("text") or "")
                            if text:
                                text_items.append(text)
                        elif item.get("type") == "tool_result":
                            body = item.get("content") or ""
                            if isinstance(body, list):
                                body = next(
                                    (b.get("text", "") for b in body if isinstance(b, dict)),
                                    "",
                                )
                            signature = _tool_error_signature(body)
                            if signature:
                                facts.tool_error_lines[signature] += 1
                elif isinstance(content, str) and content:
                    text_items.append(content)

                for text in text_items:
                    if facts.first_user is None:
                        facts.first_user = text[:300]
                    if "[Request interrupted" in text:
                        facts.user_interrupted = True
                    facts.user_messages.append((ts or "", text))

            if record_type == "assistant" and experience_buckets is not None and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        _record_experience_friction_text(
                            experience_buckets,
                            source="claude",
                            session=facts.session_id,
                            ts=ts or "",
                            text=str(item.get("text") or ""),
                        )

            if not isinstance(content, list):
                continue
            for item in content:
                if not (isinstance(item, dict) and item.get("type") == "tool_use"):
                    continue
                tool_name = str(item.get("name") or "?")
                tool_input = item.get("input") if isinstance(item.get("input"), dict) else {}
                facts.tool_histogram[tool_name] += 1
                if tool_name == "Read":
                    read_path = str(tool_input.get("file_path") or "?")
                    per_read[read_path] += 1
                    facts.reads[read_path.replace(str(REPO_ROOT) + "/", "")] += 1
                elif tool_name in ("Edit", "Write"):
                    edit_path = str(tool_input.get("file_path") or "?")
                    facts.edits[edit_path.replace(str(REPO_ROOT) + "/", "")] += 1
                elif tool_name == "Grep" and not nav_seen:
                    facts.grep_before_nav += 1
                elif tool_name == "Bash":
                    command = str(tool_input.get("command") or "").strip()
                    first = _bash_first_word(command)
                    if first:
                        facts.bash_verbs[first] += 1
                    if first in BASH_VERBS_SHOULD_BE_NATIVE:
                        facts.bad_bash[first] += 1
                    elif first in BASH_VERBS_REPO_TOOLING:
                        facts.good_bash[first] += 1
                    if "kernel.py" in command:
                        for flag in (
                            "--info", "--pulse", "--paper-module", "--docs-route",
                            "--navigate", "--shards", "--locate", "--compile",
                            "--lens", "--working-set", "--frontier",
                        ):
                            if flag in command:
                                facts.kernel_nav_calls[flag] += 1
                                nav_seen = True
                                break
        if last_timestamp_line is not None:
            facts.last_ts = _timestamp_from_line(last_timestamp_line)
    reread = [(read_path, count) for read_path, count in per_read.items() if count >= 3]
    if reread:
        facts.rereads = [
            {"path": read_path.replace(str(REPO_ROOT) + "/", ""), "reads": count}
            for read_path, count in reread
        ]
    return facts


def _build_session_diagnostics_facts(
    claude_files: list[Path],
    codex_files: list[Path],
) -> SessionDiagnosticsFacts:
    """Scan selected session files once and retain bounded in-process facts."""
    claude_facts: list[ClaudeSessionFacts] = []
    for fp in claude_files:
        session_id = fp.stem[:12]
        facts = ClaudeSessionFacts(path=fp, session_id=session_id)
        per_read = collections.Counter()
        nav_seen = False

        for record in _iter_jsonl(fp):
            facts.records += 1
            ts = str(record.get("timestamp") or "")
            if ts:
                if facts.first_ts is None:
                    facts.first_ts = ts
                facts.last_ts = ts

            if record.get("type") == "user":
                message = record.get("message") if isinstance(record.get("message"), dict) else {}
                content = message.get("content") if isinstance(message, dict) else None
                text_items: list[str] = []
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "text":
                            text = str(item.get("text") or "")
                            if text:
                                text_items.append(text)
                        elif item.get("type") == "tool_result":
                            body = item.get("content") or ""
                            if isinstance(body, list):
                                body = next(
                                    (b.get("text", "") for b in body if isinstance(b, dict)),
                                    "",
                                )
                            signature = _tool_error_signature(body)
                            if signature:
                                facts.tool_error_lines[signature] += 1
                elif isinstance(content, str) and content:
                    text_items.append(content)

                for text in text_items:
                    if facts.first_user is None:
                        facts.first_user = text[:300]
                    if "[Request interrupted" in text:
                        facts.user_interrupted = True
                    facts.user_messages.append((ts, text))

            message = record.get("message") if isinstance(record.get("message"), dict) else {}
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for item in content:
                if not (isinstance(item, dict) and item.get("type") == "tool_use"):
                    continue
                tool_name = str(item.get("name") or "?")
                tool_input = item.get("input") if isinstance(item.get("input"), dict) else {}
                facts.tool_histogram[tool_name] += 1
                if tool_name == "Read":
                    path = str(tool_input.get("file_path") or "?")
                    per_read[path] += 1
                    facts.reads[path.replace(str(REPO_ROOT) + "/", "")] += 1
                elif tool_name in ("Edit", "Write"):
                    path = str(tool_input.get("file_path") or "?")
                    facts.edits[path.replace(str(REPO_ROOT) + "/", "")] += 1
                elif tool_name == "Grep" and not nav_seen:
                    facts.grep_before_nav += 1
                elif tool_name == "Bash":
                    command = str(tool_input.get("command") or "").strip()
                    first = _bash_first_word(command)
                    if first:
                        facts.bash_verbs[first] += 1
                    if first in BASH_VERBS_SHOULD_BE_NATIVE:
                        facts.bad_bash[first] += 1
                    elif first in BASH_VERBS_REPO_TOOLING:
                        facts.good_bash[first] += 1
                    if "kernel.py" in command:
                        for flag in (
                            "--info", "--pulse", "--paper-module", "--docs-route",
                            "--navigate", "--shards", "--locate", "--compile",
                            "--lens", "--working-set", "--frontier",
                        ):
                            if flag in command:
                                facts.kernel_nav_calls[flag] += 1
                                nav_seen = True
                                break

        reread = [(path, count) for path, count in per_read.items() if count >= 3]
        if reread:
            facts.rereads = [
                {"path": path.replace(str(REPO_ROOT) + "/", ""), "reads": count}
                for path, count in reread
            ]
        claude_facts.append(facts)

    codex_facts: list[CodexSessionFacts] = []
    for fp in codex_files:
        codex_facts.append(_codex_session_facts_fast(fp))

    return SessionDiagnosticsFacts(claude=claude_facts, codex=codex_facts)


# ---------------------------------------------------------------------------
# Codex rollout parsing


def codex_rollout_meta(path: Path) -> dict[str, Any]:
    n_rec = 0
    n_fn_calls = 0
    n_compacted = 0
    first_ts, last_ts = None, None
    turns = 0
    for d in _iter_jsonl(path):
        n_rec += 1
        ts = d.get("timestamp")
        if ts:
            if first_ts is None:
                first_ts = ts
            last_ts = ts
        pl = d.get("payload") or {}
        if pl.get("type") == "function_call":
            n_fn_calls += 1
        if d.get("type") == "compacted":
            n_compacted += 1
        if pl.get("type") == "task_started":
            turns += 1
    return {
        "path": str(path),
        "records": n_rec,
        "function_calls": n_fn_calls,
        "turns": turns,
        "compactions": n_compacted,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "wallclock_s": _ts_diff(first_ts, last_ts),
    }


# ---------------------------------------------------------------------------
# Lenses


def lens_histogram(claude_files: list[Path], limit: int) -> dict[str, Any]:
    """Aggregate tool-call histogram + Bash-verb histogram across sessions."""
    tools = collections.Counter()
    bash_verbs = collections.Counter()
    total_records = 0
    per_session_tool_totals = []
    for fp in claude_files:
        local = collections.Counter()
        for tn, ip in claude_tool_uses(fp):
            tools[tn] += 1
            local[tn] += 1
            if tn == "Bash":
                cmd = (ip.get("command") or "").strip()
                if cmd:
                    first = cmd.split()[0]
                    if first in {"env", "sudo"}:
                        parts = cmd.split()
                        first = parts[1] if len(parts) > 1 else first
                    if first.startswith("./"):
                        first = first.split("/")[-1]
                    bash_verbs[first] += 1
        meta = claude_session_meta(fp)
        total_records += meta["records"]
        per_session_tool_totals.append({
            "session_id": meta["session_id"][:12],
            "records": meta["records"],
            "top_tools": dict(local.most_common(3)),
        })
    return {
        "sessions_analyzed": len(claude_files),
        "total_records": total_records,
        "tool_histogram": tools.most_common(limit),
        "bash_verbs": bash_verbs.most_common(limit),
    }


def lens_hotspots(claude_files: list[Path], limit: int) -> dict[str, Any]:
    """Files read across all sessions — candidates for inline cache / TLDR surface."""
    reads = collections.Counter()
    edits = collections.Counter()
    read_sessions = collections.defaultdict(set)
    for fp in claude_files:
        sess = fp.stem
        for tn, ip in claude_tool_uses(fp):
            path = ip.get("file_path") or ""
            if not path:
                continue
            short = path.replace(str(REPO_ROOT) + "/", "")
            if tn == "Read":
                reads[short] += 1
                read_sessions[short].add(sess)
            elif tn in ("Edit", "Write"):
                edits[short] += 1
    # Rediscovery score: (read_count × distinct_sessions)
    rediscovery = [
        (p, reads[p], len(read_sessions[p]), reads[p] * len(read_sessions[p]))
        for p in reads
    ]
    rediscovery.sort(key=lambda r: -r[3])
    return {
        "sessions_analyzed": len(claude_files),
        "top_reads": [{"path": p, "reads": c} for p, c in reads.most_common(limit)],
        "top_edits": [{"path": p, "edits": c} for p, c in edits.most_common(limit)],
        "rediscovery": [
            {"path": p, "reads": r, "distinct_sessions": s, "score": sc}
            for p, r, s, sc in rediscovery[:limit]
        ],
    }


def lens_ladder_skip(claude_files: list[Path], limit: int) -> dict[str, Any]:
    """Detect patterns where the nav ladder was skipped.

    Signals:
      - Bash verbs that should be native tools (ls, find, grep, cat, head, tail, wc, echo)
      - Same file read >= 3 times in one session (first rung pointed wrong)
      - Grep before any --paper-module / --docs-route / --navigate call
    """
    bad_bash = collections.Counter()
    good_bash = collections.Counter()
    kernel_nav_calls = collections.Counter()
    reread_events = []
    grep_before_nav = 0
    for fp in claude_files:
        per_read = collections.Counter()
        nav_seen = False
        session_grep_before_nav = 0
        for tn, ip in claude_tool_uses(fp):
            if tn == "Read":
                per_read[(ip.get("file_path") or "?")] += 1
            if tn == "Bash":
                cmd = (ip.get("command") or "").strip()
                if not cmd:
                    continue
                first = cmd.split()[0]
                if first.startswith("./"):
                    first = first.split("/")[-1]
                if first in BASH_VERBS_SHOULD_BE_NATIVE:
                    bad_bash[first] += 1
                elif first in BASH_VERBS_REPO_TOOLING:
                    good_bash[first] += 1
                # Detect kernel nav flag invocation
                if "kernel.py" in cmd:
                    for flag in (
                        "--info", "--pulse", "--paper-module", "--docs-route",
                        "--navigate", "--shards", "--locate", "--compile",
                        "--lens", "--working-set", "--frontier",
                    ):
                        if flag in cmd:
                            kernel_nav_calls[flag] += 1
                            nav_seen = True
                            break
            if tn == "Grep" and not nav_seen:
                session_grep_before_nav += 1
        reread = [(p, c) for p, c in per_read.items() if c >= 3]
        if reread:
            reread_events.append({
                "session": fp.stem[:12],
                "rereads": [{"path": p.replace(str(REPO_ROOT) + "/", ""), "reads": c} for p, c in reread],
            })
        grep_before_nav += session_grep_before_nav
    total_bad = sum(bad_bash.values())
    total_good = sum(good_bash.values())
    return {
        "sessions_analyzed": len(claude_files),
        "bash_should_be_native": bad_bash.most_common(limit),
        "bash_repo_tooling": good_bash.most_common(limit),
        "ratio_bad_to_good_bash": round(total_bad / max(total_good, 1), 3),
        "kernel_nav_flag_calls": kernel_nav_calls.most_common(),
        "grep_calls_before_any_nav_flag": grep_before_nav,
        "dominant_shell_shape": _ladder_skip_dominant_shell_shape(
            bad_bash,
            grep_before_nav=grep_before_nav,
        ),
        "reread_events": reread_events[:limit],
    }


def _ladder_skip_dominant_shell_shape(
    bad_bash: collections.Counter[str],
    *,
    grep_before_nav: int,
) -> dict[str, Any]:
    """Compactly classify which shell habit should be replaced first."""
    top = bad_bash.most_common(1)
    top_verb = str(top[0][0]) if top else None
    top_count = int(top[0][1]) if top else 0
    if not top_verb and grep_before_nav <= 0:
        return {
            "schema_version": "ladder_skip_dominant_shell_shape_v0",
            "status": "none",
            "shape": "none",
            "top_verb": None,
            "top_count": 0,
            "grep_before_nav": 0,
        }

    if grep_before_nav > 0 and (
        top_verb in {None, "grep", "rg"} or grep_before_nav >= top_count
    ):
        shape = "shell_search_before_typed_route"
        dominant_signal = "grep_before_nav"
        replacement_hint = (
            "Start with entry/context-pack and the selected option-surface card; "
            "scope rg/grep only after the owner route is known."
        )
    elif top_verb == "echo":
        shape = "shell_banner_or_separator_chain"
        dominant_signal = "bash:echo"
        replacement_hint = (
            "Do not build echo-banner shell chains; split evidence reads into typed "
            "owner routes or parallel bounded reads, then use scoped shell only if "
            "the owner route selected the path set."
        )
    elif top_verb in {"find", "grep", "rg"}:
        shape = "shell_search_before_typed_route"
        dominant_signal = f"bash:{top_verb}"
        replacement_hint = (
            "Use entry/context-pack and option-surface cards before broad search; "
            "use scoped rg only after a typed owner scope exists."
        )
    elif top_verb in {"cat", "head", "tail", "sed", "awk", "wc", "ls"}:
        shape = "shell_read_or_inventory_before_owner_route"
        dominant_signal = f"bash:{top_verb}"
        replacement_hint = (
            "Use a row card, owner summary, or bounded Read after the typed route "
            "selects the file/path scope."
        )
    else:
        shape = "bash_native_before_typed_route"
        dominant_signal = f"bash:{top_verb}"
        replacement_hint = (
            "Replace the shell-first movement with the typed navigation ladder, "
            "then use scoped shell only inside the selected owner scope."
        )

    return {
        "schema_version": "ladder_skip_dominant_shell_shape_v0",
        "status": "observed",
        "shape": shape,
        "dominant_signal": dominant_signal,
        "top_verb": top_verb,
        "top_count": top_count,
        "grep_before_nav": int(grep_before_nav),
        "replacement_route": LADDER_SKIP_TYPED_ROUTE_REPLACEMENT,
        "command_card_debug_route": LADDER_SKIP_COMMAND_CARD_DEBUG,
        "replacement_hint": replacement_hint,
    }


def _ladder_skip_metric_dominant_shell_shape(
    ladder: dict[str, Any],
    *,
    grep_before_nav: int,
) -> dict[str, Any] | None:
    if not isinstance(ladder, dict):
        return None
    existing = ladder.get("dominant_shell_shape")
    if isinstance(existing, dict) and existing.get("shape") not in {None, "", "none"}:
        return existing
    bad_bash: collections.Counter[str] = collections.Counter()
    for row in ladder.get("bash_should_be_native_top") or ladder.get("bash_should_be_native") or []:
        if isinstance(row, dict):
            verb = str(row.get("verb") or row.get("command") or row.get("name") or "").strip()
            count = _coerce_count(row.get("count") or row.get("calls") or row.get("value"))
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            verb = str(row[0] or "").strip()
            count = _coerce_count(row[1])
        else:
            continue
        if verb and count > 0:
            bad_bash[verb] += count
    if bad_bash or grep_before_nav > 0:
        return _ladder_skip_dominant_shell_shape(
            bad_bash,
            grep_before_nav=grep_before_nav,
        )
    return existing if isinstance(existing, dict) else None


_INTERRUPT_MARKER = "[Request interrupted by user"

_CODEX_SQLITE_7D_QUERY = (
    "SELECT COUNT(*), "
    "SUM(CASE WHEN level='ERROR' THEN 1 ELSE 0 END), "
    "SUM(CASE WHEN level='WARN' THEN 1 ELSE 0 END) "
    "FROM logs WHERE ts > strftime('%s','now','-7 day')"
)
_CODEX_SQLITE_7D_DEADLINE_S = 0.025


def _codex_sqlite_7d_deadline_ms() -> int:
    return round(_CODEX_SQLITE_7D_DEADLINE_S * 1000)


def _codex_sqlite_7d_store_scope_omission() -> dict[str, Any]:
    return {
        "status": "omitted_store_scope",
        "logs_7d": None,
        "errors_7d": None,
        "warns_7d": None,
        "reason": "Codex SQLite aggregate skipped because selected store excludes codex.",
        "query_plan": [],
        "deadline_ms": _codex_sqlite_7d_deadline_ms(),
    }


def _sqlite_plan_full_scans_logs(plan_rows: list[str]) -> bool:
    """True when EXPLAIN QUERY PLAN reports a full-table SCAN on `logs`.

    SQLite distinguishes `SCAN` (full table) from `SEARCH ... USING <idx>`
    (index-backed). Treat unindexed SCANs as too expensive for the latency
    lens default path.
    """
    for row in plan_rows:
        upper = row.upper()
        if "SCAN" in upper and "LOGS" in upper and "USING" not in upper:
            return True
    return False


def _codex_sqlite_7d_summary() -> dict[str, Any] | None:
    """Return the 7-day codex log aggregate as a status-bearing dict.

    Gated on EXPLAIN QUERY PLAN: if the aggregate would full-scan `logs`,
    omit it instead of paying the full-scan tax in the latency lens.
    Bounded by a short progress-handler deadline as belt-and-suspenders.
    Returns None when the codex log DB is absent (matches prior behavior).
    """
    db = CODEX_ROOT / "logs_2.sqlite"
    if not db.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except Exception as exc:  # noqa: BLE001 - DB connect boundary
        return {"status": "error", "error": str(exc)}
    try:
        try:
            plan_rows = [
                " ".join(str(col) for col in row)
                for row in con.execute(
                    "EXPLAIN QUERY PLAN " + _CODEX_SQLITE_7D_QUERY
                ).fetchall()
            ]
        except Exception as exc:  # noqa: BLE001 - plan boundary
            return {"status": "error", "error": str(exc), "query_plan": []}
        if _sqlite_plan_full_scans_logs(plan_rows):
            return {
                "status": "omitted_unindexed_scan",
                "logs_7d": None,
                "errors_7d": None,
                "warns_7d": None,
                "reason": (
                    "SQLite query plan would full-scan logs; omitted to keep "
                    "lens_latency cheap. Run an explicit SQLite drilldown "
                    "outside the latency lens, or add an index on logs(ts, "
                    "level) only with operator consent."
                ),
                "query_plan": plan_rows,
                "repair_options": [
                    "run explicit SQLite drilldown outside latency lens",
                    "add an index only with operator consent",
                    "materialize a separate cached projection",
                ],
                "deadline_ms": _codex_sqlite_7d_deadline_ms(),
            }
        deadline = time.perf_counter() + _CODEX_SQLITE_7D_DEADLINE_S
        timed_out = {"hit": False}

        def _interrupt_if_slow() -> int:
            if time.perf_counter() > deadline:
                timed_out["hit"] = True
                return 1
            return 0

        con.set_progress_handler(_interrupt_if_slow, 1000)
        started = time.perf_counter()
        try:
            row = con.execute(_CODEX_SQLITE_7D_QUERY).fetchone()
        except sqlite3.OperationalError as exc:
            if timed_out["hit"]:
                return {
                    "status": "omitted_timeout",
                    "logs_7d": None,
                    "errors_7d": None,
                    "warns_7d": None,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                    "reason": "SQLite aggregate exceeded latency-lens budget.",
                    "query_plan": plan_rows,
                    "deadline_ms": _codex_sqlite_7d_deadline_ms(),
                }
            return {"status": "error", "error": str(exc), "query_plan": plan_rows}
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return {
            "status": "available",
            "logs_7d": row[0],
            "errors_7d": row[1],
            "warns_7d": row[2],
            "query_plan": plan_rows,
            "elapsed_ms": elapsed_ms,
            "deadline_ms": _codex_sqlite_7d_deadline_ms(),
        }
    finally:
        try:
            con.close()
        except Exception:
            pass


def _claude_latency_meta_fast(path: Path) -> dict[str, Any]:
    """Raw-line metadata scan for the latency lens.

    Returns the same fields lens_latency reads from claude_session_meta
    (records, first/last timestamps, wallclock_s, user_interrupted) without
    parsing every record as JSON. Falls back to JSON parsing per file on
    open errors only.
    """
    n_rec = 0
    first_ts: str | None = None
    last_ts: str | None = None
    interrupted = False
    try:
        stream = path.open()
    except FileNotFoundError:
        return {
            "session_id": path.stem,
            "records": 0,
            "first_ts": None,
            "last_ts": None,
            "wallclock_s": None,
            "user_interrupted": False,
        }
    with stream as f:
        for line in f:
            if not line or line == "\n":
                continue
            n_rec += 1
            ts = _timestamp_from_line(line)
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            if not interrupted and _INTERRUPT_MARKER in line:
                interrupted = True
    return {
        "session_id": path.stem,
        "records": n_rec,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "wallclock_s": _ts_diff(first_ts, last_ts),
        "user_interrupted": interrupted,
    }


def _codex_latency_meta_fast(path: Path) -> dict[str, Any]:
    """Raw-line metadata scan for the latency lens (codex rollouts)."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return {
            "records": 0,
            "function_calls": 0,
            "turns": 0,
            "compactions": 0,
            "first_ts": None,
            "last_ts": None,
            "wallclock_s": None,
        }
    n_rec = _jsonl_record_count(data)
    first_ts = _first_timestamp_from_bytes(data)
    last_ts = _last_timestamp_from_bytes(data)
    marker_counts = _codex_marker_counts(data)
    n_fn_calls = marker_counts[b"function_call"]
    n_compacted = marker_counts[b"compacted"]
    turns = marker_counts[b"task_started"]
    return {
        "records": n_rec,
        "function_calls": n_fn_calls,
        "turns": turns,
        "compactions": n_compacted,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "wallclock_s": _ts_diff(first_ts, last_ts),
    }


def lens_latency(
    claude_files: list[Path],
    codex_files: list[Path],
    limit: int,
    *,
    include_codex_sqlite: bool = True,
) -> dict[str, Any]:
    """Session wall-clock + events/min + compaction signals."""
    claude_stats = []
    for fp in claude_files[:limit]:
        m = _claude_latency_meta_fast(fp)
        ws = m["wallclock_s"]
        claude_stats.append({
            "session_id": m["session_id"][:12],
            "records": m["records"],
            "wallclock_s": round(ws) if ws else None,
            "events_per_min": round(m["records"] * 60 / ws, 1) if ws else None,
            "interrupted": m["user_interrupted"],
        })
    codex_stats = []
    for fp in codex_files[:limit]:
        m = _codex_latency_meta_fast(fp)
        ws = m["wallclock_s"]
        codex_stats.append({
            "path": fp.name,
            "records": m["records"],
            "function_calls": m["function_calls"],
            "turns": m["turns"],
            "compactions": m["compactions"],
            "wallclock_s": round(ws) if ws else None,
        })
    # Codex SQLite summary for the window — store-scoped, plan-gated,
    # and deadline-bounded so the latency lens stays cheap by default.
    sqlite_summary = (
        _codex_sqlite_7d_summary()
        if include_codex_sqlite
        else _codex_sqlite_7d_store_scope_omission()
    )
    return {
        "claude_sessions": claude_stats[:limit],
        "codex_sessions": codex_stats[:limit],
        "codex_sqlite_7d": sqlite_summary,
    }


def lens_prompts(claude_files: list[Path], limit: int, *, include_text: bool = False) -> dict[str, Any]:
    """First-user prompt surface across sessions — what did agents get asked?

    Useful for discoverability diagnostics: repeated phrasings that the nav
    layer should route cleanly, or topic clusters the current plane underserves.
    """
    prompts = []
    for fp in claude_files:
        m = claude_session_meta(fp)
        if m["first_user"]:
            row = _prompt_ref(
                source="claude",
                session=m["session_id"][:12],
                text=m["first_user"],
                include_text=include_text,
            )
            if include_text:
                row["first_user"] = m["first_user"]
            row["interrupted"] = m["user_interrupted"]
            prompts.append(row)
    return {
        "sessions_analyzed": len(claude_files),
        "prompts": prompts[:limit],
    }


# Heuristics for detecting operator-authored autonomous-seed wake prompts.
# Conservative: prefer precision over recall. The downstream skill
# (autonomous_seed_prompt_author) wants real exemplars, not every user message.
_WAKE_PATTERNS = (
    r"\bautonomous\s*seed\b",
    r"\byou\s+are\s+an?\s+autonomous\b",
    r"\bTHIS\s+IS\s+AN\s+AUTON",
    r"\btype\s*A\s+meta\s+mission\b",
    r"\bthis\s+is\s+a\s+type\s*A\b",
    r"\bim\s+sending\s+this\s+repeatedly\b",
    r"\bi'?ll\s+keep\s+sending\s+this\b",
    r"\bwe\s+have\s+\w+\s+other\s+autonomous\s+seed",
    r"\binvoke\s+care\s+and\s+passion\b",
    r"\bextract\s+what\s+i'?m\s+gesturing\s+towards\b",
    r"\bterrain[-\s]*lane\s+seed\b",
    r"\btask[-\s]*lane\s+seed\b",
    r"\blane:\s*(?:task|terrain)\b",
)
_WAKE_SKIP = (
    r"^Execution\s+mode:",
    r"^<subagent_notification>",
    r"^<permissions\s+instructions>",
    r"^# AGENTS\.md\s+instructions",
    r"^okay\s+next\s+wave\s*$",
    r"^keep\s+going\s*$",
)

# Pre-compiled combined alternation: one regex engine pass per text instead of
# up to 19 separate re.search/re.match calls. lens_wake_prompts evaluates these
# patterns against every user-message text across the window — at last=50 the
# old per-call style was ~35% of build_report(lens="all") wall time.
_WAKE_PATTERNS_RE = re.compile(
    "|".join(f"(?:{p})" for p in _WAKE_PATTERNS), re.IGNORECASE
)
_WAKE_SKIP_RE = re.compile(
    "|".join(f"(?:{p})" for p in _WAKE_SKIP), re.IGNORECASE
)


def _is_wake_prompt(text: str) -> bool:
    if not text or len(text) < 40 or len(text) > 2500:
        return False
    if _WAKE_SKIP_RE.match(text):
        return False
    return _WAKE_PATTERNS_RE.search(text) is not None


def _text_sha16(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").casefold()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


_EXPERIENCE_FRICTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule_id": "ledger_claim_contention",
        "family": "ledger_claim_contention",
        "pattern": re.compile(
            r"\b(active Work Ledger claim|same-path active claim|claim is still live|"
            r"claim collision|single-writer lock|exclusive claim|leased until|"
            r"not going to bypass)\b",
            re.IGNORECASE,
        ),
    },
    {
        "rule_id": "scoped_commit_cas_retry_exhausted",
        "family": "scoped_commit_cas_retry_handoff",
        "pattern": re.compile(
            r"\b(scoped[-_ ]commit|private[-_ ]index|HEAD[-_ ]CAS|parent[-_ ]CAS|ref mutation)\b"
            r".{0,240}\b(CAS failed|CAS retry|retry budget exhausted|HEAD advanced|"
            r"ref mutation|blocked receipt)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    },
    {
        "rule_id": "cas_retry_budget_exhausted",
        "family": "scoped_commit_cas_retry_handoff",
        "pattern": re.compile(
            r"\b(CAS retry budget|retry budget was exhausted|second_head_cas_failure|"
            r"parent_cas_retry_budget_exhausted|private[-_ ]index CAS failed|HEAD later advanced)\b",
            re.IGNORECASE,
        ),
    },
    {
        "rule_id": "task_ledger_payload_rejection",
        "family": "task_ledger_payload_rejection",
        "pattern": re.compile(
            r"\b(invalid surface status|rejected without appending|invalid .*status|"
            r"task_ledger_apply\.py .*usage|usage: task_ledger_apply\.py)\b",
            re.IGNORECASE,
        ),
    },
    {
        "rule_id": "metadata_settlement_detour",
        "family": "metadata_settlement_detour",
        "pattern": re.compile(
            r"\b(metadata settlement|Task Ledger settlement|satisfaction contract|"
            r"execution receipt|separate scoped metadata commit|post-source-commit)\b",
            re.IGNORECASE,
        ),
    },
    {
        "rule_id": "compaction_recovery",
        "family": "compaction_recovery",
        "pattern": re.compile(
            r"\b(Context automatically compacted|compacted state|continuing from the compacted|"
            r"context compaction|after compaction)\b",
            re.IGNORECASE,
        ),
    },
    {
        "rule_id": "closeout_authority_confusion",
        "family": "closeout_authority_confusion",
        "pattern": re.compile(
            r"\b(closeout .*blocked|held-closeout|publication closeout|origin/main|"
            r"not published|local commits .*ahead|closeout_executor|run_git\.py audit push)\b",
            re.IGNORECASE,
        ),
    },
    {
        "rule_id": "command_contract_mismatch",
        "family": "command_contract_mismatch",
        "pattern": re.compile(
            r"\b(usage: [\w./-]+\.py|No such tool available|String to replace not found|"
            r"File has not been read yet|File has been modified since read)\b",
            re.IGNORECASE,
        ),
    },
)


_EXPERIENCE_FRICTION_FAMILY_INFO: dict[str, dict[str, Any]] = {
    "ledger_claim_contention": {
        "priority": 91,
        "title": "Trace updates show ledger claim contention blocking settlement or closeout",
        "owner_surface": "codex/standards/std_work_ledger.json + codex/doctrine/skills/task_ledger/task_ledger_metacontrol_uppropagation.md",
        "next_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30 --cards-only",
        "candidate_patch": "Tighten claim ordering, lease handling, or same-path settlement guidance so agents do not improvise around active owners.",
    },
    "scoped_commit_cas_retry_handoff": {
        "priority": 90,
        "title": "Trace updates show scoped-commit CAS retry exhaustion needs landing handoff",
        "owner_surface": "tools/meta/control/scoped_commit.py + system/lib/work_ledger_runtime.py + cogop_landing_handoff_compiler",
        "next_command": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12",
        "candidate_patch": "Surface exact owned paths, validation evidence, HEAD movement, retry count, and re-entry condition through Work Ledger seed-speed or the landing handoff compiler before any further ref mutation.",
    },
    "task_ledger_payload_rejection": {
        "priority": 88,
        "title": "Trace updates show Task Ledger payload/schema rejection",
        "owner_surface": "codex/standards/std_task_ledger.json + tools/meta/factory/task_ledger_apply.py",
        "next_command": "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings",
        "candidate_patch": "Use the warning-tolerant health check for trace triage, then expose accepted statuses, dry-run validation, and append-safe examples before agents hit Task Ledger mutation errors.",
    },
    "metadata_settlement_detour": {
        "priority": 86,
        "title": "Trace updates show post-source metadata settlement as a separate friction lane",
        "owner_surface": "codex/standards/std_task_ledger.json + codex/standards/std_work_ledger.json",
        "next_command": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
        "candidate_patch": "Route post-source-commit Task Ledger settlement through an explicit contract instead of ad hoc closeout narration.",
    },
    "compaction_recovery": {
        "priority": 80,
        "title": "Trace updates show context compaction recovery during execution",
        "owner_surface": "codex/doctrine/skills/kernel/agent_session_diagnostics.md + compact continuation packets",
        "next_command": "./repo-python kernel.py --session-diagnostics --lens latency --last 10 --store codex --json",
        "candidate_patch": "Make compaction/resume packets preserve owner, claim, validation, and residual state without reopening raw trace bodies.",
    },
    "closeout_authority_confusion": {
        "priority": 87,
        "title": "Trace updates show closeout/publication authority ambiguity",
        "owner_surface": "system/lib/closeout_executor.py + codex/standards/std_work_ledger.json",
        "next_command": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions",
        "candidate_patch": "Separate landed source commits, publication state, active ownership, and metadata settlement before declaring closeout.",
    },
    "command_contract_mismatch": {
        "priority": 78,
        "title": "Trace updates show agents learning command contracts by failing them",
        "owner_surface": "command cards, CLI help, or owning standard for the failing command",
        "next_command": "./repo-python kernel.py --session-diagnostics --lens errors --last 20 --store both --json",
        "candidate_patch": "Add a command card, dry-run lane, or clearer accepted-value contract for repeated command usage failures.",
    },
}


_CLAUDE_SUMMARY_FRICTION_LINE_MARKERS = (
    "active work ledger claim",
    "same-path active claim",
    "claim is still live",
    "claim collision",
    "single-writer lock",
    "exclusive claim",
    "leased until",
    "not going to bypass",
    "private-index cas",
    "head-cas",
    "parent-cas",
    "cas retry budget",
    "retry budget was exhausted",
    "head advanced",
    "head later advanced",
    "blocked receipt",
    "ref mutation",
    "rejected without appending",
    "task_ledger_apply.py",
    "metadata settlement",
    "task ledger settlement",
    "satisfaction contract",
    "execution receipt",
    "separate scoped metadata commit",
    "post-source-commit",
    "context automatically compacted",
    "compacted state",
    "continuing from the compacted",
    "context compaction",
    "compaction",
    "publication closeout",
    "origin/main",
    "not published",
    "run_git.py",
    "no such tool available",
    "string to replace not found",
    "file has not been read yet",
    "file has been modified since read",
)


def _line_may_hold_experience_friction(text: str) -> bool:
    lowered = text.casefold()
    return (
        any(marker in lowered for marker in _CLAUDE_SUMMARY_FRICTION_LINE_MARKERS)
        or ("invalid" in lowered and "status" in lowered)
        or ("closeout" in lowered and "blocked" in lowered)
        or ("local commits" in lowered and "ahead" in lowered)
        or ("usage:" in lowered and ".py" in lowered)
    )


def _experience_friction_matches(text: str) -> dict[str, set[str]]:
    matches: dict[str, set[str]] = collections.defaultdict(set)
    for rule in _EXPERIENCE_FRICTION_RULES:
        pattern = rule["pattern"]
        if pattern.search(text):
            matches[str(rule["family"])].add(str(rule["rule_id"]))
    return matches


def _record_experience_friction_text(
    buckets: dict[str, list[dict[str, Any]]],
    *,
    source: str,
    session: str,
    ts: str,
    text: str,
) -> None:
    if not text:
        return
    matches = _experience_friction_matches(text)
    if not matches:
        return
    base = {
        "source": source,
        "session": session,
        "ts": ts,
        "text_sha16": _text_sha16(text),
        "text_length": len(text),
        "text_omitted": True,
    }
    for family, rule_ids in matches.items():
        row = dict(base)
        row["matched_rules"] = sorted(rule_ids)
        buckets[family].append(row)


def _experience_friction_payload(
    buckets: dict[str, list[dict[str, Any]]],
    *,
    sessions_analyzed: int,
    limit: int,
) -> dict[str, Any]:
    family_rows: list[dict[str, Any]] = []
    for family, refs in buckets.items():
        info = _EXPERIENCE_FRICTION_FAMILY_INFO.get(family, {})
        family_rows.append({
            "family": family,
            "title": info.get("title") or family.replace("_", " "),
            "priority": info.get("priority", 70),
            "count": len(refs),
            "distinct_sessions": len({str(ref.get("session") or "") for ref in refs}),
            "owner_surface": info.get("owner_surface"),
            "next_command": info.get("next_command"),
            "candidate_patch": info.get("candidate_patch"),
            "evidence_refs": refs[:limit],
        })
    family_rows.sort(
        key=lambda row: (
            int(row.get("priority") or 0),
            int(row.get("count") or 0),
            int(row.get("distinct_sessions") or 0),
        ),
        reverse=True,
    )
    return {
        "schema_version": "experience_friction_lens_v0",
        "sessions_analyzed": sessions_analyzed,
        "event_count": sum(len(refs) for refs in buckets.values()),
        "family_count": len(family_rows),
        "families": family_rows[:limit],
        "privacy_boundary": "Assistant/status prose and tool bodies are omitted; rows carry rule ids, counts, sessions, timestamps, lengths, and text hashes only.",
    }


def _prompt_ref(
    *,
    source: str,
    session: Any,
    text: str,
    ts: Any = None,
    include_text: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source": source,
        "session": session,
        "ts": ts,
        "length": len(text),
        "prompt_sha16": _text_sha16(text),
        "text_omitted": not include_text,
    }
    if include_text:
        row["text"] = text
    return {key: value for key, value in row.items() if value is not None}


_TOOL_ERROR_SIGNAL_RE = re.compile(
    r"(<tool_use_error>|traceback|error\b|exception\b|valueerror|inputvalidationerror|"
    r"no such tool|not found|failed|usage:|exit code \d+)",
    re.IGNORECASE,
)
_TOOL_ERROR_NOISE_RE = re.compile(
    r"^(?:\d+\t)?(?:[\{\}\[\],]|from __future__ import annotations|#!/usr/bin/env python3|"
    r"import\s|\"\"\"|---|#\s|>\s*ui@|\"[^\"]+\"\s*:|\"[^\"]+\",?|\d+\s+-\s+|$)"
)


def _tool_error_signature(body: Any) -> str | None:
    if isinstance(body, list):
        body = next((b.get("text", "") for b in body if isinstance(b, dict)), "")
    if not isinstance(body, str):
        return None
    signal_lines: list[str] = []
    for raw_line in body.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or _TOOL_ERROR_NOISE_RE.match(line):
            continue
        if re.search(r"\bfailed:\s*0\b", line, re.IGNORECASE):
            continue
        if _TOOL_ERROR_SIGNAL_RE.search(line):
            signal_lines.append(line)
    if not signal_lines:
        return None
    return signal_lines[0][:120]


def _interrupt_ref(*, session: Any, first_user: Any) -> dict[str, Any]:
    text = str(first_user or "")
    row: dict[str, Any] = {
        "session": session,
        "first_user_omitted": True,
    }
    if text:
        row["first_user_sha16"] = _text_sha16(text)
        row["first_user_length"] = len(text)
    return row


def _wake_prompt_repeat_fingerprint(text: str) -> tuple[str, str]:
    """Return a stable hash and excerpt for exact repeated wake-prompt checks."""
    normalized = re.sub(r"\s+", " ", str(text or "").casefold()).strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return digest, normalized[:220]


def _wake_prompt_repetition_clusters(
    buckets: dict[str, list[dict[str, Any]]], *, limit: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for digest, entries in buckets.items():
        if len(entries) < 2:
            continue
        latest_ts = max(str(entry.get("ts") or "") for entry in entries)
        rows.append({
            "prompt_sha16": digest,
            "count": len(entries),
            "latest_ts": latest_ts,
            "prompt_body_omitted": True,
            "prompt_length": entries[0].get("length"),
            "classification": "exact_normalized_repeated_wake_prompt",
            "route_hint": (
                "./repo-python kernel.py --docs-route \"autonomous seed\"; "
                "./repo-python kernel.py --option-surface type_a_autonomous_seeds --band cluster_flag"
            ),
            "sources": [
                {
                    "source": entry.get("source"),
                    "session": entry.get("session"),
                    "ts": entry.get("ts"),
                }
                for entry in entries[:5]
            ],
        })
    rows.sort(
        key=lambda row: (
            int(row.get("count") or 0),
            str(row.get("latest_ts") or ""),
        ),
        reverse=True,
    )
    return rows[:limit]


def _iter_claude_user_messages(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (timestamp, text) for every user-typed message in a Claude jsonl."""
    for d in _iter_jsonl(path):
        if d.get("type") != "user":
            continue
        ts = d.get("timestamp") or ""
        m = d.get("message") or {}
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list):
            for it in c:
                if isinstance(it, dict) and it.get("type") == "text":
                    txt = it.get("text") or ""
                    if txt:
                        yield ts, txt
        elif isinstance(c, str) and c:
            yield ts, c


def _iter_codex_user_messages(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (timestamp, text) for every user `input_text` in a Codex rollout."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return
    if b'"response_item"' not in data or b'"user"' not in data:
        return
    for raw_line in data.splitlines():
        if b'"response_item"' not in raw_line or b'"user"' not in raw_line:
            continue
        line = raw_line.decode("utf-8", errors="replace")
        ts = _timestamp_from_line(line) or ""
        for text in _codex_user_texts_from_line(line):
            yield ts, text


def lens_wake_prompts(
    claude_files: list[Path], codex_files: list[Path], limit: int, *, include_text: bool = False
) -> dict[str, Any]:
    """Extract operator-authored autonomous-seed wake prompts across sessions.

    Intent: give the `autonomous_seed_prompt_author` skill a cheap way to show
    Will real exemplars of his own wake-prompt voice, instead of paraphrasing
    from memory. The lens is precision-biased — misses are fine, false
    positives cost the author's register discipline.
    """
    seen: dict[str, dict[str, Any]] = {}
    repeat_buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    def _record(source: str, session_tag: str, ts: str, text: str) -> None:
        text = text.strip()
        if not _is_wake_prompt(text):
            return
        prompt_sha16, excerpt = _wake_prompt_repeat_fingerprint(text)
        repeat_buckets[prompt_sha16].append({
            "source": source,
            "session": session_tag,
            "ts": ts,
            "excerpt": excerpt,
            "length": len(text),
        })
        key = text[:220]
        if key in seen:
            return
        seen[key] = _prompt_ref(
            source=source,
            session=session_tag,
            ts=ts,
            text=text,
            include_text=include_text,
        )

    for fp in claude_files:
        for ts, txt in _iter_claude_user_messages(fp):
            _record("claude", fp.stem[:12], ts, txt)
    for fp in codex_files:
        for ts, txt in _iter_codex_user_messages(fp):
            _record("codex", fp.name[:55], ts, txt)

    prompts = sorted(seen.values(), key=lambda r: r.get("ts") or "", reverse=True)
    repetition_clusters = _wake_prompt_repetition_clusters(repeat_buckets, limit=limit)
    return {
        "sessions_analyzed": len(claude_files) + len(codex_files),
        "claude_sessions": len(claude_files),
        "codex_sessions": len(codex_files),
        "matched_wake_prompt_count": sum(len(entries) for entries in repeat_buckets.values()),
        "unique_wake_prompts": len(prompts),
        "repeated_prompt_cluster_count": len(repetition_clusters),
        "repetition_clusters": repetition_clusters,
        "detection_policy": (
            "Precision-biased autonomous-seed wake prompt detection; repeated clusters "
            "mean exact normalized prompt text occurred more than once."
        ),
        "prompts": prompts[:limit],
    }


_ROUTE_MISS_PATTERNS = (
    r"\broute[-\s]*miss(?:es)?(?:\s+(?:miner|auto[-\s]*miner|candidate|candidates|phrases?|sidecar))?\b",
    r"\bdocs[-\s]*route\s+(?:failed\s+phrases?|miss(?:es)?|alias(?:es)?|hints?|failed\s+to\s+resolve)\b",
    r"\bphrases?\s+docs[-\s]*route\s+failed(?:\s+to\s+resolve)?\b",
    r"\bwake[-\s]*prompts?\s+(?:lens|route[-\s]*miss(?:es)?|phrases?|candidate|candidates)\b",
    r"\bprompts?\s+(?:lens|route[-\s]*miss(?:es)?|phrases?|candidate|candidates)\b",
    r"\bsuggested[-\s]*alias\s+sidecar\b",
    r"\balias\s+sidecar\b",
    r"\broute\s+alias(?:es)?\b",
    r"\bnavigation(?:[-\s]*layer)?\s+(?:timing|process[-\s]*trace|route|routing)\b",
    r"\bprocess[-\s]*(?:trace|audit|bottlenecks?|compare)\b",
    r"\bagent[-\s]*wake[-\s]*packet\b",
    r"\bphase\s+summary\b",
    r"\bwarnings[-\s]*only\b",
    r"\bbash[-\s]*before[-\s]*kernel\b",
)

_ROUTE_MISS_ANCHORS = {
    "agent-wake-packet",
    "alias",
    "audit",
    "bash-before-kernel",
    "candidate",
    "docs-route",
    "failed",
    "kernel",
    "lens",
    "miner",
    "miss",
    "misses",
    "navigation",
    "phrase",
    "phrases",
    "process-audit",
    "process-trace",
    "prompt",
    "prompts",
    "route",
    "routing",
    "sidecar",
    "trace",
    "wake-prompts",
}

_ROUTE_MISS_DROP_TOKENS = {
    "a", "an", "and", "are", "as", "for", "from", "in", "is", "it", "of",
    "on", "or", "that", "the", "this", "to", "with", "you", "your",
}


def _normalise_route_candidate(value: str) -> str:
    text = value.lower()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"(?<!\w)--(?=[a-z])", "", text)
    text = re.sub(r"[^a-z0-9._+/-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -_./")
    words = [w for w in text.split() if w not in _ROUTE_MISS_DROP_TOKENS]
    if len(words) > 7:
        words = words[:7]
    return " ".join(words)


def _route_candidate_tokens(text: str) -> list[str]:
    cleaned = re.sub(r"`([^`]+)`", r"\1", text.lower())
    cleaned = re.sub(r"(?<!\w)--(?=[a-z])", "", cleaned)
    cleaned = cleaned.replace("_", "-")
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", cleaned)


def _route_miss_candidate_phrases(text: str, *, limit: int = 24) -> list[str]:
    """Extract bounded docs-route candidate phrases from operator prompts."""
    seen: dict[str, None] = {}
    cleaned = re.sub(r"`([^`]+)`", r"\1", text)
    cleaned = re.sub(r"(?<!\w)--(?=[A-Za-z])", "", cleaned)

    def _add(value: str) -> None:
        phrase = _normalise_route_candidate(value)
        if len(phrase) < 5 or phrase in seen:
            return
        if len(phrase.split()) > 7:
            return
        seen[phrase] = None

    for pattern in _ROUTE_MISS_PATTERNS:
        for match in re.finditer(pattern, cleaned, re.IGNORECASE):
            _add(match.group(0))
            if len(seen) >= limit:
                return list(seen)

    tokens = _route_candidate_tokens(cleaned)
    for idx, token in enumerate(tokens):
        if token not in _ROUTE_MISS_ANCHORS:
            continue
        start = max(0, idx - 2)
        end = min(len(tokens), idx + 5)
        window = tokens[start:end]
        if len(window) >= 2:
            _add(" ".join(window))
        if idx + 3 <= len(tokens):
            _add(" ".join(tokens[idx:idx + 3]))
        if len(seen) >= limit:
            break
    return list(seen)


_ROUTE_GRAPH_ALIAS_HINTS = (
    "route edge",
    "route target",
    "route graph",
    "navigation graph",
    "generated navigation graph",
    "validated route",
    "targets resolve",
    "concept-backed",
    "how things route",
    "mean by routing",
    "routing typed semantic",
    "typed semantic routing",
    "perception becomes routing",
    "routing becomes action",
)


def _route_miss_suggested_alias(phrase: str) -> dict[str, Any]:
    normalized = _normalise_route_candidate(phrase)
    if any(hint in normalized for hint in _ROUTE_GRAPH_ALIAS_HINTS):
        return {
            "route_id": "sit_unified_navigation_layer",
            "owner": "codex/doctrine/paper_modules/unified_navigation_layer.md",
            "index": "codex/doctrine/documentation_theory_index.json",
            "reason": (
                "Prompt-derived docs-route miss is about route graph/topology; "
                "route to the unified navigation layer as the alias owner, with "
                "session diagnostics retained as the evidence-producing lens."
            ),
            "regression_test": "system/server/tests/test_docs_route.py",
        }
    return {
        "route_id": "sit_agent_session_diagnostics_training_loop",
        "owner": "codex/doctrine/skills/kernel/agent_session_diagnostics.md",
        "index": "codex/doctrine/documentation_theory_index.json",
        "reason": (
            "Prompt-derived docs-route miss; route to the session-diagnostics "
            "training loop before deciding whether to add a permanent alias."
        ),
        "regression_test": "system/server/tests/test_docs_route.py",
    }


def _probe_docs_route_phrase(phrase: str) -> dict[str, Any]:
    try:
        from system.lib.kernel_navigation import KernelNavigation

        result = KernelNavigation(REPO_ROOT).build_docs_route(phrase)
        payload = result.payload if hasattr(result, "payload") else {}
        resolution = payload.get("resolution") if isinstance(payload, dict) else {}
        if not isinstance(resolution, dict):
            resolution = {}
        return {
            "resolved": True,
            "route_id": resolution.get("route_id"),
            "confidence": resolution.get("confidence"),
            "minimum_read_set_id": (
                (payload.get("minimum_read_set") or {}).get("id")
                if isinstance(payload, dict) else None
            ),
        }
    except Exception as exc:  # noqa: BLE001 - unresolved query is the signal.
        return {
            "resolved": False,
            "error": str(exc),
            "suggested_alias": _route_miss_suggested_alias(phrase),
        }


def lens_route_misses(
    claude_files: list[Path], codex_files: list[Path], limit: int,
    *,
    prompts_payload: dict[str, Any] | None = None,
    wake_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Probe prompt-derived phrases against docs-route and emit alias candidates.

    This is intentionally bounded. It does not edit the route index; it turns the
    prompts and wake-prompts lenses into a candidate sidecar so the next agent can
    repair one phrase cohort with evidence instead of manually grepping docs.

    When invoked from build_report(lens="all"), the caller passes the already
    computed prompts/wake payloads to avoid re-walking the cached records.
    """
    prompt_sources: list[dict[str, Any]] = []

    if prompts_payload is None:
        prompts_payload = lens_prompts(claude_files, limit=max(limit, 20), include_text=True)
    for row in prompts_payload.get("prompts", []):
        text = str(row.get("first_user") or "")
        if text:
            prompt_sources.append({
                "lens": "prompts",
                "source": "claude",
                "session": row.get("session"),
                "text": text,
            })

    if wake_payload is None:
        wake_payload = lens_wake_prompts(claude_files, codex_files, limit=max(limit, 20), include_text=True)
    for row in wake_payload.get("prompts", []):
        text = str(row.get("text") or "")
        if text:
            prompt_sources.append({
                "lens": "wake-prompts",
                "source": row.get("source"),
                "session": row.get("session"),
                "ts": row.get("ts"),
                "text": text,
            })

    candidate_sources: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for source in prompt_sources:
        text = str(source.get("text") or "")
        for phrase in _route_miss_candidate_phrases(text, limit=limit):
            candidate_sources[phrase].append({
                "lens": source.get("lens"),
                "source": source.get("source"),
                "session": source.get("session"),
                "ts": source.get("ts"),
                "prompt_sha16": _text_sha16(text),
                "prompt_length": len(text),
                "prompt_body_omitted": True,
            })

    rows: list[dict[str, Any]] = []
    for phrase, sources in candidate_sources.items():
        probe = _probe_docs_route_phrase(phrase)
        rows.append({
            "phrase": phrase,
            "resolved": bool(probe.get("resolved")),
            "probe": probe,
            "source_count": len(sources),
            "sources": sources[:3],
        })
    rows.sort(key=lambda row: (row["resolved"], -row["source_count"], row["phrase"]))

    unresolved = [row for row in rows if not row["resolved"]]
    return {
        "sessions_analyzed": len(claude_files) + len(codex_files),
        "source_prompt_count": len(prompt_sources),
        "candidate_count": len(rows),
        "resolved_count": len(rows) - len(unresolved),
        "unresolved_count": len(unresolved),
        "sidecar_kind": "docs_route_miss_candidates",
        "write_flag": "--write-route-miss-candidates <path>",
        "unresolved_candidates": unresolved[:limit],
        "candidates": rows[:limit],
    }


def lens_errors(claude_files: list[Path], limit: int) -> dict[str, Any]:
    """User interrupts + error patterns across sessions."""
    interrupts = []
    tool_errors = collections.Counter()
    for fp in claude_files:
        m = claude_session_meta(fp)
        if m["user_interrupted"]:
            interrupts.append(_interrupt_ref(
                session=m["session_id"][:12],
                first_user=m["first_user"],
            ))
        for d in _iter_jsonl(fp):
            if d.get("type") != "user":
                continue
            mm = d.get("message", {})
            c = mm.get("content") if isinstance(mm, dict) else None
            if isinstance(c, list):
                for it in c:
                    if isinstance(it, dict) and it.get("type") == "tool_result":
                        body = it.get("content") or ""
                        if isinstance(body, list):
                            body = next(
                                (b.get("text", "") for b in body if isinstance(b, dict)),
                                "",
                            )
                        signature = _tool_error_signature(body)
                        if signature:
                            tool_errors[signature] += 1
    return {
        "sessions_analyzed": len(claude_files),
        "user_interrupts": interrupts[:limit],
        "top_tool_error_lines": tool_errors.most_common(limit),
    }


def _iter_claude_assistant_texts(path: Path) -> Iterator[tuple[str, str]]:
    for d in _iter_jsonl(path):
        if d.get("type") != "assistant":
            continue
        message = d.get("message") if isinstance(d.get("message"), dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        ts = str(d.get("timestamp") or "")
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text") or "")
                if text:
                    yield ts, text


def _iter_codex_assistant_texts(path: Path) -> Iterator[tuple[str, str]]:
    for d in _iter_jsonl(path):
        if d.get("type") != "response_item":
            continue
        payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        if payload.get("type") != "message" or payload.get("role") != "assistant":
            continue
        content = payload.get("content") or []
        if not isinstance(content, list):
            continue
        ts = str(d.get("timestamp") or "")
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"output_text", "text"}:
                text = str(item.get("text") or "")
                if text:
                    yield ts, text


def lens_experience_frictions(
    claude_files: list[Path], codex_files: list[Path], limit: int
) -> dict[str, Any]:
    """Classify repair-shaped experience episodes without exposing prose bodies."""
    buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for fp in claude_files:
        session = fp.stem[:12]
        for ts, text in _iter_claude_assistant_texts(fp):
            _record_experience_friction_text(
                buckets,
                source="claude",
                session=session,
                ts=ts,
                text=text,
            )
    for fp in codex_files:
        session = fp.name[:55]
        for ts, text in _iter_codex_assistant_texts(fp):
            _record_experience_friction_text(
                buckets,
                source="codex",
                session=session,
                ts=ts,
                text=text,
            )
    return _experience_friction_payload(
        buckets,
        sessions_analyzed=len(claude_files) + len(codex_files),
        limit=limit,
    )


def _facts_histogram(facts: SessionDiagnosticsFacts, limit: int) -> dict[str, Any]:
    tools = collections.Counter()
    bash_verbs = collections.Counter()
    total_records = 0
    for row in facts.claude:
        tools.update(row.tool_histogram)
        bash_verbs.update(row.bash_verbs)
        total_records += row.records
    return {
        "sessions_analyzed": len(facts.claude),
        "total_records": total_records,
        "tool_histogram": tools.most_common(limit),
        "bash_verbs": bash_verbs.most_common(limit),
    }


def _facts_hotspots(facts: SessionDiagnosticsFacts, limit: int) -> dict[str, Any]:
    reads = collections.Counter()
    edits = collections.Counter()
    read_sessions = collections.defaultdict(set)
    for row in facts.claude:
        reads.update(row.reads)
        edits.update(row.edits)
        for path in row.reads:
            read_sessions[path].add(row.session_id)
    rediscovery = [
        (path, count, len(read_sessions[path]), count * len(read_sessions[path]))
        for path, count in reads.items()
    ]
    rediscovery.sort(key=lambda item: -item[3])
    return {
        "sessions_analyzed": len(facts.claude),
        "top_reads": [{"path": p, "reads": c} for p, c in reads.most_common(limit)],
        "top_edits": [{"path": p, "edits": c} for p, c in edits.most_common(limit)],
        "rediscovery": [
            {"path": p, "reads": r, "distinct_sessions": s, "score": score}
            for p, r, s, score in rediscovery[:limit]
        ],
    }


def _facts_ladder_skip(facts: SessionDiagnosticsFacts, limit: int) -> dict[str, Any]:
    bad_bash = collections.Counter()
    good_bash = collections.Counter()
    kernel_nav_calls = collections.Counter()
    reread_events = []
    grep_before_nav = 0
    for row in facts.claude:
        bad_bash.update(row.bad_bash)
        good_bash.update(row.good_bash)
        kernel_nav_calls.update(row.kernel_nav_calls)
        grep_before_nav += row.grep_before_nav
        if row.rereads:
            reread_events.append({
                "session": row.session_id,
                "rereads": row.rereads,
            })
    total_bad = sum(bad_bash.values())
    total_good = sum(good_bash.values())
    return {
        "sessions_analyzed": len(facts.claude),
        "bash_should_be_native": bad_bash.most_common(limit),
        "bash_repo_tooling": good_bash.most_common(limit),
        "ratio_bad_to_good_bash": round(total_bad / max(total_good, 1), 3),
        "kernel_nav_flag_calls": kernel_nav_calls.most_common(),
        "grep_calls_before_any_nav_flag": grep_before_nav,
        "dominant_shell_shape": _ladder_skip_dominant_shell_shape(
            bad_bash,
            grep_before_nav=grep_before_nav,
        ),
        "reread_events": reread_events[:limit],
    }


def _facts_latency(
    facts: SessionDiagnosticsFacts,
    limit: int,
    *,
    include_codex_sqlite: bool = True,
) -> dict[str, Any]:
    claude_stats = []
    for row in facts.claude:
        ws = row.wallclock_s
        claude_stats.append({
            "session_id": row.session_id,
            "records": row.records,
            "wallclock_s": round(ws) if ws else None,
            "events_per_min": round(row.records * 60 / ws, 1) if ws else None,
            "interrupted": row.user_interrupted,
        })
    codex_stats = []
    for row in facts.codex:
        ws = row.wallclock_s
        codex_stats.append({
            "path": row.path.name,
            "records": row.records,
            "function_calls": row.function_calls,
            "turns": row.turns,
            "compactions": row.compactions,
            "wallclock_s": round(ws) if ws else None,
        })
    return {
        "claude_sessions": claude_stats[:limit],
        "codex_sessions": codex_stats[:limit],
        "codex_sqlite_7d": (
            _codex_sqlite_7d_summary()
            if include_codex_sqlite
            else _codex_sqlite_7d_store_scope_omission()
        ),
    }


def _facts_prompts(facts: SessionDiagnosticsFacts, limit: int) -> dict[str, Any]:
    prompts = [
        {
            "session": row.session_id,
            "first_user": row.first_user,
            "interrupted": row.user_interrupted,
        }
        for row in facts.claude
        if row.first_user
    ]
    return {
        "sessions_analyzed": len(facts.claude),
        "prompts": prompts[:limit],
    }


def _facts_wake_prompts(facts: SessionDiagnosticsFacts, limit: int) -> dict[str, Any]:
    seen: dict[str, dict[str, Any]] = {}
    repeat_buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    def _record(source: str, session_tag: str, ts: str, text: str) -> None:
        text = text.strip()
        if not _is_wake_prompt(text):
            return
        prompt_sha16, excerpt = _wake_prompt_repeat_fingerprint(text)
        repeat_buckets[prompt_sha16].append({
            "source": source,
            "session": session_tag,
            "ts": ts,
            "excerpt": excerpt,
            "length": len(text),
        })
        key = text[:220]
        if key in seen:
            return
        seen[key] = _prompt_ref(
            source=source,
            session=session_tag,
            ts=ts,
            text=text,
            include_text=True,
        )

    for row in facts.claude:
        for ts, text in row.user_messages:
            _record("claude", row.session_id, ts, text)
    for row in facts.codex:
        for ts, text in row.user_messages:
            _record("codex", row.path.name[:55], ts, text)

    prompts = sorted(seen.values(), key=lambda r: r.get("ts") or "", reverse=True)
    repetition_clusters = _wake_prompt_repetition_clusters(repeat_buckets, limit=limit)
    return {
        "sessions_analyzed": len(facts.claude) + len(facts.codex),
        "claude_sessions": len(facts.claude),
        "codex_sessions": len(facts.codex),
        "matched_wake_prompt_count": sum(len(entries) for entries in repeat_buckets.values()),
        "unique_wake_prompts": len(prompts),
        "repeated_prompt_cluster_count": len(repetition_clusters),
        "repetition_clusters": repetition_clusters,
        "detection_policy": (
            "Precision-biased autonomous-seed wake prompt detection; repeated clusters "
            "mean exact normalized prompt text occurred more than once."
        ),
        "prompts": prompts[:limit],
    }


def _facts_errors(facts: SessionDiagnosticsFacts, limit: int) -> dict[str, Any]:
    interrupts = []
    tool_errors = collections.Counter()
    for row in facts.claude:
        if row.user_interrupted:
            interrupts.append(_interrupt_ref(
                session=row.session_id,
                first_user=row.first_user,
            ))
        tool_errors.update(row.tool_error_lines)
    return {
        "sessions_analyzed": len(facts.claude),
        "user_interrupts": interrupts[:limit],
        "top_tool_error_lines": tool_errors.most_common(limit),
    }


def _sanitize_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    rows = []
    for row in payload.get("prompts") or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("first_user") or row.get("text") or "")
        if text:
            safe = _prompt_ref(
                source=str(row.get("source") or "claude"),
                session=row.get("session"),
                ts=row.get("ts"),
                text=text,
                include_text=False,
            )
        else:
            safe = {
                key: value
                for key, value in row.items()
                if key not in {"first_user", "text"}
            }
            safe.setdefault("text_omitted", True)
        if "interrupted" in row:
            safe["interrupted"] = row.get("interrupted")
        rows.append(safe)
    sanitized["prompts"] = rows
    sanitized["privacy_omission"] = "prompt bodies omitted; prompt_sha16/length/session retained"
    return sanitized


def _sanitize_wake_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    rows = []
    for row in payload.get("prompts") or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or row.get("first_user") or "")
        if text:
            safe = _prompt_ref(
                source=str(row.get("source") or ""),
                session=row.get("session"),
                ts=row.get("ts"),
                text=text,
                include_text=False,
            )
        else:
            safe = {
                key: value
                for key, value in row.items()
                if key not in {"first_user", "text"}
            }
            safe.setdefault("text_omitted", True)
        rows.append(safe)
    sanitized["prompts"] = rows
    sanitized["repetition_clusters"] = [
        {
            key: value
            for key, value in cluster.items()
            if key not in {"excerpt", "text", "first_user"}
        }
        for cluster in payload.get("repetition_clusters") or []
        if isinstance(cluster, dict)
    ]
    sanitized["privacy_omission"] = "wake prompt bodies omitted; prompt_sha16/count/source refs retained"
    return sanitized


_FACT_LENS_PROJECTORS = {
    "histogram": _facts_histogram,
    "hotspots": _facts_hotspots,
    "ladder-skip": _facts_ladder_skip,
    "latency": _facts_latency,
    "prompts": _facts_prompts,
    "wake-prompts": _facts_wake_prompts,
    "errors": _facts_errors,
}


# ---------------------------------------------------------------------------
# CLI


def _emit_table(name: str, data: Any) -> None:
    print(f"\n=== lens: {name} ===")
    if isinstance(data, dict):
        for k, v in data.items():
            print(f"\n-- {k} --")
            if isinstance(v, list):
                for item in v[:40]:
                    print(f"  {item}")
            else:
                print(f"  {v}")
    else:
        print(data)


LENSES = {
    "histogram": lens_histogram,
    "hotspots": lens_hotspots,
    "ladder-skip": lens_ladder_skip,
    "latency": lens_latency,
    "prompts": lens_prompts,
    "wake-prompts": lens_wake_prompts,
    "route-misses": lens_route_misses,
    "errors": lens_errors,
    "experience-frictions": lens_experience_frictions,
}


def normalize_lens_name(lens: str | None) -> str:
    """Return the canonical lens registry key for user-facing lens input."""
    token = (lens or "all").strip().lower().replace("_", "-")
    if token == "all" or token in LENSES:
        return token
    raise ValueError(f"unknown lens: {lens}")


def _build_trace_to_git_handoff(
    *,
    lens: str,
    store: str,
    last: int,
    source_kind: str,
) -> dict[str, Any]:
    """Compact transaction-graph route for turning trace evidence into proof."""
    try:
        safe_lens = normalize_lens_name(lens)
    except ValueError:
        safe_lens = "all"
    safe_store = store if store in {"claude", "codex", "both"} else "both"
    try:
        window_last = max(int(last), 1)
    except (TypeError, ValueError):
        window_last = 20
    bounded_last = min(window_last, 10)

    full_trace_command = (
        f"./repo-python kernel.py --session-diagnostics --lens {safe_lens} "
        f"--last {window_last} --store {safe_store} --json"
    )
    current_summary_command = _summary_first_diagnostics_command(full_trace_command)
    summary_command = (
        "./repo-python kernel.py --session-diagnostics --lens all "
        f"--last {bounded_last} --store {safe_store} --json --diagnostics-summary"
    )
    return {
        "schema": "session_diagnostics_trace_to_git_handoff_v0",
        "status": "routed",
        "source_kind": source_kind,
        "purpose": (
            "Connect retrospective trace evidence to live Git, Work Ledger, "
            "Task Ledger, validation, landing, and residual routes without "
            "replaying the full session corpus first."
        ),
        "cheap_first_command": summary_command,
        "current_trace_command": full_trace_command,
        "current_trace_summary_command": current_summary_command,
        "transaction_edges": {
            "agent_trace": {
                "status": "current_report",
                "command": current_summary_command,
                "summary_command": current_summary_command,
                "full_fallback_command": full_trace_command,
            },
            "claimed_intent": {
                "status": "external_route_required",
                "command": "./repo-python tools/meta/factory/work_ledger.py session-claims --limit 40",
            },
            "head_and_dirty_tree": {
                "status": "external_route_required",
                "command": (
                    "./repo-python tools/meta/control/git_state_snapshot.py "
                    "--path-limit 120 --recent-limit 25 --include-upstream --compact"
                ),
            },
            "owner_path": {
                "status": "external_route_required",
                "command": (
                    "./repo-python tools/meta/control/mission_transaction_preflight.py "
                    "--subject-id <id> --owned-path <path> --fail-on-status blocked"
                ),
            },
            "commands_run": {
                "status": "external_route_required",
                "command": "./repo-python kernel.py --command-profile <surface>",
            },
            "validation": {
                "status": "external_route_required",
                "command": "./repo-python tools/meta/control/mission_transaction_preflight.py --control-summary",
            },
            "task_work_ledger_disposition": {
                "status": "external_route_required",
                "task_ledger_command": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "organizer-report --transcript-file-limit 2"
                ),
                "work_ledger_command": (
                    WORK_LEDGER_SEED_SPEED_COMMAND
                ),
            },
            "commit_or_failed_landing": {
                "status": "scoped_commit_required",
                "command": "./repo-python tools/meta/control/scoped_commit.py --help",
            },
        },
        "trust_rule": (
            "Do not promote a trace or closeout claim to substrate truth until "
            "Git HEAD, owned paths, validation, and ledger disposition confirm it."
        ),
        "omission_receipt": {
            "omitted": [
                "raw session bodies",
                "raw diffs",
                "full Work Ledger session cards",
                "full Task Ledger organizer report",
            ],
            "reason": (
                "The handoff names proof routes and transaction edges; detailed "
                "evidence stays behind the owner commands."
            ),
        },
    }


def build_report(
    *,
    lens: str = "all",
    store: str = "both",
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    project: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Build the stable session-diagnostics report consumed by CLI and kernel."""
    lens = normalize_lens_name(lens)
    if store not in {"claude", "codex", "both"}:
        raise ValueError(f"unknown store: {store}")
    _records_for_path.cache_clear()

    claude_files: list[Path] = []
    codex_files: list[Path] = []
    if store in ("claude", "both"):
        claude_files = claude_session_files(project)
        claude_files = filter_by_window(claude_files, after, before)[:last]
    if store in ("codex", "both"):
        codex_files = codex_rollout_files()
        codex_files = filter_by_window(codex_files, after, before)[:last]

    facts: SessionDiagnosticsFacts | None = None
    scan_wall_ms: int | None = None
    if lens == "all":
        scan_started = time.perf_counter()
        facts = _build_session_diagnostics_facts(claude_files, codex_files)
        scan_wall_ms = round((time.perf_counter() - scan_started) * 1000)

    summary = {
        "stores": {
            "claude_project_dir": str(resolve_claude_project_dir(project)),
            "codex_root": str(CODEX_ROOT),
        },
        "window": {"after": after, "before": before, "last": last},
        "counts": {
            "claude_sessions": len(claude_files),
            "codex_sessions": len(codex_files),
        },
        "trace_to_git_handoff": _build_trace_to_git_handoff(
            lens=lens,
            store=store,
            last=last,
            source_kind="agent_session_diagnostics",
        ),
    }

    lenses_to_run = list(LENSES.keys()) if lens == "all" else [lens]
    lens_payload: dict[str, Any] = {}
    lens_wall_ms: dict[str, int] = {}
    # In all-mode, prompts/wake-prompts are computed before route-misses so
    # route-misses can reuse them via kwargs and avoid recomputation.
    if lens == "all":
        ordered = [
            name
            for name in (
                "histogram", "hotspots", "ladder-skip", "latency",
                "prompts", "wake-prompts", "route-misses", "errors",
                "experience-frictions",
            )
            if name in LENSES
        ]
    else:
        ordered = lenses_to_run
    for name in ordered:
        fn = LENSES[name]
        started = time.perf_counter()
        if facts is not None and name == "latency":
            lens_payload[name] = _facts_latency(
                facts,
                limit,
                include_codex_sqlite=store in ("codex", "both"),
            )
        elif facts is not None and name in _FACT_LENS_PROJECTORS:
            lens_payload[name] = _FACT_LENS_PROJECTORS[name](facts, limit)
        elif name == "route-misses":
            lens_payload[name] = fn(
                claude_files, codex_files, limit,
                prompts_payload=lens_payload.get("prompts"),
                wake_payload=lens_payload.get("wake-prompts"),
            )
        elif name == "latency":
            lens_payload[name] = fn(
                claude_files,
                codex_files,
                limit,
                include_codex_sqlite=store in ("codex", "both"),
            )
        elif name in ("wake-prompts", "experience-frictions"):
            lens_payload[name] = fn(claude_files, codex_files, limit)
        else:
            lens_payload[name] = fn(claude_files, limit)
        lens_wall_ms[name] = round((time.perf_counter() - started) * 1000)

    if "prompts" in lens_payload:
        lens_payload["prompts"] = _sanitize_prompt_payload(lens_payload["prompts"])
    if "wake-prompts" in lens_payload:
        lens_payload["wake-prompts"] = _sanitize_wake_prompt_payload(lens_payload["wake-prompts"])

    diagnostic_profile: dict[str, Any] = {
        "lens_wall_ms": lens_wall_ms,
        "profile_scope": "in_process_lens_build_only",
    }
    if facts is not None:
        diagnostic_profile["scan_wall_ms"] = scan_wall_ms
        diagnostic_profile["scan_counts"] = {
            "claude_sessions": len(facts.claude),
            "codex_sessions": len(facts.codex),
        }

    report = {
        "kind": "agent_session_diagnostics",
        "schema_version": "agent_session_diagnostics_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": summary,
        "lenses": lens_payload,
        "diagnostic_profile": diagnostic_profile,
        "host_pressure_surface": _build_host_pressure_surface(),
    }
    report["trace_improvement_surface"] = summarize_report(report)["trace_improvement_surface"]
    return report


def _build_host_pressure_surface(*, window_s: int = 900) -> dict[str, Any]:
    """Attach the compact host-pressure surface to diagnostics without tracing."""
    try:
        from system.lib.agent_observability import AgentTraceStore
        from system.lib.host_pressure import build_progress_pressure_packet_from_store

        store = AgentTraceStore(REPO_ROOT)
        return build_progress_pressure_packet_from_store(
            store,
            REPO_ROOT,
            window_s=window_s,
            event_limit=500,
            include_processes=False,
        )
    except Exception as exc:  # noqa: BLE001 - diagnostics must degrade
        return {
            "kind": "progress_pressure_ledger",
            "schema_version": "progress_pressure_packet_v0",
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "summary": {
                "bottleneck_class": "unknown_needs_trace",
                "governor_decision": "host_pressure_unavailable",
                "confidence": "low",
            },
        }


def _deferred_host_pressure_surface() -> dict[str, Any]:
    return {
        "kind": "progress_pressure_ledger",
        "schema_version": "progress_pressure_packet_v0",
        "status": "deferred_in_first_contact_summary",
        "summary": {
            "bottleneck_class": "deferred_to_host_pressure_surface",
            "governor_decision": "deferred",
            "confidence": "not_measured",
        },
        "deferred_reason": (
            "Bare session diagnostics keeps first-contact latency low; run the "
            "host-pressure summary route when host scheduling authority is needed."
        ),
        "summary_first_command": HOST_PRESSURE_SUMMARY_FIRST_COMMAND,
    }


def build_summary_report(
    *,
    store: str = "both",
    last: int = 20,
    after: str | None = None,
    before: str | None = None,
    project: str | None = None,
    limit: int = 20,
    host_pressure_mode: str = "full",
    codex_max_scan_bytes: int | None = None,
) -> dict[str, Any]:
    """Build the compact diagnostics packet without running every full lens.

    The full `all` report intentionally preserves drilldown detail. Summary mode
    is a bird's-eye control surface, so it scans each selected session once and
    omits docs-route probing until the route-misses drilldown is requested.
    """
    if store not in {"claude", "codex", "both"}:
        raise ValueError(f"unknown store: {store}")
    if host_pressure_mode not in {"full", "deferred"}:
        raise ValueError(f"unknown host_pressure_mode: {host_pressure_mode}")
    effective_codex_max_scan_bytes = (
        CODEX_SUMMARY_SCAN_MAX_BYTES
        if codex_max_scan_bytes is None
        else codex_max_scan_bytes
    )
    profile_started = time.perf_counter()
    phase_wall_ms: dict[str, int] = {}
    _records_for_path.cache_clear()

    claude_files: list[Path] = []
    codex_files: list[Path] = []
    if store in ("claude", "both"):
        started = time.perf_counter()
        claude_files = filter_by_window(claude_session_files(project), after, before)[:last]
        phase_wall_ms["discover_claude_files"] = round((time.perf_counter() - started) * 1000)
    if store in ("codex", "both"):
        started = time.perf_counter()
        codex_files = filter_by_window(codex_rollout_files(), after, before)[:last]
        phase_wall_ms["discover_codex_files"] = round((time.perf_counter() - started) * 1000)

    tools = collections.Counter()
    bash_verbs = collections.Counter()
    bad_bash = collections.Counter()
    good_bash = collections.Counter()
    kernel_nav_calls = collections.Counter()
    reads = collections.Counter()
    edits = collections.Counter()
    read_sessions = collections.defaultdict(set)
    reread_events: list[dict[str, Any]] = []
    grep_before_nav = 0
    prompts: list[dict[str, Any]] = []
    wake_seen: dict[str, dict[str, Any]] = {}
    wake_repeat_buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    interrupts: list[dict[str, Any]] = []
    tool_errors = collections.Counter()
    experience_buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    total_records = 0

    def _bash_first_word(command: str) -> str:
        parts = command.strip().split()
        if not parts:
            return ""
        first = parts[0]
        if first in {"env", "sudo"} and len(parts) > 1:
            first = parts[1]
        if first.startswith("./"):
            first = first.split("/")[-1]
        return first

    def _record_wake(source: str, session_tag: str, ts: str, text: str) -> None:
        text = text.strip()
        if not _is_wake_prompt(text):
            return
        prompt_sha16, excerpt = _wake_prompt_repeat_fingerprint(text)
        wake_repeat_buckets[prompt_sha16].append({
            "source": source,
            "session": session_tag,
            "ts": ts,
            "excerpt": excerpt,
        })
        key = text[:220]
        if key in wake_seen:
            return
        wake_seen[key] = {
            "source": source,
            "session": session_tag,
            "ts": ts,
            "length": len(text),
            "text": text,
        }

    started = time.perf_counter()
    for fp in claude_files:
        facts = _claude_summary_facts_fast(fp, experience_buckets=experience_buckets)
        tools.update(facts.tool_histogram)
        bash_verbs.update(facts.bash_verbs)
        bad_bash.update(facts.bad_bash)
        good_bash.update(facts.good_bash)
        kernel_nav_calls.update(facts.kernel_nav_calls)
        reads.update(facts.reads)
        edits.update(facts.edits)
        for read_path in facts.reads:
            read_sessions[read_path].add(facts.session_id)
        total_records += facts.records
        if facts.first_user:
            prompts.append({
                "session": facts.session_id,
                "first_user": facts.first_user,
                "interrupted": facts.user_interrupted,
            })
        if facts.user_interrupted:
            interrupts.append(_interrupt_ref(session=facts.session_id, first_user=facts.first_user))
        if facts.rereads:
            reread_events.append({
                "session": facts.session_id,
                "rereads": facts.rereads,
            })
        grep_before_nav += facts.grep_before_nav
        tool_errors.update(facts.tool_error_lines)
        for ts, text in facts.user_messages:
            _record_wake("claude", facts.session_id, ts, text)
    phase_wall_ms["scan_claude_summary"] = round((time.perf_counter() - started) * 1000)

    codex_stats: list[dict[str, Any]] = []
    codex_file_bytes = 0
    codex_scanned_bytes = 0
    codex_truncated_files = 0
    started = time.perf_counter()
    for fp in codex_files:
        facts = _codex_session_facts_fast(
            fp,
            experience_buckets=experience_buckets,
            max_scan_bytes=effective_codex_max_scan_bytes,
        )
        codex_file_bytes += facts.file_size_bytes
        codex_scanned_bytes += facts.bytes_scanned
        if facts.scan_truncated:
            codex_truncated_files += 1
        for ts, text in facts.user_messages:
            _record_wake("codex", fp.name[:55], ts, text)
        ws = facts.wallclock_s
        codex_stats.append({
            "path": fp.name,
            "records": facts.records,
            "function_calls": facts.function_calls,
            "turns": facts.turns,
            "compactions": facts.compactions,
            "wallclock_s": round(ws) if ws else None,
            "scan_mode": facts.scan_mode,
            "scan_truncated": facts.scan_truncated,
            "file_size_bytes": facts.file_size_bytes,
            "bytes_scanned": facts.bytes_scanned,
            "count_semantics": "sample_lower_bound" if facts.scan_truncated else "exact",
        })
    phase_wall_ms["scan_codex_summary"] = round((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    rediscovery = [
        (path, count, len(read_sessions[path]), count * len(read_sessions[path]))
        for path, count in reads.items()
    ]
    rediscovery.sort(key=lambda row: -row[3])
    wake_prompts = sorted(wake_seen.values(), key=lambda row: row.get("ts") or "", reverse=True)
    wake_repetition_clusters = _wake_prompt_repetition_clusters(wake_repeat_buckets, limit=limit)

    route_phrases: dict[str, None] = {}
    for row in prompts[: max(limit, 20)]:
        for phrase in _route_miss_candidate_phrases(str(row.get("first_user") or ""), limit=limit):
            route_phrases[phrase] = None
    for row in wake_prompts[: max(limit, 20)]:
        for phrase in _route_miss_candidate_phrases(str(row.get("text") or ""), limit=limit):
            route_phrases[phrase] = None

    total_bad = sum(bad_bash.values())
    total_good = sum(good_bash.values())
    wake_prompt_payload = {
        "sessions_analyzed": len(claude_files) + len(codex_files),
        "claude_sessions": len(claude_files),
        "codex_sessions": len(codex_files),
        "matched_wake_prompt_count": sum(len(entries) for entries in wake_repeat_buckets.values()),
        "unique_wake_prompts": len(wake_prompts),
        "repeated_prompt_cluster_count": len(wake_repetition_clusters),
        "repetition_clusters": wake_repetition_clusters,
        "detection_policy": (
            "Precision-biased autonomous-seed wake prompt detection; repeated clusters "
            "mean exact normalized prompt text occurred more than once."
        ),
        "prompts": wake_prompts[:limit],
    }
    phase_wall_ms["aggregate_summary_lenses"] = round((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    host_pressure_surface = (
        _deferred_host_pressure_surface()
        if host_pressure_mode == "deferred"
        else _build_host_pressure_surface()
    )
    phase_wall_ms["host_pressure_surface"] = round((time.perf_counter() - started) * 1000)

    report = {
        "kind": "agent_session_diagnostics_fast_scan",
        "schema_version": "agent_session_diagnostics_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": {
            "stores": {
                "claude_project_dir": str(resolve_claude_project_dir(project)),
                "codex_root": str(CODEX_ROOT),
            },
            "window": {"after": after, "before": before, "last": last},
            "counts": {
                "claude_sessions": len(claude_files),
                "codex_sessions": len(codex_files),
            },
        },
        "lenses": {
            "histogram": {
                "sessions_analyzed": len(claude_files),
                "total_records": total_records,
                "tool_histogram": tools.most_common(limit),
                "bash_verbs": bash_verbs.most_common(limit),
            },
            "hotspots": {
                "sessions_analyzed": len(claude_files),
                "top_reads": [{"path": p, "reads": c} for p, c in reads.most_common(limit)],
                "top_edits": [{"path": p, "edits": c} for p, c in edits.most_common(limit)],
                "rediscovery": [
                    {"path": p, "reads": r, "distinct_sessions": s, "score": score}
                    for p, r, s, score in rediscovery[:limit]
                ],
            },
            "ladder-skip": {
                "sessions_analyzed": len(claude_files),
                "bash_should_be_native": bad_bash.most_common(limit),
                "bash_repo_tooling": good_bash.most_common(limit),
                "ratio_bad_to_good_bash": round(total_bad / max(total_good, 1), 3),
                "kernel_nav_flag_calls": kernel_nav_calls.most_common(),
                "grep_calls_before_any_nav_flag": grep_before_nav,
                "reread_events": reread_events[:limit],
            },
            "latency": {
                "claude_sessions": [],
                "codex_sessions": codex_stats[:limit],
                "codex_sqlite_7d": None,
            },
            "wake-prompts": _sanitize_wake_prompt_payload(wake_prompt_payload),
            "route-misses": {
                "sessions_analyzed": len(claude_files) + len(codex_files),
                "source_prompt_count": len(prompts) + len(wake_prompts),
                "candidate_count": len(route_phrases),
                "resolved_count": None,
                "unresolved_count": None,
                "probe_status": "omitted_in_summary",
                "write_flag": "--write-route-miss-candidates <path>",
                "candidates": [{"phrase": phrase} for phrase in list(route_phrases)[:limit]],
            },
            "errors": {
                "sessions_analyzed": len(claude_files),
                "user_interrupts": interrupts[:limit],
                "top_tool_error_lines": tool_errors.most_common(limit),
            },
            "experience-frictions": _experience_friction_payload(
                experience_buckets,
                sessions_analyzed=len(claude_files) + len(codex_files),
                limit=limit,
            ),
        },
        "host_pressure_surface": host_pressure_surface,
    }
    started = time.perf_counter()
    summary = summarize_report(report)
    phase_wall_ms["summarize_report"] = round((time.perf_counter() - started) * 1000)
    summary["source_kind"] = "agent_session_diagnostics_fast_scan"
    phase_wall_ms["total"] = round((time.perf_counter() - profile_started) * 1000)
    summary["diagnostic_profile"] = {
        "profile_scope": "summary_mode_in_process",
        "host_pressure_mode": host_pressure_mode,
        "codex_max_scan_bytes": effective_codex_max_scan_bytes,
        "phase_wall_ms": phase_wall_ms,
        "scan_counts": {
            "claude_sessions": len(claude_files),
            "codex_sessions": len(codex_files),
            "codex_file_bytes": codex_file_bytes,
            "codex_scanned_bytes": codex_scanned_bytes,
            "codex_truncated_files": codex_truncated_files,
        },
    }
    summary["metrics"]["discoverability"]["route_miss_probe_status"] = "omitted_in_summary"
    if (
        summary.get("summary_first_sufficiency", {}).get("selected_lens")
        == "route-misses"
    ):
        summary["next"][0]["reason"] = (
            "Route-miss resolution is the active drilldown; probe docs-route only inside this selected lens."
        )
    return summary


def emit_report(report: dict[str, Any], output: str) -> None:
    if output == "json":
        print(json.dumps(report, indent=2, default=str))
        return
    _emit_table("summary", report.get("summary"))
    for name, data in (report.get("lenses") or {}).items():
        _emit_table(name, data)


def _safe_lens(report: dict[str, Any], name: str) -> dict[str, Any]:
    payload = (report.get("lenses") or {}).get(name)
    return payload if isinstance(payload, dict) else {}


def _json_estimated_bytes(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, default=str, sort_keys=True).encode("utf-8"))


HOST_PRESSURE_SUMMARY_FIRST_COMMAND = (
    "./repo-python kernel.py --host-pressure --host-pressure-no-processes "
    "--host-pressure-event-limit 500 --json"
)
HOST_PRESSURE_PROCESS_DRILLDOWN_COMMAND = "./repo-python kernel.py --host-pressure --json"


def _compact_host_pressure_surface(surface: dict[str, Any]) -> dict[str, Any]:
    if not surface:
        return {}
    host = surface.get("host") if isinstance(surface.get("host"), dict) else {}
    agents = surface.get("agents") if isinstance(surface.get("agents"), dict) else {}
    pressure = surface.get("pressure") if isinstance(surface.get("pressure"), dict) else {}
    summary = surface.get("summary") if isinstance(surface.get("summary"), dict) else {}
    envelope = (
        surface.get("codex_parallelism_envelope")
        if isinstance(surface.get("codex_parallelism_envelope"), dict)
        else {}
    )
    activation = (
        surface.get("host_pressure_activation_receipt")
        if isinstance(surface.get("host_pressure_activation_receipt"), dict)
        else {}
    )
    assay = (
        surface.get("host_pressure_assay_receipt")
        if isinstance(surface.get("host_pressure_assay_receipt"), dict)
        else {}
    )
    endpoint_probe = (
        activation.get("endpoint_probe")
        if isinstance(activation.get("endpoint_probe"), dict)
        else {}
    )
    return {
        "kind": surface.get("kind"),
        "schema_version": surface.get("schema_version"),
        "generated_at": surface.get("generated_at"),
        "window_s": surface.get("window_s"),
        "summary": {
            "active_agents": summary.get("active_agents"),
            "progress_units": summary.get("progress_units"),
            "pressure_index": summary.get("pressure_index"),
            "progress_per_pressure": summary.get("progress_per_pressure"),
            "bottleneck_class": summary.get("bottleneck_class"),
            "governor_decision": summary.get("governor_decision"),
            "admission_default_decision": summary.get("admission_default_decision"),
            "load_shed_recommended": summary.get("load_shed_recommended"),
            "resident_pressure_mode": summary.get("resident_pressure_mode"),
            "runtime_readiness_status": summary.get("runtime_readiness_status"),
            "runtime_readiness_next_action": summary.get("runtime_readiness_next_action"),
            "confidence": summary.get("confidence"),
        },
        "pressure": {
            "cpu_class": pressure.get("cpu_class"),
            "memory_class": pressure.get("memory_class"),
            "disk_class": pressure.get("disk_class"),
            "network_class": pressure.get("network_class"),
            "sandbox_class": pressure.get("sandbox_class"),
            "pressure_index": pressure.get("pressure_index"),
        },
        "agents": {
            "active_agent_count": agents.get("active_agent_count"),
            "trace_session_count": agents.get("trace_session_count"),
            "process_agent_hint": agents.get("process_agent_hint"),
            "process_count": agents.get("process_count"),
            "process_kind_counts": agents.get("process_kind_counts"),
        },
        "policy_source": envelope.get("policy_source"),
        "activation": {
            "schema_version": activation.get("schema_version"),
            "endpoint_status": endpoint_probe.get("status"),
            "http_status": endpoint_probe.get("http_status"),
            "action_taken": activation.get("action_taken"),
        },
        "assay": {
            "schema_version": assay.get("schema_version"),
            "status": assay.get("status"),
            "calibration_status": assay.get("calibration_status"),
            "workload_class": assay.get("workload_class"),
            "agent_count": assay.get("agent_count"),
            "marginal_progress_curve_status": assay.get("marginal_progress_curve_status"),
        },
        "collection_warning_count": len(host.get("collection_warnings") or []),
        "raw_drilldown_refs": surface.get("raw_drilldown_refs") if isinstance(surface.get("raw_drilldown_refs"), dict) else {},
        "summary_omission_receipt": {
            "omitted": "full host-pressure resident, relief, admission calibration, and endpoint detail",
            "drilldown": HOST_PRESSURE_SUMMARY_FIRST_COMMAND,
        },
    }


def _coerce_count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _context_top_read_count(context: dict[str, Any]) -> int:
    counts: list[int] = []
    for key in ("top_reads", "rediscovery"):
        rows = context.get(key)
        if not isinstance(rows, list):
            continue
        counts.extend(
            _coerce_count(row.get("reads"))
            for row in rows
            if isinstance(row, dict)
        )
    return max(counts or [0])


def _context_reread_pressure_count(context: dict[str, Any]) -> int:
    return max(
        _coerce_count(context.get("reread_pressure_count")),
        _coerce_count(context.get("reread_file_count")),
        _coerce_count(context.get("max_rereads_per_file")),
        _context_top_read_count(context),
    )


def _compact_text(value: Any, *, max_chars: int = 180) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _status_from_fail_warn(*, fail: bool = False, warn: bool = False) -> str:
    if fail:
        return "fail"
    if warn:
        return "warn"
    return "pass"


def _select_summary_drilldown(metrics: dict[str, Any]) -> dict[str, str]:
    context = metrics.get("context_pressure") if isinstance(metrics.get("context_pressure"), dict) else {}
    ladder = metrics.get("ladder_skip") if isinstance(metrics.get("ladder_skip"), dict) else {}
    discoverability = metrics.get("discoverability") if isinstance(metrics.get("discoverability"), dict) else {}
    recovery = metrics.get("recovery") if isinstance(metrics.get("recovery"), dict) else {}
    experience = metrics.get("experience_frictions") if isinstance(metrics.get("experience_frictions"), dict) else {}
    max_compactions = _coerce_count(context.get("max_compactions"))
    reread_pressure_count = _context_reread_pressure_count(context)

    if max_compactions >= 2 or reread_pressure_count >= 10:
        runtime_focus = _context_pressure_store_hint(max_compactions, reread_pressure_count)
        context_evidence = dict(context)
        context_evidence["runtime_focus"] = runtime_focus
        context_evidence["reread_pressure_count"] = reread_pressure_count
        context_command = _context_pressure_runtime_commands(context_evidence, last=10)[0]
        context_lens = "hotspots" if "--lens hotspots" in context_command else "latency"
        return {
            "lens": context_lens,
            "command": context_command,
            "reason": (
                "Context pressure is active: inspect the dominant runtime first instead "
                "of opening both trace stores."
            ),
        }
    if _coerce_count(ladder.get("grep_calls_before_any_nav_flag")) > 0 or float(ladder.get("ratio_bad_to_good_bash") or 0.0) >= 0.2:
        return {
            "lens": "ladder-skip",
            "command": _session_diagnostics_command("ladder-skip", last=10, store="claude"),
            "reason": "Ladder drift is active: inspect Claude ladder-skip rows before broad trace stores.",
        }
    if _coerce_count(discoverability.get("route_miss_unresolved")) > 0 or _coerce_count(discoverability.get("route_miss_candidates")) > 0:
        return {
            "lens": "route-misses",
            "command": "./repo-python kernel.py --session-diagnostics --lens route-misses --last 10 --store both --json",
            "reason": "Discoverability is active: route-miss candidates exist, so inspect only route-miss rows.",
        }
    if _coerce_count(recovery.get("user_interrupt_count")) > 0:
        return {
            "lens": "errors",
            "command": "./repo-python kernel.py --session-diagnostics --lens errors --last 10 --store both --json",
            "reason": "Recovery is active: interrupts or errors exist, so inspect only error rows.",
        }
    if _coerce_count(experience.get("event_count")) > 0:
        return {
            "lens": "experience-frictions",
            "command": "./repo-python kernel.py --session-diagnostics --lens experience-frictions --last 20 --store both --json",
            "reason": "Experience-friction episodes are active: inspect classified repair-shaped updates before raw trace bodies.",
        }
    return {
        "lens": "none",
        "command": "",
        "reason": "No detailed drilldown is indicated by the compact summary.",
    }


_TRACE_CAP_VIEW_IDS = (
    "missing_contracts_ranked",
    "capture_triage",
    "propagation_needed",
    "execution_menu",
    "promotion_candidates",
)

_TRACE_CAP_TERMS = (
    "agent trace",
    "agent traces",
    "agent observability",
    "session diagnostics",
    "process audit",
    "process trace",
    "trace forensics",
    "trace live",
    "trace tape",
    "trace compact",
    "trace compactness",
    "telemetry",
    "route miss",
    "route misses",
    "bottleneck",
    "friction",
)
_TRACE_CAP_NON_ACTION_RECOMMENDATIONS = {
    "no_action",
    "no_action_closed",
    "no_action_needed",
    "none",
}
_TRACE_CAP_TERMINAL_TRIAGE_STATUSES = {
    "closed",
    "closed_or_signed_off",
    "done",
    "retired",
    "signed_off",
}
_TRACE_CAP_TERMINAL_STATES = {
    "closed",
    "completed",
    "completed_with_validation_residuals",
    "done",
    "propagated",
    "retired",
    "satisfied",
    "signed_off",
    "signoff",
}

_TRACE_CAP_SCORE_FIELDS = (
    "id",
    "title",
    "state",
    "candidate_work_item_type",
    "missing_fields",
    "recommended_action",
    "summary",
    "statement",
    "satisfaction_summary",
    "tags",
)


def _task_ledger_view_items(view_id: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / "state" / "task_ledger" / "views" / f"{view_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _trace_cap_score(item: dict[str, Any]) -> int:
    parts: list[str] = []
    for field_name in _TRACE_CAP_SCORE_FIELDS:
        value = item.get(field_name)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(part) for part in value)
        elif isinstance(value, dict):
            parts.append(json.dumps(value, default=str, sort_keys=True))
        else:
            parts.append(str(value))
    raw = " ".join(parts)
    text = re.sub(r"[-_]+", " ", raw).lower()
    score = 0
    for term in _TRACE_CAP_TERMS:
        normalized = re.sub(r"[-_]+", " ", term).lower()
        if normalized in text:
            score += 10 if "trace" in normalized else 6
    missing_fields = item.get("missing_fields")
    if isinstance(missing_fields, list) and missing_fields:
        score += 4
    state = str(item.get("state") or "")
    if state in {"captured", "shaping", "ready", "claimed"}:
        score += 2
    return score


def _trace_cap_is_actionable(row: dict[str, Any]) -> bool:
    missing_fields = row.get("missing_fields")
    if isinstance(missing_fields, list) and missing_fields:
        return True
    recommended_action = str(row.get("recommended_action") or "").strip().lower()
    if recommended_action in _TRACE_CAP_NON_ACTION_RECOMMENDATIONS:
        return False
    triage_status = str(row.get("triage_status") or "").strip().lower()
    if triage_status in _TRACE_CAP_TERMINAL_TRIAGE_STATUSES:
        return False
    state = str(row.get("state") or "").strip().lower()
    if state in _TRACE_CAP_TERMINAL_STATES:
        return False
    return bool(
        recommended_action
        or triage_status
        or state in {"captured", "claimed", "ready", "shaping"}
    )


def _task_ledger_trace_cap_matches(*, limit: int = 5) -> dict[str, Any]:
    """Return trace-observability CAP/WorkItem matches from projection views.

    This stays read-only and deliberately points to Task Ledger owner commands.
    The views are projections; events.jsonl remains mutation authority.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for view_id in _TRACE_CAP_VIEW_IDS:
        for item in _task_ledger_view_items(view_id):
            row_id = str(item.get("id") or "")
            if not row_id:
                continue
            score = _trace_cap_score(item)
            if score <= 0:
                continue
            current = by_id.setdefault(
                row_id,
                {
                    "id": row_id,
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "work_item_type": item.get("work_item_type"),
                    "candidate_work_item_type": item.get("candidate_work_item_type"),
                    "missing_fields": item.get("missing_fields") or [],
                    "triage_status": item.get("triage_status"),
                    "recommended_action": item.get("recommended_action"),
                    "updated_at": item.get("updated_at"),
                    "views": [],
                    "score": 0,
                },
            )
            current["score"] = max(int(current.get("score") or 0), score)
            if view_id not in current["views"]:
                current["views"].append(view_id)
            if not current.get("title") and item.get("title"):
                current["title"] = item.get("title")
            if not current.get("state") and item.get("state"):
                current["state"] = item.get("state")
            if not current.get("work_item_type") and item.get("work_item_type"):
                current["work_item_type"] = item.get("work_item_type")
            if (
                not current.get("candidate_work_item_type")
                and item.get("candidate_work_item_type")
            ):
                current["candidate_work_item_type"] = item.get("candidate_work_item_type")
            if not current.get("triage_status") and item.get("triage_status"):
                current["triage_status"] = item.get("triage_status")
            if not current.get("recommended_action") and item.get("recommended_action"):
                current["recommended_action"] = item.get("recommended_action")
            if not current.get("updated_at") and item.get("updated_at"):
                current["updated_at"] = item.get("updated_at")
            for field in item.get("missing_fields") or []:
                if field not in current["missing_fields"]:
                    current["missing_fields"].append(field)
    rows = sorted(
        by_id.values(),
        key=lambda row: (
            int(row.get("score") or 0),
            str(row.get("updated_at") or ""),
        ),
        reverse=True,
    )[:limit]
    card_ids = ",".join(str(row.get("id")) for row in rows if row.get("id"))
    return {
        "status": "available" if rows else "no_trace_cap_matches",
        "view_ids": list(_TRACE_CAP_VIEW_IDS),
        "match_count": len(rows),
        "rows": rows,
        "authority": "state/task_ledger/views/* are projections; mutate through state/task_ledger/events.jsonl",
        "next_command": (
            f"./repo-python kernel.py --option-surface task_ledger --band card --ids {card_ids}"
            if card_ids
            else "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2"
        ),
    }


def _compact_trace_cap_rows(rows: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        compact.append({
            "id": row.get("id"),
            "state": row.get("state"),
            "work_item_type": row.get("work_item_type"),
            "candidate_work_item_type": row.get("candidate_work_item_type"),
            "triage_status": row.get("triage_status"),
            "recommended_action": row.get("recommended_action"),
            "missing_fields": list(row.get("missing_fields") or [])[:5],
            "views": list(row.get("views") or [])[:5],
        })
    return compact


def _trace_summary_action_contract(
    *,
    symptom_family: str,
    owner_surface: str,
    next_command: str,
    evidence: dict[str, Any],
    source_lenses: list[str],
    cap_refs: list[str],
) -> dict[str, Any]:
    full_drilldown = str(next_command or "")
    if symptom_family == "context_pressure":
        first_drilldown = _summary_first_diagnostics_command(full_drilldown)
    elif symptom_family == "host_pressure":
        first_drilldown = HOST_PRESSURE_SUMMARY_FIRST_COMMAND
        if full_drilldown == first_drilldown:
            full_drilldown = HOST_PRESSURE_PROCESS_DRILLDOWN_COMMAND
    else:
        first_drilldown = full_drilldown
    cap_ref_kinds = _trace_cap_ref_kinds(symptom_family=symptom_family, cap_refs=cap_refs)
    cap_policy = _trace_cap_policy(cap_ref_kinds)
    disconfirming_check = _TRACE_FRICTION_DISCONFIRMING_CHECK.get(
        symptom_family,
        "A later diagnostics window no longer emits the selected symptom family after the owner action.",
    )
    contract = {
        "schema_version": "trace_summary_owner_action_contract_v1",
        "mode": "selector_not_authority",
        "owner_type": _trace_friction_owner_type(owner_surface, symptom_family),
        "first_drilldown": first_drilldown,
        "supporting_drilldowns": _trace_summary_supporting_drilldowns(
            first_command=first_drilldown,
            evidence=evidence,
            source_lenses=source_lenses,
        ),
        "receipt_needed": _trace_friction_receipts(symptom_family, evidence=evidence),
        "disconfirming_check": disconfirming_check,
        "raw_body_policy": (
            "Do not open raw session bodies, prompt text, assistant prose, or tool stdout/stderr "
            "until the first drilldown proves the summary row is insufficient."
        ),
        "cap_policy": cap_policy,
        "self_propagation_rule": (
            "Patch the named owner surface when safe; otherwise record the exact blocked owner "
            "and re-entry condition through Task Ledger/Work Ledger."
        ),
    }
    if cap_ref_kinds:
        contract["cap_ref_kinds"] = cap_ref_kinds
    if symptom_family == "experience_friction" and _is_claim_contention_experience(evidence):
        contract["claim_contention_policy"] = (
            "Use claim cards as first evidence for ownership, scope, lease, and collision state. "
            "If a preflight returns a sessionless identity hint or candidate --session-id, rerun "
            "the check bound to that session before treating the claim as external or switching lanes. "
            "If preflight returns observed_path_overlaps without an active same-path claim collision, "
            "classify the overlap before treating it as a blocker."
        )
        contract["claim_contention_boundary_contract"] = _claim_contention_boundary_contract(
            first_drilldown=first_drilldown
        )
    if symptom_family == "context_pressure":
        context_contract = _context_pressure_summary_first_contract(
            evidence=evidence,
            first_drilldown=first_drilldown,
            full_drilldown=full_drilldown,
        )
        contract["context_pressure_summary_first_contract"] = context_contract
        if context_contract.get("runtime_support_routes"):
            contract["runtime_support_routes"] = context_contract["runtime_support_routes"]
        if context_contract.get("runtime_support_policy"):
            contract["runtime_support_policy"] = context_contract["runtime_support_policy"]
    if symptom_family == "recovery_friction":
        usage_contract = _command_usage_error_contract(
            evidence=evidence,
            first_drilldown=first_drilldown,
        )
        if usage_contract:
            contract["command_usage_error_contract"] = usage_contract
    if symptom_family == "route_discoverability":
        route_contract = _route_discoverability_resolution_contract(evidence=evidence)
        contract["route_discoverability_resolution_contract"] = route_contract
        if route_contract["status"] == "resolved_sidecar_trend_only":
            contract["self_propagation_rule"] = (
                "Do not patch docs-route aliases from resolved-only candidates. Persist or sample "
                "the route-miss sidecar, then re-enter docs-route ownership only if unresolved_count "
                "becomes positive or a sampled resolved candidate proves to be a false negative."
            )
        elif route_contract["status"] == "unresolved_probe_deferred":
            contract["self_propagation_rule"] = (
                "Do not patch docs-route aliases or mark the cohort resolved from a fast summary "
                "that omitted probing. Run the route-misses lens with sidecar output first, then "
                "re-enter the unresolved or resolved-only branch from that explicit count."
            )
    if symptom_family == "experience_friction":
        family_contracts = _experience_family_boundary_contracts(
            evidence=evidence,
            first_drilldown=first_drilldown,
        )
        if family_contracts:
            contract["experience_family_boundary_contracts"] = family_contracts
        if any(
            item.get("schema_version") == "metadata_settlement_boundary_contract_v0"
            for item in family_contracts
        ):
            contract["metadata_settlement_policy"] = (
                "Treat post-source Task Ledger/Work Ledger settlement as a separate authority lane: "
                "source commits, append-log receipts, projection freshness, and blocked re-entry "
                "conditions are different state axes."
            )
        if any(
            item.get("schema_version") == "closeout_authority_boundary_contract_v0"
            for item in family_contracts
        ):
            contract["closeout_authority_policy"] = (
                "Do not collapse local source landing, publication state, metadata settlement, active "
                "claims, and Work Ledger finalization into one closeout flag."
            )
        if any(
            item.get("schema_version") == "command_contract_boundary_contract_v0"
            for item in family_contracts
        ):
            contract["command_contract_policy"] = (
                "Treat repeated command, tool, schema, or edit-precondition failures as owner "
                "contract mismatches: classify the specific signature, run the help/validate or "
                "tool-surface check, then patch the command card, CLI help, standard, or dry-run "
                "lane instead of retrying from memory."
            )
        if any(
            item.get("schema_version") == "compaction_recovery_boundary_contract_v0"
            for item in family_contracts
        ):
            contract["compaction_recovery_policy"] = (
                "Treat compaction/resume as continuation-state preservation: recover owner, "
                "claim/session, validation, residual, and re-entry state from compact packets "
                "and authority routes before reopening raw trace bodies."
            )
        if any(
            item.get("schema_version") == "scoped_commit_cas_retry_boundary_contract_v0"
            for item in family_contracts
        ):
            contract["scoped_commit_cas_retry_policy"] = (
                "Treat scoped-commit CAS retry exhaustion as a landing-continuity handoff: "
                "preserve owned paths, validation evidence, HEAD movement, attempt count, and "
                "re-entry condition, then stop further ref mutation until a fresh owner resumes."
            )
    if symptom_family == "host_pressure":
        contract["runtime_readiness_contract"] = {
            "schema_version": "runtime_readiness_receipt_contract_v0",
            "classify_as": [
                "runtime_prerequisite_gap",
                "launch_readiness_receipt_gap",
                "background_work_receipt_gap",
            ],
            "required_fields": [
                "prerequisite_probe",
                "setup_or_install_authority",
                "launch_command_or_reuse_route",
                "readiness_probe",
                "detached_work_receipt",
                "status",
                "recheck_command",
            ],
            "status_values": ["passed", "failed", "blocked", "not_run"],
            "owner_rule": (
                "Use the named launcher/setup owner surface; do not specialize the repair around "
                "one product binary, cache path, server, or helper process."
            ),
            "admission_rule": (
                "Run the no-process host-pressure admission packet before starting new setup, "
                "browser, server, helper, test, or background work; sample process rows only when "
                "the compact packet cannot decide run, wait, reuse, or release."
            ),
        }
    if symptom_family == "rediscovery_hotspot" and evidence.get("owner_paper_module_slug"):
        slug = str(evidence.get("owner_paper_module_slug") or "")
        contract["paper_module_compression_contract"] = {
            "schema_version": "paper_module_rediscovery_compression_contract_v0",
            "classify_as": [
                "paper_module_card_fallback_compression",
                "source_reread_before_compression_passport",
                "projection_rebuild_or_blocked_receipt_gap",
            ],
            "owner_slug": slug,
            "card_command": next_command,
            "source_command": str(evidence.get("paper_module_source_command") or ""),
            "projection_check_command": str(evidence.get("paper_module_index_check_command") or ""),
            "write_profile": str(evidence.get("paper_module_write_profile") or "paper_module_index"),
            "rule": (
                "If the paper-module card reports fallback compression, author the compression "
                "passport in the source module and refresh the generated paper_module_index outputs, "
                "or record the host-pressure/owner blocker with an exact re-entry condition."
            ),
        }
    if symptom_family == "ladder_skip":
        contract["typed_route_replacement_contract"] = _ladder_skip_typed_route_replacement_contract(
            first_drilldown=first_drilldown
        )
        dominant_shape_contract = _ladder_skip_dominant_shell_shape_contract(
            evidence=evidence,
            first_drilldown=first_drilldown,
        )
        if dominant_shape_contract:
            contract["dominant_shell_shape_contract"] = dominant_shape_contract
    if first_drilldown != full_drilldown:
        contract["full_drilldown"] = full_drilldown
        if symptom_family == "host_pressure":
            contract["summary_first_reason"] = (
                "Host-pressure rows usually need admission, bottleneck, load-shed, and readiness "
                "receipts first; sample live process rows only when the no-process packet cannot "
                "decide whether a launcher/browser/helper should run, wait, or reuse/release."
            )
        else:
            contract["summary_first_reason"] = (
                "Context-pressure rows can usually be acted on from compact metrics; "
                "open full selected-lens JSON only when the compact receipt is insufficient."
            )
    return contract


def _context_pressure_summary_first_contract(
    *,
    evidence: dict[str, Any],
    first_drilldown: str,
    full_drilldown: str,
) -> dict[str, Any]:
    top_hotspot = (
        evidence.get("top_reread_hotspot")
        if isinstance(evidence.get("top_reread_hotspot"), dict)
        else {}
    )
    top_compaction = (
        evidence.get("top_compaction_session")
        if isinstance(evidence.get("top_compaction_session"), dict)
        else {}
    )
    has_hotspot = bool(top_hotspot.get("path"))
    hotspot_claim_check_route = _work_ledger_path_mutation_check_command(
        str(top_hotspot.get("path") or "")
    )
    process_summary_command = _context_pressure_process_summary_command(evidence)
    if not process_summary_command:
        runtime_scope = str(evidence.get("runtime_focus") or "both").strip().lower() or "both"
        process_summary_command = f"{_process_summary_cached_command(runtime_scope)} --force"
    cohort_omission_summary = _context_pressure_cohort_omission_summary(
        evidence=evidence,
        top_compaction=top_compaction,
    )
    runtime_support_routes = _context_pressure_runtime_support_routes(evidence)
    has_partial_cohort = bool(cohort_omission_summary.get("has_omitted_rows"))
    has_lower_bound_counts = bool(cohort_omission_summary.get("has_lower_bound_counts"))
    classify_as = [
        "summary_first_sufficiency",
        "reread_hotspot_pressure" if has_hotspot else "compaction_window_pressure",
        "owner_or_claim_check_before_source_body",
    ]
    if has_partial_cohort:
        classify_as.append("partial_context_pressure_cohort")
    if has_lower_bound_counts:
        classify_as.append("sample_lower_bound_scan")
    return {
        "schema_version": "context_pressure_summary_first_contract_v0",
        "classify_as": classify_as,
        "first_summary_route": first_drilldown,
        "full_drilldown_route": full_drilldown,
        "claim_cards_route": WORK_LEDGER_CLAIM_CARDS_COMMAND,
        "hotspot_claim_check_route": hotspot_claim_check_route if has_hotspot else None,
        "process_summary_route": process_summary_command,
        "runtime_focus": evidence.get("runtime_focus"),
        "max_compactions": evidence.get("max_compactions"),
        "reread_pressure_count": evidence.get("reread_pressure_count"),
        "top_reread_hotspot_path": top_hotspot.get("path"),
        "top_compaction_session_id": top_compaction.get("session_id"),
        "process_summary_lookup": top_compaction.get("process_summary_lookup"),
        "cohort_omission_summary": cohort_omission_summary,
        "runtime_support_routes": runtime_support_routes,
        "runtime_support_policy": (
            "When context pressure spans Codex compactions and Claude reread hotspots, "
            "preserve separate runtime-scoped summary routes instead of collapsing both "
            "signals into a single --store both drilldown."
        ),
        "allowed_actions": [
            "run_selected_lens_summary_first",
            "run_runtime_specific_support_summaries_when_mixed_pressure",
            "measure_summary_vs_full_size",
            "dogfood_last_10_and_last_30_windows",
            "read_cohort_omission_summary_before_treating_top_rows_as_complete",
            (
                "run_exact_hotspot_claim_check"
                if has_hotspot
                else "record_compaction_window_receipt"
            ),
            (
                "run_claim_cards_for_hotspot_owner"
                if has_hotspot
                else "skip_claim_cards_without_hotspot"
            ),
            "use_explicit_process_summary_only_when_resolvable",
        ],
        "blocked_actions": [
            "open_full_lens_json_before_summary_insufficient",
            "open_raw_trace_body_before_summary_insufficient",
            "reopen_hot_file_before_owner_or_claim_check",
            "treat_rollout_filename_as_verified_process_summary_id",
            "replace_row_selected_session_with_latest_when_session_is_resolvable",
            "treat_top_rows_as_complete_when_omitted_count_positive",
            "treat_sample_lower_bound_counts_as_exact",
        ],
        "receipt_fields": [
            "diagnostics_summary_size_check",
            "selected_lens_summary_command",
            "full_lens_fallback_command",
            "runtime_support_route_receipt",
            "cohort_omission_summary",
            "count_semantics_receipt",
            "last_10_window_check",
            "last_30_window_check",
            (
                "hotspot_owner_or_claim_check"
                if has_hotspot
                else "compaction_window_receipt"
            ),
            (
                "exact_hotspot_claim_check"
                if has_hotspot
                else "no_hotspot_claim_check_needed"
            ),
            "full_drilldown_not_used_or_insufficiency_reason",
        ],
    }


def _work_ledger_path_mutation_check_command(path: str) -> str:
    clean_path = path.strip()
    if not clean_path:
        return ""
    return (
        "./repo-python tools/meta/factory/work_ledger.py mutation-check "
        f"--path {shlex.quote(clean_path)} --require-exclusive"
    )


COMMAND_USAGE_OWNER_PATHS = {
    "task_ledger_apply.py": "tools/meta/factory/task_ledger_apply.py",
    "work_ledger.py": "tools/meta/factory/work_ledger.py",
    "scoped_commit.py": "tools/meta/control/scoped_commit.py",
    "mission_transaction_preflight.py": "tools/meta/control/mission_transaction_preflight.py",
}


def _repo_python_help_route(owner_path: str, subcommand: str | None = None) -> str:
    parts = ["./repo-python", owner_path]
    if subcommand:
        parts.append(subcommand)
    parts.append("--help")
    return " ".join(shlex.quote(part) for part in parts)


def _missing_tool_name(signature: str) -> str | None:
    match = re.search(
        r"no such tool available:\s*(?P<tool>[^<\n\r]+)",
        str(signature or ""),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    tool = match.group("tool").strip().strip("\"'")
    tool = tool.rstrip(".,;")
    return tool or None


def _missing_tool_fallback_route(tool_name: str | None) -> str | None:
    lower = str(tool_name or "").strip().lower()
    if lower in {"grep", "glob", "find"}:
        return "rg/rg --files after entry or context-pack selects a known owner scope"
    return None


def _command_usage_error_family(signature: str, count: int) -> dict[str, Any]:
    text = str(signature or "").strip()
    lower = text.lower()
    usage_match = re.match(r"usage:\s+(?P<script>[\w./-]+\.py)(?:\s+(?P<subcommand>[\w-]+))?", text)
    if usage_match:
        script = Path(usage_match.group("script")).name
        subcommand = usage_match.group("subcommand")
        owner_path = COMMAND_USAGE_OWNER_PATHS.get(script)
        family_parts = ["usage", Path(script).stem]
        if subcommand:
            family_parts.append(subcommand)
        row: dict[str, Any] = {
            "family": ":".join(family_parts),
            "count": count,
            "signature": text,
            "specific": True,
            "repair_class": "owner_command_help_before_retry",
            "owner_surface": owner_path or f"{script} owner command",
            "action": "run_owner_help_route_before_retrying_command",
        }
        if owner_path:
            row["help_route"] = _repo_python_help_route(owner_path, subcommand)
        return row
    if "no such tool available" in lower:
        missing_tool = _missing_tool_name(text)
        row = {
            "family": "tool_namespace_mismatch",
            "count": count,
            "signature": text,
            "specific": True,
            "repair_class": "current_tool_surface_check",
            "owner_surface": "current agent tool list and runtime instructions",
            "action": "select an available tool or repo command before retrying",
            "tool_surface_check": "current_agent_tool_manifest",
            "blocked_action": "retry_missing_provider_native_tool_name",
        }
        if missing_tool:
            row["missing_tool"] = missing_tool
        fallback_route = _missing_tool_fallback_route(missing_tool)
        if fallback_route:
            row["fallback_route"] = fallback_route
        return row
    if lower.startswith("exit code "):
        return {
            "family": "generic_exit_failure",
            "count": count,
            "signature": text,
            "specific": False,
            "repair_class": "pair_with_specific_error_signature",
            "owner_surface": "nearest specific failing owner command",
            "action": "do not select an owner from exit-code text alone",
        }
    return {
        "family": "unclassified_tool_error",
        "count": count,
        "signature": text,
        "specific": False,
        "repair_class": "classify_before_owner_patch",
        "owner_surface": "failing owner command",
        "action": "group the repeated signature before mutating an owner surface",
    }


def _compact_command_usage_error_families(tool_errors: list[Any], *, limit: int = 5) -> list[dict[str, Any]]:
    families: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in tool_errors:
        if isinstance(row, (list, tuple)) and row:
            signature = str(row[0] or "").strip()
            count = _coerce_count(row[1] if len(row) > 1 else 1)
        else:
            signature = str(row or "").strip()
            count = 1
        if not signature:
            continue
        family = _command_usage_error_family(signature, count)
        family_id = str(family.get("family") or signature)
        if family_id in seen:
            continue
        seen.add(family_id)
        families.append(family)
        if len(families) >= limit:
            break
    return families


def _recovery_friction_priority(command_usage_families: list[dict[str, Any]]) -> int:
    specific_counts = [
        _coerce_count(row.get("count"))
        for row in command_usage_families
        if row.get("specific")
    ]
    if not specific_counts:
        return 73
    if max(specific_counts) >= 10:
        return 78
    return 75


def _command_usage_error_contract(
    *,
    evidence: dict[str, Any],
    first_drilldown: str,
) -> dict[str, Any] | None:
    families = [
        row for row in evidence.get("top_command_usage_families") or []
        if isinstance(row, dict)
    ]
    if not families:
        return None
    specific_count = sum(1 for row in families if row.get("specific"))
    return {
        "schema_version": "command_usage_error_contract_v0",
        "classify_as": [
            "owner_command_usage_error",
            "tool_namespace_mismatch",
            "generic_exit_requires_specific_signature",
        ],
        "evidence_drilldown": first_drilldown,
        "top_error_families": families,
        "specific_family_count": specific_count,
        "selection_rule": (
            "Pick the highest-count specific usage or tool-namespace family; treat generic "
            "exit-code rows as supporting evidence only."
        ),
        "allowed_actions": [
            "run_owner_help_route_before_retrying_command",
            "check_current_tool_manifest_before_retrying_namespace_error",
            "patch_the_owner_skill_or_cli_help_when_usage_remains_ambiguous",
            "record_blocked_owner_and_reentry_condition_when_outside_current_authority",
        ],
        "blocked_actions": [
            "retry_same_malformed_command_without_help_route",
            "retry_missing_provider_native_tool_name",
            "open_raw_trace_body_before_specific_signature_is_insufficient",
            "select_owner_surface_from_generic_exit_code_alone",
        ],
        "receipt_fields": [
            "errors_lens_check",
            "usage_family_classification",
            "current_tool_surface_checked_or_not_applicable",
            "owner_help_route_checked_or_not_applicable",
            "owner_patch_or_blocked_reentry_condition",
            "post_repair_errors_window",
        ],
        "tool_namespace_contract": {
            "schema_version": "tool_namespace_mismatch_contract_v0",
            "required_fields": [
                "missing_tool",
                "tool_surface_check",
                "blocked_action",
                "fallback_route_or_not_applicable",
            ],
            "tool_surface_check": "current_agent_tool_manifest",
            "owner_rule": (
                "Namespace mismatch rows belong to the current runtime tool surface, not "
                "to the unavailable provider-native tool name."
            ),
            "fallback_rule": (
                "When the missing tool is a shell/file discovery primitive, use scoped "
                "repo commands only after the typed route selected an owner scope."
            ),
        },
    }


def _ladder_skip_typed_route_replacement_contract(*, first_drilldown: str) -> dict[str, Any]:
    return {
        "schema_version": "ladder_skip_typed_route_replacement_contract_v0",
        "classify_as": [
            "shell_search_before_typed_route",
            "ambient_discovery_without_owner",
            "command_card_gap",
        ],
        "evidence_drilldown": first_drilldown,
        "avoid_before_owner_route": [
            "grep/find/ls/cat/sed/awk/head/tail/wc/echo as ambient discovery",
            "cd ... && grep/find/ls wrapper chains before a selected owner route",
        ],
        "replacement_order": [
            {
                "step": "task_entry",
                "route": './repo-python kernel.py --entry "<task>" --context-budget 12000',
                "use_when": "A live task needs route selection before any debug or command-memory surface.",
            },
            {
                "step": "task_context",
                "route": LADDER_SKIP_TYPED_ROUTE_REPLACEMENT,
                "use_when": "The task still lacks a stable owner, kind, row, or path scope after entry.",
            },
            {
                "step": "selected_kind_or_row",
                "route": "./repo-python kernel.py --option-surface <kind_id> --band cluster_flag|card",
                "use_when": "Context-pack names a kind, cluster, or row before source search.",
            },
            {
                "step": "command_memory",
                "route": './repo-python kernel.py --command-card "<query>" --debug',
                "use_when": (
                    "The trace repeats command-choice discovery rather than source ownership, "
                    "and entry/context-pack have already selected the task family."
                ),
            },
            {
                "step": "scoped_shell",
                "route": "rg --files <known-scope> / rg <literal> <known-scope>",
                "use_when": "Only after a typed route selected the owner scope and shell search is still needed.",
            },
        ],
        "receipt_fields": [
            "typed_replacement_route",
            "selected_owner_surface_or_blocker",
            "post_repair_ladder_skip_window",
        ],
    }


def _ladder_skip_dominant_shell_shape_contract(
    *,
    evidence: dict[str, Any],
    first_drilldown: str,
) -> dict[str, Any] | None:
    if not isinstance(evidence, dict):
        return None
    shape = evidence.get("dominant_shell_shape")
    if not isinstance(shape, dict) or shape.get("shape") in {None, "", "none"}:
        return None
    shape_id = str(shape.get("shape") or "").strip()
    shape_actions = {
        "shell_banner_or_separator_chain": [
            "remove_echo_banner_separator_chains",
            "split_parallel_reads_without_shell_banners",
            "use_typed_owner_route_before_scoped_shell",
        ],
        "shell_search_before_typed_route": [
            "start_with_entry_then_context_pack",
            "open_selected_option_surface_card",
            "use_scoped_rg_only_after_owner_scope",
        ],
        "shell_read_or_inventory_before_owner_route": [
            "open_row_card_or_owner_summary_first",
            "read_files_only_after_path_scope_selected",
            "replace_inventory_shell_with_option_surface",
        ],
        "bash_native_before_typed_route": [
            "replace_shell_first_movement_with_navigation_ladder",
            "record_selected_owner_surface_or_blocker",
            "use_scoped_shell_only_inside_selected_owner_scope",
        ],
    }
    return {
        "schema_version": "ladder_skip_dominant_shell_shape_contract_v0",
        "shape": shape_id,
        "dominant_signal": shape.get("dominant_signal"),
        "top_verb": shape.get("top_verb"),
        "top_count": shape.get("top_count"),
        "grep_before_nav": shape.get("grep_before_nav"),
        "first_lens_route": first_drilldown,
        "replacement_route": shape.get("replacement_route") or LADDER_SKIP_TYPED_ROUTE_REPLACEMENT,
        "command_card_debug_route": shape.get("command_card_debug_route") or LADDER_SKIP_COMMAND_CARD_DEBUG,
        "replacement_hint": shape.get("replacement_hint"),
        "allowed_actions": shape_actions.get(shape_id, shape_actions["bash_native_before_typed_route"]),
        "blocked_actions": [
            "open_raw_trace_body_before_compact_shape_is_insufficient",
            "treat_echo_banners_as_harmless_when_they_dominate",
            "run_command_card_debug_before_entry_or_context_pack",
            "use_broad_grep_find_ls_before_owner_route",
        ],
        "receipt_fields": [
            "dominant_shell_shape",
            "replacement_route_consumed",
            "selected_owner_surface_or_blocker",
            "post_repair_ladder_skip_window",
        ],
    }


def _claim_contention_boundary_contract(*, first_drilldown: str) -> dict[str, Any]:
    read_only_route = first_drilldown or (
        "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 30 --cards-only"
    )
    return {
        "schema_version": "claim_contention_boundary_contract_v0",
        "classify_as": [
            "claim_contention",
            "heartbeat_gap_authority_boundary",
            "same_path_claim_frontier",
            "observed_path_overlap_boundary",
        ],
        "authority_rule": (
            "A heartbeat gap on another live session is a read-only ownership signal for this "
            "agent, not permission to heartbeat, finalize, release, or bypass that session's claims."
        ),
        "observed_path_overlap_boundary": {
            "schema_version": "observed_path_overlap_boundary_v0",
            "classify_as": [
                "telemetry_only",
                "watch_overlap",
                "blocking_owner_claim",
                "mutation_entanglement",
            ],
            "rule": (
                "session-preflight observed_path_overlaps are watch telemetry, not blockers, "
                "when exact claim cards and mutation-check are clear and observed rows have "
                "mutation_path_count=0 or referenced-path-only evidence. Treat them as blocking "
                "only when they resolve to an active owner claim, same-path mutation evidence, "
                "or an explicit preflight refusal."
            ),
        },
        "first_read_only_route": read_only_route,
        "owner_drilldown_route_template": (
            "./repo-python tools/meta/factory/work_ledger.py session-status "
            "--session-id <session_id> --full"
        ),
        "allowed_actions": [
            "classify_owner_state",
            "classify_observed_path_overlaps",
            "use_read_only_alternative_command",
            "choose_disjoint_write_lane",
            "rerun_preflight_bound_to_current_session",
            "record_blocked_reentry_condition",
        ],
        "blocked_actions": [
            "heartbeat_other_session",
            "finalize_other_session",
            "release_other_session_claims",
            "bypass_active_owner",
        ],
        "receipt_fields": [
            "claim_cards_command",
            "heartbeat_authority_boundary_classification",
            "selected_claim_session_id",
            "owner_read_only_drilldown",
            "session_bound_preflight_command",
            "observed_path_overlap_classification",
        ],
    }


def _experience_family_boundary_contracts(
    *,
    evidence: dict[str, Any],
    first_drilldown: str,
) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for family in _experience_family_ids(evidence):
        command = _experience_family_command(
            evidence=evidence,
            family=family,
            default_command=first_drilldown,
        )
        if family == "metadata_settlement_detour":
            contracts.append(_metadata_settlement_boundary_contract(first_drilldown=command))
        elif family == "closeout_authority_confusion":
            contracts.append(_closeout_authority_boundary_contract(first_drilldown=command))
        elif family in {"command_contract_mismatch", "task_ledger_payload_rejection"}:
            contracts.append(
                _command_contract_boundary_contract(
                    family=family,
                    first_drilldown=command,
                )
            )
        elif family == "compaction_recovery":
            contracts.append(_compaction_recovery_boundary_contract(first_drilldown=command))
        elif family == "scoped_commit_cas_retry_handoff":
            contracts.append(_scoped_commit_cas_retry_boundary_contract(first_drilldown=command))
    return contracts


def _experience_family_ids(evidence: dict[str, Any] | None) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    families: list[str] = []

    def add(raw: Any) -> None:
        family = str(raw or "").strip()
        if family and family not in families:
            families.append(family)

    add(evidence.get("episode_family"))
    top_families = evidence.get("top_families")
    if isinstance(top_families, list):
        for row in top_families:
            if isinstance(row, dict):
                add(row.get("family"))
    return families


def _experience_family_command(
    *,
    evidence: dict[str, Any],
    family: str,
    default_command: str,
) -> str:
    top_families = evidence.get("top_families") if isinstance(evidence, dict) else []
    if isinstance(top_families, list):
        for row in top_families:
            if not isinstance(row, dict):
                continue
            if str(row.get("family") or "").strip() != family:
                continue
            command = str(row.get("next_command") or "").strip()
            if command:
                return command
    info = _EXPERIENCE_FRICTION_FAMILY_INFO.get(family, {})
    command = str(info.get("next_command") or "").strip()
    return command or default_command


def _metadata_settlement_boundary_contract(*, first_drilldown: str) -> dict[str, Any]:
    route = first_drilldown or _EXPERIENCE_FRICTION_FAMILY_INFO["metadata_settlement_detour"][
        "next_command"
    ]
    return {
        "schema_version": "metadata_settlement_boundary_contract_v0",
        "classify_as": [
            "post_source_commit_metadata_settlement",
            "task_ledger_receipt_settlement",
            "projection_stale_until_rebuild",
            "same_authority_append_log_landing",
        ],
        "authority_rule": (
            "A scoped source commit can be landed while Task Ledger and Work Ledger settlement "
            "remain separate authority lanes; a clean authority visibility receipt is not the "
            "same state as refreshed projection/card visibility."
        ),
        "first_authority_route": route,
        "support_routes": {
            "task_ledger_health": "./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings",
            "organizer_report": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
            "execution_receipt_contract": "./repo-python tools/meta/factory/task_ledger_apply.py execution-receipt --help",
            "projection_rebuild_contract": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --help",
        },
        "allowed_actions": [
            "validate_payload_schema_before_append",
            "record_execution_receipt",
            "defer_projection_rebuild_with_authority_receipt",
            "record_blocked_metadata_reentry_condition",
        ],
        "blocked_actions": [
            "declare_done_from_source_commit_only",
            "treat_stale_projection_as_missing_authority",
            "retry_rejected_payload_by_guessing_flags",
            "hand_edit_task_ledger_projection",
        ],
        "receipt_fields": [
            "source_commit_hash_or_not_applicable",
            "task_ledger_visibility_receipt",
            "execution_receipt_event_id_or_blocker",
            "projection_rebuild_status",
            "validation_warning_baseline_classification",
            "metadata_reentry_condition",
        ],
    }


def _closeout_authority_boundary_contract(*, first_drilldown: str) -> dict[str, Any]:
    route = first_drilldown or _EXPERIENCE_FRICTION_FAMILY_INFO[
        "closeout_authority_confusion"
    ]["next_command"]
    return {
        "schema_version": "closeout_authority_boundary_contract_v0",
        "classify_as": [
            "source_landed_publication_pending",
            "publication_divergence_not_source_blocker",
            "metadata_settlement_pending",
            "work_ledger_closeout_pending",
        ],
        "authority_rule": (
            "Closeout is a composite decision over source, publication, metadata, claims, and "
            "ledger finalization. Do not let one axis silently satisfy or block the others."
        ),
        "first_authority_route": route,
        "state_axes": [
            "source_commit_state",
            "publication_state",
            "metadata_settlement_state",
            "active_claim_state",
            "work_ledger_closeout_state",
        ],
        "allowed_actions": [
            "separate_local_landing_from_publication",
            "run_closeout_conditions_snapshot",
            "record_metadata_or_work_ledger_blocker",
            "finalize_session_after_append_or_append_exempt_evidence",
        ],
        "blocked_actions": [
            "block_scoped_commit_only_because_origin_diverged",
            "declare_closeout_ready_from_local_commit_only",
            "treat_final_answer_as_metadata_settlement",
            "finalize_without_append_or_append_exempt_receipt",
        ],
        "receipt_fields": [
            "closeout_conditions_command",
            "source_commit_hash_or_pending_reason",
            "publication_status",
            "metadata_settlement_status",
            "active_claim_status",
            "work_ledger_finalize_receipt_or_reentry_condition",
        ],
    }


def _command_contract_boundary_contract(
    *,
    family: str,
    first_drilldown: str,
) -> dict[str, Any]:
    route = first_drilldown or _EXPERIENCE_FRICTION_FAMILY_INFO.get(family, {}).get(
        "next_command"
    ) or _EXPERIENCE_FRICTION_FAMILY_INFO["command_contract_mismatch"]["next_command"]
    return {
        "schema_version": "command_contract_boundary_contract_v0",
        "family": family,
        "classify_as": [
            "command_contract_mismatch",
            "owner_command_usage_error",
            "tool_namespace_mismatch",
            "edit_precondition_mismatch",
            "dry_run_or_help_route_gap",
        ],
        "authority_rule": (
            "A repeated command/tool/edit contract failure should be routed through the "
            "failing owner surface, command card, dry-run/validate lane, or tool-surface "
            "check before retrying or opening raw trace bodies."
        ),
        "first_authority_route": route,
        "support_routes": {
            "errors_lens": "./repo-python kernel.py --session-diagnostics --lens errors --last 20 --store both --json",
            "command_card_debug": "./repo-python kernel.py --command-card \"<failing command or tool contract>\" --debug",
            "owner_help_template": "./repo-python <owner-command> --help",
            "owner_validate_template": "./repo-python <owner-command> validate --help",
        },
        "allowed_actions": [
            "classify_specific_signature_before_owner_patch",
            "run_owner_help_or_validate_route",
            "open_command_card_after_entry_context_pack",
            "add_dry_run_or_accepted_value_contract",
            "record_blocked_owner_and_reentry_condition",
        ],
        "blocked_actions": [
            "retry_same_malformed_command_without_help_or_validate",
            "select_owner_surface_from_generic_exit_code_alone",
            "open_raw_trace_body_before_compact_signature_is_insufficient",
            "patch_runtime_tool_alias_without_current_tool_surface_check",
        ],
        "receipt_fields": [
            "experience_friction_lens_check",
            "command_contract_family",
            "specific_signature_or_probe",
            "owner_help_or_validate_route",
            "command_card_or_standard_patch",
            "post_repair_errors_or_experience_window",
        ],
    }


def _compaction_recovery_boundary_contract(*, first_drilldown: str) -> dict[str, Any]:
    route = first_drilldown or _EXPERIENCE_FRICTION_FAMILY_INFO["compaction_recovery"][
        "next_command"
    ]
    return {
        "schema_version": "compaction_recovery_boundary_contract_v0",
        "classify_as": [
            "context_resume_state_gap",
            "compact_continuation_packet_gap",
            "owner_claim_validation_residual_state_loss",
            "raw_body_reopen_after_compaction",
        ],
        "authority_rule": (
            "A compaction or resume event is not itself proof of lost work. Use compact "
            "continuation packets and owner/status routes to preserve or recover owner, "
            "claim/session, validation, residual, and re-entry state before reopening raw bodies."
        ),
        "first_authority_route": route,
        "support_routes": {
            "latency_lens": "./repo-python kernel.py --session-diagnostics --lens latency --last 10 --store codex --json",
            "work_ledger_seed_speed": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12",
            "task_ledger_organizer": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
            "git_closeout_conditions": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions",
        },
        "allowed_actions": [
            "resume_from_compact_owner_packet",
            "verify_claim_and_session_state",
            "verify_validation_and_commit_state",
            "record_residual_or_reentry_condition",
            "refresh_or_rebuild_compact_projection_when_owner_owned",
        ],
        "blocked_actions": [
            "reopen_raw_trace_body_before_compact_packet_is_insufficient",
            "declare_compaction_recovery_done_without_owner_claim_validation_state",
            "drop_residual_or_reentry_state_after_resume",
            "treat_context_compaction_as_new_task_scope",
        ],
        "receipt_fields": [
            "experience_friction_lens_check",
            "compaction_recovery_family",
            "continuation_packet_or_owner_status_route",
            "claim_session_validation_state",
            "residual_or_reentry_condition",
            "post_repair_compaction_window",
        ],
    }


def _scoped_commit_cas_retry_boundary_contract(*, first_drilldown: str) -> dict[str, Any]:
    route = first_drilldown or _EXPERIENCE_FRICTION_FAMILY_INFO[
        "scoped_commit_cas_retry_handoff"
    ]["next_command"]
    return {
        "schema_version": "scoped_commit_cas_retry_boundary_contract_v0",
        "classify_as": [
            "validated_slice_unlanded_after_head_churn",
            "private_index_cas_retry_exhausted",
            "landing_handoff_required",
            "ref_mutation_budget_boundary",
        ],
        "authority_rule": (
            "A scoped-commit CAS failure after HEAD advances is a landing-continuity problem, "
            "not proof that the source slice is invalid. After the governed retry budget is "
            "exhausted, stop mutating refs and publish a handoff with owned paths, validation, "
            "base/head observations, and the exact re-entry condition."
        ),
        "first_authority_route": route,
        "support_routes": {
            "work_ledger_seed_speed": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12",
            "scoped_commit_help": "./repo-python tools/meta/control/scoped_commit.py full-paths --help",
            "git_containment_snapshot": "./repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions",
            "landing_handoff_context_pack": (
                "./repo-python kernel.py --context-pack \"validated slice passed tests but "
                "scoped commit blocked after HEAD advanced and CAS retry budget exhausted "
                "exact owned paths uncommitted handoff landing continuity\" --context-budget 12000"
            ),
        },
        "allowed_actions": [
            "refresh_head_and_retry_once_when_budget_allows",
            "rerun_validation_after_head_refresh",
            "record_blocked_handoff_receipt_after_budget_exhaustion",
            "preserve_owned_paths_and_validation_evidence",
            "resume_from_seed_speed_or_landing_handoff",
        ],
        "blocked_actions": [
            "attempt_third_ref_mutation_after_retry_budget_exhausted",
            "drop_validated_owned_paths_from_handoff",
            "declare_source_slice_failed_from_cas_churn_alone",
            "broaden_commit_scope_to_escape_head_churn",
        ],
        "receipt_fields": [
            "experience_friction_lens_check",
            "scoped_commit_command_and_attempt_count",
            "base_head_and_observed_head_advances",
            "owned_pathspecs",
            "validation_commands_and_results",
            "blocked_handoff_receipt_or_landed_commit",
            "reentry_condition",
        ],
    }


def _context_pressure_cohort_omission_summary(
    *,
    evidence: dict[str, Any],
    top_compaction: dict[str, Any],
) -> dict[str, Any]:
    omitted = {
        "top_compaction_sessions_omitted": _coerce_count(
            evidence.get("top_compaction_sessions_omitted")
        ),
        "top_reads_omitted": _coerce_count(evidence.get("top_reads_omitted")),
        "rediscovery_omitted": _coerce_count(evidence.get("rediscovery_omitted")),
    }
    count_semantics = str(top_compaction.get("count_semantics") or "").strip() or None
    scan_truncated = top_compaction.get("scan_truncated")
    if scan_truncated is not None:
        scan_truncated = bool(scan_truncated)
    has_lower_bound_counts = count_semantics == "sample_lower_bound" or scan_truncated is True
    return {
        "schema_version": "context_pressure_cohort_omission_summary_v0",
        **omitted,
        "has_omitted_rows": any(count > 0 for count in omitted.values()),
        "top_compaction_count_semantics": count_semantics,
        "top_compaction_scan_truncated": scan_truncated,
        "has_lower_bound_counts": has_lower_bound_counts,
        "rule": (
            "Top context-pressure rows are a compact selector, not full cohort authority; "
            "positive omitted counts or sample-lower-bound scans require summary/full-window "
            "receipts before treating the visible top row as representative."
        ),
    }


def _context_pressure_runtime_support_routes(evidence: dict[str, Any]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for full_command in _context_pressure_runtime_commands(evidence, last=10):
        lens = _diagnostics_command_lens(full_command)
        store = _diagnostics_command_store(full_command)
        if not lens or not store:
            continue
        summary_command, full_drilldown_command = _summary_first_diagnostics_drilldown(full_command)
        routes.append(
            {
                "lens": lens,
                "store": store,
                "summary_command": summary_command,
                "full_drilldown_command": full_drilldown_command or full_command,
            }
        )
    return routes


def _trace_cap_ref_kinds(
    *,
    symptom_family: str,
    cap_refs: list[str],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {
        "work_item_refs": [],
        "artifact_refs": [],
        "other_refs": [],
    }
    for raw_ref in cap_refs:
        ref = str(raw_ref or "").strip()
        if not ref:
            continue
        if _is_trace_work_item_ref(symptom_family=symptom_family, ref=ref):
            grouped["work_item_refs"].append(ref)
        elif _is_trace_artifact_ref(ref):
            grouped["artifact_refs"].append(ref)
        else:
            grouped["other_refs"].append(ref)
    return {key: value for key, value in grouped.items() if value}


def _is_trace_work_item_ref(*, symptom_family: str, ref: str) -> bool:
    if symptom_family in {"task_ledger_cap_pressure", "cap_pressure"}:
        return True
    return ref.startswith(("cap_", "td_"))


def _is_trace_artifact_ref(ref: str) -> bool:
    return (
        ref in {"progress_pressure_ledger_v0"}
        or ref.endswith("_ledger_v0")
        or ref.endswith("_surface_v0")
    )


def _trace_cap_policy(cap_ref_kinds: dict[str, list[str]]) -> str:
    if cap_ref_kinds.get("work_item_refs"):
        if cap_ref_kinds.get("artifact_refs"):
            return (
                "Open and shape/link the existing CAP or WorkItem refs before creating "
                "parallel backlog; treat artifact refs as evidence handles, not backlog rows."
            )
        return "Open and shape/link the existing CAP or WorkItem before creating any parallel backlog."
    if cap_ref_kinds.get("artifact_refs"):
        return (
            "Treat cap_refs as existing artifact/evidence handles, not WorkItem backlog rows; "
            "inspect or reuse the named artifact or owner surface before creating parallel backlog."
        )
    if cap_ref_kinds.get("other_refs"):
        return (
            "Classify cap_refs before acting: shape/link WorkItem refs, inspect artifact refs, "
            "and create new backlog only after the owner lane is unsafe or blocked."
        )
    return "Create a new CAP only when the owner patch is unsafe, blocked, or outside current authority."


def _add_trace_improvement_row(
    rows: list[dict[str, Any]],
    *,
    priority: int,
    symptom_family: str,
    title: str,
    evidence: dict[str, Any],
    owner_surface: str,
    next_command: str,
    candidate_patch: str,
    source_lenses: list[str],
    cap_refs: list[str] | None = None,
) -> None:
    compact_cap_refs = cap_refs or []
    action_contract = _trace_summary_action_contract(
        symptom_family=symptom_family,
        owner_surface=owner_surface,
        next_command=next_command,
        evidence=evidence,
        source_lenses=source_lenses,
        cap_refs=compact_cap_refs,
    )
    row_next_command = str(action_contract.get("first_drilldown") or next_command)
    row = {
        "row_id": f"{symptom_family}:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:10]}",
        "priority": priority,
        "severity": "high" if priority >= 85 else "medium" if priority >= 70 else "low",
        "symptom_family": symptom_family,
        "title": title,
        "evidence": evidence,
        "owner_surface": owner_surface,
        "next_command": row_next_command,
        "candidate_patch": candidate_patch,
        "source_lenses": source_lenses,
        "cap_refs": compact_cap_refs,
        "action_contract": action_contract,
    }
    if "full_drilldown" in action_contract:
        row["summary_first_command"] = action_contract["first_drilldown"]
        row["full_drilldown_command"] = action_contract["full_drilldown"]
    rows.append(row)


def _compact_trace_summary_action_contract_for_summary(
    contract: dict[str, Any],
) -> dict[str, Any]:
    compact = {
        key: contract.get(key)
        for key in (
            "schema_version",
            "mode",
            "owner_type",
            "first_drilldown",
            "receipt_needed",
            "full_drilldown",
            "summary_first_reason",
            "disconfirming_check",
            "cap_policy",
            "cap_ref_kinds",
            "runtime_support_routes",
            "runtime_support_policy",
        )
        if contract.get(key) not in (None, "", [], {})
    }
    for key in TRACE_SUMMARY_COMPACT_PRESERVED_CONTRACT_KEYS:
        value = contract.get(key)
        if value not in (None, "", [], {}):
            compact[key] = _compact_nested_trace_contract_for_summary(value)
    supporting = contract.get("supporting_drilldowns")
    if isinstance(supporting, list):
        preview_rows = _supporting_drilldown_preview_for_summary(supporting)
        compact["supporting_drilldowns"] = [
            {
                key: row.get(key)
                for key in ("lens", "command", "role", "full_fallback_command")
                if isinstance(row, dict) and row.get(key) not in (None, "", [], {})
            }
            for row in preview_rows
            if isinstance(row, dict)
        ]
        compact["supporting_drilldown_count"] = len(supporting)
        omitted = max(0, len(supporting) - len(compact["supporting_drilldowns"]))
        if omitted:
            compact["supporting_drilldowns_omitted"] = omitted
            compact["supporting_drilldown_omission_receipt"] = {
                "reason": (
                    "diagnostics-summary keeps only the first supporting drilldown; "
                    "use full diagnostics JSON for the complete supporting route list"
                ),
                "full_drilldown": compact.get("full_drilldown"),
            }
    return compact


def _supporting_drilldown_preview_for_summary(rows: list[Any]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()

    def add(index: int, row: Any) -> None:
        if len(preview) >= TRACE_SUMMARY_SUPPORTING_DRILLDOWN_PREVIEW_LIMIT:
            return
        if index in seen_indexes or not isinstance(row, dict):
            return
        preview.append(row)
        seen_indexes.add(index)

    if rows:
        add(0, rows[0])
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if row.get("lens") == "experience_family:command_contract_mismatch":
            add(index, row)
            break
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if row.get("role") == "supporting_episode_family_drilldown":
            add(index, row)
            break
    for index, row in enumerate(rows):
        add(index, row)
    return preview


_TRACE_SUMMARY_COMPACT_NESTED_KEYS = {
    "schema_version",
    "status",
    "shape",
    "dominant_signal",
    "top_verb",
    "top_count",
    "grep_before_nav",
    "runtime_focus",
    "max_compactions",
    "reread_pressure_count",
    "top_reread_hotspot_path",
    "top_compaction_session_id",
    "process_summary_lookup",
    "first_summary_route",
    "full_drilldown_route",
    "first_authority_route",
    "first_read_only_route",
    "first_lens_route",
    "evidence_drilldown",
    "replacement_route",
    "command_card_debug_route",
    "claim_cards_route",
    "hotspot_claim_check_route",
    "process_summary_route",
    "owner_slug",
    "card_command",
    "source_command",
    "projection_check_command",
    "write_profile",
    "specific_family_count",
    "selection_rule",
    "unresolved_count_known",
    "unresolved_count",
    "candidate_count",
    "route_miss_probe_status",
    "docs_route_patch_allowed",
    "patch_docs_route_when",
    "tool_namespace_contract",
    "tool_surface_check",
    "owner_rule",
    "fallback_rule",
    "runtime_support_routes",
    "runtime_support_policy",
}


def _compact_nested_trace_contract_for_summary(value: Any) -> Any:
    if isinstance(value, list):
        return [
            _compact_nested_trace_contract_for_summary(item)
            for item in value
            if isinstance(item, (dict, list))
        ]
    if not isinstance(value, dict):
        return value

    compact = {
        key: value.get(key)
        for key in _TRACE_SUMMARY_COMPACT_NESTED_KEYS
        if value.get(key) not in (None, "", [], {})
    }
    schema_version = str(compact.get("schema_version") or "")
    preserve_action_lists = schema_version.startswith(("ladder_skip_", "tool_namespace_"))
    classify_as = value.get("classify_as")
    if isinstance(classify_as, list):
        compact["classify_as"] = list(classify_as)
    receipt_fields = value.get("receipt_fields")
    if isinstance(receipt_fields, list):
        if preserve_action_lists:
            compact["receipt_fields"] = list(receipt_fields)
        else:
            compact["receipt_fields_count"] = len(receipt_fields)
    for count_key in ("allowed_actions", "blocked_actions", "required_fields", "status_values"):
        rows = value.get(count_key)
        if isinstance(rows, list):
            if preserve_action_lists:
                compact[count_key] = list(rows)
            else:
                compact[f"{count_key}_count"] = len(rows)
    for route_key in ("support_routes", "replacement_order", "top_error_families", "cohort_omission_summary"):
        rows = value.get(route_key)
        if isinstance(rows, dict):
            compact[f"{route_key}_keys"] = sorted(str(key) for key in rows.keys())
        elif isinstance(rows, list):
            if route_key == "replacement_order" and preserve_action_lists:
                compact[route_key] = [
                    {
                        key: row.get(key)
                        for key in ("step", "route", "use_when")
                        if isinstance(row, dict) and row.get(key) not in (None, "", [], {})
                    }
                    for row in rows
                    if isinstance(row, dict)
                ]
            else:
                compact[f"{route_key}_count"] = len(rows)
    return compact


def _compact_trace_improvement_surface_for_summary(
    surface: dict[str, Any],
    *,
    full_action_contract_row_count: int = 1,
) -> dict[str, Any]:
    rows = [row for row in surface.get("rows") or [] if isinstance(row, dict)]
    if not rows:
        return surface

    compact_rows: list[dict[str, Any]] = []
    compacted_count = 0
    for index, row in enumerate(rows):
        compact_row = _compact_trace_improvement_row_for_summary(row)
        contract = row.get("action_contract")
        if index >= full_action_contract_row_count and isinstance(contract, dict):
            compact_row["action_contract"] = _compact_trace_summary_action_contract_for_summary(
                contract
            )
            compact_row["action_contract_omission_receipt"] = {
                "drilldown": row.get("next_command") or contract.get("first_drilldown"),
                "reason": "non_top_contract_compacted_for_summary_output",
            }
            compacted_count += 1
        compact_rows.append(compact_row)

    compact_surface = dict(surface)
    compact_surface["rows"] = compact_rows
    summary = (
        dict(compact_surface.get("summary"))
        if isinstance(compact_surface.get("summary"), dict)
        else {}
    )
    summary["full_action_contract_row_count"] = min(
        full_action_contract_row_count,
        len(rows),
    )
    summary["compacted_action_contract_row_count"] = compacted_count
    compact_surface["summary"] = summary
    return compact_surface


def _compact_trace_improvement_row_for_summary(row: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: row.get(key)
        for key in (
            "row_id",
            "priority",
            "severity",
            "symptom_family",
            "title",
            "owner_surface",
            "next_command",
            "candidate_patch",
            "source_lenses",
            "cap_refs",
            "summary_first_command",
            "full_drilldown_command",
        )
        if row.get(key) not in (None, "", [], {})
    }
    evidence = row.get("evidence")
    if isinstance(evidence, dict):
        compact["evidence"] = _compact_trace_improvement_evidence_for_summary(
            str(row.get("symptom_family") or ""),
            evidence,
        )
    if isinstance(row.get("action_contract"), dict):
        compact["action_contract"] = row["action_contract"]
    return compact


def _compact_trace_improvement_evidence_for_summary(
    symptom_family: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if symptom_family == "context_pressure":
        top_compaction = (
            evidence.get("top_compaction_session")
            if isinstance(evidence.get("top_compaction_session"), dict)
            else {}
        )
        top_hotspot = (
            evidence.get("top_reread_hotspot")
            if isinstance(evidence.get("top_reread_hotspot"), dict)
            else {}
        )
        return {
            "max_compactions": evidence.get("max_compactions"),
            "reread_file_count": evidence.get("reread_file_count"),
            "reread_pressure_count": evidence.get("reread_pressure_count"),
            "top_compaction_sessions_omitted": evidence.get("top_compaction_sessions_omitted"),
            "top_reads_omitted": evidence.get("top_reads_omitted"),
            "rediscovery_omitted": evidence.get("rediscovery_omitted"),
            "runtime_focus": evidence.get("runtime_focus"),
            "top_compaction_session": {
                key: top_compaction.get(key)
                for key in (
                    "path",
                    "compactions",
                    "turns",
                    "scan_mode",
                    "scan_truncated",
                    "count_semantics",
                    "session_id",
                    "session_id_source",
                    "process_summary_lookup",
                    "process_summary_resolvable",
                    "process_summary_session_id",
                )
                if top_compaction.get(key) not in (None, "", [], {})
            },
            "top_reread_hotspot": {
                key: top_hotspot.get(key)
                for key in ("path", "reads", "distinct_sessions", "score")
                if top_hotspot.get(key) not in (None, "", [], {})
            },
        }
    if symptom_family == "experience_friction":
        top_families = evidence.get("top_families")
        family_rows = top_families if isinstance(top_families, list) else []
        return {
            "episode_family": evidence.get("episode_family"),
            "event_count": evidence.get("event_count"),
            "family_count": evidence.get("family_count"),
            "top_families": [
                {
                    key: row.get(key)
                    for key in ("family", "count", "distinct_sessions", "next_command", "priority")
                    if isinstance(row, dict) and row.get(key) not in (None, "", [], {})
                }
                for row in family_rows[:3]
                if isinstance(row, dict)
            ],
            "top_families_omitted": max(0, len(family_rows) - 3),
        }
    if symptom_family == "ladder_skip":
        return {
            key: evidence.get(key)
            for key in (
                "ratio_bad_to_good_bash",
                "grep_calls_before_any_nav_flag",
                "bash_should_be_native_top",
                "kernel_nav_flag_calls",
                "dominant_shell_shape",
                "runtime_focus",
            )
            if evidence.get(key) not in (None, "", [], {})
        }
    return {
        key: evidence.get(key)
        for key in (
            "active_agents",
            "progress_units",
            "pressure_index",
            "progress_per_pressure",
            "bottleneck_class",
            "governor_decision",
            "confidence",
            "route_miss_candidates",
            "route_miss_unresolved",
            "route_miss_unresolved_known",
            "route_miss_probe_status",
            "recovery_events",
            "top_command_usage_families",
            "top_cap_rows",
            "runtime_focus",
            "owner_paper_module_slug",
            "owner_route_id",
            "owner_component_id",
        )
        if evidence.get(key) not in (None, "", [], {})
    }


def _trace_summary_store_hint(evidence: dict[str, Any]) -> str:
    runtime_focus = str(evidence.get("runtime_focus") or "").strip().lower()
    if runtime_focus in {"codex", "claude", "both"}:
        return runtime_focus
    return "both"


def _trace_summary_supporting_drilldowns(
    *,
    first_command: str,
    evidence: dict[str, Any],
    source_lenses: list[str],
) -> list[dict[str, str]]:
    store = _trace_summary_store_hint(evidence)
    lens_last = {
        "latency": 10,
        "hotspots": 10,
        "ladder-skip": 10,
        "histogram": 10,
        "prompts": 20,
        "wake-prompts": 20,
        "route-misses": 20,
        "errors": 20,
        "experience-frictions": 20,
    }
    special_commands = {
        "host_pressure_surface": HOST_PRESSURE_SUMMARY_FIRST_COMMAND,
        "task_ledger_views": first_command,
    }
    rows: list[dict[str, str]] = []
    seen_commands: set[str] = set()

    context_pressure_routes_by_lens: dict[str, tuple[str, str | None]] = {}
    if any(
        key in evidence
        for key in (
            "max_compactions",
            "reread_pressure_count",
            "top_compaction_session",
            "top_reread_hotspot",
        )
    ):
        for full_command in _context_pressure_runtime_commands(evidence, last=10):
            lens = _diagnostics_command_lens(full_command)
            if not lens or lens in context_pressure_routes_by_lens:
                continue
            context_pressure_routes_by_lens[lens] = _summary_first_diagnostics_drilldown(
                full_command
            )

    def commands_for_lens(lens: str) -> tuple[str | None, str | None]:
        if lens in special_commands:
            return special_commands[lens], None
        if lens in context_pressure_routes_by_lens:
            return context_pressure_routes_by_lens[lens]
        if lens in lens_last:
            full_command = _session_diagnostics_command(lens, last=lens_last[lens], store=store)
            return _summary_first_diagnostics_drilldown(full_command)
        return None, None

    def add_row(
        lens: str,
        command: str,
        role: str,
        *,
        full_fallback_command: str | None = None,
    ) -> None:
        if not command or command in seen_commands:
            return
        seen_commands.add(command)
        row = {
            "lens": lens,
            "command": command,
            "role": role,
        }
        if full_fallback_command and full_fallback_command != command:
            row["full_fallback_command"] = full_fallback_command
        rows.append(row)

    first_lens = "primary"
    first_lens_full_fallback = _full_fallback_diagnostics_command(first_command)
    for lens in source_lenses:
        command, full_fallback = commands_for_lens(lens)
        if command == first_command or f"--lens {lens}" in first_command:
            first_lens = lens
            if not first_lens_full_fallback:
                first_lens_full_fallback = full_fallback
            break
    add_row(
        first_lens,
        first_command,
        "first_drilldown",
        full_fallback_command=first_lens_full_fallback,
    )
    for lens in source_lenses:
        command, full_fallback = commands_for_lens(lens)
        if command is None:
            continue
        add_row(
            lens,
            command,
            "supporting_lens_drilldown",
            full_fallback_command=full_fallback,
        )
    if evidence.get("owner_paper_module_slug"):
        paper_module_source_command = str(evidence.get("paper_module_source_command") or "").strip()
        paper_module_index_check_command = str(evidence.get("paper_module_index_check_command") or "").strip()
        supporting_paper_module_card_command = str(
            evidence.get("supporting_paper_module_card_command") or ""
        ).strip()
        if paper_module_source_command:
            add_row(
                "paper_module_source",
                paper_module_source_command,
                "compression_authoring_drilldown",
            )
        if supporting_paper_module_card_command:
            add_row(
                "supporting_paper_module_cards",
                supporting_paper_module_card_command,
                "owner_context_drilldown",
            )
        if paper_module_index_check_command:
            add_row(
                "paper_module_index",
                paper_module_index_check_command,
                "projection_refresh_or_blocked_check",
            )
    top_hotspot = evidence.get("top_reread_hotspot") if isinstance(evidence, dict) else {}
    if isinstance(top_hotspot, dict) and top_hotspot.get("path"):
        hotspot_claim_check_command = _work_ledger_path_mutation_check_command(
            str(top_hotspot.get("path") or "")
        )
        if hotspot_claim_check_command:
            add_row(
                "work_ledger_hotspot_claim_check",
                hotspot_claim_check_command,
                "hotspot_owner_exact_claim_check",
            )
        add_row(
            "work_ledger_claim_cards",
            WORK_LEDGER_CLAIM_CARDS_COMMAND,
            "hotspot_owner_claim_drilldown",
        )
    if _is_claim_contention_experience(evidence):
        add_row(
            "work_ledger_seed_speed",
            WORK_LEDGER_SEED_SPEED_COMMAND,
            "live_claim_cohort_drilldown",
        )
    for family_row in evidence.get("top_command_usage_families") or []:
        if not isinstance(family_row, dict):
            continue
        help_route = str(family_row.get("help_route") or "").strip()
        if not help_route:
            continue
        family = str(family_row.get("family") or "command_usage").strip()
        add_row(
            f"command_usage:{family}",
            help_route,
            "owner_help_route",
        )
    for family_row in _secondary_experience_family_drilldown_rows(evidence):
        command, full_fallback = _summary_first_diagnostics_drilldown(family_row["next_command"])
        add_row(
            f"experience_family:{family_row['family']}",
            command,
            "supporting_episode_family_drilldown",
            full_fallback_command=full_fallback,
        )
    return rows


def _is_claim_contention_experience(evidence: dict[str, Any]) -> bool:
    if not isinstance(evidence, dict):
        return False
    episode_family = str(evidence.get("episode_family") or "").lower()
    return any(term in episode_family for term in ("claim", "collision", "contention"))


def _compact_experience_family_action_row(row: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "family": row.get("family"),
        "count": row.get("count"),
        "distinct_sessions": row.get("distinct_sessions"),
    }
    for field in ("owner_surface", "next_command", "candidate_patch", "priority"):
        value = row.get(field)
        if value not in (None, "", []):
            compact[field] = value
    return compact


def _secondary_experience_family_drilldown_rows(evidence: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(evidence, dict):
        return []
    top_families = evidence.get("top_families")
    if not isinstance(top_families, list) or len(top_families) < 2:
        return []
    rows: list[dict[str, str]] = []
    for row in top_families[1:]:
        if not isinstance(row, dict):
            continue
        family = str(row.get("family") or "").strip()
        command = str(row.get("next_command") or "").strip()
        if not family or not command:
            continue
        rows.append({"family": family, "next_command": command})
    return rows


def _has_secondary_experience_family_drilldown(evidence: dict[str, Any]) -> bool:
    return bool(_secondary_experience_family_drilldown_rows(evidence))


def _context_pressure_store_hint(max_compactions: int, reread_file_count: int) -> str:
    if max_compactions >= 2 and reread_file_count == 0:
        return "codex"
    if reread_file_count >= 5 and max_compactions < 2:
        return "claude"
    return "both"


def _context_pressure_prefers_reread_drilldown(
    max_compactions: int,
    reread_pressure_count: int,
) -> bool:
    if reread_pressure_count < 10:
        return False
    return reread_pressure_count >= max(10, max_compactions * 2)


def _session_diagnostics_command(
    lens: str,
    *,
    last: int,
    store: str,
    diagnostics_summary: bool = False,
) -> str:
    command = (
        f"./repo-python kernel.py --session-diagnostics --lens {lens} "
        f"--last {last} --store {store} --json"
    )
    if diagnostics_summary:
        command += " --diagnostics-summary"
    return command


def _summary_first_diagnostics_command(command: str) -> str:
    text = str(command or "").strip()
    if not text or "--session-diagnostics" not in text:
        return text
    if "--diagnostics-summary" in text:
        return text
    if "--json" not in text:
        text += " --json"
    return f"{text} --diagnostics-summary"


def _summary_first_diagnostics_drilldown(command: str) -> tuple[str, str | None]:
    summary_command = _summary_first_diagnostics_command(command)
    full_fallback = _full_fallback_diagnostics_command(summary_command)
    if full_fallback == summary_command:
        full_fallback = None
    return summary_command, full_fallback


def _full_fallback_diagnostics_command(command: str) -> str | None:
    parts = str(command or "").strip().split()
    if "--session-diagnostics" not in parts or "--diagnostics-summary" not in parts:
        return None
    return " ".join(part for part in parts if part != "--diagnostics-summary")


def _diagnostics_command_store(command: str) -> str | None:
    parts = str(command or "").split()
    try:
        store_idx = parts.index("--store")
    except ValueError:
        return None
    if store_idx + 1 >= len(parts):
        return None
    store = parts[store_idx + 1].strip().lower()
    if store in {"codex", "claude"}:
        return store
    return None


def _diagnostics_command_lens(command: str) -> str | None:
    parts = str(command or "").split()
    try:
        lens_idx = parts.index("--lens")
    except ValueError:
        return None
    if lens_idx + 1 >= len(parts):
        return None
    lens = parts[lens_idx + 1].strip()
    return lens or None


def _codex_session_id_from_rollout_path(path_token: Any) -> str | None:
    path_text = str(path_token or "").strip()
    if not path_text:
        return None
    filename = Path(path_text).name
    stem = filename[:-6] if filename.endswith(".jsonl") else filename
    match = re.match(
        r"^rollout-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-[0-9a-fA-F-]+)$",
        stem,
    )
    if not match:
        return None
    return match.group(1)


def _context_pressure_process_summary_command(
    evidence: dict[str, Any],
    *,
    force: bool = True,
) -> str | None:
    runtime_focus = str(evidence.get("runtime_focus") or "").strip().lower()
    if runtime_focus not in {"codex", "both"}:
        return None
    top_compaction = (
        evidence.get("top_compaction_session")
        if isinstance(evidence.get("top_compaction_session"), dict)
        else {}
    )
    session_id = top_compaction.get("process_summary_session_id")
    if not session_id and top_compaction.get("process_summary_resolvable") is True:
        session_id = top_compaction.get("session_id") or _codex_session_id_from_rollout_path(
            top_compaction.get("path")
        )
    if not session_id:
        return None
    command = f"./repo-python kernel.py --process-summary {session_id}"
    if force:
        command += " --force"
    command += f" --limit {PROCESS_SUMMARY_EXPLICIT_SESSION_LOOKUP_LIMIT}"
    return command


def _already_loaded_summary_next(
    *,
    selected_lens: str,
    full_lens_fallback_command: str,
    trace_improvement_surface: dict[str, Any],
) -> dict[str, str] | None:
    """Return the cheap owner/action hop after the compact lens is loaded.

    The full selected-lens JSON remains available as fallback metadata, but it
    should not be the default `next` command once the compact receipt has
    already established the row and sufficiency state.
    """
    rows = trace_improvement_surface.get("rows")
    top_row = rows[0] if isinstance(rows, list) and rows else {}
    if not isinstance(top_row, dict):
        top_row = {}
    evidence = top_row.get("evidence") if isinstance(top_row.get("evidence"), dict) else {}
    symptom_family = str(top_row.get("symptom_family") or "")
    if selected_lens in {"latency", "hotspots"} and symptom_family == "context_pressure":
        top_hotspot = (
            evidence.get("top_reread_hotspot")
            if isinstance(evidence.get("top_reread_hotspot"), dict)
            else {}
        )
        if top_hotspot.get("path"):
            return {
                "command": WORK_LEDGER_CLAIM_CARDS_COMMAND,
                "reason": (
                    "Selected diagnostics summary is already loaded; check compact claim cards "
                    "for the reread hotspot owner before opening the hot file or full diagnostics JSON."
                ),
            }
        runtime_scope = evidence.get("runtime_focus") or _diagnostics_command_store(full_lens_fallback_command)
        process_summary_command = _context_pressure_process_summary_command(evidence)
        if process_summary_command:
            return {
                "command": process_summary_command,
                "reason": (
                    "Selected diagnostics summary is already loaded; use the verified explicit "
                    "process-summary session before escalating to full diagnostics JSON."
                ),
            }
        process_summary_command = f"{_process_summary_cached_command(str(runtime_scope or 'both'))} --force"
        return {
            "command": process_summary_command,
            "reason": (
                "Selected diagnostics summary is already loaded; use the runtime-scoped "
                "process-summary alias before escalating to full diagnostics JSON. Rollout-derived "
                "session ids are evidence only unless the row marks them process-summary resolvable."
            ),
        }
    action_contract = (
        top_row.get("action_contract")
        if isinstance(top_row.get("action_contract"), dict)
        else {}
    )
    owner_command = str(action_contract.get("first_drilldown") or top_row.get("next_command") or "").strip()
    redundant_commands = {
        str(full_lens_fallback_command or "").strip(),
        str(_summary_first_diagnostics_command(full_lens_fallback_command) or "").strip(),
    }
    if owner_command and owner_command not in redundant_commands:
        title = str(top_row.get("title") or symptom_family or "top trace-improvement row").strip()
        return {
            "command": owner_command,
            "reason": (
                "Selected diagnostics summary is already loaded; follow the top trace-improvement "
                f"owner drilldown for {title} instead of reopening full diagnostics JSON."
            ),
        }
    return None


def _process_summary_runtime_stores(runtime_scope: str | None) -> list[str]:
    scope = str(runtime_scope or "both").strip().lower()
    if scope in {"codex", "claude"}:
        return [scope]
    return ["codex", "claude"]


def _process_summary_cached_command(runtime_scope: str | None) -> str:
    scope = str(runtime_scope or "both").strip().lower()
    if scope in {"codex", "claude"}:
        return f"./repo-python kernel.py --process-summary {scope}:latest"
    return "./repo-python kernel.py --process-summary latest"


def _process_summary_force_commands(runtime_scope: str | None) -> list[str]:
    return [
        f"./repo-python kernel.py --process-summary {store}:latest --force"
        for store in _process_summary_runtime_stores(runtime_scope)
    ]


def _primary_process_summary_force_command(runtime_scope: str | None) -> str:
    return _process_summary_force_commands(runtime_scope)[0]


def _is_bare_process_summary_latest_command(command: Any) -> bool:
    text = str(command or "")
    return "--process-summary latest" in text


def _live_trace_readiness_contract(runtime_scope: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "live_trace_readiness_contract_v0",
        "cached_probe": _process_summary_cached_command(runtime_scope),
        "force_live_commands": _process_summary_force_commands(runtime_scope),
        "refresh_command": "./repo-python tools/meta/factory/build_agent_execution_trace.py",
        "unready_statuses": [
            "not_loaded",
            "missing_or_malformed_summary",
            "stale",
            "advisory_only_stale_read_model",
        ],
        "required_receipts": [
            "source_freshness.status",
            "source_freshness.ok",
            "identity_scope",
            "selected_session_id_or_agent",
            "force_live_or_refresh_command",
        ],
        "rules": [
            "Treat the cached process-summary command as a readiness probe, not proof that no live trace pressure exists.",
            "If source_freshness.ok is false or projections are missing, run a runtime-scoped force-live command or refresh the projection before selecting a live source-patch target.",
            "During sibling-seed work, prefer codex:latest or claude:latest force-live commands over bare latest when identity matters.",
            "If host pressure or authority blocks a live rebuild, record blocked or not_run and use finished trace-summary rows only within their stated window.",
        ],
    }


def _process_summary_hint_needs_runtime_scope(preferred_next: Any) -> bool:
    text = str(preferred_next or "")
    return "<session_id|" in text or "--process-summary <" in text


def _context_pressure_runtime_commands(evidence: dict[str, Any], *, last: int = 10) -> list[str]:
    focus = str(evidence.get("runtime_focus") or "both").lower()
    max_compactions = _coerce_count(evidence.get("max_compactions"))
    reread_pressure_count = _context_reread_pressure_count(evidence)
    commands: list[str] = []
    prefer_reread = _context_pressure_prefers_reread_drilldown(
        max_compactions,
        reread_pressure_count,
    )
    if prefer_reread and focus in {"claude", "both"}:
        commands.append(_session_diagnostics_command("hotspots", last=last * 2, store="claude"))
    if focus in {"codex", "both"} and max_compactions >= 2:
        commands.append(_session_diagnostics_command("latency", last=last, store="codex"))
    if not prefer_reread and focus in {"claude", "both"} and reread_pressure_count >= 5:
        commands.append(_session_diagnostics_command("hotspots", last=last * 2, store="claude"))
    if not commands:
        commands.append(_session_diagnostics_command("latency", last=last, store=focus if focus in {"codex", "claude"} else "both"))
    return commands


def _frontend_component_id_from_path(path: str) -> str | None:
    if not path.startswith("system/server/ui/src/") or not path.endswith((".tsx", ".ts")):
        return None
    stem = Path(path).stem
    if not stem or stem in {"index", "types"}:
        return None
    return f"{path}::{stem}"


def _rediscovery_hotspot_repair(path: str) -> dict[str, str]:
    if path.startswith("microcosm-substrate/"):
        return {
            "owner_surface": "public Microcosm docs route",
            "next_command": './repo-python kernel.py --docs-route "public microcosm"',
            "candidate_patch": (
                "Use the public Microcosm route and std_microcosm card, then inspect the named "
                "organ/source path for runnable substrate, schema-only fixture, stale macro pointer, "
                "or delete/demote cleanup."
            ),
            "owner_route_id": "sit_public_microcosm_evolution",
        }
    if path.startswith("tools/agent_trace_structurer/"):
        return {
            "owner_surface": "agent_trace_structurer_surface paper-module card",
            "next_command": (
                "./repo-python kernel.py --option-surface paper_modules "
                "--band card --ids agent_trace_structurer_surface"
            ),
            "candidate_patch": (
                "Use the Agent Trace Structurer paper-module card, README, and focused contract "
                "tests before reopening the large app source body; open app.mjs only after the "
                "card cannot answer the owner question. If the card reports fallback compression, "
                "author the paper-module compression fields and refresh or explicitly block the "
                "paper_module_index projection before treating the source reread as necessary."
            ),
            "owner_paper_module_slug": "agent_trace_structurer_surface",
            "paper_module_source_command": (
                "./repo-python kernel.py --paper-module agent_trace_structurer_surface"
            ),
            "paper_module_index_check_command": (
                "./repo-python tools/meta/factory/build_paper_module_index.py --check"
            ),
            "paper_module_write_profile": "paper_module_index",
        }
    if path == "tools/meta/dissemination/build_microcosm_public_site.py":
        return {
            "owner_surface": "tools_meta_dissemination_index paper-module card",
            "next_command": (
                "./repo-python kernel.py --option-surface paper_modules "
                "--band card --ids tools_meta_dissemination_index"
            ),
            "candidate_patch": (
                "Use the dissemination index card, then the Microcosm public export and graph-scene "
                "cards plus the focused --check --validate command before reopening the public-site "
                "builder source; open build_microcosm_public_site.py only for exact renderer/helper "
                "behavior or a failing focused regression."
            ),
            "owner_paper_module_slug": "tools_meta_dissemination_index",
            "paper_module_source_command": (
                "./repo-python kernel.py --paper-module tools_meta_dissemination_index"
            ),
            "supporting_paper_module_card_command": (
                "./repo-python kernel.py --option-surface paper_modules "
                "--band card --ids microcosm_public_export_type_plane,graph_scene_core"
            ),
            "paper_module_index_check_command": (
                "./repo-python tools/meta/factory/build_paper_module_index.py --check"
            ),
            "paper_module_write_profile": "paper_module_index",
        }
    component_id = _frontend_component_id_from_path(path)
    if component_id:
        return {
            "owner_surface": "frontend_components option surface card",
            "next_command": (
                "./repo-python kernel.py --option-surface frontend_components "
                f"--band card --ids {component_id}"
            ),
            "candidate_patch": (
                "Use the frontend_components card first for source span, currentness, and omission receipts; "
                "open the TSX body only after the component card proves the needed owner detail is absent."
            ),
            "owner_component_id": component_id,
        }
    return {
        "owner_surface": "paper module, option-surface card, or command-card for the hot path",
        "next_command": _session_diagnostics_command("hotspots", last=20, store="claude"),
        "candidate_patch": (
            "If the hot file is source authority, add or tighten a card/TLDR route; if it is an output "
            "artifact, replace rereads with a structured status packet."
        ),
    }


def _rediscovery_hotspot_priority(
    hotspot: dict[str, Any],
    repair: dict[str, str],
    *,
    max_compactions: int,
) -> int:
    score = _coerce_count(hotspot.get("score"))
    has_typed_owner = any(
        repair.get(key)
        for key in (
            "owner_paper_module_slug",
            "owner_component_id",
            "owner_route_id",
        )
    )
    if max_compactions <= 0 and has_typed_owner and score >= 100:
        return 82
    if has_typed_owner and score >= 50:
        return 77
    return 76


def _compact_cap_rows(rows: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        compact.append({
            "id": row.get("id"),
            "title": row.get("title"),
            "state": row.get("state"),
            "views": row.get("views", []),
            "score": row.get("score"),
        })
    return compact


def build_trace_improvement_surface(
    *,
    metrics: dict[str, Any],
    report: dict[str, Any],
    limit: int = 8,
) -> dict[str, Any]:
    """Synthesize lens fragments into owner-action candidates.

    The raw lenses are useful but scattered. This packet is the compact
    "what should we improve from these traces?" layer: ranked symptoms,
    owner routes, and optional Task Ledger CAP alignment.
    """
    rows: list[dict[str, Any]] = []
    context = metrics.get("context_pressure") if isinstance(metrics.get("context_pressure"), dict) else {}
    ladder = metrics.get("ladder_skip") if isinstance(metrics.get("ladder_skip"), dict) else {}
    discoverability = metrics.get("discoverability") if isinstance(metrics.get("discoverability"), dict) else {}
    recovery = metrics.get("recovery") if isinstance(metrics.get("recovery"), dict) else {}
    experience = metrics.get("experience_frictions") if isinstance(metrics.get("experience_frictions"), dict) else {}
    host_pressure = metrics.get("host_pressure") if isinstance(metrics.get("host_pressure"), dict) else {}
    lenses = report.get("lenses") if isinstance(report.get("lenses"), dict) else {}
    wake_prompts = lenses.get("wake-prompts") if isinstance(lenses.get("wake-prompts"), dict) else {}
    trace_context_text = json.dumps(lenses, default=str, sort_keys=True).lower()
    has_trace_context = any(
        term in trace_context_text
        for term in (
            "trace",
            "telemetry",
            "agent observability",
            "process audit",
            "process trace",
            "bottleneck",
            "friction",
        )
    )

    max_compactions = _coerce_count(context.get("max_compactions"))
    reread_file_count = _coerce_count(context.get("reread_file_count"))
    reread_pressure_count = _context_reread_pressure_count(context)
    host_bottleneck = str(host_pressure.get("bottleneck_class") or "")
    host_active_agents = _coerce_count(host_pressure.get("active_agents"))
    if host_bottleneck and host_bottleneck not in {"productive_parallelism", "cpu_saturated_but_productive"}:
        _add_trace_improvement_row(
            rows,
            priority=90 if host_active_agents >= 2 else 74,
            symptom_family="host_pressure",
            title="Parallel agent throughput needs host-pressure correlation",
            evidence={
                "active_agents": host_pressure.get("active_agents"),
                "progress_units": host_pressure.get("progress_units"),
                "pressure_index": host_pressure.get("pressure_index"),
                "progress_per_pressure": host_pressure.get("progress_per_pressure"),
                "bottleneck_class": host_bottleneck,
                "governor_decision": host_pressure.get("governor_decision"),
                "confidence": host_pressure.get("confidence"),
            },
            owner_surface="system/lib/host_pressure.py + /api/agent-observability/host-pressure + AgentObservabilityLens",
            next_command=HOST_PRESSURE_SUMMARY_FIRST_COMMAND,
            candidate_patch=(
                "Use the no-process progress-pressure packet to classify admission, bottleneck, "
                "load-shed, and runtime readiness before launching more tests, browsers, helpers, "
                "servers, or background setup."
            ),
            source_lenses=["host_pressure_surface"],
            cap_refs=["progress_pressure_ledger_v0"],
        )
    if max_compactions >= 2 or reread_pressure_count >= 5:
        store_hint = _context_pressure_store_hint(max_compactions, reread_pressure_count)
        top_compaction = (context.get("top_compaction_sessions") or [{}])[0]
        top_reread = (context.get("rediscovery") or [{}])[0]
        rollout_session_id = (
            _codex_session_id_from_rollout_path(top_compaction.get("path"))
            if isinstance(top_compaction, dict)
            else None
        )
        context_evidence = {
            "max_compactions": max_compactions,
            "reread_file_count": reread_file_count,
            "reread_pressure_count": reread_pressure_count,
            "top_compaction_sessions_omitted": _coerce_count(
                context.get("top_compaction_sessions_omitted")
            ),
            "top_reads_omitted": _coerce_count(context.get("top_reads_omitted")),
            "rediscovery_omitted": _coerce_count(context.get("rediscovery_omitted")),
            "top_compaction_session": {
                "path": top_compaction.get("path"),
                "compactions": top_compaction.get("compactions"),
                "turns": top_compaction.get("turns"),
                "scan_mode": top_compaction.get("scan_mode"),
                "scan_truncated": top_compaction.get("scan_truncated"),
                "count_semantics": top_compaction.get("count_semantics"),
                "bytes_scanned": top_compaction.get("bytes_scanned"),
                "file_size_bytes": top_compaction.get("file_size_bytes"),
                "session_id": rollout_session_id,
                "session_id_source": "rollout_filename_unverified" if rollout_session_id else None,
                "process_summary_lookup": (
                    "runtime_alias_required" if rollout_session_id else "no_rollout_session_id"
                ),
            } if isinstance(top_compaction, dict) else {},
            "top_reread_hotspot": {
                "path": top_reread.get("path"),
                "reads": top_reread.get("reads"),
                "distinct_sessions": top_reread.get("distinct_sessions"),
                "score": top_reread.get("score"),
            } if isinstance(top_reread, dict) else {},
            "runtime_focus": store_hint,
        }
        _add_trace_improvement_row(
            rows,
            priority=92 if max_compactions >= 2 else 78,
            symptom_family="context_pressure",
            title="Trace window shows compactions or repeated file rereads",
            evidence=context_evidence,
            owner_surface="tools/meta/observability/session_analyzer.py + compact owner packets",
            next_command=_context_pressure_runtime_commands(context_evidence, last=10)[0],
            candidate_patch=(
                "Prefer summary-first trace packets, process-summary, or bounded owner cards before "
                "opening full session bodies or large repeated files."
            ),
            source_lenses=["latency", "hotspots", "ladder-skip"],
        )

    ratio = float(ladder.get("ratio_bad_to_good_bash") or 0.0)
    grep_before_nav = _coerce_count(ladder.get("grep_calls_before_any_nav_flag"))
    if ratio >= 0.2 or grep_before_nav > 0:
        dominant_shell_shape = _ladder_skip_metric_dominant_shell_shape(
            ladder,
            grep_before_nav=grep_before_nav,
        )
        _add_trace_improvement_row(
            rows,
            priority=88 if ratio >= 0.4 or grep_before_nav > 0 else 72,
            symptom_family="ladder_skip",
            title="Agents still reach for shell discovery before typed navigation",
            evidence={
                "ratio_bad_to_good_bash": ratio,
                "grep_calls_before_any_nav_flag": grep_before_nav,
                "bash_should_be_native_top": ladder.get("bash_should_be_native_top", [])[:3],
                "kernel_nav_flag_calls": ladder.get("kernel_nav_flag_calls", [])[:3],
                "dominant_shell_shape": dominant_shell_shape,
                "runtime_focus": "claude",
            },
            owner_surface="codex/doctrine/skills/kernel/agent_session_diagnostics.md#lens-3--ladder-skip",
            next_command=_session_diagnostics_command("ladder-skip", last=10, store="claude"),
            candidate_patch=(
                "Patch the missing route, hook hint, or command card for the repeated Claude shell "
                "shape instead of treating grep/find/cat volume as harmless noise."
            ),
            source_lenses=["histogram", "ladder-skip"],
        )

    unresolved_known = _route_miss_unresolved_count_known(discoverability)
    unresolved = _coerce_count(discoverability.get("route_miss_unresolved"))
    candidates = _coerce_count(discoverability.get("route_miss_candidates"))
    route_miss_command = (
        "./repo-python kernel.py --session-diagnostics --lens route-misses --last 20 "
        "--store both --json --write-route-miss-candidates state/session_diagnostics/route_miss_candidates.json"
    )
    if unresolved_known and unresolved > 0:
        _add_trace_improvement_row(
            rows,
            priority=86,
            symptom_family="route_discoverability",
            title="Operator and agent trace vocabulary is ahead of docs-route aliases",
            evidence={
                "route_miss_candidates": candidates,
                "route_miss_unresolved": unresolved,
                "route_miss_unresolved_known": unresolved_known,
                "route_miss_probe_status": discoverability.get("route_miss_probe_status"),
            },
            owner_surface="codex/doctrine/documentation_theory_index.json",
            next_command=route_miss_command,
            candidate_patch=(
                "Patch one phrase cohort into the owning docs-route row and add a docs-route regression "
                "before broadening entry prose."
            ),
            source_lenses=["prompts", "wake-prompts", "route-misses"],
        )
    elif candidates > 0 and not unresolved_known:
        _add_trace_improvement_row(
            rows,
            priority=68,
            symptom_family="route_discoverability",
            title="Route-miss candidates need explicit probe before patch decision",
            evidence={
                "route_miss_candidates": candidates,
                "route_miss_unresolved": discoverability.get("route_miss_unresolved"),
                "route_miss_unresolved_known": unresolved_known,
                "route_miss_probe_status": discoverability.get("route_miss_probe_status"),
                "resolution_status": "unresolved_probe_deferred",
            },
            owner_surface="tools/meta/observability/session_analyzer.py::route-misses lens",
            next_command=route_miss_command,
            candidate_patch=(
                "Run the route-misses lens with sidecar output before deciding docs-route alias work; "
                "fast summaries with omitted probes are neither unresolved proof nor resolved-only "
                "no-patch proof."
            ),
            source_lenses=["route-misses"],
        )
    elif candidates > 0:
        _add_trace_improvement_row(
            rows,
            priority=58,
            symptom_family="route_discoverability",
            title="Route-miss candidates are resolved; keep sidecar trend only",
            evidence={
                "route_miss_candidates": candidates,
                "route_miss_unresolved": unresolved,
                "route_miss_unresolved_known": unresolved_known,
                "route_miss_probe_status": discoverability.get("route_miss_probe_status"),
                "resolution_status": "resolved_sidecar_trend_only",
            },
            owner_surface="state/session_diagnostics/route_miss_candidates.json",
            next_command=route_miss_command,
            candidate_patch=(
                "Write or review the route-miss sidecar as vocabulary trend evidence only; do not "
                "patch docs-route aliases unless unresolved_count becomes positive or a sampled "
                "resolved candidate proves to be a false negative."
            ),
            source_lenses=["route-misses"],
        )

    rediscovery = context.get("rediscovery") if isinstance(context.get("rediscovery"), list) else []
    top_rediscovery = rediscovery[0] if rediscovery and isinstance(rediscovery[0], dict) else {}
    if _coerce_count(top_rediscovery.get("score")) >= 20:
        rediscovery_path = str(top_rediscovery.get("path") or "")
        rediscovery_repair = _rediscovery_hotspot_repair(rediscovery_path)
        rediscovery_evidence = {
            "path": top_rediscovery.get("path"),
            "reads": top_rediscovery.get("reads"),
            "distinct_sessions": top_rediscovery.get("distinct_sessions"),
            "score": top_rediscovery.get("score"),
            "runtime_focus": "claude",
        }
        if rediscovery_repair.get("owner_component_id"):
            rediscovery_evidence["owner_component_id"] = rediscovery_repair["owner_component_id"]
        if rediscovery_repair.get("owner_route_id"):
            rediscovery_evidence["owner_route_id"] = rediscovery_repair["owner_route_id"]
        if rediscovery_repair.get("owner_paper_module_slug"):
            rediscovery_evidence["owner_paper_module_slug"] = rediscovery_repair["owner_paper_module_slug"]
        for key in (
            "paper_module_source_command",
            "paper_module_index_check_command",
            "supporting_paper_module_card_command",
            "paper_module_write_profile",
        ):
            if rediscovery_repair.get(key):
                rediscovery_evidence[key] = rediscovery_repair[key]
        _add_trace_improvement_row(
            rows,
            priority=_rediscovery_hotspot_priority(
                top_rediscovery,
                rediscovery_repair,
                max_compactions=max_compactions,
            ),
            symptom_family="rediscovery_hotspot",
            title="Multiple sessions rediscover the same file instead of a compact owner surface",
            evidence=rediscovery_evidence,
            owner_surface=rediscovery_repair["owner_surface"],
            next_command=rediscovery_repair["next_command"],
            candidate_patch=rediscovery_repair["candidate_patch"],
            source_lenses=["hotspots"],
        )

    interrupt_count = _coerce_count(recovery.get("user_interrupt_count"))
    tool_errors = recovery.get("top_tool_error_lines") if isinstance(recovery.get("top_tool_error_lines"), list) else []
    if interrupt_count > 0 or tool_errors:
        command_usage_families = _compact_command_usage_error_families(tool_errors[:5])
        _add_trace_improvement_row(
            rows,
            priority=_recovery_friction_priority(command_usage_families),
            symptom_family="recovery_friction",
            title="Trace corpus contains interruptions or repeated tool-error signatures",
            evidence={
                "user_interrupt_count": interrupt_count,
                "top_tool_error_lines": [row[0] if isinstance(row, (list, tuple)) and row else row for row in tool_errors[:3]],
                "top_command_usage_families": command_usage_families,
            },
            owner_surface="skill trigger, runtime hook, or failing owner command",
            next_command="./repo-python kernel.py --session-diagnostics --lens errors --last 20 --store both --json",
            candidate_patch=(
                "Group the repeated correction/error shape, then patch the owning skill/hook/command "
                "or capture a bounded Task Ledger residual."
            ),
            source_lenses=["errors"],
        )

    repeated_wake = _coerce_count(discoverability.get("repeated_wake_prompt_clusters"))
    if repeated_wake > 0:
        _add_trace_improvement_row(
            rows,
            priority=68,
            symptom_family="wake_prompt_repetition",
            title="Wake prompts repeat an orientation shape that may deserve a bounded packet",
            evidence={
                "repeated_wake_prompt_clusters": repeated_wake,
            },
            owner_surface="codex/doctrine/skills/kernel/agent_session_diagnostics.md + autonomous seed authoring",
            next_command="./repo-python kernel.py --session-diagnostics --lens wake-prompts --last 20 --store both --json",
            candidate_patch=(
                "If the repeated wake prompt carries stable route scaffolding, move that scaffolding into "
                "a compact packet or skill route instead of making future prompts repeat it."
            ),
            source_lenses=["wake-prompts"],
        )

    experience_families = [
        row for row in experience.get("top_families", [])
        if isinstance(row, dict)
    ]
    if _coerce_count(experience.get("event_count")) > 0 and experience_families:
        top_experience = experience_families[0]
        episode_family = str(top_experience.get("family") or "unknown")
        _add_trace_improvement_row(
            rows,
            priority=_coerce_count(top_experience.get("priority")) or 82,
            symptom_family="experience_friction",
            title="Trace updates expose a recurring repair-shaped friction episode",
            evidence={
                "episode_family": episode_family,
                "event_count": experience.get("event_count"),
                "family_count": experience.get("family_count"),
                "top_families": [
                    _compact_experience_family_action_row(row)
                    for row in experience_families[:TRACE_IMPROVEMENT_SUMMARY_ROW_LIMIT]
                ],
            },
            owner_surface=str(top_experience.get("owner_surface") or "agent_session_diagnostics experience-frictions lens"),
            next_command=str(top_experience.get("next_command") or "./repo-python kernel.py --session-diagnostics --lens experience-frictions --last 20 --store both --json"),
            candidate_patch=str(top_experience.get("candidate_patch") or "Patch the smallest owner surface for the classified episode family."),
            source_lenses=["experience-frictions"],
        )

    if report.get("kind") == "agent_session_diagnostics_fast_scan":
        cap_signal = {
            "status": "deferred_in_fast_scan_summary",
            "match_count": 0,
            "rows": [],
            "next_command": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
            "reason": "summary_first_route_defers_task_ledger_cap_alignment",
        }
    elif has_trace_context:
        cap_signal = _task_ledger_trace_cap_matches(limit=3)
    else:
        cap_signal = {
            "status": "skipped_no_trace_observability_context",
            "match_count": 0,
            "rows": [],
            "next_command": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
        }
    cap_rows = cap_signal.get("rows") if isinstance(cap_signal.get("rows"), list) else []
    actionable_cap_rows = [
        row for row in cap_rows
        if isinstance(row, dict) and _trace_cap_is_actionable(row)
    ]
    if actionable_cap_rows:
        cap_refs = [str(row.get("id")) for row in actionable_cap_rows if row.get("id")]
        compact_cap_rows = _compact_trace_cap_rows(actionable_cap_rows, limit=3)
        _add_trace_improvement_row(
            rows,
            priority=84,
            symptom_family="task_ledger_cap_pressure",
            title="Task Ledger already has trace-observability CAPs that need shaping or owner repair",
            evidence={
                "match_count": cap_signal.get("match_count"),
                "top_ids": cap_refs[:3],
                "top_cap_rows": compact_cap_rows,
            },
            owner_surface="state/task_ledger/events.jsonl via task_ledger_apply.py",
            next_command=str(cap_signal.get("next_command") or ""),
            candidate_patch=(
                "Use Task Ledger CAPs as the work-item angle: shape satisfaction/acceptance contracts "
                "or link the trace improvement to an existing row before creating a parallel backlog."
            ),
            source_lenses=["task_ledger_views"],
            cap_refs=cap_refs,
        )

    rows.sort(key=lambda row: int(row.get("priority") or 0), reverse=True)
    rows = rows[:limit]
    cap_alignment = dict(cap_signal)
    cap_alignment["actionable_match_count"] = len(actionable_cap_rows)
    cap_alignment["non_actionable_match_count"] = max(
        0,
        len(cap_rows) - len(actionable_cap_rows),
    )
    cap_alignment["actionability_rule"] = (
        "closed/signed-off/no-action trace CAP matches stay visible as alignment evidence, "
        "but they do not emit task_ledger_cap_pressure owner-action rows."
    )
    if isinstance(cap_alignment.get("rows"), list):
        cap_alignment["top_rows"] = _compact_trace_cap_rows(cap_alignment["rows"], limit=3)
        cap_alignment["top_ids"] = [
            str(row.get("id")) for row in cap_alignment["rows"][:3]
            if isinstance(row, dict) and row.get("id")
        ]
        cap_alignment.pop("rows", None)
    return {
        "schema_version": "session_trace_improvement_surface_v0",
        "status": "available",
        "purpose": (
            "Rank trace-observed friction into owner-action candidates without exposing raw session bodies."
        ),
        "live_vs_finished_boundary": {
            "finished_trace_surface": "./repo-python kernel.py --session-diagnostics --lens all --last 10 --store both --json --diagnostics-summary",
            "live_trace_surface": "./repo-python kernel.py --process-summary latest",
            "span_trace_surface": "./repo-python kernel.py --process-trace latest",
            "live_trace_readiness_contract": _live_trace_readiness_contract(),
        },
        "summary": {
            "row_count": len(rows),
            "top_symptom_family": rows[0]["symptom_family"] if rows else None,
            "cap_match_count": cap_signal.get("match_count"),
        },
        "self_propagation_contract": {
            "schema_version": "trace_summary_self_propagation_contract_v0",
            "default_first_command": (
                "./repo-python kernel.py --session-diagnostics --lens all --last 30 "
                "--store both --json --diagnostics-summary"
            ),
            "selection_rule": (
                "Pick the highest-priority row whose owner lane is safe and patchable; "
                "otherwise use its action_contract to record the blocked owner and exact re-entry condition."
            ),
            "owner_action_rule": (
                "Rows are selectors, not source authority: run action_contract.first_drilldown, "
                "use supporting_drilldowns for any evidence lens not covered there, then mutate only "
                "the named owner surface with the required receipts."
            ),
            "cap_rule": (
                "When action_contract.cap_ref_kinds.work_item_refs are present, shape, link, "
                "retire, or block those existing rows before creating any new trace-observability "
                "CAP. When only artifact_refs are present, inspect or reuse those evidence handles "
                "instead of treating them as backlog rows."
            ),
            "raw_body_rule": (
                "Do not open raw session bodies, prompt bodies, assistant prose, or tool output bodies "
                "unless the selected owner drilldown proves the compact row is insufficient."
            ),
        },
        "rows": rows,
        "cap_alignment": cap_alignment,
        "privacy_boundary": "Rows carry counts, paths, ids, and owner commands; raw prompts and tool bodies stay behind diagnostics/process drilldowns.",
    }


_TRACE_FRICTION_IMPACT: dict[str, list[str]] = {
    "context_pressure": ["context", "latency"],
    "ladder_skip": ["repeated_tooling", "latency"],
    "route_discoverability": ["repeated_tooling", "operator_interrupt"],
    "rediscovery_hotspot": ["context", "repeated_tooling"],
    "recovery_friction": ["operator_interrupt", "validation_risk"],
    "wake_prompt_repetition": ["context", "repeated_tooling"],
    "experience_friction": ["operator_interrupt", "validation_risk", "backlog_duplication"],
    "task_ledger_cap_pressure": ["backlog_duplication"],
    "cap_pressure": ["backlog_duplication"],
    "host_pressure": ["latency", "host_pressure", "throughput"],
    "context_yield": ["context", "latency", "repeated_tooling"],
    "route_lease_churn": ["context", "latency", "repeated_tooling"],
    "live_stall": ["latency"],
    "handoff_loss": ["operator_interrupt", "validation_risk"],
    "evidence_gap": ["validation_risk"],
}

_TRACE_FRICTION_MUTATION: dict[str, str] = {
    "route_discoverability": "diagnostic_fixture",
    "experience_friction": "owner_surface_patch",
    "task_ledger_cap_pressure": "candidate_WorkItem",
    "cap_pressure": "candidate_WorkItem",
    "host_pressure": "owner_surface_patch",
    "context_yield": "evaluator_guard",
    "route_lease_churn": "evaluator_guard",
    "live_stall": "evaluator_guard",
    "handoff_loss": "evaluator_guard",
    "evidence_gap": "evaluator_guard",
}

_TRACE_FRICTION_DISCONFIRMING_CHECK: dict[str, str] = {
    "context_pressure": "Last 10 and last 30 diagnostics windows both show low compactions and no repeated reread hotspot.",
    "ladder_skip": "Post-repair diagnostics show no grep/find/raw shell discovery before typed navigation in the selected window.",
    "route_discoverability": "Route-miss lens resolves the candidate phrase cohort and docs-route regression passes.",
    "rediscovery_hotspot": "Hotspot lens shows the repeated path no longer crosses the rediscovery score floor.",
    "recovery_friction": "Errors lens shows the repeated interruption/tool-error signature retired from the current window.",
    "wake_prompt_repetition": "Wake-prompt lens shows the repeated orientation cluster no longer recurs after the packet/skill patch.",
    "experience_friction": "Experience-frictions lens shows the classified episode family no longer recurs in the later window.",
    "task_ledger_cap_pressure": "Task Ledger views show the matched trace CAPs shaped, linked, retired, or explicitly blocked.",
    "cap_pressure": "Task Ledger views show the matched trace CAPs shaped, linked, retired, or explicitly blocked.",
    "host_pressure": "Host-pressure no-process packets show no heavy-work queue decision, or launcher/browser/backend work carries an admission and readiness receipt with a recheck command.",
    "context_yield": "Process-bottleneck context-yield attribution shows the motif below the active-byte floor or the existing route used before raw body carryover.",
    "route_lease_churn": "Process-summary route-lease mode-control counts no longer show repeated broad routes or kernel-output bloat before direct action.",
    "live_stall": "Live process bottlenecks after the repair window show the action kind below threshold or stale-only.",
    "handoff_loss": "Work Ledger claims show no collisions and no orphaned active sessions for the current window.",
    "evidence_gap": "The named projection refreshes cleanly and the next trace board run carries a fresh authority receipt.",
}

_COMMAND_EFFICIENCY_CLASS_BY_FAMILY: dict[str, str] = {
    "context_pressure": "context_pack_reread_pressure",
    "ladder_skip": "shell_search_before_typed_route",
    "route_discoverability": "shell_search_before_typed_route",
    "rediscovery_hotspot": "context_pack_reread_pressure",
    "recovery_friction": "validation_overbreadth",
    "wake_prompt_repetition": "duplicate_bootstrap_preflight_churn",
    "experience_friction": "stale_claim_preflight_friction",
    "task_ledger_cap_pressure": "stale_claim_preflight_friction",
    "cap_pressure": "stale_claim_preflight_friction",
    "context_yield": "context_pack_reread_pressure",
    "route_lease_churn": "repeated_broad_route_churn",
    "live_stall": "task_tool_wait_saturation",
    "handoff_loss": "stale_claim_preflight_friction",
    "evidence_gap": "generated_projection_rebuild_churn",
    "host_pressure": "runtime_readiness_before_launch",
}

_COMMAND_EFFICIENCY_CLASS_DEFAULTS: dict[str, dict[str, str]] = {
    "duplicate_bootstrap_preflight_churn": {
        "old_command_pattern": "Repeated bootstrap or wake-orientation commands before a reusable packet has been selected.",
        "replacement_action": "Use the generated seed/summary packet first, then run only the missing state check.",
        "expected_proof": "Later trace board replay shows the wake/bootstrap recurrence retired or lower while required state receipts remain present.",
        "seed_rewrite_clause": "Start future autonomous-seed passes from the generated packet for this route; repeat bootstrap/preflight only when freshness or authority changed.",
    },
    "context_pack_reread_pressure": {
        "old_command_pattern": "Repeated context-pack, session diagnostics, file rereads, or full trace/body opens before selecting a compact owner row.",
        "replacement_action": "Enter through the summary-first diagnostics packet or the row's runtime-scoped owner route before opening broad context.",
        "expected_proof": "Replay preserves the trace-board quality gate and shows lower reread/context-pressure recurrence in the compared window.",
        "seed_rewrite_clause": "When this class appears, use `{replacement_route}` as the first drilldown and avoid broad rereads until that route proves insufficient.",
    },
    "shell_search_before_typed_route": {
        "old_command_pattern": "Shell search or grep-style discovery appears before typed navigation, docs-route, or owner-card selection.",
        "replacement_action": "Use context-pack or the row's typed route before source search; after ownership is selected, patch the missing route alias or command card.",
        "expected_proof": "Ladder-skip replay shows grep-before-navigation reduced and the context-pack, docs-route, or selected lens still resolves the owner.",
        "seed_rewrite_clause": "For matching vocabulary, route through `{replacement_route}` before any broad shell search.",
    },
    "stale_claim_preflight_friction": {
        "old_command_pattern": "Claim, CAP, or handoff friction repeats before the compact Work Ledger/Task Ledger status surface is used.",
        "replacement_action": "Refresh the compact claim/CAP projection, use read-only owner status for peer heartbeat gaps, and shape or link the existing row before creating new backlog or source patches.",
        "expected_proof": "Work Ledger/CAP receipts remain attached and later replay shows no collision/orphan, duplicate trace-CAP pressure, or unclassified heartbeat authority boundary.",
        "seed_rewrite_clause": "Before new trace work in this area, run `{replacement_route}`, classify claim and heartbeat ownership, and bind the result to an existing claim/CAP when one exists.",
    },
    "task_tool_wait_saturation": {
        "old_command_pattern": "Slow task/tool or process spans are inspected through serial waits instead of a scoped process summary or bottleneck route.",
        "replacement_action": "Use the runtime-scoped process summary or force-live bottleneck route to pick the slow action-kind owner first.",
        "expected_proof": "Process-bottleneck replay shows the selected action kind below threshold or marked stale-only, with validation receipts unchanged.",
        "seed_rewrite_clause": "If process latency is the top pressure, call `{replacement_route}` before serial task/tool probing.",
    },
    "generated_projection_rebuild_churn": {
        "old_command_pattern": "Generated read models are stale or missing, causing agents to rerun exploratory diagnostics instead of refreshing the owner projection.",
        "replacement_action": "Refresh the named projection through its owner command and use the fresh authority receipt before selecting a source patch.",
        "expected_proof": "Projection freshness is available and trace_board_quality_gate freshness_authority remains pass.",
        "seed_rewrite_clause": "When a trace claim depends on a stale projection, refresh with `{replacement_route}` before using the row as source-patch authority.",
    },
    "runtime_readiness_before_launch": {
        "old_command_pattern": "Runtime blockers trigger install, browser, helper, server, or background launch work before admission and readiness receipts are recorded.",
        "replacement_action": "Use the no-process host-pressure packet first, then ask the owner launcher for prerequisite, setup, launch/reuse, readiness, and detached-work receipts.",
        "expected_proof": "The trace row carries admission/load-shed status plus a runtime readiness status and recheck command; full process census is only used when compact readiness cannot decide.",
        "seed_rewrite_clause": "For runtime prerequisites or launcher blockers, run `{replacement_route}` first and carry the readiness contract before installing, launching, or backgrounding work.",
    },
    "repeated_broad_route_churn": {
        "old_command_pattern": "Repeated broad kernel routes or full-output route calls run after an entry lease before direct local action consumes the lease.",
        "replacement_action": "Use the runtime-scoped process-summary route to identify the repeated route signal, then switch to the selected owner route or direct local action before repeating broad navigation.",
        "expected_proof": "Process-summary route-lease mode-control counts show the repeated-route and full-output-bloat signals retired or below the warning floor.",
        "seed_rewrite_clause": "When route-lease churn appears, run `{replacement_route}` to select the exact repeated route signal, then consume the lease with a typed owner route or direct local action before rerunning broad navigation.",
    },
    "validation_overbreadth": {
        "old_command_pattern": "Repeated errors or interruptions trigger broad validation or forensic reads before a targeted failing owner command is selected.",
        "replacement_action": "Use the selected error/experience lens to isolate the owner command, then run the narrow validation receipt.",
        "expected_proof": "Focused validation preserves failure/success status while reducing repeated error or interruption recurrence.",
        "seed_rewrite_clause": "For repeated command-contract or validation friction, run `{replacement_route}` and validate the narrow owner before broad suites.",
    },
}


def _trace_friction_owner_type(owner_surface: str, symptom_family: str) -> str:
    text = f"{owner_surface} {symptom_family}".lower()
    if "task_ledger" in text or "cap" in text or "workitem" in text:
        return "WorkItem/CAP"
    if "documentation_theory_index" in text or "docs-route" in text:
        return "docs_route"
    if "skill" in text or ".md#" in text:
        return "skill"
    if "std_" in text or "standard" in text:
        return "standard"
    if "hud" in text or "frontend" in text or "station" in text:
        return "HUD"
    if "test" in text:
        return "test_lane"
    if "command" in text or "process_bottlenecks" in text:
        return "command_card"
    return "owner_surface"


def _route_discoverability_resolution_contract(
    *,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = evidence or {}
    unresolved_known = _route_miss_unresolved_count_known(evidence)
    unresolved = _coerce_count(evidence.get("route_miss_unresolved"))
    candidates = _coerce_count(evidence.get("route_miss_candidates"))
    docs_route_patch_allowed = unresolved_known and unresolved > 0
    status = (
        "unresolved_alias_patch_required"
        if docs_route_patch_allowed
        else "unresolved_probe_deferred"
        if candidates > 0 and not unresolved_known
        else "resolved_sidecar_trend_only"
        if candidates > 0
        else "no_route_miss_pressure"
    )
    return {
        "schema_version": "route_discoverability_resolution_contract_v0",
        "status": status,
        "candidate_count": candidates,
        "unresolved_count": unresolved if unresolved_known else None,
        "unresolved_count_known": unresolved_known,
        "probe_status": evidence.get("route_miss_probe_status"),
        "docs_route_patch_allowed": docs_route_patch_allowed,
        "patch_docs_route_when": "route_miss_unresolved > 0",
        "probe_deferred_rule": (
            "When the fast summary omits route-miss probing, run the route-misses lens with "
            "sidecar output before classifying the cohort as unresolved or resolved-only."
        ),
        "resolved_only_rule": (
            "Resolved candidates are vocabulary trend evidence, not docs-route patch authority, "
            "unless sampling shows the probe produced a false negative."
        ),
        "reentry_condition": (
            "Patch docs-route aliases only after unresolved_count becomes positive or a sampled "
            "resolved candidate is shown to be unresolved in practice."
        ),
    }


def _route_miss_unresolved_count_known(evidence: dict[str, Any] | None) -> bool:
    if not isinstance(evidence, dict):
        return False
    if evidence.get("route_miss_unresolved_known") is not None:
        return bool(evidence.get("route_miss_unresolved_known"))
    value = evidence.get("route_miss_unresolved")
    return value not in (None, "")


def _trace_friction_receipts(
    symptom_family: str,
    *,
    evidence: dict[str, Any] | None = None,
) -> list[str]:
    if symptom_family == "route_discoverability":
        if not _route_miss_unresolved_count_known(evidence):
            return [
                "route_miss_probe_resolution_check",
                "route_miss_sidecar_check",
                "no_docs_route_patch_without_unresolved_count",
            ]
        if _coerce_count((evidence or {}).get("route_miss_unresolved")) > 0:
            return ["docs_route_regression", "route_miss_sidecar_check"]
        return [
            "route_miss_sidecar_check",
            "resolved_candidate_sample_check",
            "no_docs_route_patch_needed",
        ]
    if symptom_family in {"task_ledger_cap_pressure", "cap_pressure"}:
        return ["cap_shape_or_link_receipt", "task_ledger_projection_check"]
    if symptom_family == "live_stall":
        return ["process_bottlenecks_force_check", "post_repair_window_check"]
    if symptom_family == "context_yield":
        return [
            "process_bottlenecks_force_check",
            "context_yield_attribution_check",
            "replacement_route_owner_check",
            "post_repair_context_yield_window",
        ]
    if symptom_family == "route_lease_churn":
        return [
            "process_summary_force_check",
            "route_lease_mode_control_check",
            "replacement_route_consumed_before_repeating_broad_route",
            "post_repair_route_lease_window",
        ]
    if symptom_family == "evidence_gap":
        return ["projection_refresh_check", "privacy_omission_receipt"]
    if symptom_family == "handoff_loss":
        return ["work_ledger_claim_check", "collision_or_orphan_retirement_receipt"]
    if symptom_family == "context_pressure":
        receipts = [
            "diagnostics_summary_size_check",
            "dogfood_last_10_last_30",
        ]
        if _context_pressure_has_hotspot_path(evidence):
            receipts.append("hotspot_owner_or_claim_check")
        else:
            receipts.append("compaction_window_receipt")
        return receipts
    if symptom_family == "ladder_skip":
        return [
            "ladder_skip_lens_check",
            "typed_route_or_command_card_patch_receipt",
            "post_repair_ladder_skip_window",
        ]
    if symptom_family == "host_pressure":
        return [
            "host_pressure_no_processes_check",
            "workload_admission_or_load_shed_receipt",
            "runtime_launcher_readiness_state",
        ]
    if symptom_family == "recovery_friction":
        receipts = [
            "errors_lens_check",
            "recovery_signature_classification",
        ]
        families = [
            row for row in (evidence or {}).get("top_command_usage_families") or []
            if isinstance(row, dict)
        ]
        if families:
            receipts.extend([
                "owner_help_route_checked_or_not_applicable",
                "owner_patch_or_blocked_reentry_condition",
            ])
        if _coerce_count((evidence or {}).get("user_interrupt_count")) > 0:
            receipts.append("interruption_recovery_classification")
        receipts.append("post_repair_errors_window")
        return receipts
    if symptom_family == "rediscovery_hotspot" and (evidence or {}).get("owner_paper_module_slug"):
        return [
            "selected_lens_check",
            "paper_module_compression_status_check",
            "projection_refresh_or_blocked_receipt",
            "dogfood_summary_size_check",
        ]
    if symptom_family == "experience_friction":
        secondary_receipt = (
            ["supporting_family_drilldown_check"]
            if _has_secondary_experience_family_drilldown(evidence or {})
            else []
        )
        boundary_receipts: list[str] = []
        family_ids = set(_experience_family_ids(evidence or {}))
        if "metadata_settlement_detour" in family_ids:
            boundary_receipts.append("metadata_settlement_boundary_check")
        if "closeout_authority_confusion" in family_ids:
            boundary_receipts.append("closeout_authority_boundary_check")
        if family_ids.intersection({"command_contract_mismatch", "task_ledger_payload_rejection"}):
            boundary_receipts.append("command_contract_boundary_check")
        if "compaction_recovery" in family_ids:
            boundary_receipts.append("compaction_recovery_boundary_check")
        if _is_claim_contention_experience(evidence or {}):
            return [
                "experience_friction_lens_check",
                "claim_cards_first_check",
                "claim_classification_receipt",
                "heartbeat_authority_boundary_check",
                "session_bound_preflight_check",
                *secondary_receipt,
                *boundary_receipts,
                "owner_surface_patch_receipt",
                "post_repair_window_check",
            ]
        return [
            "experience_friction_lens_check",
            *secondary_receipt,
            *boundary_receipts,
            "owner_surface_patch_receipt",
            "post_repair_window_check",
        ]
    return ["selected_lens_check", "dogfood_summary_size_check"]


def _context_pressure_has_hotspot_path(evidence: dict[str, Any] | None) -> bool:
    if not isinstance(evidence, dict):
        return False
    top_hotspot = evidence.get("top_reread_hotspot")
    if not isinstance(top_hotspot, dict):
        return False
    return bool(top_hotspot.get("path"))


def _command_efficiency_class_for_row(row: dict[str, Any]) -> str:
    family = str(row.get("symptom_family") or "")
    if family == "live_stall":
        recurrence = row.get("recurrence") if isinstance(row.get("recurrence"), dict) else {}
        action_kinds = " ".join(str(value) for value in recurrence.get("action_kinds") or [])
        if "task_tool" in action_kinds:
            return "task_tool_wait_saturation"
    if family == "experience_friction":
        episode = str(row.get("episode_family") or "").lower()
        if "claim" in episode or "ledger" in episode or "cap" in episode:
            return "stale_claim_preflight_friction"
        if "contract" in episode or "validation" in episode or "error" in episode:
            return "validation_overbreadth"
    return _COMMAND_EFFICIENCY_CLASS_BY_FAMILY.get(family, "validation_overbreadth")


def _command_efficiency_replacement_route(row: dict[str, Any], class_id: str) -> str:
    runtime_commands = [
        str(command)
        for command in row.get("runtime_scoped_commands") or []
        if str(command).strip()
    ]
    if class_id in {"context_pack_reread_pressure", "task_tool_wait_saturation", "repeated_broad_route_churn"} and runtime_commands:
        return runtime_commands[0]
    family = str(row.get("symptom_family") or "")
    if class_id == "shell_search_before_typed_route" and family == "ladder_skip":
        return LADDER_SKIP_TYPED_ROUTE_REPLACEMENT
    next_command = str(row.get("next_command") or "").strip()
    if next_command:
        return next_command
    if class_id == "stale_claim_preflight_friction":
        return "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 20 --cards-only"
    if class_id == "generated_projection_rebuild_churn":
        return "./repo-python kernel.py --trace-friction-board --last 30 --write-trace-observatory-projection"
    return "./repo-python kernel.py --session-diagnostics --lens all --last 10 --store both --json --diagnostics-summary"


def _command_efficiency_action_from_row(row: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
    class_id = _command_efficiency_class_for_row(row)
    defaults = _COMMAND_EFFICIENCY_CLASS_DEFAULTS[class_id]
    replacement_route = _command_efficiency_replacement_route(row, class_id)
    recurrence = row.get("recurrence") if isinstance(row.get("recurrence"), dict) else {}
    owner = row.get("candidate_owner") if isinstance(row.get("candidate_owner"), dict) else {}
    row_id = str(row.get("row_id") or f"row:{ordinal}")
    action_id = f"command_efficiency:{class_id}:{hashlib.sha256(row_id.encode('utf-8')).hexdigest()[:10]}"
    seed_clause = defaults["seed_rewrite_clause"].format(replacement_route=replacement_route)
    action = {
        "action_id": action_id,
        "source_row_id": row_id,
        "rank": ordinal + 1,
        "inefficiency_class": class_id,
        "symptom_family": row.get("symptom_family"),
        "old_command_pattern": defaults["old_command_pattern"],
        "replacement_route": replacement_route,
        "replacement_action": defaults["replacement_action"],
        "expected_proof": defaults["expected_proof"],
        "seed_rewrite_clause": seed_clause,
        "validation_preservation": "Required bootstrap, claim, freshness, privacy, and validation receipts remain mandatory.",
        "owner_surface": owner.get("surface") or row.get("candidate_owner") or row.get("candidate_mutation"),
        "candidate_mutation": row.get("candidate_mutation"),
        "receipt_needed": list(row.get("receipt_needed") or [])[:5],
        "evidence": {
            "mode": row.get("mode"),
            "priority": row.get("priority"),
            "recurrence_count": recurrence.get("count"),
            "recurrence_basis": recurrence.get("basis"),
            "source_window": recurrence.get("window"),
        },
    }
    return action


def _compact_command_efficiency_action(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": action.get("action_id"),
        "inefficiency_class": action.get("inefficiency_class"),
        "replacement_route": action.get("replacement_route"),
        "expected_proof": _compact_text(action.get("expected_proof"), max_chars=90),
    }


def _packet_command_efficiency_action(action: dict[str, Any]) -> dict[str, Any]:
    evidence = action.get("evidence") if isinstance(action.get("evidence"), dict) else {}
    return {
        "action_id": action.get("action_id"),
        "source_row_id": action.get("source_row_id"),
        "rank": action.get("rank"),
        "inefficiency_class": action.get("inefficiency_class"),
        "symptom_family": action.get("symptom_family"),
        "old_command_pattern": _compact_text(action.get("old_command_pattern"), max_chars=80),
        "replacement_route": action.get("replacement_route"),
        "replacement_action": _compact_text(action.get("replacement_action"), max_chars=85),
        "expected_proof": _compact_text(action.get("expected_proof"), max_chars=90),
        "seed_rewrite_clause": _compact_text(action.get("seed_rewrite_clause"), max_chars=115),
        "validation_preservation": action.get("validation_preservation"),
        "owner_surface": _compact_text(action.get("owner_surface"), max_chars=90),
        "candidate_mutation": action.get("candidate_mutation"),
        "receipt_needed": list(action.get("receipt_needed") or [])[:3],
        "evidence": {
            "mode": evidence.get("mode"),
            "priority": evidence.get("priority"),
            "recurrence_count": evidence.get("recurrence_count"),
            "recurrence_basis": evidence.get("recurrence_basis"),
            "source_window": evidence.get("source_window"),
        },
    }


def _unique_strings(values: Iterable[Any], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
        if limit is not None and len(unique) >= limit:
            break
    return unique


def _previous_command_efficiency_actions(previous_projection: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(previous_projection, dict):
        return []
    packet = previous_projection.get("command_efficiency_actions")
    if isinstance(packet, dict) and isinstance(packet.get("rows"), list):
        return [row for row in packet["rows"] if isinstance(row, dict)]
    board = previous_projection.get("board") if isinstance(previous_projection.get("board"), dict) else {}
    rows = [row for row in board.get("rows") or [] if isinstance(row, dict)]
    return [
        _command_efficiency_action_from_row(row, ordinal=index)
        for index, row in enumerate(rows)
    ]


def _command_efficiency_replay_delta(
    actions: list[dict[str, Any]],
    *,
    previous_projection: dict[str, Any] | None,
) -> dict[str, Any]:
    previous_actions = _previous_command_efficiency_actions(previous_projection)
    previous_classes = collections.Counter(
        str(action.get("inefficiency_class") or "")
        for action in previous_actions
        if action.get("inefficiency_class")
    )
    rows = []
    for action in actions[:3]:
        evidence = action.get("evidence") if isinstance(action.get("evidence"), dict) else {}
        class_id = str(action.get("inefficiency_class") or "")
        rows.append({
            "trace_session_id": evidence.get("source_window") or "trace_observatory_projection",
            "top_inefficiency_class": class_id,
            "old_command_pattern": _compact_text(action.get("old_command_pattern"), max_chars=95),
            "replacement_route": action.get("replacement_route"),
            "command_count_delta_if_replayed": None,
            "before_class_seen": previous_classes.get(class_id, 0),
            "validation_status_preserved": action.get("validation_preservation"),
            "seed_or_prompt_shelf_clause_updated": _compact_text(action.get("seed_rewrite_clause"), max_chars=135),
            "commit_hash": None,
        })
    return {
        "schema_version": "command_efficiency_replay_delta_v0",
        "status": "compared_to_previous_projection" if previous_actions else "no_previous_projection",
        "comparison_basis": "previous projection vs current emitted rows; command deltas need post-repair replay.",
        "table_columns": [
            "trace/session id",
            "top inefficiency class",
            "old command pattern",
            "replacement route/action",
            "command-count delta if replayed",
            "validation status preserved",
            "seed or prompt-shelf clause updated",
            "commit hash",
        ],
        "rows": rows,
    }


def _attach_command_efficiency_actions(
    projection: dict[str, Any],
    *,
    previous_projection: dict[str, Any] | None,
) -> None:
    board = projection.get("board") if isinstance(projection.get("board"), dict) else {}
    rows = [row for row in board.get("rows") or [] if isinstance(row, dict)]
    actions = [
        _command_efficiency_action_from_row(row, ordinal=index)
        for index, row in enumerate(rows)
    ]
    for row, action in zip(rows, actions):
        row["command_efficiency_action"] = _compact_command_efficiency_action(action)
    board["rows"] = rows
    projection["board"] = board

    top_classes = _unique_strings(
        action.get("inefficiency_class") for action in actions
    )
    replacement_routes = _unique_strings(
        action.get("replacement_route") for action in actions
    )
    seed_clauses = _unique_strings(
        action.get("seed_rewrite_clause") for action in actions
    )
    proof_commands = _unique_strings(
        [
            "./repo-python kernel.py --trace-friction-board --last 30 --write-trace-observatory-projection",
            *replacement_routes,
        ],
        limit=3,
    )
    emitted_actions = actions[:COMMAND_EFFICIENCY_ACTION_EMIT_LIMIT]
    projection["command_efficiency_actions"] = {
        "schema_version": "command_efficiency_action_packet_v0",
        "status": "available" if actions else "empty",
        "purpose": "Route substitutions from Trace Friction Board rows for future autonomous-seed passes.",
        "source_board_schema": str(board.get("schema_version") or "trace_friction_board_v0"),
        "row_count": len(actions),
        "emitted_row_count": len(emitted_actions),
        "omitted_row_count": max(0, len(actions) - len(emitted_actions)),
        "top_inefficiency_classes": top_classes[:5],
        "replacement_routes": replacement_routes[:5],
        "seed_rewrite_clauses": [
            _compact_text(clause, max_chars=135)
            for clause in seed_clauses[:1]
        ],
        "rows": [_packet_command_efficiency_action(action) for action in emitted_actions],
        "before_after_replay": _command_efficiency_replay_delta(
            actions,
            previous_projection=previous_projection,
        ),
        "proof_commands": proof_commands,
        "privacy_boundary": "No raw traces, prompts, operator text, or tool bodies.",
    }


def _trace_friction_recurrence_from_finished(row: dict[str, Any]) -> dict[str, Any]:
    family = str(row.get("symptom_family") or "")
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    if family == "context_pressure":
        return {
            "count": max(
                _coerce_count(evidence.get("max_compactions")),
                _coerce_count(evidence.get("reread_file_count")),
            ),
            "distinct_sessions": None,
            "basis": "max_compactions_or_reread_file_count",
        }
    if family == "ladder_skip":
        return {
            "count": _coerce_count(evidence.get("grep_calls_before_any_nav_flag")),
            "distinct_sessions": None,
            "basis": "grep_before_navigation_count",
        }
    if family == "route_discoverability":
        return {
            "count": _coerce_count(evidence.get("route_miss_candidates")),
            "distinct_sessions": None,
            "basis": "route_miss_candidate_count",
        }
    if family == "rediscovery_hotspot":
        return {
            "count": _coerce_count(evidence.get("score")),
            "distinct_sessions": evidence.get("distinct_sessions"),
            "basis": "rediscovery_score",
        }
    if family == "recovery_friction":
        return {
            "count": _coerce_count(evidence.get("user_interrupt_count")),
            "distinct_sessions": None,
            "basis": "user_interrupt_count",
        }
    if family == "wake_prompt_repetition":
        return {
            "count": _coerce_count(evidence.get("repeated_wake_prompt_clusters")),
            "distinct_sessions": None,
            "basis": "wake_prompt_cluster_count",
        }
    if family == "task_ledger_cap_pressure":
        return {
            "count": _coerce_count(evidence.get("match_count")),
            "distinct_sessions": None,
            "basis": "task_ledger_trace_cap_match_count",
        }
    if family == "experience_friction":
        top = (evidence.get("top_families") or [{}])[0]
        if not isinstance(top, dict):
            top = {}
        return {
            "count": _coerce_count(evidence.get("event_count")),
            "distinct_sessions": top.get("distinct_sessions"),
            "basis": str(evidence.get("episode_family") or "classified_experience_episode"),
        }
    return {"count": 1, "distinct_sessions": None, "basis": "trace_improvement_surface_row"}


def _trace_friction_evidence_refs(row: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    row_id = str(row.get("row_id") or "")
    refs: list[dict[str, Any]] = [
        {
            "source": "trace_improvement_surface" if mode == "finished" else "process_trace_surface",
            "ref": row_id or str(row.get("symptom_family") or "row"),
            "omits_raw_body": True,
        }
    ]
    for cap_id in row.get("cap_refs") or []:
        refs.append({"source": "task_ledger", "ref": str(cap_id), "omits_raw_body": True})
    return refs


def _normalize_finished_trace_row(
    row: dict[str, Any],
    *,
    source_window: str,
) -> dict[str, Any]:
    family = str(row.get("symptom_family") or "unknown")
    normalized_family = "cap_pressure" if family == "task_ledger_cap_pressure" else family
    owner_surface = str(row.get("owner_surface") or "")
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    recurrence = _trace_friction_recurrence_from_finished(row)
    recurrence["window"] = source_window
    board_row = {
        "row_id": str(row.get("row_id") or f"finished:{normalized_family}"),
        "priority": _coerce_count(row.get("priority")),
        "severity": row.get("severity") or "medium",
        "symptom_family": normalized_family,
        "mode": "finished",
        "title": row.get("title") or normalized_family.replace("_", " "),
        "evidence_refs": _trace_friction_evidence_refs(row, mode="finished"),
        "recurrence": recurrence,
        "impact": _TRACE_FRICTION_IMPACT.get(family) or _TRACE_FRICTION_IMPACT.get(normalized_family, []),
        "candidate_owner": {
            "type": _trace_friction_owner_type(owner_surface, family),
            "surface": owner_surface,
        },
        "candidate_mutation": _TRACE_FRICTION_MUTATION.get(family)
        or _TRACE_FRICTION_MUTATION.get(normalized_family)
        or "owner_surface_patch",
        "candidate_patch": _compact_text(row.get("candidate_patch"), max_chars=120),
        "disconfirming_check": _compact_text(
            _TRACE_FRICTION_DISCONFIRMING_CHECK.get(normalized_family)
            or _TRACE_FRICTION_DISCONFIRMING_CHECK.get(family)
            or "A later diagnostics window no longer emits this symptom family.",
            max_chars=150,
        ),
        "next_command": row.get("next_command"),
        "receipt_needed": _trace_friction_receipts(normalized_family, evidence=evidence),
        "source_row_id": row.get("row_id"),
        "cap_refs": list(row.get("cap_refs") or []),
    }
    runtime_focus = evidence.get("runtime_focus")
    if runtime_focus:
        board_row["runtime_focus"] = runtime_focus
    if normalized_family == "context_pressure":
        runtime_commands = _context_pressure_runtime_commands(evidence)
        board_row["runtime_scoped_commands"] = runtime_commands
        board_row["next_command"] = runtime_commands[0]
    if normalized_family == "experience_friction" and evidence.get("episode_family"):
        board_row["episode_family"] = evidence.get("episode_family")
    return board_row


def _process_summary_live_status(
    process_summary: dict[str, Any] | None,
    *,
    runtime_scope: str = "both",
) -> dict[str, Any]:
    runtime_commands = _process_summary_force_commands(runtime_scope)
    if not isinstance(process_summary, dict):
        return {
            "status": "not_loaded",
            "ok": False,
            "next_command": runtime_commands[0],
            "runtime_scoped_commands": runtime_commands,
        }
    freshness = process_summary.get("source_freshness")
    if not isinstance(freshness, dict):
        freshness = {}
    raw_next_command = (
        ((process_summary.get("next") or [{}])[0] or {}).get("command")
        if isinstance(process_summary.get("next"), list)
        else None
    )
    next_command = raw_next_command or runtime_commands[0]
    if _is_bare_process_summary_latest_command(next_command):
        next_command = runtime_commands[0]
    summary = process_summary.get("summary") if isinstance(process_summary.get("summary"), dict) else {}
    return {
        "status": freshness.get("status") or ("available" if "payload" in process_summary else "unknown"),
        "ok": bool(freshness.get("ok")) or bool(process_summary.get("payload")),
        "mode": freshness.get("mode"),
        "generated_at": freshness.get("generated_at"),
        "next_command": next_command,
        "runtime_scoped_commands": runtime_commands,
        "selected_agent": summary.get("agent"),
        "selected_session_id": summary.get("session_id"),
        "warning_count": len(process_summary.get("warnings") or []),
        "warning_preview": _compact_text((process_summary.get("warnings") or [None])[0], max_chars=120)
        if process_summary.get("warnings")
        else None,
    }


def _context_yield_trace_rows(process_bottlenecks: dict[str, Any]) -> list[dict[str, Any]]:
    payload = process_bottlenecks.get("payload") if isinstance(process_bottlenecks.get("payload"), dict) else {}
    packet = (
        payload.get("context_yield_attribution")
        if isinstance(payload.get("context_yield_attribution"), dict)
        else {}
    )
    rows = [row for row in packet.get("rows") or [] if isinstance(row, dict)]
    if not rows:
        return []
    board_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows[:2]):
        motif = str(row.get("motif") or "context_yield")
        counts = (
            row.get("governance_status_counts")
            if isinstance(row.get("governance_status_counts"), dict)
            else {}
        )
        owner_coverage = (
            row.get("owner_coverage")
            if isinstance(row.get("owner_coverage"), dict)
            else {}
        )
        active_bytes = _coerce_count(row.get("actionable_active_bytes")) or _coerce_count(row.get("active_bytes"))
        span_count = _coerce_count(row.get("actionable_span_count")) or _coerce_count(row.get("span_count"))
        actionable_count = max(
            _coerce_count(counts.get("governed_route_available_but_not_used")),
            _coerce_count(counts.get("needs_owner_patch")),
            _coerce_count(counts.get("ungoverned")),
            span_count,
        )
        if active_bytes <= 0 and actionable_count <= 0:
            continue
        existing_route = str(
            row.get("existing_route")
            or ((row.get("steering") or {}).get("replacement_route") if isinstance(row.get("steering"), dict) else "")
            or row.get("owner_surface")
            or "./repo-python kernel.py --process-bottlenecks --force"
        )
        route_gap = str(owner_coverage.get("route_gap") or "")
        score = str(row.get("next_wave_score") or "").lower()
        priority = 89 if score == "high" else 81 if score == "medium" else 73
        if route_gap == "route_available_but_not_used_for_active_examples":
            priority += 1
        title = f"Process context-yield motif '{motif}' has an existing compact route"
        board_rows.append({
            "row_id": f"live:context_yield:{hashlib.sha256(motif.encode('utf-8')).hexdigest()[:10]}",
            "priority": priority - index,
            "severity": "medium",
            "symptom_family": "context_yield",
            "mode": "live",
            "title": title,
            "evidence_refs": [
                {
                    "source": "process_bottlenecks.context_yield_attribution",
                    "ref": motif,
                    "active_bytes": row.get("active_bytes"),
                    "actionable_active_bytes": row.get("actionable_active_bytes"),
                    "span_count": row.get("span_count"),
                    "route_gap": route_gap or None,
                    "omits_raw_body": True,
                }
            ],
            "recurrence": {
                "count": active_bytes or actionable_count,
                "distinct_sessions": row.get("session_count") or (process_bottlenecks.get("summary") or {}).get("session_count"),
                "window": "live:process_bottlenecks.context_yield_attribution",
                "basis": "context_yield_active_bytes",
                "motif": motif,
            },
            "impact": _TRACE_FRICTION_IMPACT["context_yield"],
            "candidate_owner": {
                "type": "command_card",
                "surface": str(row.get("owner_surface") or existing_route),
            },
            "candidate_mutation": _TRACE_FRICTION_MUTATION["context_yield"],
            "candidate_patch": _compact_text(
                row.get("candidate_patch")
                or "Use the existing compact route before opening raw bodies or re-callable tool results.",
                max_chars=120,
            ),
            "disconfirming_check": _compact_text(
                row.get("disconfirming_check")
                or _TRACE_FRICTION_DISCONFIRMING_CHECK["context_yield"],
                max_chars=150,
            ),
            "next_command": existing_route,
            "receipt_needed": _trace_friction_receipts("context_yield"),
            "cap_refs": [],
        })
    return board_rows


_ROUTE_LEASE_CHURN_SIGNAL_IDS = (
    "broad_route_repeated_without_new_authority_question",
    "full_output_kernel_bloat",
    "second_kernel_call_before_direct_action",
    "kernel_call_for_known_path_question",
)


def _process_summary_audit_summary(process_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(process_summary, dict):
        return {}
    payload = process_summary.get("payload") if isinstance(process_summary.get("payload"), dict) else {}
    payload_audit = payload.get("audit_summary") if isinstance(payload.get("audit_summary"), dict) else {}
    summary = process_summary.get("summary") if isinstance(process_summary.get("summary"), dict) else {}
    candidates: list[Any] = [
        payload_audit.get("summary"),
        process_summary.get("audit_summary"),
        summary.get("audit_summary"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return {}


def _process_summary_route_lease_counts(process_summary: dict[str, Any] | None) -> dict[str, int]:
    audit_summary = _process_summary_audit_summary(process_summary)
    raw_counts = audit_summary.get("route_lease_mode_control_counts")
    if not isinstance(raw_counts, dict):
        return {}
    counts: dict[str, int] = {}
    for key, value in raw_counts.items():
        count = _coerce_count(value)
        if count > 0:
            counts[str(key)] = count
    return counts


def _route_lease_trace_rows(
    process_summary: dict[str, Any] | None,
    *,
    runtime_scope: str,
) -> list[dict[str, Any]]:
    counts = _process_summary_route_lease_counts(process_summary)
    active_counts = {
        signal_id: counts[signal_id]
        for signal_id in _ROUTE_LEASE_CHURN_SIGNAL_IDS
        if counts.get(signal_id, 0) > 0
    }
    if not active_counts:
        return []

    audit_summary = _process_summary_audit_summary(process_summary)
    total_count = sum(active_counts.values())
    top_signal, top_count = max(active_counts.items(), key=lambda item: (item[1], item[0]))
    runtime_commands = _process_summary_force_commands(runtime_scope)
    distinct_sessions = (
        audit_summary.get("route_lease_warning_session_count")
        or audit_summary.get("route_lease_session_count")
    )
    priority = min(91, 84 + max(1, total_count // 20))
    row_id_seed = "|".join(f"{key}:{value}" for key, value in sorted(active_counts.items()))
    return [
        {
            "row_id": f"live:route_lease_churn:{hashlib.sha256(row_id_seed.encode('utf-8')).hexdigest()[:10]}",
            "priority": priority,
            "severity": "medium",
            "symptom_family": "route_lease_churn",
            "mode": "live",
            "title": "Process summary shows repeated broad route use after entry lease",
            "evidence_refs": [
                {
                    "source": "process_summary.audit_summary.route_lease_mode_control_counts",
                    "ref": top_signal,
                    "count": top_count,
                    "signal_counts": dict(sorted(active_counts.items())),
                    "route_lease_warning_session_count": audit_summary.get("route_lease_warning_session_count"),
                    "route_lease_session_count": audit_summary.get("route_lease_session_count"),
                    "omits_raw_body": True,
                }
            ],
            "recurrence": {
                "count": total_count,
                "distinct_sessions": distinct_sessions,
                "window": "live:process_summary.audit_summary",
                "basis": "route_lease_warning_signal_count",
                "top_signal": top_signal,
            },
            "impact": _TRACE_FRICTION_IMPACT["route_lease_churn"],
            "candidate_owner": {
                "type": "command_card",
                "surface": "system/lib/agent_execution_trace.py + ./repo-python kernel.py --process-summary <session_id|claude:latest|codex:latest>",
            },
            "candidate_mutation": _TRACE_FRICTION_MUTATION["route_lease_churn"],
            "candidate_patch": _compact_text(
                "Replace repeated broad route calls with a runtime-scoped process-summary check, "
                "then consume the entry lease through the selected owner route or direct local action.",
                max_chars=120,
            ),
            "disconfirming_check": _compact_text(
                _TRACE_FRICTION_DISCONFIRMING_CHECK["route_lease_churn"],
                max_chars=150,
            ),
            "next_command": runtime_commands[0],
            "runtime_scoped_commands": runtime_commands,
            "receipt_needed": _trace_friction_receipts("route_lease_churn"),
            "cap_refs": [],
        }
    ]


def _live_process_trace_rows(
    *,
    process_summary: dict[str, Any] | None,
    process_bottlenecks: dict[str, Any] | None,
    runtime_scope: str = "both",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    live_status = _process_summary_live_status(process_summary, runtime_scope=runtime_scope)
    if not live_status.get("ok"):
        rows.append({
            "row_id": "live:evidence_gap:process_summary",
            "priority": 82,
            "severity": "medium",
            "symptom_family": "evidence_gap",
            "mode": "live",
            "title": "Live process-summary read model is unavailable or stale for current trace selection",
            "evidence_refs": [
                {
                    "source": "process_summary",
                    "ref": "source_freshness",
                    "status": live_status.get("status"),
                    "omits_raw_body": True,
                }
            ],
            "recurrence": {
                "count": 1,
                "distinct_sessions": None,
                "window": "live:latest",
                "basis": "process_summary_source_freshness",
            },
            "impact": _TRACE_FRICTION_IMPACT["evidence_gap"],
            "candidate_owner": {
                "type": "standard",
                "surface": "codex/standards/std_agent_execution_trace.json + codex/hologram/process/summary.json",
            },
            "candidate_mutation": "evaluator_guard",
            "candidate_patch": "Refresh or force-live the process summary before using live trace rows as source-patch authority.",
            "disconfirming_check": _compact_text(
                _TRACE_FRICTION_DISCONFIRMING_CHECK["evidence_gap"],
                max_chars=150,
            ),
            "next_command": live_status.get("next_command") or "./repo-python kernel.py --process-summary latest --force",
            "receipt_needed": _trace_friction_receipts("evidence_gap"),
            "cap_refs": [],
        })

    rows.extend(_route_lease_trace_rows(process_summary, runtime_scope=runtime_scope))

    if not isinstance(process_bottlenecks, dict):
        return rows
    decision = process_bottlenecks.get("decision_authority")
    if not isinstance(decision, dict):
        decision = {}
    source_freshness = process_bottlenecks.get("source_freshness")
    if not isinstance(source_freshness, dict):
        source_freshness = {}
    if str(decision.get("status") or "").startswith("advisory"):
        rows.append({
            "row_id": "live:evidence_gap:process_bottlenecks_advisory",
            "priority": 70,
            "severity": "medium",
            "symptom_family": "evidence_gap",
            "mode": "live",
            "title": "Live bottleneck rows are advisory until force-live refresh",
            "evidence_refs": [
                {
                    "source": "process_bottlenecks",
                    "ref": "decision_authority",
                    "status": decision.get("status"),
                    "omits_raw_body": True,
                }
            ],
            "recurrence": {
                "count": _coerce_count((process_bottlenecks.get("summary") or {}).get("action_kind_count")),
                "distinct_sessions": (process_bottlenecks.get("summary") or {}).get("session_count"),
                "window": "live:process_bottlenecks",
                "basis": "advisory_bottleneck_action_kind_count",
            },
            "impact": _TRACE_FRICTION_IMPACT["evidence_gap"],
            "candidate_owner": {"type": "command_card", "surface": "process_bottlenecks"},
            "candidate_mutation": "evaluator_guard",
            "candidate_patch": "Use the stale rows as ranking seed only; force-live before selecting a source patch target.",
            "disconfirming_check": _compact_text(
                _TRACE_FRICTION_DISCONFIRMING_CHECK["evidence_gap"],
                max_chars=150,
            ),
            "next_command": decision.get("authoritative_decision_command")
            or source_freshness.get("force_live_command")
            or "./repo-python kernel.py --process-bottlenecks --force",
            "receipt_needed": _trace_friction_receipts("evidence_gap"),
            "cap_refs": [],
        })
        return rows

    rows.extend(_context_yield_trace_rows(process_bottlenecks))

    bottleneck_rows = [
        row
        for row in (((process_bottlenecks.get("payload") or {}).get("top_bottlenecks")) or [])
        if isinstance(row, dict)
    ][:3]
    if bottleneck_rows:
        title = "Process bottleneck action kinds are over threshold"
        action_kinds = [str(row.get("action_kind") or "unknown_action") for row in bottleneck_rows]
        top_bottleneck = bottleneck_rows[0]
        repair_hints = top_bottleneck.get("repair_hints")
        preferred_next = (
            repair_hints[0].get("preferred_next")
            if isinstance(repair_hints, list)
            and repair_hints
            and isinstance(repair_hints[0], dict)
            else "Inspect the action-kind owner surface and add a compact status or targeted command path."
        )
        runtime_next_commands = (
            _process_summary_force_commands(runtime_scope)
            if _process_summary_hint_needs_runtime_scope(preferred_next)
            else []
        )
        live_stall_row = {
            "row_id": f"live:live_stall:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:10]}",
            "priority": 78 if any(_coerce_count(row.get("slow_count")) for row in bottleneck_rows) else 66,
            "severity": "medium",
            "symptom_family": "live_stall",
            "mode": "live",
            "title": title,
            "evidence_refs": [
                {
                    "source": "process_bottlenecks",
                    "ref": str(row.get("action_kind") or "unknown_action"),
                    "p95_ms": row.get("p95_ms"),
                    "count": row.get("count"),
                    "omits_raw_body": True,
                }
                for row in bottleneck_rows
            ],
            "recurrence": {
                "count": sum(_coerce_count(row.get("count")) for row in bottleneck_rows),
                "distinct_sessions": (process_bottlenecks.get("summary") or {}).get("session_count"),
                "window": "live:process_bottlenecks",
                "basis": "top_action_kind_count_sum",
                "action_kinds": action_kinds,
            },
            "impact": _TRACE_FRICTION_IMPACT["live_stall"],
            "candidate_owner": {"type": "command_card", "surface": "process_bottlenecks"},
            "candidate_mutation": "evaluator_guard",
            "candidate_patch": _compact_text(
                "Use a runtime-scoped process summary before full process-trace drilldown."
                if runtime_next_commands
                else preferred_next,
                max_chars=120,
            ),
            "disconfirming_check": _compact_text(
                _TRACE_FRICTION_DISCONFIRMING_CHECK["live_stall"],
                max_chars=150,
            ),
            "next_command": (
                runtime_next_commands[0]
                if runtime_next_commands
                else decision.get("authoritative_decision_command")
                or "./repo-python kernel.py --process-bottlenecks --force"
            ),
            "receipt_needed": _trace_friction_receipts("live_stall"),
            "cap_refs": [],
        }
        if runtime_next_commands:
            live_stall_row["runtime_scoped_commands"] = runtime_next_commands
        rows.append(live_stall_row)
    return rows


def _work_ledger_trace_rows(work_ledger_claims: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(work_ledger_claims, dict):
        return []
    counts = work_ledger_claims.get("counts") if isinstance(work_ledger_claims.get("counts"), dict) else {}
    collisions = _coerce_count(counts.get("claim_collisions"))
    orphaned = _coerce_count(counts.get("orphaned_active_sessions"))
    if collisions <= 0 and orphaned <= 0:
        return []
    return [
        {
            "row_id": "live:handoff_loss:work_ledger_claims",
            "priority": 79 if collisions else 72,
            "severity": "medium",
            "symptom_family": "handoff_loss",
            "mode": "live",
            "title": "Work Ledger live claims show collision or orphan pressure relevant to trace handoff",
            "evidence_refs": [
                {
                    "source": "work_ledger_active_claims_snapshot",
                    "ref": "counts",
                    "claim_collisions": collisions,
                    "orphaned_active_sessions": orphaned,
                    "omits_raw_body": True,
                }
            ],
            "recurrence": {
                "count": collisions or orphaned,
                "distinct_sessions": counts.get("effective_active_sessions"),
                "window": "live:work_ledger_claims",
                "basis": "claim_collision_or_orphan_count",
            },
            "impact": _TRACE_FRICTION_IMPACT["handoff_loss"],
            "candidate_owner": {
                "type": "WorkItem/CAP",
                "surface": "state/work_ledger/active_claims_snapshot.json",
            },
            "candidate_mutation": "evaluator_guard",
            "candidate_patch": "Resolve collisions/orphans before treating trace-to-owner rows as landing authority.",
            "disconfirming_check": _compact_text(
                _TRACE_FRICTION_DISCONFIRMING_CHECK["handoff_loss"],
                max_chars=150,
            ),
            "next_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 20 --cards-only",
            "receipt_needed": _trace_friction_receipts("handoff_loss"),
            "cap_refs": [],
        }
    ]


def _compact_work_ledger_claims(work_ledger_claims: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(work_ledger_claims, dict):
        return {
            "status": "not_loaded",
            "next_command": WORK_LEDGER_SEED_SPEED_COMMAND,
        }
    counts = work_ledger_claims.get("counts") if isinstance(work_ledger_claims.get("counts"), dict) else {}
    return {
        "status": work_ledger_claims.get("status") or "available",
        "generated_at": work_ledger_claims.get("generated_at"),
        "counts": {
            "active_claims": counts.get("active_claims"),
            "claim_collisions": counts.get("claim_collisions"),
            "effective_active_sessions": counts.get("effective_active_sessions"),
            "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
        },
        "refresh_command": work_ledger_claims.get("refresh_command")
        or "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 20 --cards-only",
    }


def _trace_projection_delta(
    current_rows: list[dict[str, Any]],
    previous_projection: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(previous_projection, dict):
        return _trace_projection_delta_empty("no_previous_projection")
    previous_rows = (((previous_projection.get("board") or {}).get("rows")) or [])
    previous_by_family: dict[str, int] = {}
    for row in previous_rows:
        if isinstance(row, dict):
            previous_by_family[str(row.get("symptom_family") or "")] = max(
                previous_by_family.get(str(row.get("symptom_family") or ""), 0),
                _coerce_count(row.get("priority")),
            )
    current_by_family: dict[str, int] = {}
    for row in current_rows:
        current_by_family[str(row.get("symptom_family") or "")] = max(
            current_by_family.get(str(row.get("symptom_family") or ""), 0),
            _coerce_count(row.get("priority")),
        )
    new_or_worse = [
        family
        for family, priority in sorted(current_by_family.items())
        if family and (family not in previous_by_family or priority > previous_by_family[family] + 5)
    ]
    retired = [
        family
        for family in sorted(previous_by_family)
        if family and family not in current_by_family
    ]
    return {
        "status": "compared",
        "new_or_worsening_symptoms": new_or_worse,
        "retired_symptoms": retired,
        "recurring_symptoms": [
            family
            for family in sorted(current_by_family)
            if family and family in previous_by_family
        ],
    }


def _trace_projection_delta_empty(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "new_or_worsening_symptoms": [],
        "retired_symptoms": [],
        "recurring_symptoms": [],
    }


def _row_raw_body_findings(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def visit(value: Any, path: list[str]) -> None:
        if len(findings) >= 5:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                key_norm = key_text.lower()
                next_path = [*path, key_text]
                if key_norm in _TRACE_BOARD_RAW_BODY_FIELD_KEYS:
                    findings.append({
                        "path": ".".join(next_path),
                        "reason": "raw_body_field_key",
                    })
                    if len(findings) >= 5:
                        return
                visit(child, next_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, [*path, str(index)])
                if len(findings) >= 5:
                    return

    for index, row in enumerate(rows):
        visit(row, ["board", "rows", str(index)])
        if len(findings) >= 5:
            break
    return findings


def evaluate_trace_board_quality(projection: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether the Trace Friction Board is actionable, safe, and fresh."""
    board = projection.get("board") if isinstance(projection.get("board"), dict) else {}
    rows = [row for row in board.get("rows") or [] if isinstance(row, dict)]
    top_row = rows[0] if rows else {}
    compactness = projection.get("compactness_metrics") if isinstance(projection.get("compactness_metrics"), dict) else {}
    source_windows = projection.get("source_windows") if isinstance(projection.get("source_windows"), dict) else {}
    live = source_windows.get("live") if isinstance(source_windows.get("live"), dict) else {}
    process_summary = live.get("process_summary") if isinstance(live.get("process_summary"), dict) else {}
    process_bottlenecks = live.get("process_bottlenecks") if isinstance(live.get("process_bottlenecks"), dict) else {}

    missing_top_fields = [
        field
        for field in _TRACE_BOARD_REQUIRED_ROW_FIELDS
        if not top_row.get(field)
    ]
    top_owner = top_row.get("candidate_owner") if isinstance(top_row.get("candidate_owner"), dict) else {}
    if not top_owner.get("surface"):
        missing_top_fields.append("candidate_owner.surface")

    invalid_specific_rows = [
        str(row.get("row_id") or index)
        for index, row in enumerate(rows)
        if row.get("symptom_family") not in _TRACE_FRICTION_IMPACT
        or not (
            (row.get("candidate_owner") if isinstance(row.get("candidate_owner"), dict) else {})
        ).get("surface")
        or not row.get("next_command")
    ]

    privacy_receipts_text = json.dumps(projection.get("privacy_omission_receipts") or [], sort_keys=True).lower()
    privacy_receipts_present = all(
        token in privacy_receipts_text
        for token in ("raw session bodies", "prompt bodies", "tool stdout/stderr")
    )
    evidence_refs = [
        ref
        for row in rows
        for ref in (row.get("evidence_refs") or [])
        if isinstance(ref, dict)
    ]
    unsafe_evidence_refs = [
        str(ref.get("ref") or ref.get("source") or index)
        for index, ref in enumerate(evidence_refs)
        if ref.get("omits_raw_body") is not True
    ]
    raw_body_findings = _row_raw_body_findings(rows)

    summary_ok = bool(process_summary.get("ok"))
    bottleneck_decision = str(process_bottlenecks.get("decision_authority") or "")
    bottleneck_advisory = bottleneck_decision.startswith("advisory")
    missing_summary_gap = not summary_ok and not any(
        row.get("symptom_family") == "evidence_gap"
        and any(ref.get("source") == "process_summary" for ref in (row.get("evidence_refs") or []))
        for row in rows
    )
    stale_bottleneck_authority_rows = [
        str(row.get("row_id") or index)
        for index, row in enumerate(rows)
        if bottleneck_advisory
        and row.get("mode") == "live"
        and row.get("symptom_family") != "evidence_gap"
        and any(ref.get("source") == "process_bottlenecks" for ref in (row.get("evidence_refs") or []))
    ]

    cap_rows = [row for row in rows if row.get("symptom_family") == "cap_pressure"]
    unsafe_cap_rows = [
        str(row.get("row_id") or index)
        for index, row in enumerate(cap_rows)
        if row.get("candidate_mutation") != "candidate_WorkItem"
        or "cap_shape_or_link_receipt" not in (row.get("receipt_needed") or [])
        or not row.get("cap_refs")
    ]
    ambiguous_live_commands = [
        str(row.get("row_id") or index)
        for index, row in enumerate(rows)
        if row.get("mode") == "live"
        and _is_bare_process_summary_latest_command(row.get("next_command"))
    ]

    ratio = compactness.get("projection_to_summary_ratio")
    compactness_warn = (
        isinstance(ratio, (int, float))
        and ratio > TRACE_OBSERVATORY_SUMMARY_RATIO_LIMIT
    )
    emitted_count = _coerce_count(board.get("emitted_row_count"))
    row_limit_fail = emitted_count > TRACE_OBSERVATORY_EMIT_LIMIT or len(rows) > TRACE_OBSERVATORY_EMIT_LIMIT
    recurrence_status = str((projection.get("recurrence_comparison") or {}).get("status") or "")
    recurrence_warn = recurrence_status in {"", "no_previous_projection"}

    checks = {
        "top_row_actionable": _status_from_fail_warn(fail=not rows or bool(missing_top_fields)),
        "row_specificity": _status_from_fail_warn(fail=bool(invalid_specific_rows)),
        "privacy_safe": _status_from_fail_warn(
            fail=bool(raw_body_findings or unsafe_evidence_refs) or not privacy_receipts_present
        ),
        "freshness_authority": _status_from_fail_warn(
            fail=bool(missing_summary_gap or stale_bottleneck_authority_rows or ambiguous_live_commands)
        ),
        "row_limit": _status_from_fail_warn(fail=row_limit_fail),
        "compactness": _status_from_fail_warn(warn=compactness_warn),
        "cap_routing": _status_from_fail_warn(fail=bool(unsafe_cap_rows)),
        "retirement_tracking": _status_from_fail_warn(warn=recurrence_warn),
    }
    status = "fail" if "fail" in checks.values() else "warn" if "warn" in checks.values() else "pass"

    return {
        "schema_version": "trace_board_quality_gate_v0",
        "status": status,
        "checks": checks,
        "thresholds": {
            "emitted_row_limit": TRACE_OBSERVATORY_EMIT_LIMIT,
            "projection_to_summary_ratio_max": TRACE_OBSERVATORY_SUMMARY_RATIO_LIMIT,
        },
        "findings": {
            "missing_top_fields": missing_top_fields[:5],
            "invalid_specific_rows": invalid_specific_rows[:5],
            "raw_body_findings": raw_body_findings,
            "unsafe_evidence_refs": unsafe_evidence_refs[:5],
            "stale_live_authority_rows": stale_bottleneck_authority_rows[:5],
            "ambiguous_live_commands": ambiguous_live_commands[:5],
            "unsafe_cap_rows": unsafe_cap_rows[:5],
        },
        "retirement_delta": {
            "status": recurrence_status or "unknown",
            "new_or_worsening": projection.get("new_or_worsening_symptoms") or [],
            "retired": projection.get("retired_symptoms") or [],
            "recurring": projection.get("recurring_symptoms") or [],
        },
    }


def _set_trace_board_emitted_rows(
    projection: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    emit_limit: int,
) -> None:
    board = projection.get("board") if isinstance(projection.get("board"), dict) else {}
    emitted = min(len(rows), emit_limit)
    selected_rows = _select_trace_board_rows(rows, emitted)
    selected_ids = {str(row.get("row_id") or index) for index, row in enumerate(selected_rows)}
    omitted_rows = [
        row
        for index, row in enumerate(rows)
        if str(row.get("row_id") or index) not in selected_ids
    ]
    board.update({
        "row_count": len(rows),
        "emitted_row_count": len(selected_rows),
        "omitted_row_count": len(omitted_rows),
        "omitted_symptom_families": [
            row.get("symptom_family")
            for row in omitted_rows
            if row.get("symptom_family")
        ],
        "rows": selected_rows,
    })
    projection["board"] = board


def _select_trace_board_rows(rows: list[dict[str, Any]], emit_limit: int) -> list[dict[str, Any]]:
    selected = list(rows[:emit_limit])
    if emit_limit <= 0:
        return selected
    required_gap = next(
        (
            row
            for row in rows
            if row.get("symptom_family") == "evidence_gap"
            and row.get("mode") == "live"
        ),
        None,
    )
    if not required_gap:
        return selected
    required_id = str(required_gap.get("row_id") or "")
    if any(str(row.get("row_id") or "") == required_id for row in selected):
        return selected
    if emit_limit == 1:
        return [required_gap]
    return [*selected[: emit_limit - 1], required_gap]


def _trace_board_min_emit_limit(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    has_required_gap = any(
        row.get("symptom_family") == "evidence_gap" and row.get("mode") == "live"
        for row in rows
    )
    if has_required_gap and rows[0].get("symptom_family") != "evidence_gap":
        return min(len(rows), 2)
    return 1


def _update_trace_compactness_metrics(
    projection: dict[str, Any],
    *,
    source_summary_bytes: int,
    full_report_bytes: int,
    top_row_preserved: bool,
    source_summary_byte_reduction_percent: Any,
) -> None:
    projection_bytes = _json_estimated_bytes(projection)
    compactness_basis = full_report_bytes or source_summary_bytes
    projection["compactness_metrics"] = {
        "source_summary_estimated_bytes": source_summary_bytes,
        "source_full_report_estimated_bytes": full_report_bytes or None,
        "projection_estimated_bytes": projection_bytes,
        "projection_to_summary_ratio": round(projection_bytes / source_summary_bytes, 4)
        if source_summary_bytes
        else None,
        "projection_to_full_ratio": round(projection_bytes / compactness_basis, 4)
        if compactness_basis
        else None,
        "source_summary_byte_reduction_percent": source_summary_byte_reduction_percent,
        "top_row_preserved": top_row_preserved,
    }
    projection["compactness_metrics"]["compactness_gate"] = (
        "pass"
        if top_row_preserved
        and (
            not source_summary_bytes
            or projection["compactness_metrics"]["projection_to_summary_ratio"] <= TRACE_OBSERVATORY_SUMMARY_RATIO_LIMIT
        )
        else "warn"
    )


def _refresh_trace_quality_and_compactness(
    projection: dict[str, Any],
    *,
    source_summary_bytes: int,
    full_report_bytes: int,
    top_row_preserved: bool,
    source_summary_byte_reduction_percent: Any,
) -> None:
    _update_trace_compactness_metrics(
        projection,
        source_summary_bytes=source_summary_bytes,
        full_report_bytes=full_report_bytes,
        top_row_preserved=top_row_preserved,
        source_summary_byte_reduction_percent=source_summary_byte_reduction_percent,
    )
    projection["trace_board_quality_gate"] = evaluate_trace_board_quality(projection)


def build_trace_observatory_projection(
    *,
    finished_summary: dict[str, Any],
    process_summary: dict[str, Any] | None = None,
    process_bottlenecks: dict[str, Any] | None = None,
    work_ledger_claims: dict[str, Any] | None = None,
    previous_projection: dict[str, Any] | None = None,
    runtime_scope: str = "both",
    last: int = 30,
) -> dict[str, Any]:
    """Build the read-only Trace Friction Board projection.

    The projection is a selector over finished diagnostics, live process state,
    Task Ledger CAP alignment, and Work Ledger claim context. It carries compact
    evidence pointers and receipt requirements, never raw trace bodies.
    """
    trace_surface = (
        finished_summary.get("trace_improvement_surface")
        if isinstance(finished_summary.get("trace_improvement_surface"), dict)
        else {}
    )
    finished_rows = [
        _normalize_finished_trace_row(row, source_window=f"finished:last_{last}")
        for row in trace_surface.get("rows") or []
        if isinstance(row, dict)
    ]
    live_rows = _live_process_trace_rows(
        process_summary=process_summary,
        process_bottlenecks=process_bottlenecks,
        runtime_scope=runtime_scope,
    )
    work_rows = _work_ledger_trace_rows(work_ledger_claims)
    rows = finished_rows + live_rows + work_rows
    rows.sort(key=lambda row: int(row.get("priority") or 0), reverse=True)

    cap_refs = sorted({
        str(cap)
        for row in rows
        for cap in (row.get("cap_refs") or [])
        if cap
    })
    owner_candidates = []
    seen_owners: set[tuple[str, str]] = set()
    for row in rows:
        owner = row.get("candidate_owner") if isinstance(row.get("candidate_owner"), dict) else {}
        key = (str(owner.get("type") or ""), str(owner.get("surface") or ""))
        if key in seen_owners or not key[1]:
            continue
        seen_owners.add(key)
        owner_candidates.append({"type": key[0], "surface": key[1]})

    process_summary_status = _process_summary_live_status(process_summary, runtime_scope=runtime_scope)
    process_bottleneck_status = {}
    if isinstance(process_bottlenecks, dict):
        process_bottleneck_status = {
            "status": (process_bottlenecks.get("source_freshness") or {}).get("status"),
            "decision_authority": (process_bottlenecks.get("decision_authority") or {}).get("status"),
            "session_count": (process_bottlenecks.get("summary") or {}).get("session_count"),
            "force_live_command": (process_bottlenecks.get("decision_authority") or {}).get("authoritative_decision_command")
            or "./repo-python kernel.py --process-bottlenecks --force",
        }
    cap_alignment = trace_surface.get("cap_alignment") if isinstance(trace_surface.get("cap_alignment"), dict) else {}
    summary_first = finished_summary.get("summary_first_sufficiency")
    if not isinstance(summary_first, dict):
        summary_first = {}

    projection: dict[str, Any] = {
        "kind": "trace_observatory_projection",
        "schema_version": "trace_observatory_projection_v0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "Compact symptom-to-owner action selection for live and finished agent traces.",
        "authority_boundary": (
            "Generated projection over diagnostics/process/ledger surfaces. Raw provider traces, "
            "prompt bodies, tool outputs, and operator text remain behind owner drilldowns."
        ),
        "source_windows": {
            "finished": {
                "surface": "./repo-python kernel.py --session-diagnostics --lens all --last "
                f"{last} --store both --json --diagnostics-summary",
                "source_kind": finished_summary.get("source_kind"),
                "window": finished_summary.get("window"),
                "counts": finished_summary.get("counts"),
                "row_count": len(finished_rows),
            },
            "live": {
                "summary_surface": _process_summary_cached_command(runtime_scope),
                "runtime_scoped_summary_surfaces": _process_summary_force_commands(runtime_scope),
                "readiness_contract": _live_trace_readiness_contract(runtime_scope),
                "bottleneck_surface": "./repo-python kernel.py --process-bottlenecks",
                "process_summary": process_summary_status,
                "process_bottlenecks": process_bottleneck_status or {"status": "not_loaded"},
            },
            "cap_views": {
                "status": cap_alignment.get("status"),
                "view_ids": cap_alignment.get("view_ids"),
                "match_count": cap_alignment.get("match_count"),
                "top_ids": cap_alignment.get("top_ids") or [],
                "next_command": cap_alignment.get("next_command"),
            },
            "work_ledger_claims": _compact_work_ledger_claims(work_ledger_claims),
        },
        "board": {
            "schema_version": "trace_friction_board_v0",
            "status": "available",
        },
        "top_symptom_families": [
            row.get("symptom_family") for row in rows[:5] if row.get("symptom_family")
        ],
        "cap_refs": cap_refs,
        "owner_candidates": owner_candidates[:5],
        "drilldown_commands": [
            command
            for command in [
                "./repo-python kernel.py --trace-friction-board --last 30",
                "./repo-python kernel.py --session-diagnostics --lens all --last 30 --store both --json --diagnostics-summary",
                "./repo-python kernel.py --process-bottlenecks --force",
                cap_alignment.get("next_command"),
                "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 20 --cards-only",
            ]
            if command
        ],
        "privacy_omission_receipts": [
            {
                "omitted": "raw session bodies",
                "reason": "Board rows carry counts, ids, paths, and owner commands only.",
            },
            {
                "omitted": "prompt bodies and operator text",
                "reason": "Task-intent and CAP coupling use explicit projection ids, not prompt mining.",
            },
            {
                "omitted": "tool stdout/stderr bodies and process span bodies",
                "reason": "Live rows use process summary/bottleneck metadata and force-live receipts.",
            },
        ],
        "validation_receipts": [
            {
                "receipt": "finished_summary_built",
                "status": "available" if finished_summary else "missing",
                "command": "./repo-python kernel.py --session-diagnostics --lens all --last 30 --store both --json --diagnostics-summary",
            },
            {
                "receipt": "live_process_summary_checked",
                "status": process_summary_status.get("status"),
                "command": _primary_process_summary_force_command(runtime_scope),
            },
            {
                "receipt": "work_ledger_claim_context_checked",
                "status": _compact_work_ledger_claims(work_ledger_claims).get("status"),
                "command": WORK_LEDGER_CLAIM_CARDS_COMMAND,
            },
        ],
    }
    delta = _trace_projection_delta(rows, previous_projection)
    projection.update({
        "new_or_worsening_symptoms": delta["new_or_worsening_symptoms"],
        "retired_symptoms": delta["retired_symptoms"],
        "recurring_symptoms": delta["recurring_symptoms"],
        "recurrence_comparison": {"status": delta["status"]},
    })

    source_summary_bytes = _json_estimated_bytes(finished_summary)
    full_report_bytes = _coerce_count(summary_first.get("full_report_estimated_bytes"))
    top_row_preserved = (
        rows[0].get("symptom_family")
        == (trace_surface.get("summary") or {}).get("top_symptom_family")
        if rows
        else True
    )
    emit_limit = TRACE_OBSERVATORY_EMIT_LIMIT
    _set_trace_board_emitted_rows(projection, rows, emit_limit=emit_limit)
    _refresh_trace_quality_and_compactness(
        projection,
        source_summary_bytes=source_summary_bytes,
        full_report_bytes=full_report_bytes,
        top_row_preserved=top_row_preserved,
        source_summary_byte_reduction_percent=summary_first.get("byte_reduction_percent"),
    )
    min_emit_limit = _trace_board_min_emit_limit(rows)
    while emit_limit > min_emit_limit:
        ratio = projection.get("compactness_metrics", {}).get("projection_to_summary_ratio")
        if not isinstance(ratio, (int, float)) or ratio <= TRACE_OBSERVATORY_SUMMARY_RATIO_LIMIT:
            break
        emit_limit -= 1
        _set_trace_board_emitted_rows(projection, rows, emit_limit=emit_limit)
        _refresh_trace_quality_and_compactness(
            projection,
            source_summary_bytes=source_summary_bytes,
            full_report_bytes=full_report_bytes,
            top_row_preserved=top_row_preserved,
            source_summary_byte_reduction_percent=summary_first.get("byte_reduction_percent"),
        )
    _attach_command_efficiency_actions(
        projection,
        previous_projection=previous_projection,
    )
    _refresh_trace_quality_and_compactness(
        projection,
        source_summary_bytes=source_summary_bytes,
        full_report_bytes=full_report_bytes,
        top_row_preserved=top_row_preserved,
        source_summary_byte_reduction_percent=summary_first.get("byte_reduction_percent"),
    )
    while emit_limit > min_emit_limit:
        ratio = projection.get("compactness_metrics", {}).get("projection_to_summary_ratio")
        if not isinstance(ratio, (int, float)) or ratio <= TRACE_OBSERVATORY_SUMMARY_RATIO_LIMIT:
            break
        emit_limit -= 1
        _set_trace_board_emitted_rows(projection, rows, emit_limit=emit_limit)
        _attach_command_efficiency_actions(
            projection,
            previous_projection=previous_projection,
        )
        _refresh_trace_quality_and_compactness(
            projection,
            source_summary_bytes=source_summary_bytes,
            full_report_bytes=full_report_bytes,
            top_row_preserved=top_row_preserved,
            source_summary_byte_reduction_percent=summary_first.get("byte_reduction_percent"),
        )
    return projection


def summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    """Return a compact diagnostics packet for context-preserving self-inspection."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    window = summary.get("window") if isinstance(summary.get("window"), dict) else {}
    store_counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}

    histogram = _safe_lens(report, "histogram")
    hotspots = _safe_lens(report, "hotspots")
    ladder = _safe_lens(report, "ladder-skip")
    latency = _safe_lens(report, "latency")
    wake_prompts = _safe_lens(report, "wake-prompts")
    route_misses = _safe_lens(report, "route-misses")
    errors = _safe_lens(report, "errors")
    experience_frictions = _safe_lens(report, "experience-frictions")
    host_pressure_surface = (
        report.get("host_pressure_surface")
        if isinstance(report.get("host_pressure_surface"), dict)
        else {}
    )
    host_pressure_summary = (
        host_pressure_surface.get("summary")
        if isinstance(host_pressure_surface.get("summary"), dict)
        else {}
    )
    host_pressure_envelope = (
        host_pressure_surface.get("codex_parallelism_envelope")
        if isinstance(host_pressure_surface.get("codex_parallelism_envelope"), dict)
        else {}
    )
    host_pressure_activation = (
        host_pressure_surface.get("host_pressure_activation_receipt")
        if isinstance(host_pressure_surface.get("host_pressure_activation_receipt"), dict)
        else {}
    )
    host_pressure_endpoint_probe = (
        host_pressure_activation.get("endpoint_probe")
        if isinstance(host_pressure_activation.get("endpoint_probe"), dict)
        else {}
    )
    host_pressure_assay = (
        host_pressure_surface.get("host_pressure_assay_receipt")
        if isinstance(host_pressure_surface.get("host_pressure_assay_receipt"), dict)
        else {}
    )

    codex_sessions = [
        row for row in latency.get("codex_sessions", [])
        if isinstance(row, dict)
    ]
    compaction_rows = []
    for row in codex_sessions:
        if int(row.get("compactions") or 0) <= 0:
            continue
        compaction_row = {
            "path": row.get("path"),
            "compactions": row.get("compactions", 0),
            "turns": row.get("turns"),
        }
        for key in (
            "scan_mode",
            "scan_truncated",
            "count_semantics",
            "bytes_scanned",
            "file_size_bytes",
        ):
            if row.get(key) is not None:
                compaction_row[key] = row.get(key)
        compaction_rows.append(compaction_row)
    compaction_rows.sort(key=lambda row: int(row.get("compactions") or 0), reverse=True)

    reread_events = [
        row for row in ladder.get("reread_events", [])
        if isinstance(row, dict)
    ]
    reread_file_count = sum(
        len(row.get("rereads") or [])
        for row in reread_events
        if isinstance(row.get("rereads"), list)
    )

    top_reads = [
        row for row in hotspots.get("top_reads", [])[:5]
        if isinstance(row, dict)
    ]
    rediscovery = [
        row for row in hotspots.get("rediscovery", [])[:5]
        if isinstance(row, dict)
    ]
    max_rereads_per_file = max(
        [
            _coerce_count(row.get("reads"))
            for row in [*top_reads, *rediscovery]
            if isinstance(row, dict)
        ] or [0]
    )
    reread_pressure_count = max(reread_file_count, max_rereads_per_file)
    user_interrupts = errors.get("user_interrupts") or []
    tool_errors = errors.get("top_tool_error_lines") or []
    experience_families = [
        row for row in experience_frictions.get("families", [])
        if isinstance(row, dict)
    ]

    metrics = {
        "tools": {
            "top_tool_histogram": histogram.get("tool_histogram", [])[:5],
            "top_bash_verbs": histogram.get("bash_verbs", [])[:8],
        },
        "ladder_skip": {
            "ratio_bad_to_good_bash": ladder.get("ratio_bad_to_good_bash"),
            "bash_should_be_native_top": ladder.get("bash_should_be_native", [])[:8],
            "grep_calls_before_any_nav_flag": ladder.get("grep_calls_before_any_nav_flag"),
            "kernel_nav_flag_calls": ladder.get("kernel_nav_flag_calls", [])[:8],
            "dominant_shell_shape": ladder.get("dominant_shell_shape"),
        },
        "context_pressure": {
            "codex_sessions_with_compactions": len(compaction_rows),
            "max_compactions": max(
                [int(row.get("compactions") or 0) for row in compaction_rows] or [0]
            ),
            "top_compaction_sessions": compaction_rows[:2],
            "top_compaction_sessions_omitted": max(0, len(compaction_rows) - 2),
            "reread_event_sessions": len(reread_events),
            "reread_file_count": reread_file_count,
            "max_rereads_per_file": max_rereads_per_file,
            "reread_pressure_count": reread_pressure_count,
            "top_reads": top_reads[:2],
            "top_reads_omitted": max(0, len(top_reads) - 2),
            "rediscovery": rediscovery[:2],
            "rediscovery_omitted": max(0, len(rediscovery) - 2),
        },
        "discoverability": {
            "unique_wake_prompts": wake_prompts.get("unique_wake_prompts"),
            "repeated_wake_prompt_clusters": wake_prompts.get("repeated_prompt_cluster_count"),
            "route_miss_candidates": route_misses.get("candidate_count"),
            "route_miss_unresolved": route_misses.get("unresolved_count"),
        },
        "recovery": {
            "user_interrupt_count": len(user_interrupts) if isinstance(user_interrupts, list) else 0,
            "top_tool_error_lines": tool_errors[:5] if isinstance(tool_errors, list) else [],
        },
        "experience_frictions": {
            "event_count": _coerce_count(experience_frictions.get("event_count")),
            "family_count": _coerce_count(experience_frictions.get("family_count")),
            "top_family": experience_families[0].get("family") if experience_families else None,
            "top_families": [
                {
                    "family": row.get("family"),
                    "count": row.get("count"),
                    "distinct_sessions": row.get("distinct_sessions"),
                    "owner_surface": row.get("owner_surface"),
                    "next_command": row.get("next_command"),
                    "candidate_patch": row.get("candidate_patch"),
                    "priority": row.get("priority"),
                }
                for row in experience_families[:TRACE_IMPROVEMENT_SUMMARY_ROW_LIMIT]
            ],
            "top_families_omitted": max(
                0,
                len(experience_families) - TRACE_IMPROVEMENT_SUMMARY_ROW_LIMIT,
            ),
        },
        "host_pressure": {
            "active_agents": host_pressure_summary.get("active_agents"),
            "progress_units": host_pressure_summary.get("progress_units"),
            "pressure_index": host_pressure_summary.get("pressure_index"),
            "progress_per_pressure": host_pressure_summary.get("progress_per_pressure"),
            "bottleneck_class": host_pressure_summary.get("bottleneck_class"),
            "governor_decision": host_pressure_summary.get("governor_decision"),
            "confidence": host_pressure_summary.get("confidence"),
            "policy_source": host_pressure_envelope.get("policy_source"),
            "activation_status": host_pressure_endpoint_probe.get("status"),
            "calibration_status": host_pressure_assay.get("calibration_status"),
        },
    }

    selected_drilldown = _select_summary_drilldown(metrics)
    lens_names = list((report.get("lenses") or {}).keys())
    selected_lens = str(selected_drilldown.get("lens") or "none")
    selected_lens_already_loaded = selected_lens != "none" and set(lens_names) == {selected_lens}
    full_lens_fallback_command = str(selected_drilldown.get("command") or "")
    selected_lens_summary_command = (
        _summary_first_diagnostics_command(full_lens_fallback_command)
        if selected_lens != "none" and full_lens_fallback_command
        else full_lens_fallback_command
    )
    trace_improvement_surface = (
        report.get("trace_improvement_surface")
        if isinstance(report.get("trace_improvement_surface"), dict)
        else build_trace_improvement_surface(
            metrics=metrics,
            report=report,
            limit=TRACE_IMPROVEMENT_SUMMARY_ROW_LIMIT,
        )
    )
    trace_improvement_surface = _compact_trace_improvement_surface_for_summary(
        trace_improvement_surface,
        full_action_contract_row_count=0,
    )
    loaded_summary_next = (
        _already_loaded_summary_next(
            selected_lens=selected_lens,
            full_lens_fallback_command=full_lens_fallback_command,
            trace_improvement_surface=trace_improvement_surface,
        )
        if selected_lens_already_loaded
        else None
    )
    recommended_next_command = selected_lens_summary_command if not selected_lens_already_loaded else None
    recommended_next_reason = selected_drilldown["reason"]
    if loaded_summary_next:
        recommended_next_command = loaded_summary_next["command"]
        recommended_next_reason = loaded_summary_next["reason"]
    packet = {
        "kind": "agent_session_diagnostics_summary",
        "schema_version": "agent_session_diagnostics_summary_v1",
        "generated_at": report.get("generated_at"),
        "source_kind": report.get("kind"),
        "output_mode": "summary",
        "window": window,
        "counts": store_counts,
        "trace_to_git_handoff": summary.get("trace_to_git_handoff")
        if isinstance(summary.get("trace_to_git_handoff"), dict)
        else _build_trace_to_git_handoff(
            lens="all",
            store="both",
            last=_coerce_count(window.get("last")) or 20,
            source_kind=str(report.get("kind") or "agent_session_diagnostics"),
        ),
        "lens_names": lens_names,
        "metrics": metrics,
        "host_pressure_surface": _compact_host_pressure_surface(host_pressure_surface),
        "trace_improvement_surface": trace_improvement_surface,
        "summary_first_sufficiency": {
            "status": "pending_size_estimate",
            "selected_lens": selected_lens,
            "selected_lens_count": 0 if selected_lens == "none" else 1,
            "selected_lens_adequacy": "no_drilldown_needed"
            if selected_lens == "none"
            else "single_lens_sufficient",
            "selection_reason": selected_drilldown["reason"],
            "drilldown_policy": (
                "Open the selected-lens diagnostics summary first; full selected-lens JSON is "
                "the fallback after the compact receipt proves insufficient."
            ),
            "selected_lens_summary_already_loaded": selected_lens_already_loaded,
            "selected_lens_summary_command": selected_lens_summary_command or None,
            "full_lens_fallback_command": full_lens_fallback_command or None,
        },
        "next": [
            {
                "command": recommended_next_command,
                "reason": recommended_next_reason,
            }
        ] if recommended_next_command else [],
    }
    summary_bytes = _json_estimated_bytes(packet)
    if report.get("kind") == "agent_session_diagnostics_fast_scan":
        full_bytes = None
        packet["summary_first_sufficiency"].update({
            "status": "summary_measured_full_estimate_deferred",
            "full_report_estimated_bytes": None,
            "summary_estimated_bytes": summary_bytes,
            "byte_reduction_ratio": None,
            "byte_reduction_percent": None,
            "full_report_estimate_deferred_reason": (
                "fast_scan_summary_avoids_serializing_full_intermediate_report"
            ),
        })
    else:
        full_report_for_size = dict(report)
        full_report_for_size.setdefault("trace_improvement_surface", trace_improvement_surface)
        full_bytes = _json_estimated_bytes(full_report_for_size)
        packet["summary_first_sufficiency"].update({
            "status": "measured",
            "full_report_estimated_bytes": full_bytes,
            "summary_estimated_bytes": summary_bytes,
            "byte_reduction_ratio": round(summary_bytes / full_bytes, 4) if full_bytes else None,
            "byte_reduction_percent": round((1 - (summary_bytes / full_bytes)) * 100, 1) if full_bytes else None,
        })
    summary_bytes = _json_estimated_bytes(packet)
    packet["summary_first_sufficiency"].update({
        "summary_estimated_bytes": summary_bytes,
        "byte_reduction_ratio": round(summary_bytes / full_bytes, 4) if full_bytes else None,
        "byte_reduction_percent": round((1 - (summary_bytes / full_bytes)) * 100, 1) if full_bytes else None,
    })
    return packet


def write_report(report: dict[str, Any], path_token: str) -> Path:
    path = Path(path_token).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def route_miss_sidecar(report: dict[str, Any]) -> dict[str, Any]:
    payload = (report.get("lenses") or {}).get("route-misses")
    if not isinstance(payload, dict):
        raise ValueError("route-misses lens is required to write route-miss candidates")
    return {
        "kind": "docs_route_miss_candidates",
        "schema_version": "docs_route_miss_candidates_v1",
        "generated_at": report.get("generated_at"),
        "source_report_kind": report.get("kind"),
        "summary": {
            "source_prompt_count": payload.get("source_prompt_count", 0),
            "candidate_count": payload.get("candidate_count", 0),
            "resolved_count": payload.get("resolved_count", 0),
            "unresolved_count": payload.get("unresolved_count", 0),
        },
        "unresolved_candidates": payload.get("unresolved_candidates") or [],
        "candidates": payload.get("candidates") or [],
    }


def write_route_miss_candidates(report: dict[str, Any], path_token: str) -> Path:
    return write_report(route_miss_sidecar(report), path_token)


def context_pressure_hotspot_sidecar(report: dict[str, Any]) -> dict[str, Any]:
    """Build a compact candidate sidecar for repeated reread / compaction pressure.

    The sidecar is intentionally command-and-receipt shaped. It gives agents a
    small owner route and claim-check packet before they reopen a hot source
    file, without copying prompt bodies, assistant prose, or raw trace output.
    """
    summary = report if report.get("output_mode") == "summary" else summarize_report(report)
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    context = (
        metrics.get("context_pressure")
        if isinstance(metrics.get("context_pressure"), dict)
        else {}
    )
    trace_surface = (
        summary.get("trace_improvement_surface")
        if isinstance(summary.get("trace_improvement_surface"), dict)
        else {}
    )
    context_row = next(
        (
            row
            for row in trace_surface.get("rows", [])
            if isinstance(row, dict) and row.get("symptom_family") == "context_pressure"
        ),
        {},
    )
    action_contract = (
        context_row.get("action_contract")
        if isinstance(context_row.get("action_contract"), dict)
        else {}
    )
    summary_contract = (
        action_contract.get("context_pressure_summary_first_contract")
        if isinstance(action_contract.get("context_pressure_summary_first_contract"), dict)
        else {}
    )
    sufficiency = (
        summary.get("summary_first_sufficiency")
        if isinstance(summary.get("summary_first_sufficiency"), dict)
        else {}
    )
    rediscovery = context.get("rediscovery")
    if not isinstance(rediscovery, list):
        rediscovery = []
    candidates: list[dict[str, Any]] = []
    for row in rediscovery[:TRACE_IMPROVEMENT_SUMMARY_ROW_LIMIT]:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        if not path:
            continue
        candidates.append(
            {
                "path": path,
                "reads": _coerce_count(row.get("reads")),
                "distinct_sessions": _coerce_count(row.get("distinct_sessions")),
                "score": _coerce_count(row.get("score")),
                "owner_claim_check_route": _work_ledger_path_mutation_check_command(path),
                "claim_cards_route": WORK_LEDGER_CLAIM_CARDS_COMMAND,
                "first_summary_route": summary_contract.get("first_summary_route")
                or sufficiency.get("selected_lens_summary_command"),
                "full_drilldown_route": summary_contract.get("full_drilldown_route")
                or sufficiency.get("full_lens_fallback_command"),
                "source_body_boundary": (
                    "Do not reopen this source file or raw session bodies until the compact "
                    "summary and owner claim check prove the sidecar is insufficient."
                ),
            }
        )
    return {
        "kind": "context_pressure_hotspot_candidates",
        "schema_version": "context_pressure_hotspot_candidates_v1",
        "generated_at": summary.get("generated_at") or report.get("generated_at"),
        "source_report_kind": report.get("kind"),
        "summary": {
            "selected_lens": sufficiency.get("selected_lens"),
            "candidate_count": len(candidates),
            "reread_pressure_count": context.get("reread_pressure_count"),
            "max_compactions": context.get("max_compactions"),
            "summary_estimated_bytes": sufficiency.get("summary_estimated_bytes"),
            "full_report_estimated_bytes": sufficiency.get("full_report_estimated_bytes"),
            "byte_reduction_percent": sufficiency.get("byte_reduction_percent"),
            "selected_lens_summary_already_loaded": sufficiency.get(
                "selected_lens_summary_already_loaded"
            ),
        },
        "recommended_next": summary.get("next") or [],
        "context_pressure_contract": summary_contract,
        "candidates": candidates,
        "privacy_boundary": (
            "Candidate rows carry path/count/command receipts only; raw prompt, assistant, "
            "tool stdout/stderr, and session body text stay behind explicit drilldowns."
        ),
    }


def write_context_pressure_hotspots(report: dict[str, Any], path_token: str) -> Path:
    return write_report(context_pressure_hotspot_sidecar(report), path_token)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lens", default="all",
                    help=(
                        "histogram | hotspots | ladder-skip | latency | prompts | wake-prompts | "
                        "route-misses | errors | experience-frictions | all; snake_case aliases accepted"
                    ))
    ap.add_argument("--store", default="both", choices=["claude", "codex", "both"])
    ap.add_argument("--last", type=int, default=20,
                    help="Analyze only the last N sessions per store")
    ap.add_argument("--after", help="ISO timestamp; only include sessions modified after")
    ap.add_argument("--before", help="ISO timestamp; only include sessions modified before")
    ap.add_argument("--project", help="Claude project slug (default: this repo)")
    ap.add_argument("--limit", type=int, default=20, help="Top-N per lens")
    ap.add_argument("--output", default="table", choices=["table", "json"])
    ap.add_argument(
        "--summary",
        action="store_true",
        help="Emit a compact cross-lens summary instead of the full diagnostics report.",
    )
    ap.add_argument(
        "--trace-friction-board",
        action="store_true",
        help="Emit the generated trace observatory projection / Trace Friction Board.",
    )
    ap.add_argument(
        "--write-session-diagnostics",
        default=None,
        metavar="PATH",
        help="Write the stable JSON report to PATH in addition to stdout.",
    )
    ap.add_argument(
        "--write-trace-observatory-projection",
        nargs="?",
        const=TRACE_OBSERVATORY_DEFAULT_PATH,
        default=None,
        metavar="PATH",
        help=(
            "Write the trace observatory projection to PATH "
            f"(default: {TRACE_OBSERVATORY_DEFAULT_PATH})."
        ),
    )
    ap.add_argument(
        "--write-route-miss-candidates",
        default=None,
        metavar="PATH",
        help="Write the route-misses sidecar to PATH in addition to stdout.",
    )
    ap.add_argument(
        "--write-context-pressure-hotspots",
        default=None,
        metavar="PATH",
        help="Write the context-pressure hotspot sidecar to PATH in addition to stdout.",
    )
    args = ap.parse_args()

    try:
        selected_lens = normalize_lens_name(args.lens)
        if args.trace_friction_board or args.write_trace_observatory_projection:
            report = build_summary_report(
                store=args.store,
                last=args.last,
                after=args.after,
                before=args.before,
                project=args.project,
                limit=args.limit,
            )
            previous = None
            if args.write_trace_observatory_projection:
                previous_path = Path(args.write_trace_observatory_projection)
                if not previous_path.is_absolute():
                    previous_path = REPO_ROOT / previous_path
                try:
                    previous = json.loads(previous_path.read_text(encoding="utf-8"))
                except (FileNotFoundError, json.JSONDecodeError, OSError):
                    previous = None
            output_report = build_trace_observatory_projection(
                finished_summary=report,
                previous_projection=previous,
                runtime_scope=args.store,
                last=args.last,
            )
        elif (
            args.summary
            and selected_lens == "all"
            and not args.write_route_miss_candidates
            and not args.write_context_pressure_hotspots
        ):
            report = build_summary_report(
                store=args.store,
                last=args.last,
                after=args.after,
                before=args.before,
                project=args.project,
                limit=args.limit,
            )
            output_report = report
        else:
            report = build_report(
                lens=selected_lens,
                store=args.store,
                last=args.last,
                after=args.after,
                before=args.before,
                project=args.project,
                limit=args.limit,
            )
            output_report = summarize_report(report) if args.summary else report
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.write_session_diagnostics:
        write_report(output_report, args.write_session_diagnostics)
    if args.write_trace_observatory_projection:
        written = write_report(output_report, args.write_trace_observatory_projection)
        output_report["written_path"] = str(
            written.relative_to(REPO_ROOT) if written.is_relative_to(REPO_ROOT) else written
        )
    if args.write_route_miss_candidates:
        if "route-misses" not in (report.get("lenses") or {}):
            report = build_report(
                lens="route-misses",
                store=args.store,
                last=args.last,
                after=args.after,
                before=args.before,
                project=args.project,
                limit=args.limit,
            )
        write_route_miss_candidates(report, args.write_route_miss_candidates)
    if args.write_context_pressure_hotspots:
        if "hotspots" not in (report.get("lenses") or {}):
            report = build_report(
                lens="hotspots",
                store=args.store,
                last=args.last,
                after=args.after,
                before=args.before,
                project=args.project,
                limit=args.limit,
            )
        write_context_pressure_hotspots(report, args.write_context_pressure_hotspots)
    emit_report(output_report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
