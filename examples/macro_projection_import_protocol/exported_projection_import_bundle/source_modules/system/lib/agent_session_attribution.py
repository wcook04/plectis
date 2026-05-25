"""
Agent session attribution: read-only join of AgentTraceStore active sessions
with the work_ledger runtime_status view.

Purpose
-------
Two stores currently know about live sessions but never talk:

* ``system/lib/agent_observability.py::AgentTraceStore`` knows that a session
  exists, what it has touched, and how stale its event stream is.
* ``state/work_ledger/runtime_status.json`` (written by
  ``system/lib/work_ledger_runtime.py``) knows which phase/family/lane each
  session bootstrapped under, plus its claims and stale flags.

A consumer that wants to answer "is *that* warning from a concurrent session
on a different lane, or from me?" needs both views joined. This module is the
canonical join. It is pure and read-only: callers pass in the two views and
get back attributed records. Callers (HTTP route, hook, CLI) own the I/O.

Schema is ``agent_session_attribution_v0``: choices below are first-pass and
subject to revision once at least one downstream consumer is wired (see the
paper module ``agent_session_attribution.md``).
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
    "context.loaded",
    "session.snapshot",
})


@dataclass
class AttributedSession:
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
        return asdict(self)


def _classify_currently_live(
    *,
    liveness: str,
    last_canonical_type: Optional[str],
) -> tuple[bool, bool]:
    """
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
    return datetime.now(timezone.utc)


def _parse_iso(value: object) -> Optional[datetime]:
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
    if newest_observed is None:
        return LIVENESS_UNKNOWN, None
    lag_s = max(0.0, (now - newest_observed).total_seconds())
    if lag_s <= live_window_s:
        return LIVENESS_LIVE, lag_s
    if lag_s <= recent_window_s:
        return LIVENESS_RECENT, lag_s
    return LIVENESS_STALE, lag_s


def _normalize_codex_id(session_id: str) -> str:
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
    Return two lookups:
      * direct: session_id -> work-ledger record
      * normalized: codex-stripped session_id -> work-ledger record
    The normalized lookup lets ATS records with bare UUID match work-ledger
    entries that carry the ``codex:`` prefix.
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
    Join the ATS ``active_sessions`` view with the work-ledger ``sessions`` map
    and return a single attributed view.

    Parameters
    ----------
    ats_active_sessions:
        The list returned by ``AgentTraceStore.status()['active_sessions']``.
    work_ledger_status:
        The dict loaded from ``state/work_ledger/runtime_status.json`` (or the
        in-memory equivalent from ``work_ledger_runtime.load_runtime_status``).
    now:
        Override clock for tests.
    live_window_s, recent_window_s:
        Liveness thresholds in seconds. Records newer than ``live_window_s``
        are ``live``; newer than ``recent_window_s`` are ``recent``; older
        are ``stale``.
    include_workledger_only:
        When True (default), append work-ledger sessions that have no ATS row.
        Their attribution_status is ``workledger_only``.
    include_stale_workledger_only:
        When False (default), workledger-only sessions classified as ``stale``
        are dropped from the response. They number in the hundreds and would
        swamp consumers; set True for audit/debug.
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
    Return the most-recent session whose ``title`` or ``current_activity``
    contains ``title_query`` as a substring. Use this so a hook or CLI can
    answer "which of these is me?" by grepping for a known prompt fragment
    (e.g. the user's first message in this turn). Recency is judged by
    ``last_observed_at`` falling back to ``last_activity_at``.

    The returned record is the same shape passed in. None if no match.
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
    Return the most-recent session whose ``cwd`` equals (or is a path-prefix
    parent of) ``cwd``. Use as a fallback to ``find_session_by_title`` when
    no title fragment is known but the working directory is.
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
    Try to find the calling session in ``sessions`` (typically the
    ``sessions`` field of an ``attribute_sessions`` view). Title match wins
    when provided; cwd match is the fallback. The caller's purpose is to
    learn its own ``session_id`` / ``phase_id`` / ``actor`` so it can
    classify other sessions as "concurrent on a different lane".
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
