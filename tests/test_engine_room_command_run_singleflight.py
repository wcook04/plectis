from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.command_run_singleflight import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    _metadata,
    _paths,
    _short_hash,
    _write_json,
    build_command_key,
    evaluate_fixture_dir,
    run_command_singleflight,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_command_run_singleflight/input"


def _counter_command(counter_path: Path, *, sleep_s: float = 0.0) -> list[str]:
    code = (
        "from pathlib import Path\n"
        "import fcntl, time\n"
        f"path = Path({str(counter_path)!r})\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "with path.open('a+', encoding='utf-8') as fh:\n"
        "    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)\n"
        "    fh.seek(0)\n"
        "    value = int((fh.read().strip() or '0')) + 1\n"
        "    fh.seek(0)\n"
        "    fh.truncate()\n"
        "    fh.write(str(value))\n"
        "    fh.flush()\n"
        f"time.sleep({sleep_s!r})\n"
        "print(f'counter={value}')\n"
    )
    return [sys.executable, "-c", code]


def test_scope_fingerprint_changes_when_scoped_file_changes(tmp_path: Path) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    scoped = cwd / "scoped.txt"
    scoped.write_text("before\n", encoding="utf-8")
    command = [sys.executable, "-c", "print('scope')"]
    before = build_command_key(
        argv=command,
        cwd=cwd,
        resource_class="unit",
        scope_paths=["scoped.txt"],
    )
    scoped.write_text("after\n", encoding="utf-8")
    after = build_command_key(
        argv=command,
        cwd=cwd,
        resource_class="unit",
        scope_paths=["scoped.txt"],
    )
    assert before["dirty_fingerprint"] != after["dirty_fingerprint"]


def test_completed_run_can_be_reused_without_rerunning(tmp_path: Path) -> None:
    counter = tmp_path / "counter.txt"
    state = tmp_path / "state"
    command = _counter_command(counter)
    first = run_command_singleflight(command, state_root=state, cwd=tmp_path)
    second = run_command_singleflight(command, state_root=state, cwd=tmp_path, reuse_completed=True)
    assert first.role == "leader"
    assert second.role == "reused"
    assert first.run_id == second.run_id
    assert counter.read_text(encoding="utf-8") == "1"
    assert "counter=1" in second.stdout


def test_concurrent_duplicate_replays_leader_output(tmp_path: Path) -> None:
    counter = tmp_path / "counter.txt"
    state = tmp_path / "state"
    command = _counter_command(counter, sleep_s=0.8)
    base = [
        sys.executable,
        "-m",
        "microcosm_core.engine_room.command_run_singleflight",
        "run",
        "--state-root",
        str(state),
        "--cwd",
        str(tmp_path),
        "--json",
        "--",
        *command,
    ]
    env = {"PYTHONPATH": str(ROOT / "src")}
    first = subprocess.Popen(base, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE)
    second = subprocess.Popen(base, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE)
    first_stdout, _ = first.communicate(timeout=10)
    second_stdout, _ = second.communicate(timeout=10)
    assert first.returncode == 0
    assert second.returncode == 0
    receipts = [json.loads(first_stdout), json.loads(second_stdout)]
    assert {receipt["role"] for receipt in receipts} == {"leader", "follower"}
    assert len({receipt["run_id"] for receipt in receipts}) == 1
    assert counter.read_text(encoding="utf-8") == "1"
    assert all("counter=1" in receipt["stdout"] for receipt in receipts)


def test_active_run_timeout_refuses_duplicate_without_rerun(tmp_path: Path) -> None:
    counter = tmp_path / "counter.txt"
    state = tmp_path / "state"
    command = _counter_command(counter)
    key = build_command_key(
        argv=command,
        cwd=tmp_path,
        resource_class="command",
    )
    key_hash = _short_hash(key)
    run_id = "cmdrun_stuck_public_fixture"
    active = _metadata(
        key_hash=key_hash,
        run_id=run_id,
        key=key,
        resource_class="command",
        owner_surface="unit_test_stale_active",
    )
    _write_json(_paths(state, key_hash, run_id)["active"], {**active, "pid": os.getpid()})

    receipt = run_command_singleflight(
        command,
        state_root=state,
        cwd=tmp_path,
        wait_timeout_s=0.01,
    )

    assert receipt.role == "follower"
    assert receipt.status == "stale_or_timeout"
    assert receipt.exit_code == 124
    assert "active run did not complete before timeout" in receipt.stderr
    assert not counter.exists()


def test_missing_command_is_rejected(tmp_path: Path) -> None:
    try:
        run_command_singleflight([], state_root=tmp_path / "state", cwd=tmp_path)
    except ValueError as exc:
        assert "argv must not be empty" in str(exc)
    else:
        raise AssertionError("missing command was accepted")


def test_fixture_matrix_matches_singleflight_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 4
    assert receipt["passed_case_count"] == 4
    assert receipt["source_to_target_relation"] == "source_faithful_public_refactor"
    assert "not_a_job_scheduler" in ANTI_CLAIMS
    assert "not a job scheduler" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.command_run_singleflight",
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
    assert payload["organ_id"] == "engine_room_command_run_singleflight"
    assert payload["status"] == "pass"
