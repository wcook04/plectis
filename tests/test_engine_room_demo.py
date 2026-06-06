from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.demo import CAPSULES, audit_controller_coverage, run_demo


ROOT = Path(__file__).resolve().parents[1]


def _copy_first_wave_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "microcosm-root"
    shutil.copytree(ROOT / "fixtures" / "first_wave", root / "fixtures" / "first_wave")
    return root


def test_demo_inventory_covers_all_engine_room_targets() -> None:
    target_ids = {target for capsule in CAPSULES for target in capsule.jewel_targets}
    assert len(CAPSULES) == 10
    assert len(target_ids) == 14
    assert "lean_and_or_proof_search" in target_ids
    assert "metabolism_reconciler" in target_ids
    assert "annex_knowledge_router" in target_ids


def test_demo_runner_executes_staged_capsules_without_shared_registry_mutation() -> None:
    receipt = run_demo(root=ROOT)
    assert receipt["status"] == "pass"
    assert receipt["capsule_count"] == 10
    assert receipt["passed_capsule_count"] == 10
    assert receipt["covered_jewel_count"] == 14
    assert receipt["shared_registry_mutated"] is False


def test_demo_runner_composition_flips_when_sub_capsule_fixture_input_changes(tmp_path: Path) -> None:
    root = _copy_first_wave_fixture_root(tmp_path)
    baseline = run_demo(root=root)
    assert baseline["status"] == "pass"

    fixture = (
        root
        / "fixtures"
        / "first_wave"
        / "engine_room_command_run_singleflight"
        / "input"
        / "single_leader.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["expected_ok"] = False
    fixture.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    mutated = run_demo(root=root)
    command_row = next(
        row
        for row in mutated["rows"]
        if row["capsule_id"] == "engine_room_command_run_singleflight"
    )
    assert mutated["status"] == "fail"
    assert mutated["passed_capsule_count"] == mutated["capsule_count"] - 1
    assert command_row["status"] == "fail"
    assert command_row["summary"]["status"] == "fail"
    assert command_row["summary"]["passed_case_count"] == command_row["summary"]["case_count"] - 1


def test_demo_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.demo",
            "run",
            "--root",
            str(ROOT),
            "--capsule-id",
            "engine_room_command_run_singleflight",
            "--json",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["organ_id"] == "engine_room_demo"
    assert payload["status"] == "pass"
    assert payload["capsule_count"] == 1
    assert payload["covered_jewel_count"] == 1
    assert payload["covered_jewel_targets"] == ["command_run_singleflight"]


def test_controller_audit_verifies_staged_surfaces_and_names_shared_gap() -> None:
    receipt = audit_controller_coverage(root=ROOT)
    assert receipt["status"] == "pass"
    assert receipt["expected_jewel_count"] == 14
    assert receipt["covered_jewel_count"] == 14
    assert receipt["missing_jewel_targets"] == []
    assert receipt["unexpected_jewel_targets"] == []
    assert receipt["missing_surface_capsule_count"] == 0
    assert receipt["shared_registry_mutated"] is False
    assert receipt["shared_integration_status"] in {"pending", "integrated"}
    if receipt["shared_integration_status"] == "pending":
        assert receipt["controller_completion_status"] == "staged_capsules_pass_shared_integration_pending"
    else:
        assert receipt["controller_completion_status"] == "staged_capsules_pass_shared_registry_integrated"


def test_controller_audit_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.demo",
            "audit",
            "--root",
            str(ROOT),
            "--skip-exercises",
            "--json",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "engine_room_controller_audit_v1"
    assert payload["status"] == "pass"
    assert payload["covered_jewel_count"] == 14
    assert payload["demo_receipt"] is None
