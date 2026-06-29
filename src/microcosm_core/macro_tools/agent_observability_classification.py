"""
Public telemetry-quality classification over agent observability metadata.

This module is a source-faithful public refactor of
`system/lib/agent_observability_classification.py`. It preserves the macro
classifier behavior for auth-failure loops, stale sources, schema gaps, and
projection warnings while accepting only explicit public metadata envelopes.
It does not read live home session logs, provider payload bodies, browser/HUD
state, account/session state, credentials, cookies, or recipient-send material.

[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.agent_observability_classification` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: PASS, BLOCKED, KIND, SCHEMA_VERSION, SOURCE_REF, TARGET_REF, SOURCE_SYMBOL_REFS, TARGET_SYMBOL_REFS, SOURCE_REFS, TARGET_REFS, CLASS_ID_AUTH_FAILURE_LOOP, CLAUDE_MEM_OBSERVER_CWD_FRAGMENT, AUTH_FAILURE_TOKENS, DEFAULT_AUTH_FAILURE_TOKEN_REQUIRED, DEFAULT_MIN_LOOP_FAILURES, INFRASTRUCTURE_SOURCE_RUNTIMES_FOR_NOISE, FORBIDDEN_PAYLOAD_KEYS, AUTHORITY_CEILING, ANTI_CLAIM, INPUT_NAMES, HASH_CHUNK_SIZE, classify_auth_failure_loop, noisy_session_ids_from_classes, stale_source_warnings, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, cast

from microcosm_core.schemas import read_json_strict

PASS = "pass"
BLOCKED = "blocked"

KIND = "public_agent_observability_classification"
SCHEMA_VERSION = "agent_observability_classification_v0"
SOURCE_REF = "system/lib/agent_observability_classification.py"
TARGET_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/"
    "agent_observability_classification.py"
)
SOURCE_SYMBOL_REFS = [
    "system/lib/agent_observability_classification.py::classify_auth_failure_loop",
    "system/lib/agent_observability_classification.py::noisy_session_ids_from_classes",
    "system/lib/agent_observability_classification.py::stale_source_warnings",
    "system/lib/agent_observability_classification.py::classify_telemetry_quality",
]
TARGET_SYMBOL_REFS = [
    (
        "microcosm_core.macro_tools.agent_observability_classification::"
        "classify_auth_failure_loop"
    ),
    (
        "microcosm_core.macro_tools.agent_observability_classification::"
        "noisy_session_ids_from_classes"
    ),
    (
        "microcosm_core.macro_tools.agent_observability_classification::"
        "stale_source_warnings"
    ),
    (
        "microcosm_core.macro_tools.agent_observability_classification::"
        "classify_telemetry_quality"
    ),
    (
        "microcosm_core.macro_tools.agent_observability_classification::"
        "build_public_agent_observability_classification_view"
    ),
]
SOURCE_REFS = [
    SOURCE_REF,
    "codex/standards/std_agent_execution_trace.json",
    "codex/doctrine/paper_modules/agent_observability.md",
    "codex/doctrine/paper_modules/agent_self_observability_plane.md",
]
TARGET_REFS = [TARGET_REF]

CLASS_ID_AUTH_FAILURE_LOOP = "auth_failure_loop"
CLAUDE_MEM_OBSERVER_CWD_FRAGMENT = "/.claude-mem/observer-sessions"
AUTH_FAILURE_TOKENS = (
    "failed to authenticate",
    "401",
    "authentication_error",
)
DEFAULT_AUTH_FAILURE_TOKEN_REQUIRED = 2
DEFAULT_MIN_LOOP_FAILURES = 2
INFRASTRUCTURE_SOURCE_RUNTIMES_FOR_NOISE = frozenset(
    {
        "metabolism",
        "station_render",
        "backend",
    }
)
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
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_agent_observability_classification_metadata_only",
    "live_home_session_logs_read": False,
    "live_transcript_tail_authorized": False,
    "provider_payload_read": False,
    "hidden_reasoning_exported": False,
    "browser_hud_cockpit_state_exported": False,
    "account_session_state_exported": False,
    "credential_or_cookie_exported": False,
    "recipient_send_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Agent observability classification validates public metadata quality, "
    "noise classes, stale sources, schema gaps, and projection warnings. It "
    "does not read live logs, transcript bodies, provider payloads, hidden "
    "reasoning, browser/HUD state, account/session state, credentials, cookies, "
    "recipient-send material, or certify behavior changes."
)
INPUT_NAMES = (
    "bundle_manifest.json",
    "public_agent_events.json",
    "source_status.json",
    "telemetry_policy.json",
)
HASH_CHUNK_SIZE = 1024 * 1024


def _safe_mapping(value: object) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_safe_mapping` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value if isinstance(value, Mapping) else {}


def _payload_text(event: Mapping[str, Any]) -> str:
    """
    [ACTION]
    Best-effort flat string of the assistant content carried by `event`.
    - Teleology: Implements `_payload_text` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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


def _looks_like_auth_failure(
    text: str,
    *,
    required: int = DEFAULT_AUTH_FAILURE_TOKEN_REQUIRED,
) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_looks_like_auth_failure` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not text:
        return False
    lowered = text.lower()
    hits = sum(1 for token in AUTH_FAILURE_TOKENS if token in lowered)
    return hits >= required


def _is_observer_cwd(
    cwd: object,
    fragment: str = CLAUDE_MEM_OBSERVER_CWD_FRAGMENT,
) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_is_observer_cwd` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(cwd, str) or not cwd or not fragment:
        return False
    return fragment in cwd


def _representative_session(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_representative_session` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    [ACTION]
    Detect repeated unauthenticated assistant messages from SDK observer sessions.

    A session is flagged only when its `cwd` contains `cwd_fragment` and at
    least `min_failures` assistant-message events carry the authentication
    failure token floor.
    - Teleology: Implements `classify_auth_failure_loop` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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

    for rows in grouped.values():
        if len(rows) < min_failures:
            continue
        affected.append(_representative_session(rows))
        total_events += len(rows)
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
            "Refresh claude-mem CLAUDE_CODE_PATH / auth credentials, or stop "
            "the claude-mem worker, then drain the affected observer-session "
            "ids from the active mission view. Raw events remain available via "
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
    """
    [ACTION]
    Return session ids flagged by any noise class.
    - Teleology: Implements `noisy_session_ids_from_classes` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    """
    [ACTION]
    Flag source runtimes whose last observation is older than `stale_after_s`.
    - Teleology: Implements `stale_source_warnings` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
        rows.append(
            {
                "source_runtime": entry.get("source_runtime"),
                "last_observed_at": last,
                "lag_s": round(lag, 2),
                "event_count": entry.get("event_count"),
                "stale_after_s": stale_after_s,
            }
        )
    return rows


def _parse_iso(value: object) -> Optional[datetime]:
    """
    [ACTION]
    - Teleology: Implements `_parse_iso` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
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
    [ACTION]
    Build the telemetry-quality panel for public mission status reducers.
    - Teleology: Implements `classify_telemetry_quality` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    noise_classes: list[dict[str, Any]] = []
    auth = classify_auth_failure_loop(events)
    if auth:
        noise_classes.append(auth)

    persistence = _safe_mapping(persistence_status)
    projection_warnings: list[dict[str, Any]] = []
    if persistence.get("error_count"):
        projection_warnings.append(
            {
                "kind": "persistence_errors",
                "severity": "warn",
                "message": (
                    "AgentTraceStore reports persistence errors; on-disk "
                    "durability is degraded."
                ),
                "evidence": {
                    "error_count": persistence.get("error_count"),
                    "last_error": persistence.get("last_error"),
                },
            }
        )
    if persistence.get("retry_in_s"):
        projection_warnings.append(
            {
                "kind": "persistence_retrying",
                "severity": "info",
                "message": (
                    "AgentTraceStore is in retry backoff; new events may be "
                    "buffered in memory only."
                ),
                "evidence": {"retry_in_s": persistence.get("retry_in_s")},
            }
        )
    if dropped_count:
        projection_warnings.append(
            {
                "kind": "events_dropped",
                "severity": "warn",
                "message": f"{dropped_count} events dropped by the broadcaster queue.",
                "evidence": {"dropped_count": dropped_count},
            }
        )
    if gap_count:
        projection_warnings.append(
            {
                "kind": "stream_gaps",
                "severity": "info",
                "message": f"{gap_count} sequence gaps observed in the bounded window.",
                "evidence": {"gap_count": gap_count},
            }
        )

    schema_gaps: list[dict[str, Any]] = []
    canonical_counter: Counter[str] = Counter()
    for event in events:
        if not isinstance(event, Mapping):
            continue
        canonical = str(event.get("canonical_type") or "")
        canonical_counter[canonical] += 1
        if not canonical:
            schema_gaps.append(
                {
                    "kind": "missing_canonical_type",
                    "evidence_ref": (
                        f"agent_event:{event.get('seq')}"
                        if event.get("seq") is not None
                        else None
                    ),
                }
            )
    schema_gaps = schema_gaps[:8]

    return {
        "schema_version": SCHEMA_VERSION,
        "noise_classes": noise_classes,
        "stale_sources": stale_source_warnings(
            source_status,
            now=now,
            stale_after_s=stale_source_after_s,
        ),
        "schema_gaps": schema_gaps,
        "projection_warnings": projection_warnings,
        "history_limit_used": history_limit_used,
        "canonical_type_counts": dict(
            sorted(canonical_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:24]
        ),
    }


def load_public_agent_observability_classification_bundle(
    input_dir: str | Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_public_agent_observability_classification_bundle` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root = Path(input_dir)
    payloads: dict[str, Any] = {}
    for name in INPUT_NAMES:
        path = root / name
        if path.is_file():
            payloads[path.stem] = read_json_strict(path)
    return payloads


def build_public_agent_observability_classification_view(
    payloads: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_agent_observability_classification_view` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest = _safe_mapping(payloads.get("bundle_manifest"))
    events_payload = payloads.get("public_agent_events")
    source_payload = _safe_mapping(payloads.get("source_status"))
    policy = _safe_mapping(payloads.get("telemetry_policy"))

    events = _event_rows(events_payload)
    source_status = _source_status_rows(source_payload)
    persistence_status = _safe_mapping(
        source_payload.get("persistence_status") or source_payload.get("persistence")
    )
    resolved_now = (
        now
        or _parse_iso(policy.get("now"))
        or _parse_iso(manifest.get("generated_at"))
        or datetime.now(timezone.utc)
    )
    stale_after_s = _float_value(policy.get("stale_source_after_s"), default=600.0)
    gap_count = _int_value(source_payload.get("gap_count"), default=0)
    dropped_count = _int_value(source_payload.get("dropped_count"), default=0)
    history_limit_used = _optional_int(source_payload.get("history_limit_used"))

    findings: list[dict[str, Any]] = []
    if not events:
        findings.append(
            _bundle_finding(
                "AGENT_OBSERVABILITY_CLASSIFICATION_EVENT_ROWS_MISSING",
                "Public classification requires at least one explicit event row.",
                subject_id="public_agent_events",
            )
        )
    forbidden_payload_keys = sorted(FORBIDDEN_PAYLOAD_KEYS & _walk_payload_keys(payloads))
    findings.extend(
        _bundle_finding(
            "AGENT_OBSERVABILITY_CLASSIFICATION_FORBIDDEN_PAYLOAD_KEY",
            (
                "Public classification inputs cannot include transcript bodies, "
                "provider payloads, hidden reasoning, browser/HUD state, "
                "account/session state, credentials, cookies, recipient-send "
                "payloads, or live session state."
            ),
            subject_id=key,
        )
        for key in forbidden_payload_keys
    )
    if policy.get("public_metadata_only") is False:
        findings.append(
            _bundle_finding(
                "AGENT_OBSERVABILITY_CLASSIFICATION_POLICY_NOT_PUBLIC_ONLY",
                "telemetry_policy.public_metadata_only must not be false.",
                subject_id="telemetry_policy.public_metadata_only",
            )
        )

    telemetry_quality = classify_telemetry_quality(
        events=events,
        source_status=source_status,
        persistence_status=persistence_status,
        gap_count=gap_count,
        dropped_count=dropped_count,
        history_limit_used=history_limit_used,
        now=resolved_now,
        stale_source_after_s=stale_after_s,
    )
    noisy_session_ids = sorted(
        noisy_session_ids_from_classes(telemetry_quality["noise_classes"])
    )
    status = PASS if events and not findings else BLOCKED
    view_fingerprint = _stable_digest(
        {
            "bundle_id": manifest.get("bundle_id"),
            "telemetry_quality": telemetry_quality,
            "noisy_session_ids": noisy_session_ids,
            "findings": findings,
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": status,
        "bundle_id": manifest.get("bundle_id"),
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "source_refs": _strings(manifest.get("source_refs")) or SOURCE_REFS,
        "target_refs": _strings(manifest.get("target_refs")) or TARGET_REFS,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "body_import_verification": body_import_verification(),
        "telemetry_quality": telemetry_quality,
        "noisy_session_ids": noisy_session_ids,
        "event_count": len(events),
        "source_status_count": len(source_status),
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


def _event_rows(payload: object) -> list[Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_event_rows` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        events = payload.get("events")
        if isinstance(events, list):
            return [row for row in events if isinstance(row, Mapping)]
    return []


def _source_status_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_source_status_rows` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for key in ("source_status", "sources", "rows"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
    return []


def _walk_payload_keys(value: object) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_walk_payload_keys` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_walk_payload_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_payload_keys(child))
    return keys


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item.strip()]


def _int_value(value: object, *, default: int) -> int:
    """
    [ACTION]
    - Teleology: Implements `_int_value` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_int(value: object) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_optional_int` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_value(value: object, *, default: float) -> float:
    """
    [ACTION]
    - Teleology: Implements `_float_value` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _stable_digest(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_digest` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_file_sha256` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_repo_root_from_target` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
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


def body_import_verification() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `body_import_verification` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target_path = Path(__file__).resolve(strict=False)
    repo_root = _repo_root_from_target()
    source_path = repo_root / SOURCE_REF if repo_root else None
    source_digest = (
        _file_sha256(source_path)
        if source_path is not None and source_path.is_file()
        else ""
    )
    target_digest = _file_sha256(target_path) if target_path.is_file() else ""
    return {
        "verification_status": (
            "verified" if source_digest and target_digest else "target_available"
        ),
        "verification_mode": "verified_light_edit_recipe",
        "source_to_target_relation": "source_faithful_public_light_edit",
        "source_ref": SOURCE_REF,
        "target_ref": TARGET_REF,
        "source_body_digest": source_digest or None,
        "target_body_digest": target_digest or None,
        "rewrite_recipe_ref": TARGET_REF + "::classify_telemetry_quality",
        "source_symbol_refs": SOURCE_SYMBOL_REFS,
        "target_symbol_refs": TARGET_SYMBOL_REFS,
        "runtime_consumed_by": [
            (
                "python -m microcosm_core.macro_tools."
                "agent_observability_classification validate-public-bundle --input <dir>"
            ),
            (
                "microcosm-substrate/tests/"
                "test_agent_observability_classification_public.py"
            ),
        ],
        "body_in_receipt": False,
    }


def _bundle_finding(
    code: str,
    message: str,
    *,
    subject_id: str,
    subject_kind: str = "agent_observability_classification_input",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_bundle_finding` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `main` for `microcosm_core.macro_tools.agent_observability_classification` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        prog="python -m microcosm_core.macro_tools.agent_observability_classification"
    )
    parser.add_argument("action", choices=["validate-public-bundle"])
    parser.add_argument("--input", required=True)
    args = parser.parse_args(argv)

    if args.action == "validate-public-bundle":
        view = build_public_agent_observability_classification_view(
            cast(
                Mapping[str, Any],
                load_public_agent_observability_classification_bundle(args.input),
            )
        )
        print(json.dumps(view, indent=2, sort_keys=True))
        return 0 if view["status"] == PASS else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
