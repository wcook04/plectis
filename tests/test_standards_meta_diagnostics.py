from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core.organs.standards_meta_diagnostics import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_diagnostics_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/standards_meta_diagnostics/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle"
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


def test_standards_meta_diagnostics_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/standards_meta_diagnostics",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/standards_meta_diagnostics_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["accepted_organ_count"] == 38
    assert result["standard_mapping_count"] == 38
    assert result["runtime_contract_count"] == 38
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["standards_registry_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_standards_meta_diagnostics_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_diagnostics_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_standards_meta_diagnostics_bundle"
    assert result["bundle_id"] == "public_standards_meta_diagnostics_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["accepted_organ_count"] == 38
    assert "lean_std_premise_index" in result["covered_organ_ids"]
    assert "formal_math_verifier_trace_repair_loop" in result["covered_organ_ids"]
    assert "formal_evidence_cell_anchor_resolver" in result["covered_organ_ids"]
    assert "undeclared_library_prior_symbol_classifier" in result["covered_organ_ids"]
    assert "agent_benchmark_integrity_anti_gaming_replay" in result["covered_organ_ids"]
    assert "durable_agent_work_landing_replay" in result["covered_organ_ids"]
    assert "standards_meta_diagnostics" in result["covered_organ_ids"]
    assert "cold_reader_route_map" in result["covered_organ_ids"]
    assert "agent_monitor_redteam_falsification_replay" in result["covered_organ_ids"]
    assert "agent_sabotage_scheming_monitor_replay" in result["covered_organ_ids"]
    assert "agent_memory_temporal_conflict_replay" in result["covered_organ_ids"]
    assert "sleeper_memory_poisoning_quarantine_replay" in result["covered_organ_ids"]
    assert "mcp_tool_authority_replay" in result["covered_organ_ids"]
    assert "proof_derived_governed_mutation_authorization" in result["covered_organ_ids"]
    assert "belief_state_process_reward_replay" in result["covered_organ_ids"]
    assert result["authority_ceiling"]["whole_system_correctness_claim"] is False


def test_standards_meta_diagnostics_receipts_are_redacted(tmp_path: Path) -> None:
    out = tmp_path / "receipts/first_wave/standards_meta_diagnostics"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "standards_meta_diagnostics_validation_receipt.json"
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
