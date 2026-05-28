from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from system.lib import agent_seed_handoffs, shared_worktree_guard, work_admission, work_ledger, work_ledger_runtime
from tools.meta.factory import work_ledger as work_ledger_cli


HOSTILE_BODY = (
    "Closeout payload with backticks: `inline code`\n"
    "Command token: $(echo unsafe)\n"
    "Env tokens: $HOME and ${PATH:-default}\n"
    "Unicode arrow: \u2192\n"
    "JSON braces: {\"body_ingest\": {\"sha256\": \"fake\"}}\n"
    "Fence:\n"
    "```bash\n"
    "echo \"$HOME\"\n"
    "```\n"
)


def _write_json(root: Path, rel_path: str, payload: object) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _seed_phase_family(root: Path) -> tuple[str, str]:
    family_rel = "obsidian/okay lets do this/09 - Live Family"
    phase_rel = f"{family_rel}/09.35 - Phase 09.35 - Live"
    _write_json(
        root,
        f"{family_rel}/phase_family.json",
        {
            "kind": "phase_family",
            "family_id": "09",
            "family_number": "09",
            "family_title": "Live Family",
            "family_dir": family_rel,
            "active_phase_id": "09_35",
            "active_phase_number": "09.35",
            "active_phase_title": "Phase 09.35 - Live",
            "active_phase_dir": phase_rel,
            "active_phase_changed_at": "2026-04-19T00:00:00+00:00",
        },
    )
    return family_rel, phase_rel


def _bootstrap_session(root: Path, session_id: str = "sess_1") -> str:
    payload = work_ledger_runtime.bootstrap_session(
        root,
        session_id=session_id,
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    return str(payload["read_receipt_id"])


def _open_test_thread(root: Path, session_id: str = "sess_1") -> str:
    opened = work_ledger.open_thread(
        root,
        actor="claude_code",
        actor_session_id=session_id,
        phase_id="09_35",
        family_id="09",
        title="Concurrency guard target",
        body="Seed thread for mutation guard tests.",
    )
    return str(opened["event"]["td_id"])


def test_atomic_write_json_uses_unique_temp_paths_for_reentrant_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "codex/ledger/09_52/work_ledger_index.json"
    real_replace = work_ledger.os.replace
    replace_sources: list[str] = []
    reentered = False

    def replace_with_reentrant_write(src: str | bytes, dst: str | bytes) -> None:
        nonlocal reentered
        replace_sources.append(Path(src).name)
        if not reentered:
            reentered = True
            work_ledger.atomic_write_json(target, {"writer": "inner"})
        real_replace(src, dst)

    monkeypatch.setattr(work_ledger.os, "replace", replace_with_reentrant_write)

    work_ledger.atomic_write_json(target, {"writer": "outer"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"writer": "outer"}
    assert len(replace_sources) == 2
    assert len(set(replace_sources)) == 2


def _progress_args(
    *,
    receipt: str,
    td_id: str,
    session_id: str,
    body: str = "progress body",
    metadata_json: str | None = None,
    allow_unclaimed_note: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        actor="claude_code",
        actor_session_id=session_id,
        phase_id="09_35",
        family_id="09",
        read_receipt_id=receipt,
        td_id=td_id,
        title=None,
        body=body,
        body_file=None,
        body_stdin=False,
        evidence_ref=[],
        metadata_json=metadata_json,
        allow_unclaimed_note=allow_unclaimed_note,
    )


def _close_args(
    *,
    receipt: str,
    td_id: str,
    session_id: str,
    body: str = "close body",
    metadata_json: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        actor="claude_code",
        actor_session_id=session_id,
        phase_id="09_35",
        family_id="09",
        read_receipt_id=receipt,
        td_id=td_id,
        title=None,
        body=body,
        body_file=None,
        body_stdin=False,
        evidence_ref=[],
        metadata_json=metadata_json,
        resolution_kind="artifact",
        resolution_ref="test",
        resolution_label=None,
        resolution_metadata_json=None,
    )


def test_body_file_ingest_records_source_and_stored_attestation(tmp_path: Path) -> None:
    body_path = tmp_path / "payload.md"
    raw = HOSTILE_BODY.encode("utf-8")
    body_path.write_bytes(raw)
    args = SimpleNamespace(body=None, body_file=str(body_path), body_stdin=False)

    work_ledger_cli._resolve_body_and_ingest(args)

    stored = HOSTILE_BODY.strip().encode("utf-8")
    ingest = args._body_ingest
    assert args.body == HOSTILE_BODY
    assert ingest["mode"] == "file"
    assert ingest["path"] == str(body_path)
    assert ingest["sha256"] == hashlib.sha256(raw).hexdigest()
    assert ingest["source_sha256"] == ingest["sha256"]
    assert ingest["byte_count"] == len(raw)
    assert ingest["source_byte_count"] == len(raw)
    assert ingest["newline_count"] == HOSTILE_BODY.count("\n")
    assert ingest["source_newline_count"] == HOSTILE_BODY.count("\n")
    assert ingest["stored_sha256"] == hashlib.sha256(stored).hexdigest()
    assert ingest["stored_byte_count"] == len(stored)
    assert ingest["stored_newline_count"] == HOSTILE_BODY.strip().count("\n")
    assert ingest["canonicalization"]["trailing_newline_removed"] is True
    assert ingest["canonicalization"]["leading_trailing_whitespace_stripped"] is True


def test_body_stdin_ingest_records_source_without_path(monkeypatch) -> None:
    raw = HOSTILE_BODY.encode("utf-8")

    class FakeStdin:
        buffer = io.BytesIO(raw)

    monkeypatch.setattr(work_ledger_cli.sys, "stdin", FakeStdin())
    args = SimpleNamespace(body=None, body_file=None, body_stdin=True)

    work_ledger_cli._resolve_body_and_ingest(args)

    ingest = args._body_ingest
    assert args.body == HOSTILE_BODY
    assert "`inline code`" in args.body
    assert "$(echo unsafe)" in args.body
    assert "$HOME" in args.body
    assert "${PATH:-default}" in args.body
    assert "\u2192" in args.body
    assert "{\"body_ingest\": {\"sha256\": \"fake\"}}" in args.body
    assert "```bash" in args.body
    assert ingest["mode"] == "stdin"
    assert "path" not in ingest
    assert ingest["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert ingest["stored_sha256"] == hashlib.sha256(HOSTILE_BODY.strip().encode("utf-8")).hexdigest()


def test_body_ingest_metadata_is_system_owned(tmp_path: Path) -> None:
    body_path = tmp_path / "payload.md"
    body_path.write_text(HOSTILE_BODY, encoding="utf-8")
    args = SimpleNamespace(body=None, body_file=str(body_path), body_stdin=False)
    work_ledger_cli._resolve_body_and_ingest(args)

    clean = work_ledger_cli._metadata_from_args(
        SimpleNamespace(metadata_json='{"operator_field": true}', _body_ingest=args._body_ingest)
    )
    assert clean["operator_field"] is True
    assert clean["body_ingest"]["source_sha256"] == args._body_ingest["source_sha256"]

    with pytest.raises(SystemExit, match="body_ingest is system-owned attestation metadata"):
        work_ledger_cli._metadata_from_args(
            SimpleNamespace(
                metadata_json='{"body_ingest": {"sha256": "fake"}}',
                _body_ingest=args._body_ingest,
            )
        )


def test_existing_thread_mutation_requires_active_td_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_missing_claim"
    receipt = _bootstrap_session(tmp_path, session_id)
    td_id = _open_test_thread(tmp_path, session_id)
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    with pytest.raises(SystemExit) as raised:
        work_ledger_cli.cmd_progress(
            _progress_args(receipt=receipt, td_id=td_id, session_id=session_id)
        )

    payload = json.loads(str(raised.value))
    assert payload["schema"] == "work_ledger_mutation_claim_conflict_v1"
    assert payload["status"] == "blocked"
    assert payload["reason"] == "missing_or_stale_td_id_claim"
    assert payload["td_id"] == td_id
    assert payload["actor_session_id"] == session_id
    assert "session-claim --td-id" in payload["repair_route"]


def test_existing_thread_mutation_with_active_td_claim_records_guard_metadata(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_guard_verified"
    receipt = _bootstrap_session(tmp_path, session_id)
    td_id = _open_test_thread(tmp_path, session_id)
    claim = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id=session_id,
        td_id=td_id,
        lease_minutes=30,
    )
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_progress(
        _progress_args(receipt=receipt, td_id=td_id, session_id=session_id)
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    guard = payload["event"]["metadata"]["mutation_guard"]
    assert guard["schema"] == "work_ledger_mutation_guard_v1"
    assert guard["status"] == "claim_verified"
    assert guard["operation"] == "progress_note"
    assert guard["claim_id"] == claim["claim"]["claim_id"]
    assert guard["claim_scope"] == td_id


def test_existing_thread_mutation_with_expired_claim_fails_with_repair_route(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_expired_claim"
    receipt = _bootstrap_session(tmp_path, session_id)
    td_id = _open_test_thread(tmp_path, session_id)
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id=session_id,
        td_id=td_id,
        lease_minutes=30,
    )
    status_path = tmp_path / work_ledger_runtime.RUNTIME_STATUS_REL
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    status_payload["sessions"][session_id]["claims"][0]["leased_until"] = (
        datetime.now(timezone.utc) - timedelta(minutes=5)
    ).isoformat()
    status_path.write_text(json.dumps(status_payload), encoding="utf-8")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    with pytest.raises(SystemExit) as raised:
        work_ledger_cli.cmd_close(
            _close_args(receipt=receipt, td_id=td_id, session_id=session_id)
        )

    payload = json.loads(str(raised.value))
    assert payload["schema"] == "work_ledger_mutation_claim_conflict_v1"
    assert payload["operation"] == "todo_close"
    assert payload["status"] == "blocked"
    assert "session-claim --td-id" in payload["repair_route"]


def test_close_with_task_ledger_work_item_id_explains_identity_axis_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_cap_close_axis"
    receipt = _bootstrap_session(tmp_path, session_id)
    work_item_id = "cap_quick_self_error_work_ledger_close_used_workit_8d2fb2ecfc6e"
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id=session_id,
        td_id=work_item_id,
        lease_minutes=30,
    )
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    with pytest.raises(SystemExit) as raised:
        work_ledger_cli.cmd_close(
            _close_args(receipt=receipt, td_id=work_item_id, session_id=session_id)
        )

    payload = json.loads(str(raised.value))
    assert payload["schema"] == "work_ledger_mutation_claim_conflict_v1"
    assert payload["operation"] == "todo_close"
    assert payload["status"] == "blocked"
    assert payload["td_id"] == work_item_id
    assert payload["reason"] == "missing_or_stale_td_id_claim"
    assert "Task Ledger WorkItem id" in payload["repair_route"]
    assert "next_close_command" in payload["repair_route"]
    mismatch = payload["identity_axis_mismatch"]
    assert mismatch["schema"] == "work_ledger_identity_axis_mismatch_v1"
    assert mismatch["requested_id"] == work_item_id
    assert mismatch["requested_id_kind"] == "task_ledger_work_item_id"
    assert mismatch["expected_id_kind"] == "work_ledger_td_id"
    assert mismatch["expected_pattern"] == "td_*"
    assert "progress" in mismatch["progress_bridge_command"]
    assert "task_ledger_apply.py" in mismatch["task_ledger_receipt_command"]


def test_explicit_unclaimed_note_bypass_records_warning_guard_metadata(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_unclaimed_note"
    receipt = _bootstrap_session(tmp_path, session_id)
    td_id = _open_test_thread(tmp_path, session_id)
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_progress(
        _progress_args(
            receipt=receipt,
            td_id=td_id,
            session_id=session_id,
            allow_unclaimed_note=True,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    guard = payload["event"]["metadata"]["mutation_guard"]
    assert guard["status"] == "claim_bypassed"
    assert guard["mode"] == "explicit_unclaimed_note"
    assert guard["severity"] == "warning"
    assert guard["operation"] == "progress_note"


def test_mutation_guard_metadata_is_system_owned(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_spoof_guard"
    receipt = _bootstrap_session(tmp_path, session_id)
    td_id = _open_test_thread(tmp_path, session_id)
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id=session_id,
        td_id=td_id,
        lease_minutes=30,
    )
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    with pytest.raises(SystemExit, match="mutation_guard is system-owned concurrency metadata"):
        work_ledger_cli.cmd_progress(
            _progress_args(
                receipt=receipt,
                td_id=td_id,
                session_id=session_id,
                metadata_json='{"mutation_guard": {"status": "fake"}}',
            )
        )


def test_open_close_reduces_to_closed_thread(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    opened = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Tighten ledger core",
        body="Implement the first append-only event row.",
    )
    td_id = str(opened["event"]["td_id"])
    work_ledger.close_thread(
        tmp_path,
        td_id=td_id,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        resolution_episode=work_ledger.build_resolution_episode(
            "artifact",
            "system/lib/work_ledger.py",
        ),
    )

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    thread = projection["threads"][td_id]

    assert thread["status"] == "closed"
    assert projection["counts"]["open_threads"] == 0
    assert projection["counts"]["closed_threads"] == 1
    assert projection["recently_closed"][0]["td_id"] == td_id


def test_open_close_reopen_reactivates_same_thread_id(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    opened = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Reopenable work",
    )
    td_id = str(opened["event"]["td_id"])
    work_ledger.close_thread(
        tmp_path,
        td_id=td_id,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        resolution_episode=work_ledger.build_resolution_episode("session", "sess_1"),
    )
    work_ledger.reopen_thread(
        tmp_path,
        td_id=td_id,
        actor="claude_code",
        actor_session_id="sess_2",
        phase_id="09_35",
        family_id="09",
        body="Closure reversed after new evidence.",
    )

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    thread = projection["threads"][td_id]

    assert thread["status"] == "open"
    assert len(thread["intervals"]) == 2
    assert thread["intervals"][0]["invalid_at"] is not None
    assert thread["intervals"][1]["invalid_at"] is None


def test_supersede_creates_successor_chain(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    opened = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Old scope",
    )
    td_id = str(opened["event"]["td_id"])
    superseded = work_ledger.supersede_thread(
        tmp_path,
        td_id=td_id,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="New scope",
        resolution_episode=work_ledger.build_resolution_episode("git_commit", "abc123"),
    )
    successor_id = str(superseded["successor_td_id"])

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    predecessor = projection["threads"][td_id]
    successor = projection["threads"][successor_id]

    assert predecessor["status"] == "superseded"
    assert predecessor["successor_td_id"] == successor_id
    assert successor["predecessor_td_id"] == td_id
    assert projection["supersession_chains"][0]["chain"][0]["td_id"] == td_id
    assert projection["supersession_chains"][0]["chain"][1]["td_id"] == successor_id


def test_recent_done_and_cross_agent_handoff_are_projected(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    opened = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Shared thread",
    )
    td_id = str(opened["event"]["td_id"])
    work_ledger.progress_thread(
        tmp_path,
        td_id=td_id,
        actor="codex",
        actor_session_id="sess_2",
        phase_id="09_35",
        family_id="09",
        body="Picked up the same work thread from another actor.",
    )
    work_ledger.close_thread(
        tmp_path,
        td_id=td_id,
        actor="codex",
        actor_session_id="sess_2",
        phase_id="09_35",
        family_id="09",
        resolution_episode=work_ledger.build_resolution_episode("artifact", "done.txt"),
    )

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")

    assert projection["recently_closed"][0]["td_id"] == td_id
    assert projection["cross_agent_handoffs"][0]["from_actor"] == "claude_code"
    assert projection["cross_agent_handoffs"][0]["to_actor"] == "codex"


def test_project_check_reports_fresh_and_stale_projection(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Projection check target",
    )
    work_ledger.project_phase(tmp_path, phase_id="09_35", family_id="09")

    fresh = work_ledger.check_project_phase(tmp_path, phase_id="09_35", family_id="09")
    assert fresh["ok"] is True
    assert fresh["mode"] == "check"
    assert fresh["projection_results"][0]["fresh"] is True

    index_path = tmp_path / "codex/ledger/09_35/work_ledger_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["counts"]["open_threads"] = 99
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    stale = work_ledger.check_project_phase(tmp_path, phase_id="09_35", family_id="09")
    assert stale["ok"] is False
    assert stale["projection_results"][0]["fresh"] is False
    assert stale["projection_results"][0]["reason"] == "projection_stale"


def test_project_check_ignores_stale_open_age_seconds(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    old_created_at = "2026-01-01T00:00:00+00:00"
    work_ledger.append_event(
        tmp_path,
        {
            "event_id": work_ledger.mint_event_id(),
            "td_id": work_ledger.mint_td_id(),
            "event_kind": "todo_open",
            "actor": "claude_code",
            "actor_session_id": "sess_1",
            "phase_id": "09_35",
            "family_id": "09",
            "created_at": old_created_at,
            "valid_at": old_created_at,
            "invalid_at": None,
            "expired_at": None,
            "title": "Old open item",
            "body": "Forces stale_open age_seconds into the projection.",
            "evidence_refs": [],
            "metadata": {},
        },
    )

    index_path = tmp_path / "codex/ledger/09_35/work_ledger_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["stale_open"]
    index["stale_open"][0]["age_seconds"] = 1
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    payload = work_ledger.check_project_phase(tmp_path, phase_id="09_35", family_id="09")
    assert payload["ok"] is True
    assert payload["projection_results"][0]["fresh"] is True


def test_project_projection_omits_stale_open_age_seconds(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    old_created_at = "2026-01-01T00:00:00+00:00"
    work_ledger.append_event(
        tmp_path,
        {
            "event_id": work_ledger.mint_event_id(),
            "td_id": work_ledger.mint_td_id(),
            "event_kind": "todo_open",
            "actor": "claude_code",
            "actor_session_id": "sess_1",
            "phase_id": "09_35",
            "family_id": "09",
            "created_at": old_created_at,
            "valid_at": old_created_at,
            "invalid_at": None,
            "expired_at": None,
            "title": "Old open item",
            "body": "Forces stale_open membership without volatile age fields.",
            "evidence_refs": [],
            "metadata": {},
        },
    )

    index_path = tmp_path / "codex/ledger/09_35/work_ledger_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))

    assert index["stale_open"]
    assert "age_seconds" not in index["stale_open"][0]


def test_project_phase_preserves_fresh_projection_generated_at(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Idempotent projection",
    )
    work_ledger.project_phase(tmp_path, phase_id="09_35", family_id="09")

    index_path = tmp_path / "codex/ledger/09_35/work_ledger_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["generated_at"] = "2000-01-01T00:00:00+00:00"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    work_ledger.project_phase(tmp_path, phase_id="09_35", family_id="09")
    reloaded = json.loads(index_path.read_text(encoding="utf-8"))

    assert reloaded["generated_at"] == "2000-01-01T00:00:00+00:00"


def test_write_family_projections_reuses_family_reduction_across_stale_buckets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    buckets = ["09_35", "09_36", "09_37"]
    events = [
        {
            "schema": work_ledger.WORK_LEDGER_SCHEMA,
            "event_id": f"wle_{index:016x}",
            "td_id": f"td_{index:016x}",
            "event_kind": "todo_open",
            "actor": "codex",
            "actor_session_id": "sess_projection",
            "phase_id": phase_id,
            "family_id": "09",
            "created_at": "2026-05-11T00:00:00+00:00",
            "valid_at": "2026-05-11T00:00:00+00:00",
            "title": f"Projection bucket {phase_id}",
        }
        for index, phase_id in enumerate(buckets)
    ]
    for phase_id in buckets:
        paths = work_ledger.ledger_paths(tmp_path, phase_id=phase_id, family_id="09")
        index_path = Path(paths["index_path"])
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            json.dumps(
                {
                    "schema": work_ledger.WORK_LEDGER_INDEX_SCHEMA,
                    "generated_at": "2026-05-10T00:00:00+00:00",
                    "phase_id": phase_id,
                    "family_id": "09",
                    "threads": {},
                    "counts": {"events": 0},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        work_ledger,
        "_family_projection_targets",
        lambda repo_root, family_id, include_phase_id: list(buckets),
    )
    monkeypatch.setattr(
        work_ledger,
        "load_events",
        lambda repo_root, *, family_id=None: list(events),
    )
    original_build_projection = work_ledger.build_projection
    build_calls: list[tuple[str | None, str | None]] = []

    def counting_build_projection(*args, **kwargs):
        build_calls.append((kwargs.get("phase_id"), kwargs.get("generated_at")))
        return original_build_projection(*args, **kwargs)

    monkeypatch.setattr(work_ledger, "build_projection", counting_build_projection)

    result = work_ledger.write_family_projections(
        tmp_path,
        family_id="09",
        include_phase_id="09_35",
    )

    assert [phase_id for phase_id, _generated_at in build_calls] == [None]
    assert len({generated_at for _phase_id, generated_at in build_calls}) == 1
    assert all(row["counts"]["events"] == len(events) for row in result)


def test_mixed_phase_family_projection_paths_are_disambiguated(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    shared_phase = "09_35"
    events = [
        {
            "schema": work_ledger.WORK_LEDGER_SCHEMA,
            "event_id": "wle_primary000000",
            "td_id": "td_primary000000",
            "event_kind": "todo_open",
            "actor": "codex",
            "actor_session_id": "sess_projection",
            "phase_id": shared_phase,
            "family_id": "09",
            "created_at": "2026-05-11T00:00:00+00:00",
            "valid_at": "2026-05-11T00:00:00+00:00",
            "title": "Primary family projection",
        },
        {
            "schema": work_ledger.WORK_LEDGER_SCHEMA,
            "event_id": "wle_secondary000",
            "td_id": "td_secondary000",
            "event_kind": "todo_open",
            "actor": "codex",
            "actor_session_id": "sess_projection",
            "phase_id": shared_phase,
            "family_id": "dissemination",
            "created_at": "2026-05-11T00:01:00+00:00",
            "valid_at": "2026-05-11T00:01:00+00:00",
            "title": "Secondary family projection",
        },
    ]
    for event in events:
        work_ledger.append_event(tmp_path, event, projection_mode="family")

    result = work_ledger.project_all(tmp_path)
    check = work_ledger.check_project_all(tmp_path)
    primary_paths = work_ledger.ledger_paths(tmp_path, phase_id=shared_phase, family_id="09")
    secondary_paths = work_ledger.ledger_paths(
        tmp_path,
        phase_id=shared_phase,
        family_id="dissemination",
    )
    primary_index = Path(primary_paths["index_path"])
    secondary_index = Path(secondary_paths["index_path"])
    primary_payload = json.loads(primary_index.read_text(encoding="utf-8"))
    secondary_payload = json.loads(secondary_index.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert check["ok"] is True
    assert primary_index.name == "work_ledger_index.json"
    assert secondary_index.name == "work_ledger_index.dissemination.json"
    assert primary_payload["family_id"] == "09"
    assert secondary_payload["family_id"] == "dissemination"
    assert primary_payload["counts"]["events"] == 1
    assert secondary_payload["counts"]["events"] == 1


def test_append_open_updates_only_touched_projection_and_defers_siblings(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    buckets = ["09_35", "09_36"]
    for index, phase_id in enumerate(buckets):
        work_ledger.append_event(
            tmp_path,
            {
                "schema": work_ledger.WORK_LEDGER_SCHEMA,
                "event_id": f"wle_baseline{index:010d}",
                "td_id": f"td_baseline{index:010d}",
                "event_kind": "todo_open",
                "actor": "codex",
                "actor_session_id": "sess_projection",
                "phase_id": phase_id,
                "family_id": "09",
                "created_at": f"2026-05-11T00:0{index}:00+00:00",
                "valid_at": f"2026-05-11T00:0{index}:00+00:00",
                "title": f"Baseline bucket {phase_id}",
            },
            projection_mode="family",
        )

    sibling_index = tmp_path / "codex/ledger/09_35/work_ledger_index.json"
    touched_index = tmp_path / "codex/ledger/09_36/work_ledger_index.json"
    sibling_before = sibling_index.read_text(encoding="utf-8")
    touched_before = touched_index.read_text(encoding="utf-8")

    result = work_ledger.open_thread(
        tmp_path,
        actor="codex",
        actor_session_id="sess_projection",
        phase_id="09_36",
        family_id="09",
        title="Tiny append should not fan out",
    )

    assert result["projection_mode"] == "append_event"
    assert [row["phase_id"] for row in result["projection_results"]] == ["09_36"]
    assert result["projection_results"][0]["mode"] == "append_only_incremental"
    assert [row["phase_id"] for row in result["deferred_projection_results"]] == ["09_35"]
    assert sibling_index.read_text(encoding="utf-8") == sibling_before
    assert touched_index.read_text(encoding="utf-8") != touched_before

    touched_projection = work_ledger.load_projection(tmp_path, phase_id="09_36", family_id="09")
    assert touched_projection["counts"]["events"] == 3
    freshness_rows = {
        row["phase_id"]: row
        for row in work_ledger.check_family_projections(
            tmp_path,
            family_id="09",
            include_phase_id="09_36",
        )
    }
    assert freshness_rows["09_36"]["fresh"] is True
    assert freshness_rows["09_35"]["fresh"] is False
    assert freshness_rows["09_35"]["reason"] == "projection_stale"


def test_project_check_summarizes_family_fanout_stale_indexes(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    buckets = ["09_35", "09_36", "09_37"]
    for index, phase_id in enumerate(buckets):
        work_ledger.append_event(
            tmp_path,
            {
                "schema": work_ledger.WORK_LEDGER_SCHEMA,
                "event_id": f"wle_fanout{index:010d}",
                "td_id": f"td_fanout{index:010d}",
                "event_kind": "todo_open",
                "actor": "codex",
                "actor_session_id": "sess_projection",
                "phase_id": phase_id,
                "family_id": "09",
                "created_at": f"2026-05-11T00:0{index}:00+00:00",
                "valid_at": f"2026-05-11T00:0{index}:00+00:00",
                "title": f"Baseline bucket {phase_id}",
            },
            projection_mode="family",
        )

    work_ledger.open_thread(
        tmp_path,
        actor="codex",
        actor_session_id="sess_projection",
        phase_id="09_37",
        family_id="09",
        title="Append that stales sibling projections",
    )

    check = work_ledger.check_project_all(tmp_path)
    diagnostics = check["projection_fanout_diagnostics"]

    assert check["ok"] is False
    assert len(diagnostics) == 1
    assert diagnostics[0]["diagnostic_id"] == "work_ledger_family_projection_fanout"
    assert diagnostics[0]["family_id"] == "09"
    assert diagnostics[0]["stale_projection_count"] == 2
    assert diagnostics[0]["fresh_projection_count"] == 1
    assert diagnostics[0]["stale_phase_ids"] == ["09_35", "09_36"]
    assert diagnostics[0]["stale_index_paths"] == [
        "codex/ledger/09_35/work_ledger_index.json",
        "codex/ledger/09_36/work_ledger_index.json",
    ]
    assert diagnostics[0]["repair_command"] == (
        "./repo-python tools/meta/factory/work_ledger.py project --all"
    )
    assert diagnostics[0]["commit_scope"] == diagnostics[0]["stale_index_paths"]


def test_phase_project_check_passes_when_selected_phase_is_fresh(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    buckets = ["09_35", "09_36", "09_37"]
    for index, phase_id in enumerate(buckets):
        work_ledger.append_event(
            tmp_path,
            {
                "schema": work_ledger.WORK_LEDGER_SCHEMA,
                "event_id": f"wle_phaseok{index:09d}",
                "td_id": f"td_phaseok{index:010d}",
                "event_kind": "todo_open",
                "actor": "codex",
                "actor_session_id": "sess_projection",
                "phase_id": phase_id,
                "family_id": "09",
                "created_at": f"2026-05-11T00:0{index}:00+00:00",
                "valid_at": f"2026-05-11T00:0{index}:00+00:00",
                "title": f"Baseline bucket {phase_id}",
            },
            projection_mode="family",
        )

    work_ledger.open_thread(
        tmp_path,
        actor="codex",
        actor_session_id="sess_projection",
        phase_id="09_37",
        family_id="09",
        title="Append that leaves sibling projections stale",
    )

    check = work_ledger.check_project_phase(tmp_path, phase_id="09_37", family_id="09")
    diagnostics = check["projection_fanout_diagnostics"]

    assert check["ok"] is True
    assert check["check_scope"] == "selected_phase"
    assert check["selected_phase_fresh"] is True
    assert check["family_projection_fresh"] is False
    assert [row["phase_id"] for row in check["projection_results"] if not row["fresh"]] == [
        "09_35",
        "09_36",
    ]
    assert diagnostics[0]["phase_scoped_disposition"] == "advisory"
    assert diagnostics[0]["phase_scoped_ok"] is True
    assert diagnostics[0]["broad_check_command"] == (
        "./repo-python tools/meta/factory/work_ledger.py project --check --all"
    )


def test_progress_append_updates_only_touched_projection_and_defers_siblings(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    buckets = ["09_35", "09_36"]
    target_td = ""
    for index, phase_id in enumerate(buckets):
        td_id = f"td_baseline{index:010d}"
        work_ledger.append_event(
            tmp_path,
            {
                "schema": work_ledger.WORK_LEDGER_SCHEMA,
                "event_id": f"wle_progress{index:010d}",
                "td_id": td_id,
                "event_kind": "todo_open",
                "actor": "codex",
                "actor_session_id": "sess_projection",
                "phase_id": phase_id,
                "family_id": "09",
                "created_at": f"2026-05-11T00:0{index}:00+00:00",
                "valid_at": f"2026-05-11T00:0{index}:00+00:00",
                "title": f"Baseline bucket {phase_id}",
            },
            projection_mode="family",
        )
        if phase_id == "09_36":
            target_td = td_id

    sibling_index = tmp_path / "codex/ledger/09_35/work_ledger_index.json"
    touched_index = tmp_path / "codex/ledger/09_36/work_ledger_index.json"
    sibling_before = sibling_index.read_text(encoding="utf-8")
    touched_before = touched_index.read_text(encoding="utf-8")

    result = work_ledger.progress_thread(
        tmp_path,
        td_id=target_td,
        actor="codex",
        actor_session_id="sess_projection",
        phase_id="09_36",
        family_id="09",
        body="Tiny progress should not fan out.",
    )

    assert result["projection_mode"] == "append_event"
    assert [row["phase_id"] for row in result["projection_results"]] == ["09_36"]
    assert result["projection_results"][0]["mode"] == "append_only_incremental"
    assert [row["phase_id"] for row in result["deferred_projection_results"]] == ["09_35"]
    assert sibling_index.read_text(encoding="utf-8") == sibling_before
    assert touched_index.read_text(encoding="utf-8") != touched_before

    touched_projection = work_ledger.load_projection(tmp_path, phase_id="09_36", family_id="09")
    assert touched_projection["counts"]["events"] == 3
    assert touched_projection["threads"][target_td]["notes"][0]["body"] == "Tiny progress should not fan out."


def test_work_memory_items_are_projected_from_lifecycle_events(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    opened = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Preserve ledger memory",
        body="The durable claim should become a semantic work-memory item.",
        evidence_refs=["codex/standards/std_work_ledger.json"],
    )
    td_id = str(opened["event"]["td_id"])
    work_ledger.progress_thread(
        tmp_path,
        td_id=td_id,
        actor="codex",
        actor_session_id="sess_2",
        phase_id="09_35",
        family_id="09",
        body="Codex added the deterministic projection seam.",
    )
    work_ledger.close_thread(
        tmp_path,
        td_id=td_id,
        actor="codex",
        actor_session_id="sess_2",
        phase_id="09_35",
        family_id="09",
        body="Projection and query recipe are covered by tests.",
        resolution_episode=work_ledger.build_resolution_episode(
            "artifact",
            "system/lib/work_ledger.py",
        ),
    )

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    items = projection["work_memory_items"]
    by_role = {str(item["role"]): item for item in items}

    assert projection["counts"]["work_memory_items"] == 3
    assert projection["recipe_vocabulary"] == list(work_ledger.supported_query_recipes())
    assert "work_memory_items" in projection["recipe_vocabulary"]
    assert by_role["work_claim"]["memory_type"] == "semantic"
    assert "Preserve ledger memory" in by_role["work_claim"]["summary"]
    assert by_role["progress_update"]["memory_type"] == "episodic"
    assert by_role["progress_update"]["actor"] == "codex"
    assert by_role["resolution"]["memory_type"] == "procedural"
    assert by_role["resolution"]["resolution_episode"]["ref"] == "system/lib/work_ledger.py"


def test_query_recipe_error_names_supported_vocabulary(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    with pytest.raises(ValueError, match="supported: open_in_family"):
        work_ledger.query_recipe(
            tmp_path,
            recipe="active_sessions",
            phase_id="09_35",
            family_id="09",
        )


def test_work_ledger_event_metadata_surfaces_in_projection_and_memory(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    opened = work_ledger.open_thread(
        tmp_path,
        actor="codex",
        actor_session_id="sess_meta",
        phase_id="09_35",
        family_id="09",
        title="Promote agent-seed handoff",
        evidence_refs=["par_agent_example_001"],
        metadata={
            "source_substrate": "agent_seed",
            "source_paragraph_id": "par_agent_example_001",
            "work_kind": "annex_assimilation",
            "plane_home": "annex",
            "target_paths": ["annexes/example"],
            "dedupe_key": "agent_seed:par_agent_example_001:abc123",
            "confidence": 0.72,
        },
    )
    td_id = str(opened["event"]["td_id"])

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    thread = projection["threads"][td_id]
    card = projection["open_by_family"]["09"][0]
    memory = projection["work_memory_items"][0]

    assert opened["event"]["metadata"]["source_substrate"] == "agent_seed"
    assert thread["metadata"]["dedupe_key"] == "agent_seed:par_agent_example_001:abc123"
    assert card["metadata"]["plane_home"] == "annex"
    assert memory["metadata"]["target_paths"] == ["annexes/example"]


def test_work_memory_items_query_recipe_filters_thread_and_actor(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    first = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="First memory thread",
    )
    first_td = str(first["event"]["td_id"])
    work_ledger.progress_thread(
        tmp_path,
        td_id=first_td,
        actor="codex",
        actor_session_id="sess_2",
        phase_id="09_35",
        family_id="09",
        body="Codex contributed one filtered memory item.",
    )
    second = work_ledger.open_thread(
        tmp_path,
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        title="Second memory thread",
    )
    second_td = str(second["event"]["td_id"])

    thread_payload = work_ledger.query_recipe(
        tmp_path,
        recipe="work_memory_items",
        phase_id="09_35",
        family_id="09",
        td_id=first_td,
        limit=10,
    )
    actor_payload = work_ledger.query_recipe(
        tmp_path,
        recipe="work_memory_items",
        phase_id="09_35",
        family_id="09",
        actor="codex",
        limit=10,
    )

    assert thread_payload["matched"] == 2
    assert {item["td_id"] for item in thread_payload["results"]} == {first_td}
    assert actor_payload["matched"] == 1
    assert actor_payload["results"][0]["td_id"] == first_td
    assert second_td not in {item["td_id"] for item in actor_payload["results"]}


def test_cli_mutation_rejects_missing_valid_read_receipt(tmp_path: Path, monkeypatch) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    args = SimpleNamespace(
        actor="claude_code",
        actor_session_id="sess_1",
        phase_id="09_35",
        family_id="09",
        read_receipt_id="wlr_invalid",
        title="Should fail",
        body=None,
        evidence_ref=[],
    )

    with pytest.raises(ValueError):
        work_ledger_cli.cmd_append_open(args)


def test_cli_progress_rejects_ended_receipt_with_structured_recovery(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    session_id = "sess_finished_progress"
    receipt = _bootstrap_session(tmp_path, session_id)
    work_ledger_runtime.finalize_session(
        tmp_path,
        session_id=session_id,
        action="codex-turn-end",
    )

    args = _progress_args(
        receipt=receipt,
        td_id="cap_live_concurrency_projection_freshness",
        session_id=session_id,
        allow_unclaimed_note=True,
    )

    with pytest.raises(SystemExit) as raised:
        work_ledger_cli.cmd_progress(args)
    payload = json.loads(str(raised.value))
    assert payload["schema"] == "work_ledger_read_receipt_error_v1"
    assert payload["status"] == "blocked"
    assert payload["command"] == "progress"
    assert payload["operation"] == "progress_note"
    assert payload["reason"] == "ended_session"
    assert payload["message"] == "read_receipt_id belongs to an ended session"
    assert payload["read_receipt_id"] == receipt
    assert payload["actor_session_id"] == session_id
    assert "session-preflight" in payload["recovery_command"]
    assert "--td-id cap_live_concurrency_projection_freshness" in payload["recovery_command"]


def test_cli_mutation_accepts_valid_read_receipt(tmp_path: Path, monkeypatch) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    receipt = _bootstrap_session(tmp_path, "sess_cli")

    args = SimpleNamespace(
        actor=None,
        actor_session_id=None,
        phase_id=None,
        family_id=None,
        read_receipt_id=receipt,
        title="CLI write succeeds",
        body="A valid session bootstrap issued this receipt.",
        evidence_ref=[],
    )

    assert work_ledger_cli.cmd_append_open(args) == 0
    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    assert projection["counts"]["open_threads"] == 1


def test_append_open_auto_claims_thread_for_same_session_close(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    session_id = "sess_append_open_claim"
    receipt = _bootstrap_session(tmp_path, session_id)

    args = SimpleNamespace(
        actor=None,
        actor_session_id=None,
        phase_id=None,
        family_id=None,
        read_receipt_id=receipt,
        title="Opened and closed by one session",
        body="A valid session bootstrap issued this receipt.",
        body_file=None,
        body_stdin=False,
        evidence_ref=[],
        metadata_json=None,
    )

    assert work_ledger_cli.cmd_append_open(args) == 0
    opened_payload = json.loads(capsys.readouterr().out)
    td_id = opened_payload["event"]["td_id"]

    runtime_claim = opened_payload["runtime_claim"]
    assert runtime_claim["status"] == "claimed"
    assert runtime_claim["session_id"] == session_id
    assert runtime_claim["claim"]["td_id"] == td_id

    assert work_ledger_cli.cmd_close(
        _close_args(receipt=receipt, td_id=td_id, session_id=session_id)
    ) == 0
    capsys.readouterr()

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    assert projection["counts"]["open_threads"] == 0
    assert projection["counts"]["closed_threads"] == 1


def test_work_item_claim_progress_opens_linked_receipt_and_finalizes_clean(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    session_id = "sess_cap_progress"
    work_item_id = "cap_live_concurrency_projection_freshness"
    receipt = _bootstrap_session(tmp_path, session_id)

    claim = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id=session_id,
        td_id=work_item_id,
        lease_minutes=30,
    )
    assert claim["scope_kind"] == "work_item_id"
    assert claim["work_item_id"] == work_item_id

    assert work_ledger_cli.cmd_progress(
        _progress_args(
            receipt=receipt,
            td_id=work_item_id,
            session_id=session_id,
            body="cap-backed progress receipt",
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    opened = next(iter(projection["threads"].values()))
    assert opened["status"] == "open"
    assert opened["td_id"].startswith("td_")
    assert payload["generated_td_id"] == opened["td_id"]
    assert payload["runtime_claim"]["status"] == "claimed"
    assert payload["runtime_claim"]["claim"]["td_id"] == opened["td_id"]
    assert f"--td-id {opened['td_id']}" in payload["next_close_command"]
    assert work_item_id not in payload["next_close_command"]
    assert f"--td-id {opened['td_id']}" in payload["next_claim_command"]
    assert "--resolution-kind session" in payload["next_close_command"]
    assert f"--resolution-ref {session_id}" in payload["next_close_command"]
    assert "--resolution-label 'Work Ledger progress bridge closeout'" in payload["next_close_command"]
    assert "<ref>" not in payload["next_close_command"]
    assert "<artifact" not in payload["next_close_command"]
    bridge = opened["events"][0]["metadata"]["task_ledger_work_item_bridge"]
    assert bridge["receipt_mode"] == "task_ledger_work_item_progress"
    assert bridge["task_ledger_work_item_id"] == work_item_id

    assert work_ledger_cli.cmd_close(
        _close_args(receipt=receipt, td_id=opened["td_id"], session_id=session_id)
    ) == 0
    capsys.readouterr()
    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    assert projection["counts"]["open_threads"] == 0
    assert projection["counts"]["closed_threads"] == 1

    finalized = work_ledger_runtime.finalize_session(
        tmp_path,
        session_id=session_id,
        action="codex-turn-end",
    )
    session = finalized["sessions"][session_id]
    assert session["stale"] is False
    assert session["stale_reason"] is None
    assert session["touched_work_item_ids"] == [work_item_id]
    assert session["touched_td_ids"] == [opened["td_id"]]


def test_session_activity_classifies_cap_ids_as_work_items(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_cap_activity"
    work_item_id = "cap_live_concurrency_projection_freshness"
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id=session_id,
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )

    work_ledger_runtime.mark_session_activity(
        tmp_path,
        session_id=session_id,
        action="tool-use",
        td_id=work_item_id,
    )

    session = work_ledger_runtime.load_runtime_status(tmp_path)["sessions"][session_id]
    assert session["touched_work_item_ids"] == [work_item_id]
    assert session["touched_td_ids"] == []
    legacy_session = dict(session)
    legacy_session["touched_td_ids"] = [work_item_id, "td_legacy"]
    legacy_session.pop("touched_work_item_ids")
    rebuilt = work_ledger_runtime.rebuild_runtime_status(
        {"sessions": {session_id: legacy_session}}
    )
    assert rebuilt["sessions"][session_id]["touched_td_ids"] == ["td_legacy"]
    assert rebuilt["sessions"][session_id]["touched_work_item_ids"] == [work_item_id]
    overview = work_ledger_runtime.load_runtime_status(tmp_path)["cohort_overview"]
    row = overview["contention"]["unclaimed_touched_sessions"][0]
    assert row["unclaimed_touched_work_item_ids"] == [work_item_id]


def test_mark_ledger_query_updates_activity_in_one_runtime_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    session_id = "sess_query"
    receipt = _bootstrap_session(tmp_path, session_id)
    real_write = work_ledger_runtime._write_runtime_status
    write_count = 0

    def counted_write(repo_root: Path, status: dict) -> dict:
        nonlocal write_count
        write_count += 1
        return real_write(repo_root, status)

    monkeypatch.setattr(work_ledger_runtime, "_write_runtime_status", counted_write)

    saved = work_ledger_runtime.mark_ledger_query(
        tmp_path,
        read_receipt_id=receipt,
        session_id=session_id,
        td_id="cap_query_work_item",
    )

    assert write_count == 1
    session = saved["sessions"][session_id]
    assert session["queries"] == 1
    assert session["has_activity"] is True
    assert session["touched_work"] is True
    assert session["touched_work_item_ids"] == ["cap_query_work_item"]
    assert session["open_todos_touched_this_session"] == 1


def test_cli_session_bootstrap_exposes_host_neutral_receipt(tmp_path: Path, monkeypatch, capsys) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_session_bootstrap(
        SimpleNamespace(
            session_id="codex_sess",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            limit=8,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    receipt = str(payload["read_receipt_id"])

    session = work_ledger_runtime.validate_read_receipt(
        tmp_path,
        read_receipt_id=receipt,
        session_id="codex_sess",
    )
    assert session["actor"] == "codex"

    assert work_ledger_cli.cmd_append_open(
        SimpleNamespace(
            actor=None,
            actor_session_id=None,
            phase_id=None,
            family_id=None,
            read_receipt_id=receipt,
            title="Codex CLI write succeeds",
            body="Host-neutral session bootstrap issued this receipt.",
            evidence_ref=[],
        )
    ) == 0
    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    assert projection["open_by_actor"]["codex"][0]["title"] == "Codex CLI write succeeds"


def test_cli_session_finalize_blocks_missing_append_before_stale_finalize(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    work_ledger_cli.cmd_session_bootstrap(
        SimpleNamespace(
            session_id="codex_stale",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            limit=8,
        )
    )
    capsys.readouterr()
    assert work_ledger_cli.cmd_session_activity(
        SimpleNamespace(session_id="codex_stale", action="tool-use", td_id=None)
    ) == 0
    activity_payload = json.loads(capsys.readouterr().out)
    assert activity_payload["schema"] == "work_ledger_session_activity_result_v1"
    assert activity_payload["mode"] == "compact"
    assert activity_payload["session_id"] == "codex_stale"
    assert "sessions" not in activity_payload
    assert activity_payload["session"]["touched_work"] is True

    assert work_ledger_cli.cmd_session_finalize(
        SimpleNamespace(session_id="codex_stale", action="session-end")
    ) == 2
    blocked_payload = json.loads(capsys.readouterr().out)
    assert blocked_payload["schema"] == "work_ledger_session_finalize_result_v1"
    assert blocked_payload["mode"] == "compact"
    assert blocked_payload["status"] == "blocked"
    assert blocked_payload["mutation_performed"] is False
    assert blocked_payload["blocked_by"] == ["append_missing_before_finalize"]
    assert blocked_payload["session_id"] == "codex_stale"
    assert "sessions" not in blocked_payload
    assert blocked_payload["session"]["stale"] is False
    assert blocked_payload["session"]["ended_at"] is None
    assert blocked_payload["landmine_avoidance"]["rule"]
    assert blocked_payload["receipt_authority_guard"]["status"] == "append_missing_before_finalize"
    assert blocked_payload["receipt_authority_guard"]["mutation_stage"] == "pre_finalize_block"
    assert "before session-finalize" in blocked_payload["receipt_authority_guard"]["rule"]
    assert "session-preflight" in blocked_payload["receipt_authority_guard"]["recovery_command_template"]
    assert blocked_payload["append_exempt_closeout"]["required_flag"] == "--append-exempt-reason"
    assert blocked_payload["diagnostic_escape_hatch"]["flag"] == "--allow-missing-append"

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["codex_stale"]
    assert session["actor"] == "codex"
    assert session["ended_at"] is None
    assert session["stale"] is False
    assert status["counts"]["stale_sessions"] == 0
    assert status["triggers"]["stale_session_ready"] is False

    assert work_ledger_cli.cmd_session_finalize(
        SimpleNamespace(
            session_id="codex_stale",
            action="session-end",
            allow_missing_append=True,
        )
    ) == 0
    finalize_payload = json.loads(capsys.readouterr().out)
    assert finalize_payload["schema"] == "work_ledger_session_finalize_result_v1"
    assert finalize_payload["session"]["stale"] is True
    assert finalize_payload["session"]["ended_at"]
    assert finalize_payload["receipt_authority_guard"]["mutation_stage"] == "post_finalize_stale_session"

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["codex_stale"]
    assert session["actor"] == "codex"
    assert session["stale"] is True
    assert status["counts"]["stale_sessions"] == 1
    assert status["triggers"]["stale_session_ready"] is True


def test_session_finalize_append_exempt_releases_path_claim_without_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    session_id = "codex_commit_only"
    receipt = work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id=session_id,
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )["read_receipt_id"]
    claim = work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id=session_id,
        path="tools/meta/factory/work_ledger.py",
        lease_minutes=30,
    )
    assert claim["status"] == "claimed"

    assert work_ledger_cli.cmd_session_finalize(
        SimpleNamespace(
            session_id=session_id,
            action="codex-turn-end",
            read_receipt_id=receipt,
            append_exempt_reason="scoped commit carries the durable evidence",
            append_exempt_ref=["commit:abc123"],
            append_exempt_td_id=[],
            append_exempt_work_item_id=[],
            allow_missing_append=False,
            no_release_claims=False,
            full=False,
            limit=8,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "work_ledger_session_finalize_result_v1"
    assert payload["session"]["append_exempt"] is True
    assert payload["session"]["append_exempt_refs"] == ["commit:abc123"]
    assert payload["session"]["session_had_ledger_append"] is False
    assert payload["session"]["stale"] is False
    assert "receipt_authority_guard" not in payload

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"][session_id]
    assert session["ended_at"]
    assert session["append_exempt"] is True
    assert session["append_exempt_reason"] == "scoped commit carries the durable evidence"
    assert session["append_exempt_refs"] == ["commit:abc123"]
    assert session["session_had_ledger_append"] is False
    assert session["stale"] is False
    assert session["stale_reason"] is None
    assert all(claim["released_at"] for claim in session["claims"])
    assert status["counts"]["stale_sessions"] == 0
    assert status["triggers"]["stale_session_ready"] is False


def test_session_finalize_append_exempt_repairs_ended_stale_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    session_id = "codex_commit_only_ended"
    receipt = work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id=session_id,
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )["read_receipt_id"]
    claim = work_ledger_runtime.claim_work_item(
        tmp_path,
        session_id=session_id,
        work_item_id="cap_live_concurrency_transactional_workitems",
        lease_minutes=30,
    )
    assert claim["status"] == "claimed"

    work_ledger_runtime.finalize_session(
        tmp_path,
        session_id=session_id,
        action="completed_commit_cb901e37",
        release_claims=True,
        release_reason="completed_commit_cb901e37",
    )
    stale_status = work_ledger_runtime.load_runtime_status(tmp_path)
    stale_session = stale_status["sessions"][session_id]
    assert stale_session["ended_at"]
    original_ended_at = stale_session["ended_at"]
    original_end_action = stale_session["end_action"]
    assert stale_session["stale"] is True

    with pytest.raises(ValueError, match="ended session"):
        work_ledger_runtime.validate_read_receipt(
            tmp_path,
            read_receipt_id=receipt,
            session_id=session_id,
        )

    assert work_ledger_cli.cmd_session_finalize(
        SimpleNamespace(
            session_id=session_id,
            action="append_exempt_closeout",
            read_receipt_id=receipt,
            append_exempt_reason="completed commit carries the durable evidence",
            append_exempt_ref=["commit:cb901e37"],
            append_exempt_td_id=[],
            append_exempt_work_item_id=["cap_live_concurrency_transactional_workitems"],
            allow_missing_append=False,
            no_release_claims=False,
            full=False,
            limit=8,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "work_ledger_session_finalize_result_v1"
    assert payload["session"]["append_exempt"] is True
    assert payload["session"]["append_exempt_refs"] == ["commit:cb901e37"]
    assert payload["session"]["stale"] is False
    assert payload["session"]["stale_reason"] is None

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"][session_id]
    assert session["ended_at"] == original_ended_at
    assert session["end_action"] == original_end_action
    assert session["append_exempt"] is True
    assert session["stale"] is False
    assert session["stale_reason"] is None
    assert session["touched_work_item_ids"] == [
        "cap_live_concurrency_transactional_workitems"
    ]
    assert all(claim["released_at"] for claim in session["claims"])
    assert status["counts"]["stale_sessions"] == 0
    assert status["triggers"]["stale_session_ready"] is False


def test_runtime_status_projects_multi_agent_cohort_overview(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")

    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_owner",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="claude_owner",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_unknown",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="cursor_unknown",
        actor="cursor",
        phase_id="09_35",
        family_id="09",
    )

    work_ledger_runtime.mark_session_activity(
        tmp_path,
        session_id="codex_owner",
        action="tool-use",
        td_id="td_shared",
    )
    work_ledger_runtime.mark_session_activity(
        tmp_path,
        session_id="claude_owner",
        action="tool-use",
        td_id="td_shared",
    )
    work_ledger_runtime.mark_session_activity(
        tmp_path,
        session_id="codex_unknown",
        action="tool-use",
    )
    work_ledger_runtime.mark_session_activity(
        tmp_path,
        session_id="cursor_unknown",
        action="tool-use",
    )

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    overview = status["cohort_overview"]

    assert overview["schema"] == "work_ledger_session_cohort_overview_v1"
    assert status["triggers"]["multi_agent_coordination_ready"] is True
    assert overview["contention"]["risk_level"] == "contention"
    assert "td_id_contention" in overview["contention"]["signals"]
    assert "unknown_scope_parallelism" in overview["contention"]["signals"]
    assert overview["contention"]["td_id_collisions"][0]["td_id"] == "td_shared"
    assert overview["contention"]["td_id_collisions"][0]["session_count"] == 2
    assert len(overview["contention"]["unknown_scope_active_sessions"]) == 2
    assert overview["actors"]["codex"]["active_sessions"] == 2
    assert overview["phases"]["09_35"]["active_sessions"] == 4
    assert overview["recommended_actions"]


def test_cohort_overview_separates_orphaned_active_sessions_from_live_pressure() -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    old = (now - timedelta(hours=8)).isoformat()
    fresh = (now - timedelta(minutes=10)).isoformat()
    status = {
        "generated_at": now.isoformat(),
        "counts": {"active_sessions": 4},
        "sessions": {
            "old_unknown": {
                "session_id": "old_unknown",
                "actor": "codex",
                "phase_id": "09_35",
                "family_id": "09",
                "bootstrapped_at": old,
                "last_activity_at": old,
                "touched_work": True,
                "touched_td_ids": [],
            },
            "old_owner": {
                "session_id": "old_owner",
                "actor": "claude_code",
                "phase_id": "09_35",
                "family_id": "09",
                "bootstrapped_at": old,
                "last_activity_at": old,
                "touched_work": True,
                "touched_td_ids": ["td_shared"],
            },
            "fresh_unknown": {
                "session_id": "fresh_unknown",
                "actor": "codex",
                "phase_id": "09_35",
                "family_id": "09",
                "bootstrapped_at": fresh,
                "last_activity_at": fresh,
                "touched_work": True,
                "touched_td_ids": [],
            },
            "fresh_owner": {
                "session_id": "fresh_owner",
                "actor": "claude_code",
                "phase_id": "09_35",
                "family_id": "09",
                "bootstrapped_at": fresh,
                "last_activity_at": fresh,
                "touched_work": True,
                "touched_td_ids": ["td_shared"],
            },
        },
    }

    overview = work_ledger_runtime.build_session_cohort_overview(
        status,
        now=now,
        orphan_after=timedelta(hours=4),
    )

    assert overview["counts"]["active_sessions"] == 4
    assert overview["counts"]["effective_active_sessions"] == 2
    assert overview["counts"]["orphaned_active_sessions"] == 2
    assert overview["contention"]["risk_level"] == "watch"
    assert "orphaned_active_sessions" in overview["contention"]["signals"]
    assert "td_id_contention" not in overview["contention"]["signals"]
    assert "unknown_scope_parallelism" not in overview["contention"]["signals"]
    assert {s["session_id"] for s in overview["orphaned_active_sessions"]} == {
        "old_unknown",
        "old_owner",
    }
    assert {s["session_id"] for s in overview["effective_active_sessions"]} == {
        "fresh_unknown",
        "fresh_owner",
    }
    assert overview["actors"]["codex"]["active_sessions"] == 2
    assert overview["actors"]["codex"]["effective_active_sessions"] == 1
    assert overview["actors"]["codex"]["orphaned_active_sessions"] == 1


def test_cohort_overview_does_not_compact_ended_history_for_live_pressure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    status = {
        "generated_at": now.isoformat(),
        "sessions": {
            **{
                f"ended_{index}": {
                    "session_id": f"ended_{index}",
                    "actor": "codex",
                    "phase_id": "09_35",
                    "ended_at": now.isoformat(),
                }
                for index in range(20)
            },
            "active_owner": {
                "session_id": "active_owner",
                "actor": "codex",
                "phase_id": "09_35",
                "bootstrapped_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "claims": [
                    {
                        "claim_id": "wlc_active",
                        "scope_kind": work_ledger_runtime.CLAIM_SCOPE_THREAD,
                        "scope_id": "td_active",
                        "td_id": "td_active",
                        "leased_until": (now + timedelta(minutes=30)).isoformat(),
                    }
                ],
            },
        },
    }
    compacted_session_ids: list[str] = []
    real_compact = work_ledger_runtime._compact_session

    def counted_compact(session: dict, **kwargs) -> dict:
        compacted_session_ids.append(str(session.get("session_id") or ""))
        return real_compact(session, **kwargs)

    monkeypatch.setattr(work_ledger_runtime, "_compact_session", counted_compact)

    overview = work_ledger_runtime.build_session_cohort_overview(status, now=now)

    assert overview["counts"]["active_claims"] == 1
    assert "active_owner" in compacted_session_ids
    assert all(not session_id.startswith("ended_") for session_id in compacted_session_ids)


def test_cohort_overview_flags_unbound_topic_mission_focus() -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(minutes=5)).isoformat()
    status = {
        "generated_at": now.isoformat(),
        "counts": {"active_sessions": 3, "stale_sessions": 0},
        "sessions": {
            "codex_frontend": {
                "session_id": "codex_frontend",
                "actor": "codex",
                "phase_id": "09_54",
                "family_id": "09",
                "bootstrapped_at": recent,
                "last_activity_at": recent,
                "external_observed": True,
                "external_title": "frontend graph proof pass",
            },
            "claude_frontend": {
                "session_id": "claude_frontend",
                "actor": "claude_code",
                "phase_id": "09_54",
                "family_id": "09",
                "bootstrapped_at": recent,
                "last_activity_at": recent,
                "external_observed": True,
                "external_title": "frontend graph visual audit",
            },
            "claimed_backend": {
                "session_id": "claimed_backend",
                "actor": "codex",
                "phase_id": "09_54",
                "family_id": "09",
                "bootstrapped_at": recent,
                "last_activity_at": recent,
                "touched_work_item_ids": ["cap_backend_contract"],
            },
        },
    }

    overview = work_ledger_runtime.build_session_cohort_overview(status, now=now)
    cards = {str(card["card_id"]): card for card in overview["monitor_cards"]}
    group = overview["contention"]["mission_focus_pressure_groups"][0]

    assert overview["contention"]["risk_level"] == "watch"
    assert "unbound_mission_focus_parallelism" in overview["contention"]["signals"]
    assert "unknown_scope_parallelism" not in overview["contention"]["signals"]
    assert overview["counts"]["mission_focus_pressure_groups"] == 1
    assert cards["mission_focus"]["status"] == "watch"
    assert cards["mission_focus"]["count"] == 1
    assert group["group_id"] == "title_focus:09_54:frontend+graph"
    assert group["pressure_kind"] == "unbound_topic_focus"
    assert group["focus_key"] == "frontend+graph"
    assert group["session_count"] == 2
    assert {row["session_id"] for row in group["sessions"]} == {
        "codex_frontend",
        "claude_frontend",
    }
    assert all(row["explicit_work_ids"] == [] for row in group["sessions"])
    assert any("--td-id <work_item_id>" in action for action in overview["recommended_actions"])


def test_cohort_overview_adds_monitor_cards_and_compacts_host_titles() -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(minutes=2)).isoformat()
    long_title = "Run this repeatedly as an autonomous seed. " * 20
    long_command = "./repo-python kernel.py --context-pack " + ("monitor surface " * 40)
    status = {
        "generated_at": now.isoformat(),
        "counts": {"active_sessions": 2, "stale_sessions": 0},
        "sessions": {
            "codex_long": {
                "session_id": "codex_long",
                "actor": "codex",
                "phase_id": "09_35",
                "family_id": "09",
                "bootstrapped_at": recent,
                "last_activity_at": recent,
                "external_observed": True,
                "external_title": long_title,
                "external_metadata": {
                    "rollout_activity": {
                        "available": True,
                        "recent_commands": [long_command],
                    }
                },
            },
            "claude_short": {
                "session_id": "claude_short",
                "actor": "claude_code",
                "phase_id": "09_35",
                "family_id": "09",
                "bootstrapped_at": recent,
                "last_activity_at": recent,
            },
        },
    }

    overview = work_ledger_runtime.build_session_cohort_overview(status, now=now)
    cards = {str(card["card_id"]): card for card in overview["monitor_cards"]}
    codex_row = next(
        row for row in overview["active_sessions"] if row["session_id"] == "codex_long"
    )
    compacted_command = codex_row["external_metadata"]["rollout_activity"]["recent_commands"][0]

    assert overview["recommended_landing_lane"] == "claim_then_scoped_landing"
    assert cards["cohort"]["status"] == "watch"
    assert cards["cohort"]["risk_band"] == "watch"
    assert cards["claims"]["risk_band"] == "clear"
    assert cards["scope_hygiene"]["status"] == "clear"
    assert cards["scope_hygiene"]["risk_band"] == "clear"
    assert codex_row["external_title_truncated"] is True
    assert codex_row["external_title_full_chars"] > work_ledger_runtime.SESSION_TITLE_LIMIT
    assert len(codex_row["external_title"]) <= work_ledger_runtime.SESSION_TITLE_LIMIT
    assert len(compacted_command) <= work_ledger_runtime.SESSION_METADATA_TEXT_LIMIT


def test_cli_session_status_overview_prints_compact_payload(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_one",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_two",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )

    assert work_ledger_cli.cmd_session_status(
        SimpleNamespace(overview=True, limit=1)
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "work_ledger_session_cohort_overview_v1"
    assert "sessions" not in payload
    assert payload["mode"] == "compact_overview"
    assert len(payload["active_session_rows"]) == 1
    assert "external_metadata" not in payload["active_session_rows"][0]
    assert "active_sessions" not in payload
    assert payload["counts"]["active_sessions"] == 2

    assert work_ledger_cli.cmd_session_status(
        SimpleNamespace(overview=True, full=False, with_session_cards=True, limit=1)
    ) == 0
    detailed_payload = json.loads(capsys.readouterr().out)
    assert len(detailed_payload["active_sessions"]) == 1


def test_cli_session_status_defaults_to_compact_and_full_is_explicit(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_one",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )

    assert work_ledger_cli.cmd_session_status(
        SimpleNamespace(overview=False, full=False, with_session_cards=False, limit=1)
    ) == 0
    compact_payload = json.loads(capsys.readouterr().out)
    assert compact_payload["schema"] == "work_ledger_session_cohort_overview_v1"
    assert compact_payload["mode"] == "compact_overview"
    assert "sessions" not in compact_payload
    assert "active_sessions" not in compact_payload

    assert work_ledger_cli.cmd_session_status(
        SimpleNamespace(overview=False, full=True, with_session_cards=False, limit=1)
    ) == 0
    full_payload = json.loads(capsys.readouterr().out)
    assert full_payload["schema"] == "work_ledger_runtime_status_v1"
    assert "sessions" in full_payload


def test_external_codex_observation_creates_runtime_only_session(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    now = datetime.now(timezone.utc)

    observed = work_ledger_runtime.observe_external_session(
        tmp_path,
        session_id="codex:thread-one",
        actor="codex",
        phase_id="09_35",
        family_id="09",
        started_at=(now - timedelta(minutes=30)).isoformat(),
        last_signal_at=now.isoformat(),
        title="Build runtime tracker",
        source="codex_state_5.sqlite",
        metadata={"tokens_used": 1234},
    )

    assert observed["status"] == "created"
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["codex:thread-one"]
    assert session["actor"] == "codex"
    assert session["read_receipt_id"] is None
    assert session["external_observed"] is True
    assert session["external_title"] == "Build runtime tracker"
    assert session["external_metadata"]["tokens_used"] == 1234
    assert session["touched_work"] is False
    assert status["cohort_overview"]["actors"]["codex"]["effective_active_sessions"] == 1
    compact = status["cohort_overview"]["effective_active_sessions"][0]
    assert compact["external_observed"] is True
    assert compact["external_title"] == "Build runtime tracker"
    assert compact["external_metadata"]["tokens_used"] == 1234


def test_cli_session_import_codex_upserts_recent_host_threads(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    db_path = tmp_path / "state_5.sqlite"
    rollout_path = tmp_path / "rollout.jsonl"
    rollout_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps(
                                {
                                    "cmd": "nl -ba tools/meta/factory/work_ledger.py | sed -n '1,40p'",
                                    "workdir": str(tmp_path),
                                }
                            ),
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "apply_patch",
                            "arguments": (
                                "*** Begin Patch\n"
                                "*** Update File: docs/agent_telemetry.md\n"
                                "@@\n"
                                "+runtime note\n"
                                "*** End Patch\n"
                            ),
                        },
                    }
                ),
            ]
        )
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                title TEXT NOT NULL,
                agent_role TEXT,
                reasoning_effort TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                git_branch TEXT,
                model TEXT,
                cwd TEXT NOT NULL,
                rollout_path TEXT,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        conn.execute(
            """
            INSERT INTO threads (
                id, created_at, updated_at, title, agent_role, reasoning_effort,
                tokens_used, git_branch, model, cwd, rollout_path, archived
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                "thread-live",
                now_epoch - 60,
                now_epoch,
                "Track concurrent agents",
                "",
                "xhigh",
                4567,
                "main",
                "gpt-5.4",
                str(tmp_path),
                str(rollout_path),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    assert work_ledger_cli.cmd_session_import_codex(
        SimpleNamespace(
            actor="codex",
            phase_id="09_35",
            family_id="09",
            since_minutes=15,
            limit=5,
            db_path=str(db_path),
            include_all_cwds=False,
            include_all_workspaces=False,
            dry_run=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "work_ledger_codex_session_import_v1"
    assert payload["candidate_count"] == 1
    assert payload["imported_count"] == 1
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    imported = status["sessions"]["codex:thread-live"]
    assert imported["external_observed"] is True
    assert imported["external_metadata"]["reasoning_effort"] == "xhigh"
    rollout_activity = imported["external_metadata"]["rollout_activity"]
    assert rollout_activity["schema"] == "codex_rollout_activity_summary_v1"
    assert "exec_command" in rollout_activity["recent_tool_names"]
    assert "tools/meta/factory/work_ledger.py" in rollout_activity["recent_referenced_paths"]
    assert "docs/agent_telemetry.md" in rollout_activity["recent_mutation_paths"]
    assert rollout_activity["recent_commands"] == [
        "nl -ba tools/meta/factory/work_ledger.py | sed -n '1,40p'"
    ]
    compact_activity = status["cohort_overview"]["active_sessions"][0]["external_metadata"][
        "rollout_activity"
    ]
    assert compact_activity["schema"] == "codex_rollout_activity_summary_v1"
    assert "tools/meta/factory/work_ledger.py" in compact_activity["recent_referenced_paths"]
    assert len(compact_activity["recent_referenced_paths"]) <= 12


def test_cli_session_import_host_surfaces_imports_claude_ide_locks(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    claude_ide = tmp_path / ".claude" / "ide"
    claude_todos = tmp_path / ".claude" / "todos"
    claude_ide.mkdir(parents=True)
    claude_todos.mkdir(parents=True)
    _write_json(
        tmp_path,
        ".claude/ide/123.lock",
        {
            "pid": 123,
            "workspaceFolders": [str(tmp_path)],
            "ideName": "Visual Studio Code",
            "transport": "ws",
            "authToken": "must-not-surface",
        },
    )
    _write_json(tmp_path, ".claude/todos/todo.json", [{"content": "open"}])
    monkeypatch.setattr(work_ledger_cli, "CLAUDE_IDE_DIR", claude_ide)
    monkeypatch.setattr(work_ledger_cli, "CLAUDE_TODOS_DIR", claude_todos)

    assert work_ledger_cli.cmd_session_import_host_surfaces(
        SimpleNamespace(
            phase_id="09_35",
            family_id="09",
            since_minutes=60,
            limit=5,
            overview_limit=5,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            skip_codex=True,
            skip_claude=False,
            dry_run=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "work_ledger_host_surface_import_v1"
    assert payload["claude_ide_import"]["imported_count"] == 1
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["claude_ide:123"]
    assert session["actor"] == "claude_code"
    assert session["external_source"] == "claude_ide_lock"
    assert "authToken" not in json.dumps(session["external_metadata"])
    assert session["external_metadata"]["todo_files_nonempty"] == 1


def test_cli_session_preflight_bootstraps_claims_and_prints_closeout_commands(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    real_write = work_ledger_runtime._write_runtime_status
    write_count = 0

    def counted_write(repo_root: Path, status: dict) -> dict:
        nonlocal write_count
        write_count += 1
        return real_write(repo_root, status)

    def fail_standalone_claims(*_args, **_kwargs):
        raise AssertionError("session-preflight should claim inside bootstrap transaction")

    monkeypatch.setattr(work_ledger_runtime, "_write_runtime_status", counted_write)
    monkeypatch.setattr(work_ledger_runtime, "claim_work_scopes", fail_standalone_claims)

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight",
            session_slug="meta",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=["td_existing"],
            path=[
                "tools/meta/factory/work_ledger.py",
                "obsidian/okay lets do this/raw seed.md",
            ],
            lease_minutes=30,
            note="bounded preflight test",
            require_exclusive=True,
            skip_import_codex=True,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=20,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert write_count == 1
    assert payload["schema"] == "work_ledger_session_preflight_v1"
    assert payload["mode"] == "compact"
    assert payload["session_id"] == "codex_preflight"
    assert payload["read_receipt_id"].startswith("wlr_")
    assert "bootstrap" not in payload
    assert "overview" not in payload
    assert payload["codex_import_summary"] is None
    assert payload["claim_summary"] == {
        "requested": 3,
        "claimed": 3,
        "claimed_with_collision": 0,
        "refused": 0,
    }
    assert [claim["status"] for claim in payload["claims"]] == ["claimed", "claimed", "claimed"]
    assert payload["overview_summary"]["counts"]["active_claims"] == 3
    assert payload["closeout_rule"]["status"] == "append_or_append_exempt_before_finalize"
    assert payload["closeout_rule"]["read_receipt_id"] == payload["read_receipt_id"]
    assert payload["closeout_plan"]["schema"] == "work_ledger_closeout_plan_v1"
    assert payload["closeout_plan"]["recommended_sequence"] == payload["closeout_commands"]
    commands = payload["closeout_commands"]
    assert commands[-1] == (
        "./repo-python tools/meta/factory/work_ledger.py "
        "session-finalize --session-id codex_preflight --action codex-turn-end"
    )
    assert any(
        "--td-id td_existing" in command
        and f"--read-receipt-id {payload['read_receipt_id']}" in command
        for command in commands
    )
    assert payload["closeout_plan"]["alternative_commands"]
    assert any(
        "--append-exempt-reason" in item["command"]
        and f"--read-receipt-id {payload['read_receipt_id']}" in item["command"]
        and item["do_not_follow_with_bare_finalize"] is True
        for item in payload["closeout_plan"]["alternative_commands"]
    )

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["codex_preflight"]
    assert session["read_receipt_id"] == payload["read_receipt_id"]
    assert len(session["claims"]) == 3


def test_cli_session_preflight_path_only_claim_recommends_append_exempt_finalize(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_path_only",
            session_slug="meta",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=["tools/meta/factory/work_ledger.py"],
            lease_minutes=30,
            note="bounded preflight test",
            require_exclusive=True,
            skip_import_codex=True,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=20,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["closeout_plan"]["schema"] == "work_ledger_closeout_plan_v1"
    assert payload["closeout_commands"] == payload["closeout_plan"]["recommended_sequence"]
    assert len(payload["closeout_commands"]) == 1
    assert "--append-exempt-reason" in payload["closeout_commands"][0]
    assert "--read-receipt-id" in payload["closeout_commands"][0]
    assert "session-finalize --session-id codex_path_only" in payload["closeout_commands"][0]
    assert not payload["closeout_plan"]["alternative_commands"]
    bare_finalize = [
        role
        for role in payload["closeout_plan"]["command_roles"]
        if role["role"] == "bare_finalize_after_append_exists"
    ][0]
    assert bare_finalize["will_block_if"].startswith("touched_work=true")

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["codex_path_only"]
    assert session["read_receipt_id"] == payload["read_receipt_id"]
    assert len(session["claims"]) == 1


def test_session_preflight_accepts_common_shorthand_aliases() -> None:
    parser = work_ledger_cli.build_parser()

    args = parser.parse_args(
        [
            "session-preflight",
            "--session-id",
            "codex_alias_preflight",
            "--work-item-id",
            "cap_alias",
            "--claim-path",
            "tools/meta/factory/work_ledger.py",
            "--limit",
            "4",
        ]
    )

    assert args.td_id == ["cap_alias"]
    assert args.path == ["tools/meta/factory/work_ledger.py"]
    assert args.overview_limit == 4


def test_cli_session_preflight_imports_codex_peers_before_bootstrap(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    db_path = tmp_path / "state_5.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                title TEXT NOT NULL,
                agent_role TEXT,
                reasoning_effort TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                git_branch TEXT,
                model TEXT,
                cwd TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        conn.execute(
            """
            INSERT INTO threads (
                id, created_at, updated_at, title, agent_role, reasoning_effort,
                tokens_used, git_branch, model, cwd, archived
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                "peer-thread",
                now_epoch - 120,
                now_epoch,
                "Peer autonomous seed",
                "",
                "xhigh",
                999,
                "main",
                "gpt-5.4",
                str(tmp_path),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_import",
            session_slug="meta",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=[],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=False,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=5,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=str(db_path),
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "compact"
    assert payload["codex_import_summary"]["candidate_count"] == 1
    assert payload["codex_import_summary"]["imported_count"] == 1
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    assert "codex:peer-thread" in status["sessions"]
    assert "codex_preflight_import" in status["sessions"]


def test_cli_session_preflight_reports_observed_path_overlap_from_codex_rollout(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    db_path = tmp_path / "state_5.sqlite"
    rollout_path = tmp_path / "peer_rollout.jsonl"
    rollout_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "apply_patch",
                            "arguments": (
                                "*** Begin Patch\n"
                                "*** Update File: tools/meta/factory/work_ledger.py\n"
                                "@@\n"
                                "+peer change\n"
                                "*** End Patch\n"
                            ),
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps(
                                {
                                    "cmd": "sed -n '1,20p' tools/meta/factory/work_ledger.py",
                                    "workdir": str(tmp_path),
                                }
                            ),
                        },
                    }
                ),
            ]
        )
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                title TEXT NOT NULL,
                agent_role TEXT,
                reasoning_effort TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                git_branch TEXT,
                model TEXT,
                cwd TEXT NOT NULL,
                rollout_path TEXT,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        conn.execute(
            """
            INSERT INTO threads (
                id, created_at, updated_at, title, agent_role, reasoning_effort,
                tokens_used, git_branch, model, cwd, rollout_path, archived
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                "peer-overlap",
                now_epoch - 90,
                now_epoch,
                "Peer touches work ledger",
                "",
                "xhigh",
                111,
                "main",
                "gpt-5.4",
                str(tmp_path),
                str(rollout_path),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_overlap",
            session_slug="overlap",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=["tools/meta/factory/work_ledger.py"],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=False,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=5,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=str(db_path),
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    overlaps = payload["observed_path_overlaps"]
    assert len(overlaps) == 1
    overlap = overlaps[0]
    assert overlap["requested_path"] == "tools/meta/factory/work_ledger.py"
    assert overlap["session_id"] == "codex:peer-overlap"
    assert "title" not in overlap
    assert overlap["title_preview"] == "Peer touches work ledger"
    assert overlap["title_full_omitted"] is False
    assert overlap["mutation_paths"] == ["tools/meta/factory/work_ledger.py"]
    assert overlap["recent_commands"] == [
        "sed -n '1,20p' tools/meta/factory/work_ledger.py"
    ]


def test_cli_session_preflight_omits_long_overlap_title_cargo(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    db_path = tmp_path / "state_5.sqlite"
    rollout_path = tmp_path / "peer_rollout.jsonl"
    rollout_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "apply_patch",
                            "arguments": (
                                "*** Begin Patch\n"
                                "*** Update File: tools/meta/factory/work_ledger.py\n"
                                "@@\n"
                                "+peer change\n"
                                "*** End Patch\n"
                            ),
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps(
                                {
                                    "cmd": "sed -n '1,20p' tools/meta/factory/work_ledger.py",
                                    "workdir": str(tmp_path),
                                }
                            ),
                        },
                    }
                ),
            ]
        )
    )
    long_title = (
        "PACKET v=3.2\n"
        "thread: metadata cargo regression\n"
        + ("repeated packet title cargo " * 1800)
        + "UNBOUNDED_TITLE_CARGO_SENTINEL"
    )
    title_hash = f"sha256:{hashlib.sha256(long_title.encode('utf-8')).hexdigest()}"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                title TEXT NOT NULL,
                agent_role TEXT,
                reasoning_effort TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                git_branch TEXT,
                model TEXT,
                cwd TEXT NOT NULL,
                rollout_path TEXT,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        for thread_id, offset in (("peer-long-one", 90), ("peer-long-two", 80)):
            conn.execute(
                """
                INSERT INTO threads (
                    id, created_at, updated_at, title, agent_role, reasoning_effort,
                    tokens_used, git_branch, model, cwd, rollout_path, archived
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    thread_id,
                    now_epoch - offset,
                    now_epoch,
                    long_title,
                    "",
                    "xhigh",
                    111,
                    "main",
                    "gpt-5.4",
                    str(tmp_path),
                    str(rollout_path),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_long_overlap_title",
            session_slug="overlap",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=["tools/meta/factory/work_ledger.py"],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=False,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=5,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=str(db_path),
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert "UNBOUNDED_TITLE_CARGO_SENTINEL" not in out
    overlaps = payload["observed_path_overlaps"]
    assert len(overlaps) == 2
    for overlap in overlaps:
        assert overlap["requested_path"] == "tools/meta/factory/work_ledger.py"
        assert "title" not in overlap
        assert overlap["title_preview"].startswith("PACKET v=3.2 thread: metadata cargo regression")
        assert len(overlap["title_preview"]) <= work_ledger_cli.OVERLAP_TITLE_PREVIEW_CHARS
        assert overlap["title_bytes"] == len(long_title.encode("utf-8"))
        assert overlap["title_hash"] == title_hash
        assert overlap["title_kind"] == "packet_title_or_long_prompt"
        assert overlap["title_full_omitted"] is True
        assert overlap["title_ref"].endswith(":external_title")
        assert overlap["omission_receipt"]["omitted"] == ["full title body"]
        assert "session-preflight" in overlap["omission_receipt"]["drilldown"]
        assert "--full" in overlap["omission_receipt"]["drilldown"]
        assert overlap["mutation_paths"] == ["tools/meta/factory/work_ledger.py"]
        assert overlap["recent_commands"] == [
            "sed -n '1,20p' tools/meta/factory/work_ledger.py"
        ]


def test_cli_session_preflight_flags_shared_worktree_git_stash(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    db_path = tmp_path / "state_5.sqlite"
    rollout_path = tmp_path / "peer_rollout.jsonl"
    rollout_path.write_text(
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "exec_command",
                    "arguments": json.dumps(
                        {
                            "cmd": "git stash push -u -m before-fix && git stash apply",
                            "workdir": str(tmp_path),
                        }
                    ),
                },
            }
        )
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                title TEXT NOT NULL,
                agent_role TEXT,
                reasoning_effort TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                git_branch TEXT,
                model TEXT,
                cwd TEXT NOT NULL,
                rollout_path TEXT,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        conn.execute(
            """
            INSERT INTO threads (
                id, created_at, updated_at, title, agent_role, reasoning_effort,
                tokens_used, git_branch, model, cwd, rollout_path, archived
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                "peer-stash",
                now_epoch - 90,
                now_epoch,
                "Peer uses stash",
                "",
                "high",
                111,
                "main",
                "gpt-5.4",
                str(tmp_path),
                str(rollout_path),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_git_risk",
            session_slug="git-risk",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=[],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=False,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=5,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=str(db_path),
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    risks = payload["shared_worktree_git_risks"]
    assert len(risks) == 1
    assert risks[0]["risk"] == "shared_git_stash"
    assert risks[0]["session_id"] == "codex:peer-stash"
    assert "git stash push" in risks[0]["command"]
    assert "shared dirty worktree" in risks[0]["advice"]


def test_shared_worktree_guard_blocks_destructive_git_in_dirty_tree() -> None:
    decision = shared_worktree_guard.assess_git_argv(
        ["restore", "codex/doctrine/agent_bootstrap.json"],
        repo_root=Path("/unused"),
        dirty_paths=["codex/doctrine/agent_bootstrap.json", "system/lib/navigation_hologram.py"],
    )

    assert decision["allowed"] is False
    assert decision["blocked"] is True
    assert decision["dirty_path_count"] == 2
    assert decision["risks"][0]["risk"] == "shared_git_restore"
    assert "shared dirty worktree" in decision["advice"]


def test_shared_worktree_guard_allows_read_only_git_status_in_dirty_tree() -> None:
    decision = shared_worktree_guard.assess_git_argv(
        ["status", "--short"],
        repo_root=Path("/unused"),
        dirty_paths=["AGENTS.md"],
    )

    assert decision["allowed"] is True
    assert decision["blocked"] is False
    assert decision["risks"] == []


def test_shared_worktree_guard_detects_shell_chained_stash_apply() -> None:
    risks = shared_worktree_guard.detect_git_risks_in_text(
        "git stash push -u -m before-fix && git stash apply"
    )

    assert [risk["risk"] for risk in risks] == ["shared_git_stash"]
    assert "git stash push" in risks[0]["command"]


def test_cli_session_preflight_full_payload_keeps_diagnostic_detail(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_full",
            session_slug="meta",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=["tools/meta/factory/work_ledger.py"],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=True,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=20,
            bootstrap_limit=8,
            overview_limit=2,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            full=True,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "work_ledger_session_preflight_v1"
    assert payload["mode"] == "full"
    assert payload["bootstrap"]["schema"] == "work_ledger_bootstrap_v1"
    assert payload["overview"]["schema"] == "work_ledger_session_cohort_overview_v1"
    assert payload["claims"][0]["claim"]["path"] == "tools/meta/factory/work_ledger.py"


def test_cli_session_preflight_write_profile_expands_generated_write_claims(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_profiles",
            session_slug="projection",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=["tools/meta/factory/work_ledger.py"],
            write_profile=["skill_catalog_projection", "paper_module_index", "navigation_hologram_projection"],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=True,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=20,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    claimed_paths = {
        claim["path"]
        for claim in payload["claims"]
        if claim["status"] == "claimed"
    }
    assert payload["claim_summary"]["requested"] == 10
    assert {profile["profile"] for profile in payload["write_profiles"]} == {
        "skill_catalog_projection",
        "paper_module_index",
        "navigation_hologram_projection",
    }
    assert "tools/meta/factory/work_ledger.py" in claimed_paths
    assert "AGENTS.md" in claimed_paths
    assert "codex/doctrine/skills/skill_registry.json" in claimed_paths
    assert "codex/doctrine/skills/skill_map.md" in claimed_paths
    assert "codex/doctrine/paper_modules/README.md" in claimed_paths
    assert "codex/doctrine/paper_modules/_index.json" in claimed_paths
    assert "codex/doctrine/paper_modules/_validation_report.json" in claimed_paths
    assert "codex/doctrine/paper_modules/_doctrine_to_paper_modules.json" in claimed_paths
    assert "codex/doctrine/paper_modules/_route_coverage.json" in claimed_paths
    assert "codex/navigation_hologram" in claimed_paths

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["codex_preflight_profiles"]
    active_claim_paths = {
        claim["path"]
        for claim in session["claims"]
        if not claim["released_at"] and not claim["expired_at"]
    }
    assert claimed_paths == active_claim_paths


def test_cli_session_preflight_blocks_heavy_work_before_claims_under_host_pressure(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    def blocked_admission(*_args, **_kwargs):
        return {
            "schema": "work_creation_host_pressure_admission_v0",
            "status": "available",
            "decision": "queue_until_pressure_clears",
            "should_block_run": True,
            "recommendation_effect": "defer_or_use_cheaper_summary",
            "admission": {
                "decision": "queue_until_pressure_clears",
                "reason": "synthetic swap churn",
            },
        }

    def fail_bootstrap(*_args, **_kwargs):
        raise AssertionError("blocked session-preflight must not create Work Ledger claims")

    monkeypatch.setattr(work_ledger_cli.work_admission, "build_host_pressure_admission", blocked_admission)
    monkeypatch.setattr(work_ledger_runtime, "bootstrap_session", fail_bootstrap)

    rc = work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_blocked_heavy",
            session_slug="projection",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=["codex/doctrine/paper_modules/README.md"],
            write_profile=["paper_module_index"],
            lease_minutes=30,
            note=None,
            host_pressure_policy="auto",
            work_admission_class=None,
            require_exclusive=False,
            skip_import_codex=True,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=20,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == work_admission.ADMISSION_TEMPFAIL
    assert payload["status"] == "blocked_by_work_admission"
    assert payload["claim_summary"] == {
        "requested": 5,
        "claimed": 0,
        "claimed_with_collision": 0,
        "refused": 5,
    }
    assert payload["work_admission"]["result"] == "queue_until_pressure_clears"
    assert payload["work_admission"]["new_heavy_work_launched"] is False


def test_cli_helper_lease_admission_blocks_new_helper_under_host_pressure(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    def blocked_admission(*_args, **_kwargs):
        return {
            "schema": "work_creation_host_pressure_admission_v0",
            "status": "available",
            "decision": "queue_until_pressure_clears",
            "should_block_run": True,
            "summary": {
                "bottleneck_class": "memory_pressure_swap_churn",
                "load_shed_recommended": True,
            },
            "admission": {
                "decision": "queue_until_pressure_clears",
                "reason": "synthetic swap churn",
            },
        }

    monkeypatch.setattr(work_ledger_cli.work_admission, "build_host_pressure_admission", blocked_admission)

    rc = work_ledger_cli.cmd_helper_lease_admission(
        SimpleNamespace(
            lease_kind=work_admission.PLAYWRIGHT_MCP,
            host_pressure_policy="auto",
            request_id="playwright_tool_start",
            requested_by="codex_session",
            owner_status="active_session",
            current_lease_count=2,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == work_admission.ADMISSION_TEMPFAIL
    assert payload["schema"] == work_admission.HELPER_LEASE_ADMISSION_SCHEMA
    assert payload["result"] == "queue_until_pressure_clears"
    assert payload["new_helper_lease_started"] is False
    assert payload["safety"]["no_unknown_owner_killed"] is True


def test_cli_resident_pressure_relief_requires_resident_actuator(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        work_ledger_cli,
        "_current_host_pressure_packet",
        lambda *_args, **_kwargs: {
            "summary": {
                "active_agents": 8,
                "pressure_index": 1.0,
                "progress_per_pressure": 40.0,
                "bottleneck_class": "memory_pressure_swap_churn",
            }
        },
    )

    rc = work_ledger_cli.cmd_resident_pressure_relief(
        SimpleNamespace(
            process_kind=work_admission.PLAYWRIGHT_MCP,
            owner_status="active_session",
            rss_mb_total=512.0,
            target_owner="codex_session",
            pressure_mode="degraded",
            owner_release_result="unsupported",
            result_note=None,
            background_loop_kind=None,
            owner_surface=None,
            background_loop_result="unsupported",
            duration_s=600,
            effective_interval_s=15.0,
            apply_background_downshift=False,
            blocked_work_starts=1,
            blocked_helper_leases=1,
            workload_mix_changed=False,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == work_admission.ADMISSION_TEMPFAIL
    assert payload["schema"] == "resident_pressure_relief_command_v1"
    assert payload["resident_pressure_relief_window"]["verdict"] == "no_resident_actuator"
    assert payload["safety"]["no_active_session_terminated"] is True


def test_cli_resident_pressure_relief_accepts_applied_downshift(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        work_ledger_cli,
        "_current_host_pressure_packet",
        lambda *_args, **_kwargs: {
            "summary": {
                "active_agents": 8,
                "pressure_index": 1.0,
                "progress_per_pressure": 40.0,
                "bottleneck_class": "memory_pressure_swap_churn",
            }
        },
    )

    rc = work_ledger_cli.cmd_resident_pressure_relief(
        SimpleNamespace(
            process_kind=work_admission.PLAYWRIGHT_MCP,
            owner_status="active_session",
            rss_mb_total=512.0,
            target_owner="codex_session",
            pressure_mode="degraded",
            owner_release_result="accepted",
            result_note=None,
            background_loop_kind=work_admission.AGENT_OBSERVABILITY_SAMPLER,
            owner_surface="system/server/main.py::agent_observability_sampler_loop",
            background_loop_result="applied",
            duration_s=600,
            effective_interval_s=15.0,
            apply_background_downshift=False,
            blocked_work_starts=1,
            blocked_helper_leases=1,
            workload_mix_changed=False,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["owner_release_result"]["release_confirmed"] is True
    assert payload["background_loop_downshift"]["applied"] is True
    assert payload["resident_pressure_relief_window"]["verdict"] == "pending_recheck"


def test_cli_resident_pressure_relief_can_write_downshift_state(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    state_path = tmp_path / "state/performance/background_loop_downshift.json"
    monkeypatch.setattr(work_ledger_cli, "BACKGROUND_DOWNSHIFT_STATE", state_path)
    monkeypatch.setattr(
        work_ledger_cli,
        "_current_host_pressure_packet",
        lambda *_args, **_kwargs: {
            "summary": {
                "active_agents": 8,
                "pressure_index": 1.0,
                "progress_per_pressure": 40.0,
                "bottleneck_class": "memory_pressure_swap_churn",
            }
        },
    )

    rc = work_ledger_cli.cmd_resident_pressure_relief(
        SimpleNamespace(
            process_kind=work_admission.PLAYWRIGHT_MCP,
            owner_status="active_session",
            rss_mb_total=512.0,
            target_owner="codex_session",
            pressure_mode="degraded",
            owner_release_result="unsupported",
            result_note=None,
            background_loop_kind=work_admission.AGENT_OBSERVABILITY_SAMPLER,
            owner_surface="system/server/main.py::agent_observability_sampler_loop",
            background_loop_result="unsupported",
            duration_s=600,
            effective_interval_s=15.0,
            apply_background_downshift=True,
            blocked_work_starts=1,
            blocked_helper_leases=1,
            workload_mix_changed=False,
        )
    )
    payload = json.loads(capsys.readouterr().out)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert rc == 0
    assert payload["background_downshift_state_path"] == "state/performance/background_loop_downshift.json"
    assert state["loop_kind"] == work_admission.AGENT_OBSERVABILITY_SAMPLER
    assert state["result"] == "applied"
    assert state["effective_interval_s"] == 15.0


def test_cli_session_yield_request_appends_owner_visible_bus(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    request_path = tmp_path / "state/performance/session_yield_requests.jsonl"
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(work_ledger_cli, "SESSION_YIELD_REQUESTS", request_path)

    rc = work_ledger_cli.cmd_session_yield_request(
        SimpleNamespace(
            target_session_id="codex-session",
            request_id=None,
            target_class="high_helper_footprint_session",
            requested_action="release_tool_lease",
            owner_status="active_session",
            pressure_mode="degraded",
            result="requested",
            helper_rss_mb=768.0,
            recent_progress_units=0.0,
            idle_age_s=900.0,
            last_heartbeat_age_s=1200.0,
            active_claim_count=0,
            operator_priority_hint=None,
            result_note=None,
            dry_run=False,
        )
    )
    payload = json.loads(capsys.readouterr().out)
    rows = [json.loads(line) for line in request_path.read_text(encoding="utf-8").splitlines()]

    assert rc == 0
    assert payload["schema"] == "session_yield_request_command_v1"
    assert payload["written"] is True
    assert payload["request_id"].startswith("syr_")
    assert payload["session_yield_request"]["schema"] == work_admission.SESSION_YIELD_REQUEST_SCHEMA
    assert payload["session_yield_request"]["request_id"] == payload["request_id"]
    assert payload["session_pressure_rank"]["rows"][0]["candidate_action"] == "ask_release_tool_lease"
    assert rows[0]["session_yield_request"]["target_id"] == "codex-session"
    assert rows[0]["safety"]["no_active_session_terminated"] is True


def test_cli_session_yield_request_dry_run_does_not_write_unknown_owner(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    request_path = tmp_path / "state/performance/session_yield_requests.jsonl"
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(work_ledger_cli, "SESSION_YIELD_REQUESTS", request_path)

    rc = work_ledger_cli.cmd_session_yield_request(
        SimpleNamespace(
            target_session_id="unknown-session",
            request_id=None,
            target_class="high_helper_footprint_session",
            requested_action="release_tool_lease",
            owner_status="unknown_parent",
            pressure_mode="degraded",
            result="accepted",
            helper_rss_mb=768.0,
            recent_progress_units=0.0,
            idle_age_s=900.0,
            last_heartbeat_age_s=1200.0,
            active_claim_count=0,
            operator_priority_hint=None,
            result_note=None,
            dry_run=True,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == work_admission.ADMISSION_TEMPFAIL
    assert payload["written"] is False
    assert payload["session_yield_request"]["result"] == "owner_unresolved"
    assert not request_path.exists()


def test_cli_session_yield_result_appends_accepted_applied_result(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    request_path = tmp_path / "state/performance/session_yield_requests.jsonl"
    result_path = tmp_path / "state/performance/session_yield_results.jsonl"
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(work_ledger_cli, "SESSION_YIELD_REQUESTS", request_path)
    monkeypatch.setattr(work_ledger_cli, "SESSION_YIELD_RESULTS", result_path)

    rc = work_ledger_cli.cmd_session_yield_request(
        SimpleNamespace(
            target_session_id="station",
            request_id="syr-test",
            target_class="background_loop_owner",
            requested_action="lower_poll_rate",
            owner_status="active_session",
            pressure_mode="degraded",
            result="requested",
            helper_rss_mb=0.0,
            recent_progress_units=0.0,
            idle_age_s=0.0,
            last_heartbeat_age_s=0.0,
            active_claim_count=0,
            operator_priority_hint=None,
            result_note=None,
            dry_run=False,
        )
    )
    assert rc == 0
    capsys.readouterr()

    rc = work_ledger_cli.cmd_session_yield_result(
        SimpleNamespace(
            request_id="syr-test",
            target_session_id=None,
            result="accepted",
            applied_action="lowered_poll_rate",
            delivery="visible_to_owner",
            result_note="Station downshift accepted",
            dry_run=False,
        )
    )
    payload = json.loads(capsys.readouterr().out)
    rows = [json.loads(line) for line in result_path.read_text(encoding="utf-8").splitlines()]

    assert rc == 0
    assert payload["schema"] == "owner_yield_result_command_v1"
    assert payload["owner_yield_result"]["accepted"] is True
    assert payload["owner_yield_result"]["applied"] is True
    assert rows[0]["owner_yield_result"]["applied_action"] == "lowered_poll_rate"
    assert rows[0]["safety"]["no_process_signal_sent"] is True


def test_cli_session_yield_control_summarizes_pending_and_applied(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    request_path = tmp_path / "state/performance/session_yield_requests.jsonl"
    result_path = tmp_path / "state/performance/session_yield_results.jsonl"
    downshift_path = tmp_path / "state/performance/background_loop_downshift.json"
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(work_ledger_cli, "SESSION_YIELD_REQUESTS", request_path)
    monkeypatch.setattr(work_ledger_cli, "SESSION_YIELD_RESULTS", result_path)
    monkeypatch.setattr(work_ledger_cli, "BACKGROUND_DOWNSHIFT_STATE", downshift_path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    pending = work_admission.build_session_yield_request_receipt(
        target_id="codex-session",
        request_id="syr-pending",
        owner_status="active_session",
    )
    applied_request = work_admission.build_session_yield_request_receipt(
        target_id="station",
        request_id="syr-applied",
        target_class="background_loop_owner",
        requested_action="lower_poll_rate",
        owner_status="active_session",
    )
    result = work_admission.build_owner_yield_result_receipt(
        yield_request=applied_request,
        result="accepted",
        applied_action="lowered_poll_rate",
    )
    work_ledger_cli._append_jsonl(request_path, {"session_yield_request": pending})
    work_ledger_cli._append_jsonl(request_path, {"session_yield_request": applied_request})
    work_ledger_cli._append_jsonl(result_path, {"owner_yield_result": result})
    downshift_path.write_text(
        json.dumps(
            {
                "schema": "background_loop_downshift_receipt_v1",
                "loop_kind": "station_polling",
                "result": "applied",
                "applied": True,
                "effective_interval_s": 60.0,
            }
        ),
        encoding="utf-8",
    )

    rc = work_ledger_cli.cmd_session_yield_control(SimpleNamespace(limit=20))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["schema"] == work_admission.SESSION_YIELD_CONTROL_SURFACE_SCHEMA
    assert payload["counts"]["pending_request_count"] == 1
    assert payload["counts"]["applied_result_count"] == 1
    assert payload["station_downshift_active"] is True
    assert payload["accepted_actuator_count"] == 2


def test_cli_session_preflight_workitem_profiles_expand_shared_spine_claims(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)

    assert work_ledger_cli.cmd_session_preflight(
        SimpleNamespace(
            session_id="codex_preflight_workitem_spine_profiles",
            session_slug="workitem-spine",
            actor="codex",
            phase_id="09_35",
            family_id="09",
            td_id=[],
            path=[],
            write_profile=["task_ledger", "autonomous_seed"],
            lease_minutes=30,
            note=None,
            require_exclusive=False,
            skip_import_codex=True,
            skip_import_claude=True,
            since_minutes=60,
            import_limit=20,
            bootstrap_limit=8,
            overview_limit=5,
            db_path=None,
            include_all_cwds=False,
            include_all_workspaces=False,
            full=False,
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    claimed_paths = {
        claim["path"]
        for claim in payload["claims"]
        if claim["status"] == "claimed"
    }
    assert payload["claim_summary"]["requested"] == 6
    assert {profile["profile"] for profile in payload["write_profiles"]} == {
        "task_ledger",
        "autonomous_seed",
    }
    assert "state/task_ledger/events.jsonl" in claimed_paths
    assert "state/task_ledger/events_audit.jsonl" in claimed_paths
    assert "state/task_ledger/ledger.json" in claimed_paths
    assert "state/task_ledger/views" in claimed_paths
    assert "state/meta_missions/type_a_autonomous_seed_loop/README.md" in claimed_paths
    assert "state/meta_missions/type_a_autonomous_seed_loop/seeds" in claimed_paths


def test_agent_seed_handoffs_extract_and_live_import_open_ledger_rows(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    family_rel, _ = _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    _write_json(
        tmp_path,
        f"{family_rel}/agent_seed.json",
        {
            "kind": "agent_seed",
            "family_id": "09",
            "paragraphs": [
                {
                    "id": "par_agent_phase_09_agent_seed__claude_code_2026_04_24_example_001",
                    "section_id": "sec_agent_phase_09_agent_seed__claude_code_2026_04_24_example",
                    "line_start": 10,
                    "line_end": 10,
                    "plain_text": (
                        "Next-agent verbs: (a) run `./repo-python annex_import.py init --url "
                        "https://example.test/repo`; (b) author topology_substrate.md paper module "
                        "after the annex import lands."
                    ),
                }
            ],
        },
    )

    dry = agent_seed_handoffs.extract_agent_seed_handoffs(
        tmp_path,
        family_id="09",
        since_date="2026-04-24",
    )
    assert dry["candidate_count"] == 2
    assert dry["candidates"][0]["metadata"]["source_substrate"] == "agent_seed"
    assert dry["candidates"][0]["metadata"]["plane_home"] == "annex"

    receipt = work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_handoff_import",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )["read_receipt_id"]
    assert work_ledger_cli.cmd_agent_seed_handoffs(
        SimpleNamespace(
            phase_id="09_35",
            family_id="09",
            since_date="2026-04-24",
            limit=10,
            include_imported=True,
            live=True,
            read_receipt_id=receipt,
            actor="codex",
            actor_session_id="codex_handoff_import",
        )
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["opened_count"] == 2
    projection = work_ledger.load_projection(tmp_path, phase_id="09_35", family_id="09")
    rows = list(projection["open_by_family"]["09"])
    assert {row["metadata"]["source_substrate"] for row in rows} == {"agent_seed"}

    after = agent_seed_handoffs.extract_agent_seed_handoffs(
        tmp_path,
        family_id="09",
        since_date="2026-04-24",
        include_imported=False,
    )
    assert after["unimported_count"] == 0


def test_mutation_check_blocks_when_exclusive_path_claim_collides(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="other_agent",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="other_agent",
        path="annexes",
        lease_minutes=30,
    )

    result = work_ledger_cli.cmd_mutation_check(
        SimpleNamespace(
            session_id="this_agent",
            path=[],
            write_profile=["annex_assimilation"],
            require_exclusive=True,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["status"] == "blocked"
    assert payload["collisions"][0]["requested_path"] == "annexes"
    assert payload["collisions"][0]["session_id"] == "other_agent"


def test_mutation_check_blocks_path_claim_beyond_cohort_preview(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="target_owner",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="target_owner",
        path="tools/meta/dissemination/assemble_ai_workflow_proof.py",
        lease_minutes=5,
    )
    for index in range(14):
        session_id = f"newer_owner_{index}"
        work_ledger_runtime.bootstrap_session(
            tmp_path,
            session_id=session_id,
            actor="codex",
            phase_id="09_35",
            family_id="09",
        )
        work_ledger_runtime.claim_work_path(
            tmp_path,
            session_id=session_id,
            path=f"tools/other/{index}.py",
            lease_minutes=60,
        )

    result = work_ledger_cli.cmd_mutation_check(
        SimpleNamespace(
            session_id="this_agent",
            path=["tools/meta/dissemination/assemble_ai_workflow_proof.py"],
            write_profile=[],
            require_exclusive=True,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["status"] == "blocked"
    assert payload["collision_count"] == 1
    assert payload["collisions"][0]["session_id"] == "target_owner"


def test_mutation_check_blocks_directory_claim_descendant_path(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="docs_owner",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="docs_owner",
        path="system/lib",
        lease_minutes=30,
    )

    result = work_ledger_cli.cmd_mutation_check(
        SimpleNamespace(
            session_id="this_agent",
            path=["system/lib/closeout_executor.py"],
            write_profile=[],
            require_exclusive=True,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["status"] == "blocked"
    assert payload["collision_count"] == 1
    assert payload["collisions"][0]["requested_path"] == "system/lib/closeout_executor.py"
    assert payload["collisions"][0]["claim_path"] == "system/lib"
    assert payload["collisions"][0]["session_id"] == "docs_owner"


def test_mutation_check_ignores_callers_own_path_claim(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    monkeypatch.setattr(work_ledger_cli, "REPO_ROOT", tmp_path)
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="this_agent",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="this_agent",
        path="state/architectural_projection",
        lease_minutes=30,
    )

    result = work_ledger_cli.cmd_mutation_check(
        SimpleNamespace(
            session_id="this_agent",
            path=[],
            write_profile=["architectural_projection"],
            require_exclusive=True,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["status"] == "clear"
    assert payload["collision_count"] == 0
    assert any(
        profile["profile"] == "architectural_projection"
        for profile in payload["write_profiles"]
    )


def test_claim_work_thread_records_lease_and_reports_no_collision(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_claim_a",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )

    result = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_claim_a",
        td_id="td_alpha",
        lease_minutes=15,
        note="distilling shard alpha",
    )

    assert result["status"] == "claimed"
    assert result["collisions"] == []
    assert result["claim"]["td_id"] == "td_alpha"
    assert result["claim"]["claim_id"].startswith("wlc_")
    assert result["claim"]["note"] == "distilling shard alpha"

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["sess_claim_a"]
    assert "td_alpha" in session["touched_td_ids"]
    assert len(session["claims"]) == 1
    assert session["claims"][0]["released_at"] is None
    assert session["claims"][0]["expired_at"] is None


def test_claim_work_thread_reports_collision_when_parallel_active_claim(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_owner",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_intruder",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )

    first = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_owner",
        td_id="td_shared",
        lease_minutes=60,
    )
    assert first["status"] == "claimed"

    second = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_intruder",
        td_id="td_shared",
        lease_minutes=60,
    )
    assert second["status"] == "claimed_with_collision"
    assert len(second["collisions"]) == 1
    assert second["collisions"][0]["session_id"] == "sess_owner"
    assert second["collisions"][0]["claim"]["td_id"] == "td_shared"


def test_claim_work_thread_refuses_exclusive_on_collision(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_holder",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_newcomer",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_holder",
        td_id="td_exclusive",
        lease_minutes=30,
    )

    refused = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_newcomer",
        td_id="td_exclusive",
        lease_minutes=30,
        require_exclusive=True,
    )
    assert refused["status"] == "refused"
    assert refused["reason"] == "exclusive_claim_refused_due_to_collision"

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    assert status["sessions"]["sess_newcomer"]["claims"] == []


def test_claim_work_scopes_batches_multiple_claims_in_one_runtime_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_batch",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    real_write = work_ledger_runtime._write_runtime_status
    real_rebuild = work_ledger_runtime.rebuild_runtime_status
    write_count = 0
    rebuild_count = 0

    def counted_write(repo_root: Path, status: dict) -> dict:
        nonlocal write_count
        write_count += 1
        return real_write(repo_root, status)

    def counted_rebuild(status: dict) -> dict:
        nonlocal rebuild_count
        rebuild_count += 1
        return real_rebuild(status)

    monkeypatch.setattr(work_ledger_runtime, "_write_runtime_status", counted_write)
    monkeypatch.setattr(work_ledger_runtime, "rebuild_runtime_status", counted_rebuild)

    results = work_ledger_runtime.claim_work_scopes(
        tmp_path,
        session_id="sess_batch",
        scopes=[
            {"scope_kind": work_ledger_runtime.CLAIM_SCOPE_THREAD, "scope_id": "td_batch"},
            {"scope_kind": work_ledger_runtime.CLAIM_SCOPE_THREAD, "scope_id": "cap_batch"},
            {"scope_kind": work_ledger_runtime.CLAIM_SCOPE_PATH, "scope_id": "system/lib"},
        ],
        lease_minutes=45,
        note="batch claim test",
        require_exclusive=True,
    )

    assert write_count == 1
    assert rebuild_count == 1
    assert [result["status"] for result in results] == ["claimed", "claimed", "claimed"]
    assert [result["scope_kind"] for result in results] == [
        work_ledger_runtime.CLAIM_SCOPE_THREAD,
        work_ledger_runtime.CLAIM_SCOPE_WORK_ITEM,
        work_ledger_runtime.CLAIM_SCOPE_PATH,
    ]
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["sess_batch"]
    assert "td_batch" in session["touched_td_ids"]
    assert "cap_batch" in session["touched_work_item_ids"]
    assert len(session["claims"]) == 3
    assert status["cohort_overview"]["counts"]["active_claims"] == 3


def test_claim_work_scopes_preserves_partial_exclusive_refusal(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_path_holder",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_batch_newcomer",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_path_holder",
        path="system/lib",
        lease_minutes=30,
    )

    results = work_ledger_runtime.claim_work_scopes(
        tmp_path,
        session_id="sess_batch_newcomer",
        scopes=[
            {
                "scope_kind": work_ledger_runtime.CLAIM_SCOPE_PATH,
                "scope_id": "system/lib/work_ledger_runtime.py",
            },
            {
                "scope_kind": work_ledger_runtime.CLAIM_SCOPE_PATH,
                "scope_id": "tools/meta/factory/work_ledger.py",
            },
        ],
        lease_minutes=30,
        require_exclusive=True,
    )

    assert [result["status"] for result in results] == ["refused", "claimed"]
    assert results[0]["collisions"][0]["claim"]["path"] == "system/lib"
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    newcomer_claims = status["sessions"]["sess_batch_newcomer"]["claims"]
    assert len(newcomer_claims) == 1
    assert newcomer_claims[0]["path"] == "tools/meta/factory/work_ledger.py"


def test_claim_work_path_reports_directory_child_collision(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_docs_owner",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_docs_child",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )

    first = work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_docs_owner",
        path="codex/doctrine/paper_modules",
        lease_minutes=60,
    )
    assert first["status"] == "claimed"
    assert first["claim"]["scope_kind"] == "path"
    assert first["claim"]["path"] == "codex/doctrine/paper_modules"

    second = work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_docs_child",
        path="codex/doctrine/paper_modules/work_ledger.md",
        lease_minutes=60,
    )
    assert second["status"] == "claimed_with_collision"
    assert len(second["collisions"]) == 1
    assert second["collisions"][0]["session_id"] == "sess_docs_owner"
    assert second["collisions"][0]["claim"]["scope_kind"] == "path"

    overview = work_ledger_runtime.load_runtime_status(tmp_path)["cohort_overview"]
    assert overview["counts"]["claim_collisions"] == 1
    assert "claim_collision" in overview["contention"]["signals"]
    assert "unknown_scope_parallelism" not in overview["contention"]["signals"]
    collision = overview["contention"]["claim_collisions"][0]
    assert collision["scope_kind"] == "path"
    assert collision["path"] == "codex/doctrine/paper_modules"
    assert collision["claim_count"] == 2
    cards = {str(card["card_id"]): card for card in overview["monitor_cards"]}
    preview = cards["claims"]["details"]["claim_collision_preview"]
    assert cards["claims"]["risk_band"] == "blocked"
    assert preview["collision_count"] == 1
    assert preview["items"][0]["path"] == "codex/doctrine/paper_modules"
    assert {claim["session_id"] for claim in preview["items"][0]["active_claims_preview"]} == {
        "sess_docs_owner",
        "sess_docs_child",
    }


def test_claim_work_path_refuses_exclusive_on_overlapping_path(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_path_holder",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_path_newcomer",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_path_holder",
        path="system/lib",
        lease_minutes=30,
    )

    refused = work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_path_newcomer",
        path="system/lib/work_ledger_runtime.py",
        lease_minutes=30,
        require_exclusive=True,
    )

    assert refused["status"] == "refused"
    assert refused["path"] == "system/lib/work_ledger_runtime.py"
    assert refused["collisions"][0]["claim"]["path"] == "system/lib"

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    assert status["sessions"]["sess_path_newcomer"]["claims"] == []


def test_release_claim_by_path_marks_released_without_deletion(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_release_path",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_release_path",
        path="./tools/meta/factory/work_ledger.py",
        lease_minutes=30,
    )

    released = work_ledger_runtime.release_claim(
        tmp_path,
        session_id="sess_release_path",
        path="tools/meta/factory/work_ledger.py",
        reason="path_slice_done",
    )
    assert released["status"] == "released"
    assert len(released["released"]) == 1

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    claims = status["sessions"]["sess_release_path"]["claims"]
    assert len(claims) == 1
    assert claims[0]["path"] == "tools/meta/factory/work_ledger.py"
    assert claims[0]["released_at"] is not None
    assert claims[0]["release_reason"] == "path_slice_done"


def test_finalize_session_releases_active_claims_by_default(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_finalize_release",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="sess_finalize_release",
        path="tools/meta/factory/work_ledger.py",
        lease_minutes=30,
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_finalize_release",
        td_id="td_beta",
        lease_minutes=30,
    )

    status = work_ledger_runtime.finalize_session(
        tmp_path,
        session_id="sess_finalize_release",
        action="codex-turn-end",
        release_claims=True,
        release_reason="codex-turn-end",
    )

    session = status["sessions"]["sess_finalize_release"]
    assert session["ended_at"] is not None
    assert session["end_action"] == "codex-turn-end"
    assert len(session["claims"]) == 2
    assert all(claim["released_at"] is not None for claim in session["claims"])
    assert {claim["release_reason"] for claim in session["claims"]} == {"codex-turn-end"}
    overview = work_ledger_runtime.build_session_cohort_overview(status)
    assert not [
        claim
        for claim in overview["active_claims"]
        if claim["session_id"] == "sess_finalize_release"
    ]


def test_bootstrap_session_preserves_append_state_when_refreshing_existing_session(
    tmp_path: Path,
) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    first = work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_refresh_after_append",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.mark_ledger_append(
        tmp_path,
        read_receipt_id=str(first["read_receipt_id"]),
        session_id="sess_refresh_after_append",
        td_ids=["td_receipt"],
        event_ids=["wle_receipt"],
    )

    refreshed = work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_refresh_after_append",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )

    assert refreshed["read_receipt_id"] != first["read_receipt_id"]
    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["sess_refresh_after_append"]
    assert session["session_had_ledger_append"] is True
    assert session["writes"] == 1
    assert session["touched_td_ids"] == ["td_receipt"]
    finalized = work_ledger_runtime.finalize_session(
        tmp_path,
        session_id="sess_refresh_after_append",
        action="codex-turn-end",
    )
    assert finalized["sessions"]["sess_refresh_after_append"]["stale"] is False
    assert finalized["sessions"]["sess_refresh_after_append"]["stale_reason"] is None


def test_release_claim_by_td_id_marks_released_without_deletion(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_release",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_release",
        td_id="td_beta",
        lease_minutes=30,
    )

    released = work_ledger_runtime.release_claim(
        tmp_path,
        session_id="sess_release",
        td_id="td_beta",
        reason="shard_imported",
    )
    assert released["status"] == "released"
    assert len(released["released"]) == 1

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    claims = status["sessions"]["sess_release"]["claims"]
    assert len(claims) == 1  # preserved, not deleted
    assert claims[0]["released_at"] is not None
    assert claims[0]["release_reason"] == "shard_imported"


def test_sweep_expired_claims_marks_past_lease_without_deleting(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_expire",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    claim_result = work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_expire",
        td_id="td_gamma",
        lease_minutes=1,
    )
    claim_id = claim_result["claim"]["claim_id"]

    # Fast-forward well past the 1-minute lease.
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    report = work_ledger_runtime.sweep_expired_claims(tmp_path, now=future)

    assert report["swept_count"] == 1
    assert report["details"][0]["claim_id"] == claim_id

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    claims = status["sessions"]["sess_expire"]["claims"]
    assert len(claims) == 1
    assert claims[0]["expired_at"] is not None
    assert claims[0]["release_reason"] == "lease_expired"
    assert claims[0]["released_at"] is None


def test_sweep_orphan_sessions_finalizes_old_and_releases_claims(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_ghost",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="sess_ghost",
        td_id="td_ghost_owned",
        lease_minutes=60,
    )

    # Simulate 30h without any lifecycle signal from this session.
    future = datetime.now(timezone.utc) + timedelta(hours=30)
    report = work_ledger_runtime.sweep_orphan_sessions(
        tmp_path,
        now=future,
        orphan_sweep_after=timedelta(hours=24),
    )
    assert report["swept_count"] == 1
    assert report["details"][0]["session_id"] == "sess_ghost"
    assert report["details"][0]["released_claims"]

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    session = status["sessions"]["sess_ghost"]
    assert session["ended_at"] is not None
    assert session["end_action"] == "auto_orphan_sweep"
    claim = session["claims"][0]
    assert claim["released_at"] is not None
    assert claim["release_reason"] == "session_auto_swept"

    recent = status["recent_sweep_events"]
    assert recent
    assert recent[-1]["kind"] == "orphan_sweep"
    assert recent[-1]["swept_count"] == 1


def test_bootstrap_session_autosweeps_orphans_but_never_itself(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_old",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    # Age the old session past sweep threshold by hand-mutating runtime_status.
    status_path = tmp_path / work_ledger_runtime.RUNTIME_STATUS_REL
    status_payload = json.loads(status_path.read_text())
    far_past = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    status_payload["sessions"]["sess_old"]["bootstrapped_at"] = far_past
    status_payload["sessions"]["sess_old"]["last_activity_at"] = far_past
    status_payload["sessions"]["sess_old"]["touched_work"] = True
    status_path.write_text(json.dumps(status_payload))

    bootstrap = work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="sess_new",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    assert bootstrap["auto_sweep"]["orphan_sweep"]["swept_count"] == 1
    assert bootstrap["auto_sweep"]["orphan_sweep"]["details"][0]["session_id"] == "sess_old"

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    assert status["sessions"]["sess_old"]["ended_at"] is not None
    # The newly bootstrapped session survives; sweep must exclude it.
    assert status["sessions"]["sess_new"]["ended_at"] is None


def test_cohort_overview_surfaces_active_claims_and_claim_collisions(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="claude_claim",
        actor="claude_code",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_claim",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="claude_claim",
        td_id="td_contested",
        lease_minutes=30,
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="codex_claim",
        td_id="td_contested",
        lease_minutes=30,
    )

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    overview = status["cohort_overview"]

    assert overview["counts"]["active_claims"] >= 2
    assert overview["counts"]["claim_collisions"] == 1
    assert "claim_collision" in overview["contention"]["signals"]
    assert overview["contention"]["risk_level"] == "contention"
    repair_rows = {
        row["failure_class"]: row for row in overview["repair_rows"]
    }
    assert "td_claim_collision" in repair_rows
    td_repair = repair_rows["td_claim_collision"]
    assert td_repair["schema"] == work_ledger_runtime.CONCURRENCY_REPAIR_ROW_SCHEMA
    assert td_repair["owning_surface"] == "work_ledger.claims"
    assert "safe_next_command" in td_repair
    assert "proof_route" in td_repair
    assert "residual_capture_route" in td_repair
    collision = overview["contention"]["claim_collisions"][0]
    assert collision["td_id"] == "td_contested"
    assert collision["claim_count"] == 2
    assert set(collision["actors"]) == {"claude_code", "codex"}
    compact_overview = work_ledger_runtime.build_session_cohort_overview(status, limit=0)
    compact_cards = {
        str(card["card_id"]): card for card in compact_overview["monitor_cards"]
    }
    compact_preview = compact_cards["claims"]["details"]["claim_collision_preview"]
    assert compact_overview["contention"]["claim_collisions"] == []
    assert compact_cards["claims"]["risk_band"] == "blocked"
    assert compact_cards["claims"]["repair_rows"][0]["failure_class"] == "td_claim_collision"
    assert compact_preview["collision_count"] == 1
    assert compact_preview["items"][0]["td_id"] == "td_contested"
    assert {claim["session_id"] for claim in compact_preview["items"][0]["active_claims_preview"]} == {
        "claude_claim",
        "codex_claim",
    }
    assert any(
        "claim collisions" in action.lower()
        for action in overview["recommended_actions"]
    )


def test_cohort_overview_emits_duplicate_same_session_claim_repair_row(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_duplicate",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="codex_duplicate",
        td_id="td_duplicate",
        lease_minutes=30,
    )
    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="codex_duplicate",
        td_id="td_duplicate",
        lease_minutes=30,
    )

    overview = work_ledger_runtime.load_runtime_status(tmp_path)["cohort_overview"]
    row = next(
        item
        for item in overview["repair_rows"]
        if item["failure_class"] == "duplicate_same_session_claim"
    )

    assert row["status"] == "watch"
    assert "session-release-claim" in row["safe_next_command"]
    assert "--reason duplicate_same_session_claim" in row["safe_next_command"]


def test_cohort_overview_emits_path_claim_collision_repair_row(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    for session_id in ("codex_path", "claude_path"):
        work_ledger_runtime.bootstrap_session(
            tmp_path,
            session_id=session_id,
            actor="codex",
            phase_id="09_35",
            family_id="09",
        )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="codex_path",
        path="system/lib/work_ledger_runtime.py",
        lease_minutes=30,
    )
    work_ledger_runtime.claim_work_path(
        tmp_path,
        session_id="claude_path",
        path="system/lib/work_ledger_runtime.py",
        lease_minutes=30,
    )

    overview = work_ledger_runtime.load_runtime_status(tmp_path)["cohort_overview"]
    row = next(
        item for item in overview["repair_rows"] if item["failure_class"] == "path_claim_collision"
    )

    assert "mutation-check" in row["safe_next_command"]
    assert "--path system/lib/work_ledger_runtime.py" in row["safe_next_command"]
    assert "--require-exclusive" in row["safe_next_command"]


def test_cohort_overview_flags_touched_threads_without_live_claim(tmp_path: Path) -> None:
    _seed_phase_family(tmp_path)
    work_ledger.bootstrap_phase_bucket(tmp_path, phase_id="09_35", family_id="09")
    work_ledger_runtime.bootstrap_session(
        tmp_path,
        session_id="codex_unclaimed",
        actor="codex",
        phase_id="09_35",
        family_id="09",
    )

    work_ledger_runtime.mark_session_activity(
        tmp_path,
        session_id="codex_unclaimed",
        action="tool-use",
        td_id="td_unclaimed",
    )

    status = work_ledger_runtime.load_runtime_status(tmp_path)
    overview = status["cohort_overview"]

    assert overview["counts"]["unclaimed_touched_sessions"] == 1
    assert "unclaimed_touched_work" in overview["contention"]["signals"]
    assert overview["contention"]["risk_level"] == "watch"
    row = overview["contention"]["unclaimed_touched_sessions"][0]
    assert row["session_id"] == "codex_unclaimed"
    assert row["unclaimed_touched_td_ids"] == ["td_unclaimed"]
    repair_row = next(
        item for item in overview["repair_rows"] if item["failure_class"] == "unclaimed_touched_work"
    )
    assert "session-claim" in repair_row["safe_next_command"]
    assert "--session-id codex_unclaimed" in repair_row["safe_next_command"]
    assert "--td-id td_unclaimed" in repair_row["safe_next_command"]
    assert any("without a live claim" in action for action in overview["recommended_actions"])

    work_ledger_runtime.claim_work_thread(
        tmp_path,
        session_id="codex_unclaimed",
        td_id="td_unclaimed",
        lease_minutes=30,
    )
    overview_after_claim = work_ledger_runtime.load_runtime_status(tmp_path)["cohort_overview"]
    assert overview_after_claim["counts"]["unclaimed_touched_sessions"] == 0
    assert "unclaimed_touched_work" not in overview_after_claim["contention"]["signals"]


def test_cohort_overview_awareness_cards_demote_unknown_and_orphaned_passes() -> None:
    now = datetime(2026, 5, 22, 17, 0, tzinfo=timezone.utc)
    old = now - timedelta(hours=6)
    status = {
        "schema": work_ledger_runtime.WORK_LEDGER_RUNTIME_SCHEMA,
        "generated_at": now.isoformat(),
        "sessions": {
            "sess_live": {
                "session_id": "sess_live",
                "actor": "codex",
                "phase_id": "09_54",
                "bootstrapped_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "claims": [],
                "pass_heartbeat": {
                    "schema": work_ledger_runtime.PASS_HEARTBEAT_SCHEMA,
                    "pass_id": "wlp_live",
                    "pass_seq": 1,
                    "pass_state": "editing",
                    "current_pass_line": "Editing the runtime pass heartbeat owner surface.",
                    "last_pass_result_line": "Confirmed no existing card carried pass intent.",
                    "updated_at": now.isoformat(),
                    "expires_at": (now + timedelta(hours=4)).isoformat(),
                    "source": "manual_cli",
                    "scope_refs": [{"kind": "path", "ref": "system/lib/work_ledger_runtime.py"}],
                },
            },
            "sess_unknown": {
                "session_id": "sess_unknown",
                "actor": "codex",
                "phase_id": "09_54",
                "bootstrapped_at": now.isoformat(),
                "last_activity_at": now.isoformat(),
                "claims": [],
            },
            "sess_orphan": {
                "session_id": "sess_orphan",
                "actor": "codex",
                "phase_id": "09_54",
                "bootstrapped_at": old.isoformat(),
                "last_activity_at": old.isoformat(),
                "claims": [],
                "pass_heartbeat": {
                    "schema": work_ledger_runtime.PASS_HEARTBEAT_SCHEMA,
                    "pass_id": "wlp_orphan",
                    "pass_seq": 2,
                    "pass_state": "validating",
                    "current_pass_line": "Validating a stale prior pass.",
                    "updated_at": old.isoformat(),
                    "expires_at": (old + timedelta(hours=4)).isoformat(),
                    "source": "manual_cli",
                },
            },
        },
        "counts": {},
    }

    overview = work_ledger_runtime.build_session_cohort_overview(status, limit=3, now=now)
    cards = {str(card["session_id"]): card for card in overview["awareness_cards"]}

    assert cards["sess_live"]["freshness_state"] == "live"
    assert cards["sess_live"]["current_pass_line"] == (
        "Editing the runtime pass heartbeat owner surface."
    )
    assert cards["sess_live"]["last_pass_result_line"] == (
        "Confirmed no existing card carried pass intent."
    )
    assert cards["sess_unknown"]["freshness_state"] == "unknown"
    assert cards["sess_unknown"]["current_pass_line"] is None
    assert cards["sess_unknown"]["source"] == "projected_unknown"
    unknown_repair = cards["sess_unknown"]["repair_rows"][0]
    assert unknown_repair["failure_class"] == "projected_unknown_heartbeat"
    assert "session-heartbeat --session-id sess_unknown" in unknown_repair["safe_next_command"]
    assert cards["sess_orphan"]["freshness_state"] == "orphaned"
    assert cards["sess_orphan"]["orphaned_active"] is True
    orphaned_classes = {
        row["failure_class"] for row in cards["sess_orphan"]["repair_rows"]
    }
    assert "orphaned_active_session" in orphaned_classes
