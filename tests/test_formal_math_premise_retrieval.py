from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_math_premise_retrieval import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_retrieval_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_premise_retrieval/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle"
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


def test_formal_math_premise_retrieval_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_math_premise_retrieval",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_math_premise_retrieval_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["premise_count"] == 11
    assert result["query_count"] == 4
    assert result["recipe_count"] == 3
    assert result["strategy_case_count"] == 4
    assert result["mean_public_retrieval_recall"] == 1.0
    assert result["body_copied_material_count"] == 1
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert result["authority_ceiling"]["proof_bodies_allowed"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_premise_retrieval_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_premise_retrieval",
        public_root / "fixtures/first_wave/formal_math_premise_retrieval",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_premise_retrieval/input",
        public_root / "receipts/first_wave/formal_math_premise_retrieval",
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
        assert "synthetic forbidden proof payload" not in text
        assert '"proof_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert "proof_body" not in _walk_keys(payload)


def test_formal_math_premise_retrieval_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_retrieval_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_premise_retrieval_bundle"
    assert result["bundle_id"] == "formal_math_premise_retrieval_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["premise_count"] == 11
    assert result["query_count"] == 4
    assert result["mean_public_retrieval_recall"] == 1.0
    assert result["body_copied_material_count"] == 1
    assert result["premise_retrieval_board"]["formal_proof_authority"] is False


def test_formal_math_premise_retrieval_imports_real_macro_premise_index() -> None:
    premise_index = json.loads(
        (FIXTURE_INPUT / "premise_index.json").read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (FIXTURE_INPUT / "projection_protocol.json").read_text(encoding="utf-8")
    )

    assert premise_index["index_id"] == "lean_std_toolchain_premise_index_v0_public_import"
    assert premise_index["source_ref"] == (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_index.json"
    )
    assert premise_index["source_sha256"] == (
        "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1"
    )
    assert premise_index["premise_count"] == 11
    assert all(row["body_copied"] is True for row in premise_index["premises"])
    assert all("/Users/" not in row["source_ref"] for row in premise_index["premises"])
    assert {row["premise_id"] for row in premise_index["premises"]} >= {
        "premise_nat_add_comm",
        "premise_bool_not_not",
        "premise_list_length_append",
        "premise_iff_intro",
    }
    copied = protocol["copied_material"][0]
    assert copied["classification"] == "copied_non_secret_macro_body_with_provenance"
    assert copied["body_copied"] is True
    assert copied["source_sha256"] == premise_index["source_sha256"]
