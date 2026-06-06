from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from microcosm_core.organs.engine_room_demo import (
    ACCEPTANCE_RECEIPT_NAME,
    BOARD_NAME,
    RESULT_NAME,
    VALIDATION_RECEIPT_NAME,
    build_result,
    run,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "fixtures/first_wave/engine_room_demo/input"


def _fast_cli_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "positive_controller_audit.json").write_text(
        json.dumps(
            {
                "case_id": "positive_controller_audit",
                "case_type": "positive",
                "run_exercises": False,
            }
        ),
        encoding="utf-8",
    )
    (input_dir / "missing_expected_target_negative.json").write_text(
        (INPUT / "missing_expected_target_negative.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return input_dir


def _copy_engine_room_demo_root(tmp_path: Path) -> Path:
    root = tmp_path / "microcosm-root"
    root.mkdir()
    shutil.copytree(ROOT / "fixtures" / "first_wave", root / "fixtures" / "first_wave")
    for name in ("core", "paper_modules", "src", "standards", "tests"):
        (root / name).symlink_to(ROOT / name, target_is_directory=True)
    return root


def _positive_controller_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "positive-input"
    input_dir.mkdir()
    (input_dir / "positive_controller_audit.json").write_text(
        (INPUT / "positive_controller_audit.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return input_dir


def test_engine_room_demo_organ_observes_positive_and_negative_cases() -> None:
    result = build_result(INPUT)
    assert result["status"] == "pass"
    assert result["expected_jewel_count"] == 14
    assert result["positive_case_count"] == 1
    assert result["negative_case_count"] == 1
    assert result["observed_negative_case_count"] == 1
    serialized = json.dumps(result, sort_keys=True)
    assert str(ROOT) not in serialized
    assert "/Users/" not in serialized
    assert all(row["fixture_ref"].startswith("fixtures/") for row in result["cases"])


def test_engine_room_demo_negative_case_is_semantic_not_answer_key(tmp_path: Path) -> None:
    fixture_path = INPUT / "missing_expected_target_negative.json"
    original = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert "expected_error_code" not in original

    result = build_result(INPUT)
    negative = next(
        row for row in result["cases"] if row["case_id"] == "missing_expected_target_negative"
    )
    assert negative["status"] == "fail"
    assert negative["observed_error_codes"] == ["ENGINE_ROOM_EXPECTED_TARGET_MISSING"]
    assert "engine_room_target_that_should_not_exist" in negative["missing_jewel_targets"]

    moving_input = _fast_cli_input(tmp_path)
    valid_target_case = dict(original)
    valid_target_case["expected_jewel_targets"] = ["lean_and_or_proof_search"]
    (moving_input / "missing_expected_target_negative.json").write_text(
        json.dumps(valid_target_case, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    moved = build_result(moving_input)
    moved_negative = next(
        row for row in moved["cases"] if row["case_id"] == "missing_expected_target_negative"
    )
    assert moved_negative["status"] == "pass"
    assert moved_negative["observed_error_codes"] == []
    assert moved["observed_negative_case_count"] == 0
    assert moved["status"] == "fail"


def test_engine_room_demo_organ_composition_fails_when_real_subcapsule_fixture_mutates(
    tmp_path: Path,
) -> None:
    root = _copy_engine_room_demo_root(tmp_path)
    input_dir = _positive_controller_input(tmp_path)
    baseline = build_result(input_dir, root=root)
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

    mutated = build_result(input_dir, root=root)
    positive = next(
        row for row in mutated["cases"] if row["case_id"] == "positive_controller_audit"
    )
    failed = positive["failed_subcapsules"]
    assert mutated["status"] == "fail"
    assert positive["status"] == "fail"
    assert positive["controller_completion_status"] == "staged_capsules_incomplete"
    assert positive["observed_error_codes"] == ["ENGINE_ROOM_SUBCAPSULE_COMPOSITION_FAILED"]
    assert positive["failed_subcapsule_count"] == 1
    assert failed[0]["capsule_id"] == "engine_room_command_run_singleflight"
    assert failed[0]["summary"]["passed_case_count"] == failed[0]["summary"]["case_count"] - 1


def test_engine_room_demo_organ_writes_receipts(tmp_path: Path) -> None:
    acceptance = tmp_path / ACCEPTANCE_RECEIPT_NAME
    result = run(INPUT, tmp_path, acceptance_out=acceptance)
    assert result["status"] == "pass"
    for name in (RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME):
        assert (tmp_path / name).is_file()
    assert acceptance.is_file()
    payload = json.loads(acceptance.read_text(encoding="utf-8"))
    assert payload["organ_id"] == "engine_room_demo"
    assert payload["real_substrate_disposition"] == "real_substrate_capsule"


def test_engine_room_demo_organ_cli_writes_acceptance(tmp_path: Path) -> None:
    out = tmp_path / "receipts"
    acceptance = tmp_path / ACCEPTANCE_RECEIPT_NAME
    input_dir = _fast_cli_input(tmp_path)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.engine_room_demo",
            "run",
            "--input",
            str(input_dir),
            "--out",
            str(out),
            "--acceptance-out",
            str(acceptance),
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
    assert payload["status"] == "pass"
    assert (out / RESULT_NAME).is_file()
    assert acceptance.is_file()
