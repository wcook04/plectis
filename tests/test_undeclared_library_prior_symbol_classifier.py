from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.undeclared_library_prior_symbol_classifier import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_symbol_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/undeclared_library_prior_symbol_classifier/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle"
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


def test_undeclared_library_prior_symbol_classifier_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/undeclared_library_prior_symbol_classifier",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["premise_count"] == 11
    assert result["classification_count"] == 3
    assert result["undeclared_library_prior_count"] == 1
    assert result["premise_budget_precedence_count"] == 1
    assert result["bridge_escalation_count"] == 1
    assert result["retry_count"] == 1
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["symbol_boundary_status"] == (
        "real_lean_std_symbol_boundary_and_mathlib_absence_context"
    )
    assert result["toolchain_boundary_status"] == "real_lean_4_29_1_std_mathlib_absence_probe"
    assert result["body_in_receipt"] is False
    assert result["source_digests"][
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json"
    ] == "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1"
    assert "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_retrieval_graph_v0/run_summary.json" in result["source_refs"]
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_symbol_classifier_receipts_are_real_substrate_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/undeclared_library_prior_symbol_classifier",
        public_root / "fixtures/first_wave/undeclared_library_prior_symbol_classifier",
    )

    result = run(
        public_root / "fixtures/first_wave/undeclared_library_prior_symbol_classifier/input",
        public_root / "receipts/first_wave/undeclared_library_prior_symbol_classifier",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/undeclared_library_prior_symbol_classifier_fixture_acceptance.json"
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
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        assert "macro-private:formal-lab" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
        assert payload["body_in_receipt"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["secret_exclusion_scan"]["real_substrate_default"] is True
        assert "proof_body" not in _walk_keys(payload)
        assert "private_source_ref" not in _walk_keys(payload)


def test_symbol_classifier_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_symbol_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/undeclared_library_prior_symbol_classifier",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_symbol_classifier_bundle"
    assert result["bundle_id"] == "undeclared_library_prior_symbol_classifier_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["classification_count"] == 3
    assert result["premise_count"] == 11
    assert result["undeclared_library_prior_count"] == 1
    assert result["premise_budget_precedence_count"] == 1
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["symbol_boundary_status"] == (
        "real_lean_std_symbol_boundary_and_mathlib_absence_context"
    )
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
