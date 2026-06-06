from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs import batch8_compliance_pipeline_capsule as capsule_module
from microcosm_core.organs.batch8_compliance_pipeline_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch8_compliance_pipeline_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch8_compliance_pipeline_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch8_compliance_pipeline_capsule/exported_batch8_compliance_pipeline_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"
STAGE_EXTRACT_REF = "system/lib/pipeline/stage_extract.py"
DIRECTIVE_HEURISTIC_TOKEN = '"need to", "should ", "must ", "the entire point", "the critical"'
DROPPED_DIRECTIVE_HEURISTIC_TOKEN = (
    '"removed_need_to", "should ", "must ", "the entire point", "the critical"'
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_exported_bundle_to_temp_public_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    bundle = (
        public_root
        / "examples/batch8_compliance_pipeline_capsule/"
        "exported_batch8_compliance_pipeline_capsule_bundle"
    )
    bundle.parent.mkdir(parents=True)
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    policy_target = public_root / "core/private_state_forbidden_classes.json"
    policy_target.parent.mkdir(parents=True)
    shutil.copy2(
        MICROCOSM_ROOT / "core/private_state_forbidden_classes.json",
        policy_target,
    )
    return bundle


def _refresh_temp_manifest_row(bundle: Path, source_ref: str) -> None:
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["modules"]:
        if row["source_ref"] != source_ref:
            continue
        target = bundle / row["path"]
        digest = _sha256(target)
        row["sha256"] = digest
        row["source_sha256"] = digest
        row["target_sha256"] = digest
        row["byte_count"] = target.stat().st_size
        row["line_count"] = len(target.read_text(encoding="utf-8").splitlines())
        row["sha256_match"] = True
        break
    else:  # pragma: no cover - fixture manifest shape is asserted elsewhere.
        raise AssertionError(f"missing source_ref {source_ref}")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    root = tmp_path_factory.mktemp("batch8_compliance_pipeline_capsule")
    return run(
        FIXTURE_INPUT,
        root / "receipts/first_wave/batch8_compliance_pipeline_capsule",
        acceptance_out=root
        / "receipts/acceptance/first_wave/batch8_compliance_pipeline_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch8_compliance_pipeline_capsule_runs_all_engines(
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
    assert by_engine["compliance_registry_runtime_witness"]["adapter_count"] >= 190
    assert by_engine["compliance_coverage_bounded_check"]["check_status"] == "ok"
    assert by_engine["compliance_coverage_bounded_check"]["wrote_ledger"] is False
    assert by_engine["baseline_companion_scanner_contract"]["coverage_row_kind"] == "baseline_inventory_only"
    assert by_engine["pipeline_digest_and_shard_normalization"]["status_variant_preserved"] is True
    assert by_engine["pipeline_observe_compile_helpers"]["probe_questions"] == [
        "What pipeline helper is next?",
        "Which compliance scanner is missing?",
    ]
    assert by_engine["pipeline_dispatch_process_boundary_contract"]["dispatch_boundary_present"] is True
    assert result["body_in_receipt"] is False


def test_batch8_compliance_pipeline_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch8_compliance_pipeline_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch8_compliance_pipeline_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch8_compliance_pipeline_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] >= 11
    assert result["exercise"]["copied_macro_source_module_count"] >= 11
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch8_compliance_pipeline_bundle_uses_standalone_witness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_public_witness(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("exported bundle validation should not shell out to parent repo")

    monkeypatch.setattr(capsule_module, "_run_public_witness", fail_public_witness)

    result = run_batch8_compliance_pipeline_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch8_compliance_pipeline_capsule",
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "pass"
    assert (
        by_engine["compliance_registry_runtime_witness"]["witness_mode"]
        == "standalone_copied_source_contract"
    )
    assert (
        by_engine["compliance_coverage_bounded_check"]["original_witness"][
            "witness_mode"
        ]
        == "standalone_copied_source_contract"
    )
    assert by_engine["compliance_coverage_bounded_check"]["wrote_ledger"] is False
    assert (
        by_engine["baseline_companion_scanner_contract"]["scan_input_mode"]
        == "standalone_copied_source_contract"
    )


def test_batch8_compliance_exported_bundle_rejects_dropped_digest_directive(
    tmp_path: Path,
) -> None:
    bundle = _copy_exported_bundle_to_temp_public_root(tmp_path)
    copied_stage_extract = bundle / f"source_modules/{STAGE_EXTRACT_REF}"
    text = copied_stage_extract.read_text(encoding="utf-8")
    assert DIRECTIVE_HEURISTIC_TOKEN in text
    copied_stage_extract.write_text(
        text.replace(DIRECTIVE_HEURISTIC_TOKEN, DROPPED_DIRECTIVE_HEURISTIC_TOKEN),
        encoding="utf-8",
    )
    _refresh_temp_manifest_row(bundle, STAGE_EXTRACT_REF)

    result = run_batch8_compliance_pipeline_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch8_wrong_input",
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}
    digest_engine = by_engine["pipeline_digest_and_shard_normalization"]

    assert result["status"] == "blocked"
    assert digest_engine["status"] == "blocked"
    assert digest_engine["directive_preserved"] is False
    assert digest_engine["copied_source_anchors_present"] is True
    assert "digest_loses_directive" in result["observed_negative_cases"]
    assert result["missing_negative_cases"] == []
    assert any(
        row["error_code"] == "BATCH8_COMPLIANCE_PIPELINE_ENGINE_BLOCKED"
        and row["subject_id"] == "pipeline_digest_and_shard_normalization"
        for row in result["findings"]
    )


def test_batch8_compliance_pipeline_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] >= 11

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


def test_batch8_compliance_pipeline_card_omits_private_bodies(
    capsule_result: dict[str, Any],
) -> None:
    result = capsule_result
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["source_module_count"] >= 11
    assert card["body_in_receipt"] is False
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": "real_substrate_capsule",
        "release_authorized": False,
        "publication_authorized": False,
        "provider_dispatch": False,
        "model_dispatch": False,
        "source_mutation_authorized": False,
        "raw_seed_mutation_authorized": False,
        "full_compliance_ledger_freshness_claim": False,
        "full_pipeline_dispatch_authority": False,
        "test_completeness_proof": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)


def test_batch8_compliance_pipeline_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch8_compliance_common_negative_cases_ignore_declared_codes(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    shutil.copytree(FIXTURE_INPUT, input_dir)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = input_dir / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["DECLARED_FIXTURE_CODE_SHOULD_NOT_WIN"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    echo_result = validate_negative_cases(input_dir, EXPECTED_NEGATIVE_CASES)
    assert echo_result["status"] == "blocked"
    assert echo_result["observed_negative_cases"] == []

    semantic_result = validate_negative_cases(
        input_dir,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=lambda case_id, _input_dir, _expected: {
            "status": "blocked",
            "error_codes": list(EXPECTED_NEGATIVE_CASES[case_id]),
            "body_in_receipt": False,
        },
    )
    assert semantic_result["status"] == "pass"
    assert semantic_result["semantic_evaluator_used"] is True
    assert set(semantic_result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_batch8_compliance_semantic_negative_cases_move_with_runtime_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moved_case = "bounded_check_failed"

    def fake_runtime(_input_ref: str) -> dict[str, Any]:
        return {
            "negative_exercises": {
                case_id: {
                    "status": "blocked",
                    "negative_condition_observed": case_id != moved_case,
                    "body_in_receipt": False,
                }
                for case_id in EXPECTED_NEGATIVE_CASES
            }
        }

    monkeypatch.setattr(capsule_module, "_semantic_runtime_exercises", fake_runtime)

    moved = evaluate_negative_case(
        moved_case,
        FIXTURE_INPUT,
        EXPECTED_NEGATIVE_CASES[moved_case],
    )
    assert moved["status"] == "pass"
    assert moved["error_codes"] == []

    result = validate_negative_cases(
        FIXTURE_INPUT,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )
    assert result["status"] == "blocked"
    assert moved_case in result["missing_negative_cases"]
