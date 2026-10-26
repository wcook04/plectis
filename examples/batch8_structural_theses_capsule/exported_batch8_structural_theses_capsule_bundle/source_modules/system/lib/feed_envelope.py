"""
[PURPOSE]
- Teleology: Shared, compatibility-focused helpers that every deterministic feed lane
  (stock / etf / macro / news / polymarket / stockgrid / calculator) uses to build
  status, diagnostics, and envelope metadata consistently without breaking per-lane ABI.
- Mechanism: Narrow utility functions (no framework, no class hierarchy) for UTC timestamp
  derivation, `as_of` / `run_id` resolution, diagnostics normalisation, bounded warning
  and partial-failure append, secret redaction, and envelope-metadata assembly.

[INTERFACE]
- Reads: Caller-supplied runtime dicts and `run_dir` hints. No disk or network I/O.
- Writes: Nothing. Pure return values; never mutates caller state unless the caller
  passes a diagnostics dict to the append helpers explicitly for in-place mutation.
- Exports: `UtcNow`, `utc_now`, `resolve_as_of`, `resolve_run_id`, `new_diagnostics`,
  `append_warning`, `append_partial_failure`, `record_fetch_outcome`,
  `redact_secret_values`, `warning_event`, `build_metadata`, `build_envelope`.

[CONSTRAINTS]
- Additive only: never rename or drop existing envelope keys; existing lane fields
  (legend, quality, display_hints, definitions, sector_map, data_schema, date_baseline)
  pass through the `extra` mapping unchanged.
- `metadata.timestamp` is `Union[float, str]` per `system/lib/types.py::ArtifactMetadata`;
  the builder preserves whatever the caller passes and defaults to `UtcNow.iso` only
  when the caller does not specify.
- Bounded diagnostics lists (default 500 warnings, 200 partial failures) prevent
  artifact explosion when a transient upstream outage floods messages.
- Stdlib only (datetime, re, os, typing, dataclasses) — no third-party deps so this
  module can be imported by every feed tool without widening the dependency graph.
- Determinism first: all canonical fields accept a single `UtcNow` instance so success
  and failure paths inside one `run()` share a single timestamp reading.
"""

from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from system.lib.types import TOOL_METADATA_SCHEMA_VERSION

__all__ = [
    "UtcNow",
    "utc_now",
    "resolve_as_of",
    "resolve_run_id",
    "new_diagnostics",
    "append_warning",
    "append_partial_failure",
    "record_fetch_outcome",
    "redact_secret_values",
    "warning_event",
    "build_metadata",
    "build_envelope",
    "DEFAULT_SECRET_ENV_KEYS",
    "DEFAULT_MAX_WARNINGS",
    "DEFAULT_MAX_PARTIAL_FAILURES",
]

# Secret names commonly surfaced by feed tools; kept in sync with run_tools6.SECRET_ENV_KEYS
# but widened here because individual lane modules may use a different subset.
DEFAULT_SECRET_ENV_KEYS: Sequence[str] = (
    "FRED_API_KEY",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_PHONE",
    "POLYGON_API_KEY",
    "ALPHAVANTAGE_API_KEY",
    "POLYMARKET_API_KEY",
)

DEFAULT_MAX_WARNINGS: int = 500
DEFAULT_MAX_PARTIAL_FAILURES: int = 200


@dataclass(frozen=True)
class UtcNow:
    """Single, internally-consistent UTC timestamp reading.

    Lanes capture one instance at the top of `run()` / `execute()` and reuse it for
    success and failure envelopes so that `timestamp`, `timestamp_iso`, `timestamp_epoch_s`,
    and `as_of` always describe the same instant.
    """

    iso: str
    epoch: float
    dt: datetime


def utc_now() -> UtcNow:
    """Produce one canonical UTC timestamp reading (iso + epoch + datetime)."""
    dt = datetime.now(timezone.utc).replace(microsecond=0)
    return UtcNow(iso=dt.isoformat(), epoch=dt.timestamp(), dt=dt)


def _coerce_iso_utc(value: str) -> Optional[str]:
    """Parse an ISO-ish timestamp and return a normalised UTC ISO string or None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def resolve_as_of(
    runtime: Optional[Mapping[str, Any]],
    *,
    fallback: Optional[UtcNow] = None,
) -> str:
    """Resolve the logical `as_of` ISO timestamp from `runtime.time_anchor`.

    Falls back to the provided `UtcNow.iso` if the anchor is missing or unparseable.
    Generates a fresh reading only if no fallback is supplied.
    """
    if isinstance(runtime, Mapping):
        anchor = runtime.get("time_anchor")
        iso = _coerce_iso_utc(anchor) if isinstance(anchor, str) else None
        if iso:
            return iso
    if fallback is not None:
        return fallback.iso
    return utc_now().iso


def resolve_run_id(
    runtime: Optional[Mapping[str, Any]],
    run_dir: Any = None,
    *,
    default: str = "unknown_run",
) -> str:
    """Resolve `run_id` from runtime context, falling back to run_dir basename.

    Preserves the existing `str(getattr(run_dir, "name", str(run_dir)))` semantics
    used across the feed lanes. Callers may override `default` to match their
    lane's current literal (e.g. stockgrid uses `"manual"`).
    """
    if isinstance(runtime, Mapping):
        rid = runtime.get("run_id")
        if isinstance(rid, str) and rid.strip():
            return rid.strip()
        rid_alt = runtime.get("run_dir")
        if isinstance(rid_alt, str) and rid_alt.strip() and not run_dir:
            return Path(rid_alt).name or default
    if run_dir:
        name = getattr(run_dir, "name", None)
        if isinstance(name, str) and name.strip():
            return name.strip()
        text = str(run_dir).strip()
        if text:
            return Path(text).name or text
    return default


def new_diagnostics(**extra: Any) -> Dict[str, Any]:
    """Return a fresh canonical diagnostics dict with the four required fields.

    Additional keys passed as kwargs are preserved (used by lanes that carry
    lane-specific diagnostics — imputation_policy, html_response_count, etc.).
    """
    diagnostics: Dict[str, Any] = {
        "input_rows": 0,
        "output_rows": 0,
        "dropped_rows": 0,
        "warnings": [],
    }
    diagnostics.update(extra)
    if not isinstance(diagnostics.get("warnings"), list):
        diagnostics["warnings"] = []
    return diagnostics


def _bounded_append(
    target: List[Any],
    item: Any,
    *,
    max_items: int,
    overflow_marker: str,
) -> None:
    """Append to a list while enforcing a hard cap and a single overflow marker."""
    if max_items <= 0:
        return
    if len(target) < max_items:
        target.append(item)
        return
    if target and target[-1] != overflow_marker:
        target.append(overflow_marker)


def append_warning(
    diagnostics: Dict[str, Any],
    message: str,
    *,
    max_warnings: int = DEFAULT_MAX_WARNINGS,
) -> None:
    """Append a plain-string warning to `diagnostics["warnings"]` with bounding.

    Existing lanes store warnings as plain strings; this helper preserves that shape
    so downstream consumers (Station, Oracle `feed_health`) do not break. For a
    structured per-item failure record, use `append_partial_failure` which writes to
    a sibling list.
    """
    text = str(message).strip()
    if not text:
        return
    warnings = diagnostics.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
        diagnostics["warnings"] = warnings
    _bounded_append(
        warnings,
        text,
        max_items=max_warnings,
        overflow_marker="… [warnings truncated]",
    )


def warning_event(
    *,
    code: str,
    lane: str,
    exc: Optional[BaseException] = None,
    message: Optional[str] = None,
    ticker: Optional[str] = None,
    series_id: Optional[str] = None,
    channel: Optional[str] = None,
    endpoint: Optional[str] = None,
    http_status: Optional[int] = None,
    extra: Optional[Mapping[str, Any]] = None,
    secret_env_keys: Sequence[str] = DEFAULT_SECRET_ENV_KEYS,
) -> Dict[str, Any]:
    """Build a structured warning event dict with secret-redacted message.

    Returns a plain dict; callers decide whether to stringify it into `warnings`
    (preserving current shape) or append it to `partial_failures`.
    """
    if exc is not None and not message:
        message = f"{type(exc).__name__}: {exc}"
    if not message and exc is not None:
        message = type(exc).__name__
    redacted = redact_secret_values(str(message or ""), env_keys=secret_env_keys)
    event: Dict[str, Any] = {
        "code": code,
        "lane": lane,
        "message": redacted,
    }
    if exc is not None:
        event["exception"] = type(exc).__name__
    if ticker:
        event["ticker"] = str(ticker)
    if series_id:
        event["series_id"] = str(series_id)
    if channel:
        event["channel"] = str(channel)
    if endpoint:
        event["endpoint"] = str(endpoint)
    if http_status is not None:
        event["http_status"] = int(http_status)
    if extra:
        for k, v in extra.items():
            if k not in event:
                event[k] = v
    return event


def append_partial_failure(
    diagnostics: Dict[str, Any],
    event: Mapping[str, Any],
    *,
    max_items: int = DEFAULT_MAX_PARTIAL_FAILURES,
) -> None:
    """Append a structured failure event to `diagnostics["partial_failures"]`.

    Separate from `warnings` so existing string-consumers are not disturbed. Also
    increments `fetch_failure_count` by convention when the event represents a
    per-item fetch failure.
    """
    failures = diagnostics.get("partial_failures")
    if not isinstance(failures, list):
        failures = []
        diagnostics["partial_failures"] = failures
    _bounded_append(
        failures,
        dict(event),
        max_items=max_items,
        overflow_marker="… [partial_failures truncated]",
    )


def record_fetch_outcome(
    diagnostics: Dict[str, Any],
    *,
    ok: bool,
) -> None:
    """Increment fetch-success / fetch-failure counters and refresh success rate.

    Idempotent scaffolding: lanes that do not call this retain their existing
    diagnostics shape; lanes that do call it gain the observability the feeds
    doctrine requires (Practical Refinement Axes §5).
    """
    success_key = "fetch_success_count"
    failure_key = "fetch_failure_count"
    rate_key = "fetch_success_rate"

    success = int(diagnostics.get(success_key, 0) or 0)
    failure = int(diagnostics.get(failure_key, 0) or 0)
    if ok:
        success += 1
    else:
        failure += 1
    total = success + failure
    diagnostics[success_key] = success
    diagnostics[failure_key] = failure
    diagnostics[rate_key] = round(success / total, 6) if total > 0 else 0.0


def redact_secret_values(
    text: str,
    env_keys: Sequence[str] = DEFAULT_SECRET_ENV_KEYS,
) -> str:
    """Redact env-backed secrets and `api_key=` URL parameters from a string."""
    out = str(text)
    out = re.sub(r"(?i)(api_key=)[^&\s]+", r"\1[redacted]", out)
    for key in env_keys:
        secret = os.environ.get(key)
        if secret and len(secret) >= 6:
            out = out.replace(secret, "[redacted]")
    return out


_METADATA_CORE_ORDER: Sequence[str] = (
    "tool",
    "status",
    "items_count",
    "timestamp",
    "timestamp_iso",
    "timestamp_epoch_s",
    "schema_version",
    "data_schema_version",
    "override_keys",
    "run_id",
    "as_of",
    "diagnostics",
)


def build_metadata(
    *,
    tool: str,
    status: str,
    now: UtcNow,
    run_id: str,
    as_of: str,
    items_count: int,
    diagnostics: Mapping[str, Any],
    data_schema_version: str,
    schema_version: str = TOOL_METADATA_SCHEMA_VERSION,
    timestamp: Union[float, str, None] = None,
    timestamp_iso: Optional[str] = None,
    timestamp_epoch_s: Optional[float] = None,
    legend: Optional[Mapping[str, Any]] = None,
    error: Optional[str] = None,
    always_include_error: bool = False,
    override_keys: Optional[Sequence[str]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a canonical metadata block for a feed envelope.

    Preserves per-lane polymorphism on `timestamp`:
      - Default (timestamp=None) writes `now.iso` — matches stock / macro / calculator.
      - Pass `timestamp=now.epoch` for news / polymarket / stockgrid legacy-epoch shape.
      - Pass any other value to preserve existing literal (e.g. the anchor string).

    `timestamp_iso` / `timestamp_epoch_s` default to `now.iso` / `now.epoch`, but can
    be overridden independently. news overrides `timestamp_iso` with `as_of` because
    its original shape coupled `timestamp_iso` to logical time rather than wall-clock.

    `always_include_error=True` emits `"error": None` even on success — required by
    lanes that historically emit the key unconditionally (stock, news). Other lanes
    omit the key on success.
    """
    md: Dict[str, Any] = {
        "tool": tool,
        "status": status,
        "items_count": int(items_count),
        "timestamp": timestamp if timestamp is not None else now.iso,
        "timestamp_iso": timestamp_iso if timestamp_iso is not None else now.iso,
        "timestamp_epoch_s": timestamp_epoch_s if timestamp_epoch_s is not None else now.epoch,
        "schema_version": schema_version,
        "data_schema_version": data_schema_version,
        "override_keys": list(override_keys or []),
        "run_id": run_id,
        "as_of": as_of,
        "diagnostics": copy.deepcopy(dict(diagnostics)),
    }
    if legend is not None:
        md["legend"] = dict(legend)
    if error is not None or always_include_error:
        md["error"] = error
    if extra:
        for key, value in extra.items():
            # Do not let `extra` clobber core identity fields by accident.
            if key in {"tool", "status", "diagnostics"}:
                continue
            md[key] = value
    return md


def build_envelope(metadata: Mapping[str, Any], data: Any) -> Dict[str, Any]:
    """Shallow `{metadata, data}` wrapper. Convenience only."""
    return {"metadata": dict(metadata), "data": data}
