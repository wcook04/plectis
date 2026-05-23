from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_math_verifier_trace_repair_loop import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_loop_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/formal_math_verifier_trace_repair_loop/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle"
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


def test_formal_math_verifier_trace_repair_loop_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_math_verifier_trace_repair_loop",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_math_verifier_trace_repair_loop_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["attempt_count"] == 5
    assert result["trace_event_count"] == 15
    assert result["repair_action_count"] == 5
    assert result["cold_rerun_promotion_count"] == 3
    assert result["failure_mode_count"] == 3
    assert result["curriculum_edge_count"] == 3
    assert (
        result["macro_run_id"]
        == "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
    )
    assert (
        result["body_material_status"]
        == "copied_non_secret_macro_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 3
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
    source_digests = result["source_digests"]
    assert (
        source_digests[
            "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/run_summary.json"
        ]
        == "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008"
    )
    copied_material_ids = {material["material_id"] for material in result["copied_material"]}
    assert copied_material_ids == {
        "ring2_premise_retrieval_failure_trace_rows",
        "ring2_premise_retrieval_graph_update_candidates",
        "ring2_oracle_repair_cold_rerun_contrast_rows",
    }
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["authority_ceiling"]["human_approval_as_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_verifier_trace_repair_receipts_are_public_relative_and_provenanced(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_verifier_trace_repair_loop",
        public_root / "fixtures/first_wave/formal_math_verifier_trace_repair_loop",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_verifier_trace_repair_loop/input",
        public_root / "receipts/first_wave/formal_math_verifier_trace_repair_loop",
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
        assert "synthetic" not in text
        assert "body_redacted" not in text
        assert "private_state_scan" not in text
        assert "public_replacement" not in text
        assert '"proof_body":' not in text
        assert '"provider_payload_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert (
            payload["body_material_status"]
            == "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["body_copied_material_count"] == 3
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in _walk_keys(payload)
        assert "body_redacted" not in _walk_keys(payload)
        assert "proof_body" not in _walk_keys(payload)
        assert "provider_payload_body" not in _walk_keys(payload)


def test_formal_math_verifier_trace_repair_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_loop_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_verifier_trace_repair_bundle"
    assert result["bundle_id"] == "formal_math_verifier_trace_repair_loop_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["attempt_count"] == 5
    assert result["trace_event_count"] == 15
    assert result["repair_action_count"] == 5
    assert result["cold_rerun_promotion_count"] == 3
    assert (
        result["body_material_status"]
        == "copied_non_secret_macro_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 3
    assert result["authority_ceiling"]["formal_proof_authority"] is False
