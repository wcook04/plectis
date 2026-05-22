from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.tactic_portfolio_availability_probe import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_availability_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle"
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


def test_tactic_portfolio_availability_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/tactic_portfolio_availability_probe_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["tactic_count"] == 8
    assert result["compile_status_counts"] == {
        "compile_pass": 7,
        "environment_fail": 1,
    }
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]
    assert result["unavailable_tactic_ids"] == ["aesop"]
    assert result["mathlib_dependent_tactic_ids"] == ["aesop"]
    assert result["mathlib_lake_project_import_available"] is False
    assert result["mathlib_absence_gate_enforced"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        for code in codes:
            assert code in result["observed_negative_cases"][case_id]


def test_tactic_portfolio_availability_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/tactic_portfolio_availability_probe",
        public_root / "fixtures/first_wave/tactic_portfolio_availability_probe",
    )
    result = run(
        public_root / "fixtures/first_wave/tactic_portfolio_availability_probe/input",
        public_root / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_path in result["receipt_paths"]:
        assert not Path(receipt_path).is_absolute()
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "synthetic forbidden proof material" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_tactic_portfolio_availability_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/tactic_portfolio_availability_probe",
        public_root / "examples/tactic_portfolio_availability_probe",
    )
    result = run_availability_bundle(
        public_root
        / "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle",
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_tactic_portfolio_availability_bundle"
    assert result["bundle_id"] == "tactic_portfolio_availability_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["tactic_count"] == 8
    assert result["mathlib_absence_gate_enforced"] is True
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle_validation_result.json"
        )
    ]
