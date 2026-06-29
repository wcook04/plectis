"""
Public agent observability trace-store substrate.

This module is a source-faithful public refactor of
`system/lib/agent_observability.py`. It preserves the macro AgentEvent /
AgentTraceStore mechanics that make route decisions and trace capsules
inspectable, while accepting only explicit public metadata envelopes. It does
not read live home session logs, provider payload bodies, browser/HUD state,
account/session state, credentials, cookies, or recipient-send material.

[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.agent_observability_store` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: PASS, BLOCKED, KIND, SCHEMA_VERSION, SOURCE_REF, TARGET_REF, SOURCE_REFS, TARGET_REFS, SOURCE_SYMBOL_REFS, TARGET_SYMBOL_REFS, AUTHORITY_CEILING, ANTI_CLAIM, INPUT_NAMES, ACTIVITY_CANONICAL_TYPES, TRACE_DECISION_TYPES, FORBIDDEN_PAYLOAD_KEYS, MAX_EVENT_LINE_BYTES, MAX_PAYLOAD_VALUE_BYTES, MAX_PAYLOAD_CONTAINER_ITEMS, HASH_CHUNK_SIZE, AgentEvent, AgentTraceStore, PublicAgentObservabilitySampler, load_public_agent_observability_store_bundle, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import queue
import threading
from collections import Counter, deque
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, cast

from microcosm_core.schemas import read_json_strict

PASS = "pass"
BLOCKED = "blocked"

KIND = "public_agent_observability_store"
SCHEMA_VERSION = "public_agent_observability_store_v1"
SOURCE_REF = "system/lib/agent_observability.py"
TARGET_REF = "microcosm-substrate/src/microcosm_core/macro_tools/agent_observability_store.py"
SOURCE_REFS = [
    SOURCE_REF,
    "codex/standards/std_agent_execution_trace.json",
    "codex/doctrine/paper_modules/agent_observability.md",
    "codex/doctrine/paper_modules/agent_self_observability_plane.md",
    "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json#agent_self_observability_plane",
]
TARGET_REFS = [TARGET_REF]
SOURCE_SYMBOL_REFS = [
    "system/lib/agent_observability.py::AgentEvent",
    "system/lib/agent_observability.py::AgentTraceStore",
    "system/lib/agent_observability.py::AgentObservabilitySampler",
    "system/lib/agent_observability.py::_compact_event_if_oversized",
    "system/lib/agent_observability.py::ingest_recent_codex_rollouts",
    "system/lib/agent_observability.py::ingest_recent_claude_transcripts",
]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.agent_observability_store::AgentEvent",
    "microcosm_core.macro_tools.agent_observability_store::AgentTraceStore",
    "microcosm_core.macro_tools.agent_observability_store::PublicAgentObservabilitySampler",
    "microcosm_core.macro_tools.agent_observability_store::build_public_agent_observability_store_view",
    "microcosm_core.macro_tools.agent_observability_store::load_public_agent_observability_store_bundle",
]

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_agent_observability_store_metadata_not_live_session_authority",
    "live_home_session_logs_read": False,
    "live_transcript_tail_authorized": False,
    "live_process_probe_authorized": False,
    "operator_bridge_poll_authorized": False,
    "raw_transcript_body_exported": False,
    "provider_payload_read": False,
    "hidden_reasoning_exported": False,
    "browser_hud_cockpit_state_exported": False,
    "account_session_state_exported": False,
    "credential_or_cookie_exported": False,
    "recipient_send_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "private_data_equivalence_claim": False,
}
ANTI_CLAIM = (
    "Agent observability store replay validates public event metadata, bounded "
    "payload compaction, source/canonical counters, active-session summaries, "
    "telemetry queue behavior, and safe route-decision digests. It does not "
    "read live home session logs, transcript bodies, provider payloads, hidden "
    "reasoning, browser/HUD state, account/session state, credentials, cookies, "
    "recipient-send material, or launch resident samplers."
)

INPUT_NAMES = (
    "bundle_manifest.json",
    "public_agent_events.json",
    "observability_policy.json",
    "expected_store_summary.json",
)
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
TRACE_DECISION_TYPES = {
    "route.decision",
    "route.lease",
    "tool.proposed",
    "tool.started",
    "tool.completed",
    "runtime.error",
}
FORBIDDEN_PAYLOAD_KEYS = {
    "raw_transcript_body",
    "transcript_body",
    "provider_payload",
    "hidden_reasoning",
    "thinking_signature",
    "browser_hud_state",
    "browser_hud_cockpit_state",
    "account_session_state",
    "credential_value",
    "cookie",
    "password",
    "secret_value",
    "api_key",
    "access_token",
    "refresh_token",
    "recipient_send_payload",
    "live_operator_state",
    "live_session_state",
}
MAX_EVENT_LINE_BYTES = 64 * 1024
MAX_PAYLOAD_VALUE_BYTES = 16 * 1024
MAX_PAYLOAD_CONTAINER_ITEMS = 80
HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class AgentEvent:
    """
    [ROLE]
    - Teleology: Groups `AgentEvent` data or behavior for `microcosm_core.macro_tools.agent_observability_store` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.macro_tools.agent_observability_store`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
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
    cwd_ref: Optional[str] = None
    transcript_ref: Optional[str] = None
    artifact_refs: list[str] = field(default_factory=list)
    occurred_at: Optional[str] = None
    summary: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `AgentEvent.to_dict` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        return _json_safe(asdict(self))


class AgentTraceStore:
    """
    [ROLE]
    Thread-safe append-only public trace materializer.
    - Teleology: Groups `AgentTraceStore` data or behavior for `microcosm_core.macro_tools.agent_observability_store` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.macro_tools.agent_observability_store`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """

    def __init__(self, *, max_history: int = 2000, queue_size: int = 5000) -> None:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.__init__` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        self.max_history = max(1, int(max_history))
        self._lock = threading.RLock()
        self._history: deque[dict[str, Any]] = deque(maxlen=self.max_history)
        self._telemetry_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=queue_size)
        self._seq = 0
        self._dropped_count = 0
        self._gap_count = 0
        self._source_status: dict[str, dict[str, Any]] = {}
        self._active_sessions: dict[str, dict[str, Any]] = {}
        self._canonical_counts: Counter[str] = Counter()
        self._source_counts: Counter[str] = Counter()

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
        cwd_ref: Optional[str] = None,
        transcript_ref: Optional[str] = None,
        artifact_refs: Optional[list[str]] = None,
        occurred_at: Optional[str] = None,
        observed_at: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.emit` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        safe_payload = _json_safe(dict(payload or {}))
        blocked_keys = sorted(FORBIDDEN_PAYLOAD_KEYS & _walk_payload_keys(safe_payload))
        if blocked_keys:
            raise ValueError(f"public agent event contains forbidden payload keys: {', '.join(blocked_keys)}")
        resolved_session_id = (
            str(session_id or safe_payload.get("session_id") or safe_payload.get("thread_id") or "").strip()
            or "unknown"
        )
        resolved_trace_id = str(trace_id or safe_payload.get("trace_id") or resolved_session_id).strip() or resolved_session_id

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
                turn_id=turn_id or _optional_str(safe_payload.get("turn_id")),
                tool_use_id=tool_use_id or _optional_str(safe_payload.get("tool_use_id") or safe_payload.get("call_id")),
                subagent_id=subagent_id or _optional_str(safe_payload.get("subagent_id") or safe_payload.get("agent_id")),
                cwd_ref=cwd_ref or _optional_str(safe_payload.get("cwd_ref")),
                transcript_ref=transcript_ref or _optional_str(safe_payload.get("transcript_ref")),
                artifact_refs=list(artifact_refs or []),
                observed_at=observed_at or _now_iso(),
                occurred_at=occurred_at or _optional_str(safe_payload.get("timestamp")),
                summary=summary,
                payload=safe_payload,
            ).to_dict()
            event = _compact_event_if_oversized(event)
            self._history.append(event)
            self._index_event_locked(event)

        try:
            self._telemetry_queue.put_nowait(event)
        except queue.Full:
            with self._lock:
                self._dropped_count += 1
        return event

    def emit_gap(self, *, source_runtime: str, reason: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.emit_gap` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        return self.emit(
            source_runtime=source_runtime,
            source_event_name="stream_gap",
            canonical_type="stream.gap",
            payload={"reason": reason, **dict(payload or {})},
            summary=f"gap: {reason}",
        )

    def ingest_public_event(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.ingest_public_event` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        return self.emit(
            source_runtime=str(row.get("source_runtime") or "public_replay"),
            source_event_name=str(row.get("source_event_name") or row.get("event_name") or "public_event"),
            canonical_type=str(row.get("canonical_type") or "runtime.event"),
            payload=payload,
            session_id=_optional_str(row.get("session_id")),
            trace_id=_optional_str(row.get("trace_id")),
            parent_id=_optional_str(row.get("parent_id")),
            turn_id=_optional_str(row.get("turn_id")),
            tool_use_id=_optional_str(row.get("tool_use_id")),
            subagent_id=_optional_str(row.get("subagent_id")),
            cwd_ref=_optional_str(row.get("cwd_ref")),
            transcript_ref=_optional_str(row.get("transcript_ref")),
            artifact_refs=_strings(row.get("artifact_refs")),
            occurred_at=_optional_str(row.get("occurred_at")),
            observed_at=_optional_str(row.get("observed_at")),
            summary=_compact_summary(row.get("summary") or payload.get("summary")),
        )

    def get_telemetry_nowait(self) -> Optional[dict[str, Any]]:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.get_telemetry_nowait` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
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
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.replay` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        limit = max(1, min(int(limit or 500), self.max_history))
        with self._lock:
            events = list(self._history)
        rows: list[dict[str, Any]] = []
        for event in events:
            if int(event.get("seq") or 0) <= since_seq:
                continue
            if session_id and event.get("session_id") != session_id:
                continue
            if source_runtime and event.get("source_runtime") != source_runtime:
                continue
            if canonical_type and event.get("canonical_type") != canonical_type:
                continue
            rows.append(event)
        return rows[-limit:]

    def status(self) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore.status` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        with self._lock:
            active_sessions = sorted(
                self._active_sessions.values(),
                key=lambda item: str(item.get("last_observed_at") or ""),
                reverse=True,
            )
            return {
                "schema": SCHEMA_VERSION,
                "seq": self._seq,
                "history_size": len(self._history),
                "max_history": self.max_history,
                "dropped_count": self._dropped_count,
                "gap_count": self._gap_count,
                "source_status": sorted(self._source_status.values(), key=lambda row: row["source_runtime"]),
                "active_sessions": active_sessions[:50],
                "canonical_counts": dict(self._canonical_counts),
                "source_counts": dict(self._source_counts),
                "authority_ceiling": AUTHORITY_CEILING,
            }

    def _index_event_locked(self, event: Mapping[str, Any]) -> None:
        """
        [ACTION]
        - Teleology: Implements `AgentTraceStore._index_event_locked` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        canonical_type = str(event.get("canonical_type") or "unknown")
        source_runtime = str(event.get("source_runtime") or "unknown")
        session_id = str(event.get("session_id") or "unknown")
        observed_at = str(event.get("observed_at") or "")
        self._canonical_counts[canonical_type] += 1
        self._source_counts[source_runtime] += 1
        self._source_status[source_runtime] = {
            "source_runtime": source_runtime,
            "last_observed_at": observed_at or None,
            "last_canonical_type": canonical_type,
            "event_count": self._source_counts[source_runtime],
        }
        existing = self._active_sessions.get(
            session_id,
            {"session_id": session_id, "activity_count": 0, "touched_files": []},
        )
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        touched_files = list(existing.get("touched_files") or [])
        for path in _event_touched_files(event):
            if path not in touched_files:
                touched_files.append(path)
        if len(touched_files) > 12:
            touched_files = touched_files[-12:]
        title = existing.get("title")
        payload_title = _session_title_from_text(payload.get("title") or payload.get("session_title"))
        if payload_title and not title:
            title = payload_title
        if not title and canonical_type in {"message.user", "turn.prompt"}:
            title = _session_title_from_text(payload.get("content") or event.get("summary"))
        if not title and canonical_type in {"message.assistant", "intent.observed", "plan.observed"}:
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
            "cwd_ref": event.get("cwd_ref") or existing.get("cwd_ref"),
            "transcript_ref": event.get("transcript_ref") or existing.get("transcript_ref"),
            "summary": event.get("summary") or existing.get("summary"),
            "title": title,
            "activity_count": activity_count,
            "last_activity_at": observed_at if is_activity else existing.get("last_activity_at"),
            "current_activity": event.get("summary") if is_activity else existing.get("current_activity"),
            "touched_files": touched_files,
        }
        if canonical_type == "stream.gap":
            self._gap_count += 1


class PublicAgentObservabilitySampler:
    """
    [ROLE]
    Deterministic public sampler wrapper over explicit metadata snapshots.
    - Teleology: Groups `PublicAgentObservabilitySampler` data or behavior for `microcosm_core.macro_tools.agent_observability_store` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.macro_tools.agent_observability_store`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """

    def __init__(self, store: AgentTraceStore) -> None:
        """
        [ACTION]
        - Teleology: Implements `PublicAgentObservabilitySampler.__init__` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        self.store = store
        self.poll_count = 0

    def ingest_snapshot(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `PublicAgentObservabilitySampler.ingest_snapshot` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        self.poll_count += 1
        return self.store.emit(
            source_runtime="public_sampler",
            source_event_name="public_sampler_snapshot",
            canonical_type="runtime.heartbeat",
            session_id=str(snapshot.get("session_id") or "public_agent_observability"),
            trace_id=str(snapshot.get("trace_id") or snapshot.get("session_id") or "public_agent_observability"),
            payload={
                "poll_count": self.poll_count,
                "source_counts": snapshot.get("source_counts", {}),
                "canonical_counts": snapshot.get("canonical_counts", {}),
                "metadata_envelope_only": True,
            },
            summary="public agent observability sampler metadata snapshot",
        )


def load_public_agent_observability_store_bundle(input_dir: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_public_agent_observability_store_bundle` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root = Path(input_dir)
    return {
        path.stem: cast(dict[str, Any], read_json_strict(path))
        for path in (root / name for name in INPUT_NAMES)
    }


def build_public_agent_observability_store_view(payloads: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_agent_observability_store_view` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest = payloads.get("bundle_manifest") if isinstance(payloads.get("bundle_manifest"), Mapping) else {}
    events_payload = payloads.get("public_agent_events") if isinstance(payloads.get("public_agent_events"), Mapping) else {}
    policy = payloads.get("observability_policy") if isinstance(payloads.get("observability_policy"), Mapping) else {}
    expected = payloads.get("expected_store_summary") if isinstance(payloads.get("expected_store_summary"), Mapping) else {}

    store = AgentTraceStore(max_history=int(manifest.get("max_history") or 2000))
    event_rows = _rows(events_payload, "events")
    findings: list[dict[str, Any]] = []
    event_decisions: list[dict[str, Any]] = []
    redacted_payload_count = 0
    metadata_digest_count = 0
    for row in event_rows:
        event_id = str(row.get("event_id") or row.get("id") or "public_event")
        row_findings = _validate_public_event_row(row, event_id=event_id)
        findings.extend(row_findings)
        if row.get("payload_redacted") is True:
            redacted_payload_count += 1
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        if payload.get("metadata_digest"):
            metadata_digest_count += 1
        if not row_findings:
            try:
                event = store.ingest_public_event(row)
                event_decisions.append(
                    {
                        "event_id": event_id,
                        "seq": event["seq"],
                        "canonical_type": event["canonical_type"],
                        "session_id": event["session_id"],
                        "decision": "accepted",
                        "error_codes": [],
                        "body_in_receipt": False,
                    }
                )
            except ValueError as exc:
                code = "AGENT_OBSERVABILITY_STORE_EVENT_BLOCKED"
                findings.append(_bundle_finding(code, str(exc), subject_id=event_id))
                event_decisions.append(
                    {
                        "event_id": event_id,
                        "decision": "blocked",
                        "error_codes": [code],
                        "body_in_receipt": False,
                    }
                )
        else:
            event_decisions.append(
                {
                    "event_id": event_id,
                    "decision": "blocked",
                    "error_codes": sorted({finding["error_code"] for finding in row_findings}),
                    "body_in_receipt": False,
                }
            )

    policy_validation = _validate_policy(policy)
    expected_validation = _validate_expected_summary(expected, store, redacted_payload_count, metadata_digest_count)
    findings.extend(policy_validation["findings"])
    findings.extend(expected_validation["findings"])
    status_payload = store.status()
    summary = _store_summary(status_payload, redacted_payload_count, metadata_digest_count)
    source_refs = _strings(manifest.get("source_refs")) or SOURCE_REFS
    target_refs = _strings(manifest.get("target_refs")) or TARGET_REFS
    forbidden_payload_keys = sorted(FORBIDDEN_PAYLOAD_KEYS & _walk_payload_keys(payloads))
    if forbidden_payload_keys:
        findings.extend(
            _bundle_finding(
                "AGENT_OBSERVABILITY_STORE_FORBIDDEN_PAYLOAD_KEY",
                "Public agent-observability inputs cannot include transcript bodies, provider payloads, hidden reasoning, browser/HUD state, account/session state, credentials, cookies, recipient-send payloads, or live session state.",
                subject_id=key,
            )
            for key in forbidden_payload_keys
        )

    status = (
        PASS
        if event_rows
        and store.replay()
        and not findings
        and policy_validation["status"] == PASS
        and expected_validation["status"] == PASS
        else BLOCKED
    )
    view_fingerprint = _stable_digest(
        {
            "bundle_id": manifest.get("bundle_id"),
            "summary": summary,
            "policy_id": policy_validation.get("policy_id"),
            "event_decisions": event_decisions,
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": status,
        "bundle_id": manifest.get("bundle_id"),
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "source_refs": source_refs,
        "target_refs": target_refs,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "body_import_verification": _body_import_verification(),
        "store_summary": summary,
        "status_snapshot": status_payload,
        "event_decisions": event_decisions,
        "policy_validation": policy_validation,
        "expected_summary_validation": expected_validation,
        "public_event_count": len(event_rows),
        "accepted_event_count": len(store.replay()),
        "active_session_count": len(status_payload["active_sessions"]),
        "source_runtime_count": len(status_payload["source_counts"]),
        "canonical_type_count": len(status_payload["canonical_counts"]),
        "redacted_payload_count": redacted_payload_count,
        "metadata_digest_count": metadata_digest_count,
        "forbidden_payload_keys": forbidden_payload_keys,
        "findings": findings,
        "view_fingerprint": view_fingerprint,
        "metadata_envelope_only": True,
        "body_in_receipt": False,
        "live_home_session_logs_read": False,
        "provider_payload_exported": False,
        "browser_hud_cockpit_state_exported": False,
        "account_session_state_exported": False,
        "credential_or_cookie_exported": False,
        "recipient_send_authorized": False,
    }


def _validate_public_event_row(row: Mapping[str, Any], *, event_id: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_validate_public_event_row` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    required = (
        "source_runtime",
        "source_event_name",
        "canonical_type",
        "session_id",
        "trace_id",
        "observed_at",
        "summary",
        "payload",
    )
    missing = [field for field in required if row.get(field) in (None, "", [])]
    if missing:
        findings.append(
            _bundle_finding(
                "AGENT_OBSERVABILITY_STORE_EVENT_FIELD_MISSING",
                f"Public agent event is missing required fields: {', '.join(missing)}.",
                subject_id=event_id,
            )
        )
    if row.get("metadata_envelope_only") is not True:
        findings.append(
            _bundle_finding(
                "AGENT_OBSERVABILITY_STORE_EVENT_NOT_METADATA_ONLY",
                "Public agent event must declare metadata_envelope_only.",
                subject_id=event_id,
            )
        )
    for field in (
        "raw_transcript_body_exported",
        "provider_payload_exported",
        "browser_hud_cockpit_state_exported",
        "account_session_state_exported",
        "credential_or_cookie_exported",
    ):
        if row.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "AGENT_OBSERVABILITY_STORE_EVENT_AUTHORITY_OVERCLAIM",
                    "Public agent event must reject transcript bodies, provider/browser/account state, and credentials.",
                    subject_id=event_id or field,
                )
            )
    leaked = sorted(FORBIDDEN_PAYLOAD_KEYS & _walk_payload_keys(row))
    for key in leaked:
        findings.append(
            _bundle_finding(
                "AGENT_OBSERVABILITY_STORE_FORBIDDEN_PAYLOAD_KEY",
                "Public agent event contains a forbidden payload key.",
                subject_id=f"{event_id}:{key}",
            )
        )
    return findings


def _validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_policy` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    required_false = (
        "live_home_session_logs_read",
        "live_transcript_tail_authorized",
        "live_process_probe_authorized",
        "operator_bridge_poll_authorized",
        "raw_transcript_body_exported",
        "provider_payload_read",
        "hidden_reasoning_exported",
        "browser_hud_cockpit_state_exported",
        "account_session_state_exported",
        "credential_or_cookie_exported",
        "recipient_send_authorized",
        "source_mutation_authorized",
        "release_authorized",
        "private_data_equivalence_claim",
    )
    for field in required_false:
        if policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "AGENT_OBSERVABILITY_STORE_POLICY_AUTHORITY_OVERCLAIM",
                    "Agent observability store policy must keep live/session/provider/account/release authority disabled.",
                    subject_id=field,
                    subject_kind="agent_observability_store_policy",
                )
            )
    if policy.get("metadata_envelope_only") is not True:
        findings.append(
            _bundle_finding(
                "AGENT_OBSERVABILITY_STORE_POLICY_NOT_METADATA_ONLY",
                "Agent observability store policy must declare metadata_envelope_only.",
                subject_id=str(policy.get("policy_id") or "observability_policy"),
                subject_kind="agent_observability_store_policy",
            )
        )
    return {
        "status": PASS if not findings else BLOCKED,
        "policy_id": policy.get("policy_id"),
        "forbidden_authority_rejected": not findings,
        "metadata_envelope_only": policy.get("metadata_envelope_only") is True,
        "findings": findings,
        "body_in_receipt": False,
    }


def _validate_expected_summary(
    expected: Mapping[str, Any],
    store: AgentTraceStore,
    redacted_payload_count: int,
    metadata_digest_count: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validate_expected_summary` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    actual = _store_summary(store.status(), redacted_payload_count, metadata_digest_count)
    fields = (
        "event_count",
        "active_session_count",
        "source_runtime_count",
        "route_decision_event_count",
        "tool_event_count",
        "metadata_digest_count",
        "redacted_payload_count",
    )
    mismatches = [
        {
            "field": field,
            "expected": expected.get(field),
            "actual": actual.get(field),
        }
        for field in fields
        if expected.get(field) != actual.get(field)
    ]
    findings = [
        _bundle_finding(
            "AGENT_OBSERVABILITY_STORE_EXPECTED_SUMMARY_MISMATCH",
            "Expected agent observability store summary does not match replayed public events.",
            subject_id=str(row["field"]),
            subject_kind="agent_observability_store_expected_summary",
        )
        for row in mismatches
    ]
    return {
        "status": PASS if not findings else BLOCKED,
        "expected_summary": dict(expected),
        "actual_summary": actual,
        "mismatches": mismatches,
        "findings": findings,
        "body_in_receipt": False,
    }


def _store_summary(
    status_payload: Mapping[str, Any],
    redacted_payload_count: int,
    metadata_digest_count: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_store_summary` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    canonical_counts = status_payload.get("canonical_counts") if isinstance(status_payload.get("canonical_counts"), Mapping) else {}
    source_counts = status_payload.get("source_counts") if isinstance(status_payload.get("source_counts"), Mapping) else {}
    event_count = int(status_payload.get("seq") or 0)
    route_decision_event_count = sum(
        int(canonical_counts.get(kind) or 0)
        for kind in TRACE_DECISION_TYPES
    )
    tool_event_count = sum(
        int(canonical_counts.get(kind) or 0)
        for kind in ("tool.proposed", "tool.started", "tool.completed")
    )
    activity_event_count = sum(
        int(canonical_counts.get(kind) or 0)
        for kind in ACTIVITY_CANONICAL_TYPES
    )
    return {
        "event_count": event_count,
        "history_size": int(status_payload.get("history_size") or 0),
        "active_session_count": len(status_payload.get("active_sessions") or []),
        "source_runtime_count": len(source_counts),
        "canonical_type_count": len(canonical_counts),
        "activity_event_count": activity_event_count,
        "route_decision_event_count": route_decision_event_count,
        "tool_event_count": tool_event_count,
        "gap_count": int(status_payload.get("gap_count") or 0),
        "dropped_count": int(status_payload.get("dropped_count") or 0),
        "metadata_digest_count": metadata_digest_count,
        "redacted_payload_count": redacted_payload_count,
        "source_counts": dict(source_counts),
        "canonical_counts": dict(canonical_counts),
        "body_in_receipt": False,
    }


def _json_safe(value: Any) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_json_safe` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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


def _compact_summary(text: object, *, limit: int = 220) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Implements `_compact_summary` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    raw = " ".join(str(text or "").strip().split())
    if not raw:
        return None
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 3)].rstrip() + "..."


def _session_title_from_text(text: object) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Implements `_session_title_from_text` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    summary = _compact_summary(text, limit=96)
    if not summary:
        return None
    summary = summary.lstrip("#").strip()
    return summary[:1].upper() + summary[1:] if summary else None


def _event_touched_files(event: Mapping[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_event_touched_files` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    candidates: list[Any] = []
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), Mapping) else {}
    candidates.extend(
        [
            tool_input.get("file_path"),
            tool_input.get("path"),
            tool_input.get("target_file"),
            payload.get("target_ref"),
        ]
    )
    for key in ("files", "paths", "file_paths", "target_refs"):
        value = tool_input.get(key) or payload.get(key)
        if isinstance(value, list):
            candidates.extend(value)
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


def _compact_json_bytes(value: Any, *, sort_keys: bool = False) -> bytes:
    """
    [ACTION]
    - Teleology: Implements `_compact_json_bytes` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=sort_keys).encode("utf-8")


def _large_value_ref(value: Any, *, value_type: str, original_bytes: int) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_large_value_ref` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    return {
        "compacted_payload_value": True,
        "value_type": value_type,
        "original_bytes": original_bytes,
        "sha256": hashlib.sha256(str(raw).encode("utf-8")).hexdigest(),
    }


def _compact_payload_value(value: Any, *, depth: int = 0) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_compact_payload_value` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
            compacted_items.append(
                {
                    "compacted_payload_value": True,
                    "value_type": "list_tail",
                    "omitted_item_count": len(value) - MAX_PAYLOAD_CONTAINER_ITEMS,
                }
            )
        return compacted_items
    return value


def _payload_skeleton(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_payload_skeleton` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    keep_keys = (
        "session_id",
        "trace_id",
        "turn_id",
        "tool_use_id",
        "call_id",
        "tool_name",
        "type",
        "timestamp",
        "cwd_ref",
        "transcript_ref",
        "metadata_digest",
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
            if key in {"file_path", "path", "command_digest", "description", "pattern", "query", "target_ref"}
        }
    return skeleton


def _compact_event_if_oversized(event: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_compact_event_if_oversized` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    if len(_compact_json_bytes(compacted)) <= MAX_EVENT_LINE_BYTES:
        compacted["payload_compaction"]["compacted_line_bytes"] = len(_compact_json_bytes(compacted))
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


def _walk_payload_keys(payload: object) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_walk_payload_keys` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(payload, Mapping):
        keys = {str(key) for key in payload}
        for value in payload.values():
            keys.update(_walk_payload_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for item in payload:
            keys.update(_walk_payload_keys(item))
        return keys
    return set()


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, Mapping):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _optional_str(value: object) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Implements `_optional_str` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if value in (None, ""):
        return None
    return str(value)


def _now_iso() -> str:
    """
    [ACTION]
    - Teleology: Implements `_now_iso` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _stable_digest(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_digest` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_file_sha256` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _repo_root_from_target() -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_repo_root_from_target` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for candidate in Path(__file__).resolve(strict=False).parents:
        if (candidate / SOURCE_REF).is_file():
            return candidate
    return None


def _body_import_verification() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_body_import_verification` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target_path = Path(__file__).resolve(strict=False)
    repo_root = _repo_root_from_target()
    source_path = repo_root / SOURCE_REF if repo_root else None
    source_digest = _file_sha256(source_path) if source_path is not None and source_path.is_file() else ""
    target_digest = _file_sha256(target_path) if target_path.is_file() else ""
    return {
        "verification_status": "verified" if source_digest and target_digest else "target_available",
        "verification_mode": "verified_light_edit_recipe",
        "source_to_target_relation": "source_faithful_public_light_edit",
        "source_ref": SOURCE_REF,
        "target_ref": TARGET_REF,
        "source_body_digest": source_digest or None,
        "target_body_digest": target_digest or None,
        "rewrite_recipe_ref": TARGET_REF + "::AUTHORITY_CEILING",
        "source_symbol_refs": SOURCE_SYMBOL_REFS,
        "target_symbol_refs": TARGET_SYMBOL_REFS,
        "runtime_consumed_by": [
            "microcosm agent-route-observability-runtime validate-agent-observability-store-bundle --input examples/agent_route_observability_runtime/exported_agent_observability_store_bundle",
            "microcosm-substrate/tests/test_agent_route_observability_runtime.py::test_agent_observability_store_bundle_validates_runtime_shape",
        ],
        "body_in_receipt": False,
    }


def _bundle_finding(
    code: str,
    message: str,
    *,
    subject_id: str,
    subject_kind: str = "agent_observability_store_input",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_bundle_finding` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "error_code": code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.macro_tools.agent_observability_store` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="python -m microcosm_core.macro_tools.agent_observability_store")
    parser.add_argument("action", choices=["validate-public-bundle"])
    parser.add_argument("--input", required=True)
    args = parser.parse_args(argv)

    if args.action == "validate-public-bundle":
        view = build_public_agent_observability_store_view(
            load_public_agent_observability_store_bundle(args.input)
        )
        print(json.dumps(view, indent=2, sort_keys=True))
        return 0 if view["status"] == PASS else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
