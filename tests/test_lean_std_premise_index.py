from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core.organs.lean_std_premise_index import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_index_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/lean_std_premise_index/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT / "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle"
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


def test_lean_std_premise_index_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/lean_std_premise_index",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/lean_std_premise_index_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["premise_count"] == 11
    assert set(result["namespace_counts"]) == {"Bool", "Iff", "List", "Nat"}
    assert result["authority_ceiling"]["mathlib_allowed"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_lean_std_premise_index_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_index_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/lean_std_premise_index",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_lean_std_premise_index_bundle"
    assert result["bundle_id"] == "public_lean_std_premise_index_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["premise_count"] == 11
    assert result["closed_index_only"] is True


def test_lean_std_premise_index_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    out = tmp_path / "receipts/first_wave/lean_std_premise_index"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "lean_std_premise_index_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
