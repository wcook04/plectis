from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_math_readiness_gate import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_readiness_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate/input"
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle"
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


def test_formal_math_readiness_gate_covers_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["blocked_capabilities"] == ["lean_std_synthetic_core:mathlib"]
    assert "aesop" in result["unavailable_tactic_ids"]
    assert result["premise_count"] == 11
    assert result["route_case_count"] == 5
    assert result["recipe_count"] == 3
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_readiness_gate_accepts_exported_bundle(tmp_path: Path) -> None:
    result = run_readiness_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_formal_math_readiness_bundle"
    assert result["bundle_id"] == "public_formal_math_readiness_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["blocked_capabilities"] == ["lean_std_synthetic_core:mathlib"]
    assert result["readiness_board"]["lean_lake_execution_authorized"] is False
    assert result["readiness_board"]["formal_proof_authority"] is False
    assert result["receipt_paths"] == [
        "receipts/exported_formal_math_readiness_bundle_validation_result.json"
    ]


def test_formal_math_readiness_receipts_are_redacted_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate",
        public_root / "fixtures/first_wave/formal_math_readiness_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_readiness_gate/input",
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert "synthetic redacted proof payload" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
