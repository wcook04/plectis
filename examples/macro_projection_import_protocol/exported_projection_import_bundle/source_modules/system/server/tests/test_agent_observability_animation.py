from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from system.lib import work_ledger_runtime
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
    assert scene["data_quality"]["snapshot_required"] is False
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


def test_animation_route_default_limit_is_bounded_for_live_floor(monkeypatch) -> None:
    from system.server import main

    replay_calls: list[dict] = []

    class FakeStore:
        def status(self) -> dict:
            return _status()

        def replay(self, **kwargs) -> list[dict]:
            replay_calls.append(dict(kwargs))
            limit = int(kwargs.get("limit") or main._AGENT_OBSERVABILITY_ANIMATION_DEFAULT_LIMIT)
            return [
                _event(
                    seq,
                    canonical_type="tool.started",
                    summary=f"Bash: step {seq}",
                    tool_use_id=f"tool-{seq}",
                    observed_at="2026-05-20T22:00:10+00:00",
                )
                for seq in range(1, limit + 1)
            ]

    main._clear_agent_observability_work_ledger_cache_for_tests()
    monkeypatch.setattr(main, "agent_trace_store", FakeStore())
    monkeypatch.setattr(main, "_load_work_ledger_runtime_status", lambda _root: {})

    response = TestClient(main.app).get("/api/agent-observability/animation?window_ms=60000")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cursor"]["limit"] == main._AGENT_OBSERVABILITY_ANIMATION_DEFAULT_LIMIT
    assert payload["summary"]["event_count"] == main._AGENT_OBSERVABILITY_ANIMATION_DEFAULT_LIMIT
    assert replay_calls
    assert max(int(call.get("limit") or 0) for call in replay_calls) == main._AGENT_OBSERVABILITY_ANIMATION_DEFAULT_LIMIT


def test_agent_observability_work_ledger_status_reuses_short_cache(monkeypatch) -> None:
    from system.server import main

    calls = 0

    def fake_loader(_root):
        nonlocal calls
        calls += 1
        return {"sessions": {}, "loaded_by_test": calls}

    main._clear_agent_observability_work_ledger_cache_for_tests()
    monkeypatch.setattr(main, "_load_work_ledger_runtime_status", fake_loader)

    first = main._load_agent_observability_work_ledger_status(main.REPO_ROOT)
    second = main._load_agent_observability_work_ledger_status(main.REPO_ROOT)

    assert calls == 1
    assert first is second
    assert second["loaded_by_test"] == 1


def test_agent_observability_events_reuses_short_response_cache(monkeypatch) -> None:
    from system.server import main

    class FakeStore:
        seq = 99
        replay_calls = 0

        def status(self) -> dict:
            status = _status()
            status["seq"] = self.seq
            status["history_size"] = self.seq
            return status

        def replay(self, **kwargs) -> list[dict]:
            self.replay_calls += 1
            limit = int(kwargs["limit"])
            return [_event(limit, canonical_type="tool.started", summary=f"limit {limit}")]

    store = FakeStore()
    main._clear_agent_observability_events_cache_for_tests()
    monkeypatch.setattr(main, "agent_trace_store", store)

    client = TestClient(main.app)
    first = client.get("/api/agent-observability/events?limit=10")
    second = client.get("/api/agent-observability/events?limit=10")

    assert first.status_code == 200
    assert second.status_code == 200
    assert store.replay_calls == 1
    assert first.headers["etag"]
    assert first.headers["x-agent-projection-id"] == "agent_observability.events"
    assert first.headers["x-agent-cache"] == "miss"
    assert first.headers["x-agent-source-trace-seq"] == "99"
    assert first.headers["x-agent-trace-seq"] == "99"
    assert second.headers["x-agent-cache"] == "hit"
    assert second.headers["x-agent-body-bytes"] == str(len(second.content))
    assert second.headers["server-timing"].startswith("projection;dur=")
    assert first.json()["events"][0]["summary"] == "limit 10"
    assert second.json()["events"][0]["summary"] == "limit 10"

    unchanged = client.get(
        "/api/agent-observability/events?limit=10",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert unchanged.headers["x-agent-cache"] == "conditional"
    assert unchanged.headers["x-agent-body-bytes"] == "0"
    assert store.replay_calls == 1

    store.seq = 100
    third = client.get(
        "/api/agent-observability/events?limit=10",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert third.status_code == 200
    assert store.replay_calls == 2
    assert third.headers["etag"] != first.headers["etag"]
    assert third.headers["x-agent-cache"] == "miss"
    assert third.headers["x-agent-source-trace-seq"] == "100"
    main._clear_agent_observability_events_cache_for_tests()


def test_agent_observability_mission_status_reuses_short_response_cache(monkeypatch) -> None:
    from system.server import main

    class FakeStore:
        seq = 99

        def status(self) -> dict:
            status = _status()
            status["seq"] = self.seq
            status["history_size"] = self.seq
            return status

    calls = 0

    def fake_builder(*, store, work_ledger_status, repo_root, history_limit):
        nonlocal calls
        calls += 1
        return {
            "schema": "agent_mission_status_v1",
            "call": calls,
            "history_limit": history_limit,
            "work_ledger_loaded": bool(work_ledger_status),
            "repo_root": str(repo_root),
            "store_seq": store.status()["seq"],
        }

    store = FakeStore()
    main._clear_agent_observability_work_ledger_cache_for_tests()
    main._clear_agent_observability_mission_status_cache_for_tests()
    monkeypatch.setattr(main, "agent_trace_store", store)
    monkeypatch.setattr(main, "_load_work_ledger_runtime_status", lambda _root: {"sessions": {"s1": {}}})
    monkeypatch.setattr(main, "build_agent_mission_status", fake_builder)

    client = TestClient(main.app)
    first = client.get("/api/agent-observability/mission-status?history_limit=200")
    second = client.get("/api/agent-observability/mission-status?history_limit=200")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["etag"]
    assert first.headers["x-agent-projection-id"] == "agent_observability.mission_status"
    assert first.headers["x-agent-cache"] == "miss"
    assert first.headers["x-agent-source-trace-seq"] == "99"
    assert second.headers["x-agent-cache"] == "hit"
    assert second.headers["x-agent-body-bytes"] == str(len(second.content))
    assert calls == 1
    assert first.json()["call"] == 1
    assert second.json()["call"] == 1
    assert second.json()["work_ledger_loaded"] is True

    unchanged = client.get(
        "/api/agent-observability/mission-status?history_limit=200",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert unchanged.headers["x-agent-cache"] == "conditional"
    assert unchanged.headers["x-agent-body-bytes"] == "0"
    assert calls == 1

    store.seq = 100
    third = client.get(
        "/api/agent-observability/mission-status?history_limit=200",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert third.status_code == 200
    assert calls == 2
    assert third.json()["store_seq"] == 100
    assert third.headers["etag"] != first.headers["etag"]
    assert third.headers["x-agent-cache"] == "miss"
    assert third.headers["x-agent-source-trace-seq"] == "100"
    main._clear_agent_observability_work_ledger_cache_for_tests()
    main._clear_agent_observability_mission_status_cache_for_tests()


def test_agent_observability_mission_status_invalidates_on_work_ledger_signature(monkeypatch) -> None:
    from system.server import main

    class FakeStore:
        def status(self) -> dict:
            status = _status()
            status["seq"] = 99
            status["history_size"] = 99
            return status

    calls = 0
    signature_state = {"rev": 1}

    def fake_builder(*, store, work_ledger_status, repo_root, history_limit):
        nonlocal calls
        calls += 1
        return {
            "schema": "agent_mission_status_v1",
            "call": calls,
            "work_ledger_rev": work_ledger_status["rev"],
            "store_seq": store.status()["seq"],
        }

    main._clear_agent_observability_work_ledger_cache_for_tests()
    main._clear_agent_observability_mission_status_cache_for_tests()
    monkeypatch.setattr(main, "agent_trace_store", FakeStore())
    monkeypatch.setattr(
        main,
        "_agent_observability_work_ledger_signature",
        lambda _root: ("runtime_status.json", signature_state["rev"], 1, 1),
    )
    monkeypatch.setattr(
        main,
        "_load_work_ledger_runtime_status",
        lambda _root: {"rev": signature_state["rev"]},
    )
    monkeypatch.setattr(main, "build_agent_mission_status", fake_builder)

    client = TestClient(main.app)
    first = client.get("/api/agent-observability/mission-status?history_limit=200")
    second = client.get("/api/agent-observability/mission-status?history_limit=200")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls == 1
    assert second.json()["work_ledger_rev"] == 1

    signature_state["rev"] = 2
    third = client.get(
        "/api/agent-observability/mission-status?history_limit=200",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert third.status_code == 200
    assert calls == 2
    assert third.json()["work_ledger_rev"] == 2
    assert third.headers["etag"] != first.headers["etag"]
    assert third.headers["x-agent-cache"] == "miss"
    main._clear_agent_observability_work_ledger_cache_for_tests()
    main._clear_agent_observability_mission_status_cache_for_tests()


def test_agent_observability_host_pressure_reuses_short_cache(monkeypatch) -> None:
    from system.server import main

    calls = 0

    class FakeStore:
        def status(self) -> dict:
            return _status()

    def fake_builder(_store, _repo_root, **kwargs):
        nonlocal calls
        calls += 1
        return {
            "schema": "progress_pressure_packet_v1",
            "call": calls,
            "window_s": kwargs["window_s"],
            "activation": kwargs["activation_endpoint_probe"],
        }

    main._clear_agent_observability_host_pressure_cache_for_tests()
    monkeypatch.setattr(main, "agent_trace_store", FakeStore())
    monkeypatch.setattr(main, "build_progress_pressure_packet_from_store", fake_builder)

    client = TestClient(main.app)
    first = client.get("/api/agent-observability/host-pressure?window_s=900")
    second = client.get("/api/agent-observability/host-pressure?window_s=900")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls == 1
    assert first.json()["call"] == 1
    assert second.json()["call"] == 1
    assert second.json()["activation"]["url"] == "/api/agent-observability/host-pressure"
    main._clear_agent_observability_host_pressure_cache_for_tests()


def test_session_message_inbox_route_reads_disk_backed_bus(monkeypatch, tmp_path) -> None:
    from system.server import main

    messages_path = tmp_path / "session_messages.jsonl"
    inbound_message = work_ledger_runtime.build_session_message_receipt(
        message_id="smsg_blocker",
        from_session_id="codex_trace_projection",
        to_session_id="codex_demo_take_agent_native_editor",
        message_type="signal_blocker",
        subject="system/server/main.py claim",
        body="Please release the main.py Work Ledger claim when safe.",
        related_paths=["system/server/main.py"],
        requires_ack=True,
        issued_at="2026-06-01T22:00:00+00:00",
    )
    sent_message = work_ledger_runtime.build_session_message_receipt(
        message_id="smsg_ack",
        from_session_id="codex_demo_take_agent_native_editor",
        to_session_id="codex_trace_projection",
        message_type="acknowledge_merge_group",
        subject="ack",
        body="Received; line-disjoint route work preserved.",
        reply_to_message_id="smsg_blocker",
        issued_at="2026-06-01T22:01:00+00:00",
    )
    messages_path.write_text(
        "\n".join(
            [
                json.dumps({"session_message": inbound_message}),
                json.dumps({"session_message": sent_message}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "SESSION_MESSAGES_PATH", messages_path)

    response = TestClient(main.app).get(
        "/api/agent-observability/session-message-inbox"
        "?session_id=codex_demo_take_agent_native_editor"
        "&include_sent=true"
        "&limit=5"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == work_ledger_runtime.SESSION_MESSAGE_INBOX_SURFACE_SCHEMA
    assert payload["counts"]["message_event_count"] == 2
    assert payload["counts"]["inbox_message_count"] == 1
    assert payload["counts"]["sent_message_count"] == 1
    assert payload["latest_messages"][0]["message_id"] == "smsg_blocker"
    assert payload["latest_messages"][0]["acknowledged"] is True
    assert payload["sent_messages"][0]["message_id"] == "smsg_ack"
    assert "session-message-inbox --session-id codex_demo_take_agent_native_editor --limit 5" in payload[
        "recommended_commands"
    ]["poll_inbox"]
    assert payload["transport_boundary"]["claude_code_delivery"] == "poll_disk_backed_inbox_or_shell_command"
    assert payload["safety"]["no_process_signal_sent"] is True


def test_animation_delta_route_reuses_short_response_cache(monkeypatch) -> None:
    from system.server import main

    class FakeStore:
        seq = 99
        replay_calls = 0

        def status(self) -> dict:
            status = _status()
            status["seq"] = self.seq
            status["history_size"] = self.seq
            return status

        def replay(self, **_kwargs) -> list[dict]:
            self.replay_calls += 1
            return [_event(self.seq, canonical_type="tool.started", summary=f"seq {self.seq}")]

    mission_calls = 0
    delta_calls = 0

    def fake_mission_status(*, store, work_ledger_status, repo_root, history_limit):
        nonlocal mission_calls
        mission_calls += 1
        return {
            "schema": "agent_mission_status_v1",
            "history_limit": history_limit,
            "store_seq": store.status()["seq"],
            "work_ledger_loaded": bool(work_ledger_status),
        }

    def fake_delta(**kwargs):
        nonlocal delta_calls
        delta_calls += 1
        return {
            "kind": "agent_observability.animation_delta",
            "call": delta_calls,
            "event_count": len(kwargs["events"]),
            "since_seq": kwargs["since_seq"],
            "store_seq": kwargs["status"]["seq"],
            "mission_seq": kwargs["mission_status"]["store_seq"],
        }

    store = FakeStore()
    main._clear_agent_observability_work_ledger_cache_for_tests()
    main._clear_agent_observability_animation_delta_cache_for_tests()
    monkeypatch.setattr(main, "agent_trace_store", store)
    monkeypatch.setattr(main, "_load_work_ledger_runtime_status", lambda _root: {"sessions": {"s1": {}}})
    monkeypatch.setattr(main, "build_agent_mission_status", fake_mission_status)
    monkeypatch.setattr(main, "build_agent_observability_animation_delta", fake_delta)

    client = TestClient(main.app)
    first = client.get("/api/agent-observability/animation/delta?since_seq=1&limit=10&window_ms=60000")
    second = client.get("/api/agent-observability/animation/delta?since_seq=1&limit=10&window_ms=60000")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["etag"]
    assert first.headers["x-live-projection-cache"] == "miss"
    assert first.headers["x-agent-projection-id"] == "agent_observability.animation_delta"
    assert first.headers["x-agent-cache"] == "miss"
    assert second.headers["x-live-projection-cache"] == "hit"
    assert second.headers["x-agent-cache"] == "hit"
    assert second.headers["x-live-projection-source-seq"] == "99"
    assert second.headers["x-agent-source-trace-seq"] == "99"
    assert mission_calls == 1
    assert delta_calls == 1
    assert store.replay_calls == 1
    assert second.json()["call"] == 1
    assert second.json()["mission_seq"] == 99

    unchanged = client.get(
        "/api/agent-observability/animation/delta?since_seq=1&limit=10&window_ms=60000",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert unchanged.headers["x-live-projection-cache"] == "conditional"
    assert unchanged.headers["x-agent-cache"] == "conditional"
    assert mission_calls == 1
    assert delta_calls == 1
    assert store.replay_calls == 1

    store.seq = 100
    third = client.get(
        "/api/agent-observability/animation/delta?since_seq=1&limit=10&window_ms=60000",
        headers={"If-None-Match": first.headers["etag"]},
    )

    assert third.status_code == 200
    assert mission_calls == 2
    assert delta_calls == 2
    assert store.replay_calls == 2
    assert third.json()["store_seq"] == 100
    assert third.headers["etag"] != first.headers["etag"]
    main._clear_agent_observability_work_ledger_cache_for_tests()
    main._clear_agent_observability_animation_delta_cache_for_tests()


def test_agent_trace_mission_index_reuses_short_cache(tmp_path, monkeypatch) -> None:
    from system.server import main

    support_dir = tmp_path / "Agent Trace Structurer"
    support_dir.mkdir()
    mission_path = support_dir / "mission_index.json"
    variant_path = support_dir / "variant_artifact_index.json"

    def write_mission_index(row_count: int) -> None:
        rows = [
            {
                "session_id": f"s{index}",
                "provider": "codex",
                "session_file": f"/tmp/session-{index}.jsonl",
            }
            for index in range(row_count)
        ]
        mission_path.write_text(
            json.dumps(
                {
                    "schema": "mission_index_v1",
                    "generated_at": f"2026-05-20T22:00:{row_count:02d}+00:00",
                    "cwd": "/repo",
                    "ambiguity_window_seconds": 180,
                    "sort_mode": "recent",
                    "row_count": row_count,
                    "active_count": row_count,
                    "inactive_count": 0,
                    "hidden_old_count": 0,
                    "rows": rows,
                    "active_rows": rows,
                    "inactive_rows": [],
                }
            ),
            encoding="utf-8",
        )

    write_mission_index(1)
    variant_path.write_text(json.dumps({"sessions": {"s0": {"artifact_count": 2}}}), encoding="utf-8")
    main._clear_agent_trace_mission_index_cache_for_tests()
    monkeypatch.setattr(main, "_agent_trace_structurer_support_dir", lambda: support_dir)

    first = main._load_agent_trace_mission_index_bundle()
    second = main._load_agent_trace_mission_index_bundle()

    assert first is second
    assert second["row_count"] == 1
    assert second["variant_artifact_index"] == {"s0": {"artifact_count": 2}}

    write_mission_index(3)
    third = main._load_agent_trace_mission_index_bundle()

    assert third is not second
    assert third["row_count"] == 3
    assert len(third["rows"]) == 3

    response = TestClient(main.app).get("/api/agent-trace/mission-index")

    assert response.status_code == 200
    assert response.json()["row_count"] == 3
    main._clear_agent_trace_mission_index_cache_for_tests()


def test_agent_trace_session_projection_uses_cached_mission_index(tmp_path, monkeypatch) -> None:
    from system.server import main

    support_dir = tmp_path / "Agent Trace Structurer"
    support_dir.mkdir()
    mission_path = support_dir / "mission_index.json"
    mission_path.write_text(
        json.dumps(
            {
                "schema": "mission_index_v1",
                "generated_at": "2026-05-20T22:00:00+00:00",
                "cwd": "/repo",
                "row_count": 1,
                "active_count": 1,
                "inactive_count": 0,
                "hidden_old_count": 0,
                "rows": [
                    {
                        "session_id": "sess-a",
                        "provider": "codex",
                        "session_file": str(tmp_path / "missing-session.jsonl"),
                    }
                ],
                "active_rows": [],
                "inactive_rows": [],
            }
        ),
        encoding="utf-8",
    )
    build_calls = 0
    real_builder = main._build_agent_trace_mission_index_payload

    def counted_builder(mission_path_arg, variant_path_arg):
        nonlocal build_calls
        build_calls += 1
        return real_builder(mission_path_arg, variant_path_arg)

    main._clear_agent_trace_mission_index_cache_for_tests()
    main._clear_agent_trace_session_projection_cache_for_tests()
    monkeypatch.setattr(main, "_agent_trace_structurer_support_dir", lambda: support_dir)
    monkeypatch.setattr(main, "_build_agent_trace_mission_index_payload", counted_builder)

    client = TestClient(main.app)
    first = client.get("/api/agent-trace/session-projection?session_id=sess-a")
    second = client.get("/api/agent-trace/session-projection?session_id=sess-a")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["reason"] == "session_file_missing"
    assert second.json()["reason"] == "session_file_missing"
    assert build_calls == 1
    main._clear_agent_trace_mission_index_cache_for_tests()
    main._clear_agent_trace_session_projection_cache_for_tests()


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
