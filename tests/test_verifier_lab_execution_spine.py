from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core.organs.verifier_lab_execution_spine import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_execution_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/verifier_lab_execution_spine/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_execution_spine/exported_verifier_lab_execution_spine_bundle"
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


def test_verifier_lab_execution_spine_runs_lean_cp2_and_evolve(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/verifier_lab_execution_spine",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/verifier_lab_execution_spine_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["authority_counters"]["transition_count"] == 6
    assert result["authority_counters"]["accepted_transition_count"] == 4
    assert result["authority_counters"]["residual_transition_count"] == 2
    assert result["authority_counters"]["cp2_translation_count"] == 1
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 1
    assert result["authority_counters"]["evolve_candidate_count"] == 1
    assert result["authority_counters"]["evolve_accepted_count"] == 1
    assert result["authority_counters"]["oracle_forward_success_increment_count"] == 0
    assert result["authority_counters"]["provider_results_counted"] == 0
    assert result["authority_counters"]["proof_body_export_count"] == 0
    assert result["authority_counters"]["source_mutation_count"] == 0

    claim_separation = result["claim_separation"]
    assert len(claim_separation["lean_verified"]) == 4
    assert len(claim_separation["provider_suggested"]) == 1
    assert len(claim_separation["oracle_compared"]) == 1
    assert len(claim_separation["cp2_translated"]) == 1
    assert len(claim_separation["retrieval_miss"]) == 1
    assert len(claim_separation["evolve_accepted"]) == 1
    assert all(row["proof_body_exported"] is False for row in result["transition_trace"])
    assert all(row["provider_visible"] is False for row in result["transition_trace"])
    assert all(row["oracle_visible"] is False for row in result["transition_trace"])

    board_path = (
        tmp_path
        / "receipts/first_wave/verifier_lab_execution_spine/verifier_lab_execution_spine_board.json"
    )
    board = json.loads(board_path.read_text(encoding="utf-8"))
    assert board["lean_verified_count"] == 4
    assert board["cp2_downstream_effect_count"] == 1
    assert board["evolve_accepted_count"] == 1


def test_verifier_lab_execution_spine_bundle_is_public_redacted(tmp_path: Path) -> None:
    result = run_execution_bundle(
        EXPORTED_BUNDLE,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/verifier_lab_execution_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_verifier_lab_execution_spine_bundle"
    assert result["bundle_id"] == "public_verifier_lab_execution_spine_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["authority_counters"]["accepted_transition_count"] == 4
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 1
    assert result["authority_counters"]["evolve_accepted_count"] == 1


def test_verifier_lab_execution_spine_receipts_are_redacted(tmp_path: Path) -> None:
    out = tmp_path / "receipts/first_wave/verifier_lab_execution_spine"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "verifier_lab_execution_spine_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["receipts_include_proof_bodies"] is False
    assert payload["provider_calls_authorized"] is False
    assert payload["source_mutation_authorized"] is False
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
