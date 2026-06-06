from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from microcosm_core.engine_room.metabolism_runtime import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    JOB_RECOVERABLE,
    JOB_RUNNING,
    RULE_RUN_FINALIZED_BUT_JOB_RUNNING,
    RULE_RUNNING_JOB_NO_RUN_ROW,
    RULE_RUNNING_JOB_STALE_LAUNCH_LOG,
    append_claim_event,
    build_blackboard_projection,
    claim_next_job,
    complete_run,
    connect,
    enqueue_job,
    evaluate_fixture_dir,
    reconcile,
    requeue_expired_jobs,
    start_run,
    update_job_state,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_metabolism_runtime/input"


def test_wal_schema_and_idempotent_queue(tmp_path: Path) -> None:
    conn = connect(tmp_path / "metabolism.sqlite")
    first, inserted_first = enqueue_job(
        conn,
        kind="demo",
        provider="local",
        params={"x": 1},
        idempotency_key="same",
    )
    second, inserted_second = enqueue_job(
        conn,
        kind="demo",
        provider="local",
        params={"x": 1},
        idempotency_key="same",
    )
    assert inserted_first is True
    assert inserted_second is False
    assert first["id"] == second["id"]
    assert conn.execute("PRAGMA journal_mode;").fetchone()[0] == "wal"


def test_expired_claim_requeues_recoverable(tmp_path: Path) -> None:
    conn = connect(tmp_path / "metabolism.sqlite")
    job, _inserted = enqueue_job(conn, kind="demo", idempotency_key="lease")
    claimed = claim_next_job(conn, owner="worker", lease_seconds=-1)
    assert claimed["id"] == job["id"]
    assert requeue_expired_jobs(conn) == 1
    final = conn.execute("SELECT state, claim_owner FROM jobs WHERE id = ?", (job["id"],)).fetchone()
    assert final["state"] == JOB_RECOVERABLE
    assert final["claim_owner"] is None


def test_blackboard_projection_invalidates_contradicted_claim(tmp_path: Path) -> None:
    conn = connect(tmp_path / "metabolism.sqlite")
    asserted = append_claim_event(
        conn,
        event_kind="claim_asserted",
        claim_id="claim-a",
        subject_ref="agent:a",
        predicate="owns_path",
        object_value="public/a.py",
    )
    append_claim_event(
        conn,
        event_kind="claim_contradicted",
        claim_id="claim-a",
        assertion_event_id=asserted["event_id"],
        subject_ref="agent:a",
        predicate="invalidates_session_currentness",
        object_value="public/a.py",
    )
    projection = build_blackboard_projection(conn)
    assert projection["active_claim_count"] == 0
    assert projection["contradiction_count"] == 1


def test_reconciler_detects_running_job_without_run_row(tmp_path: Path) -> None:
    conn = connect(tmp_path / "metabolism.sqlite")
    job, _inserted = enqueue_job(conn, kind="demo", idempotency_key="no-run")
    claim_next_job(conn, owner="worker")
    update_job_state(conn, job["id"], state=JOB_RUNNING)
    receipt = reconcile(conn, tmp_path)
    assert receipt["status"] == "needs_review"
    assert receipt["rule_counts"][RULE_RUNNING_JOB_NO_RUN_ROW] == 1
    assert receipt["findings"][0]["action"] == "operator_review_required"


def test_reconciler_detects_finalized_run_but_running_job(tmp_path: Path) -> None:
    conn = connect(tmp_path / "metabolism.sqlite")
    job, _inserted = enqueue_job(conn, kind="demo", idempotency_key="finalized")
    claim_next_job(conn, owner="worker")
    run = start_run(conn, job["id"], log_path="logs/demo.log")
    complete_run(conn, run["id"], returncode=0, finalize_job=False)
    receipt = reconcile(conn, tmp_path)
    assert receipt["rule_counts"][RULE_RUN_FINALIZED_BUT_JOB_RUNNING] == 1


def test_reconciler_detects_stale_launch_log(tmp_path: Path) -> None:
    conn = connect(tmp_path / "metabolism.sqlite")
    log_path = tmp_path / "logs/demo.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("started\n", encoding="utf-8")
    old = datetime.now(timezone.utc) - timedelta(seconds=1200)
    os.utime(log_path, (old.timestamp(), old.timestamp()))
    job, _inserted = enqueue_job(conn, kind="demo", idempotency_key="stale-log")
    claim_next_job(conn, owner="worker")
    start_run(conn, job["id"], log_path="logs/demo.log")
    receipt = reconcile(conn, tmp_path, log_freshness_threshold_seconds=60)
    assert receipt["rule_counts"][RULE_RUNNING_JOB_STALE_LAUNCH_LOG] == 1


def test_fixture_matrix_matches_metabolism_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 5
    assert receipt["passed_case_count"] == 5
    assert "not_live_private_runtime_export" in ANTI_CLAIMS
    assert "does not ship the private live metabolism database" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.metabolism_runtime",
            "evaluate-fixtures",
            "--input",
            str(INPUT_DIR),
            "--json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["organ_id"] == "engine_room_metabolism_runtime"
    assert payload["status"] == "pass"
