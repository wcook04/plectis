from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.corpus_readiness_mathlib_absence_gate import (
    EXPECTED_NEGATIVE_CASES,
    SOURCE_PATTERN_IDS,
    run,
    run_projection_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input"
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle"
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


def test_corpus_readiness_mathlib_absence_gate_covers_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_pattern_ids"] == SOURCE_PATTERN_IDS
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["mathlib_lake_project_import_available"] is False
    assert result["translation_smoke_only_ids"] == ["minif2f_lean4_mathlib_translation"]
    assert result["absent_corpus_ids"] == ["leandojo", "pantograph"]
    assert result["corpus_count"] == 4
    assert result["consumer_case_count"] == 4
    assert result["allowed_case_ids"] == ["std_core_boolean_simp_allowed"]
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_search_blocked_until_probe",
        "pantograph_state_search_blocked_absent",
    ]
    assert result["readiness_board"]["public_contract"][
        "mathlib_probe_required_before_mathlib_proof_work"
    ] is True
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_corpus_readiness_mathlib_absence_gate_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_projection_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_corpus_readiness_bundle"
    assert result["bundle_id"] == "public_corpus_readiness_mathlib_absence_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["mathlib_lake_project_import_available"] is False
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_search_blocked_until_probe",
    ]
    assert result["receipt_paths"] == [
        "receipts/exported_corpus_readiness_bundle_validation_result.json"
    ]


def test_corpus_readiness_receipts_are_redacted_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input",
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
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
        assert "synthetic forbidden proof material" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
