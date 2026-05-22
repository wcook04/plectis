from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.prediction_oracle_reconciliation import (
    BUNDLE_RESULT_NAME,
    EXPECTED_NEGATIVE_CASES,
    run,
    run_prediction_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/prediction_oracle_reconciliation/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle"
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
    assert result["cp1_branch_count"] == 2
    assert result["cp2_prediction_count"] == 2
    assert result["oracle_diff_graded_count"] == 2
    assert result["oracle_diff_hit_count"] == 1
    assert result["dossier_mutation_count"] == 1
    assert result["authority_ceiling"]["trading_authorized"] is False
    assert result["authority_ceiling"]["financial_advice_authorized"] is False
    assert result["authority_ceiling"]["live_market_data_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


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
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
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
    assert result["reconciliation_rows"][1]["direction_hit"] is False
    assert result["authority_ceiling"]["trading_authorized"] is False
    assert result["authority_ceiling"]["financial_advice_authorized"] is False


def test_prediction_oracle_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/prediction_oracle_reconciliation",
        public_root / "examples/prediction_oracle_reconciliation",
    )
    result = run_prediction_bundle(
        public_root / "examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle",
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
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
