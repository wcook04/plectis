from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.batch7_oracle_sibling_capsule as capsule_module
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch7_oracle_sibling_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch7_oracle_sibling_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch7_oracle_sibling_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch7_oracle_sibling_capsule/exported_batch7_oracle_sibling_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _module_cli_env() -> dict[str, str]:
    # The documented public entry is `PYTHONPATH=src python3 -m microcosm_core`;
    # pytest's pythonpath config is process-local, so a bare sys.executable
    # subprocess only imports microcosm_core when a stale editable install
    # happens to exist. Pass the contract env explicitly.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MICROCOSM_ROOT / "src")
    return env


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
        "missing_subject_run_dir": {
            "status": "blocked",
            "subject_run_dir_required": True,
        },
        "missing_artifact_id": {
            "status": "blocked",
            "artifact_id_required": True,
        },
        "macro_truth_run_missing": {
            "status": "blocked",
            "truth_run_dir_required": True,
        },
        "quartet_run_missing_excluded": {
            "status": "blocked",
            "run_missing_quartet_excluded": True,
            "godmode_engine_invoked": False,
        },
        "original_pytest_witness_required": {
            "status": "blocked",
            "original_pytest_witness_required": True,
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


@pytest.fixture(scope="module")
def capsule_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("batch7_oracle_sibling_capsule")
    return run(
        FIXTURE_INPUT,
        root / "receipts/first_wave/batch7_oracle_sibling_capsule",
        acceptance_out=root
        / "receipts/acceptance/first_wave/batch7_oracle_sibling_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch7_oracle_sibling_capsule_runs_oracle_substrate(
    capsule_result: dict[str, Any],
) -> None:
    result = capsule_result

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
    assert by_engine["oracle_subject_index_grounding_map"]["xom_has_stock_support"] is True
    assert by_engine["oracle_subject_index_grounding_map"]["tlt_stays_contextual"] is True
    assert by_engine["oracle_subject_snapshot_hydration"]["prediction_payload_hydrated"] is True
    assert by_engine["oracle_truth_diff_macro_series_delta"]["changed_series_ranked"] is True
    assert by_engine["oracle_truth_diff_macro_series_delta"]["new_series_detected"] is True
    assert by_engine["oracle_quartet_repair_alias_plan"]["run_missing_quartet_excluded"] is True
    assert by_engine["oracle_quartet_repair_alias_plan"]["godmode_engine_not_invoked"] is True
    witness = by_engine["oracle_original_pytest_witness"]["original_witness"]
    assert witness["returncode"] == 0
    assert witness["passed_test_count_observed"] >= 7
    assert result["body_in_receipt"] is False


def test_batch7_oracle_sibling_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch7_oracle_sibling_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_oracle_sibling_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch7_oracle_sibling_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] >= 6
    assert result["exercise"]["copied_macro_source_module_count"] >= 6
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch7_oracle_sibling_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] >= 6
    assert manifest["public_safe_carveouts"] == []

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


def test_batch7_oracle_sibling_card_omits_private_bodies(
    capsule_result: dict[str, Any],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    result = capsule_result
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["original_pytest_witness_status"] == "pass"
    assert card["run_missing_quartet_excluded"] is True
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["body_in_receipt"] is False
    assert card["authority_floor"] == {
        "authority_ceiling": (
            "batch7_oracle_sibling_capsule_not_oracle_reasoning_or_provider_authority"
        ),
        "real_substrate_disposition": "real_substrate_capsule",
        "release_authorized": False,
        "publication_authorized": False,
        "provider_dispatch": False,
        "model_dispatch": False,
        "browser_or_wallet_access": False,
        "oracle_run_missing_authorized": False,
        "godmode_engine_invocation_authorized": False,
        "source_mutation_authorized": False,
        "operator_thread_authority": False,
        "semantic_truth_authority": False,
        "test_completeness_proof": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "original_pytest_stdout_in_receipt": False,
        "original_pytest_stderr_in_receipt": False,
        "source_bodies_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)

    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.batch7_oracle_sibling_capsule",
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(tmp_path_factory.mktemp("batch7_oracle_cli_fixture")),
            "--card",
        ],
        cwd=MICROCOSM_ROOT,
        env=_module_cli_env(),
        check=True,
        text=True,
        capture_output=True,
    )
    cli_card = json.loads(cli.stdout)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]

    bundle_cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.batch7_oracle_sibling_capsule",
            "validate-bundle",
            "--input",
            str(EXPORTED_BUNDLE),
            "--out",
            str(tmp_path_factory.mktemp("batch7_oracle_cli_bundle")),
            "--card",
        ],
        cwd=MICROCOSM_ROOT,
        env=_module_cli_env(),
        check=True,
        text=True,
        capture_output=True,
    )
    bundle_cli_card = json.loads(bundle_cli.stdout)
    assert bundle_cli_card["authority_floor"] == card["authority_floor"]
    assert bundle_cli_card["body_floor"] == card["body_floor"]


def test_batch7_oracle_sibling_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch7_oracle_common_negative_cases_ignore_declared_codes(
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


def test_batch7_oracle_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shutil.copytree(FIXTURE_INPUT, tmp_path / "input")
    monkeypatch.setattr(
        capsule_module,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {
                "macro_truth_run_missing": {
                    "status": "pass",
                    "truth_run_dir_required": False,
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
    assert "macro_truth_run_missing" in result["missing_negative_cases"]
    assert "BATCH7_ORACLE_TRUTH_RUN_REQUIRED" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors
