from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs import batch8_validator_checker_capsule as capsule_module
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch8_validator_checker_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch8_validator_checker_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch8_validator_checker_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch8_validator_checker_capsule/exported_batch8_validator_checker_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


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
) -> dict[str, Any]:
    engines = {
        "validator_source_anchor_matrix": {
            "status": "pass",
            "engine_id": "validator_source_anchor_matrix",
            "checker_failure_function_count": 31,
            "anchors_present": True,
            "release_gate_anchors_present": True,
        },
        "status_policy_judge_matrix": {
            "status": "pass",
            "engine_id": "status_policy_judge_matrix",
            "poisoned_policy_decision": "block",
            "forbidden_decision": "block",
            "transition_failure_count": 1,
        },
        "private_boundary_scanner_matrix": {
            "status": "pass",
            "engine_id": "private_boundary_scanner_matrix",
            "observed_patterns": ["private_email", "private_home_path"],
        },
        "specimen_checker_matrix": {
            "status": "pass",
            "engine_id": "specimen_checker_matrix",
            "checker_count": 6,
            "checkers": [
                {"checker": f"specimen_{idx}", "failure_count": 0}
                for idx in range(6)
            ],
        },
        "release_gate_checker_matrix": {
            "status": "pass",
            "engine_id": "release_gate_checker_matrix",
            "checker_count": 6,
            "checkers": [
                {"checker": f"release_{idx}", "failure_count": 0}
                for idx in range(6)
            ],
        },
        "validate_entrypoint_witness": {
            "status": "pass",
            "engine_id": "validate_entrypoint_witness",
            "validator_status": "ok",
            "write_receipt": False,
        },
    }
    for engine_id, patch in (overrides or {}).items():
        engines[engine_id].update(patch)
    return {
        "source_manifest": {"module_count": 1},
        "exercise": {"engines": list(engines.values())},
    }


@pytest.fixture(scope="module")
def capsule_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("batch8_validator_checker_capsule")
    return run(
        FIXTURE_INPUT,
        root / "receipts/first_wave/batch8_validator_checker_capsule",
        acceptance_out=root
        / "receipts/acceptance/first_wave/batch8_validator_checker_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch8_validator_checker_capsule_runs_all_engines(
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
    assert by_engine["validator_source_anchor_matrix"]["checker_failure_function_count"] >= 30
    assert by_engine["status_policy_judge_matrix"]["poisoned_policy_decision"] == "block"
    assert "private_home_path" in by_engine["private_boundary_scanner_matrix"]["observed_patterns"]
    assert by_engine["specimen_checker_matrix"]["checker_count"] == 6
    assert by_engine["release_gate_checker_matrix"]["checker_count"] == 6
    assert by_engine["validate_entrypoint_witness"]["validator_status"] == "ok"
    assert result["body_in_receipt"] is False


def test_batch8_validator_checker_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch8_validator_checker_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch8_validator_checker_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch8_validator_checker_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["copied_macro_source_module_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch8_validator_checker_bundle_uses_source_only_public_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_import_validators(*_args: Any, **_kwargs: Any) -> object:
        raise AssertionError("exported bundle validation should not import macro validators")

    monkeypatch.setattr(capsule_module, "_import_validators", fail_import_validators)

    result = run_batch8_validator_checker_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch8_validator_checker_capsule",
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "pass"
    assert by_engine["status_policy_judge_matrix"]["public_runtime_source_only"] is True
    assert by_engine["validate_entrypoint_witness"]["public_runtime_source_only"] is True


def test_batch8_validator_checker_source_modules_are_exact_macro_body_imports() -> None:
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


def test_batch8_validator_checker_rejects_copied_source_missing_anchor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil_root = MICROCOSM_ROOT / "examples/batch8_validator_checker_capsule"

    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        shutil_root,
        public_root / "examples/batch8_validator_checker_capsule",
    )

    bundle = (
        public_root
        / "examples/batch8_validator_checker_capsule/"
        "exported_batch8_validator_checker_capsule_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = manifest["modules"][0]
    copied_source = bundle / module["path"]
    removed_anchor = "def validate(root: Path"
    text = copied_source.read_text(encoding="utf-8")
    assert removed_anchor in text
    copied_source.write_text(
        text.replace(removed_anchor, "def validate_anchor_removed(root: Path", 1),
        encoding="utf-8",
    )
    corrupted_digest = _sha256(copied_source)
    module["sha256"] = corrupted_digest
    module["source_sha256"] = corrupted_digest
    module["target_sha256"] = corrupted_digest
    module["sha256_match"] = True
    module["line_count"] = _line_count(copied_source)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch8_validator_checker_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch8_validator_checker_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    source_manifest = result["source_module_manifest"]
    assert source_manifest["all_expected_digests_matched"] is True
    assert source_manifest["all_required_anchors_present"] is False
    assert source_manifest["modules"][0]["missing_required_anchors"] == [removed_anchor]
    error_codes = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_SOURCE_ANCHOR_MISSING" in error_codes
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" not in error_codes


def test_batch8_validator_checker_card_omits_private_bodies(
    capsule_result: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = capsule_result
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["source_module_count"] == 1
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["body_in_receipt"] is False
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": AUTHORITY_CEILING["real_substrate_disposition"],
        "release_authorized": AUTHORITY_CEILING["release_authorized"],
        "publication_authorized": AUTHORITY_CEILING["publication_authorized"],
        "provider_dispatch": AUTHORITY_CEILING["provider_dispatch"],
        "model_dispatch": AUTHORITY_CEILING["model_dispatch"],
        "source_mutation_authorized": AUTHORITY_CEILING["source_mutation_authorized"],
        "full_validator_suite_freshness_claim": AUTHORITY_CEILING[
            "full_validator_suite_freshness_claim"
        ],
        "public_clone_or_hosting_authority": AUTHORITY_CEILING[
            "public_clone_or_hosting_authority"
        ],
        "test_completeness_proof": AUTHORITY_CEILING["test_completeness_proof"],
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

    assert (
        capsule_module.main(
            [
                "run",
                "--input",
                str(FIXTURE_INPUT),
                "--out",
                str(tmp_path / "cli_card"),
                "--card",
            ]
        )
        == 0
    )
    cli_card = json.loads(capsys.readouterr().out)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]


def test_batch8_validator_checker_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch8_common_negative_cases_ignore_declared_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        capsule_module,
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


def test_batch8_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        capsule_module,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {"status_policy_judge_matrix": {"poisoned_policy_decision": "allow"}}
        ),
    )

    result = validate_negative_cases(
        tmp_path,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "blocked"
    assert "policy_allows_poisoning" in result["missing_negative_cases"]
    assert "BATCH8_VALIDATOR_POLICY_POISONING_BLOCK_REQUIRED" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors
