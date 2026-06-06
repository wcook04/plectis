from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch12_market_dashboard_read_model_capsule import (
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch12_market_dashboard_read_model_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/batch12_market_dashboard_read_model_capsule/input"
)
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch12_market_dashboard_read_model_capsule/"
    "exported_batch12_market_dashboard_read_model_capsule_bundle"
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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch12_market_dashboard_read_model_capsule",
        public_root / "examples/batch12_market_dashboard_read_model_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch12_market_dashboard_read_model_capsule",
        public_root / "fixtures/first_wave/batch12_market_dashboard_read_model_capsule",
    )
    return public_root / "fixtures/first_wave/batch12_market_dashboard_read_model_capsule/input"


def test_batch12_market_dashboard_read_model_capsule_runs_macro_mechanisms(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch12_market_dashboard_read_model_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "batch12_market_dashboard_read_model_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    exercise = result["exercise"]
    assert exercise["mechanism_count"] == 3
    assert exercise["clean_validator_error_count"] == 0
    assert exercise["computed_negative_case_count"] >= len(EXPECTED_NEGATIVE_CASES)
    by_id = {row["mechanism_id"]: row for row in exercise["mechanisms"]}
    assert by_id["market_dashboard_read_model_overclaim_ceiling_validator"]["status"] == "pass"
    assert by_id["market_feed_freshness_state_classifier"]["status"] == "pass"
    assert by_id["market_situation_entity_overlap_cohort_scorer"]["status"] == "pass"
    freshness = by_id["market_feed_freshness_state_classifier"]["negative_cases"]
    assert {row["state"] for row in freshness} >= {
        "fresh_green_feed",
        "stale_green_feed",
        "blocked_missing_artifact",
    }
    related = by_id["market_situation_entity_overlap_cohort_scorer"]["negative_cases"]
    truncation = next(row for row in related if row["case_id"] == "truncates_sorted_self_excluded")
    assert truncation["result"] == [f"related-{idx}" for idx in range(1, 7)]
    assert result["body_in_receipt"] is False
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch12_market_dashboard_read_model_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch12_market_dashboard_read_model_bundle(
        EXPORTED_BUNDLE,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "batch12_market_dashboard_read_model_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch12_market_dashboard_read_model_capsule_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["mechanism_count"] == 3
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_batch12_market_dashboard_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch12_market_dashboard_read_model_capsule/"
        "exported_batch12_market_dashboard_read_model_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch12_market_dashboard_read_model_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "batch12_market_dashboard_read_model_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False


def test_batch12_market_dashboard_read_model_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1
    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.read_bytes() == target.read_bytes()
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch12_market_dashboard_card_omits_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch12_market_dashboard_read_model_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == 1
    assert card["mechanism_count"] == 3
    assert card["computed_negative_case_count"] >= len(EXPECTED_NEGATIVE_CASES)
    assert card["authority_floor"] == {
        "authority_ceiling": (
            "batch12_market_dashboard_read_model_capsule_fixture_only_not_market_truth"
        ),
        "real_substrate_disposition": "real_substrate_capsule",
        "live_market_truth": False,
        "investment_advice": False,
        "provider_dispatch": False,
        "release_authorized": False,
        "publication_authorized": False,
        "source_mutation_authorized": False,
        "whole_system_correctness_claim": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "validator_errors_body_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)

    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.batch12_market_dashboard_read_model_capsule",
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(tmp_path / "cli_fixture"),
            "--card",
        ],
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
            "microcosm_core.organs.batch12_market_dashboard_read_model_capsule",
            "validate-bundle",
            "--input",
            str(EXPORTED_BUNDLE),
            "--out",
            str(tmp_path / "cli_bundle"),
            "--card",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    bundle_cli_card = json.loads(bundle_cli.stdout)
    assert bundle_cli_card["authority_floor"] == card["authority_floor"]
    assert bundle_cli_card["body_floor"] == card["body_floor"]


def test_batch12_market_dashboard_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["body_in_receipt"] is False


def test_batch12_market_dashboard_negative_cases_are_semantic_not_declared_labels(
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
        fixture.parents[3]
        / "receipts/first_wave/batch12_market_dashboard_read_model_capsule",
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


def test_batch12_market_dashboard_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]
