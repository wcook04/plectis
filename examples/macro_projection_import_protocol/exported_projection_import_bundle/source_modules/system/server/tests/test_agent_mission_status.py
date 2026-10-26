from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.agent_mission_status import (
    KIND,
    SCHEMA_VERSION,
    build_agent_mission_status,
)
from system.lib.agent_observability_classification import (
    CLASS_ID_AUTH_FAILURE_LOOP,
    classify_auth_failure_loop,
    classify_telemetry_quality,
    noisy_session_ids_from_classes,
)


NOW = datetime(2026, 5, 10, 0, 45, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixture builders


def _event(
    seq: int,
    *,
    session_id: str,
    source_runtime: str = "claude_code",
    canonical_type: str = "tool.completed",
    cwd: str | None = "/Users/example/src/ai_workflow",
    summary: str | None = None,
    payload: Mapping[str, Any] | None = None,
    minute: int = 45,
) -> dict[str, Any]:
    observed = NOW.replace(second=seq % 60, microsecond=(seq % 1000) * 1000) - timedelta(seconds=(60 - minute) * 60)
    return {
        "id": f"event-{seq}",
        "seq": seq,
        "schema": "1.0.0",
        "trace_id": session_id,
        "source_runtime": source_runtime,
        "source_event_name": canonical_type,
        "canonical_type": canonical_type,
        "session_id": session_id,
        "observed_at": observed.isoformat(),
        "occurred_at": observed.isoformat(),
        "cwd": cwd,
        "payload": dict(payload or {"content": summary or canonical_type}),
        "summary": summary or canonical_type,
    }


def _auth_failure_event(seq: int, *, session_id: str) -> dict[str, Any]:
    return _event(
        seq,
        session_id=session_id,
        canonical_type="message.assistant",
        cwd=f"/Users/example/.claude-mem/observer-sessions/{session_id}.jsonl",
        summary='Failed to authenticate. API Error: 401 {"error":{"type":"authentication_error"}}',
        payload={
            "role": "assistant",
            "content": (
                'Failed to authenticate. API Error: 401 '
                '{"type":"error","error":{"type":"authentication_error","message":"Invalid auth"}}'
            ),
        },
    )


def _healthy_claude_session_events(session_id: str, *, base_seq: int) -> list[dict[str, Any]]:
    return [
        _event(base_seq + 0, session_id=session_id, canonical_type="message.user", summary="user prompt"),
        _event(base_seq + 1, session_id=session_id, canonical_type="tool.proposed", summary="Bash"),
        _event(base_seq + 2, session_id=session_id, canonical_type="tool.completed", summary="ok"),
    ]


def _healthy_codex_session_events(session_id: str, *, base_seq: int) -> list[dict[str, Any]]:
    return [
        _event(base_seq + 0, session_id=session_id, source_runtime="codex_app", canonical_type="turn.prompt", summary="codex prompt"),
        _event(base_seq + 1, session_id=session_id, source_runtime="codex_app", canonical_type="tool.completed", summary="function_call_output"),
    ]


class _FakeStore:
    """Deterministic stand-in for ``AgentTraceStore`` used in pure tests."""

    def __init__(self, *, events: list[dict[str, Any]], status: dict[str, Any]):
        self._events = events
        self._status = status

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def replay(self, *, limit: int = 100, **_kwargs: Any) -> list[dict[str, Any]]:
        return list(self._events[-limit:])


# ---------------------------------------------------------------------------
# classify_auth_failure_loop


def test_classify_auth_failure_loop_detects_observer_session_storm():
    events = [
        _auth_failure_event(seq, session_id="obs-aaaa") for seq in range(1, 6)
    ] + [
        _auth_failure_event(seq, session_id="obs-bbbb") for seq in range(10, 13)
    ] + _healthy_claude_session_events("real-1", base_seq=20)

    noise = classify_auth_failure_loop(events)
    assert noise is not None
    assert noise["class_id"] == CLASS_ID_AUTH_FAILURE_LOOP
    assert noise["affected_session_count"] == 2
    assert noise["event_count"] == 5 + 3
    sids = {row["session_id"] for row in noise["representative_sessions"]}
    assert sids == {"obs-aaaa", "obs-bbbb"}
    assert noise["first_seq"] is not None and noise["last_seq"] is not None
    assert noise["first_seq"] <= noise["last_seq"]
    assert noise["raw_refs"], "raw_refs must be populated for drilldown"


def test_classify_auth_failure_loop_skips_singletons_and_non_observer_cwd():
    events = [
        _auth_failure_event(1, session_id="obs-zzzz"),  # singleton — below threshold
        _event(
            2,
            session_id="real-1",
            canonical_type="message.assistant",
            cwd="/Users/example/src/ai_workflow",
            summary="Failed to authenticate. API Error: 401",
            payload={"content": "Failed to authenticate. API Error: 401 — but this is a real session, not observer-cwd"},
        ),
    ]
    assert classify_auth_failure_loop(events) is None


def test_noisy_session_ids_from_classes_extracts_session_ids():
    events = [_auth_failure_event(seq, session_id="obs-xxxx") for seq in range(1, 5)]
    noise = classify_auth_failure_loop(events)
    assert noise is not None
    sids = noisy_session_ids_from_classes([noise])
    assert sids == {"obs-xxxx"}


def test_classify_auth_failure_loop_honors_configurable_cwd_fragment():
    """Caller-provided cwd_fragment must propagate to the matcher."""
    custom_cwd = "/Users/example/.alt-observer-rig/sessions/obs-yyyy.jsonl"
    events = [
        _event(
            seq,
            session_id="obs-yyyy",
            canonical_type="message.assistant",
            cwd=custom_cwd,
            summary='Failed to authenticate. API Error: 401 authentication_error',
            payload={"content": "Failed to authenticate. API Error: 401 authentication_error"},
        )
        for seq in range(1, 5)
    ]
    # Default cwd_fragment (claude-mem) does not match this directory:
    assert classify_auth_failure_loop(events) is None
    # Configurable cwd_fragment should match:
    noise = classify_auth_failure_loop(events, cwd_fragment="/.alt-observer-rig/")
    assert noise is not None
    assert noise["affected_session_count"] == 1
    assert noise["match_rule"]["cwd_fragment"] == "/.alt-observer-rig/"


def test_classify_auth_failure_loop_aggregate_seqs_span_all_matched_events():
    """first_seq and last_seq must cover the full storm, not just the first
    four representative rows used for raw_refs sampling."""
    seqs_for_session = list(range(100, 120))  # 20 events
    events = [_auth_failure_event(seq, session_id="obs-storm") for seq in seqs_for_session]
    noise = classify_auth_failure_loop(events)
    assert noise is not None
    assert noise["first_seq"] == 100
    assert noise["last_seq"] == 119
    # raw_refs stays capped at the per-session sample size.
    assert len(noise["raw_refs"]) <= 4
    # last_observed_at should reflect the latest matched event, not just the
    # first four.
    assert noise["last_observed_at"] is not None
    last_event = events[-1]
    assert noise["last_observed_at"] == last_event["observed_at"]


# ---------------------------------------------------------------------------
# classify_telemetry_quality projection panel


def test_classify_telemetry_quality_emits_noise_classes_and_projection_warnings():
    events = [
        _auth_failure_event(seq, session_id="obs-aaaa") for seq in range(1, 4)
    ] + _healthy_codex_session_events("codex-real", base_seq=10)

    panel = classify_telemetry_quality(
        events=events,
        source_status=[
            {"source_runtime": "claude_code", "last_observed_at": NOW.isoformat(), "event_count": 1},
            {
                "source_runtime": "metabolism",
                "last_observed_at": (NOW - timedelta(seconds=900)).isoformat(),
                "event_count": 1,
            },
        ],
        persistence_status={"error_count": 1, "last_error": "disk full"},
        gap_count=2,
        dropped_count=3,
        history_limit_used=200,
        now=NOW,
    )

    assert panel["schema_version"] == "agent_observability_classification_v0"
    classes = {entry["class_id"] for entry in panel["noise_classes"]}
    assert CLASS_ID_AUTH_FAILURE_LOOP in classes

    stale_runtimes = {row["source_runtime"] for row in panel["stale_sources"]}
    assert "metabolism" in stale_runtimes

    warning_kinds = {entry["kind"] for entry in panel["projection_warnings"]}
    assert "persistence_errors" in warning_kinds
    assert "events_dropped" in warning_kinds
    assert "stream_gaps" in warning_kinds


# ---------------------------------------------------------------------------
# build_agent_mission_status — acceptance specimen


def _make_acceptance_store() -> _FakeStore:
    """Three concurrent claude_code/codex sessions plus the 401 storm."""
    obs_events: list[dict[str, Any]] = []
    for sid in ("obs-aaaa", "obs-bbbb", "obs-cccc"):
        obs_events.extend(_auth_failure_event(seq, session_id=sid) for seq in range(1, 4))
    healthy = (
        _healthy_claude_session_events("claude-real", base_seq=100)
        + _healthy_codex_session_events("codex-real", base_seq=200)
    )
    events = obs_events + healthy

    active_sessions = [
        {
            "session_id": sid,
            "source_runtime": "claude_code",
            "last_observed_at": NOW.isoformat(),
            "last_canonical_type": "message.assistant",
            "cwd": f"/Users/example/.claude-mem/observer-sessions/{sid}.jsonl",
            "title": "Failed to authenticate. API Error: 401",
            "activity_count": 3,
            "touched_files": [],
        }
        for sid in ("obs-aaaa", "obs-bbbb", "obs-cccc")
    ] + [
        {
            "session_id": "claude-real",
            "source_runtime": "claude_code",
            "last_observed_at": NOW.isoformat(),
            "last_canonical_type": "tool.completed",
            "cwd": "/Users/example/src/ai_workflow",
            "title": "real claude session",
            "activity_count": 3,
            "touched_files": ["system/lib/agent_mission_status.py"],
        },
        {
            "session_id": "codex-real",
            "source_runtime": "codex_app",
            "last_observed_at": NOW.isoformat(),
            "last_canonical_type": "tool.completed",
            "cwd": None,
            "title": None,
            "activity_count": 2,
            "touched_files": [],
        },
        {
            "session_id": "metabolismd",
            "source_runtime": "metabolism",
            "last_observed_at": NOW.isoformat(),
            "last_canonical_type": "runtime.heartbeat",
            "cwd": None,
            "title": None,
            "activity_count": 0,
        },
    ]

    status = {
        "schema": "1.0.0",
        "api_revision": "agent_observability_backend_v2",
        "seq": 999,
        "history_size": 14,
        "max_history": 2000,
        "gap_count": 0,
        "dropped_count": 0,
        "persistence": {"enabled": True, "retry_in_s": 0.0, "dropped_count": 0, "error_count": 0, "last_error": None},
        "source_status": [
            {"source_runtime": "claude_code", "last_observed_at": NOW.isoformat(), "event_count": 12, "last_canonical_type": "tool.completed"},
            {"source_runtime": "codex_app", "last_observed_at": NOW.isoformat(), "event_count": 2, "last_canonical_type": "tool.completed"},
            {"source_runtime": "metabolism", "last_observed_at": (NOW - timedelta(seconds=1200)).isoformat(), "event_count": 1, "last_canonical_type": "runtime.heartbeat"},
        ],
        "active_sessions": active_sessions,
    }
    return _FakeStore(events=events, status=status)


def test_build_agent_mission_status_acceptance_specimen():
    store = _make_acceptance_store()

    payload = build_agent_mission_status(
        store=store,
        work_ledger_status={},
        history_limit=200,
        now=NOW,
    )

    # Shape contract -------------------------------------------------------
    assert payload["kind"] == KIND
    assert payload["schema_version"] == SCHEMA_VERSION
    for key in ("source", "health", "missions", "demoted_missions", "telemetry_quality", "raw_drilldown_refs"):
        assert key in payload, f"missing top-level field {key}"

    # Raw event availability preserved -------------------------------------
    assert payload["source"]["trace_path"].endswith("events.jsonl")
    assert payload["raw_drilldown_refs"]["endpoint_events"] == "/api/agent-observability/events"
    assert payload["raw_drilldown_refs"]["endpoint_websocket"] == "/ws/agent-observability"

    # Telemetry quality picks up the auth-failure-loop ---------------------
    classes = {entry["class_id"] for entry in payload["telemetry_quality"]["noise_classes"]}
    assert CLASS_ID_AUTH_FAILURE_LOOP in classes
    auth_class = next(
        e for e in payload["telemetry_quality"]["noise_classes"]
        if e["class_id"] == CLASS_ID_AUTH_FAILURE_LOOP
    )
    assert auth_class["affected_session_count"] == 3
    assert auth_class["raw_refs"], "auth_failure_loop must carry raw drilldown refs"

    # Noisy observer sessions excluded from default missions ---------------
    mission_session_ids = {row["session_id"] for row in payload["missions"]}
    assert mission_session_ids.isdisjoint({"obs-aaaa", "obs-bbbb", "obs-cccc"})

    # Healthy sessions still appear ----------------------------------------
    assert "claude-real" in mission_session_ids
    assert "codex-real" in mission_session_ids

    # Demoted list carries the noisy sessions for drilldown ----------------
    demoted_ids = {row["session_id"] for row in payload["demoted_missions"]}
    assert demoted_ids == {"obs-aaaa", "obs-bbbb", "obs-cccc"}
    for row in payload["demoted_missions"]:
        assert row["demoted"] is True
        assert row["demote_reason"] == "auth_failure_loop"
        assert row["raw_refs"]["events_endpoint"].startswith("/api/agent-observability/events?session_id=")

    # Source runtime counters remain visible -------------------------------
    by_runtime = payload["health"]["traffic"]["by_runtime"]
    assert "claude_code" in by_runtime
    assert "codex_app" in by_runtime
    assert payload["health"]["saturation"]["max_history"] == 2000
    assert payload["health"]["saturation"]["history_saturation_ratio"] is not None

    # Stale source warning fires for the metabolism heartbeat --------------
    stale = {row["source_runtime"] for row in payload["telemetry_quality"]["stale_sources"]}
    assert "metabolism" in stale

    # Constants exported so the frontend can drop its hardcoded copies -----
    assert "message.assistant" in payload["constants"]["activity_canonical_types"]
    assert "metabolism" in payload["constants"]["infrastructure_source_runtimes"]


def test_build_agent_mission_status_handles_empty_substrate():
    empty_store = _FakeStore(events=[], status={
        "seq": 0,
        "history_size": 0,
        "max_history": 2000,
        "gap_count": 0,
        "dropped_count": 0,
        "persistence": {"enabled": True, "retry_in_s": 0.0, "dropped_count": 0, "error_count": 0, "last_error": None},
        "source_status": [],
        "active_sessions": [],
    })
    payload = build_agent_mission_status(
        store=empty_store, work_ledger_status={}, now=NOW,
    )
    assert payload["missions"] == []
    assert payload["demoted_missions"] == []
    assert payload["telemetry_quality"]["noise_classes"] == []
    assert payload["health"]["traffic"]["events_per_second_total"] == 0.0
