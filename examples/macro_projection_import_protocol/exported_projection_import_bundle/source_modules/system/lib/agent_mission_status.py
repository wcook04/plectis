"""
Mission-status reducer over the agent observability plane.

This module composes the existing pure surfaces

  * ``AgentTraceStore.status()`` and ``AgentTraceStore.replay()``
  * ``work_ledger_runtime.load_runtime_status``
  * ``agent_session_attribution.attribute_sessions``
  * ``agent_observability_classification.classify_telemetry_quality``

into one typed projection that answers, in operator-facing terms, "what is
happening, who is doing it, is it healthy, what is noise?". The canonical
JSONL trace remains lossless and untouched; this projection is intentionally
opinionated and lossy. Every demoted session and every health number carries
raw drilldown refs back to ``state/observability/agent_trace/events.jsonl``.

- When-needed: Open when adding a backend mission-control surface, when
  tuning the demoted-session list, or when wiring a new health signal into
  the operator HUD.
- Escalates-to: system/lib/agent_observability.py;
  system/lib/agent_recent_activity.py;
  system/lib/agent_session_attribution.py;
  system/lib/agent_observability_classification.py;
  system/server/main.py.
- Navigation-group: kernel_lib
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, Sequence

from system.lib.agent_observability import DEFAULT_TRACE_RELATIVE_PATH
from system.lib.agent_observability_classification import (
    classify_telemetry_quality,
    noisy_session_ids_from_classes,
)
from system.lib.agent_session_attribution import (
    INFRASTRUCTURE_SOURCE_RUNTIMES,
    SCHEMA_VERSION as ATTRIBUTION_SCHEMA_VERSION,
    attribute_sessions,
)


SCHEMA_VERSION = "agent_mission_status_v0"
KIND = "agent_observability.mission_status"

DEFAULT_HISTORY_LIMIT = 200
MIN_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 2000

# Canonical types we treat as meaningful activity for "is this session
# actively doing work?" decisions and traffic counters. Source of truth is
# the same set used by ``agent_observability.py``; we re-state it here as a
# stable contract that the mission projection guarantees to consumers, so
# the frontend can drop its own copy.
ACTIVITY_CANONICAL_TYPES = frozenset({
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
})

ERROR_CANONICAL_TYPES = frozenset({
    "runtime.error",
    "tool.error",
    "session.error",
})


class _StoreProtocol(Protocol):
    def status(self) -> Mapping[str, Any]: ...
    def replay(self, *, limit: int = ...) -> list[Mapping[str, Any]]: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(now: datetime) -> str:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.isoformat(timespec="milliseconds")


def _parse_iso(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
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


def _safe_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _truncate(value: object, limit: int = 180) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    if not text:
        return None
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _events_per_second(events: Sequence[Mapping[str, Any]]) -> tuple[float, dict[str, float]]:
    """Compute total + per-runtime events/sec over the bounded window."""
    if not events:
        return 0.0, {}
    times: list[datetime] = []
    by_runtime_times: dict[str, list[datetime]] = defaultdict(list)
    by_runtime_count: Counter[str] = Counter()
    for event in events:
        parsed = _parse_iso(event.get("observed_at") or event.get("occurred_at"))
        if parsed is None:
            continue
        times.append(parsed)
        runtime = str(event.get("source_runtime") or "unknown")
        by_runtime_times[runtime].append(parsed)
        by_runtime_count[runtime] += 1
    if not times:
        return 0.0, {}
    span_total = max(0.001, (max(times) - min(times)).total_seconds())
    total_rate = round(len(times) / span_total, 3)
    by_runtime_rate: dict[str, float] = {}
    for runtime, ts in by_runtime_times.items():
        if not ts:
            continue
        span = max(0.001, (max(ts) - min(ts)).total_seconds())
        by_runtime_rate[runtime] = round(by_runtime_count[runtime] / span, 3)
    return total_rate, by_runtime_rate


def _error_counts(events: Sequence[Mapping[str, Any]]) -> tuple[int, dict[str, int], dict[str, int]]:
    total = 0
    by_runtime: Counter[str] = Counter()
    by_class: Counter[str] = Counter()
    for event in events:
        canonical = str(event.get("canonical_type") or "")
        payload = _safe_mapping(event.get("payload"))
        is_error = (
            canonical in ERROR_CANONICAL_TYPES
            or canonical.endswith(".error")
            or bool(payload.get("is_error"))
            or (payload.get("exit_code") not in (None, 0, "0", "", "None"))
        )
        if not is_error:
            continue
        total += 1
        by_runtime[str(event.get("source_runtime") or "unknown")] += 1
        by_class[canonical or "unknown"] += 1
    return total, dict(by_runtime), dict(by_class)


def _heartbeat_age(source_status: Sequence[Mapping[str, Any]], now: datetime) -> dict[str, Optional[float]]:
    out: dict[str, Optional[float]] = {}
    for entry in source_status:
        runtime = str(entry.get("source_runtime") or "")
        if not runtime:
            continue
        parsed = _parse_iso(entry.get("last_observed_at"))
        if parsed is None:
            out[runtime] = None
            continue
        out[runtime] = round(max(0.0, (now - parsed).total_seconds()), 2)
    return out


def _trace_file_size(trace_path: Path) -> Optional[int]:
    try:
        return trace_path.stat().st_size
    except OSError:
        return None


def _filter_events_for_session_match(
    events: Sequence[Mapping[str, Any]],
    *,
    session_id: str,
) -> list[Mapping[str, Any]]:
    return [event for event in events if str(event.get("session_id") or "") == session_id]


def _last_meaningful_event(events: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    for event in reversed(events):
        canonical = str(event.get("canonical_type") or "")
        if canonical in ACTIVITY_CANONICAL_TYPES:
            return event
    return None


def _summary_for_session(
    session: Mapping[str, Any],
    session_events: Sequence[Mapping[str, Any]],
) -> Optional[str]:
    last = _last_meaningful_event(session_events)
    if last is not None:
        text = _truncate(last.get("summary") or _safe_mapping(last.get("payload")).get("content"))
        if text:
            return text
    return _truncate(session.get("current_activity") or session.get("title"))


def _mission_row(
    *,
    attributed: Mapping[str, Any],
    raw_session: Mapping[str, Any] | None,
    session_events: Sequence[Mapping[str, Any]],
    demoted: bool,
    demote_reason: Optional[str],
    events_endpoint: str,
) -> dict[str, Any]:
    session_id = str(attributed.get("session_id") or "")
    seqs = [int(event.get("seq") or 0) for event in session_events if event.get("seq") is not None]
    raw_refs = {
        "events_endpoint": (
            f"{events_endpoint}?session_id={session_id}" if session_id else events_endpoint
        ),
        "first_seq": min(seqs) if seqs else None,
        "last_seq": max(seqs) if seqs else None,
        "event_count_in_window": len(session_events),
    }
    touched_from_raw = list((raw_session or {}).get("touched_files") or [])
    return {
        "session_id": session_id or None,
        "source_runtime": attributed.get("source_runtime"),
        "actor": attributed.get("actor"),
        "phase_id": attributed.get("phase_id"),
        "family_id": attributed.get("family_id"),
        "attribution_status": attributed.get("attribution_status"),
        "liveness": attributed.get("liveness"),
        "currently_live": attributed.get("currently_live"),
        "mid_turn": attributed.get("mid_turn"),
        "title": _truncate(attributed.get("title")),
        "current_activity": _summary_for_session(attributed, session_events),
        "last_canonical_type": attributed.get("last_canonical_type"),
        "last_observed_at": attributed.get("last_observed_at"),
        "last_activity_at": attributed.get("last_activity_at"),
        "lag_s": attributed.get("lag_s"),
        "cwd": attributed.get("cwd"),
        "touched_files": touched_from_raw[-12:],
        "touched_td_ids": list(attributed.get("touched_td_ids") or [])[:8],
        "active_claims": list(attributed.get("active_claims") or [])[:4],
        "demoted": demoted,
        "demote_reason": demote_reason,
        "raw_refs": raw_refs,
    }


def build_agent_mission_status(
    *,
    store: _StoreProtocol,
    work_ledger_status: Mapping[str, Any] | None = None,
    repo_root: Path | None = None,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    now: datetime | None = None,
    events_endpoint: str = "/api/agent-observability/events",
) -> dict[str, Any]:
    """
    Build one mission-status payload from the live trace store, the work
    ledger, attribution, and noise classification.

    Parameters
    ----------
    store:
        Object exposing ``status()`` and ``replay(limit=...)``. Either the
        live ``AgentTraceStore`` instance or a fake for tests.
    work_ledger_status:
        Already-loaded work-ledger runtime status, or ``None`` for empty.
        The route-layer caller is responsible for I/O so this builder stays
        pure and easy to test.
    repo_root:
        Used solely to resolve ``trace_file_size_bytes``. Optional.
    history_limit:
        Bounded window for the events tail and golden signals. Clamped to
        ``[MIN_HISTORY_LIMIT, MAX_HISTORY_LIMIT]``.
    now:
        Override clock for tests.
    events_endpoint:
        Base path used in per-session ``raw_refs.events_endpoint``. Allows
        tests and alternative deployments to relabel without changing logic.
    """
    safe_limit = max(MIN_HISTORY_LIMIT, min(int(history_limit or DEFAULT_HISTORY_LIMIT), MAX_HISTORY_LIMIT))
    now = now or _utc_now()
    status = dict(store.status() or {})
    events = list(store.replay(limit=safe_limit) or [])

    source_status = [s for s in (status.get("source_status") or []) if isinstance(s, Mapping)]
    persistence = _safe_mapping(status.get("persistence"))
    history_size = int(status.get("history_size") or 0)
    max_history = int(status.get("max_history") or 0)
    gap_count = int(status.get("gap_count") or 0)
    dropped_count = int(status.get("dropped_count") or persistence.get("dropped_count") or 0)

    attribution = attribute_sessions(
        ats_active_sessions=list(status.get("active_sessions") or []),
        work_ledger_status=dict(work_ledger_status or {}),
        now=now,
        include_workledger_only=True,
        include_stale_workledger_only=False,
    )
    attributed_sessions = [row for row in (attribution.get("sessions") or []) if isinstance(row, Mapping)]

    telemetry_quality = classify_telemetry_quality(
        events=events,
        source_status=source_status,
        persistence_status=persistence,
        gap_count=gap_count,
        dropped_count=dropped_count,
        history_limit_used=safe_limit,
        now=now,
    )
    noisy_ids = noisy_session_ids_from_classes(telemetry_quality.get("noise_classes") or [])

    raw_session_lookup: dict[str, Mapping[str, Any]] = {}
    for raw in status.get("active_sessions") or []:
        if isinstance(raw, Mapping) and raw.get("session_id"):
            raw_session_lookup[str(raw.get("session_id"))] = raw

    missions: list[dict[str, Any]] = []
    demoted_rows: list[dict[str, Any]] = []
    for attributed in attributed_sessions:
        session_id = str(attributed.get("session_id") or "")
        runtime = attributed.get("source_runtime")
        if runtime in INFRASTRUCTURE_SOURCE_RUNTIMES:
            continue
        if attributed.get("attribution_status") == "infrastructure":
            continue
        session_events = (
            _filter_events_for_session_match(events, session_id=session_id)
            if session_id else []
        )
        if session_id and session_id in noisy_ids:
            row = _mission_row(
                attributed=attributed,
                raw_session=raw_session_lookup.get(session_id),
                session_events=session_events,
                demoted=True,
                demote_reason="auth_failure_loop",
                events_endpoint=events_endpoint,
            )
            demoted_rows.append(row)
            continue
        # Skip the codex_app stream bucket from the default mission list; it
        # is the all-codex aggregator, not a real session.
        if session_id == "codex_app":
            continue
        # Skip sessions with literally no recent activity in the window AND
        # no work-ledger evidence — they pollute the HUD without value.
        if (
            not session_events
            and not (attributed.get("touched_td_ids") or attributed.get("active_claims"))
            and attributed.get("liveness") in {"stale", "unknown", None}
        ):
            continue
        missions.append(_mission_row(
            attributed=attributed,
            raw_session=raw_session_lookup.get(session_id),
            session_events=session_events,
            demoted=False,
            demote_reason=None,
            events_endpoint=events_endpoint,
        ))

    missions.sort(
        key=lambda row: (
            0 if row.get("liveness") == "live" else
            1 if row.get("liveness") == "recent" else 2,
            float(row.get("lag_s") if row.get("lag_s") is not None else 1_000_000_000),
            str(row.get("last_observed_at") or row.get("last_activity_at") or ""),
        )
    )

    traffic_total, traffic_by_runtime = _events_per_second(events)
    err_total, err_by_runtime, err_by_class = _error_counts(events)
    heartbeat_age = _heartbeat_age(source_status, now)
    history_saturation = (
        round(history_size / max_history, 3) if max_history else None
    )

    trace_path = (Path(repo_root) / DEFAULT_TRACE_RELATIVE_PATH) if repo_root else None
    trace_file_size = _trace_file_size(trace_path) if trace_path else None

    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso(now),
        "source": {
            "trace_path": str(DEFAULT_TRACE_RELATIVE_PATH),
            "trace_file_size_bytes": trace_file_size,
            "trace_seq": status.get("seq"),
            "history_limit": safe_limit,
            "history_size": history_size,
            "max_history": max_history,
            "gap_count": gap_count,
            "dropped_count": dropped_count,
            "api_revision": status.get("api_revision"),
            "store_schema_version": status.get("schema") or status.get("schema_version"),
            "attribution_schema_version": ATTRIBUTION_SCHEMA_VERSION,
        },
        "health": {
            "traffic": {
                "events_per_second_total": traffic_total,
                "by_runtime": traffic_by_runtime,
                "event_count_in_window": len(events),
            },
            "errors": {
                "total_in_window": err_total,
                "by_runtime": err_by_runtime,
                "by_class": err_by_class,
            },
            "latency": {
                "heartbeat_age_s_by_runtime": heartbeat_age,
            },
            "saturation": {
                "history_size": history_size,
                "max_history": max_history,
                "history_saturation_ratio": history_saturation,
                "active_session_count": len([
                    row for row in (status.get("active_sessions") or [])
                    if isinstance(row, Mapping)
                ]),
            },
        },
        "missions": missions,
        "demoted_missions": demoted_rows,
        "telemetry_quality": telemetry_quality,
        "constants": {
            "activity_canonical_types": sorted(ACTIVITY_CANONICAL_TYPES),
            "infrastructure_source_runtimes": sorted(INFRASTRUCTURE_SOURCE_RUNTIMES),
        },
        "raw_drilldown_refs": {
            "endpoint_status": "/api/agent-observability/status",
            "endpoint_events": events_endpoint,
            "endpoint_websocket": "/ws/agent-observability",
            "trace_path": str(DEFAULT_TRACE_RELATIVE_PATH),
            "demoted_session_ids": sorted(noisy_ids),
        },
    }
