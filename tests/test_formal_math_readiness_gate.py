from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_math_readiness_gate import (
    EXPECTED_NEGATIVE_CASES,
    SELECTED_PATTERN_IDS,
    plan_readiness_extensions,
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
    assert result["projection_cell_id"] == "formal_math_readiness_extensions"
    assert result["selected_pattern_ids"] == SELECTED_PATTERN_IDS
    extension = result["readiness_extension_board"]
    assert extension["source_intake_ref"].endswith("#formal_math_readiness_extensions")
    assert extension["projection_status"] == "public_replacement_landed"
    assert extension["premise_index_projection"]["namespace_counts"] == {
        "Bool": 2,
        "Iff": 3,
        "List": 3,
        "Nat": 3,
    }
    assert extension["premise_index_projection"]["split_eligibility_counts"] == {
        "dev": 11,
        "test": 11,
        "train": 11,
    }
    assert extension["tactic_portfolio_projection"]["available_tactic_count"] == 6
    assert extension["tactic_portfolio_projection"][
        "mathlib_dependent_unavailable_tactic_ids"
    ] == ["aesop"]
    assert extension["target_shape_routing_projection"]["blocked_route_case_ids"] == [
        "mathlib_search_uses_aesop_without_probe"
    ]
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
    assert result["readiness_extension_board"]["cell_id"] == "formal_math_readiness_extensions"
    assert result["readiness_extension_board"]["target_shape_routing_projection"][
        "blocked_route_case_count"
    ] == 0
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
        if payload["schema_version"] == "formal_math_readiness_extension_board_receipt_v1":
            assert payload["cell_id"] == "formal_math_readiness_extensions"
            assert payload["projection_contract"]["body_copied"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_math_readiness_plan_is_non_writing_extension_preview(
    tmp_path: Path,
) -> None:
    result = plan_readiness_extensions(FIXTURE_INPUT, command="pytest")

    assert result["status"] == "pass"
    assert result["schema_version"] == "formal_math_readiness_extension_preview_v1"
    assert result["projection_cell_id"] == "formal_math_readiness_extensions"
    assert result["selected_pattern_ids"] == SELECTED_PATTERN_IDS
    assert result["readiness_extension_board"]["projection_status"] == "public_replacement_landed"
    assert result["readiness_extension_board"]["provider_context_projection"][
        "provider_calls_authorized"
    ] is False
    assert not any(tmp_path.iterdir())
