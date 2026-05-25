"""
Pure telemetry-quality classification over the agent observability plane.

The classifiers here are read-only over already-emitted events. They never
suppress writes to the canonical store. Their job is to produce a derived
projection that distinguishes valid-but-useless event production
(unauthenticated SDK loops, idle infrastructure heartbeats) from meaningful
live cognition.

Every classified noise instance carries enough raw drilldown refs (seq,
session_id) that an operator can fall back to the lossless
``state/observability/agent_trace/events.jsonl`` for the original payload.

- When-needed: Open when extending or auditing the mission-status reducer's
  noise classification layer, or when adding a new ``noise_class``.
- Escalates-to: system/lib/agent_mission_status.py;
  system/lib/agent_observability.py;
  system/server/tests/test_agent_observability_classification.py.
- Navigation-group: kernel_lib
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence


SCHEMA_VERSION = "agent_observability_classification_v0"

CLASS_ID_AUTH_FAILURE_LOOP = "auth_failure_loop"

# Cwd substring that marks claude-mem SDK observer sessions. We match a
# substring rather than a strict prefix so home-relative paths and absolute
# paths both classify. Anchored to the directory name to keep matches narrow.
CLAUDE_MEM_OBSERVER_CWD_FRAGMENT = "/.claude-mem/observer-sessions"

# Substrings whose joint presence in an assistant message strongly indicates
# an unauthenticated SDK call. Matched case-insensitively. The ``401`` digit
# anchor is the load-bearing one; the others reduce false positives on
# ordinary discussions of authentication.
AUTH_FAILURE_TOKENS = (
    "failed to authenticate",
    "401",
    "authentication_error",
)

DEFAULT_AUTH_FAILURE_TOKEN_REQUIRED = 2

# A session needs at least this many auth-failure assistant messages in the
# bounded window before it counts as "looping". One transient 401 should not
# tarnish an otherwise healthy session.
DEFAULT_MIN_LOOP_FAILURES = 2

# Source runtimes whose events should never be classified as user-facing
# noise. Mirrors INFRASTRUCTURE_SOURCE_RUNTIMES in agent_session_attribution
# so consumers do not need to pass two filter sets through.
INFRASTRUCTURE_SOURCE_RUNTIMES_FOR_NOISE = frozenset({
    "metabolism",
    "station_render",
    "backend",
})


def _safe_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _payload_text(event: Mapping[str, Any]) -> str:
    """Best-effort flat string of the assistant content carried by ``event``."""
    payload = _safe_mapping(event.get("payload"))
    parts: list[str] = []
    for key in ("content", "text", "message", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            parts.append(value)
    block = payload.get("block")
    if isinstance(block, Mapping):
        for key in ("text", "content"):
            value = block.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
    summary = event.get("summary")
    if isinstance(summary, str) and summary:
        parts.append(summary)
    return " ".join(parts)


def _looks_like_auth_failure(text: str, *, required: int = DEFAULT_AUTH_FAILURE_TOKEN_REQUIRED) -> bool:
    if not text:
        return False
    lowered = text.lower()
    hits = sum(1 for token in AUTH_FAILURE_TOKENS if token in lowered)
    return hits >= required


def _is_observer_cwd(cwd: object, fragment: str = CLAUDE_MEM_OBSERVER_CWD_FRAGMENT) -> bool:
    if not isinstance(cwd, str) or not cwd or not fragment:
        return False
    return fragment in cwd


def _representative_session(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    seqs = [int(row.get("seq") or 0) for row in rows if row.get("seq") is not None]
    last_observed = ""
    for row in rows:
        candidate = str(row.get("observed_at") or row.get("occurred_at") or "")
        if candidate and candidate > last_observed:
            last_observed = candidate
    sample = rows[-1] if rows else {}
    return {
        "session_id": str(sample.get("session_id") or "") or None,
        "cwd": sample.get("cwd"),
        "event_count": len(rows),
        "first_seq": min(seqs) if seqs else None,
        "last_seq": max(seqs) if seqs else None,
        "last_observed_at": last_observed or None,
    }


def classify_auth_failure_loop(
    events: Sequence[Mapping[str, Any]],
    *,
    min_failures: int = DEFAULT_MIN_LOOP_FAILURES,
    required_tokens: int = DEFAULT_AUTH_FAILURE_TOKEN_REQUIRED,
    cwd_fragment: str = CLAUDE_MEM_OBSERVER_CWD_FRAGMENT,
) -> Optional[dict[str, Any]]:
    """
    Detect repeated unauthenticated assistant messages from claude-mem SDK
    observer sessions.

    Conservative match: a session is flagged only when both
      * its ``cwd`` contains ``cwd_fragment``, AND
      * at least ``min_failures`` of its ``message.assistant`` events carry
        the literal authentication-failure tokens.

    Returns ``None`` when nothing matches, otherwise a single
    ``noise_class`` dict aggregating the affected sessions. The shape is
    stable so frontends can render telemetry-quality entries uniformly.
    """
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        if not isinstance(event, Mapping):
            continue
        canonical = str(event.get("canonical_type") or "")
        if canonical != "message.assistant":
            continue
        if event.get("source_runtime") in INFRASTRUCTURE_SOURCE_RUNTIMES_FOR_NOISE:
            continue
        cwd = event.get("cwd")
        if cwd_fragment and not _is_observer_cwd(cwd, cwd_fragment):
            # Only require cwd match when caller passed a non-empty fragment.
            continue
        if not _looks_like_auth_failure(_payload_text(event), required=required_tokens):
            continue
        sid = str(event.get("session_id") or "unknown")
        grouped[sid].append(event)

    affected: list[dict[str, Any]] = []
    raw_refs: list[str] = []
    seqs: list[int] = []
    last_observed = ""
    total_events = 0

    for sid, rows in grouped.items():
        if len(rows) < min_failures:
            continue
        affected.append(_representative_session(rows))
        total_events += len(rows)
        # Aggregate seq + last_observed_at across ALL matched rows in the
        # session so the noise_class span covers the full storm; cap
        # ``raw_refs`` to a few representative ids to keep the payload
        # bounded.
        for row in rows:
            seq = row.get("seq")
            if seq is not None:
                seqs.append(int(seq))
            obs = str(row.get("observed_at") or row.get("occurred_at") or "")
            if obs and obs > last_observed:
                last_observed = obs
        for row in rows[:4]:
            seq = row.get("seq")
            if seq is not None:
                raw_refs.append(f"agent_event:{seq}")

    if not affected:
        return None

    affected.sort(key=lambda row: row.get("event_count") or 0, reverse=True)

    return {
        "class_id": CLASS_ID_AUTH_FAILURE_LOOP,
        "severity": "warn",
        "affected_session_count": len(affected),
        "event_count": total_events,
        "first_seq": min(seqs) if seqs else None,
        "last_seq": max(seqs) if seqs else None,
        "last_observed_at": last_observed or None,
        "representative_sessions": affected[:8],
        "recommended_action": (
            "Refresh claude-mem CLAUDE_CODE_PATH / auth credentials, or stop the "
            "claude-mem worker, then drain the affected observer-session ids from "
            "the active mission view. Raw events remain available via "
            "/api/agent-observability/events?session_id=<id>."
        ),
        "raw_refs": raw_refs[:16],
        "match_rule": {
            "cwd_fragment": cwd_fragment,
            "tokens_required": required_tokens,
            "min_failures_per_session": min_failures,
        },
    }


def noisy_session_ids_from_classes(noise_classes: Sequence[Mapping[str, Any]]) -> set[str]:
    """Return the set of session_ids that any noise_class flagged as noisy.

    Used by the mission-status builder to demote those sessions out of the
    default ``missions`` list. It does not delete them; consumers can still
    fetch the raw events.
    """
    out: set[str] = set()
    for entry in noise_classes:
        if not isinstance(entry, Mapping):
            continue
        for sample in entry.get("representative_sessions") or []:
            sid = sample.get("session_id") if isinstance(sample, Mapping) else None
            if sid:
                out.add(str(sid))
    return out


def stale_source_warnings(
    source_status: Sequence[Mapping[str, Any]],
    *,
    now: datetime,
    stale_after_s: float = 600.0,
) -> list[dict[str, Any]]:
    """Flag source runtimes whose last_observed_at is older than ``stale_after_s``."""
    rows: list[dict[str, Any]] = []
    for entry in source_status:
        if not isinstance(entry, Mapping):
            continue
        last = entry.get("last_observed_at")
        parsed = _parse_iso(last)
        if parsed is None:
            continue
        lag = max(0.0, (now - parsed).total_seconds())
        if lag < stale_after_s:
            continue
        rows.append({
            "source_runtime": entry.get("source_runtime"),
            "last_observed_at": last,
            "lag_s": round(lag, 2),
            "event_count": entry.get("event_count"),
            "stale_after_s": stale_after_s,
        })
    return rows


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


def classify_telemetry_quality(
    *,
    events: Sequence[Mapping[str, Any]],
    source_status: Sequence[Mapping[str, Any]],
    persistence_status: Mapping[str, Any] | None = None,
    gap_count: int = 0,
    dropped_count: int = 0,
    history_limit_used: int | None = None,
    now: datetime,
    stale_source_after_s: float = 600.0,
) -> dict[str, Any]:
    """
    Build the ``telemetry_quality`` panel of the mission-status reducer.

    Composes individual classifiers into a single typed payload. Adding a
    new noise class is a matter of appending another classifier function and
    extending the ``noise_classes`` list.
    """
    noise_classes: list[dict[str, Any]] = []
    auth = classify_auth_failure_loop(events)
    if auth:
        noise_classes.append(auth)

    persistence = _safe_mapping(persistence_status)
    projection_warnings: list[dict[str, Any]] = []
    if persistence.get("error_count"):
        projection_warnings.append({
            "kind": "persistence_errors",
            "severity": "warn",
            "message": "AgentTraceStore reports persistence errors; on-disk durability is degraded.",
            "evidence": {
                "error_count": persistence.get("error_count"),
                "last_error": persistence.get("last_error"),
            },
        })
    if persistence.get("retry_in_s"):
        projection_warnings.append({
            "kind": "persistence_retrying",
            "severity": "info",
            "message": "AgentTraceStore is in retry backoff; new events may be buffered in memory only.",
            "evidence": {"retry_in_s": persistence.get("retry_in_s")},
        })
    if dropped_count:
        projection_warnings.append({
            "kind": "events_dropped",
            "severity": "warn",
            "message": f"{dropped_count} events dropped by the broadcaster queue.",
            "evidence": {"dropped_count": dropped_count},
        })
    if gap_count:
        projection_warnings.append({
            "kind": "stream_gaps",
            "severity": "info",
            "message": f"{gap_count} sequence gaps observed in the bounded window.",
            "evidence": {"gap_count": gap_count},
        })

    schema_gaps: list[dict[str, Any]] = []
    canonical_counter: Counter[str] = Counter()
    for event in events:
        if not isinstance(event, Mapping):
            continue
        canonical = str(event.get("canonical_type") or "")
        canonical_counter[canonical] += 1
        if not canonical:
            schema_gaps.append({
                "kind": "missing_canonical_type",
                "evidence_ref": f"agent_event:{event.get('seq')}" if event.get("seq") is not None else None,
            })
    schema_gaps = schema_gaps[:8]

    return {
        "schema_version": SCHEMA_VERSION,
        "noise_classes": noise_classes,
        "stale_sources": stale_source_warnings(
            source_status, now=now, stale_after_s=stale_source_after_s,
        ),
        "schema_gaps": schema_gaps,
        "projection_warnings": projection_warnings,
        "history_limit_used": history_limit_used,
        "canonical_type_counts": dict(sorted(canonical_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:24]),
    }
