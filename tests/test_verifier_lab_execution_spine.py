from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core.organs import verifier_lab_execution_spine as spine
from microcosm_core.organs.verifier_lab_execution_spine import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
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
    assert all(row["stdout_stderr_in_receipt"] is False for row in result["transition_trace"])
    assert all(row["provider_visible"] is False for row in result["transition_trace"])
    assert all(row["oracle_visible"] is False for row in result["transition_trace"])
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert all(
        ref.startswith("fixtures/first_wave/verifier_lab_execution_spine/input/")
        for ref in result["public_runtime_refs"]
    )

    board_path = (
        tmp_path
        / "receipts/first_wave/verifier_lab_execution_spine/verifier_lab_execution_spine_board.json"
    )
    board = json.loads(board_path.read_text(encoding="utf-8"))
    assert board["lean_verified_count"] == 4
    assert board["cp2_downstream_effect_count"] == 1
    assert board["evolve_accepted_count"] == 1


def test_verifier_lab_execution_spine_bundle_is_public_structured(tmp_path: Path) -> None:
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
    assert result["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert all(
        ref.startswith(
            "examples/verifier_lab_execution_spine/"
            "exported_verifier_lab_execution_spine_bundle/"
        )
        for ref in result["public_runtime_refs"]
    )


def test_verifier_lab_execution_spine_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = tmp_path / "receipts/runtime_shell/demo_project/organs/verifier_lab_execution_spine"
    argv = [
        "run-execution-bundle",
        "--input",
        str(EXPORTED_BUNDLE),
        "--out",
        str(out),
        "--card",
    ]

    assert main(argv) == 0
    first_stdout = capsys.readouterr().out
    first_card = json.loads(first_stdout)

    assert len(first_stdout.encode("utf-8")) < 5000
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["input_mode"] == "exported_verifier_lab_execution_spine_bundle"
    assert first_card["execution_summary"]["transition_count"] == 6
    assert first_card["execution_summary"]["accepted_transition_count"] == 4
    assert first_card["execution_summary"]["cp2_downstream_effect_count"] == 1
    assert first_card["execution_summary"]["evolve_accepted_count"] == 1
    assert first_card["negative_case_coverage"]["expected_negative_case_count"] == 0
    assert first_card["negative_case_coverage"]["missing_negative_case_count"] == 0
    assert first_card["secret_exclusion_summary"]["blocking_hit_count"] == 0
    assert first_card["receipt_summary"]["receipt_count"] == 1
    assert first_card["no_export_guards"]["transition_trace_exported"] is False
    assert first_card["no_export_guards"]["claim_separation_exported"] is False
    assert first_card["no_export_guards"]["receipt_paths_exported"] is False

    card_keys = set(_walk_keys(first_card))
    assert "transition_trace" not in card_keys
    assert "claim_separation" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "findings" not in card_keys
    assert "anti_claim" not in card_keys

    full_receipt = json.loads((out / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
    assert full_receipt["status"] == "pass"
    assert full_receipt["transition_trace"][0]["problem_id"] == "closed_nat_mod_public"
    assert "claim_separation" in full_receipt

    def fail_build_result(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh exported-bundle card should reuse the receipt")

    monkeypatch.setattr(spine, "_build_result", fail_build_result)

    assert main(argv) == 0
    second_stdout = capsys.readouterr().out
    second_card = json.loads(second_stdout)

    assert len(second_stdout.encode("utf-8")) < 5000
    assert second_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert second_card["execution_summary"] == first_card["execution_summary"]


def test_verifier_lab_execution_spine_receipts_are_transparent_without_bodies(
    tmp_path: Path,
) -> None:
    out = tmp_path / "receipts/first_wave/verifier_lab_execution_spine"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "verifier_lab_execution_spine_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert payload["receipt_transparency_contract"]["omitted_payload_scope"] == (
        "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only"
    )
    assert payload["body_in_receipt"] is False
    assert payload["real_runtime_receipt"] is True
    assert payload["synthetic_receipt_standin_allowed"] is False
    assert payload["transition_trace"][0]["problem_id"] == "closed_nat_mod_public"
    assert payload["transition_trace"][0]["lean_return_code"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["receipts_include_proof_bodies"] is False
    assert payload["provider_calls_authorized"] is False
    assert payload["source_mutation_authorized"] is False
    assert "private_state_scan" not in payload
    assert "body_redacted" not in payload
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
