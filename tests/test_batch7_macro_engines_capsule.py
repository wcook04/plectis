from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.batch7_macro_engines_capsule as batch7
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch7_macro_engines_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch7_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch7_macro_engines_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch7_macro_engines_capsule/exported_batch7_macro_engines_capsule_bundle"
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
    input_dir.mkdir(parents=True, exist_ok=True)
    for case_id in EXPECTED_NEGATIVE_CASES:
        (input_dir / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "status": "blocked",
                    "error_codes": ["DECLARED_BOGUS_NEGATIVE_CODE"],
                    "body_in_receipt": False,
                }
            ),
            encoding="utf-8",
        )


def _semantic_runtime_fixture(
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {
        "agent_trace_ir_compiler": {
            "status": "pass",
            "engine_id": "agent_trace_ir_compiler",
            "edit_claim_gate": "covered_by_parser_test_commit_without_diff_case",
            "original_witness": {"status": "pass"},
        },
        "codemap_orbit_layout": {
            "status": "pass",
            "engine_id": "codemap_orbit_layout",
            "zero_overlap": True,
        },
        "constitutional_dag_kernel": {
            "status": "pass",
            "engine_id": "constitutional_dag_kernel",
            "cycle_rejected": True,
        },
        "release_root_compiler": {
            "status": "pass",
            "engine_id": "release_root_compiler",
            "bad_ref_negative_covered": True,
        },
        "source_surgeon_patch": {
            "status": "pass",
            "engine_id": "source_surgeon_patch",
            "context_mismatch_rejected": True,
        },
        "hermetic_clean_clone": {
            "status": "pass",
            "engine_id": "hermetic_clean_clone",
            "network_blocked": True,
        },
        "calculator_standard_actor": {
            "status": "pass",
            "engine_id": "calculator_standard_actor",
            "outlier_resisted": True,
        },
        "personalized_pagerank_ranker": {
            "status": "pass",
            "engine_id": "personalized_pagerank_ranker",
            "missing_source_refused": True,
        },
        "regression_test_selection": {
            "status": "pass",
            "engine_id": "regression_test_selection",
            "fallback_test_count": 1,
        },
    }
    for engine_id, patch in (overrides or {}).items():
        rows[engine_id].update(patch)
    return rows


@pytest.fixture(scope="module")
def capsule_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("batch7_macro_engines_capsule")
    return run(
        FIXTURE_INPUT,
        root / "receipts/first_wave/batch7_macro_engines_capsule",
        acceptance_out=root
        / "receipts/acceptance/first_wave/batch7_macro_engines_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch7_macro_engines_capsule_runs_all_engines(
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
    assert by_engine["agent_trace_ir_compiler"]["original_witness"]["returncode"] == 0
    assert by_engine["agent_trace_ir_compiler"]["original_witness"]["body_in_receipt"] is False
    assert by_engine["agent_trace_ir_compiler"]["public_fixture_policy"] == "synthetic_transcripts_only"
    assert by_engine["codemap_orbit_layout"]["original_witness"]["returncode"] == 0
    assert by_engine["codemap_orbit_layout"]["zero_overlap"] is True
    assert by_engine["constitutional_dag_kernel"]["cycle_rejected"] is True
    assert by_engine["constitutional_dag_kernel"]["impure_path_flagged"] is True
    assert by_engine["release_root_compiler"]["bad_ref_negative_covered"] is True
    assert by_engine["release_root_compiler"]["function_count"] >= 50
    assert set(by_engine["release_root_compiler"]["required_functions_present"]) == {
        "build_release_root_compiler",
        "build_std_python_report",
    }
    assert by_engine["source_surgeon_patch"]["context_mismatch_rejected"] is True
    assert by_engine["source_surgeon_patch"]["syntax_error_blocked"] is True
    assert by_engine["hermetic_clean_clone"]["network_blocked"] is True
    assert "redaction scan" in by_engine["hermetic_clean_clone"]["private_marker_policy"]
    assert by_engine["calculator_standard_actor"]["outlier_resisted"] is True
    assert by_engine["calculator_standard_actor"]["dependency_versions"]["numpy"]
    assert by_engine["calculator_standard_actor"]["naive_mean"] > 19.0
    assert by_engine["personalized_pagerank_ranker"]["mass"] == 1.0
    assert by_engine["personalized_pagerank_ranker"]["missing_source_refused"] is True
    assert by_engine["regression_test_selection"]["fallback_used"] is True
    assert by_engine["regression_test_selection"]["fallback_test_count"] > 0
    assert result["body_in_receipt"] is False


def test_batch7_macro_engines_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch7_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_macro_engines_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch7_macro_engines_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] >= 15
    assert result["exercise"]["copied_macro_source_module_count"] >= 15
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch7_macro_engines_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] >= 15

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


def test_batch7_macro_engines_card_omits_private_bodies(
    capsule_result: dict[str, Any],
) -> None:
    result = capsule_result
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["copied_macro_source_module_count"] >= 15
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)


def test_batch7_macro_engines_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch7_common_negative_cases_ignore_declared_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        batch7,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(),
    )

    result = validate_negative_cases(
        tmp_path,
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


def test_batch7_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        batch7,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {"source_surgeon_patch": {"context_mismatch_rejected": False}}
        ),
    )

    result = validate_negative_cases(
        tmp_path,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "blocked"
    assert "source_surgeon_context_mismatch" in result["missing_negative_cases"]
    assert "BATCH7_SOURCE_SURGEON_CONTEXT_MISMATCH" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors


def test_batch7_numeric_dependencies_are_declared() -> None:
    project = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    test_deps = project["project"]["optional-dependencies"]["test"]

    assert any(dep.startswith("numpy") for dep in test_deps)
    assert any(dep.startswith("pandas") for dep in test_deps)
