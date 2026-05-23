from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.verifier_lab_kernel import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_kernel_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/verifier_lab_kernel/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
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


def test_verifier_lab_kernel_runs_component_stack_and_separates_claims(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/verifier_lab_kernel",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/verifier_lab_kernel_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["component_statuses"] == {
        "formal_math_lean_proof_witness": "pass",
        "formal_math_verifier_trace_repair_loop": "pass",
        "tactic_portfolio_availability_probe": "pass",
        "target_shape_tactic_routing_gate": "pass",
    }
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8
    assert result["target_shape_route_case_count"] >= 4
    assert result["verifier_trace_attempt_count"] >= 3
    assert set(result["claim_separation"]) == {
        "lean_verified",
        "provider_suggested",
        "oracle_compared",
        "contract_rejected",
        "retrieval_miss",
        "cp2_translated",
        "evolve_candidate",
    }
    assert len(result["claim_separation"]["cp2_translated"]) == 2
    assert len(result["claim_separation"]["evolve_candidate"]) == 1
    assert result["authority_counters"][
        "oracle_forward_success_increment_count"
    ] == 0
    assert result["authority_counters"]["provider_results_counted"] == 0
    assert result["authority_ceiling"]["provider_text_counts_as_proof"] is False
    assert result["authority_ceiling"]["oracle_success_counts_as_forward_success"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_verifier_lab_kernel_receipts_are_public_relative_and_transparent_without_bodies(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")

    result = run(
        public_root / "fixtures/first_wave/verifier_lab_kernel/input",
        public_root / "receipts/first_wave/verifier_lab_kernel",
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
        assert '"proof_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
        assert payload["receipt_transparency_contract"]["omitted_payload_scope"] == (
            "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only"
        )
        assert payload["receipt_transparency_contract"]["body_in_receipt"] is False
        assert payload["receipt_transparency_contract"]["real_substrate_default"] is True
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "public_replacement_refs" not in payload
        assert "proof_body" not in _walk_keys(payload)


def test_verifier_lab_kernel_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_kernel_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/verifier_lab_kernel",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_verifier_lab_kernel_bundle"
    assert result["bundle_id"] == "verifier_lab_kernel_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["component_statuses"]["formal_math_lean_proof_witness"] == "pass"
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8
    assert len(result["claim_separation"]["provider_suggested"]) == 1
    assert len(result["claim_separation"]["cp2_translated"]) == 2
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
