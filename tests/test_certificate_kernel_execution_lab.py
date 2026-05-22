from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core.organs.certificate_kernel_execution_lab import (
    EXPECTED_NEGATIVE_CASES,
    build_public_readout,
    run,
    run_certificate_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/certificate_kernel_execution_lab/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle"
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


def test_certificate_kernel_execution_lab_runs_lean_cp2_evolve_and_analyzer(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/certificate_kernel_execution_lab",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/certificate_kernel_execution_lab_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    counters = result["authority_counters"]
    assert counters["transition_count"] == 10
    assert counters["accepted_transition_count"] == 7
    assert counters["residual_transition_count"] == 3
    assert counters["cp2_translation_count"] == 2
    assert counters["cp2_downstream_effect_count"] == 2
    assert counters["evolve_candidate_count"] == 2
    assert counters["evolve_accepted_count"] == 2
    assert counters["analyzed_lean_file_count"] == 5
    assert counters["analyzed_declaration_count"] >= 20
    assert counters["oracle_forward_success_increment_count"] == 0
    assert counters["provider_results_counted"] == 0
    assert counters["proof_body_export_count"] == 0
    assert counters["source_mutation_count"] == 0
    assert counters["macro_private_body_import_count"] == 0

    transparency = result["receipt_transparency_contract"]
    assert transparency["receipt_body_is_public_evidence"] is True
    assert transparency["redaction_scope"] == "dangerous_payload_fields_only"
    assert "theorem_or_declaration_names" in transparency["required_public_evidence_fields"]
    assert "proof_body" in transparency["forbidden_payload_fields"]
    assert "provider_text" in transparency["forbidden_payload_fields"]

    analyzer = result["lean_analyzer_receipt"]
    assert all(
        file_row["source_ref"].startswith(
            "fixtures/first_wave/certificate_kernel_execution_lab/input/lake_project/"
        )
        for file_row in analyzer["files"]
    )
    assert all("/private/" not in file_row["source_ref"] for file_row in analyzer["files"])
    assert all(not Path(file_row["source_ref"]).is_absolute() for file_row in analyzer["files"])
    declarations = {
        declaration
        for file_row in analyzer["files"]
        for declaration in file_row["declarations"]
    }
    assert "NatSumCertificate" in declarations
    assert "validateNatSumCertificate" in declarations
    assert "BoundedOrderCertificate" in declarations
    assert "validateBoundedOrderCertificate" in declarations
    assert "cert_8_13_21_valid" in declarations
    assert "order_cert_3_4_mod5_valid" in declarations
    assert analyzer["generated_certificates_separate_from_kernel"] is True

    claim_separation = result["claim_separation"]
    assert len(claim_separation["lean_verified"]) == 7
    assert len(claim_separation["provider_suggested"]) == 2
    assert len(claim_separation["oracle_compared"]) == 2
    assert len(claim_separation["cp2_translated"]) == 2
    assert len(claim_separation["retrieval_miss"]) == 2
    assert len(claim_separation["proof_synthesis_fail"]) == 1
    assert len(claim_separation["evolve_accepted"]) == 2


def test_certificate_kernel_execution_lab_bundle_is_public_structured(
    tmp_path: Path,
) -> None:
    result = run_certificate_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_certificate_kernel_execution_lab_bundle"
    assert result["bundle_id"] == "public_certificate_kernel_execution_lab_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["authority_counters"]["accepted_transition_count"] == 7
    assert result["authority_counters"]["cp2_downstream_effect_count"] == 2
    assert result["authority_counters"]["evolve_accepted_count"] == 2
    assert result["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True


def test_certificate_kernel_execution_lab_receipts_are_transparent_without_bodies(
    tmp_path: Path,
) -> None:
    out = tmp_path / "receipts/first_wave/certificate_kernel_execution_lab"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "certificate_kernel_execution_lab_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    assert payload["receipt_transparency_contract"]["redaction_scope"] == (
        "dangerous_payload_fields_only"
    )
    assert payload["lean_analyzer_receipt"]["declaration_count"] >= 20
    assert all(
        "/private/" not in row["source_ref"]
        for row in payload["lean_analyzer_receipt"]["files"]
    )
    assert payload["transition_trace"][0]["problem_id"] == "cert_2_3_5"
    assert payload["transition_trace"][0]["lean_return_code"] == 0
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["provider_calls_authorized"] is False
    assert payload["source_mutation_authorized"] is False
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)


def test_certificate_kernel_execution_lab_public_readout_is_cold_reader_route(
    tmp_path: Path,
) -> None:
    readout = build_public_readout(
        MICROCOSM_ROOT,
        out=tmp_path
        / "receipts/first_wave/certificate_kernel_execution_lab/"
        "certificate_kernel_execution_lab_public_readout.json",
    )

    assert readout["status"] == "pass"
    assert readout["schema_version"] == "certificate_kernel_execution_lab_public_readout_v1"
    assert readout["readout_id"] == "certificate_kernel_execution_lab_runtime_readout"
    assert [
        stage["stage_id"]
        for stage in readout["public_flow"]
    ] == [
        "public_certificate_kernel",
        "generated_certificate_rows",
        "lean_lake_execution",
        "transition_adjudication",
        "cp2_translation_rerun",
        "bounded_evolve_policy_rerun",
        "authority_counter_boundary",
    ]
    families = {
        family["family_id"]: family for family in readout["public_flow"][1]["certificate_families"]
    }
    assert families["nat_sum_certificate"]["valid_row_count"] == 3
    assert families["bounded_order_certificate"]["valid_row_count"] == 2
    counters = readout["authority_counters"]
    assert counters["accepted_transition_count"] == 7
    assert counters["residual_transition_count"] == 3
    assert counters["cp2_downstream_effect_count"] == 2
    assert counters["evolve_accepted_count"] == 2
    assert counters["provider_results_counted"] == 0
    assert counters["oracle_forward_success_increment_count"] == 0
    assert counters["proof_body_export_count"] == 0
    assert counters["source_mutation_count"] == 0
    assert readout["dangerous_payload_absent"] is True
    assert readout["receipt_transparency_contract"]["receipt_body_is_public_evidence"] is True
    text = json.dumps(readout, sort_keys=True)
    assert "/private/" not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "proof_body" not in _walk_keys(readout)
    assert "provider_text" not in _walk_keys(readout)


def test_certificate_kernel_execution_lab_readout_out_keeps_repo_root_path(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    output_path = (
        Path("microcosm-substrate")
        / "receipts/first_wave/certificate_kernel_execution_lab/"
        / "certificate_kernel_execution_lab_public_readout.json"
    )
    monkeypatch.chdir(tmp_path)

    build_public_readout(public_root, out=output_path)

    assert (public_root / output_path.relative_to("microcosm-substrate")).is_file()
    assert not (public_root / output_path).exists()
