from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.prediction_oracle_reconciliation import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    RESULT_NAME,
    main,
    run,
    run_prediction_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/prediction_oracle_reconciliation/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle"
)


def _copy_public_bundle_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/prediction_oracle_reconciliation",
        public_root / "examples/prediction_oracle_reconciliation",
    )
    return public_root


def _bundle_input(public_root: Path) -> Path:
    return (
        public_root
        / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle"
    )


def _rewrite_bundle_packet(public_root: Path, packet: dict[str, Any]) -> None:
    packet_path = _bundle_input(public_root) / "reconciliation_packet.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")


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


def test_prediction_oracle_reconciliation_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["cp1_branch_count"] == 3
    assert result["cp2_prediction_count"] == 3
    assert result["oracle_diff_graded_count"] == 2
    assert result["oracle_diff_hit_count"] == 2
    assert result["numeric_reconciliation_row_count"] == 2
    assert result["numeric_reconciliation_summary"]["asset_class_counts"] == {
        "ETF": 1,
        "STOCK": 1,
    }
    assert result["numeric_reconciliation_summary"]["large_numeric_miss_count"] == 1
    assert (
        result["numeric_reconciliation_summary"]["largest_absolute_miss_target"]
        == "SYNTH_TARGET_BETA"
    )
    assert result["numeric_reconciliation_summary"]["degraded_feed_gate_count"] == 1
    assert result["numeric_reconciliation_source"]["source_body_invoked"] is True
    assert result["numeric_reconciliation_source"]["source_faithful_fallback_used"] is False
    assert result["numeric_reconciliation_rows"][0]["target_id"] == "SYNTH_TARGET_BETA"
    assert result["numeric_reconciliation_rows"][0]["directional_correct"] is True
    assert result["numeric_reconciliation_rows"][0]["large_numeric_miss"] is True
    assert result["reconciliation_rows"][2]["prediction_id"] == "pred_gamma_direction"
    assert result["reconciliation_rows"][2]["numeric_graded"] is False
    assert result["reconciliation_rows"][2]["oracle_feed_health"] == "degraded"
    assert result["dossier_mutation_count"] == 1
    assert result["authority_ceiling"]["trading_authorized"] is False
    assert result["authority_ceiling"]["financial_advice_authorized"] is False
    assert result["authority_ceiling"]["live_market_data_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    assert result["error_codes"] == sorted(
        code for codes in EXPECTED_NEGATIVE_CASES.values() for code in codes
    )


def test_prediction_oracle_reconciliation_receipts_are_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/prediction_oracle_reconciliation",
        public_root / "fixtures/first_wave/prediction_oracle_reconciliation",
    )
    result = run(
        public_root / "fixtures/first_wave/prediction_oracle_reconciliation/input",
        public_root / "receipts/first_wave/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in _walk_keys(payload)
        assert "public_replacement_refs" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_prediction_oracle_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_prediction_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_prediction_oracle_bundle"
    assert result["bundle_id"] == "public_prediction_oracle_reconciliation_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["reconciliation_rows"][0]["direction_hit"] is True
    assert result["reconciliation_rows"][1]["direction_hit"] is True
    assert result["reconciliation_rows"][1]["large_numeric_miss"] is True
    assert result["reconciliation_rows"][2]["direction_hit"] is None
    assert result["reconciliation_rows"][2]["numeric_graded"] is False
    assert result["numeric_reconciliation_rows"][0]["target_id"] == "SYNTH_TARGET_BETA"
    assert result["numeric_reconciliation_rows"][0]["asset_class"] == "ETF"
    assert result["numeric_reconciliation_rows"][0]["directional_correct"] is True
    assert result["numeric_reconciliation_rows"][0]["large_numeric_miss"] is True
    assert result["numeric_reconciliation_summary"]["asset_class_counts"] == {
        "ETF": 1,
        "STOCK": 1,
    }
    assert (
        result["numeric_reconciliation_summary"]["largest_absolute_miss_target"]
        == "SYNTH_TARGET_BETA"
    )
    assert result["numeric_reconciliation_summary"]["source_body_invoked"] is True
    assert result["numeric_reconciliation_source"]["source_body_invoked"] is True
    assert result["numeric_reconciliation_source"]["source_helper_names"] == [
        "_build_prediction_reconciliation_rows",
        "_build_prediction_reconciliation_summary",
    ]
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 14
    assert result["body_material_status"] == (
        "copied_non_secret_macro_prediction_oracle_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 14
    assert result["authority_ceiling"]["trading_authorized"] is False
    assert result["authority_ceiling"]["financial_advice_authorized"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)
    assert "public_replacement_refs" not in result


def test_prediction_oracle_source_modules_are_digest_verified(tmp_path: Path) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    tampered = (
        _bundle_input(public_root)
        / "source_artifacts/macro_source/tools/oracle/truth_diff_equity.py"
    )
    tampered.write_text(
        tampered.read_text(encoding="utf-8") + "\n# tampered digest check\n",
        encoding="utf-8",
    )

    result = run_prediction_bundle(
        public_root / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "PREDICTION_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_open_body_imports"]["body_material_count"] == 14
    assert result["source_open_body_imports"]["body_in_receipt"] is False


def test_prediction_oracle_source_modules_reject_body_text_in_receipt(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    manifest_path = _bundle_input(public_root) / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["body_text_in_receipt"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_prediction_bundle(
        public_root / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "PREDICTION_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in result["error_codes"]
    assert result["source_open_body_imports"]["body_in_receipt"] is False


def test_prediction_oracle_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    result = run_prediction_bundle(
        _bundle_input(public_root),
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "pass"
    receipt_file = (
        public_root
        / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation"
        / BUNDLE_RESULT_NAME
    )
    text = receipt_file.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    payload = json.loads(text)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_prediction_oracle_bundle"
    assert payload["source_open_body_imports"]["body_material_count"] == 14
    assert payload["source_open_body_imports"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["real_runtime_receipt"] is True
    assert payload["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in payload
    assert "body_redacted" not in _walk_keys(payload)
    assert "public_replacement_refs" not in payload
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)


def test_prediction_oracle_fixture_card_stdout_is_compact_and_keeps_full_receipts(
    tmp_path: Path,
    capsys: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/prediction_oracle_reconciliation",
        public_root / "fixtures/first_wave/prediction_oracle_reconciliation",
    )
    out_dir = public_root / "receipts/first_wave/prediction_oracle_reconciliation"

    status = main(
        [
            "run",
            "--input",
            str(public_root / "fixtures/first_wave/prediction_oracle_reconciliation/input"),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    assert len(captured.out.encode("utf-8")) < 5000
    card = json.loads(captured.out)
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "first_wave_fixture"
    assert card["receipt_summary"]["receipt_count"] == 4
    assert card["receipt_summary"]["receipt_paths_exported"] is False
    assert card["receipt_summary"]["result_receipt_name"] == RESULT_NAME
    assert card["prediction_reconciliation_summary"]["cp2_prediction_count"] == 3
    assert card["prediction_reconciliation_summary"]["oracle_diff_hit_count"] == 2
    assert card["prediction_reconciliation_summary"]["numeric_reconciliation_row_count"] == 2
    assert card["prediction_reconciliation_summary"]["numeric_large_miss_count"] == 1
    assert card["prediction_reconciliation_summary"]["numeric_asset_class_counts"] == {
        "ETF": 1,
        "STOCK": 1,
    }
    assert (
        card["prediction_reconciliation_summary"]["largest_absolute_miss_target"]
        == "SYNTH_TARGET_BETA"
    )
    assert card["negative_case_coverage"]["expected_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["observed_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["trading_authorized"] is False
    assert card["no_export_guards"]["findings_exported"] is False

    card_keys = set(_walk_keys(card))
    assert "findings" not in card_keys
    assert "observed_negative_cases" not in card_keys
    assert "source_refs" not in card_keys
    assert "reconciliation_rows" not in card_keys
    assert "numeric_reconciliation_rows" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "anti_claim" not in card_keys
    full_receipt = json.loads((out_dir / RESULT_NAME).read_text(encoding="utf-8"))
    assert full_receipt["status"] == "pass"
    assert set(full_receipt["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_prediction_oracle_bundle_card_stdout_is_compact_and_keeps_full_receipt(
    tmp_path: Path,
    capsys: Any,
) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    out_dir = public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation"

    status = main(
        [
            "run-prediction-bundle",
            "--input",
            str(
                public_root
                / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle"
            ),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    assert len(captured.out.encode("utf-8")) < 4500
    card = json.loads(captured.out)
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "exported_prediction_oracle_bundle"
    assert card["receipt_summary"]["receipt_count"] == 1
    assert card["receipt_summary"]["result_receipt_name"] == BUNDLE_RESULT_NAME
    assert card["receipt_summary"]["board_receipt_name"] is None
    assert card["negative_case_coverage"]["expected_case_count"] == 0
    assert card["negative_case_coverage"]["observed_case_count"] == 0
    assert card["prediction_reconciliation_summary"]["reconciliation_row_count"] == 3
    assert card["prediction_reconciliation_summary"]["numeric_reconciliation_row_count"] == 2
    assert card["prediction_reconciliation_summary"]["numeric_large_miss_count"] == 1
    assert card["prediction_reconciliation_summary"]["source_body_invoked"] is True
    assert card["source_open_body_imports_summary"]["body_material_count"] == 14
    assert card["source_open_body_imports_summary"]["body_in_receipt"] is False
    assert card["no_export_guards"]["reconciliation_rows_exported"] is False
    assert card["no_export_guards"]["numeric_reconciliation_rows_exported"] is False
    assert "reconciliation_rows" not in set(_walk_keys(card))
    assert "numeric_reconciliation_rows" not in set(_walk_keys(card))
    full_receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
    assert full_receipt["status"] == "pass"
    assert full_receipt["input_mode"] == "exported_prediction_oracle_bundle"


def test_prediction_oracle_runtime_perturbation_moves_verdict(tmp_path: Path) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    packet_path = _bundle_input(public_root) / "reconciliation_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["oracle_diff"][1]["realized_direction"] = "up"
    _rewrite_bundle_packet(public_root, packet)

    result = run_prediction_bundle(
        _bundle_input(public_root),
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["oracle_diff_hit_count"] == 1
    beta = next(
        row
        for row in result["reconciliation_rows"]
        if row["prediction_id"] == "pred_beta_direction"
    )
    assert beta["direction_hit"] is False
    assert result["numeric_reconciliation_summary"]["directionally_incorrect_count"] == 1
    assert result["numeric_reconciliation_rows"][0]["directional_correct"] is False


def test_prediction_oracle_rejects_claimed_grading_contradicting_recompute(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    packet_path = _bundle_input(public_root) / "reconciliation_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["oracle_diff"][1]["abs_error"] = 1.25
    packet["oracle_diff"][1]["direction_hit"] = False
    _rewrite_bundle_packet(public_root, packet)

    result = run_prediction_bundle(
        _bundle_input(public_root),
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "PREDICTION_ORACLE_CLAIMED_ABS_ERROR_CONTRADICTS_RECOMPUTE" in result[
        "error_codes"
    ]
    assert "PREDICTION_ORACLE_CLAIMED_DIRECTION_HIT_CONTRADICTS_RECOMPUTE" in result[
        "error_codes"
    ]
    beta_numeric = next(
        row
        for row in result["numeric_reconciliation_rows"]
        if row["target_id"] == "SYNTH_TARGET_BETA"
    )
    assert beta_numeric["absolute_delta"] == 20.0
    assert beta_numeric["directional_correct"] is True
    beta_reconciliation = next(
        row
        for row in result["reconciliation_rows"]
        if row["prediction_id"] == "pred_beta_direction"
    )
    assert beta_reconciliation["direction_hit"] is True

    packet["oracle_diff"][1]["abs_error"] = 20.0
    packet["oracle_diff"][1]["direction_hit"] = True
    _rewrite_bundle_packet(public_root, packet)
    repaired = run_prediction_bundle(
        _bundle_input(public_root),
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation_repaired",
        command="pytest",
    )

    assert repaired["status"] == "pass"
    assert "PREDICTION_ORACLE_CLAIMED_ABS_ERROR_CONTRADICTS_RECOMPUTE" not in repaired[
        "error_codes"
    ]
    assert "PREDICTION_ORACLE_CLAIMED_DIRECTION_HIT_CONTRADICTS_RECOMPUTE" not in repaired[
        "error_codes"
    ]


def test_prediction_oracle_numeric_rank_is_rederived_from_runtime_evidence(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    packet_path = _bundle_input(public_root) / "reconciliation_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["oracle_diff"][0]["realized_price"] = 140.0
    packet["oracle_diff"][0]["abs_error"] = 36.0
    packet["oracle_diff"][0]["pred_error_pct"] = 36.0
    _rewrite_bundle_packet(public_root, packet)

    result = run_prediction_bundle(
        _bundle_input(public_root),
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["numeric_reconciliation_rows"][0]["target_id"] == "SYNTH_TARGET_ALPHA"
    assert result["numeric_reconciliation_rows"][0]["rank"] == 1
    assert (
        result["numeric_reconciliation_summary"]["largest_absolute_miss_target"]
        == "SYNTH_TARGET_ALPHA"
    )
    alpha = next(
        row
        for row in result["reconciliation_rows"]
        if row["prediction_id"] == "pred_alpha_direction"
    )
    assert alpha["numeric_rank"] == 1


def test_prediction_oracle_rejects_oracle_rows_not_backed_by_prediction(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_bundle_root(tmp_path)
    packet_path = _bundle_input(public_root) / "reconciliation_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["oracle_diff"][1]["predicted_direction"] = "up"
    _rewrite_bundle_packet(public_root, packet)

    result = run_prediction_bundle(
        _bundle_input(public_root),
        public_root / "receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "PREDICTION_ORACLE_PREDICTED_DIRECTION_MISMATCH" in result["error_codes"]
