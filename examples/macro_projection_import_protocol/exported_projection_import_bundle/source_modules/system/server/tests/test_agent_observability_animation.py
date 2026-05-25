from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from system.lib.agent_observability_animation import (
    build_agent_observability_animation_delta,
    build_agent_observability_animation_scene,
)


NOW = datetime(2026, 5, 20, 22, 0, 10, tzinfo=timezone.utc)


def _event(
    seq: int,
    *,
    session_id: str = "s1",
    source_runtime: str = "claude_code",
    canonical_type: str,
    summary: str = "",
    tool_use_id: str | None = None,
    payload: dict | None = None,
    observed_at: str | None = None,
    artifact_refs: list[str] | None = None,
) -> dict:
    at = observed_at or f"2026-05-20T22:00:{seq:02d}+00:00"
    return {
        "id": f"ev-{seq}",
        "seq": seq,
        "schema": "1.0.0",
        "trace_id": session_id,
        "source_runtime": source_runtime,
        "source_event_name": canonical_type,
        "canonical_type": canonical_type,
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "artifact_refs": artifact_refs or [],
        "observed_at": at,
        "occurred_at": at,
        "summary": summary or canonical_type,
        "payload": payload or {},
    }


def _status(*, dropped_count: int = 0, gap_count: int = 0) -> dict:
    return {
        "schema": "1.0.0",
        "api_revision": "agent_observability_backend_v2",
        "trace_path": "state/observability/agent_trace/events.jsonl",
        "seq": 99,
        "history_size": 99,
        "max_history": 2000,
        "dropped_count": dropped_count,
        "gap_count": gap_count,
        "persistence": {"enabled": True, "dropped_count": dropped_count},
        "source_status": [],
        "active_sessions": [
            {
                "session_id": "s1",
                "source_runtime": "claude_code",
                "title": "Fix trace viewer",
                "current_activity": "Bash: pytest",
                "last_observed_at": "2026-05-20T22:00:04+00:00",
                "last_canonical_type": "tool.completed",
                "cwd": "/repo",
                "lag_s": 6,
                "touched_files": ["system/server/main.py"],
            }
        ],
        "canonical_counts": {},
        "source_counts": {},
    }


def test_animation_scene_ties_tool_segments_to_real_event_ids() -> None:
    scene = build_agent_observability_animation_scene(
        events=[
            _event(1, canonical_type="turn.prompt", summary="make backend real"),
            _event(
                2,
                canonical_type="tool.started",
                summary="Read system/server/main.py",
                tool_use_id="tool-1",
                payload={"tool_name": "Read", "tool_input": {"file_path": "system/server/main.py"}},
            ),
            _event(5, canonical_type="tool.completed", summary="read ok", tool_use_id="tool-1"),
        ],
        status=_status(),
        now=NOW,
        window_ms=60_000,
    )

    assert scene["schema_version"] == "agent_observability_animation_v0"
    assert scene["actors"][0]["provider_label"] == "Claude Code"
    assert {event["id"] for event in scene["events"]} == {"ev-1", "ev-2", "ev-5"}
    assert any(event["animation_channel"] == "file_io" for event in scene["events"])
    assert any(event["animation_directive"] == "start_segment" for event in scene["events"])
    assert scene["cursor"]["next_since_seq"] == 5
    assert scene["stream_contract"]["delta_endpoint"] == "/api/agent-observability/animation/delta"
    assert {"spans", "flows", "counters", "file_impacts", "proof_receipts"} <= set(scene["stream_contract"]["primitive_families"])
    assert any(edge["type"] == "tool_lifecycle" and edge["tool_use_id"] == "tool-1" for edge in scene["edges"])
    segment = next(seg for track in scene["tracks"] for seg in track["segments"] if seg["event_id"] == "ev-2")
    assert segment["kind"] == "read"
    assert segment["channel"] == "file_io"
    assert segment["directive"] == "start_segment"
    assert segment["start_ms"] == 1000
    assert segment["end_ms"] >= 4000
    assert segment["event_node_id"] == "event:ev-2"
    assert any(span["event_id"] == "ev-2" and span["channel"] == "file_io" for span in scene["spans"])
    assert any(impact["path"] == "system/server/main.py" and impact["operation"] == "read" for impact in scene["file_impacts"])
    assert scene["counters"]


def test_animation_scene_emits_semantic_camera_primitives() -> None:
    scene = build_agent_observability_animation_scene(
        events=[
            _event(
                2,
                canonical_type="tool.started",
                summary="Edit system/server/main.py",
                tool_use_id="tool-edit",
                payload={"tool_name": "Edit", "tool_input": {"file_path": "system/server/main.py"}},
            ),
            _event(3, canonical_type="tool.completed", summary="edit ok", tool_use_id="tool-edit"),
            _event(
                4,
                canonical_type="tool.started",
                summary="Bash: pytest system/server/tests/test_agent_observability_animation.py",
                tool_use_id="tool-test",
                payload={"tool_name": "Bash", "tool_input": {"command": "pytest system/server/tests/test_agent_observability_animation.py"}},
            ),
            _event(5, canonical_type="tool.completed", summary="pytest passed", tool_use_id="tool-test"),
        ],
        status=_status(),
        mission_status={
            "missions": [
                {
                    "session_id": "other-agent",
                    "active_claims": [
                        {
                            "claim_id": "claim-main",
                            "path": "system/server/main.py",
                            "scope_kind": "path",
                        }
                    ],
                }
            ],
            "demoted_missions": [],
        },
        now=NOW,
        window_ms=60_000,
    )

    assert scene["summary"]["span_count"] >= 4
    assert scene["summary"]["flow_count"] >= 3
    assert scene["summary"]["file_impact_count"] >= 1
    assert scene["summary"]["proof_receipt_count"] >= 1
    impact = next(item for item in scene["file_impacts"] if item["path"] == "system/server/main.py")
    assert impact["operation"] == "write"
    assert impact["claim_state"] == "owned_by_other"
    assert impact["quality"]["authority"] == "projection"
    receipt = next(item for item in scene["proof_receipts"] if item["kind"] in {"test", "validation"})
    assert receipt["scope"] == "owned_surface"
    assert receipt["quality"]["authority"] == "canonical_event"


def test_animation_scene_attention_and_quality_use_real_trace_counts() -> None:
    scene = build_agent_observability_animation_scene(
        events=[
            _event(1, canonical_type="turn.prompt", summary="start"),
            _event(2, canonical_type="permission.requested", summary="needs approval"),
            _event(3, canonical_type="runtime.error", summary="command failed", payload={"is_error": True}),
        ],
        status=_status(dropped_count=2, gap_count=1),
        now=NOW,
        window_ms=60_000,
    )

    assert scene["summary"]["attention_count"] >= 2
    assert {item["kind"] for item in scene["attention"]} >= {"waiting_for_operator", "event_error"}
    assert scene["data_quality"]["dropped_count"] == 2
    assert scene["data_quality"]["gap_count"] == 1
    assert "store_history_dropped_events" in scene["data_quality"]["projection_notes"]
    assert "stream_gap_events_present" in scene["data_quality"]["projection_notes"]


def test_animation_scene_excludes_infrastructure_unless_requested() -> None:
    events = [
        _event(1, canonical_type="turn.prompt", summary="work"),
        _event(
            2,
            session_id="render-run",
            source_runtime="station_render",
            canonical_type="artifact.changed",
            summary="render done",
            artifact_refs=["state/observability/renders/run"],
        ),
    ]

    default_scene = build_agent_observability_animation_scene(
        events=events,
        status=_status(),
        now=NOW,
        window_ms=60_000,
    )
    full_scene = build_agent_observability_animation_scene(
        events=events,
        status=_status(),
        now=NOW,
        window_ms=60_000,
        include_infrastructure=True,
    )

    assert all(event["source_runtime"] != "station_render" for event in default_scene["events"])
    assert default_scene["data_quality"]["omitted_infrastructure_count"] == 1
    assert any(event["source_runtime"] == "station_render" for event in full_scene["events"])
    assert any(event["animation_kind"] == "render" for event in full_scene["events"])


def test_animation_delta_returns_cursor_ops_and_backpressure() -> None:
    delta = build_agent_observability_animation_delta(
        events=[
            _event(1, canonical_type="turn.prompt", summary="old"),
            _event(
                2,
                canonical_type="tool.started",
                summary="Edit api",
                tool_use_id="tool-edit",
                payload={"tool_name": "Edit", "tool_input": {"file_path": "system/server/ui/src/api.ts"}},
            ),
            _event(3, canonical_type="tool.completed", summary="edit ok", tool_use_id="tool-edit"),
        ],
        status=_status(),
        now=NOW,
        window_ms=60_000,
        since_seq=1,
        max_ops=200,
    )

    assert delta["kind"] == "agent_observability.animation_delta"
    assert delta["cursor"]["since_seq"] == 1
    assert delta["cursor"]["next_since_seq"] == 3
    assert delta["snapshot_required"] is False
    assert delta["backpressure"]["recommended_poll_ms"] >= 250
    assert any(op["op"] == "event_append" and op["event_id"] == "ev-2" for op in delta["ops"])
    assert any(op["op"] == "segment_upsert" and op["channel"] == "file_io" for op in delta["ops"])
    assert any(op["op"] == "span_upsert" for op in delta["ops"])
    assert any(op["op"] == "file_impact_upsert" for op in delta["ops"])
    assert any(op["op"] == "counter_update" for op in delta["ops"])
    assert all(op.get("quality") for op in delta["ops"])
    assert all((op.get("seq") or 0) >= 2 for op in delta["ops"] if op.get("event_id") in {"ev-2", "ev-3"})


def test_animation_delta_requires_snapshot_for_expired_or_degraded_cursor() -> None:
    status = _status(dropped_count=1, gap_count=1)
    status["seq"] = 5000
    status["history_size"] = 100
    status["max_history"] = 100

    delta = build_agent_observability_animation_delta(
        events=[_event(4999, canonical_type="runtime.error", summary="lost event", payload={"is_error": True})],
        status=status,
        now=NOW,
        window_ms=60_000,
        since_seq=12,
        max_ops=200,
    )

    assert delta["snapshot_required"] is True
    assert delta["cursor"]["earliest_available_seq"] == 4901
    assert delta["data_quality"]["snapshot_required"] is True
    assert delta["backpressure"]["degraded"] is True


def test_animation_delta_truncates_ops_without_hiding_the_gap() -> None:
    delta = build_agent_observability_animation_delta(
        events=[
            _event(seq, canonical_type="tool.started", summary=f"Bash: step {seq}", tool_use_id=f"tool-{seq}")
            for seq in range(1, 30)
        ],
        status=_status(),
        now=NOW,
        window_ms=60_000,
        since_seq=1,
        max_ops=50,
    )

    assert delta["op_count"] == 50
    assert delta["dropped_op_count"] > 0
    assert delta["snapshot_required"] is True
    assert delta["snapshot_reason"] == "delta_ops_truncated"


def test_animation_route_returns_scene_from_trace_store(monkeypatch) -> None:
    from system.server import main

    events = [
        _event(1, canonical_type="turn.prompt", summary="work"),
        _event(
            2,
            canonical_type="tool.started",
            summary="Bash: pytest",
            tool_use_id="tool-route",
            payload={"tool_name": "Bash", "tool_input": {"command": "pytest system/server/tests"}},
        ),
    ]

    class FakeStore:
        def status(self) -> dict:
            return _status()

        def replay(self, **_kwargs) -> list[dict]:
            return events

    monkeypatch.setattr(main, "agent_trace_store", FakeStore())
    monkeypatch.setattr(main, "_load_work_ledger_runtime_status", lambda _root: {})

    response = TestClient(main.app).get("/api/agent-observability/animation?limit=10&window_ms=60000")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "agent_observability.animation_scene"
    assert payload["summary"]["event_count"] == 2
    assert any(event["animation_kind"] == "validation" for event in payload["events"])


def test_animation_delta_route_returns_incremental_contract(monkeypatch) -> None:
    from system.server import main

    events = [
        _event(1, canonical_type="turn.prompt", summary="work"),
        _event(
            2,
            canonical_type="tool.started",
            summary="Bash: npm run build",
            tool_use_id="tool-build",
            payload={"tool_name": "Bash", "tool_input": {"command": "npm run build"}},
        ),
    ]

    class FakeStore:
        def status(self) -> dict:
            return _status()

        def replay(self, **_kwargs) -> list[dict]:
            return events

    monkeypatch.setattr(main, "agent_trace_store", FakeStore())
    monkeypatch.setattr(main, "_load_work_ledger_runtime_status", lambda _root: {})

    response = TestClient(main.app).get(
        "/api/agent-observability/animation/delta?since_seq=1&limit=10&window_ms=60000&max_ops=200"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "agent_observability.animation_delta"
    assert payload["cursor"]["since_seq"] == 1
    assert any(op["op"] == "event_append" and op["payload"]["animation_channel"] == "proof" for op in payload["ops"])
