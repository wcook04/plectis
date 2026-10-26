"""
[PURPOSE]
- Teleology: Validate the Bridge-to-Claude resume protocol so resume messages, trigger emission, idle-safety, session discovery, and dispatch-and-yield bookkeeping fail deterministically instead of silently drifting in production.
- Mechanism: Drive `tools.meta.bridge.bridge_resume` through temporary inbox/ledger/session files, synthetic JSONL transcript deltas, and fake bridge drivers to assert protocol behavior at the file and ledger boundary.
- Non-goal: Live Claude Desktop injection or real bridge-provider execution; this cohort stays at the persisted protocol and driver-wrapper level.

[INTERFACE]
- Exports: Local helpers such as `_make_manager`, `_write_jsonl`, `_append_jsonl`, and the module's `test_*` cases.
- Reads: `tools.meta.bridge.bridge_resume` protocol objects and temp-path JSON/JSONL artifacts created inside each test.
- Writes: Temporary inbox files, ledger rows, and transport/session snapshots under `tmp_path`.
- Schema: Assertions cover resume message text, trigger payload envelopes, ledger event sequences, transport persistence, session activity reports, and dispatch-and-yield result objects.

[FLOW]
- Build a temporary resume target/manager or session transcript -> exercise one bridge-resume protocol surface -> inspect inbox payloads, ledger rows, or session reports -> assert the contract state transition.
- When-needed: Open when debugging resume-protocol regressions around trigger idempotency, idle-safety, session stamping, or dispatch-and-yield state transitions without reopening the full injector runtime.
- Escalates-to: tools/meta/bridge/bridge_resume.py; tools/meta/bridge/claude_app_injector.py
- Couples: These tests couple directly to `tools.meta.bridge.bridge_resume` ledger events, trigger schema, and once-only delivery rules.
- Navigation-group: server_backend

[DEPENDENCIES]
- json + pathlib.Path: Create and inspect temporary transport, inbox, ledger, and session transcript files.
- tools.meta.bridge.bridge_resume: Protocol implementation under test.

[CONSTRAINTS]
- Guarantee: Tests remain file-backed and deterministic by confining protocol state to `tmp_path`.
- Orders: Ledger and trigger assertions depend on append-only event ordering remaining stable.
- Non-goal: This module does not test real GUI paste injection or provider-specific bridge dispatch internals.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from system.lib import bridge_provider_pressure as pressure
from tools.meta.bridge import bridge_resume as br


# ----------------------------------------------------------------------
# format_resume_message
# ----------------------------------------------------------------------
def test_format_resume_message_emits_expected_sections() -> None:
    job = br.ResumeJob(
        job_id="job_abc",
        plan_id="plan_x",
        group_label="probe_a",
        status="ok",
        summary_lines=["count=75", "kernel=Darwin 24.6.0", "no errors"],
        artifact_paths=["dump/probe_a.md", "dump/probe_a_receipt.json"],
        continue_instruction="proceed to apply step",
    )
    msg = br.format_resume_message(job)
    assert "BRIDGE RESUME job=job_abc status=ok" in msg
    assert "plan: plan_x" in msg
    assert "group: probe_a" in msg
    assert "summary:" in msg
    assert "- count=75" in msg
    assert "artifacts:" in msg
    assert "- dump/probe_a.md" in msg
    assert "continue: proceed to apply step" in msg
    # short by construction
    assert len(msg) < 2048


def test_format_resume_message_truncates_long_summary() -> None:
    job = br.ResumeJob(
        job_id="job_long",
        summary_lines=[f"line {i}" for i in range(50)],
    )
    msg = br.format_resume_message(job, max_summary_lines=5)
    assert "- line 0" in msg
    assert "- line 4" in msg
    assert "- line 5" not in msg
    assert "truncated" in msg


def test_format_resume_message_handles_minimal_job() -> None:
    job = br.ResumeJob(job_id="bare")
    msg = br.format_resume_message(job)
    assert "BRIDGE RESUME job=bare status=ok" in msg
    assert "plan: n/a" in msg
    assert "group: n/a" in msg
    # No summary, artifacts, or continue lines
    assert "summary:" not in msg
    assert "artifacts:" not in msg
    assert "continue:" not in msg


# ----------------------------------------------------------------------
# new_id
# ----------------------------------------------------------------------
def test_new_id_is_unique_and_well_formed() -> None:
    a = br.ResumeJob.new_id(prefix="t")
    b = br.ResumeJob.new_id(prefix="t")
    assert a != b
    assert a.startswith("t_")
    assert len(a.split("_")) == 3  # prefix_ts_uuid8


# ----------------------------------------------------------------------
# emit_trigger + idempotency
# ----------------------------------------------------------------------
def _make_manager(tmp_path: Path) -> br.BridgeResumeManager:
    """
    [ACTION]
    - Teleology: Build the default temp-path `BridgeResumeManager` fixture used across trigger and ledger tests.
    - Mechanism: Create a fixed `ResumeTarget` and return a `BridgeResumeManager` bound to `tmp_path / "inbox"` and `tmp_path / "ledger.jsonl"`.
    - Reads: `tmp_path` and `tools.meta.bridge.bridge_resume` protocol classes.
    - Writes: None directly; returned manager will write under the supplied temp directory when used.
    - Guarantee: Returns a manager with a stable target and temp-local inbox/ledger paths.
    - Fails: None.
    - When-needed: Open when debugging why bridge-resume tests are using a particular inbox/ledger layout or target configuration.
    - Escalates-to: tools/meta/bridge/bridge_resume.py::BridgeResumeManager; system/server/tests/test_bridge_resume.py::test_emit_trigger_writes_inbox_file_and_ledger_row
    """
    target = br.ResumeTarget(target_app="Claude", switch_tab=3)
    return br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
    )


def test_emit_trigger_writes_inbox_file_and_ledger_row(tmp_path: Path) -> None:
    manager = _make_manager(tmp_path)
    job = br.ResumeJob(
        job_id="job_first",
        plan_id="p1",
        status="ok",
        summary_lines=["all good"],
        artifact_paths=["a.md"],
        continue_instruction="continue",
    )
    path = manager.emit_trigger(job)
    assert path is not None
    assert path.exists()
    payload = json.loads(path.read_text())
    assert payload["text"].startswith("BRIDGE RESUME job=job_first status=ok")
    assert payload["sentinel"].endswith("job=job_first")
    assert payload["target_app"] == "Claude"
    assert payload["switch_tab"] == 3
    assert payload["_resume"]["job_id"] == "job_first"
    # Ledger has exactly one trigger_written row
    rows = manager.ledger_rows(job_id="job_first")
    assert len(rows) == 1
    assert rows[0]["event"] == "trigger_written"


def test_emit_trigger_can_stage_without_submit(tmp_path: Path) -> None:
    manager = _make_manager(tmp_path)
    job = br.ResumeJob(job_id="job_stage", summary_lines=["operator review"])

    path = manager.emit_trigger(job, submit=False)

    assert path is not None
    payload = json.loads(path.read_text())
    assert payload["submit"] is False
    rows = manager.ledger_rows(job_id="job_stage")
    assert rows[0]["event"] == "trigger_written"


def test_emit_trigger_is_idempotent(tmp_path: Path) -> None:
    manager = _make_manager(tmp_path)
    job = br.ResumeJob(job_id="job_dup", summary_lines=["x"])

    first = manager.emit_trigger(job)
    second = manager.emit_trigger(job)

    assert first is not None
    assert second is None  # second is a deduped no-op

    # Inbox still has exactly one file (with the same name as first)
    files = list((tmp_path / "inbox").glob("*.json"))
    assert len(files) == 1
    assert files[0].name == "job_dup.json"

    # Ledger has trigger_written followed by skipped_dup
    rows = manager.ledger_rows(job_id="job_dup")
    events = [r["event"] for r in rows]
    assert events == ["trigger_written", "skipped_dup"]


def test_emit_trigger_allow_dup_bypasses_dedupe(tmp_path: Path) -> None:
    manager = _make_manager(tmp_path)
    job = br.ResumeJob(job_id="job_force", summary_lines=["x"])

    first = manager.emit_trigger(job)
    second = manager.emit_trigger(job, allow_dup=True)

    assert first is not None
    assert second is not None
    # Same filename (job-id-based) → second overwrites first; only one file
    assert first == second
    files = list((tmp_path / "inbox").glob("*.json"))
    assert len(files) == 1

    # Ledger has TWO trigger_written rows (no skipped_dup)
    rows = manager.ledger_rows(job_id="job_force")
    events = [r["event"] for r in rows]
    assert events == ["trigger_written", "trigger_written"]


def test_record_inject_result_appends_ledger(tmp_path: Path) -> None:
    manager = _make_manager(tmp_path)
    job = br.ResumeJob(job_id="job_done", summary_lines=["x"])
    manager.emit_trigger(job)
    manager.record_inject_result(
        "job_done", ok=True, error="", duration_ms=1234
    )
    manager.record_inject_result(
        "job_done", ok=False, error="modal blocking", duration_ms=999
    )
    rows = manager.ledger_rows(job_id="job_done")
    events = [r["event"] for r in rows]
    assert events == ["trigger_written", "inject_ok", "inject_failed"]
    assert rows[1]["details"]["duration_ms"] == 1234
    assert rows[2]["details"]["error"] == "modal blocking"


# ----------------------------------------------------------------------
# transport persistence
# ----------------------------------------------------------------------
def test_resume_target_round_trip_through_transport(tmp_path: Path) -> None:
    transport_path = tmp_path / "claude_session_transport.json"
    target = br.ResumeTarget(
        target_app="Claude",
        switch_tab=3,
        session_id="cli_session_xyz",
        session_url=None,
        sentinel_prefix="[bridge resume]",
    )

    written = br.write_resume_target(target, transport_path=transport_path)
    assert written.exists()

    rec = json.loads(written.read_text())
    # Existing top-level schema preserved
    assert "transport_schema_version" in rec
    # New resume target stashed under extras
    assert rec["extras"]["bridge_resume"]["target"]["session_id"] == "cli_session_xyz"
    assert rec["extras"]["bridge_resume"]["target"]["switch_tab"] == 3

    loaded = br.discover_resume_target(transport_path=transport_path)
    assert loaded is not None
    assert loaded.target_app == "Claude"
    assert loaded.switch_tab == 3
    assert loaded.session_id == "cli_session_xyz"


def test_clear_resume_target_removes_block(tmp_path: Path) -> None:
    transport_path = tmp_path / "claude_session_transport.json"
    target = br.ResumeTarget(target_app="Claude", switch_tab=3)
    br.write_resume_target(target, transport_path=transport_path)

    assert br.clear_resume_target(transport_path=transport_path) is True
    rec = json.loads(transport_path.read_text())
    assert "bridge_resume" not in rec.get("extras", {})

    # Idempotent: clearing an already-cleared transport returns False
    assert br.clear_resume_target(transport_path=transport_path) is False


def test_discover_resume_target_returns_none_when_missing(tmp_path: Path) -> None:
    transport_path = tmp_path / "no_such_file.json"
    assert br.discover_resume_target(transport_path=transport_path) is None


# ----------------------------------------------------------------------
# session snapshot + idle-check primitive (1.1.0)
# ----------------------------------------------------------------------
def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_capture_session_snapshot_returns_none_when_unknown(tmp_path: Path) -> None:
    assert br.capture_session_snapshot(None, projects_dir=tmp_path) is None
    assert br.capture_session_snapshot("missing", projects_dir=tmp_path) is None


def test_capture_session_snapshot_records_size_and_path(tmp_path: Path) -> None:
    sid = "test_session"
    jsonl = tmp_path / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "hello"}}])
    snap = br.capture_session_snapshot(sid, projects_dir=tmp_path)
    assert snap is not None
    assert snap.session_id == sid
    assert snap.jsonl_path == str(jsonl)
    assert snap.jsonl_byte_size == jsonl.stat().st_size
    assert snap.captured_at  # set


def test_assess_session_activity_no_delta_is_safe(tmp_path: Path) -> None:
    sid = "sess_no_delta"
    jsonl = tmp_path / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "x"}}])
    snap = br.capture_session_snapshot(sid, projects_dir=tmp_path)
    assert snap is not None
    report = br.assess_session_activity(snap, "[bridge resume] job=t1")
    assert report.safe_to_inject is True
    assert report.reason == "no_delta"
    assert report.delta_bytes == 0


def test_assess_session_activity_assistant_only_delta_is_safe(tmp_path: Path) -> None:
    sid = "sess_assist"
    jsonl = tmp_path / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "hi"}}])
    snap = br.capture_session_snapshot(sid, projects_dir=tmp_path)
    assert snap is not None
    _append_jsonl(
        jsonl,
        [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "still typing"}],
                },
            }
        ],
    )
    report = br.assess_session_activity(snap, "[bridge resume] job=t2")
    assert report.safe_to_inject is True
    assert report.reason == "assistant_only_delta"
    assert report.has_delta is True


def test_assess_session_activity_foreign_user_blocks(tmp_path: Path) -> None:
    sid = "sess_foreign"
    jsonl = tmp_path / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "old turn"}}])
    snap = br.capture_session_snapshot(sid, projects_dir=tmp_path)
    assert snap is not None
    _append_jsonl(
        jsonl,
        [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "user typed something"}],
                },
            }
        ],
    )
    report = br.assess_session_activity(snap, "[bridge resume] job=t3")
    assert report.safe_to_inject is False
    assert report.reason == "foreign_user_activity"
    assert report.delta_contains_foreign_user is True
    assert report.delta_contains_sentinel is False


def test_assess_session_activity_already_injected_blocks(tmp_path: Path) -> None:
    sid = "sess_dup"
    jsonl = tmp_path / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "old"}}])
    snap = br.capture_session_snapshot(sid, projects_dir=tmp_path)
    assert snap is not None
    sentinel = "[bridge resume] job=t4"
    _append_jsonl(
        jsonl,
        [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{sentinel} BRIDGE RESUME body...",
                        }
                    ],
                },
            }
        ],
    )
    report = br.assess_session_activity(snap, sentinel)
    assert report.safe_to_inject is False
    assert report.reason == "already_injected"
    assert report.delta_contains_sentinel is True


def test_assess_session_activity_handles_tool_result_user_rows(tmp_path: Path) -> None:
    """tool_result blocks are still 'user' type rows in claude code's jsonl;
    they should classify as foreign-user activity (the user-channel side
    of a tool interaction is not the agent voluntarily continuing)."""
    sid = "sess_tool"
    jsonl = tmp_path / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "assistant", "message": {"content": "x"}}])
    snap = br.capture_session_snapshot(sid, projects_dir=tmp_path)
    assert snap is not None
    _append_jsonl(
        jsonl,
        [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "content": [
                                {"type": "text", "text": "ls output here"}
                            ],
                        }
                    ],
                },
            }
        ],
    )
    report = br.assess_session_activity(snap, "[bridge resume] job=tt")
    assert report.safe_to_inject is False
    assert report.reason == "foreign_user_activity"


# ----------------------------------------------------------------------
# emit_trigger snapshot wiring (1.1.0)
# ----------------------------------------------------------------------
def test_emit_trigger_includes_schema_version_and_snapshot(tmp_path: Path) -> None:
    sid = "sess_emit"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    jsonl = projects_dir / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "boot"}}])
    target = br.ResumeTarget(
        target_app="Claude", switch_tab=3, session_id=sid
    )
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
        projects_dir=projects_dir,
    )
    job = br.ResumeJob(job_id="snap_job", summary_lines=["x"])
    path = manager.emit_trigger(job)
    assert path is not None
    payload = json.loads(path.read_text())
    resume = payload["_resume"]
    assert resume["schema_version"] == br.RESUME_SCHEMA_VERSION
    snap = resume["dispatch_snapshot"]
    assert snap is not None
    assert snap["session_id"] == sid
    assert snap["jsonl_path"] == str(jsonl)
    assert snap["jsonl_byte_size"] == jsonl.stat().st_size


def test_emit_trigger_snapshot_is_none_when_session_unknown(tmp_path: Path) -> None:
    target = br.ResumeTarget(
        target_app="Claude", switch_tab=3, session_id=None
    )
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
        projects_dir=tmp_path / "no_projects",
    )
    job = br.ResumeJob(job_id="no_snap_job", summary_lines=["x"])
    path = manager.emit_trigger(job)
    assert path is not None
    payload = json.loads(path.read_text())
    assert payload["_resume"]["dispatch_snapshot"] is None


# ----------------------------------------------------------------------
# bucket_for_event + job_states + status projection (1.1.0)
# ----------------------------------------------------------------------
def test_bucket_for_event_known_and_unknown() -> None:
    assert br.bucket_for_event("trigger_written") == "pending"
    assert br.bucket_for_event("inject_ok") == "succeeded"
    assert br.bucket_for_event("inject_failed") == "failed"
    assert br.bucket_for_event("skipped_dup") == "deduped"
    assert br.bucket_for_event("skipped_already_injected") == "blocked_already_injected"
    assert br.bucket_for_event("skipped_not_idle") == "blocked_not_idle"
    assert br.bucket_for_event("future_event_xyz") == "unknown"
    assert br.bucket_for_event(None) == "unknown"


def test_job_states_collapses_history_correctly(tmp_path: Path) -> None:
    target = br.ResumeTarget(target_app="Claude", switch_tab=3)
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
    )
    # Job A: clean success path
    manager.append_ledger("trigger_written", "job_a", path="x")
    manager.append_ledger("inject_ok", "job_a", duration_ms=10)
    # Job B: blocked because user typed
    manager.append_ledger("trigger_written", "job_b", path="x")
    manager.append_ledger(
        "skipped_not_idle", "job_b", error="foreign user"
    )
    # Job C: still pending
    manager.append_ledger("trigger_written", "job_c", path="x")

    states = manager.job_states()
    assert set(states.keys()) == {"job_a", "job_b", "job_c"}
    assert states["job_a"]["current_state"] == "inject_ok"
    assert states["job_b"]["current_state"] == "skipped_not_idle"
    assert states["job_c"]["current_state"] == "trigger_written"
    # Each rolled-up record carries first_seen, last_seen, and the full
    # event sequence in order. (Newest-first key ordering is contractual
    # only when timestamps differ; same-second appends in tests tie and
    # fall back to insertion order via stable sort, which is fine.)
    assert [e["event"] for e in states["job_a"]["events"]] == [
        "trigger_written",
        "inject_ok",
    ]
    assert [e["event"] for e in states["job_b"]["events"]] == [
        "trigger_written",
        "skipped_not_idle",
    ]
    assert [e["event"] for e in states["job_c"]["events"]] == [
        "trigger_written",
    ]
    assert states["job_a"]["latest_details"].get("duration_ms") == 10
    assert states["job_b"]["latest_details"].get("error") == "foreign user"


def test_bucket_jobs_partitions_by_terminal_state(tmp_path: Path) -> None:
    target = br.ResumeTarget(target_app="Claude", switch_tab=3)
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
    )
    manager.append_ledger("trigger_written", "j_pend", path="x")
    manager.append_ledger("trigger_written", "j_ok", path="x")
    manager.append_ledger("inject_ok", "j_ok", duration_ms=1)
    manager.append_ledger("trigger_written", "j_fail", path="x")
    manager.append_ledger("inject_failed", "j_fail", error="boom")
    manager.append_ledger("trigger_written", "j_blocked", path="x")
    manager.append_ledger(
        "skipped_already_injected", "j_blocked", error="dup sentinel"
    )

    from tools.meta.bridge.bridge_resume import _bucket_jobs

    buckets = _bucket_jobs(manager.job_states())
    assert [r["job_id"] for r in buckets["pending"]] == ["j_pend"]
    assert [r["job_id"] for r in buckets["succeeded"]] == ["j_ok"]
    assert [r["job_id"] for r in buckets["failed"]] == ["j_fail"]
    assert [r["job_id"] for r in buckets["blocked_already_injected"]] == [
        "j_blocked"
    ]


def test_cmd_status_includes_provider_pressure_summary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(br, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(br, "DEFAULT_INBOX_DIR", tmp_path / "inbox")
    monkeypatch.setattr(br, "DEFAULT_LEDGER_PATH", tmp_path / "ledger.jsonl")

    manager = br.BridgeResumeManager(
        br.ResumeTarget(target_app="Claude", switch_tab=3),
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
    )
    manager.append_ledger("trigger_written", "job_pending", path="x")

    claim = pressure.acquire_provider_claim(
        tmp_path,
        provider="chatgpt",
        source="bridge_resume_test",
        wait_timeout_s=0,
        ttl_seconds=300,
    )
    assert claim["ok"] is True

    output = StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    rc = br._cmd_status(SimpleNamespace(human=False, recent=5))
    assert rc == 0

    payload = json.loads(output.getvalue())
    assert payload["provider_pressure"]["active_claims"] == 1
    assert payload["provider_pressure"]["blocked"][0]["provider"] == "chatgpt"
    assert "concurrency cap reached" in str(
        payload["provider_pressure"]["blocked"][0]["reason"] or ""
    )


# ----------------------------------------------------------------------
# stale-pending detection (provider receipt reliability)
# ----------------------------------------------------------------------
def _write_ledger_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_annotate_pending_with_age_marks_stale_and_active(tmp_path: Path) -> None:
    now = datetime(2026, 5, 8, 22, 0, 0, tzinfo=timezone.utc)
    fresh_ts = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale_ts = (now - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")
    junk_ts = "not-an-iso-timestamp"

    rows = [
        {"job_id": "fresh", "current_state": "trigger_written",
         "first_seen": fresh_ts, "last_seen": fresh_ts},
        {"job_id": "stale", "current_state": "trigger_written",
         "first_seen": stale_ts, "last_seen": stale_ts},
        {"job_id": "unparseable", "current_state": "trigger_written",
         "first_seen": junk_ts, "last_seen": junk_ts},
    ]
    annotated = br._annotate_pending_with_age(
        rows, now=now, stale_threshold_hours=6.0
    )
    by_id = {r["job_id"]: r for r in annotated}

    assert by_id["fresh"]["is_stale"] is False
    assert by_id["fresh"]["age_hours"] is not None
    assert 0.2 <= by_id["fresh"]["age_hours"] <= 0.3

    assert by_id["stale"]["is_stale"] is True
    assert by_id["stale"]["age_hours"] is not None
    assert by_id["stale"]["age_hours"] >= 24.0

    # Unparseable timestamp must degrade to age_hours=None / is_stale=None,
    # not raise. Operator still sees the row in the active cohort instead
    # of a silent quarantine.
    assert by_id["unparseable"]["is_stale"] is None
    assert by_id["unparseable"]["age_hours"] is None

    active, stale = br._partition_stale_pending(annotated)
    assert {r["job_id"] for r in stale} == {"stale"}
    assert {r["job_id"] for r in active} == {"fresh", "unparseable"}


def test_cmd_status_splits_pending_by_staleness(tmp_path: Path, monkeypatch) -> None:
    """Stale (abandoned) trigger writes must surface as a distinct cohort.

    The detached resume-protocol failure mode this guards: a `trigger_written`
    ledger row from days/weeks ago whose injector daemon never picked it up
    (provider paused, target session gone, machine asleep). Without the
    split it inflates the live `pending` count and the operator can't see
    which jobs are actually waiting on a near-term idle window.
    """
    monkeypatch.setattr(br, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(br, "DEFAULT_INBOX_DIR", tmp_path / "inbox")
    monkeypatch.setattr(br, "DEFAULT_LEDGER_PATH", tmp_path / "ledger.jsonl")

    now = datetime.now(timezone.utc)
    fresh_ts = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale_ts = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _write_ledger_rows(
        tmp_path / "ledger.jsonl",
        [
            {"ts": fresh_ts, "event": "trigger_written",
             "job_id": "job_fresh", "details": {"path": "x"}},
            {"ts": stale_ts, "event": "trigger_written",
             "job_id": "job_stale", "details": {"path": "x"}},
        ],
    )

    output = StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    rc = br._cmd_status(
        SimpleNamespace(human=False, recent=10, stale_pending_hours=6.0)
    )
    assert rc == 0

    payload = json.loads(output.getvalue())
    counts = payload["counts"]
    assert counts["pending"] == 2
    assert counts["pending_active"] == 1
    assert counts["pending_stale"] == 1
    assert payload["stale_pending_threshold_hours"] == 6.0
    assert payload["evaluated_at"]  # non-empty ISO timestamp

    stale_ids = [r["job_id"] for r in payload["recent_pending_stale"]]
    active_ids = [r["job_id"] for r in payload["recent_pending_active"]]
    assert stale_ids == ["job_stale"]
    assert active_ids == ["job_fresh"]

    stale_rec = payload["recent_pending_stale"][0]
    assert stale_rec["is_stale"] is True
    assert stale_rec["age_hours"] >= 24.0
    fresh_rec = payload["recent_pending_active"][0]
    assert fresh_rec["is_stale"] is False
    assert fresh_rec["age_hours"] is not None
    assert fresh_rec["age_hours"] < 1.0

    # `recent_pending` keeps every annotated pending row for backwards-compat
    # consumers that haven't moved to the split fields yet.
    assert {r["job_id"] for r in payload["recent_pending"]} == {
        "job_fresh", "job_stale"
    }


def test_cmd_status_human_surfaces_stale_pending_section(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(br, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(br, "DEFAULT_INBOX_DIR", tmp_path / "inbox")
    monkeypatch.setattr(br, "DEFAULT_LEDGER_PATH", tmp_path / "ledger.jsonl")

    now = datetime.now(timezone.utc)
    stale_ts = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_ledger_rows(
        tmp_path / "ledger.jsonl",
        [
            {"ts": stale_ts, "event": "trigger_written",
             "job_id": "job_old", "details": {"path": "x"}},
        ],
    )

    output = StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    rc = br._cmd_status(
        SimpleNamespace(human=True, recent=5, stale_pending_hours=6.0)
    )
    assert rc == 0

    text = output.getvalue()
    assert "stale_pending_after: 6.00h" in text
    assert "pending_stale" in text
    assert "recent pending (stale" in text
    assert "job_old" in text


def test_cmd_status_default_threshold_when_arg_missing(
    tmp_path: Path, monkeypatch
) -> None:
    """Older callers that built SimpleNamespace without `stale_pending_hours`
    must keep working — the default threshold is applied via getattr."""
    monkeypatch.setattr(br, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(br, "DEFAULT_INBOX_DIR", tmp_path / "inbox")
    monkeypatch.setattr(br, "DEFAULT_LEDGER_PATH", tmp_path / "ledger.jsonl")

    now = datetime.now(timezone.utc)
    fresh_ts = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_ledger_rows(
        tmp_path / "ledger.jsonl",
        [
            {"ts": fresh_ts, "event": "trigger_written",
             "job_id": "job_only", "details": {"path": "x"}},
        ],
    )

    output = StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    rc = br._cmd_status(SimpleNamespace(human=False, recent=5))
    assert rc == 0

    payload = json.loads(output.getvalue())
    assert payload["stale_pending_threshold_hours"] == br.DEFAULT_STALE_PENDING_THRESHOLD_HOURS
    assert payload["counts"]["pending_active"] == 1
    assert payload["counts"]["pending_stale"] == 0


# ----------------------------------------------------------------------
# once-only delivery: emit + a synthetic "already_injected" detection
# ----------------------------------------------------------------------
def test_once_only_resists_duplicate_emit_and_replay_inject(tmp_path: Path) -> None:
    """Once-only safety has TWO layers:
       1. emit_trigger dedupes by job_id (existing test); the SECOND emit is
          a no-op so a buggy retry loop can't double-write the inbox.
       2. The daemon's idle-check rejects already-injected sentinels in the
          jsonl. We simulate that by capturing a snapshot, appending the
          sentinel ourselves, and asserting assess_session_activity blocks.
    """
    sid = "sess_once"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    jsonl = projects_dir / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "assistant", "message": {"content": "boot"}}])

    target = br.ResumeTarget(
        target_app="Claude", switch_tab=3, session_id=sid
    )
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
        projects_dir=projects_dir,
    )
    job = br.ResumeJob(job_id="once_job", summary_lines=["one"])
    p1 = manager.emit_trigger(job)
    p2 = manager.emit_trigger(job)
    assert p1 is not None
    assert p2 is None  # idempotent

    # Now imagine a race: the daemon already pasted, the sentinel has
    # appeared in the jsonl, and an out-of-band trigger is fired again
    # via allow_dup. The daemon's idle-check should reject the replay.
    sentinel = f"{target.sentinel_prefix} job={job.job_id}"
    snap = br.capture_session_snapshot(sid, projects_dir=projects_dir)
    assert snap is not None
    _append_jsonl(
        jsonl,
        [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{sentinel} dup body"}
                    ],
                },
            }
        ],
    )
    report = br.assess_session_activity(snap, sentinel)
    assert report.safe_to_inject is False
    assert report.reason == "already_injected"


# ----------------------------------------------------------------------
# session identity heartbeat (transport extras.active_session)
# ----------------------------------------------------------------------
def test_stamp_active_session_creates_transport_when_missing(tmp_path: Path) -> None:
    """When no transport exists, stamp_active_session synthesizes a minimal
    notification_only record and writes extras.active_session in one shot.
    This is the happy path for a session hook firing before any watcher has
    ever touched the transport (fresh repo, dry run)."""
    from tools.meta.bridge.session_transport import (
        stamp_active_session,
        read_transport,
    )
    transport_path = tmp_path / "claude_session_transport.json"
    assert not transport_path.exists()

    rec = stamp_active_session(
        session_id="sess_fresh",
        transcript_path="/tmp/sessions/sess_fresh.jsonl",
        event="session-start",
        cwd="/Users/example/repo",
        path=transport_path,
    )
    assert rec is not None
    assert transport_path.exists()

    on_disk = read_transport(path=transport_path)
    assert on_disk is not None
    active = on_disk["extras"]["active_session"]
    assert active["session_id"] == "sess_fresh"
    assert active["transcript_path"] == "/tmp/sessions/sess_fresh.jsonl"
    assert active["cwd"] == "/Users/example/repo"
    assert active["last_event"] == "session-start"
    assert "last_seen_at" in active
    assert active["first_seen_at"] == active["last_seen_at"]
    # Synthetic record is notification_only so downstream readers see
    # a valid launch_mode even on a cold start.
    assert on_disk["launch_mode"] == "notification_only"


def test_stamp_active_session_merges_into_existing_transport(tmp_path: Path) -> None:
    """A watcher-written transport record must survive identity stamping:
    top-level fields stay intact, existing extras keys are preserved, and
    only extras.active_session is mutated. This protects the rehydration
    contract when a hook fires after a real launch."""
    from tools.meta.bridge.session_transport import (
        make_record,
        write_transport,
        stamp_active_session,
        read_transport,
    )
    transport_path = tmp_path / "claude_session_transport.json"
    base = make_record(
        launch_mode="terminal_claude",
        launched_by="pipeline_signal_watcher",
        resume_artifact_path="rel/pipeline_resume.json",
        signal_kind="attention_needed",
        summary="review pending",
        extras={"other_key": {"keep": True}},
    )
    write_transport(base, path=transport_path)

    rec = stamp_active_session(
        session_id="sess_merge",
        transcript_path="/tmp/sess_merge.jsonl",
        event="user-prompt",
        cwd=None,
        path=transport_path,
    )
    assert rec is not None

    on_disk = read_transport(path=transport_path)
    assert on_disk is not None
    # Top-level fields from the watcher must survive.
    assert on_disk["launch_mode"] == "terminal_claude"
    assert on_disk["launched_by"] == "pipeline_signal_watcher"
    assert on_disk["signal_kind"] == "attention_needed"
    assert on_disk["resume_artifact_path"] == "rel/pipeline_resume.json"
    # Pre-existing extras block must survive.
    assert on_disk["extras"]["other_key"] == {"keep": True}
    # New active_session block must be present.
    active = on_disk["extras"]["active_session"]
    assert active["session_id"] == "sess_merge"
    assert active["transcript_path"] == "/tmp/sess_merge.jsonl"
    assert active["last_event"] == "user-prompt"
    # user-prompt should not set first_seen_at / last_stop_at / last_session_end_at
    assert "first_seen_at" not in active
    assert "last_stop_at" not in active
    assert "last_session_end_at" not in active


def test_stamp_active_session_records_event_markers(tmp_path: Path) -> None:
    """session-start → first_seen_at, stop → last_stop_at, session-end →
    last_session_end_at. These timestamps let status tooling answer
    'when did this session last quiet down?' without reparsing jsonl."""
    from tools.meta.bridge.session_transport import (
        stamp_active_session,
        read_transport,
    )
    transport_path = tmp_path / "claude_session_transport.json"
    stamp_active_session(
        session_id="sess_life",
        transcript_path=None,
        event="session-start",
        path=transport_path,
    )
    stamp_active_session(
        session_id="sess_life",
        transcript_path=None,
        event="stop",
        path=transport_path,
    )
    stamp_active_session(
        session_id="sess_life",
        transcript_path=None,
        event="session-end",
        path=transport_path,
    )
    rec = read_transport(path=transport_path)
    assert rec is not None
    active = rec["extras"]["active_session"]
    assert "first_seen_at" in active
    assert "last_stop_at" in active
    assert "last_session_end_at" in active
    assert active["last_event"] == "session-end"


# ----------------------------------------------------------------------
# discover_current_session_id three-tier resolution
# ----------------------------------------------------------------------
def test_discover_current_session_id_prefers_stamped_identity(tmp_path: Path) -> None:
    """If the active-session file has a valid extras.active_session.session_id
    AND the referenced jsonl still exists, discover_current_session_id must
    return it — bypassing the mtime-based guess entirely. This is the whole
    point of the hook-stamped heartbeat. Both the one-shot transport and the
    long-lived active-session file must be sandboxed to tmp_path here —
    otherwise the real production ACTIVE_SESSION_PATH leaks into the test."""
    from tools.meta.bridge.session_transport import (
        stamp_active_session,
    )
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    # Two candidate jsonl files. The 'newer' one would win the mtime guess,
    # but the stamped one should take priority even though it's older.
    stamped_sid = "sess_stamped"
    stamped_jsonl = projects_dir / f"{stamped_sid}.jsonl"
    _write_jsonl(stamped_jsonl, [{"type": "user", "message": {"content": "a"}}])
    newer_sid = "sess_newer_mtime"
    newer_jsonl = projects_dir / f"{newer_sid}.jsonl"
    _write_jsonl(newer_jsonl, [{"type": "user", "message": {"content": "b"}}])
    # Force newer_jsonl mtime to be later.
    import os, time
    old_time = time.time() - 60
    os.utime(stamped_jsonl, (old_time, old_time))

    transport_path = tmp_path / "claude_session_transport.json"
    active_session_path = tmp_path / "claude_active_session.json"
    stamp_active_session(
        session_id=stamped_sid,
        transcript_path=str(stamped_jsonl),
        event="user-prompt",
        path=active_session_path,
    )

    sid = br.discover_current_session_id(
        projects_dir=projects_dir,
        transport_path=transport_path,
        active_session_path=active_session_path,
    )
    assert sid == stamped_sid


def test_discover_current_session_id_falls_back_when_stamp_stale(tmp_path: Path) -> None:
    """If the stamped session_id points at a jsonl that no longer exists
    (rotation, manual cleanup), discover_current_session_id must NOT return
    the stale id. It should fall back to the mtime-based guess so the
    daemon still finds a live session instead of silently doing nothing.
    Both transport and active-session paths must be sandboxed to tmp_path —
    see the sibling test for why."""
    from tools.meta.bridge.session_transport import (
        stamp_active_session,
    )
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    live_sid = "sess_live"
    live_jsonl = projects_dir / f"{live_sid}.jsonl"
    _write_jsonl(live_jsonl, [{"type": "user", "message": {"content": "alive"}}])

    transport_path = tmp_path / "claude_session_transport.json"
    active_session_path = tmp_path / "claude_active_session.json"
    stamp_active_session(
        session_id="sess_ghost",
        transcript_path=str(projects_dir / "sess_ghost.jsonl"),
        event="user-prompt",
        path=active_session_path,
    )
    # sess_ghost.jsonl does not exist → stamped identity is stale.

    sid = br.discover_current_session_id(
        projects_dir=projects_dir,
        transport_path=transport_path,
        active_session_path=active_session_path,
    )
    # Must fall back to the one that does exist.
    assert sid == live_sid


# ----------------------------------------------------------------------
# bridge_dispatch_and_yield canonical op
# ----------------------------------------------------------------------
def test_bridge_dispatch_and_yield_happy_path(tmp_path: Path) -> None:
    """
    [ACTION]
    - Teleology: Prove the canonical dispatch-and-yield operation records the happy-path ledger transitions and emits a resume trigger after a successful bridge driver call.
    - Mechanism: Set up a temp-path manager and session snapshot, run `bridge_dispatch_and_yield()` with a fake driver, then assert the result object, trigger artifact, driver context, and ledger event sequence.
    - Reads: `tools.meta.bridge.bridge_resume.bridge_dispatch_and_yield` plus temp-path inbox/ledger/session files.
    - Writes: Temporary trigger JSON, ledger rows, and session transcript files under `tmp_path`.
    - Guarantee: Confirms the successful state sequence `dispatch_scheduled -> dispatch_completed -> trigger_written`.
    - Fails: Assertion failure when happy-path dispatch bookkeeping or trigger emission drifts.
    - When-needed: Open when debugging why successful bridge dispatches are not yielding a resume trigger or are recording the wrong ledger progression.
    - Escalates-to: tools/meta/bridge/bridge_resume.py::bridge_dispatch_and_yield; tools/meta/bridge/claude_app_injector.py
    - Navigation-group: server_backend
    """
    sid = "sess_dy_ok"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    jsonl = projects_dir / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "boot"}}])

    target = br.ResumeTarget(
        target_app="Claude", switch_tab=3, session_id=sid
    )
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
        projects_dir=projects_dir,
    )

    driver_calls: list[tuple[str, dict]] = []

    def fake_driver(job: br.ResumeJob, ctx: dict) -> dict:
        driver_calls.append((job.job_id, ctx))
        return {
            "status": "ok",
            "summary_lines": [
                "bridge: provider=fake attempted=1 written=1 failed=0"
            ],
            "artifacts": ["dumps/fake/probe_a.md"],
        }

    result = br.bridge_dispatch_and_yield(
        job_id="dy_ok_1",
        plan_id="fake_plan",
        group_label="probe_a",
        bridge_driver=fake_driver,
        driver_context={"payload": "hello"},
        continue_instruction="Reply RESUME_LOOP_CLOSED=dy_ok_1 and stop.",
        target=target,
        manager=manager,
    )

    assert isinstance(result, br.DispatchAndYieldResult)
    assert result.job_id == "dy_ok_1"
    assert result.ok is True
    assert result.trigger_path is not None
    assert Path(result.trigger_path).exists()
    assert result.error is None
    assert driver_calls == [("dy_ok_1", {"payload": "hello"})]

    events = [r["event"] for r in manager.ledger_rows(job_id="dy_ok_1")]
    assert events == ["dispatch_scheduled", "dispatch_completed", "trigger_written"]


def test_bridge_dispatch_and_yield_driver_failure_writes_dispatch_failed(
    tmp_path: Path,
) -> None:
    """If the driver raises, the op must record dispatch_failed, NOT emit
    a resume trigger, and return ok=False with the error captured. This is
    the contract that prevents a flaky bridge call from silently yielding
    with no follow-up."""
    sid = "sess_dy_fail"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    jsonl = projects_dir / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "boot"}}])

    target = br.ResumeTarget(
        target_app="Claude", switch_tab=3, session_id=sid
    )
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
        projects_dir=projects_dir,
    )

    def flaky_driver(job: br.ResumeJob, ctx: dict) -> dict:
        raise RuntimeError("CDP socket gone")

    result = br.bridge_dispatch_and_yield(
        job_id="dy_fail_1",
        plan_id="fake_plan",
        group_label="probe_a",
        bridge_driver=flaky_driver,
        driver_context={},
        continue_instruction="noop",
        target=target,
        manager=manager,
    )

    assert result.ok is False
    assert result.trigger_path is None
    assert result.error is not None
    assert "CDP socket gone" in result.error

    events = [r["event"] for r in manager.ledger_rows(job_id="dy_fail_1")]
    assert events == ["dispatch_scheduled", "dispatch_failed"]
    # Inbox must NOT have a trigger file — the driver failed before emit.
    inbox_files = list((tmp_path / "inbox").glob("*.json"))
    assert inbox_files == []


def test_bridge_dispatch_and_yield_custom_extractors(tmp_path: Path) -> None:
    """The caller can plug custom extractor callables to shape the resume
    message from arbitrary driver-output shapes. This lets the canonical
    op stay provider-agnostic: the observe runner, a concept-factory call,
    or an apply-plan post-run can each map its own output into the packet
    without forking the op."""
    sid = "sess_dy_custom"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    jsonl = projects_dir / f"{sid}.jsonl"
    _write_jsonl(jsonl, [{"type": "user", "message": {"content": "boot"}}])

    target = br.ResumeTarget(
        target_app="Claude", switch_tab=3, session_id=sid
    )
    manager = br.BridgeResumeManager(
        target,
        inbox_dir=tmp_path / "inbox",
        ledger_path=tmp_path / "ledger.jsonl",
        projects_dir=projects_dir,
    )

    def custom_driver(job: br.ResumeJob, ctx: dict) -> dict:
        return {
            "outcome_code": "DEGRADED",
            "lines": ["groups: 3", "- a: ok", "- b: ok", "- c: warn"],
            "files": ["dumps/custom/session.md"],
            "raw": {"warn_count": 1},
        }

    result = br.bridge_dispatch_and_yield(
        job_id="dy_custom_1",
        plan_id="custom_plan",
        group_label="group_x",
        bridge_driver=custom_driver,
        driver_context={},
        status_from_outcome=lambda o: "warn" if o.get("outcome_code") == "DEGRADED" else "ok",
        summary_from_outcome=lambda o: list(o.get("lines", [])),
        artifacts_from_outcome=lambda o: list(o.get("files", [])),
        continue_instruction="inspect warnings",
        target=target,
        manager=manager,
    )

    assert result.ok is True
    assert result.trigger_path is not None
    payload = json.loads(Path(result.trigger_path).read_text())
    body = payload["text"]
    assert "status=warn" in body
    assert "- groups: 3" in body
    assert "- dumps/custom/session.md" in body


# ----------------------------------------------------------------------
# freeze guard: injector must not statically import bridge_resume
# ----------------------------------------------------------------------
def test_injector_has_no_toplevel_bridge_resume_import() -> None:
    """AST-level freeze guard. claude_app_injector is the transport adapter;
    it must not depend on bridge_resume at import time so the control-plane
    vs transport boundary stays enforced. Lazy imports inside functions
    are allowed (and used for ResumeJob synthesis), but the module body
    itself must be clean. A regression on this rule is how we previously
    let the injector ooze into doing protocol work."""
    import ast
    injector_path = (
        Path(__file__).resolve().parents[3]
        / "tools/meta/bridge/claude_app_injector.py"
    )
    assert injector_path.exists(), f"missing: {injector_path}"
    tree = ast.parse(injector_path.read_text(encoding="utf-8"))

    offenders: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            # `import tools.meta.bridge.bridge_resume [as _br]`
            for alias in node.names:
                if "bridge_resume" in alias.name:
                    offenders.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            # `from tools.meta.bridge.bridge_resume import ...` — caught by
            # the module substring check.
            mod = node.module or ""
            if "bridge_resume" in mod:
                offenders.append(
                    f"from {mod} import "
                    + ", ".join(a.name for a in node.names)
                )
                continue
            # `from tools.meta.bridge import bridge_resume [as _br]` — the
            # module is 'tools.meta.bridge', so we also have to look at the
            # imported names on the node. This is the shape the freeze rule
            # most commonly regresses into.
            for alias in node.names:
                if "bridge_resume" in alias.name:
                    offenders.append(
                        f"from {mod} import {alias.name}"
                        + (f" as {alias.asname}" if alias.asname else "")
                    )
    assert offenders == [], (
        "claude_app_injector has module-level bridge_resume imports. "
        "Move them inside functions or remove them entirely. Offenders: "
        f"{offenders}"
    )
