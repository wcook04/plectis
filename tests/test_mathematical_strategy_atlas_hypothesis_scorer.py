from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer import (
    EXPECTED_NEGATIVE_CASES,
    SOURCE_PATTERN_IDS,
    run,
    run_strategy_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mathematical_strategy_atlas_hypothesis_scorer/exported_mathematical_strategy_atlas_bundle"
)
SOURCE_ARTIFACT_REFS = [
    "tools/meta/factory/run_prover_graph_benchmark.py",
    "tools/meta/factory/reduce_prover_provider_receipts.py",
]


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


def test_mathematical_strategy_atlas_scorer_covers_negative_cases(
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
    assert result["strategy_count"] == 4
    assert result["problem_count"] == 3
    assert result["hypothesis_case_count"] == 3
    assert result["selected_strategy_ids"] == [
        "iff_split",
        "recursive_data_induction",
        "unknown",
    ]
    assert all("score" not in row for row in result["scored_cases"])
    assert [row["feature_overlap_count"] for row in result["scored_cases"]] == [3, 3, 0]
    assert result["strategy_selection_miss_case_ids"] == ["typed_unknown_strategy_miss"]
    assert result["all_expectations_met"] is True
    assert result["strategy_board"]["public_contract"]["strategy_selected_pre_oracle"] is True
    assert (
        result["strategy_board"]["public_contract"]["drilldown_regression_not_product_organ"]
        is True
    )
    assert result["authority_ceiling"]["oracle_label_visibility_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_mathematical_strategy_atlas_scorer_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_strategy_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_mathematical_strategy_atlas_bundle"
    assert result["bundle_id"] == "mathematical_strategy_atlas_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["strategy_selection_miss_case_ids"] == ["typed_unknown_strategy_miss"]
    assert result["body_material_status"] == (
        "copied_non_secret_macro_strategy_atlas_tool_body_with_provenance"
    )
    assert (
        result["source_module_import_status"]
        == "copied_strategy_atlas_macro_tool_source_modules_verified"
    )
    assert result["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["source_modules_pass"] is True
    assert all(row["exists"] is True for row in result["source_module_imports"])
    assert all(row["digest_match"] is True for row in result["source_module_imports"])
    assert result["strategy_board"]["source_body_import_projection"][
        "copied_source_artifact_count"
    ] == len(SOURCE_ARTIFACT_REFS)
    assert result["receipt_paths"] == [
        "receipts/exported_mathematical_strategy_atlas_bundle_validation_result.json"
    ]


def test_mathematical_strategy_atlas_exported_source_modules_are_exact_copies() -> None:
    manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    modules = {row["source_ref"]: row for row in manifest["modules"]}
    assert sorted(modules) == sorted(SOURCE_ARTIFACT_REFS)
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False

    bundle_manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert bundle_manifest["source_module_manifest_ref"] == "source_module_manifest.json"
    assert len(bundle_manifest["copied_macro_body_artifacts"]) == len(
        SOURCE_ARTIFACT_REFS
    )

    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = EXPORTED_BUNDLE_INPUT / "source_artifacts" / source_ref
        assert target.is_file()
        source_bytes = source.read_bytes()
        target_bytes = target.read_bytes()
        digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        assert source_bytes == target_bytes
        assert modules[source_ref]["sha256"] == digest
        assert modules[source_ref]["body_in_receipt"] is False


def test_mathematical_strategy_atlas_exported_bundle_receipt_omits_source_bodies(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mathematical_strategy_atlas_hypothesis_scorer",
        public_root / "examples/mathematical_strategy_atlas_hypothesis_scorer",
    )

    result = run_strategy_bundle(
        public_root
        / "examples/mathematical_strategy_atlas_hypothesis_scorer/exported_mathematical_strategy_atlas_bundle",
        public_root / "receipts/mathematical_strategy_atlas_hypothesis_scorer",
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
        assert "def _strategy_cards" not in text
        assert "def _provider_value" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["source_modules_pass"] is True
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_mathematical_strategy_atlas_receipts_are_redacted_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer",
        public_root / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer",
    )

    result = run(
        public_root / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input",
        public_root / "receipts/first_wave/mathematical_strategy_atlas_hypothesis_scorer",
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
        assert "synthetic forbidden proof material" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["authority_ceiling"]["oracle_label_visibility_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
