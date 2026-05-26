from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import verifier_lab_kernel
from microcosm_core.organs.verifier_lab_kernel import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_kernel_bundle,
    validate_source_module_imports,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/verifier_lab_kernel/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
)
SUBSTRATE_BINDINGS = (
    MICROCOSM_ROOT.parent
    / "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
)
SUBSTRATE_BINDINGS_SHA256 = (
    "sha256:4d980e40faf0a565ff8374370ed8a4c50a147f815f422fb925ad07f9b37b5a45"
)
EXPECTED_COMPONENTS = {
    "corpus_readiness_mathlib_absence_gate",
    "formal_math_lean_proof_witness",
    "formal_math_premise_retrieval",
    "formal_math_verifier_trace_repair_loop",
    "lean_std_premise_index",
    "proof_diagnostic_evidence_spine",
    "ring2_premise_retrieval_precision_recall_harness",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
}


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
    assert set(result["component_statuses"]) == EXPECTED_COMPONENTS
    assert all(status == "pass" for status in result["component_statuses"].values())
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8
    assert result["target_shape_route_case_count"] >= 4
    assert result["verifier_trace_attempt_count"] >= 3
    metrics = result["proof_lab_component_metrics"]
    assert metrics["corpus_count"] == 7
    assert metrics["lean_std_premise_count"] == 11
    assert metrics["retrieval_query_count"] == 4
    assert metrics["ring2_problem_count"] == 10
    assert metrics["ring2_mean_precision_at_k"] == 0.36
    assert metrics["proof_diagnostic_accepted_count"] >= 2
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


def test_verifier_lab_kernel_fixture_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    out_dir = tmp_path / "receipts/first_wave/verifier_lab_kernel"
    acceptance_out = (
        tmp_path
        / "receipts/acceptance/first_wave/verifier_lab_kernel_fixture_acceptance.json"
    )
    result = run(
        FIXTURE_INPUT,
        out_dir,
        command="pytest",
        acceptance_out=acceptance_out,
    )
    assert result["status"] == "pass"
    assert result["cache_status"] == "rebuilt"

    def fail_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh fixture receipt should be reused")

    monkeypatch.setattr(verifier_lab_kernel, "_build_result", fail_rebuild)
    cached = run(
        FIXTURE_INPUT,
        out_dir,
        command="pytest",
        acceptance_out=acceptance_out,
    )

    assert cached["status"] == "pass"
    assert cached["cache_status"] == "fresh_receipt_reused"
    assert cached["freshness_basis"]["input_mode"] == "first_wave_fixture"
    assert cached["freshness_basis"]["tracked_dependency_count"] > 10
    assert cached["receipt_paths"] == result["receipt_paths"]


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

    for component_receipt in (
        public_root / "receipts/first_wave/verifier_lab_kernel/components"
    ).rglob("*.json"):
        text = component_receipt.read_text(encoding="utf-8")
        assert "private_state_scan" not in text
        assert "body_redacted" not in text
        assert "public_replacement_ref" not in text


def test_verifier_lab_kernel_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
    monkeypatch,
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
    assert result["proof_lab_route"]["status"] == "pass"
    assert result["proof_lab_route_id"] == "formal_prover_context_strategy_gate"
    assert result["proof_lab_route_source_sha256"] == SUBSTRATE_BINDINGS_SHA256
    assert result["proof_lab_route_component_count"] == len(EXPECTED_COMPONENTS)
    assert result["source_module_imports"]["status"] == "pass"
    assert result["source_module_imports"]["module_count"] == 10
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 10
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["body_copied_material_count"] == 10
    assert set(result["component_statuses"]) == EXPECTED_COMPONENTS
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert all(status == "pass" for status in result["component_statuses"].values())
    assert result["lean_lake_return_code"] == 0
    assert result["lean_compiled_declaration_count"] == 8
    assert result["proof_lab_component_metrics"]["corpus_count"] == 7
    assert result["proof_lab_component_metrics"]["lean_std_premise_count"] == 11
    assert result["proof_lab_component_metrics"]["retrieval_query_count"] == 4
    assert result["proof_lab_component_metrics"]["ring2_mean_recall_at_k"] == 0.9
    assert result["proof_lab_component_metrics"]["proof_diagnostic_accepted_count"] == 1
    assert len(result["claim_separation"]["provider_suggested"]) == 1
    assert len(result["claim_separation"]["cp2_translated"]) == 2
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
    assert result["cache_status"] == "rebuilt"
    assert result["freshness_basis"]["tracked_dependency_count"] > 10

    def fail_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh exported verifier-lab receipt should be reused")

    monkeypatch.setattr(verifier_lab_kernel, "_build_result", fail_rebuild)
    cached = run_kernel_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/verifier_lab_kernel",
        command="pytest",
    )
    assert cached["cache_status"] == "fresh_receipt_reused"
    assert cached["status"] == "pass"
    assert cached["receipt_paths"] == result["receipt_paths"]


def test_verifier_lab_kernel_source_module_manifest_is_exact_public_body_floor() -> None:
    manifest_path = BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_imports = validate_source_module_imports(
        BUNDLE_INPUT,
        public_root=MICROCOSM_ROOT,
    )

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 10
    assert source_imports["status"] == "pass"
    assert source_imports["module_count"] == 10

    module_ids = {row["module_id"] for row in source_imports["modules"]}
    assert "verifier_lab_kernel_source_body_import" in module_ids
    for row in manifest["modules"]:
        source_path = MICROCOSM_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target_path = MICROCOSM_ROOT / target_ref
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["material_class"] == "public_macro_tool_body"
        assert source_path.read_bytes() == target_path.read_bytes()


def test_verifier_lab_kernel_route_slice_is_source_faithful() -> None:
    route = json.loads((BUNDLE_INPUT / "proof_lab_route.json").read_text(encoding="utf-8"))
    source = json.loads(SUBSTRATE_BINDINGS.read_text(encoding="utf-8"))
    source_route = next(
        row
        for row in source["foundation_combination_routes"]
        if row["route_id"] == "formal_prover_context_strategy_gate"
    )

    assert route["schema_version"] == "formal_prover_context_strategy_gate_public_route_slice_v1"
    assert route["source_ref"] == "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
    assert route["source_sha256"] == SUBSTRATE_BINDINGS_SHA256
    assert route["classification"] == "source_faithful_refactor"
    assert route["foundation_route"] == source_route
    assert set(route["required_component_organs"]) == EXPECTED_COMPONENTS
    assert route["body_in_receipt"] is False
