from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch8_tools_tail_primitives_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_MECHANISMS,
    EXPECTED_MODULE_IDS,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    main,
    result_card,
    run,
    run_batch8_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
ORGAN_ID = "batch8_tools_tail_primitives_capsule"
FIXTURE_INPUT = MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}/input"
EXPORTED_BUNDLE = MICROCOSM_ROOT / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / f"examples/{ORGAN_ID}",
        public_root / f"examples/{ORGAN_ID}",
    )
    shutil.copytree(
        MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}",
        public_root / f"fixtures/first_wave/{ORGAN_ID}",
    )
    return public_root / f"fixtures/first_wave/{ORGAN_ID}/input"


def test_batch8_tools_tail_primitives_capsule_runs_real_source_exercises(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        acceptance_out=tmp_path
        / f"receipts/acceptance/first_wave/{ORGAN_ID}_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert {row["mechanism_id"] for row in exercise["mechanisms"]} == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["mechanisms"])
    assert set(exercise["runtime_exercises"]) == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["runtime_exercises"].values())

    runtime = exercise["runtime_exercises"]
    observer = runtime["observer_set_diff_kernel"]
    assert observer["evidence_diff"]["missed_ledger_ids"] == ["E2"]
    assert observer["evidence_diff"]["extra_ledger_ids"] == ["E3"]
    assert observer["malformed_rows_skipped"] is True

    patch_vm = runtime["version_committer_json_patch_vm"]
    assert patch_vm["patched_document"]["profile"]["name"] == "Microcosm"
    assert patch_vm["scalar_traversal_refused"] is True

    ledger = runtime["ledger_id_identity_hash_engine"]
    assert ledger["poly_id"] == ledger["repeat_id"]
    assert ledger["unknown_lane_id"].startswith("X_")
    assert ledger["missing_identity_refused"] is True

    shadow = runtime["shadow_envelope_dsl_parser_coverage"]
    assert shadow["hard_failure"] is False
    assert shadow["malformed_tuple_coverage_gap_count"] >= 1

    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["body_in_receipt"] is False


def test_batch8_tools_tail_primitives_capsule_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch8_bundle(
        EXPORTED_BUNDLE,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch8_tools_tail_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == len(EXPECTED_MODULE_IDS)
    assert manifest["body_in_receipt"] is False
    assert {row["module_id"] for row in manifest["modules"]} == set(EXPECTED_MODULE_IDS)

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


def test_batch8_tools_tail_card_omits_private_bodies(
    tmp_path: Path,
    capsys,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert card["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["body_in_receipt"] is False
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": "real_substrate_capsule",
        "standard_authority": AUTHORITY_CEILING["standard_authority"],
        "godmode_run_missing_authorized": False,
        "provider_dispatch": False,
        "live_oracle_execution": False,
        "repo_mutation_authorized": False,
        "source_mutation_authorized": False,
        "publication_authorized": False,
        "release_authorized": False,
        "whole_system_correctness_claim": False,
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
    assert "assistant_raw_text" not in _walk_keys(result)
    assert "raw_text" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)

    assert (
        main(
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


def test_batch8_tools_tail_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / f"receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    for expected_codes in EXPECTED_NEGATIVE_CASES.values():
        for code in expected_codes:
            assert code in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch8_tools_tail_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]
