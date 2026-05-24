#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Materialize deterministic truth rows for matured CP1-admitted
  finance forecast claims.
- Mechanism: Read `finance_forecast_claim_v1` claims plus a local price-history
  artifact, compute member and benchmark event-window returns, and emit
  prediction-reconciliation-compatible rows for `eval_replay.py`.

[INTERFACE]
- Reads: admitted-claim envelope or raw `finance_forecast_claim_v1` object.
- Reads: deterministic price history JSON with rows or symbol->date price maps.
- Returns/prints: `finance_forecast_resolution.1` envelope with reconciliation rows.

[CONSTRAINTS]
- Deterministic local truth only; no provider fetches.
- Immature claims produce lifecycle status, not truth rows.
- Missing benchmark truth blocks materialization because benchmark-relative events
  cannot be scored without it.
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from system.lib import feed_envelope
from tools.finance.event_keys import (
    COMPARISON_EVENT_KEY_AUTHORITY,
    COMPARISON_EVENT_KEY_SCHEMA,
    comparison_event_key_payload,
    members_signature,
    normalize_key_parts,
)
from tools.finance.eval_replay import load_admitted_claims

TOOL_NAME = "finance_forecast_resolution"
DATA_SCHEMA_VERSION = "finance_forecast_resolution.1"

STATUS_PENDING_MATURITY = "pending_maturity"
STATUS_MISSING_BENCHMARK = "not_admissible_missing_benchmark_truth"
STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION = "not_admissible_benchmark_member_policy_violation"
STATUS_MATURED_TRUTH_MISSING = "matured_truth_missing"
STATUS_TRUTH_MATERIALIZED = "truth_materialized"
OUTCOME_BASIS_GROUP_RETURN = "equal_weight_group_return_direction"
BENCHMARK_MEMBER_POLICY_REJECT = "reject_if_benchmark_is_member"
DATE_MATCH_EXACT = "exact"
DATE_MATCH_EXACT_OR_NEXT_AVAILABLE = "exact_or_next_available"
DEFAULT_DATE_MATCH_POLICY = DATE_MATCH_EXACT_OR_NEXT_AVAILABLE
DEFAULT_MAX_ROLL_DAYS = 3
MATCH_STATUS_EXACT = "exact"
MATCH_STATUS_ROLLED_FORWARD = "rolled_forward"
MATCH_STATUS_MISSING = "missing"
MATCH_REASON_EXACT_TRADING_SESSION = "exact_trading_session"
MATCH_REASON_ROLLED_FORWARD_MARKET_CLOSED = "rolled_forward_market_closed"
MATCH_REASON_ROLLED_FORWARD_PROVIDER_MISSING = "rolled_forward_provider_missing"
MATCH_REASON_REFUSED_OUTSIDE_ROLL_WINDOW = "refused_outside_roll_window"
MATCH_REASON_REFUSED_EXACT_POLICY = "refused_exact_policy"
MATCH_REASON_REFUSED_NON_EQUITY_CALENDAR_UNKNOWN = "refused_non_equity_calendar_unknown"
SESSION_STATUS_EXPECTED_TRADING = "expected_trading_session"
SESSION_STATUS_MARKET_CLOSED = "market_closed"
SESSION_STATUS_UNKNOWN = "unknown_session"
DEFAULT_TRUTH_SESSION_POLICY_ID = "weekday_weekend_plus_declared_closed_dates"
SUPPORTED_DATE_MATCH_POLICIES = {
    DATE_MATCH_EXACT,
    DATE_MATCH_EXACT_OR_NEXT_AVAILABLE,
}
SUPPORTED_BENCHMARK_MEMBER_POLICIES = {
    "reject_if_benchmark_is_member",
    "include_as_zero_excess",
    "exclude_from_claim_outcome",
}


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else payload


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _upper(value: Any) -> str:
    return _as_text(value).upper()


def _float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _parse_dt(value: Any) -> datetime:
    text = _as_text(value)
    if not text:
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value: Any) -> str:
    return _parse_dt(value).isoformat()


def _failure_envelope(error: str, *, run_dir: Optional[Path] = None) -> Dict[str, Any]:
    now = feed_envelope.utc_now()
    diagnostics = feed_envelope.new_diagnostics()
    feed_envelope.append_warning(diagnostics, error)
    metadata = feed_envelope.build_metadata(
        tool=TOOL_NAME,
        status="failure",
        now=now,
        run_id=feed_envelope.resolve_run_id(None, run_dir, default=TOOL_NAME),
        as_of=now.iso,
        items_count=0,
        diagnostics=diagnostics,
        data_schema_version=DATA_SCHEMA_VERSION,
        timestamp=now.iso,
        error=error,
    )
    return {"metadata": metadata, "data": {}}


def _iter_price_rows(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    data = _data(payload)
    rows = data.get("rows") or payload.get("rows")
    columns = data.get("columns") if isinstance(data, Mapping) else None
    if isinstance(rows, list) and isinstance(columns, list):
        for row in rows:
            if isinstance(row, list):
                yield dict(zip(columns, row))
            elif isinstance(row, Mapping):
                yield row
        return
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping):
                yield row


def _load_price_index(payload: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    data = _data(payload)
    index: Dict[str, Dict[str, float]] = {}

    prices = data.get("prices") if isinstance(data, Mapping) else None
    if isinstance(prices, Mapping):
        for symbol, series in prices.items():
            ticker = _upper(symbol)
            if not ticker or not isinstance(series, Mapping):
                continue
            bucket = index.setdefault(ticker, {})
            for timestamp, price in series.items():
                value = _float(price)
                if value is not None:
                    bucket[_as_text(timestamp)] = value

    for row in _iter_price_rows(payload):
        ticker = _upper(row.get("target_id") or row.get("ticker") or row.get("symbol") or row.get("id"))
        timestamp = _as_text(row.get("timestamp") or row.get("as_of") or row.get("date") or row.get("time"))
        price = _float(row.get("price") or row.get("close") or row.get("adj_close") or row.get("value"))
        if ticker and timestamp and price is not None:
            index.setdefault(ticker, {})[timestamp] = price

    return index


def _closed_dates_from(value: Any) -> List[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    dates: List[str] = []
    for raw in value:
        text = _as_text(raw)[:10]
        try:
            dates.append(date.fromisoformat(text).isoformat())
        except ValueError:
            continue
    return sorted(set(dates))


def _truth_session_policy(payload: Mapping[str, Any]) -> Dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    coverage = metadata.get("coverage") if isinstance(metadata.get("coverage"), Mapping) else {}
    calendar = metadata.get("market_calendar") if isinstance(metadata.get("market_calendar"), Mapping) else {}
    if not calendar and isinstance(coverage.get("market_calendar"), Mapping):
        calendar = coverage["market_calendar"]
    closed_dates = _closed_dates_from(
        calendar.get("closed_dates")
        or coverage.get("closed_dates")
        or metadata.get("market_calendar_closed_dates")
        or []
    )
    early_close_dates = _closed_dates_from(
        calendar.get("early_close_dates")
        or coverage.get("early_close_dates")
        or metadata.get("market_calendar_early_close_dates")
        or []
    )
    return {
        "policy_id": _as_text(calendar.get("policy_id") or metadata.get("truth_session_policy_id") or DEFAULT_TRUTH_SESSION_POLICY_ID),
        "calendar_id": _as_text(calendar.get("calendar_id") or metadata.get("market_calendar_id") or "weekday_weekend_utc"),
        "calendar_source": _as_text(
            calendar.get("calendar_source")
            or calendar.get("source")
            or metadata.get("market_calendar_source")
            or "resolver_local_weekday_weekend"
        ),
        "closed_dates": closed_dates,
        "early_close_dates": early_close_dates,
        "calendar_semantics": _as_text(calendar.get("calendar_semantics") or "daily_close_truth_boundaries"),
    }


def _session_match_context(requested_date: date, session_policy: Mapping[str, Any]) -> Dict[str, Any]:
    closed_dates = set(str(d) for d in session_policy.get("closed_dates", []) if d)
    early_close_dates = set(str(d) for d in session_policy.get("early_close_dates", []) if d)
    requested = requested_date.isoformat()
    if requested in closed_dates:
        status = SESSION_STATUS_MARKET_CLOSED
        reason = "declared_closed_date"
    elif requested_date.weekday() >= 5:
        status = SESSION_STATUS_MARKET_CLOSED
        reason = "weekend"
    else:
        status = SESSION_STATUS_EXPECTED_TRADING
        reason = "weekday_expected_open"
    if requested in early_close_dates and status == SESSION_STATUS_EXPECTED_TRADING:
        reason = "declared_early_close_date"
    return {
        "truth_session_policy_id": session_policy.get("policy_id"),
        "market_calendar_id": session_policy.get("calendar_id"),
        "market_calendar_source": session_policy.get("calendar_source"),
        "requested_session_status": status,
        "requested_session_reason": reason,
        "requested_session_early_close": requested in early_close_dates,
    }


def _missing_match_reason(
    *,
    date_match_policy: str,
    session_context: Mapping[str, Any],
) -> str:
    if date_match_policy == DATE_MATCH_EXACT:
        return MATCH_REASON_REFUSED_EXACT_POLICY
    if session_context.get("requested_session_status") == SESSION_STATUS_UNKNOWN:
        return MATCH_REASON_REFUSED_NON_EQUITY_CALENDAR_UNKNOWN
    return MATCH_REASON_REFUSED_OUTSIDE_ROLL_WINDOW


def _rolled_match_reason(session_context: Mapping[str, Any]) -> str:
    if session_context.get("requested_session_status") == SESSION_STATUS_MARKET_CLOSED:
        return MATCH_REASON_ROLLED_FORWARD_MARKET_CLOSED
    if session_context.get("requested_session_status") == SESSION_STATUS_EXPECTED_TRADING:
        return MATCH_REASON_ROLLED_FORWARD_PROVIDER_MISSING
    return MATCH_REASON_REFUSED_NON_EQUITY_CALENDAR_UNKNOWN


def _date_from_price_key(key: str) -> Optional[date]:
    text = _as_text(key)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10]).date()
        except ValueError:
            return None


def _series_by_date(series: Mapping[str, float]) -> Dict[date, Tuple[str, float]]:
    by_date: Dict[date, Tuple[str, float]] = {}
    for key, value in sorted(series.items(), key=lambda item: _as_text(item[0])):
        parsed = _date_from_price_key(_as_text(key))
        if parsed is not None and parsed not in by_date:
            by_date[parsed] = (_as_text(key), float(value))
    return by_date


def _price_match(
    price_index: Mapping[str, Mapping[str, float]],
    ticker: str,
    timestamp: str,
    *,
    date_match_policy: str = DEFAULT_DATE_MATCH_POLICY,
    max_roll_days: int = DEFAULT_MAX_ROLL_DAYS,
    truth_session_policy: Optional[Mapping[str, Any]] = None,
) -> Tuple[Optional[float], Dict[str, Any]]:
    series = price_index.get(_upper(ticker))
    dt = _parse_dt(timestamp)
    exact = dt.isoformat()
    requested_date = dt.date()
    date_key = requested_date.isoformat()
    session_policy = truth_session_policy or {}
    session_context = _session_match_context(requested_date, session_policy)
    base = {
        "ticker": _upper(ticker),
        "requested_timestamp": timestamp,
        "requested_date": date_key,
        "actual_key": None,
        "actual_date": None,
        "match_policy": date_match_policy,
        "match_status": MATCH_STATUS_MISSING,
        "match_reason": _missing_match_reason(date_match_policy=date_match_policy, session_context=session_context),
        "roll_days": None,
        "max_roll_days": max_roll_days,
        **session_context,
    }
    if not series:
        return None, base
    for key in (exact, timestamp, date_key):
        if key in series:
            return float(series[key]), {
                **base,
                "actual_key": key,
                "actual_date": date_key,
                "match_status": MATCH_STATUS_EXACT,
                "match_reason": MATCH_REASON_EXACT_TRADING_SESSION,
                "roll_days": 0,
            }
    for key, value in series.items():
        if _as_text(key).startswith(date_key):
            return float(value), {
                **base,
                "actual_key": _as_text(key),
                "actual_date": date_key,
                "match_status": MATCH_STATUS_EXACT,
                "match_reason": MATCH_REASON_EXACT_TRADING_SESSION,
                "roll_days": 0,
            }
    if date_match_policy == DATE_MATCH_EXACT:
        return None, base
    if date_match_policy not in SUPPORTED_DATE_MATCH_POLICIES:
        raise ValueError(f"unsupported date_match_policy: {date_match_policy}")

    by_date = _series_by_date(series)
    for candidate_date in sorted(by_date):
        roll_days = (candidate_date - requested_date).days
        if 0 < roll_days <= max_roll_days:
            actual_key, value = by_date[candidate_date]
            return float(value), {
                **base,
                "actual_key": actual_key,
                "actual_date": candidate_date.isoformat(),
                "match_status": MATCH_STATUS_ROLLED_FORWARD,
                "match_reason": _rolled_match_reason(session_context),
                "roll_days": roll_days,
            }
    return None, base


def _price_at(price_index: Mapping[str, Mapping[str, float]], ticker: str, timestamp: str) -> Optional[float]:
    value, _match = _price_match(price_index, ticker, timestamp)
    return value


def _price_match_fields(prefix: str, match: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        f"{prefix}_requested_date": match.get("requested_date"),
        f"{prefix}_price_date": match.get("actual_date"),
        f"{prefix}_price_key": match.get("actual_key"),
        f"{prefix}_price_match_status": match.get("match_status"),
        f"{prefix}_price_match_reason": match.get("match_reason"),
        f"{prefix}_price_roll_days": match.get("roll_days"),
        f"{prefix}_requested_session_status": match.get("requested_session_status"),
        f"{prefix}_requested_session_reason": match.get("requested_session_reason"),
        f"{prefix}_requested_session_early_close": match.get("requested_session_early_close"),
        f"{prefix}_market_calendar_id": match.get("market_calendar_id"),
        f"{prefix}_market_calendar_source": match.get("market_calendar_source"),
    }


def _match_status_counts(rows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    fields = (
        "event_start_price_match_status",
        "event_end_price_match_status",
        "benchmark_start_price_match_status",
        "benchmark_end_price_match_status",
    )
    for row in rows:
        for field in fields:
            status = _as_text(row.get(field))
            if status:
                counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _match_reason_counts(rows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    fields = (
        "event_start_price_match_reason",
        "event_end_price_match_reason",
        "benchmark_start_price_match_reason",
        "benchmark_end_price_match_reason",
    )
    for row in rows:
        for field in fields:
            reason = _as_text(row.get(field))
            if reason:
                counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _members(claim: Mapping[str, Any]) -> List[str]:
    subject = claim.get("subject") if isinstance(claim.get("subject"), Mapping) else {}
    raw = subject.get("members")
    if not isinstance(raw, list):
        return []
    return sorted({_upper(member) for member in raw if _upper(member)})


def _benchmark_member_policy(event: Mapping[str, Any]) -> str:
    policy = _as_text(event.get("benchmark_member_policy"))
    return policy if policy in SUPPORTED_BENCHMARK_MEMBER_POLICIES else BENCHMARK_MEMBER_POLICY_REJECT


def _claim_resolution_base(claim: Mapping[str, Any]) -> Dict[str, Any]:
    event = claim.get("event") if isinstance(claim.get("event"), Mapping) else {}
    subject = claim.get("subject") if isinstance(claim.get("subject"), Mapping) else {}
    truth_binding = claim.get("truth_binding") if isinstance(claim.get("truth_binding"), Mapping) else {}
    comparison_event_key = _as_text(claim.get("comparison_event_key") or truth_binding.get("comparison_event_key"))
    key_payload: Dict[str, Any] = {}
    if not comparison_event_key:
        key_payload = comparison_event_key_payload(
            normalize_key_parts(
                subject_as_of=subject.get("as_of"),
                lane=subject.get("lane"),
                group=subject.get("group"),
                members=_members(claim),
                event_start=event.get("event_start"),
                event_end=event.get("event_end"),
                horizon=event.get("horizon"),
                benchmark=event.get("benchmark"),
                event_type=event.get("event_type"),
                outcome_basis=event.get("outcome_basis") or "equal_weight_group_return_direction",
                benchmark_member_policy=_benchmark_member_policy(event),
            )
        )
        comparison_event_key = key_payload["comparison_event_key"]
    return {
        "forecast_id": _as_text(claim.get("forecast_id")),
        "candidate_ref": _as_text(claim.get("candidate_ref")),
        "comparison_event_key": comparison_event_key,
        "comparison_event_key_schema": _as_text(claim.get("comparison_event_key_schema") or COMPARISON_EVENT_KEY_SCHEMA),
        "comparison_event_key_authority": _as_text(
            claim.get("comparison_event_key_authority")
            or truth_binding.get("comparison_event_key_authority")
            or key_payload.get("comparison_event_key_authority")
            or COMPARISON_EVENT_KEY_AUTHORITY
        ),
        "truth_join_key": _as_text(truth_binding.get("truth_join_key")),
        "subject_as_of": _as_text(subject.get("as_of")),
        "lane": _as_text(subject.get("lane")),
        "group": _as_text(subject.get("group")),
        "members_signature": members_signature(_members(claim)),
        "event_start": _as_text(event.get("event_start")),
        "event_end": _as_text(event.get("event_end")),
        "horizon": _as_text(event.get("horizon")),
        "benchmark": _as_text(event.get("benchmark")),
        "event_type": _as_text(event.get("event_type")),
        "outcome_basis": _as_text(event.get("outcome_basis") or "equal_weight_group_return_direction"),
        "benchmark_member_policy": _benchmark_member_policy(event),
        "expected_member_count": len(_members(claim)),
    }


def resolve_claim(
    claim: Mapping[str, Any],
    price_index: Mapping[str, Mapping[str, float]],
    *,
    resolver_as_of: str,
    truth_source: str,
    date_match_policy: str = DEFAULT_DATE_MATCH_POLICY,
    max_roll_days: int = DEFAULT_MAX_ROLL_DAYS,
    truth_session_policy: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    event = claim.get("event") if isinstance(claim.get("event"), Mapping) else {}
    subject = claim.get("subject") if isinstance(claim.get("subject"), Mapping) else {}
    base = _claim_resolution_base(claim)
    event_start = _iso(event.get("event_start"))
    event_end = _iso(event.get("event_end"))
    resolver_dt = _parse_dt(resolver_as_of)
    if _parse_dt(event_end) > resolver_dt:
        resolution = {**base, "status": STATUS_PENDING_MATURITY, "resolved_member_count": 0, "missing_members": _members(claim)}
        return [], resolution

    benchmark = _upper(event.get("benchmark"))
    if (
        _as_text(event.get("outcome_basis") or OUTCOME_BASIS_GROUP_RETURN) == OUTCOME_BASIS_GROUP_RETURN
        and _benchmark_member_policy(event) == BENCHMARK_MEMBER_POLICY_REJECT
        and benchmark in set(_members(claim))
    ):
        resolution = {
            **base,
            "status": STATUS_BENCHMARK_MEMBER_POLICY_VIOLATION,
            "resolved_member_count": 0,
            "missing_members": _members(claim),
        }
        return [], resolution

    benchmark_start, benchmark_start_match = _price_match(
        price_index,
        benchmark,
        event_start,
        date_match_policy=date_match_policy,
        max_roll_days=max_roll_days,
        truth_session_policy=truth_session_policy,
    )
    benchmark_end, benchmark_end_match = _price_match(
        price_index,
        benchmark,
        event_end,
        date_match_policy=date_match_policy,
        max_roll_days=max_roll_days,
        truth_session_policy=truth_session_policy,
    )
    if benchmark_start is None or benchmark_end is None or benchmark_start == 0:
        resolution = {
            **base,
            "status": STATUS_MISSING_BENCHMARK,
            "resolved_member_count": 0,
            "missing_members": _members(claim),
            "truth_date_match_policy": date_match_policy,
            "truth_date_match_max_roll_days": max_roll_days,
            "truth_session_policy": truth_session_policy or {},
            "benchmark_price_matches": {
                "start": benchmark_start_match,
                "end": benchmark_end_match,
            },
        }
        return [], resolution

    benchmark_return = (benchmark_end / benchmark_start) - 1.0
    rows: List[Dict[str, Any]] = []
    missing_members: List[str] = []
    missing_member_price_matches: Dict[str, Dict[str, Any]] = {}
    truth_binding = claim.get("truth_binding") if isinstance(claim.get("truth_binding"), Mapping) else {}
    for member in _members(claim):
        start_price, start_match = _price_match(
            price_index,
            member,
            event_start,
            date_match_policy=date_match_policy,
            max_roll_days=max_roll_days,
            truth_session_policy=truth_session_policy,
        )
        end_price, end_match = _price_match(
            price_index,
            member,
            event_end,
            date_match_policy=date_match_policy,
            max_roll_days=max_roll_days,
            truth_session_policy=truth_session_policy,
        )
        if start_price is None or end_price is None or start_price == 0:
            missing_members.append(member)
            missing_member_price_matches[member] = {
                "start": start_match,
                "end": end_match,
            }
            continue
        member_return = (end_price / start_price) - 1.0
        rows.append(
            {
                "target_id": member,
                "asset_class": _as_text(subject.get("lane")).upper() or "UNKNOWN",
                "forecast_id": _as_text(claim.get("forecast_id")),
                "candidate_ref": _as_text(claim.get("candidate_ref")),
                "comparison_event_key": base["comparison_event_key"],
                "comparison_event_key_schema": base["comparison_event_key_schema"],
                "comparison_event_key_authority": base["comparison_event_key_authority"],
                "truth_join_key": _as_text(truth_binding.get("truth_join_key")),
                "subject_as_of": _as_text(subject.get("as_of")),
                "lane": _as_text(subject.get("lane")),
                "group": _as_text(subject.get("group")),
                "members_signature": base["members_signature"],
                "event_start": event_start,
                "event_end": event_end,
                "horizon": _as_text(event.get("horizon")),
                "benchmark": benchmark,
                "event_type": _as_text(event.get("event_type")),
                "outcome_basis": _as_text(event.get("outcome_basis") or "equal_weight_group_return_direction"),
                "benchmark_member_policy": _benchmark_member_policy(event),
                "aggregation": _as_text(event.get("aggregation")),
                "member_return": round(member_return, 10),
                "benchmark_return": round(benchmark_return, 10),
                "subject_snapshot_price": float(start_price),
                "realized_truth_price": float(end_price),
                "benchmark_start_price": float(benchmark_start),
                "benchmark_end_price": float(benchmark_end),
                "truth_date_match_policy": date_match_policy,
                "truth_date_match_max_roll_days": max_roll_days,
                "truth_session_policy_id": (truth_session_policy or {}).get("policy_id"),
                **_price_match_fields("event_start", start_match),
                **_price_match_fields("event_end", end_match),
                **_price_match_fields("benchmark_start", benchmark_start_match),
                **_price_match_fields("benchmark_end", benchmark_end_match),
                "truth_quality_status": "OK",
                "truth_source": truth_source,
            }
        )

    status = STATUS_TRUTH_MATERIALIZED if rows else STATUS_MATURED_TRUTH_MISSING
    resolution = {
        **base,
        "status": status,
        "resolved_member_count": len(rows),
        "missing_members": missing_members,
        "benchmark_resolved": True,
        "coverage_ratio": round(len(rows) / max(len(_members(claim)), 1), 6),
        "truth_date_match_policy": date_match_policy,
        "truth_date_match_max_roll_days": max_roll_days,
        "truth_session_policy": truth_session_policy or {},
        "benchmark_price_matches": {
            "start": benchmark_start_match,
            "end": benchmark_end_match,
        },
        "missing_member_price_matches": missing_member_price_matches,
    }
    return rows, resolution


def resolve_claims(
    claims: Iterable[Mapping[str, Any]],
    price_history: Mapping[str, Any],
    *,
    resolver_as_of: str,
    truth_source: str = "price_history_artifact",
    date_match_policy: str = DEFAULT_DATE_MATCH_POLICY,
    max_roll_days: int = DEFAULT_MAX_ROLL_DAYS,
) -> Dict[str, Any]:
    if date_match_policy not in SUPPORTED_DATE_MATCH_POLICIES:
        raise ValueError(f"unsupported date_match_policy: {date_match_policy}")
    price_index = _load_price_index(price_history)
    truth_session_policy = _truth_session_policy(price_history)
    all_rows: List[Dict[str, Any]] = []
    resolutions: List[Dict[str, Any]] = []
    for claim in claims:
        rows, resolution = resolve_claim(
            claim,
            price_index,
            resolver_as_of=resolver_as_of,
            truth_source=truth_source,
            date_match_policy=date_match_policy,
            max_roll_days=max_roll_days,
            truth_session_policy=truth_session_policy,
        )
        all_rows.extend(rows)
        resolutions.append(resolution)

    status_counts: Dict[str, int] = {}
    for resolution in resolutions:
        status = _as_text(resolution.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "status": "AVAILABLE",
        "rows": all_rows,
        "claim_resolutions": resolutions,
        "summary": {
            "claim_count": len(resolutions),
            "truth_row_count": len(all_rows),
            "status_counts": dict(sorted(status_counts.items())),
            "date_match_policy": date_match_policy,
            "max_roll_days": max_roll_days,
            "truth_session_policy": truth_session_policy,
            "price_match_status_counts": _match_status_counts(all_rows),
            "price_match_reason_counts": _match_reason_counts(all_rows),
        },
    }


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    try:
        claims_path = config.get("admitted_claims") or config.get("forecast_claims") or config.get("forecast_cards")
        price_history_path = config.get("price_history")
        if not claims_path:
            raise ValueError("admitted_claims path is required")
        if not price_history_path:
            raise ValueError("price_history path is required")

        now = feed_envelope.utc_now()
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), Mapping) else {}
        resolver_as_of = _as_text(config.get("as_of") or runtime.get("as_of") or now.iso)
        claims_payload = _read_json(Path(str(claims_path)))
        price_history = _read_json(Path(str(price_history_path)))
        claims = load_admitted_claims(claims_payload)
        data = resolve_claims(
            claims,
            price_history,
            resolver_as_of=resolver_as_of,
            truth_source=_as_text(config.get("truth_source") or "price_history_artifact"),
            date_match_policy=_as_text(config.get("date_match_policy") or DEFAULT_DATE_MATCH_POLICY),
            max_roll_days=int(config.get("max_roll_days") or DEFAULT_MAX_ROLL_DAYS),
        )

        run_id = str(runtime.get("run_id") or (run_dir.name if run_dir else TOOL_NAME))
        diagnostics = feed_envelope.new_diagnostics(
            input_rows=len(claims),
            output_rows=len(data["rows"]),
            dropped_rows=0,
            resolver_as_of=resolver_as_of,
            status_counts=data["summary"]["status_counts"],
            date_match_policy=data["summary"]["date_match_policy"],
            max_roll_days=data["summary"]["max_roll_days"],
            price_match_status_counts=data["summary"]["price_match_status_counts"],
            price_match_reason_counts=data["summary"]["price_match_reason_counts"],
            truth_session_policy=data["summary"]["truth_session_policy"],
            source_refs={
                "admitted_claims": str(claims_path),
                "price_history": str(price_history_path),
            },
        )
        metadata = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="success",
            now=now,
            run_id=run_id,
            as_of=resolver_as_of,
            items_count=len(data["rows"]),
            diagnostics=diagnostics,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
        )
        return {"metadata": metadata, "data": data}
    except Exception as exc:
        return _failure_envelope(str(exc), run_dir=run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve matured CP1-admitted finance forecast claims from local price history.")
    parser.add_argument("--admitted-claims", required=True, help="finance_forecast_admission envelope or claim JSON.")
    parser.add_argument("--price-history", required=True, help="Local price-history artifact.")
    parser.add_argument("--as-of", required=True, help="Truth materialization timestamp.")
    parser.add_argument("--date-match-policy", default=DEFAULT_DATE_MATCH_POLICY, choices=sorted(SUPPORTED_DATE_MATCH_POLICIES))
    parser.add_argument("--max-roll-days", type=int, default=DEFAULT_MAX_ROLL_DAYS)
    parser.add_argument("--json", action="store_true", help="Print JSON envelope.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run(
        {
            "admitted_claims": args.admitted_claims,
            "price_history": args.price_history,
            "as_of": args.as_of,
            "date_match_policy": args.date_match_policy,
            "max_roll_days": args.max_roll_days,
            "runtime": {"run_id": TOOL_NAME, "as_of": args.as_of},
        }
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text if args.json else text)
    return 0 if payload.get("metadata", {}).get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
