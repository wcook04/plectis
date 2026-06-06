from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs import batch10_cold_eval_honesty_capsule as capsule_module
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch10_cold_eval_honesty_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch10_cold_eval_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch10_cold_eval_honesty_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch10_cold_eval_honesty_capsule/exported_batch10_cold_eval_honesty_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


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


def _write_negative_case_fixtures(input_dir: Path) -> None:
    mutation_specs = {
        "missing_tasks": {
            "kind": "remove_file",
            "path": "cold_eval_workspace/evals/cold_agent_ab/tasks.json",
        },
        "flat_route_can_win": {
            "expected_refs": [
                "README.md",
                "docs/quickstart.md",
                "pyproject.toml",
            ],
            "kind": "rewrite_tasks_route_refs",
            "path": "cold_eval_workspace/evals/cold_agent_ab/tasks.json",
            "route_source_summary": {
                "flat_route_ref_count": 3,
                "idea_route_ref_count": 3,
            },
        },
        "expected_ref_injection": {
            "field": "expected_ref_injection_allowed",
            "kind": "set_manifest_field",
            "path": "batch10_cold_eval_exercise_manifest.json",
            "value": True,
        },
        "private_fixture_ref": {
            "kind": "inject_private_fixture_probe",
            "path": "cold_eval_workspace/evals/cold_agent_ab/tasks.json",
        },
    }
    input_dir.mkdir(parents=True, exist_ok=True)
    for case_id in EXPECTED_NEGATIVE_CASES:
        (input_dir / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "status": "blocked",
                    "error_codes": ["DECLARED_BOGUS_NEGATIVE_CODE"],
                    "body_in_receipt": False,
                    "schema_version": "batch10_cold_eval_workspace_mutation_negative_case_v1",
                    "workspace_mutation": mutation_specs[case_id],
                }
            ),
            encoding="utf-8",
        )


def _semantic_runtime_fixture(
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    negative_exercises: dict[str, dict[str, Any]] = {
        "missing_tasks": {
            "status": "blocked",
            "engines": [
                {
                    "engine_id": "cold_eval_original_runner",
                    "status": "blocked",
                    "error_code": "BATCH10_COLD_EVAL_TASKS_REQUIRED",
                }
            ],
        },
        "flat_route_can_win": {
            "status": "blocked",
            "engines": [
                {
                    "engine_id": "cold_eval_original_runner",
                    "status": "blocked",
                    "flat_repo_win_count": 3,
                },
                {
                    "engine_id": "cold_eval_scorecard_shape_audit",
                    "status": "blocked",
                    "all_winners_are_idea_first": False,
                    "route_surface_asymmetry_visible": False,
                },
            ],
        },
        "expected_ref_injection": {
            "status": "blocked",
            "engines": [
                {
                    "engine_id": "cold_eval_claim_ceiling_gate",
                    "status": "blocked",
                    "expected_ref_injection_allowed": True,
                }
            ],
        },
        "private_fixture_ref": {
            "status": "blocked",
            "engines": [
                {
                    "engine_id": "cold_eval_scorecard_shape_audit",
                    "status": "blocked",
                    "private_fixture_ref_count": 1,
                }
            ],
        },
    }
    for case_id, patch in (overrides or {}).items():
        negative_exercises[case_id].update(patch)
    return {
        "source_manifest": {"module_count": 1},
        "exercise": {"engines": []},
        "negative_exercises": negative_exercises,
    }


def _copy_exported_bundle(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch10_cold_eval_honesty_capsule/"
        "exported_batch10_cold_eval_honesty_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    return public_root, bundle


def _run_copied_bundle(public_root: Path, bundle: Path) -> dict[str, Any]:
    return run_batch10_cold_eval_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_cold_eval_honesty_capsule",
        command="pytest",
    )


def _engines(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["engine_id"]: row for row in result["exercise"]["engines"]}


def test_batch10_cold_eval_honesty_capsule_runs_real_runner(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_cold_eval_honesty_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch10_cold_eval_honesty_capsule_fixture_acceptance.json",
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
    assert by_engine["cold_eval_original_runner"]["result_status"] == "ok"
    assert by_engine["cold_eval_original_runner"]["idea_first_win_count"] == 3
    assert by_engine["cold_eval_scorecard_shape_audit"]["all_winners_are_idea_first"] is True
    assert by_engine["cold_eval_scorecard_shape_audit"]["route_surface_asymmetry_visible"] is True
    assert by_engine["cold_eval_claim_ceiling_gate"]["expected_ref_injection_allowed"] is False
    assert result["body_in_receipt"] is False


def test_batch10_cold_eval_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch10_cold_eval_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch10_cold_eval_honesty_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch10_cold_eval_honesty_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["copied_macro_source_module_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_cold_eval_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _run_copied_bundle(public_root, bundle)

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_cold_eval_source_module_is_exact_macro_body_import() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1

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


def test_batch10_cold_eval_rejects_missing_tasks_file(tmp_path: Path) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    (
        bundle
        / "cold_eval_workspace/evals/cold_agent_ab/tasks.json"
    ).unlink()

    result = _run_copied_bundle(public_root, bundle)
    original_runner = _engines(result)["cold_eval_original_runner"]

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert original_runner["status"] == "blocked"
    assert original_runner["error_code"] == "BATCH10_COLD_EVAL_TASKS_REQUIRED"
    assert "BATCH10_COLD_EVAL_TASKS_REQUIRED" in result["error_codes"]
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_cold_eval_rejects_expected_ref_injection_claim(tmp_path: Path) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    manifest_path = bundle / "batch10_cold_eval_exercise_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_ref_injection_allowed"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = _run_copied_bundle(public_root, bundle)
    claim_gate = _engines(result)["cold_eval_claim_ceiling_gate"]

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert claim_gate["status"] == "blocked"
    assert claim_gate["expected_ref_injection_allowed"] is True
    assert "BATCH10_COLD_EVAL_ENGINE_BLOCKED" in result["error_codes"]
    assert "BATCH10_COLD_EVAL_EXPECTED_REF_INJECTION_FORBIDDEN" in result[
        "error_codes"
    ]
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_cold_eval_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_cold_eval_honesty_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["source_module_count"] == 1
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)


def test_batch10_cold_eval_negative_cases_are_executed_mutation_specs() -> None:
    allowed_kinds = {
        "inject_private_fixture_probe",
        "remove_file",
        "rewrite_tasks_route_refs",
        "set_manifest_field",
    }
    allowed_paths = {
        "batch10_cold_eval_exercise_manifest.json",
        "cold_eval_workspace/evals/cold_agent_ab/tasks.json",
    }
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["body_in_receipt"] is False
        assert payload["case_id"] == case_id
        assert payload["schema_version"] == "batch10_cold_eval_workspace_mutation_negative_case_v1"
        assert "status" not in payload
        assert "error_codes" not in payload
        mutation = payload["workspace_mutation"]
        assert mutation["kind"] in allowed_kinds
        assert mutation["path"] in allowed_paths
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)
        assert result["status"] == "blocked"
        assert result["error_codes"] == list(expected_codes)


def test_batch10_common_negative_cases_ignore_declared_codes(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch10_cold_eval_honesty_capsule",
        public_root / "examples/batch10_cold_eval_honesty_capsule",
    )
    input_dir = (
        public_root
        / "fixtures/first_wave/batch10_cold_eval_honesty_capsule/input"
    )
    input_dir.parent.mkdir(parents=True, exist_ok=True)
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


def test_batch10_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        capsule_module,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {
                "flat_route_can_win": {
                    "status": "pass",
                    "engines": [
                        {
                            "engine_id": "cold_eval_original_runner",
                            "status": "pass",
                            "flat_repo_win_count": 0,
                        },
                        {
                            "engine_id": "cold_eval_scorecard_shape_audit",
                            "status": "pass",
                            "all_winners_are_idea_first": True,
                            "route_surface_asymmetry_visible": True,
                        },
                    ],
                }
            }
        ),
    )

    result = validate_negative_cases(
        tmp_path,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "blocked"
    assert "flat_route_can_win" in result["missing_negative_cases"]
    assert "BATCH10_COLD_EVAL_NOT_ALWAYS_B_WIN" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors
