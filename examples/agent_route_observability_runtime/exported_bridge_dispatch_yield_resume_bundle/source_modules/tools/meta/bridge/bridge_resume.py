"""
Bridge -> Claude.app resume protocol.

[PURPOSE]
The missing primitive that lets a Claude.app Code-tab agent dispatch
long-running bridge work, end its turn, and be reawakened in the SAME
conversation when the bridge finishes. The doctrine is: *dispatch, persist,
end turn, deliver one short continuation packet, continue from disk*. The
UI keystroke path is just the current transport — the protocol is designed
so the transport can be swapped later (direct enqueue / IPC hook) without
rewriting any of the policy.

[SCHEMA VERSION]
`RESUME_SCHEMA_VERSION = "1.1.0"` — trigger payloads and ledger rows
include this so downstream consumers can detect drift.

  1.0.0: initial protocol (target, job, manager, ledger, emit_trigger).
  1.1.0: adds SessionSnapshot + idle-safe + exactly-once delivery:
           * emit_trigger captures a SessionSnapshot of the target CLI
             jsonl (path + byte_size + mtime_ns) at trigger-write time;
           * daemon calls assess_session_activity(snapshot, sentinel)
             BEFORE paste and skips ("skipped_not_idle" / "skipped_already_injected")
             when the session has seen activity that means we would either
             interrupt a live user or re-inject a message already delivered.
           * ledger events widened: dispatched, trigger_written, trigger_consumed,
             inject_succeeded, inject_failed, skipped_dup, skipped_not_idle,
             skipped_already_injected.

[ARCHITECTURE]
- A `ResumeTarget` describes WHERE to inject (which tab, which session,
  which app). Persisted in claude_session_transport.json under
  extras["bridge_resume"].
- A `ResumeJob` describes WHAT to inject (job id, status, summary, artifact
  pointers, continue instruction). Created at bridge dispatch, finalized at
  bridge completion.
- A `SessionSnapshot` describes the target session's jsonl state at the
  moment of trigger emission. It is the anchor the idle-check uses to
  detect "has the user or another turn happened since we decided to resume?"
- A `BridgeResumeManager` ties them together and writes one trigger file per
  job into the injector inbox. The daemon (claude_app_injector watch) does
  the actual paste. Idempotency is enforced via a JSONL ledger: each job_id
  may only emit one trigger, even across retries / process restarts. Idle
  safety is enforced by the daemon via assess_session_activity on the
  persisted snapshot.
- The injected message is SHORT — status + 3..10 line summary + artifact
  path + continue instruction. Raw bridge transcripts NEVER hit the chat
  box. The agent reads artifacts on disk if it wants more.

[STATE MACHINE]
  (job created)
      -> emit_trigger -> trigger_written  -> (daemon pick up)
      -> assess_session_activity
          -> safe     -> inject -> inject_succeeded | inject_failed
          -> not_safe -> skipped_not_idle / skipped_already_injected
  Duplicate emit_trigger calls -> skipped_dup (no state change).

[OPT-IN]
- Default behaviour is "do nothing". A bridge run only emits resume triggers
  if launched with `--resume-mode auto_inject`. Manual mode writes to
  tools/meta/bridge/resume_manifests/ instead of the live inbox.

[INTERFACE]
- Public API: ResumeTarget, ResumeJob, SessionSnapshot, ActivityReport,
  BridgeResumeManager, format_resume_message, discover_resume_target,
  write_resume_target, clear_resume_target, discover_current_session_id,
  capture_session_snapshot, assess_session_activity, resolve_jsonl_path,
  default_inbox_dir, default_ledger_path, RESUME_MODES,
  RESUME_SCHEMA_VERSION, DEFAULT_STALE_PENDING_THRESHOLD_HOURS.
- CLI:
    python3 -m tools.meta.bridge.bridge_resume show
    python3 -m tools.meta.bridge.bridge_resume set-target [--switch-tab 3] [--session-id auto]
    python3 -m tools.meta.bridge.bridge_resume clear-target
    python3 -m tools.meta.bridge.bridge_resume emit --job-id ID --status ok --summary "..."
    python3 -m tools.meta.bridge.bridge_resume ledger [--tail 20] [--job-id ID]
    python3 -m tools.meta.bridge.bridge_resume status
    python3 -m tools.meta.bridge.bridge_resume jobs [--limit 20]
    python3 -m tools.meta.bridge.bridge_resume job <job_id>

[FLOW]
- discover_resume_target() and discover_current_session_id() recover the destination
  session and transport hints -> bridge_dispatch_and_yield() records dispatch intent,
  runs the injected bridge driver, and builds a ResumeJob -> BridgeResumeManager
  writes trigger + ledger state -> claude_app_injector watch mode performs idle-safe
  delivery -> job_states() and bucket_for_event() project operator status from ledger rows.

[DEPENDENCIES]
- tools.meta.bridge.session_transport — persisted resume target and active-session
  heartbeat state.
- tools.meta.bridge.claude_desktop_ipc — Claude Desktop session discovery fallback
  when stamped identity is absent.
- system.lib.metabolism_store + metabolism_scheduler — shared provider-pressure
  snapshot for the operator-facing status CLI.
- Stdlib otherwise: argparse, dataclasses, json, pathlib, time, uuid.

[CONSTRAINTS]
- Guarantee: Resume triggers remain short and artifact-first; raw bridge transcripts
  never enter the injected chat body.
- Orders: Ledger rows are append-only and idempotency is enforced by trigger_written /
  skipped_dup checks per job_id.
- When-needed: Open when bridge work must end the current turn, persist a resume target,
  and later reawaken the same Claude session from disk-backed artifacts instead of
  polling in-thread.
- Escalates-to: tools/meta/bridge/claude_app_injector.py::AppInjector.watch_loop; tools/meta/bridge/session_transport.py; codex/doctrine/skills/bridge_runtime/dispatch_yield.md
- Navigation-group: bridge_tooling
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from system.lib import metabolism_scheduler as metabolism_scheduler
from system.lib import metabolism_store as metabolism_store
from tools.meta.bridge.session_transport import (
    ACTIVE_SESSION_PATH,
    TRANSPORT_PATH,
    read_active_session,
    read_transport,
    make_record,
    write_transport,
    TransportRecord,
)

__all__ = [
    "ResumeTarget",
    "ResumeJob",
    "SessionSnapshot",
    "ActivityReport",
    "BridgeResumeManager",
    "ResumeError",
    "DispatchAndYieldResult",
    "bridge_dispatch_and_yield",
    "format_resume_message",
    "discover_resume_target",
    "write_resume_target",
    "clear_resume_target",
    "discover_current_session_id",
    "capture_session_snapshot",
    "assess_session_activity",
    "resolve_jsonl_path",
    "default_inbox_dir",
    "default_ledger_path",
    "bucket_for_event",
    "RESUME_MODES",
    "RESUME_SCHEMA_VERSION",
    "EVENT_BUCKETS",
    "DEFAULT_STALE_PENDING_THRESHOLD_HOURS",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INBOX_DIR = REPO_ROOT / "tools/meta/bridge/injector_inbox"
DEFAULT_LEDGER_PATH = REPO_ROOT / "tools/meta/bridge/resume_ledger.jsonl"
DEFAULT_PROJECTS_DIR = Path.home() / ".claude/projects/-Users-example-src-ai-workflow"
DEFAULT_SENTINEL_PREFIX = "[bridge resume]"

RESUME_MODES = ("none", "manual", "auto_inject")
RESUME_SCHEMA_VERSION = "1.1.0"

# Map a ledger event (terminal-most state observed for a job) onto a small
# operator-facing bucket name. The status / jobs CLIs use this to roll up
# raw events into the four buckets that matter at a glance: still in
# flight, succeeded, failed, or skipped (with the skip subkind preserved).
EVENT_BUCKETS: dict[str, str] = {
    "dispatch_scheduled": "pending",
    "dispatch_completed": "pending",
    "dispatch_failed": "failed",
    "dispatch_emit_failed": "failed",
    "trigger_written": "pending",
    "skipped_dup": "deduped",
    "inject_ok": "succeeded",
    "inject_failed": "failed",
    "skipped_already_injected": "blocked_already_injected",
    "skipped_not_idle": "blocked_not_idle",
}
TERMINAL_BUCKETS: frozenset[str] = frozenset(
    {
        "succeeded",
        "failed",
        "deduped",
        "blocked_already_injected",
        "blocked_not_idle",
    }
)


def bucket_for_event(event: Optional[str]) -> str:
    """[ACTION]
    - Teleology: Map a ledger event name to its operator-facing bucket label for status rollups.
    - Guarantee: Returns a string bucket name; unknown or None events return "unknown" without raising.
    - Fails: None.
    """
    if not event:
        return "unknown"
    return EVENT_BUCKETS.get(event, "unknown")


def default_inbox_dir() -> Path:
    """[ACTION]
    - Teleology: Expose the canonical injector inbox directory path so callers avoid hardcoding it.
    - Guarantee: Returns the repo-relative DEFAULT_INBOX_DIR Path constant.
    - Fails: None.
    """
    return DEFAULT_INBOX_DIR


def default_ledger_path() -> Path:
    """[ACTION]
    - Teleology: Expose the canonical resume ledger path so callers avoid hardcoding it.
    - Guarantee: Returns the repo-relative DEFAULT_LEDGER_PATH Path constant.
    - Fails: None.
    """
    return DEFAULT_LEDGER_PATH


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ResumeError(RuntimeError):
    """Raised when the resume protocol cannot complete a request."""


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------
@dataclass
class ResumeTarget:
    """[ROLE]
    - Teleology: Describe WHERE a resume injection should be delivered — which app, tab, and CLI session.
    - Ownership: Owns target_app, switch_tab, session_id, session_url, and sentinel_prefix.
    - Mutability: Mutable; persisted into claude_session_transport.json via write_resume_target.
    - Concurrency: Not thread-safe; mutations should be serialized by the caller.
    """

    target_app: str = "Claude"
    switch_tab: Optional[int | str] = 3
    session_id: Optional[str] = None
    session_url: Optional[str] = None
    sentinel_prefix: str = DEFAULT_SENTINEL_PREFIX

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResumeTarget":
        return cls(
            target_app=str(data.get("target_app", "Claude")),
            switch_tab=data.get("switch_tab", 3),
            session_id=data.get("session_id"),
            session_url=data.get("session_url"),
            sentinel_prefix=str(
                data.get("sentinel_prefix", DEFAULT_SENTINEL_PREFIX)
            ),
        )


@dataclass
class ResumeJob:
    """[ROLE]
    - Teleology: Carry WHAT should be injected into a Claude session after a bridge dispatch finishes.
    - Ownership: Owns job_id, status, summary_lines, artifact_paths, continue_instruction, and extras.
    - Mutability: Mutable; fields are updated after the bridge driver returns before emit_trigger is called.
    - Concurrency: Not thread-safe; owned by a single dispatch-and-yield call.
    """

    job_id: str
    plan_id: Optional[str] = None
    group_label: Optional[str] = None
    status: str = "ok"
    summary_lines: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    continue_instruction: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new_id(prefix: str = "bridge") -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"{prefix}_{ts}_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ----------------------------------------------------------------------
# session snapshot + idle-check primitive
# ----------------------------------------------------------------------
@dataclass
class SessionSnapshot:
    """[ROLE]
    - Teleology: Record the byte-size and mtime of the target session's jsonl at trigger-emission time so the daemon can detect intervening activity before paste.
    - Ownership: Owns session_id, jsonl_path, jsonl_byte_size, jsonl_mtime_ns, and captured_at.
    - Mutability: Immutable once captured; created by capture_session_snapshot and embedded in trigger payloads.
    - Concurrency: Safe to share; read-only after construction.

    Captured at trigger emission time. The daemon compares the live jsonl
    to this snapshot before paste, so it can:
      - SKIP inject if foreign activity happened since snapshot (means the
        user typed after our dispatch — we must not interrupt);
      - SKIP inject if the delta already contains our sentinel (means a
        duplicate trigger was emitted and a previous daemon tick already
        pasted the message);
      - PROCEED if the delta is empty or only contains our own assistant
        turn-end bytes (expected gap between dispatch and trigger).
    """

    session_id: Optional[str]
    jsonl_path: str
    jsonl_byte_size: int
    jsonl_mtime_ns: int
    captured_at: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionSnapshot":
        return cls(
            session_id=data.get("session_id"),
            jsonl_path=str(data.get("jsonl_path", "")),
            jsonl_byte_size=int(data.get("jsonl_byte_size", 0) or 0),
            jsonl_mtime_ns=int(data.get("jsonl_mtime_ns", 0) or 0),
            captured_at=str(data.get("captured_at", "")),
        )


@dataclass
class ActivityReport:
    """[ROLE]
    - Teleology: Summarize what happened in the target session's jsonl delta so assess_session_activity can return a single safe_to_inject decision.
    - Ownership: Owns has_delta, delta_bytes, sentinel/foreign-user flags, safe_to_inject, and reason string.
    - Mutability: Immutable once constructed by assess_session_activity.
    - Concurrency: Safe to share; read-only after construction.
    """

    has_delta: bool
    delta_bytes: int
    delta_contains_sentinel: bool
    delta_contains_foreign_user: bool
    safe_to_inject: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def resolve_jsonl_path(
    session_id: Optional[str],
    *,
    projects_dir: Optional[Path] = None,
) -> Optional[Path]:
    """[ACTION]
    - Teleology: Compute the expected jsonl file path for a CLI session id without touching the filesystem.
    - Guarantee: Returns the Path under projects_dir when session_id is non-empty, otherwise None.
    - Fails: None.
    """
    if not session_id:
        return None
    pdir = projects_dir or DEFAULT_PROJECTS_DIR
    return pdir / f"{session_id}.jsonl"


def capture_session_snapshot(
    session_id: Optional[str],
    *,
    projects_dir: Optional[Path] = None,
) -> Optional[SessionSnapshot]:
    """[ACTION]
    - Teleology: Record the byte-size and mtime of the target session's jsonl as an idle-check anchor for later resume injection.
    - Guarantee: Returns a SessionSnapshot when the jsonl exists; None if session_id is empty or the file is absent.
    - Fails: Returns None on OSError from stat(); other filesystem errors propagate.
    - When-needed: Open when a resume trigger needs the exact session-jsonl anchor used later for idle-safe injection checks.
    - Escalates-to: tools/meta/bridge/bridge_resume.py::assess_session_activity; tools/meta/bridge/bridge_resume.py::discover_current_session_id
    """
    p = resolve_jsonl_path(session_id, projects_dir=projects_dir)
    if p is None or not p.exists():
        return None
    try:
        st = p.stat()
    except OSError:
        return None
    return SessionSnapshot(
        session_id=session_id,
        jsonl_path=str(p),
        jsonl_byte_size=int(st.st_size),
        jsonl_mtime_ns=int(st.st_mtime_ns),
        captured_at=_utc_now_iso(),
    )


def _extract_user_text_from_jsonl_row(row: dict[str, Any]) -> Optional[str]:
    """If this jsonl row is a user-type message, return its text body.
    Else return None.

    Claude Code CLI writes rows like:
      { "type": "user", "message": {"role": "user", "content": [...] } }
    where content is either a string, a list of {"type":"text","text":...}
    blocks, or a list of tool_result blocks.
    """
    if row.get("type") != "user":
        return None
    msg = row.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif block.get("type") == "tool_result":
                inner = block.get("content")
                if isinstance(inner, str):
                    parts.append(inner)
                elif isinstance(inner, list):
                    for sub in inner:
                        if isinstance(sub, dict) and sub.get("type") == "text":
                            parts.append(str(sub.get("text", "")))
        return " ".join(parts)
    return None


def assess_session_activity(
    snapshot: SessionSnapshot,
    sentinel: str,
    *,
    require_sentinel_for_safe_skip: bool = True,
) -> ActivityReport:
    """[ACTION]
    - Teleology: Classify the jsonl delta since snapshot to decide whether injecting a sentinel message is safe.
    - Guarantee: Returns an ActivityReport with safe_to_inject=True only when no foreign user activity or duplicate sentinel is detected.
    - Fails: Returns a conservative safe_to_inject=False ActivityReport on read errors; filesystem errors do not propagate.
    - When-needed: Open when the resume daemon must decide whether a queued trigger is still safe to inject into the target Claude session.
    - Escalates-to: tools/meta/bridge/claude_app_injector.py::AppInjector.watch_loop; tools/meta/bridge/bridge_resume.py::capture_session_snapshot
    """
    p = Path(snapshot.jsonl_path)
    if not p.exists():
        return ActivityReport(
            has_delta=False,
            delta_bytes=0,
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=True,
            reason="jsonl_missing_assume_safe",
        )
    try:
        current_size = p.stat().st_size
    except OSError:
        return ActivityReport(
            has_delta=False,
            delta_bytes=0,
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=True,
            reason="stat_failed_assume_safe",
        )
    delta_bytes = current_size - snapshot.jsonl_byte_size
    if delta_bytes <= 0:
        return ActivityReport(
            has_delta=False,
            delta_bytes=0,
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=True,
            reason="no_delta",
        )
    try:
        with p.open("rb") as fh:
            fh.seek(snapshot.jsonl_byte_size)
            raw = fh.read(delta_bytes)
    except OSError:
        return ActivityReport(
            has_delta=True,
            delta_bytes=delta_bytes,
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=False,
            reason="delta_read_failed",
        )
    new_text = raw.decode("utf-8", errors="replace")

    contains_sentinel = False
    contains_foreign_user = False
    saw_any_user_row = False
    for line in new_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        user_text = _extract_user_text_from_jsonl_row(row)
        if user_text is None:
            continue
        saw_any_user_row = True
        if sentinel and sentinel in user_text:
            contains_sentinel = True
        else:
            contains_foreign_user = True

    if contains_foreign_user:
        return ActivityReport(
            has_delta=True,
            delta_bytes=delta_bytes,
            delta_contains_sentinel=contains_sentinel,
            delta_contains_foreign_user=True,
            safe_to_inject=False,
            reason="foreign_user_activity",
        )
    if contains_sentinel:
        return ActivityReport(
            has_delta=True,
            delta_bytes=delta_bytes,
            delta_contains_sentinel=True,
            delta_contains_foreign_user=False,
            safe_to_inject=False,
            reason="already_injected",
        )
    if saw_any_user_row:
        # saw a user row but neither flagged — shouldn't happen; be cautious
        return ActivityReport(
            has_delta=True,
            delta_bytes=delta_bytes,
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=False,
            reason="unclassified_user_row",
        )
    # Delta exists but has no user rows (only assistant / tool_use / etc.) —
    # that's the normal "agent was still wrapping up its turn" case.
    return ActivityReport(
        has_delta=True,
        delta_bytes=delta_bytes,
        delta_contains_sentinel=False,
        delta_contains_foreign_user=False,
        safe_to_inject=True,
        reason="assistant_only_delta",
    )


# ----------------------------------------------------------------------
# message formatting
# ----------------------------------------------------------------------
def format_resume_message(
    job: ResumeJob,
    *,
    max_summary_lines: int = 10,
    include_continue: bool = True,
) -> str:
    """[ACTION]
    - Teleology: Render a ResumeJob as the short artifact-first body of a resumed user turn, staying well under 2 KB.
    - Guarantee: Returns a newline-joined string with job header, optional summary, artifact paths, and continue instruction; raw bridge transcripts never appear.
    - Fails: None.
    - When-needed: Open when a bridge result must be compressed into the short, artifact-first user turn that resumes the paused session.
    - Escalates-to: tools/meta/bridge/bridge_resume.py::bridge_dispatch_and_yield; tools/meta/bridge/bridge_campaign.py::build_resume_job
    """
    lines: list[str] = []
    # dispatch loop preamble (injected via job.extras by dispatch_loop.py)
    preamble = (job.extras or {}).get("dispatch_loop_preamble", "")
    if preamble:
        lines.append(preamble)
    lines.append(
        f"BRIDGE RESUME job={job.job_id} status={job.status}"
    )
    lines.append(f"plan: {job.plan_id or 'n/a'}")
    lines.append(f"group: {job.group_label or 'n/a'}")
    summary = list(job.summary_lines or [])
    if len(summary) > max_summary_lines:
        truncated = summary[:max_summary_lines]
        truncated.append(
            f"... ({len(summary) - max_summary_lines} more lines truncated; "
            "open the artifact for full output)"
        )
        summary = truncated
    if summary:
        lines.append("")
        lines.append("summary:")
        for s in summary:
            s_clean = str(s).strip()
            if s_clean:
                lines.append(f"- {s_clean}")
    if job.artifact_paths:
        lines.append("")
        lines.append("artifacts:")
        for a in job.artifact_paths:
            a_clean = str(a).strip()
            if a_clean:
                lines.append(f"- {a_clean}")
    if include_continue and job.continue_instruction:
        lines.append("")
        lines.append(f"continue: {job.continue_instruction.strip()}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# transport persistence
# ----------------------------------------------------------------------
def discover_resume_target(
    *,
    transport_path: Optional[Path] = None,
) -> Optional[ResumeTarget]:
    """[ACTION]
    - Teleology: Read the persisted ResumeTarget from the transport file so callers can emit triggers without re-reading the transport schema.
    - Guarantee: Returns a ResumeTarget when a valid target is stored; None if the transport file is absent or lacks a resume target.
    - Fails: Propagates filesystem or JSON errors from read_transport().
    - When-needed: Open when resume orchestration needs the persisted injection target without re-reading the transport schema by hand.
    - Escalates-to: tools/meta/bridge/session_transport.py; tools/meta/bridge/bridge_resume.py::write_resume_target
    """
    rec = read_transport(path=transport_path)
    if not rec:
        return None
    extras = rec.get("extras") or {}
    bridge_resume = extras.get("bridge_resume") or {}
    target = bridge_resume.get("target")
    if not target:
        return None
    return ResumeTarget.from_dict(target)


def write_resume_target(
    target: ResumeTarget,
    *,
    transport_path: Optional[Path] = None,
    ledger_path: Optional[Path] = None,
) -> Path:
    """[ACTION]
    - Teleology: Persist a ResumeTarget into the transport file so future dispatch-yield operations can locate the injection destination.
    - Guarantee: Returns the path written after an atomic tmp-then-replace; creates a minimal transport record if the file is absent.
    - Fails: Propagates filesystem errors from directory creation, writing, or the atomic replace.
    - When-needed: Open when a caller must persist or update the Claude resume destination before dispatch-yield work begins.
    - Escalates-to: tools/meta/bridge/session_transport.py::make_record; tools/meta/bridge/bridge_resume.py::discover_resume_target
    """
    target_path = transport_path or TRANSPORT_PATH
    rec = read_transport(path=target_path)
    if rec is None:
        record = make_record(
            launch_mode="notification_only",
            launched_by="bridge_resume",
            summary="Resume target persisted by bridge_resume.",
        )
        rec = dataclasses.asdict(record)
    extras = dict(rec.get("extras") or {})
    bridge_resume = dict(extras.get("bridge_resume") or {})
    bridge_resume["target"] = target.to_dict()
    bridge_resume["ledger_path"] = str(
        ledger_path or default_ledger_path()
    )
    bridge_resume["updated_at"] = _utc_now_iso()
    extras["bridge_resume"] = bridge_resume
    rec["extras"] = extras
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = target_path.with_suffix(target_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target_path)
    return target_path


def clear_resume_target(
    *, transport_path: Optional[Path] = None
) -> bool:
    """[ACTION]
    - Teleology: Remove the resume target from the transport file to disable future automated injection.
    - Guarantee: Returns True when the target was present and removed; False when the transport file or bridge_resume key is absent.
    - Fails: Propagates filesystem errors from writing or the atomic replace.
    - When-needed: Open when automation should explicitly disable future resume injection for the current transport state.
    - Escalates-to: tools/meta/bridge/bridge_resume.py::write_resume_target; tools/meta/bridge/session_transport.py
    """
    target_path = transport_path or TRANSPORT_PATH
    rec = read_transport(path=target_path)
    if not rec:
        return False
    extras = rec.get("extras") or {}
    if "bridge_resume" not in extras:
        return False
    extras = dict(extras)
    extras.pop("bridge_resume", None)
    rec["extras"] = extras
    tmp = target_path.with_suffix(target_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target_path)
    return True


# ----------------------------------------------------------------------
# session id discovery
# ----------------------------------------------------------------------
def discover_current_session_id(
    *,
    projects_dir: Optional[Path] = None,
    transport_path: Optional[Path] = None,
    active_session_path: Optional[Path] = None,
) -> Optional[str]:
    """[ACTION]
    - Teleology: Resolve the best available Claude CLI session id using a tiered stamped-identity + mtime fallback chain.
    - Guarantee: Returns the session_id string when any tier succeeds and the corresponding jsonl exists on disk; None if every tier fails.
    - Fails: Individual tier failures are swallowed and fall through to the next tier; does not propagate exceptions.
    - When-needed: Open when resume tooling needs the best current Claude CLI session id and must understand the stamped-identity fallbacks before guessing by mtime.
    - Escalates-to: tools/meta/bridge/claude_desktop_ipc.py::find_current_repo_session; tools/meta/bridge/session_transport.py::read_active_session
    """
    def _check_stamp(rec: Optional[dict]) -> Optional[str]:
        if not isinstance(rec, dict):
            return None
        active = (rec.get("extras") or {}).get("active_session") or {}
        stamped_id = active.get("session_id")
        if not stamped_id:
            return None
        stamped_jsonl = active.get("transcript_path")
        if stamped_jsonl and Path(stamped_jsonl).exists():
            return stamped_id
        pdir = projects_dir or DEFAULT_PROJECTS_DIR
        candidate = pdir / f"{stamped_id}.jsonl"
        if candidate.exists():
            return stamped_id
        return None

    # Tier 1a: stamped identity from the new active-session heartbeat file.
    try:
        rec = read_active_session(path=active_session_path)
        hit = _check_stamp(rec)
        if hit:
            return hit
    except Exception:
        pass

    # Tier 1b: stamped identity from the legacy transport file (one-release compat).
    try:
        rec = read_transport(path=transport_path)
        hit = _check_stamp(rec)
        if hit:
            return hit
    except Exception:
        pass

    # Tier 2: Claude Desktop session store (authoritative session mapping).
    try:
        from tools.meta.bridge.claude_desktop_ipc import find_current_repo_session
        desktop_session = find_current_repo_session()
        if desktop_session and desktop_session.cli_session_id:
            pdir = projects_dir or DEFAULT_PROJECTS_DIR
            candidate = pdir / f"{desktop_session.cli_session_id}.jsonl"
            if candidate.exists():
                return desktop_session.cli_session_id
    except ImportError:
        pass
    except Exception:
        pass

    # Tier 3: mtime-based heuristic (legacy fallback).
    pdir = projects_dir or DEFAULT_PROJECTS_DIR
    if not pdir.exists():
        return None
    candidates: list[tuple[float, str]] = []
    for entry in pdir.glob("*.jsonl"):
        try:
            candidates.append((entry.stat().st_mtime, entry.stem))
        except OSError:
            continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ----------------------------------------------------------------------
# manager + ledger
# ----------------------------------------------------------------------
class BridgeResumeManager:
    """[ROLE]
    - Teleology: Coordinate trigger emission and ledger writes for one resume target so bridge jobs can be durably resumed into the correct Claude session.
    - Ownership: Owns the inbox directory, ledger path, sentinel prefix, and resume target reference.
    - Mutability: Mutable; ledger is appended across multiple emit_trigger calls during a single bridge run.
    - Concurrency: Not thread-safe; construct one per bridge run and do not share across threads.
    """

    def __init__(
        self,
        target: ResumeTarget,
        *,
        inbox_dir: Optional[Path] = None,
        ledger_path: Optional[Path] = None,
        sentinel_prefix: Optional[str] = None,
        projects_dir: Optional[Path] = None,
    ) -> None:
        self.target = target
        self.inbox_dir = Path(inbox_dir or default_inbox_dir())
        self.ledger_path = Path(ledger_path or default_ledger_path())
        self.sentinel_prefix = (
            sentinel_prefix
            if sentinel_prefix is not None
            else target.sentinel_prefix
        )
        self.projects_dir = (
            Path(projects_dir) if projects_dir else DEFAULT_PROJECTS_DIR
        )
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.touch()

    # ------------------------------------------------------------------
    # ledger
    # ------------------------------------------------------------------
    def append_ledger(
        self, event: str, job_id: str, **details: Any
    ) -> None:
        """[ACTION]
        - Teleology: Record one named event for a job_id into the append-only JSONL resume ledger.
        - Guarantee: After return the ledger file contains a new row with ts, event, job_id, and details.
        - Fails: Propagates OSError from opening or writing the ledger file.
        """
        row = {
            "ts": _utc_now_iso(),
            "event": event,
            "job_id": job_id,
            "details": details,
        }
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def has_emitted(self, job_id: str) -> bool:
        """[ACTION]
        - Teleology: Check the ledger for a prior trigger_written or skipped_dup event so emit_trigger can enforce exactly-once delivery.
        - Guarantee: Returns True when any prior trigger_written or skipped_dup row for job_id exists; False otherwise.
        - Fails: Returns False on OSError; does not propagate filesystem errors.
        """
        if not self.ledger_path.exists():
            return False
        try:
            content = self.ledger_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        for line in reversed(content):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("job_id") != job_id:
                continue
            if row.get("event") == "trigger_written":
                return True
            if row.get("event") == "skipped_dup":
                return True
        return False

    def ledger_rows(
        self,
        *,
        job_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """[ACTION]
        - Teleology: Return parsed ledger rows for status projection, optionally scoped to one job_id and tail-limited.
        - Guarantee: Returns a list of dicts (possibly empty); invalid JSON lines are silently skipped.
        - Fails: Propagates OSError from reading the ledger file when it exists.
        """
        if not self.ledger_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if job_id and row.get("job_id") != job_id:
                continue
            rows.append(row)
        if limit is not None:
            rows = rows[-limit:]
        return rows

    # ------------------------------------------------------------------
    # trigger emission
    # ------------------------------------------------------------------
    def emit_trigger(
        self,
        job: ResumeJob,
        *,
        allow_dup: bool = False,
        submit: bool = True,
        switch_tab_settle_s: float = 0.7,
    ) -> Optional[Path]:
        """[ACTION]
        - Teleology: Write one trigger JSON into the injector inbox and record a trigger_written ledger row, enforcing exactly-once delivery.
        - Guarantee: Returns the trigger Path on success; None when the job was already emitted and allow_dup is False.
        - Fails: Propagates filesystem errors from the atomic write/replace; ledger errors are not suppressed.
        - When-needed: Open when a finished bridge outcome must become one inbox trigger plus one ledger transition with duplicate suppression and idle-check metadata.
        - Escalates-to: tools/meta/bridge/claude_app_injector.py::AppInjector.watch_loop; tools/meta/bridge/bridge_resume.py::format_resume_message
        """
        if not allow_dup and self.has_emitted(job.job_id):
            self.append_ledger(
                "skipped_dup",
                job.job_id,
                reason="already_in_ledger",
            )
            return None

        message_body = format_resume_message(job)
        sentinel = f"{self.sentinel_prefix} job={job.job_id}"

        # Capture an idle-check anchor: the jsonl byte-size + mtime of the
        # target session at trigger-emission time. The daemon uses this to
        # decide whether foreign activity has happened between now and
        # paste time (abort) OR whether a previous paste has already
        # delivered the same sentinel (skip as already-injected).
        snapshot = capture_session_snapshot(
            self.target.session_id,
            projects_dir=self.projects_dir,
        )

        payload: dict[str, Any] = {
            "text": message_body,
            "sentinel": sentinel,
            "submit": submit,
            "target_app": self.target.target_app,
            "switch_tab_settle_s": switch_tab_settle_s,
            "_resume": {
                "schema_version": RESUME_SCHEMA_VERSION,
                "job_id": job.job_id,
                "plan_id": job.plan_id,
                "group_label": job.group_label,
                "status": job.status,
                "ledger_path": str(self.ledger_path),
                "dispatch_snapshot": (
                    snapshot.to_dict() if snapshot is not None else None
                ),
            },
        }
        if self.target.switch_tab is not None:
            payload["switch_tab"] = self.target.switch_tab
        if self.target.session_url:
            payload["navigate_url"] = self.target.session_url

        trigger_path = self.inbox_dir / f"{job.job_id}.json"
        # Atomic write so the daemon never sees a half-written file.
        tmp = trigger_path.with_suffix(trigger_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(trigger_path)

        self.append_ledger(
            "trigger_written",
            job.job_id,
            schema_version=RESUME_SCHEMA_VERSION,
            path=str(trigger_path),
            sentinel=sentinel,
            target_app=self.target.target_app,
            switch_tab=self.target.switch_tab,
            status=job.status,
            allow_dup=allow_dup,
            dispatch_snapshot=(
                snapshot.to_dict() if snapshot is not None else None
            ),
        )
        return trigger_path

    def record_inject_result(
        self,
        job_id: str,
        *,
        ok: bool,
        error: str = "",
        duration_ms: int = 0,
    ) -> None:
        """[ACTION]
        - Teleology: Record whether the injector daemon's paste attempt succeeded so the ledger reflects the final inject_ok or inject_failed state.
        - Guarantee: After return the ledger contains one inject_ok or inject_failed row for the given job_id.
        - Fails: Propagates OSError from append_ledger.
        """
        event = "inject_ok" if ok else "inject_failed"
        self.append_ledger(
            event,
            job_id,
            error=error,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # status projection helpers
    # ------------------------------------------------------------------
    def job_states(self) -> dict[str, dict[str, Any]]:
        """[ACTION]
        - Teleology: Collapse the append-only ledger into one record per job_id showing the latest event, first/last timestamps, and full event list.
        - Guarantee: Returns a dict ordered by last_seen descending; empty dict when the ledger has no rows.
        - Fails: Propagates errors from ledger_rows().
        - When-needed: Open when CLI status views need the projected latest state per resume job instead of raw JSONL rows.
        - Escalates-to: tools/meta/bridge/bridge_resume.py::bucket_for_event; tools/meta/bridge/bridge_resume.py::BridgeResumeManager.ledger_rows
        """
        aggregates: dict[str, dict[str, Any]] = {}
        for row in self.ledger_rows():
            jid = row.get("job_id")
            if not jid:
                continue
            rec = aggregates.setdefault(
                jid,
                {
                    "job_id": jid,
                    "current_state": None,
                    "first_seen": row.get("ts"),
                    "last_seen": row.get("ts"),
                    "events": [],
                    "latest_details": {},
                },
            )
            rec["events"].append(
                {"ts": row.get("ts"), "event": row.get("event")}
            )
            rec["current_state"] = row.get("event")
            rec["last_seen"] = row.get("ts")
            details = row.get("details") or {}
            if isinstance(details, dict):
                rec["latest_details"].update(details)
        return dict(
            sorted(
                aggregates.items(),
                key=lambda kv: kv[1].get("last_seen") or "",
                reverse=True,
            )
        )


# ----------------------------------------------------------------------
# canonical dispatch-then-yield operation
# ----------------------------------------------------------------------
@dataclass
class DispatchAndYieldResult:
    """[ROLE]
    - Teleology: Carry the outcome of a bridge_dispatch_and_yield call so the caller can decide whether to end the turn without raising.
    - Ownership: Owns ok flag, job_id, trigger_path, ledger_path, bridge_outcome dict, and optional error string.
    - Mutability: Immutable after construction; read-only by callers.
    - Concurrency: Safe to share; read-only after construction.
    """

    ok: bool
    job_id: str
    trigger_path: Optional[str]
    ledger_path: str
    bridge_outcome: Optional[dict[str, Any]]
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


BridgeDriver = Any  # Callable[[ResumeJob, dict[str, Any]], dict[str, Any]] — see below


def bridge_dispatch_and_yield(
    *,
    job_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    group_label: Optional[str] = None,
    bridge_driver: BridgeDriver,
    driver_context: Optional[dict[str, Any]] = None,
    status_from_outcome: Optional[Any] = None,
    summary_from_outcome: Optional[Any] = None,
    artifacts_from_outcome: Optional[Any] = None,
    continue_instruction: str = "",
    target: Optional[ResumeTarget] = None,
    manager: Optional[BridgeResumeManager] = None,
    allow_dup: bool = False,
) -> DispatchAndYieldResult:
    """[ACTION]
    - Teleology: Execute the canonical dispatch-then-stop op: run a bridge driver synchronously, record ledger state, and emit a resume trigger so the daemon can reawaken this session.
    - Guarantee: Returns DispatchAndYieldResult with ok=True when the trigger was written; ok=False on missing target, driver exception, or emit failure — never raises.
    - Fails: Returns ok=False with error populated; individual failure modes (no target, driver raise, emit raise) are captured and not propagated.
    - When-needed: Open when a local agent needs the canonical dispatch-then-stop primitive that records ledger state and schedules a later resume into the same Claude session.
    - Escalates-to: tools/meta/bridge/bridge_resume.py::BridgeResumeManager.emit_trigger; codex/doctrine/skills/bridge_runtime/dispatch_yield.md
    """
    if target is None and manager is None:
        target = discover_resume_target()
        if target is None:
            return DispatchAndYieldResult(
                ok=False,
                job_id=job_id or "",
                trigger_path=None,
                ledger_path="",
                bridge_outcome=None,
                error="no resume target persisted; run `bridge_resume set-target` first",
            )
    if manager is None:
        assert target is not None
        manager = BridgeResumeManager(target)

    job = ResumeJob(
        job_id=job_id or ResumeJob.new_id(prefix="dispatch"),
        plan_id=plan_id,
        group_label=group_label,
        status="ok",
        summary_lines=[],
        artifact_paths=[],
        continue_instruction=continue_instruction,
    )

    # Record the dispatch intent before we even call the driver so a
    # crash mid-driver is observable in the ledger. `job_states()` rolls
    # this up to bucket=pending until the driver either finishes and
    # promotes it to trigger_written/inject_ok, or fails and promotes it
    # to dispatch_failed.
    manager.append_ledger(
        "dispatch_scheduled",
        job.job_id,
        plan_id=plan_id,
        group_label=group_label,
    )

    outcome: Optional[dict[str, Any]] = None
    try:
        outcome = bridge_driver(job, dict(driver_context or {}))
    except Exception as exc:
        manager.append_ledger(
            "dispatch_failed",
            job.job_id,
            error=f"{type(exc).__name__}: {exc}",
        )
        return DispatchAndYieldResult(
            ok=False,
            job_id=job.job_id,
            trigger_path=None,
            ledger_path=str(manager.ledger_path),
            bridge_outcome=None,
            error=f"bridge_driver raised: {type(exc).__name__}: {exc}",
        )

    # Let the caller decide how to extract status/summary/artifacts from
    # the driver's result. Defaults: dict keys "status", "summary_lines",
    # "artifacts".
    def _default_status(out: dict[str, Any]) -> str:
        return str(out.get("status", "ok"))

    def _default_summary(out: dict[str, Any]) -> list[str]:
        val = out.get("summary_lines")
        if isinstance(val, list):
            return [str(x) for x in val]
        return []

    def _default_artifacts(out: dict[str, Any]) -> list[str]:
        val = out.get("artifacts") or out.get("artifact_paths")
        if isinstance(val, list):
            return [str(x) for x in val]
        return []

    job.status = (status_from_outcome or _default_status)(outcome or {})
    job.summary_lines = list(
        (summary_from_outcome or _default_summary)(outcome or {})
    )
    job.artifact_paths = list(
        (artifacts_from_outcome or _default_artifacts)(outcome or {})
    )

    manager.append_ledger(
        "dispatch_completed",
        job.job_id,
        outcome_status=job.status,
        summary_count=len(job.summary_lines),
        artifact_count=len(job.artifact_paths),
    )

    try:
        trigger_path = manager.emit_trigger(job, allow_dup=allow_dup)
    except Exception as exc:
        manager.append_ledger(
            "dispatch_emit_failed",
            job.job_id,
            error=f"{type(exc).__name__}: {exc}",
        )
        return DispatchAndYieldResult(
            ok=False,
            job_id=job.job_id,
            trigger_path=None,
            ledger_path=str(manager.ledger_path),
            bridge_outcome=outcome,
            error=f"emit_trigger raised: {type(exc).__name__}: {exc}",
        )

    return DispatchAndYieldResult(
        ok=trigger_path is not None,
        job_id=job.job_id,
        trigger_path=str(trigger_path) if trigger_path else None,
        ledger_path=str(manager.ledger_path),
        bridge_outcome=outcome,
        error=None if trigger_path is not None else "trigger was deduped",
    )


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _cmd_show(args: argparse.Namespace) -> int:
    target = discover_resume_target()
    rec = read_transport()
    extras = (rec or {}).get("extras") or {}
    bridge_resume = extras.get("bridge_resume") or {}
    out = {
        "transport_path": str(TRANSPORT_PATH),
        "resume_target": target.to_dict() if target else None,
        "ledger_path": bridge_resume.get("ledger_path") or str(default_ledger_path()),
        "inbox_dir": str(default_inbox_dir()),
        "current_session_id_guess": discover_current_session_id(),
        "supported_modes": list(RESUME_MODES),
    }
    print(json.dumps(out, indent=2))
    return 0


def _cmd_set_target(args: argparse.Namespace) -> int:
    session_id = args.session_id
    if session_id == "auto":
        session_id = discover_current_session_id()
    elif session_id == "":
        session_id = None
    # Coerce numeric switch_tab strings to int for cleanliness on disk.
    switch_tab: int | str | None = args.switch_tab
    if isinstance(switch_tab, str) and switch_tab.isdigit():
        switch_tab = int(switch_tab)
    target = ResumeTarget(
        target_app=args.target_app,
        switch_tab=switch_tab,
        session_id=session_id,
        session_url=args.session_url or None,
        sentinel_prefix=args.sentinel_prefix,
    )
    path = write_resume_target(target)
    print(json.dumps({
        "ok": True,
        "transport_path": str(path),
        "resume_target": target.to_dict(),
    }, indent=2))
    return 0


def _cmd_clear_target(args: argparse.Namespace) -> int:
    removed = clear_resume_target()
    print(json.dumps({"ok": True, "removed": removed}, indent=2))
    return 0 if removed else 1


def _cmd_emit(args: argparse.Namespace) -> int:
    target = discover_resume_target()
    if target is None:
        sys.stderr.write(
            "no resume target persisted; run `set-target` first\n"
        )
        return 2
    job = ResumeJob(
        job_id=args.job_id or ResumeJob.new_id(prefix=args.prefix),
        plan_id=args.plan_id or None,
        group_label=args.group or None,
        status=args.status,
        summary_lines=list(args.summary or []),
        artifact_paths=list(args.artifact or []),
        continue_instruction=args.continue_,
    )
    manager = BridgeResumeManager(target)
    path = manager.emit_trigger(
        job,
        allow_dup=args.allow_dup,
        submit=not args.no_submit,
    )
    out = {
        "ok": path is not None,
        "job_id": job.job_id,
        "trigger_path": str(path) if path else None,
        "deduped": path is None,
        "ledger_path": str(manager.ledger_path),
        "submit": not args.no_submit,
    }
    print(json.dumps(out, indent=2))
    return 0 if path is not None else 0  # dedupe is a successful no-op


def _cmd_ledger(args: argparse.Namespace) -> int:
    target = discover_resume_target()
    manager = BridgeResumeManager(target or ResumeTarget())
    rows = manager.ledger_rows(job_id=args.job_id or None, limit=args.tail)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


DEFAULT_STALE_PENDING_THRESHOLD_HOURS = 6.0


def _parse_ledger_ts(ts: Optional[str]) -> Optional[datetime]:
    """Parse the Zulu ISO-8601 timestamp produced by `_utc_now_iso`.

    Stale-pending detection leans on this; a parse failure must skip aging
    rather than raise, so unknown / future formats degrade to "age unknown".
    """
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _age_seconds(last_seen: Optional[str], now: datetime) -> Optional[float]:
    parsed = _parse_ledger_ts(last_seen)
    if parsed is None:
        return None
    return (now - parsed).total_seconds()


def _annotate_pending_with_age(
    rows: list[dict[str, Any]],
    *,
    now: datetime,
    stale_threshold_hours: float,
) -> list[dict[str, Any]]:
    """Return a copy of pending rows with `age_hours` and `is_stale` fields.

    Rows with unparseable `last_seen` get `age_hours=None` and `is_stale=None`
    so callers can still distinguish "never aged" from "fresh / stale".
    """
    threshold_s = float(stale_threshold_hours) * 3600.0
    out: list[dict[str, Any]] = []
    for rec in rows:
        age_s = _age_seconds(rec.get("last_seen"), now)
        annotated = dict(rec)
        if age_s is None:
            annotated["age_hours"] = None
            annotated["is_stale"] = None
        else:
            annotated["age_hours"] = round(age_s / 3600.0, 3)
            annotated["is_stale"] = bool(age_s >= threshold_s)
        out.append(annotated)
    return out


def _partition_stale_pending(
    annotated: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split annotated pending rows into (active, stale) by `is_stale`.

    Rows with `is_stale=None` (unparseable timestamp) flow into `active`
    so the operator still sees them in the live cohort instead of silently
    quarantining them.
    """
    active: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    for rec in annotated:
        if rec.get("is_stale") is True:
            stale.append(rec)
        else:
            active.append(rec)
    return active, stale


def _bucket_jobs(states: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Index a job_states() projection by bucket label."""
    out: dict[str, list[dict[str, Any]]] = {
        "pending": [],
        "succeeded": [],
        "failed": [],
        "deduped": [],
        "blocked_already_injected": [],
        "blocked_not_idle": [],
        "unknown": [],
    }
    for jid, rec in states.items():
        bucket = bucket_for_event(rec.get("current_state"))
        out.setdefault(bucket, []).append(
            {
                "job_id": jid,
                "current_state": rec.get("current_state"),
                "first_seen": rec.get("first_seen"),
                "last_seen": rec.get("last_seen"),
            }
        )
    return out


def _provider_pressure_summary(repo_root: Path, *, limit: int = 4) -> dict[str, Any]:
    try:
        conn = metabolism_store.connect(repo_root)
    except Exception as exc:
        return {
            "schema": "provider_pressure_summary_v1",
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "active_claims": 0,
            "blocked": [],
            "providers": [],
        }
    try:
        rows = metabolism_scheduler.provider_runtime_status(conn)
    finally:
        conn.close()
    assert isinstance(rows, list)
    projected = [
        {
            "provider": row.get("provider"),
            "blocked": bool(row.get("blocked")),
            "reason": row.get("reason"),
            "cooldown_until": row.get("cooldown_until"),
            "active_total": row.get("active_total"),
            "max_concurrent": row.get("max_concurrent"),
            "active_job_count": row.get("active_job_count"),
            "active_runtime_claim_count": row.get("active_runtime_claim_count"),
        }
        for row in rows
        if row.get("blocked")
        or row.get("cooldown_until")
        or int(row.get("active_runtime_claim_count") or 0) > 0
        or int(row.get("active_job_count") or 0) > 0
    ]
    return {
        "schema": "provider_pressure_summary_v1",
        "available": True,
        "error": None,
        "active_claims": sum(
            int(row.get("active_runtime_claim_count") or 0)
            for row in rows
        ),
        "blocked": [row for row in projected if row.get("blocked")][:limit],
        "providers": projected[:limit],
    }


def _cmd_status(args: argparse.Namespace) -> int:
    """Compact resume-protocol health summary.

    Walks the ledger once and prints counts per bucket plus the most
    recent N pending jobs. Default output is JSON; pass --human for a
    text rollup that fits in a terminal pane.

    Pending is split by age into `pending_active` / `pending_stale` so
    abandoned trigger writes (e.g. an emit from weeks ago that no idle
    window ever picked up) surface as evidence instead of inflating the
    live pending count silently.
    """
    target = discover_resume_target()
    manager = BridgeResumeManager(target or ResumeTarget())
    states = manager.job_states()
    buckets = _bucket_jobs(states)
    counts = {k: len(v) for k, v in buckets.items()}
    counts["total"] = sum(counts.values())

    now = datetime.now(timezone.utc)
    stale_threshold_hours = float(
        getattr(args, "stale_pending_hours", DEFAULT_STALE_PENDING_THRESHOLD_HOURS)
        or DEFAULT_STALE_PENDING_THRESHOLD_HOURS
    )

    pending_annotated = _annotate_pending_with_age(
        buckets["pending"],
        now=now,
        stale_threshold_hours=stale_threshold_hours,
    )
    pending_active, pending_stale = _partition_stale_pending(pending_annotated)

    counts["pending_active"] = len(pending_active)
    counts["pending_stale"] = len(pending_stale)

    payload = {
        "schema_version": RESUME_SCHEMA_VERSION,
        "ledger_path": str(manager.ledger_path),
        "inbox_dir": str(manager.inbox_dir),
        "resume_target": target.to_dict() if target else None,
        "counts": counts,
        "stale_pending_threshold_hours": stale_threshold_hours,
        "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider_pressure": _provider_pressure_summary(REPO_ROOT),
        "recent_pending": pending_annotated[: args.recent],
        "recent_pending_active": pending_active[: args.recent],
        "recent_pending_stale": pending_stale[: args.recent],
        "recent_failed": buckets["failed"][: args.recent],
        "recent_blocked": (
            buckets["blocked_not_idle"][: args.recent]
            + buckets["blocked_already_injected"][: args.recent]
        ),
    }
    if args.human:
        print("bridge resume status")
        print(f"  schema:   {RESUME_SCHEMA_VERSION}")
        print(f"  ledger:   {manager.ledger_path}")
        print(f"  target:   {target.target_app if target else '(none)'}"
              f" tab={target.switch_tab if target else 'n/a'}")
        print(f"  evaluated_at:        {payload['evaluated_at']}")
        print(f"  stale_pending_after: {stale_threshold_hours:.2f}h")
        print("  counts:")
        for key in ("pending", "pending_active", "pending_stale",
                    "succeeded", "failed", "deduped",
                    "blocked_not_idle", "blocked_already_injected",
                    "unknown", "total"):
            print(f"    {key:<26}{counts.get(key, 0)}")
        provider_pressure = payload["provider_pressure"]
        if provider_pressure.get("available"):
            print(f"  provider claims: {provider_pressure.get('active_claims', 0)}")
            blocked = provider_pressure.get("blocked") or []
            if blocked:
                print("  provider pressure:")
                for rec in blocked:
                    summary = str(rec.get("reason") or "").strip() or (
                        f"load {rec.get('active_total')}/{rec.get('max_concurrent')}"
                    )
                    print(f"    - {rec['provider']} {summary}")
        if payload["recent_pending_active"]:
            print("  recent pending (active):")
            for rec in payload["recent_pending_active"]:
                age = rec.get("age_hours")
                age_label = f"{age:.2f}h" if isinstance(age, (int, float)) else "age=unknown"
                print(f"    - {rec['job_id']} (last_seen={rec['last_seen']}, age={age_label})")
        if payload["recent_pending_stale"]:
            print("  recent pending (stale — likely abandoned):")
            for rec in payload["recent_pending_stale"]:
                age = rec.get("age_hours")
                age_label = f"{age:.2f}h" if isinstance(age, (int, float)) else "age=unknown"
                print(f"    - {rec['job_id']} (last_seen={rec['last_seen']}, age={age_label})")
        if payload["recent_failed"]:
            print("  recent failed:")
            for rec in payload["recent_failed"]:
                print(f"    - {rec['job_id']} (last_seen={rec['last_seen']})")
        if payload["recent_blocked"]:
            print("  recent blocked:")
            for rec in payload["recent_blocked"]:
                print(f"    - {rec['job_id']} ({rec['current_state']})")
        return 0
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_jobs(args: argparse.Namespace) -> int:
    """List every job_id known to the ledger, newest-first.

    Filters:
      --bucket pending|succeeded|failed|deduped|blocked_not_idle|blocked_already_injected|unknown
      --limit N         (default 20)
      --since-iso TS    (only jobs whose last_seen >= TS)

    Output is JSON unless --human is given.
    """
    target = discover_resume_target()
    manager = BridgeResumeManager(target or ResumeTarget())
    states = manager.job_states()
    rows: list[dict[str, Any]] = []
    for jid, rec in states.items():
        bucket = bucket_for_event(rec.get("current_state"))
        if args.bucket and bucket != args.bucket:
            continue
        if args.since_iso and (rec.get("last_seen") or "") < args.since_iso:
            continue
        rows.append(
            {
                "job_id": jid,
                "bucket": bucket,
                "current_state": rec.get("current_state"),
                "first_seen": rec.get("first_seen"),
                "last_seen": rec.get("last_seen"),
                "event_count": len(rec.get("events") or []),
            }
        )
    rows = rows[: args.limit]
    if args.human:
        if not rows:
            print("(no jobs match)")
            return 0
        for r in rows:
            print(
                f"{r['last_seen']}  {r['bucket']:<26}{r['job_id']}"
                f"  state={r['current_state']}  events={r['event_count']}"
            )
        return 0
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def _cmd_job(args: argparse.Namespace) -> int:
    """Show the full event sequence for one job_id.

    This is the operator's debug surface when something goes wrong: the
    output includes every ledger row for the job (in chronological order)
    plus the rolled-up current_state and bucket. Pair with `--ledger
    --job-id ...` if you want the raw rows without the rollup.
    """
    target = discover_resume_target()
    manager = BridgeResumeManager(target or ResumeTarget())
    rows = manager.ledger_rows(job_id=args.job_id)
    if not rows:
        sys.stderr.write(f"no ledger rows for job_id={args.job_id}\n")
        return 1
    states = manager.job_states()
    rec = states.get(args.job_id) or {}
    payload = {
        "job_id": args.job_id,
        "current_state": rec.get("current_state"),
        "bucket": bucket_for_event(rec.get("current_state")),
        "first_seen": rec.get("first_seen"),
        "last_seen": rec.get("last_seen"),
        "event_count": len(rows),
        "rows": rows,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bridge_resume",
        description="Bridge -> Claude.app resume protocol manager.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_show = sub.add_parser("show", help="Print the persisted resume target.")
    p_show.set_defaults(func=_cmd_show)

    p_set = sub.add_parser(
        "set-target",
        help="Persist a ResumeTarget into claude_session_transport.json.",
    )
    p_set.add_argument("--target-app", default="Claude")
    p_set.add_argument("--switch-tab", default=3)
    p_set.add_argument(
        "--session-id",
        default="auto",
        help='CLI session id, or "auto" to detect from disk, or "" for none.',
    )
    p_set.add_argument("--session-url", default=None)
    p_set.add_argument("--sentinel-prefix", default=DEFAULT_SENTINEL_PREFIX)
    p_set.set_defaults(func=_cmd_set_target)

    p_clear = sub.add_parser("clear-target", help="Remove the persisted resume target.")
    p_clear.set_defaults(func=_cmd_clear_target)

    p_emit = sub.add_parser(
        "emit",
        help="Build a ResumeJob and write a trigger file into the injector inbox.",
    )
    p_emit.add_argument("--job-id", default=None)
    p_emit.add_argument("--prefix", default="bridge")
    p_emit.add_argument("--plan-id", default=None)
    p_emit.add_argument("--group", default=None)
    p_emit.add_argument("--status", default="ok")
    p_emit.add_argument(
        "--summary",
        action="append",
        default=[],
        help="Summary line (repeatable).",
    )
    p_emit.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact path (repeatable).",
    )
    p_emit.add_argument("--continue", dest="continue_", default="")
    p_emit.add_argument(
        "--allow-dup",
        action="store_true",
        help="Bypass ledger dedupe check (force a second injection).",
    )
    p_emit.add_argument(
        "--no-submit",
        action="store_true",
        help=(
            "Write a trigger that pastes into Claude.app but leaves the "
            "message staged in the Code tab input instead of pressing Return."
        ),
    )
    p_emit.set_defaults(func=_cmd_emit)

    p_ledger = sub.add_parser("ledger", help="Print resume ledger rows.")
    p_ledger.add_argument("--job-id", default=None)
    p_ledger.add_argument("--tail", type=int, default=20)
    p_ledger.set_defaults(func=_cmd_ledger)

    p_status = sub.add_parser(
        "status",
        help="Compact health summary: counts per bucket + recent jobs.",
    )
    p_status.add_argument(
        "--recent",
        type=int,
        default=5,
        help="How many recent pending/failed/blocked jobs to show.",
    )
    p_status.add_argument(
        "--human",
        action="store_true",
        help="Plain-text output instead of JSON.",
    )
    p_status.add_argument(
        "--stale-pending-hours",
        dest="stale_pending_hours",
        type=float,
        default=DEFAULT_STALE_PENDING_THRESHOLD_HOURS,
        help=(
            "Pending jobs whose last_seen is older than this many hours are "
            "split into the `pending_stale` cohort (default: %(default)s)."
        ),
    )
    p_status.set_defaults(func=_cmd_status)

    p_jobs = sub.add_parser(
        "jobs",
        help="List jobs (newest-first) with optional bucket / since filters.",
    )
    p_jobs.add_argument(
        "--bucket",
        default=None,
        choices=sorted(set(EVENT_BUCKETS.values()) | {"unknown"}),
        help="Filter to one bucket.",
    )
    p_jobs.add_argument("--limit", type=int, default=20)
    p_jobs.add_argument(
        "--since-iso",
        default=None,
        help="ISO timestamp; only jobs with last_seen >= this are shown.",
    )
    p_jobs.add_argument("--human", action="store_true")
    p_jobs.set_defaults(func=_cmd_jobs)

    p_job = sub.add_parser(
        "job",
        help="Show every ledger row for one job_id, plus the rollup.",
    )
    p_job.add_argument("job_id")
    p_job.set_defaults(func=_cmd_job)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
