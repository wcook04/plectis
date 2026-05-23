from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.target_shape_tactic_routing_gate import (
    EXPECTED_NEGATIVE_CASES,
    SOURCE_PATTERN_IDS,
    run,
    run_routing_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/target_shape_tactic_routing_gate/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/target_shape_tactic_routing_gate/exported_target_shape_tactic_routing_bundle"
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


def test_target_shape_tactic_routing_gate_observes_negative_cases(
    tmp_path: Path,
) -> None:
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
    assert result["route_case_count"] == 5
    assert result["target_shapes"] == [
        "bool_decision_goal",
        "list_length_rewrite_goal",
        "list_map_index_rewrite_goal",
        "nat_injective_goal",
        "propositional_intro_goal",
    ]
    assert result["selected_tactic_ids"] == ["decide", "omega", "rfl", "simp_all"]
    assert result["all_expectations_met"] is True
    assert result["body_material_status"] == "real_ring2_target_shape_routing_refs"
    assert (
        result["routing_evidence_status"]
        == "real_ring2_problem_domain_failure_class_route_refs"
    )
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["routing_board"]["public_contract"]["routing_pre_execution"] is True
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_target_shape_tactic_routing_gate_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_routing_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_target_shape_tactic_routing_bundle"
    assert result["bundle_id"] == "target_shape_tactic_routing_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["route_case_count"] == 5
    assert result["body_material_status"] == "real_ring2_target_shape_routing_refs"
    assert (
        result["routing_evidence_status"]
        == "real_ring2_problem_domain_failure_class_route_refs"
    )
    assert result["receipt_paths"] == [
        "receipts/exported_target_shape_tactic_routing_bundle_validation_result.json"
    ]


def test_target_shape_tactic_routing_receipts_use_real_substrate_contract(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/target_shape_tactic_routing_gate",
        public_root / "fixtures/first_wave/target_shape_tactic_routing_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/target_shape_tactic_routing_gate/input",
        public_root / "receipts/first_wave/target_shape_tactic_routing_gate",
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
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == "real_ring2_target_shape_routing_refs"
        assert (
            payload["routing_evidence_status"]
            == "real_ring2_problem_domain_failure_class_route_refs"
        )
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
