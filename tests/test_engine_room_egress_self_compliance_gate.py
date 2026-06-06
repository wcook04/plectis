from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.egress_self_compliance_gate import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    evaluate_fixture_dir,
    evaluate_text,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_egress_self_compliance_gate/input"


def test_permission_gate_without_blocker_is_red() -> None:
    receipt = evaluate_text("The tests passed. Let me know if you want me to continue.")
    assert receipt["status"] == "red"
    assert receipt["rows"][0]["diagnostic_id"] == "permission_gate_without_blocker"


def test_permission_gate_with_real_blocker_is_green() -> None:
    receipt = evaluate_text(
        "Should I proceed? I am stopping before a remote push due to the publication boundary."
    )
    assert receipt["status"] == "green"
    assert receipt["rows"][0]["violation"] is False


def test_self_error_requires_durable_capture_binding() -> None:
    assert evaluate_text("My mistake: I miscounted the rows.")["status"] == "red"
    assert evaluate_text("My mistake is captured in cap_quick_demo_self_error.")["status"] == "green"


def test_command_displacement_requires_execution_receipt() -> None:
    assert evaluate_text("You can run make smoke next.")["status"] == "red"
    assert evaluate_text("I ran make smoke and it passed with exit code 0.")["status"] == "green"


def test_fixture_matrix_matches_red_and_green_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 6
    assert receipt["passed_case_count"] == 6
    assert "not_taint_analysis" in ANTI_CLAIMS
    assert "not taint analysis" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.egress_self_compliance_gate",
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
    assert payload["organ_id"] == "engine_room_egress_self_compliance_gate"
    assert payload["status"] == "pass"
