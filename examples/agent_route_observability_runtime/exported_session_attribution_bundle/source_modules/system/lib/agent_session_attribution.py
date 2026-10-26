"""
[PURPOSE]
- Teleology: Joins AgentTraceStore active-session rows with Work Ledger runtime status so callers can tell which live warnings or claims belong to which actor, phase, and lane.
- Mechanism: Keeps attribution pure and read-only; callers supply both views and receive an `agent_session_attribution_v0` envelope.
- Guarantee: Importing this module defines schema constants, `AttributedSession`, attribution helpers, and self-session lookup helpers without reading or mutating disk.

[INTERFACE]
- Exports: `SCHEMA_VERSION`, attribution/liveness constants, `AttributedSession`, `attribute_sessions`, `find_session_by_title`, `find_session_by_cwd`, `identify_self_session`.
- Reads: caller-provided ATS active-session rows, caller-provided Work Ledger status rows, and optional caller-provided clock values.
- Writes: return dictionaries and dataclass instances only.
- Schema: Returned attribution envelopes use `agent_session_attribution_v0`.
- Non-goal: Does not load AgentTraceStore, read `runtime_status.json`, write claims, publish status, or decide session ownership.

[FLOW]
- Normalizes Work Ledger session ids into direct and Codex-prefix-stripped lookup tables.
- Classifies ATS rows as matched, ATS-only, infrastructure, or unattributable stream buckets.
- Optionally appends Work Ledger-only rows, dropping stale rows by default to keep consumer views bounded.
- Sorts sessions by liveness and recency, then serializes `AttributedSession` records into the response envelope.
- Provides title, cwd, and combined self-session lookup helpers over an attributed session list.

[DEPENDENCIES]
- Required: None beyond the Python standard library.
- Optional Runtime: None; filesystem and HTTP callers own I/O before invoking this module.

[CONSTRAINTS]
- Atomicity: Functions return newly built records and do not mutate caller-owned mappings.
- Determinism: Equal inputs and equal `now` values produce equal attribution and ordering; `_now()` is the only internal clock source.
- Forbid: Do not treat unattributable Codex app stream buckets as missing Work Ledger evidence.
- When-needed: Open when converting attributed sessions to dicts, joining ATS sessions to Work Ledger runtime status, or identifying the current agent session.
- Escalates-to: system/server/tests/test_agent_session_attribution.py; system/lib/agent_session_attribution.py::AttributedSession; system/lib/agent_session_attribution.py::AttributedSession.to_dict; system/lib/agent_session_attribution.py::attribute_sessions; system/lib/agent_session_attribution.py::find_session_by_title; system/lib/agent_session_attribution.py::find_session_by_cwd; system/lib/agent_session_attribution.py::identify_self_session; codex/standards/std_python.py; codex/standards/std_python_scope_index.json
- Navigation-group: kernel_lib
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional


SCHEMA_VERSION = "agent_session_attribution_v0"

# ATS source_runtime -> work_ledger actor. Other ATS source_runtimes
# (metabolism, station_render, backend) are infrastructure surfaces; the
# work ledger tracks user-facing actors only.
SOURCE_RUNTIME_TO_WORKLEDGER_ACTOR: Mapping[str, str] = {
    "claude_code": "claude_code",
    "codex_app": "codex",
}

INFRASTRUCTURE_SOURCE_RUNTIMES = frozenset({
    "metabolism",
    "station_render",
    "backend",
})

# When ATS bundles *all* codex_app snapshot events under a single literal
# session_id, no per-session attribution is possible. The unattributable
# bucket exists so consumers can distinguish "no attribution data yet" from
# "I tried to attribute and there is no work-ledger row".
CODEX_APP_STREAM_SESSION_IDS = frozenset({"codex_app"})

ATTRIBUTION_STATUS_MATCHED = "matched"
ATTRIBUTION_STATUS_ATS_ONLY = "ats_only"
ATTRIBUTION_STATUS_WORKLEDGER_ONLY = "workledger_only"
ATTRIBUTION_STATUS_UNATTRIBUTABLE = "unattributable"
ATTRIBUTION_STATUS_INFRASTRUCTURE = "infrastructure"

LIVENESS_LIVE = "live"
LIVENESS_RECENT = "recent"
LIVENESS_STALE = "stale"
LIVENESS_UNKNOWN = "unknown"

DEFAULT_LIVE_WINDOW_S = 600
DEFAULT_RECENT_WINDOW_S = 1800

CODEX_PREFIX = "codex:"

# Canonical types that mean "this session has explicitly closed". When the
# most recent event is one of these, the session is not currently live no
# matter how recent the timestamp is.
SESSION_END_CANONICAL_TYPES = frozenset({
    "session.end",
    "session.completed",
    "runtime.stopped",
})

# Canonical types that mean "this session is between turns: alive but idle".
# A session reporting only these is currently_live but not mid_turn.
BETWEEN_TURN_CANONICAL_TYPES = frozenset({
    "turn.completed",
    "runtime.waiting",
    "session.start",
    "session.heartbeat",
    "context.loaded",
    "session.snapshot",
})


@dataclass
class AttributedSession:
    """
    [ROLE]
    - Teleology: Carries one joined ATS/Work Ledger session record with liveness, attribution status, activity, and claim context.
    - Ownership: Owned by this module as the response record type for `attribute_sessions`; callers own any instance they construct or receive.
    - Mutability: Mutable dataclass fields are caller-owned after construction; list defaults are isolated per instance.
    - Concurrency: Provides no locking; callers must avoid shared cross-thread mutation of the same instance.
    - Guarantee: Successful construction exposes all serialized fields used by `to_dict` and attribution response envelopes.
    - Fails: Dataclass construction errors propagate as normal Python exceptions.
    - When-needed: Open when inspecting the attributed session record shape before using or serializing attribution output.
    - Escalates-to: system/lib/agent_session_attribution.py::AttributedSession.to_dict; system/server/tests/test_agent_session_attribution.py
    - Navigation-group: kernel_lib
    """
    session_id: str
    source_runtime: Optional[str]
    actor: Optional[str]
    phase_id: Optional[str]
    family_id: Optional[str]
    attribution_status: str
    liveness: str
    currently_live: bool
    mid_turn: bool
    title: Optional[str]
    current_activity: Optional[str]
    last_canonical_type: Optional[str]
    last_observed_at: Optional[str]
    last_activity_at: Optional[str]
    lag_s: Optional[float]
    cwd: Optional[str]
    transcript_path: Optional[str]
    touched_files: list[str] = field(default_factory=list)
    touched_td_ids: list[str] = field(default_factory=list)
    active_claims: list[Mapping[str, Any]] = field(default_factory=list)
    workledger_stale: bool = False
    workledger_stale_reason: Optional[str] = None
    matched_at: Optional[str] = None
    match_strategy: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Serializes an attributed session dataclass into the dictionary shape used by attribution envelopes and tests.
        - Preconditions: `self` is an `AttributedSession` instance.
        - Guarantee: Returns `asdict(self)` with no field filtering or mutation.
        - Fails: Propagates dataclass serialization errors if a field value cannot be copied.
        - Reads: instance fields.
        - Writes: return values.
        - When-needed: Open when a consumer needs the exact dict conversion for attributed session records.
        - Escalates-to: system/lib/agent_session_attribution.py::AttributedSession; system/server/tests/test_agent_session_attribution.py
        - Navigation-group: kernel_lib
        """
        return asdict(self)


def _classify_currently_live(
    *,
    liveness: str,
    last_canonical_type: Optional[str],
) -> tuple[bool, bool]:
    """
    [ACTION]
    Return (currently_live, mid_turn).

    currently_live = the session has not explicitly ended AND its last event
        is recent enough that we expect more from it. A session that emitted
        a Stop hook (turn.completed) but is still inside the live window is
        currently_live=True (waiting for the next prompt); a session that
        emitted SessionEnd is currently_live=False; a session whose last
        event is hours old is currently_live=False regardless of type.

    mid_turn = currently_live AND the last event indicates an in-flight turn
        (a tool call, plan, intent, prompt, etc.) rather than a between-turn
        marker. This is the "actively doing work right now" signal.
    - Teleology: Implements `_classify_currently_live` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if liveness == LIVENESS_STALE or liveness == LIVENESS_UNKNOWN:
        return False, False
    if last_canonical_type in SESSION_END_CANONICAL_TYPES:
        return False, False
    if liveness == LIVENESS_LIVE:
        return True, last_canonical_type not in BETWEEN_TURN_CANONICAL_TYPES
    # liveness == LIVENESS_RECENT: still alive, but not actively mid-turn.
    return True, False


def _now() -> datetime:
    """
    [ACTION]
    - Teleology: Implements `_now` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return datetime.now(timezone.utc)


def _parse_iso(value: object) -> Optional[datetime]:
    """
    [ACTION]
    - Teleology: Implements `_parse_iso` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _newest(*candidates: object) -> Optional[datetime]:
    """
    [ACTION]
    - Teleology: Implements `_newest` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    best: Optional[datetime] = None
    for candidate in candidates:
        parsed = _parse_iso(candidate)
        if parsed is None:
            continue
        if best is None or parsed > best:
            best = parsed
    return best


def _classify_liveness(
    *,
    newest_observed: Optional[datetime],
    now: datetime,
    live_window_s: int,
    recent_window_s: int,
) -> tuple[str, Optional[float]]:
    """
    [ACTION]
    - Teleology: Implements `_classify_liveness` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if newest_observed is None:
        return LIVENESS_UNKNOWN, None
    lag_s = max(0.0, (now - newest_observed).total_seconds())
    if lag_s <= live_window_s:
        return LIVENESS_LIVE, lag_s
    if lag_s <= recent_window_s:
        return LIVENESS_RECENT, lag_s
    return LIVENESS_STALE, lag_s


def _normalize_codex_id(session_id: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_codex_id` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if session_id.startswith(CODEX_PREFIX):
        return session_id[len(CODEX_PREFIX):]
    return session_id


def _build_workledger_lookup(
    work_ledger_sessions: Mapping[str, Mapping[str, Any]],
) -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    """
    [ACTION]
    Return two lookups:
      * direct: session_id -> work-ledger record
      * normalized: codex-stripped session_id -> work-ledger record
    The normalized lookup lets ATS records with bare UUID match work-ledger
    entries that carry the ``codex:`` prefix.
    - Teleology: Implements `_build_workledger_lookup` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    direct: dict[str, Mapping[str, Any]] = {}
    normalized: dict[str, Mapping[str, Any]] = {}
    for sid, record in work_ledger_sessions.items():
        if not isinstance(record, Mapping):
            continue
        direct[sid] = record
        normalized[_normalize_codex_id(sid)] = record
    return direct, normalized


def _attribute_one(
    ats_session: Mapping[str, Any],
    *,
    direct: Mapping[str, Mapping[str, Any]],
    normalized: Mapping[str, Mapping[str, Any]],
    now: datetime,
    live_window_s: int,
    recent_window_s: int,
) -> AttributedSession:
    """
    [ACTION]
    - Teleology: Implements `_attribute_one` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    session_id = str(ats_session.get("session_id") or "unknown")
    source_runtime = ats_session.get("source_runtime")
    last_observed_at = ats_session.get("last_observed_at")
    last_activity_at = ats_session.get("last_activity_at")

    title = ats_session.get("title")
    current_activity = ats_session.get("current_activity")
    last_canonical_type = ats_session.get("last_canonical_type")

    if source_runtime in INFRASTRUCTURE_SOURCE_RUNTIMES:
        liveness, lag_s = _classify_liveness(
            newest_observed=_newest(last_observed_at, last_activity_at),
            now=now,
            live_window_s=live_window_s,
            recent_window_s=recent_window_s,
        )
        currently_live, mid_turn = _classify_currently_live(
            liveness=liveness, last_canonical_type=last_canonical_type,
        )
        return AttributedSession(
            session_id=session_id,
            source_runtime=source_runtime,
            actor=None,
            phase_id=None,
            family_id=None,
            attribution_status=ATTRIBUTION_STATUS_INFRASTRUCTURE,
            liveness=liveness,
            currently_live=currently_live,
            mid_turn=mid_turn,
            title=title,
            current_activity=current_activity,
            last_canonical_type=last_canonical_type,
            last_observed_at=last_observed_at,
            last_activity_at=last_activity_at,
            lag_s=lag_s,
            cwd=ats_session.get("cwd"),
            transcript_path=ats_session.get("transcript_path"),
            touched_files=list(ats_session.get("touched_files") or []),
            matched_at=now.isoformat(timespec="milliseconds"),
            match_strategy="infrastructure_skip",
        )

    if session_id in CODEX_APP_STREAM_SESSION_IDS:
        liveness, lag_s = _classify_liveness(
            newest_observed=_newest(last_observed_at, last_activity_at),
            now=now,
            live_window_s=live_window_s,
            recent_window_s=recent_window_s,
        )
        currently_live, mid_turn = _classify_currently_live(
            liveness=liveness, last_canonical_type=last_canonical_type,
        )
        return AttributedSession(
            session_id=session_id,
            source_runtime=source_runtime,
            actor=None,
            phase_id=None,
            family_id=None,
            attribution_status=ATTRIBUTION_STATUS_UNATTRIBUTABLE,
            liveness=liveness,
            currently_live=currently_live,
            mid_turn=mid_turn,
            title=title,
            current_activity=current_activity,
            last_canonical_type=last_canonical_type,
            last_observed_at=last_observed_at,
            last_activity_at=last_activity_at,
            lag_s=lag_s,
            cwd=ats_session.get("cwd"),
            transcript_path=ats_session.get("transcript_path"),
            touched_files=list(ats_session.get("touched_files") or []),
            matched_at=now.isoformat(timespec="milliseconds"),
            match_strategy="codex_stream_bucket",
        )

    matched: Optional[Mapping[str, Any]] = None
    match_strategy: Optional[str] = None

    if session_id in direct:
        matched = direct[session_id]
        match_strategy = "direct_session_id"
    else:
        normalized_key = _normalize_codex_id(session_id)
        if normalized_key != session_id and normalized_key in normalized:
            matched = normalized[normalized_key]
            match_strategy = "codex_id_normalized"
        elif source_runtime == "codex_app":
            prefixed = f"{CODEX_PREFIX}{session_id}"
            if prefixed in direct:
                matched = direct[prefixed]
                match_strategy = "codex_prefix_added"

    newest_observed = _newest(
        last_observed_at,
        last_activity_at,
        matched.get("last_activity_at") if matched else None,
    )
    liveness, lag_s = _classify_liveness(
        newest_observed=newest_observed,
        now=now,
        live_window_s=live_window_s,
        recent_window_s=recent_window_s,
    )

    currently_live, mid_turn = _classify_currently_live(
        liveness=liveness, last_canonical_type=last_canonical_type,
    )

    if matched is None:
        return AttributedSession(
            session_id=session_id,
            source_runtime=source_runtime,
            actor=None,
            phase_id=None,
            family_id=None,
            attribution_status=ATTRIBUTION_STATUS_ATS_ONLY,
            liveness=liveness,
            currently_live=currently_live,
            mid_turn=mid_turn,
            title=title,
            current_activity=current_activity,
            last_canonical_type=last_canonical_type,
            last_observed_at=last_observed_at,
            last_activity_at=last_activity_at,
            lag_s=lag_s,
            cwd=ats_session.get("cwd"),
            transcript_path=ats_session.get("transcript_path"),
            touched_files=list(ats_session.get("touched_files") or []),
            matched_at=now.isoformat(timespec="milliseconds"),
            match_strategy="no_workledger_row",
        )

    return AttributedSession(
        session_id=session_id,
        source_runtime=source_runtime,
        actor=str(matched.get("actor") or "") or None,
        phase_id=str(matched.get("phase_id") or "") or None,
        family_id=str(matched.get("family_id") or "") or None,
        attribution_status=ATTRIBUTION_STATUS_MATCHED,
        liveness=liveness,
        currently_live=currently_live,
        mid_turn=mid_turn,
        title=title,
        current_activity=current_activity,
        last_canonical_type=last_canonical_type,
        last_observed_at=last_observed_at,
        last_activity_at=last_activity_at or matched.get("last_activity_at"),
        lag_s=lag_s,
        cwd=ats_session.get("cwd"),
        transcript_path=ats_session.get("transcript_path"),
        touched_files=list(ats_session.get("touched_files") or []),
        touched_td_ids=list(matched.get("touched_td_ids") or []),
        active_claims=[c for c in (matched.get("claims") or []) if isinstance(c, Mapping)],
        workledger_stale=bool(matched.get("stale")),
        workledger_stale_reason=str(matched.get("stale_reason") or "") or None,
        matched_at=now.isoformat(timespec="milliseconds"),
        match_strategy=match_strategy,
    )


def _workledger_only_record(
    session_id: str,
    record: Mapping[str, Any],
    *,
    now: datetime,
    live_window_s: int,
    recent_window_s: int,
) -> AttributedSession:
    """
    [ACTION]
    - Teleology: Implements `_workledger_only_record` for `microcosm_core.macro_tools.agent_session_attribution` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    last_activity_at = record.get("last_activity_at")
    liveness, lag_s = _classify_liveness(
        newest_observed=_parse_iso(last_activity_at),
        now=now,
        live_window_s=live_window_s,
        recent_window_s=recent_window_s,
    )
    currently_live, mid_turn = _classify_currently_live(
        liveness=liveness, last_canonical_type=None,
    )
    return AttributedSession(
        session_id=session_id,
        source_runtime=None,
        actor=str(record.get("actor") or "") or None,
        phase_id=str(record.get("phase_id") or "") or None,
        family_id=str(record.get("family_id") or "") or None,
        attribution_status=ATTRIBUTION_STATUS_WORKLEDGER_ONLY,
        liveness=liveness,
        currently_live=currently_live,
        mid_turn=mid_turn,
        title=None,
        current_activity=None,
        last_canonical_type=None,
        last_observed_at=None,
        last_activity_at=last_activity_at,
        lag_s=lag_s,
        cwd=None,
        transcript_path=None,
        touched_files=[],
        touched_td_ids=list(record.get("touched_td_ids") or []),
        active_claims=[c for c in (record.get("claims") or []) if isinstance(c, Mapping)],
        workledger_stale=bool(record.get("stale")),
        workledger_stale_reason=str(record.get("stale_reason") or "") or None,
        matched_at=now.isoformat(timespec="milliseconds"),
        match_strategy="workledger_only",
    )


def attribute_sessions(
    *,
    ats_active_sessions: Iterable[Mapping[str, Any]],
    work_ledger_status: Mapping[str, Any],
    now: Optional[datetime] = None,
    live_window_s: int = DEFAULT_LIVE_WINDOW_S,
    recent_window_s: int = DEFAULT_RECENT_WINDOW_S,
    include_workledger_only: bool = True,
    include_stale_workledger_only: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Joins AgentTraceStore active sessions with Work Ledger runtime status into one attribution envelope.
    - Preconditions: `ats_active_sessions` is iterable over mapping-like ATS rows; `work_ledger_status` may contain a `sessions` mapping.
    - Guarantee: Returns `agent_session_attribution_v0` with summary counts and serialized sessions sorted by liveness then recency.
    - Fails: Propagates mapping iteration, datetime, and serialization errors raised by malformed caller inputs.
    - Reads: ATS rows, Work Ledger status rows, liveness thresholds, `now` or the current UTC clock.
    - Writes: return values.
    - Orders: Live sessions sort before recent, stale, and unknown sessions; equal liveness sorts by ascending lag.
    - When-needed: Open when an HTTP route, hook, CLI, or test needs the canonical ATS-to-Work-Ledger attribution join.
    - Escalates-to: system/server/tests/test_agent_session_attribution.py; system/lib/agent_session_attribution.py::AttributedSession; system/lib/agent_session_attribution.py::AttributedSession.to_dict
    - Navigation-group: kernel_lib
    """
    now = now or _now()
    direct, normalized = _build_workledger_lookup(work_ledger_status.get("sessions") or {})

    attributed: list[AttributedSession] = []
    consumed_workledger_ids: set[str] = set()

    for ats_session in ats_active_sessions:
        if not isinstance(ats_session, Mapping):
            continue
        record = _attribute_one(
            ats_session,
            direct=direct,
            normalized=normalized,
            now=now,
            live_window_s=live_window_s,
            recent_window_s=recent_window_s,
        )
        attributed.append(record)
        if record.attribution_status == ATTRIBUTION_STATUS_MATCHED:
            sid = str(ats_session.get("session_id") or "")
            if sid in direct:
                consumed_workledger_ids.add(sid)
            else:
                normalized_key = _normalize_codex_id(sid)
                for wl_sid, wl_rec in direct.items():
                    if _normalize_codex_id(wl_sid) == normalized_key:
                        consumed_workledger_ids.add(wl_sid)

    if include_workledger_only:
        for wl_sid, wl_rec in direct.items():
            if wl_sid in consumed_workledger_ids:
                continue
            wl_record = _workledger_only_record(
                wl_sid,
                wl_rec,
                now=now,
                live_window_s=live_window_s,
                recent_window_s=recent_window_s,
            )
            if wl_record.liveness == LIVENESS_STALE and not include_stale_workledger_only:
                continue
            attributed.append(wl_record)

    attributed.sort(
        key=lambda r: (
            0 if r.liveness == LIVENESS_LIVE else
            1 if r.liveness == LIVENESS_RECENT else
            2 if r.liveness == LIVENESS_STALE else 3,
            r.lag_s if r.lag_s is not None else float("inf"),
        )
    )

    summary = {
        "total": len(attributed),
        "by_attribution_status": {},
        "by_liveness": {},
    }
    for record in attributed:
        s = summary["by_attribution_status"]
        s[record.attribution_status] = s.get(record.attribution_status, 0) + 1
        l = summary["by_liveness"]
        l[record.liveness] = l.get(record.liveness, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(timespec="milliseconds"),
        "live_window_s": live_window_s,
        "recent_window_s": recent_window_s,
        "include_workledger_only": include_workledger_only,
        "include_stale_workledger_only": include_stale_workledger_only,
        "summary": summary,
        "sessions": [r.to_dict() for r in attributed],
    }


def find_session_by_title(
    sessions: Iterable[Mapping[str, Any]],
    *,
    title_query: str,
    source_runtime: Optional[str] = None,
    case_sensitive: bool = False,
) -> Optional[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Finds the most recent session whose title, current activity, or summary contains a known prompt fragment.
    - Preconditions: `sessions` is iterable over mapping-like records and `title_query` is the substring to match.
    - Guarantee: Returns a shallow dict copy of the newest matching record, or `None` when no record matches.
    - Fails: Propagates iteration and timestamp comparison errors raised by malformed caller inputs.
    - Reads: session records, `title_query`, optional source runtime filter, and case-sensitivity setting.
    - Writes: return values.
    - Orders: Recency uses `last_observed_at` falling back to `last_activity_at`.
    - When-needed: Open when a caller can identify its own session from a prompt/title fragment.
    - Escalates-to: system/lib/agent_session_attribution.py::identify_self_session; system/server/tests/test_agent_session_attribution.py
    - Navigation-group: kernel_lib
    """
    needle = title_query if case_sensitive else title_query.lower()
    candidates: list[tuple[Optional[datetime], Mapping[str, Any]]] = []
    for session in sessions:
        if not isinstance(session, Mapping):
            continue
        if source_runtime and session.get("source_runtime") != source_runtime:
            continue
        haystacks: list[str] = []
        for field_name in ("title", "current_activity", "summary"):
            value = session.get(field_name)
            if value:
                haystacks.append(str(value) if case_sensitive else str(value).lower())
        if not any(needle in h for h in haystacks):
            continue
        ts = _newest(session.get("last_observed_at"), session.get("last_activity_at"))
        candidates.append((ts, session))
    if not candidates:
        return None
    candidates.sort(
        key=lambda kv: (kv[0] is not None, kv[0] or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    return dict(candidates[0][1])


def find_session_by_cwd(
    sessions: Iterable[Mapping[str, Any]],
    *,
    cwd: str,
    source_runtime: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Finds the most recent session whose recorded cwd equals or contains the requested working directory.
    - Preconditions: `sessions` is iterable over mapping-like records and `cwd` is the caller's working directory.
    - Guarantee: Returns a shallow dict copy of the newest cwd match, or `None` when no record matches.
    - Fails: Propagates iteration and timestamp comparison errors raised by malformed caller inputs.
    - Reads: session records, `cwd`, and optional source runtime filter.
    - Writes: return values.
    - Orders: Recency uses `last_observed_at` falling back to `last_activity_at`.
    - When-needed: Open when title matching is unavailable and the caller must identify its own session by working directory.
    - Escalates-to: system/lib/agent_session_attribution.py::identify_self_session; system/server/tests/test_agent_session_attribution.py
    - Navigation-group: kernel_lib
    """
    target = cwd.rstrip("/")
    candidates: list[tuple[Optional[datetime], Mapping[str, Any]]] = []
    for session in sessions:
        if not isinstance(session, Mapping):
            continue
        if source_runtime and session.get("source_runtime") != source_runtime:
            continue
        session_cwd = (session.get("cwd") or "").rstrip("/")
        if not session_cwd:
            continue
        if session_cwd != target and not target.startswith(session_cwd + "/"):
            continue
        ts = _newest(session.get("last_observed_at"), session.get("last_activity_at"))
        candidates.append((ts, session))
    if not candidates:
        return None
    candidates.sort(
        key=lambda kv: (kv[0] is not None, kv[0] or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    return dict(candidates[0][1])


def identify_self_session(
    sessions: Iterable[Mapping[str, Any]],
    *,
    title_fragment: Optional[str] = None,
    cwd: Optional[str] = None,
    source_runtime: str = "claude_code",
) -> Optional[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Identifies the caller's own attributed session so consumers can compare it against concurrent sessions.
    - Preconditions: `sessions` is iterable over attributed session records; caller supplies a title fragment, cwd, or both.
    - Guarantee: Prefers title-fragment matches, falls back to cwd matches, and returns `None` when neither route matches.
    - Fails: Propagates lookup helper errors raised by malformed caller inputs.
    - Reads: session records, optional title fragment, optional cwd, and source runtime filter.
    - Writes: return values.
    - When-needed: Open when a hook, route, or CLI needs its own `session_id`, `phase_id`, or `actor` from an attributed session list.
    - Escalates-to: system/lib/agent_session_attribution.py::find_session_by_title; system/lib/agent_session_attribution.py::find_session_by_cwd; system/server/tests/test_agent_session_attribution.py
    - Navigation-group: kernel_lib
    """
    sessions_list = list(sessions)
    if title_fragment:
        match = find_session_by_title(
            sessions_list, title_query=title_fragment, source_runtime=source_runtime,
        )
        if match is not None:
            return match
    if cwd:
        return find_session_by_cwd(
            sessions_list, cwd=cwd, source_runtime=source_runtime,
        )
    return None
