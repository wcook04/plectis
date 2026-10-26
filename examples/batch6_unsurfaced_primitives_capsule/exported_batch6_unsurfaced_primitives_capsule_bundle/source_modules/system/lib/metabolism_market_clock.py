"""
Market clock for metabolismd always-on sampling.

[PURPOSE]
- Teleology: Emit metabolism events at a fixed eight-point structure of
  wall-clock fire times per market day so the repo captures a regime-aware
  market timeline without hourly polling or a separate scheduler runtime.
- Mechanism: Load the fire-point config from metabolism settings (with safe
  defaults), compute each point's wall-clock target in the configured market
  timezone, filter to points that have passed within a bounded grace window
  and have not already fired, emit one stable-digest-keyed event per due point,
  and project cross-day market status for CLI/doctor/blackboard surfaces.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from system.lib import metabolism_store as store


DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_FIRE_GRACE_MINUTES = 120
DEFAULT_FIRE_POINTS: tuple[dict[str, str], ...] = (
    {"name": "open", "local_time": "09:30"},
    {"name": "close", "local_time": "16:00"},
)
MARKET_HOURS_HOURLY_FIRE_POINTS: tuple[dict[str, str], ...] = (
    {"name": "open", "local_time": "09:30"},
    {"name": "hour_10_30", "local_time": "10:30"},
    {"name": "hour_11_30", "local_time": "11:30"},
    {"name": "hour_12_30", "local_time": "12:30"},
    {"name": "hour_13_30", "local_time": "13:30"},
    {"name": "hour_14_30", "local_time": "14:30"},
    {"name": "hour_15_30", "local_time": "15:30"},
    {"name": "close", "local_time": "16:00"},
)
SETTING_CLOCK_CONFIG = "market_clock"
SETTING_CLOCK_STATE = "market_clock_state"
TIMELINE_PATH_REL = Path("state/metabolism/market_timeline.jsonl")


@dataclass(frozen=True)
class FirePoint:
    name: str
    local_time: time
    target_dt_market: datetime
    target_dt_utc: datetime
    market_date: date


def default_config() -> dict[str, Any]:
    return {
        "enabled": True,
        "timezone": DEFAULT_TIMEZONE,
        "fire_grace_minutes": DEFAULT_FIRE_GRACE_MINUTES,
        "fire_points": [dict(entry) for entry in DEFAULT_FIRE_POINTS],
        "all_days_of_week": False,
    }


def market_hours_hourly_config() -> dict[str, Any]:
    config = default_config()
    config["fire_points"] = [dict(entry) for entry in MARKET_HOURS_HOURLY_FIRE_POINTS]
    return config


def load_config(conn) -> dict[str, Any]:
    raw = store.get_setting(conn, SETTING_CLOCK_CONFIG, None)
    merged = default_config()
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            merged[str(key)] = value
    return merged


def _parse_hhmm(text: str) -> time:
    hour_text, minute_text = str(text or "").strip().split(":", 1)
    return time(int(hour_text), int(minute_text))


def _tz_for(config: Mapping[str, Any]) -> tzinfo:
    try:
        return ZoneInfo(str(config.get("timezone") or DEFAULT_TIMEZONE))
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _operator_tz(now_utc: datetime | None = None, *, override: tzinfo | None = None) -> tzinfo:
    if override is not None:
        return override
    now = now_utc or datetime.now(timezone.utc)
    return now.astimezone().tzinfo or timezone.utc


def _tz_name(tz: tzinfo) -> str:
    return str(getattr(tz, "key", None) or getattr(tz, "zone", None) or tz)


def _weekday_name(value: date) -> str:
    return value.strftime("%A").lower()


def _date_is_enabled(market_date: date, config: Mapping[str, Any]) -> bool:
    if bool(config.get("all_days_of_week", True)):
        return True
    return market_date.weekday() < 5


def fire_key(point: FirePoint) -> str:
    return f"{point.name}:{point.market_date.isoformat()}"


def snapshot_key_for(point: FirePoint) -> str:
    return f"market_snapshot:{point.name}:{point.market_date.isoformat()}"


def enumerate_fire_points_for_date(market_date: date, config: Mapping[str, Any]) -> list[FirePoint]:
    if not _date_is_enabled(market_date, config):
        return []
    tz = _tz_for(config)
    points: list[FirePoint] = []
    for entry in config.get("fire_points") or []:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or "").strip()
        local_text = str(entry.get("local_time") or "").strip()
        if not name or not local_text:
            continue
        try:
            local_t = _parse_hhmm(local_text)
        except (ValueError, IndexError):
            continue
        target_market = datetime.combine(market_date, local_t, tzinfo=tz)
        points.append(
            FirePoint(
                name=name,
                local_time=local_t,
                target_dt_market=target_market,
                target_dt_utc=target_market.astimezone(timezone.utc),
                market_date=market_date,
            )
        )
    points.sort(key=lambda point: point.target_dt_utc)
    return points


def due_fire_points(
    now_utc: datetime,
    config: Mapping[str, Any],
    *,
    last_fired: Mapping[str, str] | None = None,
) -> list[FirePoint]:
    if not bool(config.get("enabled", True)):
        return []
    tz = _tz_for(config)
    now_market = now_utc.astimezone(tz)
    grace = timedelta(minutes=int(config.get("fire_grace_minutes") or DEFAULT_FIRE_GRACE_MINUTES))
    last = dict(last_fired or {})
    candidates: list[FirePoint] = []
    for offset_days in (-1, 0):
        check_date = now_market.date() + timedelta(days=offset_days)
        for point in enumerate_fire_points_for_date(check_date, config):
            if point.target_dt_utc > now_utc:
                continue
            if point.target_dt_utc < now_utc - grace:
                continue
            if last.get(fire_key(point)):
                continue
            candidates.append(point)
    candidates.sort(key=lambda fp: fp.target_dt_utc)
    return candidates


def _serialize_point(
    point: FirePoint,
    *,
    config: Mapping[str, Any],
    now_utc: datetime | None = None,
    fired_at_utc: str | None = None,
    operator_tz: tzinfo | None = None,
) -> dict[str, Any]:
    market_tz = _tz_for(config)
    operator_zone = _operator_tz(now_utc, override=operator_tz)
    grace = timedelta(minutes=int(config.get("fire_grace_minutes") or DEFAULT_FIRE_GRACE_MINUTES))
    passed = bool(now_utc and point.target_dt_utc <= now_utc)
    within_grace = bool(now_utc and passed and point.target_dt_utc >= (now_utc - grace))
    return {
        "name": point.name,
        "fire_point": point.name,
        "market_date": point.market_date.isoformat(),
        "weekday": _weekday_name(point.market_date),
        "is_weekend": point.market_date.weekday() >= 5,
        "market_timezone": _tz_name(market_tz),
        "operator_timezone": _tz_name(operator_zone),
        "target_time_market": point.target_dt_market.isoformat(),
        "target_time_local": point.target_dt_market.isoformat(),
        "target_time_utc": point.target_dt_utc.isoformat(),
        "target_time_operator_local": point.target_dt_utc.astimezone(operator_zone).isoformat(),
        "fired_at_utc": fired_at_utc,
        "passed": passed,
        "within_grace": within_grace,
        "snapshot_key": snapshot_key_for(point),
    }


def build_event(
    point: FirePoint,
    *,
    now_utc: datetime,
    config: Mapping[str, Any] | None = None,
    operator_tz: tzinfo | None = None,
) -> dict[str, Any]:
    effective_config = dict(config or default_config())
    payload = _serialize_point(
        point,
        config=effective_config,
        now_utc=now_utc,
        operator_tz=operator_tz,
    )
    payload["captured_at_utc"] = now_utc.isoformat()
    payload["captured_at_operator_local"] = now_utc.astimezone(_operator_tz(now_utc, override=operator_tz)).isoformat()
    stable_fields = {
        "kind": "market_fire",
        "fire_point": point.name,
        "market_date": point.market_date.isoformat(),
    }
    canonical = json.dumps(stable_fields, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "source": "market_clock",
        "kind": "market_fire",
        "payload": payload,
        "stable_digest": digest,
    }


def _parse_iso_date(value: str) -> date:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return date.min
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def record_fire(conn, point: FirePoint, *, now_utc: datetime | None = None) -> None:
    stamp = (now_utc or datetime.now(timezone.utc)).isoformat()
    state = dict(store.get_setting(conn, SETTING_CLOCK_STATE, {}) or {})
    last = dict(state.get("last_fired") or {})
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).date()
    last = {
        key: iso
        for key, iso in last.items()
        if isinstance(iso, str) and _parse_iso_date(iso) >= cutoff
    }
    last[fire_key(point)] = stamp
    state["last_fired"] = last
    store.set_setting(conn, SETTING_CLOCK_STATE, state)


def compute_and_emit_fires(conn, *, now_utc: datetime | None = None, operator_tz: tzinfo | None = None) -> list[dict[str, Any]]:
    now = now_utc or datetime.now(timezone.utc)
    config = load_config(conn)
    state = store.get_setting(conn, SETTING_CLOCK_STATE, {}) or {}
    last_fired = dict(state.get("last_fired") or {}) if isinstance(state, Mapping) else {}
    emitted: list[dict[str, Any]] = []
    for point in due_fire_points(now, config, last_fired=last_fired):
        event = build_event(point, now_utc=now, config=config, operator_tz=operator_tz)
        _row, created = store.enqueue_event(
            conn,
            source=event["source"],
            kind=event["kind"],
            payload=event["payload"],
            stable_digest=event["stable_digest"],
        )
        record_fire(conn, point, now_utc=now)
        if created:
            emitted.append(event)
    return emitted


def _last_fired_state(conn) -> dict[str, str]:
    state = store.get_setting(conn, SETTING_CLOCK_STATE, {}) or {}
    return dict(state.get("last_fired") or {}) if isinstance(state, Mapping) else {}


def _upcoming_points(now_utc: datetime, config: Mapping[str, Any], *, limit: int = 8) -> list[FirePoint]:
    tz = _tz_for(config)
    start_date = now_utc.astimezone(tz).date()
    upcoming: list[FirePoint] = []
    for offset_days in range(0, 8):
        check_date = start_date + timedelta(days=offset_days)
        for point in enumerate_fire_points_for_date(check_date, config):
            if point.target_dt_utc <= now_utc:
                continue
            upcoming.append(point)
        if len(upcoming) >= limit:
            break
    upcoming.sort(key=lambda point: point.target_dt_utc)
    return upcoming[:limit]


def preview_status(
    conn,
    *,
    now_utc: datetime | None = None,
    operator_tz: tzinfo | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    config = load_config(conn)
    market_tz = _tz_for(config)
    operator_zone = _operator_tz(now, override=operator_tz)
    now_market = now.astimezone(market_tz)
    last_fired = _last_fired_state(conn)
    today_points = enumerate_fire_points_for_date(now_market.date(), config)
    today = [
        _serialize_point(
            point,
            config=config,
            now_utc=now,
            fired_at_utc=last_fired.get(fire_key(point)),
            operator_tz=operator_zone,
        )
        for point in today_points
    ]
    upcoming = [
        _serialize_point(point, config=config, now_utc=now, operator_tz=operator_zone)
        for point in _upcoming_points(now, config)
    ]
    due_now = [
        _serialize_point(
            point,
            config=config,
            now_utc=now,
            fired_at_utc=last_fired.get(fire_key(point)),
            operator_tz=operator_zone,
        )
        for point in due_fire_points(now, config, last_fired=last_fired)
    ]
    return {
        "schema": "market_clock_status_v2",
        "generated_at_utc": now.isoformat(),
        "generated_at_market": now_market.isoformat(),
        "generated_at_local": now_market.isoformat(),
        "generated_at_operator_local": now.astimezone(operator_zone).isoformat(),
        "market_timezone": _tz_name(market_tz),
        "timezone": _tz_name(market_tz),
        "operator_timezone": _tz_name(operator_zone),
        "enabled": bool(config.get("enabled", True)),
        "all_days_of_week": bool(config.get("all_days_of_week", True)),
        "fire_grace_minutes": int(config.get("fire_grace_minutes") or DEFAULT_FIRE_GRACE_MINUTES),
        "today_market_date": now_market.date().isoformat(),
        "today": today,
        "today_fired": [entry for entry in today if entry.get("fired_at_utc")],
        "upcoming": upcoming,
        "next_fire": upcoming[0] if upcoming else None,
        "due_now": due_now,
        "timeline_path": str(TIMELINE_PATH_REL),
    }


def _project_market_job(job: Mapping[str, Any]) -> dict[str, Any]:
    params = dict(job.get("params") or {})
    op = dict(params.get("operation_parameters") or {})
    summary = dict(job.get("summary") or {})
    operation_id = str(params.get("operation_id") or job.get("kind") or "").strip()
    return {
        "id": job.get("id"),
        "kind": job.get("kind"),
        "operation_id": operation_id,
        "state": job.get("state"),
        "provider": job.get("provider"),
        "fire_point": op.get("fire_point") or summary.get("fire_point"),
        "market_date": op.get("market_date") or summary.get("market_date"),
        "snapshot_key": op.get("snapshot_key") or f"market_snapshot:{op.get('fire_point')}:{op.get('market_date')}",
        "bundle_key": op.get("bundle_key") or summary.get("bundle_key"),
        "run_id": op.get("run_id") or summary.get("run_id"),
        "updated_at": job.get("updated_at"),
        "last_error": job.get("last_error"),
    }


def _project_latest_snapshot(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    payload = dict(row.get("payload") or {})
    return {
        "snapshot_key": row.get("snapshot_key"),
        "fire_point": row.get("fire_point"),
        "market_date": row.get("market_date"),
        "capture_status": row.get("capture_status"),
        "captured_at_utc": row.get("captured_at_utc"),
        "captured_at_operator_local": row.get("captured_at_operator_local"),
        "ticker_success_count": row.get("ticker_success_count"),
        "ticker_error_count": row.get("ticker_error_count"),
        "error_summary": row.get("error_summary") or [],
        "timeline_path": row.get("timeline_path"),
        "timeline_row_digest": row.get("timeline_row_digest"),
        "provider": row.get("provider"),
        "source": row.get("source"),
        "target_time_market": row.get("target_time_market"),
        "target_time_utc": row.get("target_time_utc"),
        "universe_hash": row.get("universe_hash"),
        "universe_size": row.get("universe_size"),
        "payload_excerpt": {
            "capture_status": payload.get("capture_status"),
            "schema": payload.get("schema"),
        },
    }


def _nothing_ran_reason(
    preview: Mapping[str, Any],
    *,
    queued_jobs: list[dict[str, Any]],
    running_jobs: list[dict[str, Any]],
    latest_snapshot: Mapping[str, Any] | None,
    daemon_running: bool | None,
) -> str | None:
    if not bool(preview.get("enabled", True)):
        return "disabled"
    if daemon_running is False and ((preview.get("due_now") or []) or queued_jobs or running_jobs):
        return "daemon_not_running"
    if running_jobs or queued_jobs:
        return None
    if latest_snapshot and str(latest_snapshot.get("capture_status") or "").strip() == "total_failure":
        return "job_failed"
    if any(
        entry.get("passed") and not entry.get("fired_at_utc") and not entry.get("within_grace")
        for entry in (preview.get("today") or [])
    ):
        return "outside_grace"
    return "no_due_fire"


def build_market_projection(
    conn,
    *,
    now_utc: datetime | None = None,
    daemon_running: bool | None = None,
    operator_tz: tzinfo | None = None,
) -> dict[str, Any]:
    preview = preview_status(conn, now_utc=now_utc, operator_tz=operator_tz)
    queued_states = [store.JOB_STATE_QUEUED, store.JOB_STATE_RECOVERABLE, store.JOB_STATE_PAUSED]
    running_states = [store.JOB_STATE_CLAIMED, store.JOB_STATE_RUNNING, store.JOB_STATE_BLOCKED]
    queued_jobs = [
        _project_market_job(job)
        for job in store.fetch_jobs(conn, states=queued_states, limit=80)
        if str(job.get("kind") or "") in {"market_snapshot", "market_feed_bundle"}
    ]
    running_jobs = [
        _project_market_job(job)
        for job in store.fetch_jobs(conn, states=running_states, limit=80)
        if str(job.get("kind") or "") in {"market_snapshot", "market_feed_bundle"}
    ]
    latest = _project_latest_snapshot(store.latest_market_snapshot(conn))
    return {
        **preview,
        "schema": "market_clock_runtime_v1",
        "queued_jobs": queued_jobs,
        "running_jobs": running_jobs,
        "latest_snapshot": latest,
        "nothing_ran_reason": _nothing_ran_reason(
            preview,
            queued_jobs=queued_jobs,
            running_jobs=running_jobs,
            latest_snapshot=latest,
            daemon_running=daemon_running,
        ),
    }
