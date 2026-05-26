from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_evidence_cell_anchor_resolver import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_anchor_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle"
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


def test_formal_evidence_cell_anchor_resolver_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_evidence_cell_anchor_resolver",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["claim_count"] == 3
    assert result["resolved_cell_count"] == 3
    assert result["unresolved_cell_count"] == 0
    assert result["evidence_cell_count"] == 3
    assert result["source_anchor_count"] == 8
    assert result["machine_anchor_count"] == 3
    assert result["source_modules_pass"] is True
    assert result["source_module_count"] == 0
    assert result["source_open_body_imports"] == {}
    assert result["evidence_anchor_status"] == (
        "real_ring2_verifier_trace_repair_receipt_refs"
    )
    assert (
        result["source_digests"][
            "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/failure_taxonomy_report.json"
        ]
        == "sha256:8b054c57001c432942a7ed97cbd4dca2a2e2b174d9cd31d9121c38c5ecc933af"
    )
    assert any(
        "formal_math_verifier_trace_repair_loop_result.json" in ref
        for ref in result["projection_receipt_refs"]
    )
    verifier_row = next(
        row
        for row in result["claim_resolution_rows"]
        if row["claim_id"] == "claim.verifier_trace_has_runtime_receipt_anchor"
    )
    assert verifier_row["claim_strength"] == "ring2_failure_taxonomy_anchor_present"
    assert verifier_row["machine_anchor_class"] == (
        "real_ring2_verifier_trace_repair_receipt"
    )
    assert any(
        "formal_math_verifier_trace_repair_loop/verifier_trace_repair_board.json"
        in ref
        for ref in verifier_row["source_anchor_refs"]
    )
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_evidence_cell_anchor_receipts_are_public_relative_with_secret_exclusion(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input",
        public_root / "receipts/first_wave/formal_evidence_cell_anchor_resolver",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "private://macro-formal-lab" not in text
        assert "synthetic forbidden proof body" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in payload
        assert "body_redacted" not in _walk_keys(payload)
        assert "proof_body" not in _walk_keys(payload)
        assert "private_source_ref" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_evidence_cell_anchor_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_anchor_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_evidence_cell_anchor_bundle"
    assert result["bundle_id"] == "formal_evidence_cell_anchor_resolver_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["claim_count"] == 3
    assert result["resolved_cell_count"] == 3
    assert result["evidence_cell_count"] == 3
    assert result["source_anchor_count"] == 5
    assert result["source_modules_pass"] is True
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 6
    assert result["source_open_body_imports"]["body_material_count"] == 6
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["source_module_secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["source_module_secret_exclusion_scan"]["scanned_path_count"] == 6
    imported_ids = set(result["source_open_body_imports"]["body_material_ids"])
    assert "paper_module_formal_evidence_auditor_source_body_import" in imported_ids
    assert "formal_evidence_cell_registry_builder_source_body_import" in imported_ids
    assert "formal_evidence_cell_registry_state_body_import" in imported_ids
    assert all(row["body_in_receipt"] is False for row in result["source_modules"])
    assert all(row["digest_matches"] is True for row in result["source_modules"])
    assert result["evidence_anchor_status"] == (
        "real_ring2_verifier_trace_repair_receipt_refs"
    )
    assert any(
        "formal_math_verifier_trace_repair_loop/verifier_trace_repair_board.json"
        in ref
        for ref in result["projection_receipt_refs"]
    )
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False


def test_formal_evidence_cell_anchor_bundle_card_is_compact(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "bundle-card"

    rc = main(
        [
            "run-anchor-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = out_dir / "exported_evidence_cell_anchor_bundle_validation_result.json"

    assert rc == 0
    assert len(captured.encode("utf-8")) < 6000
    assert full_receipt.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "formal_evidence_cell_anchor_resolver"
    assert card["input_mode"] == "exported_evidence_cell_anchor_bundle"
    assert card["bundle_id"] == "formal_evidence_cell_anchor_resolver_runtime_example"
    assert card["counts"]["claim_count"] == 3
    assert card["counts"]["resolved_cell_count"] == 3
    assert card["counts"]["source_anchor_count"] == 5
    assert card["source_summary"]["source_ref_count"] == 14
    assert card["source_summary"]["source_refs_exported"] is False
    assert card["source_module_summary"]["source_modules_pass"] is True
    assert card["source_module_summary"]["source_module_count"] == 6
    assert card["source_module_summary"]["verified_source_module_count"] == 6
    assert card["source_module_summary"]["source_module_rows_exported"] is False
    assert (
        card["source_module_summary"]["source_open_body_imports"][
            "body_material_ids_exported"
        ]
        is False
    )
    assert (
        card["source_module_summary"][
            "source_module_secret_exclusion_scan_summary"
        ]["blocking_hit_count"]
        == 0
    )
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["scan_scope_exported"] is False
    assert card["authority_ceiling"]["theorem_correctness_authority"] is False
    assert card["authority_ceiling"]["formal_proof_authority"] is False
    assert card["no_export_guards"]["proof_bodies_exported"] is False
    assert "source_modules" not in card
    assert "source_refs" not in card
    assert "claim_resolution_rows" not in card
