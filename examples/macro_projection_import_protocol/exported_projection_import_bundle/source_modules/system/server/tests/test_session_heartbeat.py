"""Tests for system.lib.session_heartbeat."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from system.lib import session_heartbeat


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _iso(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_snapshot_reports_live_when_claude_heartbeat_is_fresh(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    recent = now - timedelta(seconds=5)

    _write(
        tmp_path / "tools/meta/bridge/claude_active_session.json",
        {
            "extras": {
                "active_session": {
                    "session_id": "abc-live",
                    "transcript_path": "/tmp/live.jsonl",
                    "cwd": "/tmp",
                    "last_event": "user-prompt",
                    "last_seen_at": _iso(recent),
                    "first_seen_at": _iso(recent - timedelta(minutes=10)),
                }
            }
        },
    )
    _write(
        tmp_path / "tools/meta/bridge/claude_session_transport.json",
        {"generated_at": _iso(recent), "launch_mode": "terminal_claude"},
    )
    _write(
        tmp_path / "tools/meta/bridge/codex_session_transport.json",
        {"created_at": _iso(now - timedelta(hours=3)), "status": "failed"},
    )

    snap = session_heartbeat.snapshot(tmp_path)
    assert snap["any_alive"] is True
    assert snap["most_recent_actor"] == "claude_code"
    assert snap["claude_code"]["tone"] == "live"
    assert snap["claude_code"]["session_id"] == "abc-live"
    assert snap["claude_code"]["last_event"] == "user-prompt"
    assert snap["codex"]["tone"] == "cold"


def test_snapshot_reports_cold_when_nothing_stamped_recently(tmp_path: Path) -> None:
    ancient = datetime.now(timezone.utc) - timedelta(days=10)
    _write(
        tmp_path / "tools/meta/bridge/claude_active_session.json",
        {
            "extras": {
                "active_session": {
                    "session_id": "abc-old",
                    "last_event": "stop",
                    "last_seen_at": _iso(ancient),
                }
            }
        },
    )
    _write(
        tmp_path / "tools/meta/bridge/claude_session_transport.json",
        {"generated_at": _iso(ancient)},
    )
    _write(
        tmp_path / "tools/meta/bridge/codex_session_transport.json",
        {"created_at": _iso(ancient), "consumed_at": _iso(ancient)},
    )

    snap = session_heartbeat.snapshot(tmp_path)
    assert snap["any_alive"] is False
    assert snap["claude_code"]["tone"] == "cold"
    assert snap["codex"]["tone"] == "consumed"


def test_snapshot_handles_missing_files_without_raising(tmp_path: Path) -> None:
    snap = session_heartbeat.snapshot(tmp_path)
    assert snap["any_alive"] is False
    assert snap["claude_code"]["transport_exists"] is False
    assert snap["claude_code"]["active_session_exists"] is False
    assert snap["codex"]["transport_exists"] is False
    assert snap["claude_code"]["tone"] == "unknown"
    assert snap["codex"]["tone"] == "unknown"


def test_write_snapshot_respects_run_id_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIWF_META_MISSION_RUN_ID", "run-abc")
    output = session_heartbeat.write_snapshot(tmp_path)
    assert output.as_posix().endswith(
        "state/meta_missions/session_heartbeat_watch/runs/run-abc/outputs/heartbeat.json"
    )
    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["mission_id"] == "session_heartbeat_watch"


def test_write_snapshot_falls_back_to_latest_when_no_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIWF_META_MISSION_RUN_ID", raising=False)
    output = session_heartbeat.write_snapshot(tmp_path)
    assert output.as_posix().endswith(
        "state/meta_missions/session_heartbeat_watch/latest_heartbeat.json"
    )
    assert output.exists()


def test_main_snapshot_prints_path_and_writes_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIWF_META_MISSION_RUN_ID", raising=False)
    rc = session_heartbeat.main(["snapshot", "--repo-root", str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr().out.strip()
    assert captured
    written = Path(captured)
    assert written.exists()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["mission_id"] == "session_heartbeat_watch"
