from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import undeclared_library_prior_symbol_classifier
from microcosm_core.organs.undeclared_library_prior_symbol_classifier import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
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
    assert result["source_modules_pass"] is True
    assert result["source_open_body_imports"] == {}
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
    assert result["source_modules_pass"] is True
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 6
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 6
    imported_ids = set(result["source_open_body_imports"]["body_material_ids"])
    assert "provider_receipt_reducer_source_body_import" in imported_ids
    assert "provider_batch_receipt_reduction_matrix_body_import" in imported_ids
    assert all(row["body_in_receipt"] is False for row in result["source_modules"])
    assert all(row["digest_matches"] is True for row in result["source_modules"])
    assert all(row["missing_required_anchors"] == [] for row in result["source_modules"])
    normalized_rows = [
        row
        for row in result["source_modules"]
        if row["source_to_target_relation"]
        == "source_faithful_public_safe_path_normalized_copy"
    ]
    assert {row["module_id"] for row in normalized_rows} == {
        "ring2_premise_index_state_body_import",
        "ring2_premise_retrieval_run_summary_body_import",
    }
    for path in BUNDLE_INPUT.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md", ".py"}:
            text = path.read_text(encoding="utf-8")
            assert "/Users/willcook" not in text
            assert "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL" not in text


def test_symbol_classifier_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "undeclared_library_prior_symbol_classifier"
    )
    args = [
        "run-symbol-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["command_speed"]["freshness_input_count"] == 13
    assert first_card["symbol_classifier"]["classification_count"] == 3
    assert first_card["symbol_classifier"]["premise_count"] == 11
    assert first_card["symbol_classifier"]["undeclared_library_prior_count"] == 1
    assert first_card["symbol_classifier"]["premise_budget_precedence_count"] == 1
    assert first_card["symbol_classifier"]["source_module_count"] == 6
    assert first_card["symbol_classifier"]["verified_source_module_count"] == 6
    assert first_card["source_body_floor"]["status"] == "pass"
    assert first_card["source_body_floor"]["body_material_count"] == 6
    assert first_card["source_body_floor"]["body_material_id_count"] == 6
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "source_modules" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "body_material_ids" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "source_digests" not in _walk_keys(first_card)
    assert "proof_body" not in _walk_keys(first_card)
    assert "private_source_ref" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        undeclared_library_prior_symbol_classifier,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
