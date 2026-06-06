from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.batch7_demo_take_console_capsule as capsule_module
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch7_demo_take_console_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch7_demo_take_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch7_demo_take_console_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch7_demo_take_console_capsule/exported_batch7_demo_take_console_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _write_negative_case_fixtures(input_dir: Path) -> None:
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = input_dir / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        payload.update(
            {
                "case_id": case_id,
                "error_codes": ["DECLARED_BOGUS_NEGATIVE_CODE"],
                "body_in_receipt": False,
            }
        )
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _semantic_runtime_fixture(
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = {
        "missing_helper_bridge": {
            "status": "blocked",
            "mutation_applied": True,
            "helper_script_bound_to_repo": False,
        },
        "start_without_screen": {
            "status": "blocked",
            "mutation_applied": True,
            "start_gate_requires_screen_and_disk": False,
        },
        "hotkey_wrong_modifier": {
            "status": "blocked",
            "mutation_applied": True,
            "hotkey_requires_control_option_command_m": False,
        },
        "audio_meter_unclamped": {
            "status": "blocked",
            "mutation_applied": True,
            "audio_meter_permission_device_and_clamp_present": False,
        },
        "transcribe_missing_audio": {
            "status": "blocked",
            "mutation_applied": True,
            "missing_audio_guard_present": False,
        },
        "missing_swift_build_witness": {
            "status": "blocked",
            "swift_build_witness_required": True,
        },
    }
    if overrides:
        for case_id, patch in overrides.items():
            cases[case_id].update(patch)
    return {"negative_exercises": cases, "body_in_receipt": False}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def test_batch7_demo_take_console_capsule_runs_all_engines(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch7_demo_take_console_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch7_demo_take_console_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["engine_count"] == len(EXPECTED_ENGINES)
    assert set(exercise["engine_ids"]) == set(EXPECTED_ENGINES)
    assert all(row["status"] == "pass" for row in exercise["engines"])

    by_engine = {row["engine_id"]: row for row in exercise["engines"]}
    assert by_engine["demo_take_swiftpm_build_witness"]["original_witness"]["returncode"] == 0
    assert by_engine["recording_state_control_model"]["recording_state_count"] == 11
    assert by_engine["capture_helper_bridge_contract"]["helper_command_count"] >= 11
    assert by_engine["capture_helper_bridge_contract"]["repo_python_fallback_present"] is True
    assert by_engine["recorder_store_capture_fsm"]["start_gate_requires_screen_and_disk"] is True
    assert by_engine["recorder_store_capture_fsm"]["screen_prompt_guard_present"] is True
    assert by_engine["hotkey_audio_meter_contract"]["audio_meter_permission_device_and_clamp_present"] is True
    assert by_engine["transcribe_payload_builder"]["missing_audio_guard_present"] is True
    assert result["body_in_receipt"] is False


def test_batch7_demo_take_console_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch7_demo_take_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_demo_take_console_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch7_demo_take_console_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] >= 8
    assert result["exercise"]["copied_macro_source_module_count"] >= 8
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch7_demo_take_console_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] >= 8

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch7_demo_take_console_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch7_demo_take_console_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["source_module_count"] >= 8
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)


def test_batch7_demo_take_console_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch7_demo_take_common_negative_cases_ignore_declared_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(MICROCOSM_ROOT)
    input_dir = tmp_path / "input"
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _write_negative_case_fixtures(input_dir)

    result = validate_negative_cases(
        input_dir,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "DECLARED_BOGUS_NEGATIVE_CODE" not in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch7_demo_take_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(FIXTURE_INPUT, tmp_path / "input")
    monkeypatch.setattr(
        capsule_module,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {
                "start_without_screen": {
                    "status": "pass",
                    "start_gate_requires_screen_and_disk": True,
                }
            }
        ),
    )

    result = validate_negative_cases(
        tmp_path / "input",
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "blocked"
    assert "start_without_screen" in result["missing_negative_cases"]
    assert "BATCH7_DEMO_TAKE_START_SCREEN_GATE_REQUIRED" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors
