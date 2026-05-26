from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from microcosm_core.organs.lean_std_premise_index import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_index_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/lean_std_premise_index/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT / "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle"
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


def test_lean_std_premise_index_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/lean_std_premise_index",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/lean_std_premise_index_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["premise_count"] == 11
    assert set(result["namespace_counts"]) == {"Bool", "Iff", "List", "Nat"}
    assert result["authority_ceiling"]["mathlib_allowed"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["body_copied_material_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_lean_std_premise_index_imports_real_macro_premise_index(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/lean_std_premise_index",
        command="pytest",
    )
    premise_index = json.loads((FIXTURE_INPUT / "premise_index.json").read_text())
    copied = result["copied_material"][0]

    assert premise_index["source_ref"] == (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json"
    )
    assert premise_index["source_sha256"] == (
        "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1"
    )
    assert all(row["body_copied"] is True for row in premise_index["premises"])
    assert all(
        row["source_ref"].startswith("lean-toolchain://leanprover/lean4/v4.29.1/src/lean/Init/")
        for row in premise_index["premises"]
    )
    assert copied["classification"] == "copied_non_secret_macro_body_with_provenance"
    assert copied["source_ref"] == premise_index["source_ref"]
    assert copied["source_sha256"] == premise_index["source_sha256"]
    assert "fixtures/first_wave/lean_std_premise_index/input/premise_index.json" in copied["target_refs"]


def test_lean_std_premise_index_source_open_manifest_counts_body_floor() -> None:
    source_path = (
        MICROCOSM_ROOT.parent
        / "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json"
    )
    public_fixture_path = FIXTURE_INPUT / "premise_index.json"
    public_bundle_path = EXPORTED_BUNDLE / "premise_index.json"
    source_manifest = json.loads((EXPORTED_BUNDLE / "source_module_manifest.json").read_text())
    fixture_manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/lean_std_premise_index.fixture_manifest.json"
        ).read_text()
    )
    bundle_manifest = json.loads((EXPORTED_BUNDLE / "bundle_manifest.json").read_text())

    module = source_manifest["modules"][0]
    body_floor = fixture_manifest["source_open_body_imports"]
    copied_artifact = bundle_manifest["copied_macro_body_artifacts"][0]
    source = json.loads(source_path.read_text())
    public_fixture = json.loads(public_fixture_path.read_text())
    public_bundle = json.loads(public_bundle_path.read_text())

    assert source_manifest["module_count"] == 1
    assert module["module_id"] == "lean_std_toolchain_premise_index_body_import"
    assert module["source_to_target_relation"] == "source_faithful_normalized_copy"
    assert module["source_sha256"] == "sha256:" + sha256(source_path.read_bytes()).hexdigest()
    assert module["target_sha256"] == "sha256:" + sha256(public_bundle_path.read_bytes()).hexdigest()
    assert public_fixture == public_bundle
    assert copied_artifact["module_id"] == module["module_id"]
    assert body_floor["body_material_ids"] == [module["module_id"]]
    assert body_floor["body_material_count"] == 1
    assert body_floor["body_in_receipt"] is False
    assert body_floor["authority_ceiling"]["proof_body_or_oracle_proof_text_exported"] is False

    source_rows = source["premises"]
    public_rows = public_bundle["premises"]
    assert len(public_rows) == len(source_rows) == 11
    for source_row, public_row in zip(source_rows, public_rows):
        assert public_row["premise_id"] == source_row["premise_id"]
        assert public_row["theorem_or_def_name"] == source_row["theorem_or_def_name"]
        assert public_row["namespace"] == source_row["namespace"]
        assert public_row["retrieval_terms"] == source_row["retrieval_terms"]
        assert public_row["allowed_for_split"] == source_row["allowed_for_split"]
        assert public_row["statement_excerpt"] == source_row["statement_excerpt"]
        assert public_row["source_ref"].startswith("lean-toolchain://")
        assert public_row["body_copied"] is True
        assert "proof_body" not in public_row
        assert "oracle_needed_premise_ids" not in public_row


def test_lean_std_premise_index_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_index_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/lean_std_premise_index",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_lean_std_premise_index_bundle"
    assert result["bundle_id"] == "public_lean_std_premise_index_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["premise_count"] == 11
    assert result["closed_index_only"] is True
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["body_copied_material_count"] == 1


def test_lean_std_premise_index_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    out = tmp_path / "receipts/first_wave/lean_std_premise_index"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "lean_std_premise_index_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert payload["body_copied_material_count"] == 1
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in payload
    assert "body_redacted" not in _walk_keys(payload)
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
