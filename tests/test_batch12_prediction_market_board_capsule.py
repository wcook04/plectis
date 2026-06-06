from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch12_prediction_market_board_capsule import (
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch12_prediction_market_board_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/batch12_prediction_market_board_capsule/input"
)
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch12_prediction_market_board_capsule/"
    "exported_batch12_prediction_market_board_capsule_bundle"
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
        MICROCOSM_ROOT / "examples/batch12_prediction_market_board_capsule",
        public_root / "examples/batch12_prediction_market_board_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch12_prediction_market_board_capsule",
        public_root / "fixtures/first_wave/batch12_prediction_market_board_capsule",
    )
    return public_root / "fixtures/first_wave/batch12_prediction_market_board_capsule/input"


def _copy_public_bundle(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    forbidden_classes = public_root / "core/private_state_forbidden_classes.json"
    if not forbidden_classes.is_file():
        shutil.copy2(
            MICROCOSM_ROOT / "core/private_state_forbidden_classes.json",
            forbidden_classes,
        )
    bundle = (
        public_root
        / "examples/batch12_prediction_market_board_capsule/"
        "exported_batch12_prediction_market_board_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    return bundle


def test_batch12_prediction_market_board_capsule_runs_macro_mechanisms(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch12_prediction_market_board_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "batch12_prediction_market_board_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    exercise = result["exercise"]
    assert exercise["mechanism_count"] == 5
    mechanisms = {row["mechanism_id"]: row for row in exercise["mechanisms"]}
    prediction = mechanisms["prediction_market_event_join_dedup_aggregate_engine"]
    assert prediction["event_count"] == 2
    assert all(row["computed"] for row in prediction["negative_cases"])
    assert all(
        row["negative_cases"][0]["computed"]
        for row in (
            mechanisms["provider_drift_multisignal_flag_engine"],
            mechanisms["missingness_empty_lane_classifier"],
            mechanisms["delta_since_previous_green"],
            mechanisms["macro_lifecycle_vintage_enrichment"],
        )
    )
    helper_outputs = exercise["quant_mart_helpers"]
    provider_by_id = {
        row["provider_id"]: row
        for row in helper_outputs["provider_drift_monitor"]
    }
    assert provider_by_id["global_stock_feed"]["drift_flags"] == [
        "provider_fallback_used",
        "html_response_seen",
        "fetch_failures",
    ]
    assert provider_by_id["global_news_feed"]["drift_flags"] == []
    assert provider_by_id["global_macro_feed"]["drift_flags"] == [
        "fred_invalid_series",
        "fred_network_warning",
    ]
    missingness_by_id = {
        row["feed_id"]: row
        for row in helper_outputs["missingness_board"]
    }
    assert "healthy_feed" not in missingness_by_id
    assert missingness_by_id["empty_feed"]["empty_reason"] == "zero_rows"
    assert missingness_by_id["degraded_feed"]["empty_reason"] == "quality_degraded"
    assert helper_outputs["delta_since_previous_green_run"]["status"] == "unavailable"
    assert helper_outputs["delta_since_previous_green_run"]["row_deltas_by_lane"] == {}
    macro_by_bucket = {
        row["bucket"]: row
        for row in helper_outputs["macro_regime_board"]
    }
    assert macro_by_bucket["inflation"]["vintage_status"] == "available"
    assert macro_by_bucket["inflation"]["release_calendar_status"] == "available"
    assert macro_by_bucket["inflation"]["top_series"][0]["latest_observation_date"] == "2026-05-01"
    assert macro_by_bucket["growth"]["vintage_status"] == "missing_from_feed_artifact"
    board_by_status = {row["event_identity_status"]: row for row in exercise["board"]}
    assert board_by_status["available"]["aggregate"]["max_volume"] == 900000.0
    assert board_by_status["available"]["aggregate"]["market_count"] == 1
    assert board_by_status["missing_from_feed_artifact"]["event_id"] is None
    assert board_by_status["missing_from_feed_artifact"]["aggregate"]["max_liquidity"] == 0.0
    assert result["body_in_receipt"] is False
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch12_prediction_market_board_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch12_prediction_market_board_bundle(
        EXPORTED_BUNDLE,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "batch12_prediction_market_board_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch12_prediction_market_board_capsule_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["mechanism_count"] == 5
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_batch12_prediction_market_board_rejects_wrong_market_volume_data(
    tmp_path: Path,
) -> None:
    baseline = run_batch12_prediction_market_board_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/baseline/batch12_prediction_market_board_capsule",
        command="pytest",
    )
    bundle = _copy_public_bundle(tmp_path)
    rows_path = bundle / "prediction_market_rows.json"
    payload = json.loads(rows_path.read_text(encoding="utf-8"))
    high_volume_row = next(row for row in payload["rows"] if row["v"] == 900000)
    high_volume_row["v"] = 10000
    rows_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch12_prediction_market_board_bundle(
        bundle,
        tmp_path / "receipts/mutated/batch12_prediction_market_board_capsule",
        command="pytest",
    )

    baseline_available = {
        row["event_identity_status"]: row for row in baseline["exercise"]["board"]
    }["available"]
    mutated_available = {
        row["event_identity_status"]: row for row in result["exercise"]["board"]
    }["available"]
    prediction = next(
        row
        for row in result["exercise"]["mechanisms"]
        if row["mechanism_id"] == "prediction_market_event_join_dedup_aggregate_engine"
    )
    duplicate_case = next(
        row
        for row in prediction["negative_cases"]
        if row["case_id"] == "duplicate_lower_volume_retained_higher"
    )

    assert baseline["status"] == "pass"
    assert baseline_available["aggregate"]["max_volume"] == 900000.0
    assert result["status"] == "blocked"
    assert "BATCH12_PREDICTION_CASE_NOT_OBSERVED" in result["error_codes"]
    assert mutated_available["aggregate"]["max_volume"] == 120000.0
    assert mutated_available["markets"][0]["volume"] == 120000.0
    assert duplicate_case["computed"] is False
    assert duplicate_case["observed"] == {
        "market_count": 1,
        "top_volume": 120000.0,
    }


def test_batch12_prediction_market_board_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch12_prediction_market_board_capsule/"
        "exported_batch12_prediction_market_board_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch12_prediction_market_board_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "batch12_prediction_market_board_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False


def test_batch12_prediction_market_board_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1
    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.read_bytes() == target.read_bytes()
        assert row["anchor_count"] == len(row["required_anchors"])
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch12_prediction_market_board_card_omits_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch12_prediction_market_board_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == 1
    assert card["mechanism_count"] == 5
    assert card["computed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["authority_floor"] == {
        "authority_ceiling": (
            "batch12_prediction_market_and_quant_mart_helper_fixture_only_not_market_truth"
        ),
        "real_substrate_disposition": "real_substrate_capsule",
        "live_prediction_market_truth": False,
        "provider_truth": False,
        "forecast_correctness": False,
        "calibration_claim": False,
        "investment_advice": False,
        "provider_dispatch": False,
        "release_authorized": False,
        "publication_authorized": False,
        "private_root_equivalence_claim": False,
        "whole_system_correctness_claim": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "helper_outputs_body_in_card": False,
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
            "microcosm_core.organs.batch12_prediction_market_board_capsule",
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
        env={**os.environ, "PYTHONPATH": str(MICROCOSM_ROOT / "src")},
    )
    cli_card = json.loads(cli.stdout)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]

    bundle_cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.batch12_prediction_market_board_capsule",
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
        env={**os.environ, "PYTHONPATH": str(MICROCOSM_ROOT / "src")},
    )
    bundle_cli_card = json.loads(bundle_cli.stdout)
    assert bundle_cli_card["authority_floor"] == card["authority_floor"]
    assert bundle_cli_card["body_floor"] == card["body_floor"]


def test_batch12_prediction_market_board_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["body_in_receipt"] is False


def test_batch12_prediction_market_board_negative_cases_are_semantic_not_declared_labels(
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
        / "receipts/first_wave/batch12_prediction_market_board_capsule",
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


def test_batch12_prediction_market_board_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]
