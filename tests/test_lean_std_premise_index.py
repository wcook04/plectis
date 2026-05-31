from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from microcosm_core.organs.lean_std_premise_index import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    _line_count,
    main,
    run,
    run_index_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/lean_std_premise_index/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT / "examples/lean_std_premise_index/exported_lean_std_premise_index_bundle"
)
SOURCE_RUN = (
    MICROCOSM_ROOT.parent
    / "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
)
SOURCE_MODULE_ROOT = (
    EXPORTED_BUNDLE
    / "source_modules/ring2_runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
)
RING2_SOURCE_MODULES = [
    (
        "lean_std_ring2_top_aggregate_report_body_import",
        "aggregate_report.json",
        "public_macro_receipt_body",
    ),
    (
        "lean_std_premise_retrieval_aggregate_report_body_import",
        "premise_retrieval_graph_v0/aggregate_report.json",
        "public_macro_receipt_body",
    ),
    (
        "lean_std_premise_retrieval_cost_metrics_body_import",
        "premise_retrieval_graph_v0/cost_metrics.json",
        "public_macro_receipt_body",
    ),
    (
        "lean_std_premise_retrieval_graph_update_candidates_body_import",
        "premise_retrieval_graph_v0/graph_update_candidates.json",
        "public_macro_pattern_body",
    ),
    (
        "lean_std_premise_retrieval_graph_variant_body_import",
        "premise_retrieval_graph_v0/graph_variant.json",
        "public_macro_pattern_body",
    ),
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


def test_lean_std_premise_index_line_count_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    empty = tmp_path / "empty_source_module.py"
    source.write_text("one\n\ntwo", encoding="utf-8")
    empty.write_text("", encoding="utf-8")
    guarded_paths = {source, empty}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty) == 1


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
    assert result["body_copied_material_count"] == 6
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
    source_path = SOURCE_RUN / "premise_index.json"
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

    modules_by_id = {row["module_id"]: row for row in source_manifest["modules"]}
    module = modules_by_id["lean_std_toolchain_premise_index_body_import"]
    body_floor = fixture_manifest["source_open_body_imports"]
    copied_artifacts = {
        row["module_id"]: row for row in bundle_manifest["copied_macro_body_artifacts"]
    }
    copied_artifact = copied_artifacts[module["module_id"]]
    source = json.loads(source_path.read_text())
    public_fixture = json.loads(public_fixture_path.read_text())
    public_bundle = json.loads(public_bundle_path.read_text())

    expected_module_ids = [
        "lean_std_toolchain_premise_index_body_import",
        *[module_id for module_id, _rel, _material_class in RING2_SOURCE_MODULES],
    ]
    assert source_manifest["module_count"] == 6
    assert set(modules_by_id) == set(expected_module_ids)
    assert module["module_id"] == "lean_std_toolchain_premise_index_body_import"
    assert module["source_to_target_relation"] == "source_faithful_normalized_copy"
    assert module["source_sha256"] == "sha256:" + sha256(source_path.read_bytes()).hexdigest()
    assert module["target_sha256"] == "sha256:" + sha256(public_bundle_path.read_bytes()).hexdigest()
    assert public_fixture == public_bundle
    assert copied_artifact["module_id"] == module["module_id"]
    assert body_floor["body_material_ids"] == expected_module_ids
    assert body_floor["body_material_count"] == 6
    assert body_floor["body_in_receipt"] is False
    assert body_floor["authority_ceiling"]["proof_body_or_oracle_proof_text_exported"] is False

    for module_id, rel_path, material_class in RING2_SOURCE_MODULES:
        source_file = SOURCE_RUN / rel_path
        target_file = SOURCE_MODULE_ROOT / rel_path
        source_bytes = source_file.read_bytes()
        target_bytes = target_file.read_bytes()
        target_text = target_file.read_text()
        row = modules_by_id[module_id]
        artifact = copied_artifacts[module_id]

        assert source_bytes == target_bytes
        assert row["material_class"] == material_class
        assert row["source_sha256"] == "sha256:" + sha256(source_bytes).hexdigest()
        assert row["target_sha256"] == "sha256:" + sha256(target_bytes).hexdigest()
        assert artifact["target_sha256"] == row["target_sha256"]
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["source_to_target_relation"] == "exact_public_safe_macro_copy"
        assert "/Users/" not in target_text
        assert "provider_payload" not in target_text
        assert "oracle_needed_premise_ids" not in target_text

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
    assert result["body_copied_material_count"] == 6
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 6
    assert len(result["source_module_imports"]) == 6


def test_lean_std_premise_index_bundle_card_is_compact_and_source_open(
    tmp_path: Path,
    capsys: Any,
) -> None:
    rc = main(
        [
            "run-index-bundle",
            "--input",
            str(EXPORTED_BUNDLE),
            "--out",
            str(tmp_path / "runtime/organs/lean_std_premise_index"),
            "--card",
        ]
    )
    stdout = capsys.readouterr().out
    card = json.loads(stdout)

    assert rc == 0
    assert len(stdout.encode("utf-8")) < 3600
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "lean_std_premise_index"
    assert card["input_mode"] == "exported_lean_std_premise_index_bundle"
    assert card["premise_count"] == 11
    assert set(card["namespace_counts"]) == {"Bool", "Iff", "List", "Nat"}
    assert sum(card["namespace_counts"].values()) == 11
    assert card["source_summary"]["source_ref_count"] == 8
    assert card["source_summary"]["body_copied_material_count"] == 6
    assert card["source_summary"]["source_module_manifest_status"] == "pass"
    assert card["source_summary"]["verified_source_module_count"] == 6
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["body_text_exported"] is False
    assert card["authority_ceiling"]["mathlib_allowed"] is False
    assert card["authority_ceiling"]["proof_bodies_allowed"] is False
    assert card["output_economy"]["stdout_mode"] == "card"
    assert card["output_economy"]["full_payload_drilldown"] == "rerun without --card"
    assert "copied_material" not in card
    assert "premise_ids" not in card
    assert "findings" not in card

    receipt_path = (
        tmp_path
        / "runtime/organs/lean_std_premise_index/"
        "exported_lean_std_premise_index_bundle_validation_result.json"
    )
    assert receipt_path.is_file()


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
    assert payload["body_copied_material_count"] == 6
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in payload
    assert "body_redacted" not in _walk_keys(payload)
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
