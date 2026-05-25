from __future__ import annotations

import json
import gzip
from pathlib import Path

import system.lib.agent_observability as agent_observability
from system.lib.agent_observability import (
    AgentObservabilitySampler,
    AgentTraceStore,
    _codex_session_id_from_record,
    _jsonl_tail,
    discover_claude_code_app_sessions,
    ingest_recent_claude_transcripts,
    ingest_recent_codex_rollouts,
)


def test_agent_trace_store_emits_persists_and_filters(tmp_path: Path) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")

    first = store.emit(
        source_runtime="claude_code",
        source_event_name="PreToolUse",
        canonical_type="tool.proposed",
        session_id="s1",
        payload={"tool_name": "Read", "cwd": "/repo"},
    )
    store.emit(
        source_runtime="codex_app",
        source_event_name="task_complete",
        canonical_type="turn.completed",
        session_id="c1",
        payload={"turn_id": "t1"},
    )

    assert first["seq"] == 1
    assert store.status()["seq"] == 2
    assert store.status()["source_counts"]["claude_code"] == 1
    assert store.replay(session_id="s1")[0]["canonical_type"] == "tool.proposed"
    assert store.replay(since_seq=1)[0]["session_id"] == "c1"
    persisted = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [event["seq"] for event in persisted] == [1, 2]


def test_agent_trace_store_degrades_when_trace_persistence_fails(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("blocks mkdir", encoding="utf-8")
    store = AgentTraceStore(tmp_path, trace_path=blocked_parent / "events.jsonl")

    event = store.emit(
        source_runtime="claude_code",
        source_event_name="PreToolUse",
        canonical_type="tool.proposed",
        session_id="s1",
        payload={"tool_name": "Read"},
    )

    status = store.status()
    assert event["seq"] == 1
    assert store.replay(session_id="s1")[0]["canonical_type"] == "tool.proposed"
    assert status["persistence"]["error_count"] == 1
    assert status["persistence"]["dropped_count"] == 1
    assert status["persistence"]["enabled"] is False


def test_agent_trace_store_loads_existing_tail_without_full_history_read(tmp_path: Path, monkeypatch) -> None:
    trace_path = tmp_path / "events.jsonl"
    with trace_path.open("w", encoding="utf-8") as handle:
        for seq in range(1, 5001):
            handle.write(json.dumps({
                "id": f"event-{seq}",
                "seq": seq,
                "schema": "1.0.0",
                "trace_id": "trace",
                "source_runtime": "claude_code",
                "source_event_name": "event",
                "canonical_type": "tool.completed",
                "session_id": f"s{seq % 3}",
                "observed_at": "2026-04-25T00:00:00+00:00",
                "payload": {"seq": seq},
            }) + "\n")

    def fail_read_text(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("bounded tail path must not call Path.read_text")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    store = AgentTraceStore(tmp_path, trace_path=trace_path, max_history=25)

    assert store.status()["seq"] == 5000
    assert len(store.replay(limit=100)) == 25
    assert store.replay(limit=1)[0]["seq"] == 5000


def test_agent_trace_store_compacts_oversized_payloads_before_persisting(tmp_path: Path) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    oversized = "SENTINEL_LARGE_TRACE_PAYLOAD" + ("x" * 180_000)

    event = store.emit(
        source_runtime="codex_app",
        source_event_name="runtime_event",
        canonical_type="runtime.event",
        session_id="large-session",
        payload={"content": oversized, "tool_name": "Bash"},
    )

    persisted_text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    persisted = json.loads(persisted_text)
    assert "SENTINEL_LARGE_TRACE_PAYLOAD" not in persisted_text
    assert len(persisted_text.encode("utf-8")) < 128 * 1024
    assert event["payload"]["content"]["compacted_payload_value"] is True
    assert persisted["payload_compaction"]["strategy"] == "compact_large_values"
    assert persisted["payload"]["tool_name"] == "Bash"


def test_agent_trace_store_rotates_large_trace_file_before_append(tmp_path: Path, monkeypatch) -> None:
    trace_path = tmp_path / "events.jsonl"
    trace_path.write_text(json.dumps({"old": "x" * 5000}) + "\n", encoding="utf-8")
    monkeypatch.setattr(agent_observability, "MAX_TRACE_FILE_BYTES", 1024)
    monkeypatch.setattr(agent_observability, "MAX_TRACE_ARCHIVES", 2)
    store = AgentTraceStore(tmp_path, trace_path=trace_path)

    store.emit(
        source_runtime="backend",
        source_event_name="heartbeat",
        canonical_type="runtime.heartbeat",
        session_id="s1",
        payload={"ok": True},
    )

    current_rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    archives = list((tmp_path / "archive").glob("events_*.jsonl.gz"))
    assert [row["session_id"] for row in current_rows] == ["s1"]
    assert len(archives) == 1
    with gzip.open(archives[0], "rt", encoding="utf-8") as handle:
        assert '"old"' in handle.read()


def test_jsonl_tail_reads_latest_records_without_full_history_read(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "events.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for seq in range(1, 1001):
            handle.write(json.dumps({"seq": seq, "payload": "x" * 200}) + "\n")

    def fail_read_text(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise AssertionError("bounded tail path must not call Path.read_text")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    rows = _jsonl_tail(path, limit=7)

    assert [row["seq"] for row in rows] == list(range(994, 1001))


def test_claude_hook_normalizer_preserves_provider_payload(tmp_path: Path) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")

    event = store.ingest_claude_hook(
        "pre-tool",
        {
            "hook_event_name": "PreToolUse",
            "session_id": "claude-session",
            "transcript_path": "/tmp/session.jsonl",
            "cwd": "/repo",
            "tool_name": "Bash",
        },
    )

    assert event["source_runtime"] == "claude_code"
    assert event["canonical_type"] == "tool.proposed"
    assert event["session_id"] == "claude-session"
    assert event["payload"]["tool_name"] == "Bash"


def test_codex_rollout_replay_uses_authoritative_jsonl(tmp_path: Path) -> None:
    sessions = tmp_path / ".codex/sessions/2026/04/25"
    sessions.mkdir(parents=True)
    rollout = sessions / "rollout-1-thread-a.jsonl"
    rollout.write_text(
        "\n".join(
            [
                json.dumps({"timestamp": "2026-04-25T00:00:00Z", "payload": {"type": "task_started", "thread_id": "thread-a", "turn_id": "turn-1"}}),
                json.dumps({"timestamp": "2026-04-25T00:00:02Z", "payload": {"type": "task_complete", "thread_id": "thread-a", "turn_id": "turn-1"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")

    result = ingest_recent_codex_rollouts(store, sessions_root=tmp_path / ".codex/sessions", file_limit=2, tail_lines=10)

    assert result["events_ingested"] == 2
    assert [event["canonical_type"] for event in store.replay(session_id="thread-a")] == [
        "turn.start",
        "turn.completed",
    ]


def test_claude_transcript_replay_appends_without_overwriting_live_events(tmp_path: Path) -> None:
    projects = tmp_path / ".claude/projects/repo"
    projects.mkdir(parents=True)
    transcript = projects / "claude-session.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "timestamp": "2026-04-25T00:00:00Z", "message": {"content": [{"type": "text", "text": "hello"}]}})
        + "\n",
        encoding="utf-8",
    )
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    live = store.ingest_claude_hook("SessionStart", {"hook_event_name": "SessionStart", "session_id": "live-session"})

    result = ingest_recent_claude_transcripts(store, projects_root=tmp_path / ".claude/projects", file_limit=1, tail_lines=5)

    assert live["seq"] == 1
    assert result["events_ingested"] == 1
    assert store.replay()[0]["session_id"] == "live-session"
    assert store.replay()[-1]["canonical_type"] == "message.user"


def test_claude_transcript_parser_emits_messages_thinking_and_tools(tmp_path: Path) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")

    events = store.ingest_claude_transcript_record(
        {
            "type": "assistant",
            "sessionId": "claude-session",
            "timestamp": "2026-04-25T00:00:00Z",
            "uuid": "row-1",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "", "signature": "redacted"},
                    {"type": "text", "text": "I will inspect the backend route."},
                    {"type": "tool_use", "id": "tool-1", "name": "Read", "input": {"file_path": "system/server/main.py"}},
                ],
            },
        },
        transcript_path="/tmp/claude-session.jsonl",
    )

    assert [event["canonical_type"] for event in events] == [
        "message.thinking",
        "message.assistant",
        "tool.started",
    ]
    assert events[0]["summary"] == "Thinking..."
    assert events[2]["tool_use_id"] == "tool-1"


def test_agent_trace_status_titles_sessions_and_touched_files(tmp_path: Path) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")

    store.ingest_claude_transcript_record(
        {"type": "user", "sessionId": "s1", "message": {"role": "user", "content": "set up bounded meta mission infrastructure"}},
        transcript_path="/tmp/s1.jsonl",
        cwd="/repo",
    )
    store.ingest_claude_transcript_record(
        {
            "type": "assistant",
            "sessionId": "s1",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "tool-1", "name": "Read", "input": {"file_path": "system/server/main.py"}}],
            },
        },
        transcript_path="/tmp/s1.jsonl",
        cwd="/repo",
    )

    session = next(row for row in store.status()["active_sessions"] if row["session_id"] == "s1")
    assert session["title"] == "Set up bounded meta mission infrastructure"
    assert session["activity_count"] == 2
    assert "system/server/main.py" in session["touched_files"]


def test_sampler_emits_backend_heartbeat_without_provider_activity(tmp_path: Path, monkeypatch) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    sampler = AgentObservabilitySampler(
        store,
        tmp_path,
        poll_interval_s=2,
        heartbeat_interval_s=2,
        codex_probe_interval_s=1_000_000,
        file_scan_interval_s=1_000_000,
        process_probe_interval_s=1_000_000,
    )
    monkeypatch.setattr("system.lib.agent_observability.discover_claude_code_app_sessions", lambda: [])

    sampler.poll_once()

    events = store.replay()
    heartbeats = [event for event in events if event["source_runtime"] == "backend"]
    assert heartbeats
    assert any(event["canonical_type"] == "runtime.heartbeat" for event in heartbeats)
    assert store.status()["sampler"]["running"] is True


def test_sampler_tails_only_new_codex_rollout_lines(tmp_path: Path) -> None:
    sessions = tmp_path / ".codex/sessions/2026/04/25"
    sessions.mkdir(parents=True)
    rollout = sessions / "rollout-1-thread-a.jsonl"
    rollout.write_text(
        json.dumps({"timestamp": "2026-04-25T00:00:00Z", "payload": {"type": "task_started", "thread_id": "thread-a", "turn_id": "old"}})
        + "\n",
        encoding="utf-8",
    )
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    sampler = AgentObservabilitySampler(
        store,
        tmp_path,
        poll_interval_s=2,
        heartbeat_interval_s=1_000_000,
        codex_probe_interval_s=1_000_000,
        file_scan_interval_s=2,
        process_probe_interval_s=1_000_000,
    )

    # Override the default home directory lookup by feeding the sampler's
    # offset table directly, then appending a new authoritative rollout line.
    sampler._file_offsets[str(rollout)] = rollout.stat().st_size
    rollout.write_text(
        rollout.read_text(encoding="utf-8")
        + json.dumps({"timestamp": "2026-04-25T00:00:01Z", "payload": {"type": "task_complete", "thread_id": "thread-a", "turn_id": "new"}})
        + "\n",
        encoding="utf-8",
    )

    for record in sampler._tail_new_jsonl(rollout):
        store.ingest_codex_rollout_record(record, rollout_path=str(rollout))

    events = store.replay(session_id="thread-a")
    assert len(events) == 1
    assert events[0]["turn_id"] == "new"
    assert events[0]["canonical_type"] == "turn.completed"


def test_sampler_publishes_active_claude_session(tmp_path: Path, monkeypatch) -> None:
    from tools.meta.bridge import session_transport

    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    sampler = AgentObservabilitySampler(
        store,
        tmp_path,
        poll_interval_s=2,
        heartbeat_interval_s=1_000_000,
        codex_probe_interval_s=1_000_000,
        file_scan_interval_s=1_000_000,
        process_probe_interval_s=1_000_000,
    )
    monkeypatch.setattr(
        session_transport,
        "read_active_session",
        lambda: {
            "extras": {
                "active_session": {
                    "session_id": "claude-live",
                    "last_event": "post-tool",
                    "transcript_path": "/tmp/live.jsonl",
                    "cwd": str(tmp_path),
                }
            }
        },
    )
    monkeypatch.setattr("system.lib.agent_observability.discover_claude_code_app_sessions", lambda: [])

    sampler.poll_once()

    active_events = [event for event in store.replay() if event["canonical_type"] == "session.heartbeat"]
    assert active_events
    assert active_events[0]["session_id"] == "claude-live"


def test_discovers_running_claude_code_app_sessions(tmp_path: Path, monkeypatch) -> None:
    sessions_root = tmp_path / ".claude/sessions"
    projects_root = tmp_path / ".claude/projects"
    sessions_root.mkdir(parents=True)
    cwd = "/Users/willcook/src/ai_workflow"
    session_id = "live-session"
    (sessions_root / "123.json").write_text(
        json.dumps(
            {
                "pid": 123,
                "sessionId": session_id,
                "cwd": cwd,
                "startedAt": 1777083856472,
                "kind": "interactive",
                "entrypoint": "claude-desktop",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    transcript = projects_root / "-Users-willcook-src-ai-workflow" / f"{session_id}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "investigate annex coverage and parallelism"}})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("system.lib.agent_observability._pid_running", lambda pid: pid == 123)

    sessions = discover_claude_code_app_sessions(sessions_root=sessions_root, projects_root=projects_root)

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["title"] == "Investigate annex coverage and parallelism"
    assert sessions[0]["transcript_path"] == str(transcript)


def test_sampler_emits_discovered_claude_code_app_sessions(tmp_path: Path, monkeypatch) -> None:
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    sampler = AgentObservabilitySampler(
        store,
        tmp_path,
        poll_interval_s=2,
        heartbeat_interval_s=1_000_000,
        codex_probe_interval_s=1_000_000,
        file_scan_interval_s=1_000_000,
        process_probe_interval_s=1_000_000,
    )
    monkeypatch.setattr(
        "system.lib.agent_observability.discover_claude_code_app_sessions",
        lambda: [
            {
                "pid": 123,
                "session_id": "live-session",
                "cwd": str(tmp_path),
                "entrypoint": "claude-desktop",
                "state_path": "/tmp/session.json",
            }
        ],
    )

    sampler.poll_once()

    events = [event for event in store.replay() if event["canonical_type"] == "session.discovered"]
    assert len(events) == 1
    assert events[0]["session_id"] == "live-session"


def test_sampler_primes_live_claude_session_with_recent_activity(tmp_path: Path, monkeypatch) -> None:
    transcript = tmp_path / "live-session.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "sessionId": "live-session", "message": {"role": "user", "content": "Please inspect the system."}}),
                json.dumps(
                    {
                        "type": "assistant",
                        "sessionId": "live-session",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "tool_use", "id": "tool-1", "name": "Bash", "input": {"description": "List files"}}],
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    sampler = AgentObservabilitySampler(
        store,
        tmp_path,
        poll_interval_s=1,
        heartbeat_interval_s=1_000_000,
        codex_probe_interval_s=1_000_000,
        file_scan_interval_s=1_000_000,
        process_probe_interval_s=1_000_000,
    )
    monkeypatch.setattr(
        "system.lib.agent_observability.discover_claude_code_app_sessions",
        lambda: [
            {
                "pid": 123,
                "session_id": "live-session",
                "cwd": str(tmp_path),
                "entrypoint": "claude-desktop",
                "state_path": "/tmp/session.json",
                "transcript_path": str(transcript),
            }
        ],
    )

    sampler.poll_once()

    activity_types = [event["canonical_type"] for event in store.replay(session_id="live-session")]
    assert "message.user" in activity_types
    assert "tool.started" in activity_types


def test_codex_session_id_resolver_prefers_legacy_payload_keys() -> None:
    record = {"type": "task_complete", "payload": {"thread_id": "thread-x", "turn_id": "t9"}}
    assert _codex_session_id_from_record(
        record, record["payload"], rollout_path="/some/rollout-2026-05-09T01-02-03-019e0eee-1c35-71a0-9e79-33bbf740fa33.jsonl"
    ) == "thread-x"


def test_codex_session_id_resolver_lifts_session_meta_id() -> None:
    record = {
        "type": "session_meta",
        "payload": {"id": "019e0eee-1c35-71a0-9e79-33bbf740fa33", "cwd": "/repo"},
    }
    assert _codex_session_id_from_record(
        record, record["payload"], rollout_path=None,
    ) == "019e0eee-1c35-71a0-9e79-33bbf740fa33"


def test_codex_session_id_resolver_falls_back_to_rollout_filename() -> None:
    record = {
        "type": "response_item",
        "payload": {"role": "assistant", "content": "hi"},
    }
    rollout = "/Users/x/.codex/sessions/2026/05/09/rollout-2026-05-09T23-49-06-019e0eee-1c35-71a0-9e79-33bbf740fa33.jsonl"
    assert _codex_session_id_from_record(record, record["payload"], rollout_path=rollout) == \
        "019e0eee-1c35-71a0-9e79-33bbf740fa33"
    # No rollout_path AND no payload id means we honestly return None rather
    # than guessing.
    assert _codex_session_id_from_record(record, record["payload"], rollout_path=None) is None


def test_ingest_codex_rollout_record_uses_filename_uuid_for_unidentified_records(tmp_path: Path) -> None:
    """A response_item record from a real rollout file should land under the
    UUID extracted from the filename, not under the literal ``codex_app``
    aggregate bucket."""
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    rollout = (
        tmp_path / "rollout-2026-05-09T23-49-06-019e0eee-1c35-71a0-9e79-33bbf740fa33.jsonl"
    )
    rollout.write_text("", encoding="utf-8")  # path just needs to exist for str()

    response_record = {
        "timestamp": "2026-05-09T23:50:00Z",
        "type": "response_item",
        "payload": {"type": "response_item", "role": "assistant", "content": "ok"},
    }
    event = store.ingest_codex_rollout_record(response_record, rollout_path=str(rollout))
    assert event["session_id"] == "019e0eee-1c35-71a0-9e79-33bbf740fa33"
    assert event["trace_id"] == "019e0eee-1c35-71a0-9e79-33bbf740fa33"
    assert event["source_runtime"] == "codex_app"


def test_ingest_codex_rollout_record_session_meta_uses_payload_id(tmp_path: Path) -> None:
    """A session_meta record carries the canonical session UUID at
    ``payload.id`` — confirm it propagates straight through to session_id /
    trace_id even before the filename fallback is consulted."""
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    meta_record = {
        "timestamp": "2026-05-09T23:49:06Z",
        "type": "session_meta",
        "payload": {
            "type": "session_meta",
            "id": "019e0eee-1c35-71a0-9e79-33bbf740fa33",
            "cwd": "/Users/willcook/src/ai_workflow",
        },
    }
    rollout = tmp_path / "rollout-with-no-uuid-in-name.jsonl"
    rollout.write_text("", encoding="utf-8")
    event = store.ingest_codex_rollout_record(meta_record, rollout_path=str(rollout))
    assert event["session_id"] == "019e0eee-1c35-71a0-9e79-33bbf740fa33"
    assert event["canonical_type"] == "session.start"


def test_ingest_codex_rollout_record_two_rollouts_yield_two_session_ids(tmp_path: Path) -> None:
    """Two distinct rollout files must produce two distinct canonical
    session_ids on the trace, not collapse into one aggregate bucket."""
    store = AgentTraceStore(tmp_path, trace_path=tmp_path / "events.jsonl")
    rollout_a = tmp_path / "rollout-2026-05-09T20-00-00-aaaaaaaa-1c35-71a0-9e79-33bbf740fa00.jsonl"
    rollout_b = tmp_path / "rollout-2026-05-09T21-00-00-bbbbbbbb-1c35-71a0-9e79-33bbf740fa11.jsonl"
    for r in (rollout_a, rollout_b):
        r.write_text("", encoding="utf-8")

    record = {
        "timestamp": "2026-05-09T20:00:01Z",
        "type": "response_item",
        "payload": {"type": "response_item", "role": "assistant", "content": "x"},
    }
    store.ingest_codex_rollout_record(record, rollout_path=str(rollout_a))
    store.ingest_codex_rollout_record(record, rollout_path=str(rollout_b))

    sids = {event["session_id"] for event in store.replay()}
    assert "aaaaaaaa-1c35-71a0-9e79-33bbf740fa00" in sids
    assert "bbbbbbbb-1c35-71a0-9e79-33bbf740fa11" in sids
    # The literal aggregate bucket must NOT be used when real ids are
    # available from the rollout filename.
    assert "codex_app" not in sids
