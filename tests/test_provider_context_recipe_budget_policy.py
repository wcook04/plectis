from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.provider_context_recipe_budget_policy import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    RESULT_NAME,
    _line_count,
    main,
    run,
    run_budget_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/provider_context_recipe_budget_policy/input"
PROVIDER_CONTEXT_SOURCE_MODULE_IDS = [
    "provider_context_batch_calibration_report_body_import",
    "provider_context_compute_provider_standard_body_import",
    "provider_context_formal_ladder_eval_body_import",
    "provider_context_graph_benchmark_body_import",
    "provider_context_provider_adapter_standard_body_import",
    "provider_context_provider_navigation_transform_receipt_standard_body_import",
    "provider_context_receipt_reducer_body_import",
    "provider_context_transform_job_standard_body_import",
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


def test_provider_context_line_count_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    empty_source = tmp_path / "empty_source_module.py"
    source.write_text("one\n\ntwo", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty_source) == 1


def test_provider_context_recipe_budget_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/provider_context_recipe_budget_policy",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/provider_context_recipe_budget_policy_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["recipe_count"] == 6
    assert result["recipe_ids"] == [
        "fewshot_64kb",
        "minimal_4kb",
        "premise_16kb",
        "repair_32kb",
        "skill_32kb",
        "strategy_classification_4kb",
    ]
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["source_module_import_status"] == "pass"
    assert result["source_module_count"] == len(PROVIDER_CONTEXT_SOURCE_MODULE_IDS)
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        for code in codes:
            assert code in result["observed_negative_cases"][case_id]


def test_provider_context_budget_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/provider_context_recipe_budget_policy",
        public_root / "fixtures/first_wave/provider_context_recipe_budget_policy",
    )
    result = run(
        public_root / "fixtures/first_wave/provider_context_recipe_budget_policy/input",
        public_root / "receipts/first_wave/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_path in result["receipt_paths"]:
        assert not Path(receipt_path).is_absolute()
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        if "source_module_import_status" in payload:
            assert payload["source_module_import_status"] == "pass"
        if "source_module_import" in payload:
            assert payload["source_module_import"]["status"] == "pass"
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_provider_context_budget_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    result = run_budget_bundle(
        public_root / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_provider_context_budget_bundle"
    assert result["bundle_id"] == "provider_context_budget_runtime_example"
    assert result["source_module_import_status"] == "pass"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["deliverable_routes"]["premise_16kb"] == "ranked_premise_ids"
    assert result["deliverable_routes"]["strategy_classification_4kb"] == (
        "strategy_id_classification"
    )
    assert result["context_packets"][4]["omitted_section_ids"] == ["fewshot_examples"]
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["truth_side_material_authorized"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle_validation_result.json"
        )
    ]


def test_provider_context_fixture_card_stdout_is_compact_and_keeps_full_receipts(
    tmp_path: Path,
    capsys,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/provider_context_recipe_budget_policy",
        public_root / "fixtures/first_wave/provider_context_recipe_budget_policy",
    )
    out_dir = public_root / "receipts/first_wave/provider_context_recipe_budget_policy"
    rc = main(
        [
            "run",
            "--input",
            str(public_root / "fixtures/first_wave/provider_context_recipe_budget_policy/input"),
            "--out",
            str(out_dir),
            "--card",
        ]
    )
    captured = capsys.readouterr().out
    card = json.loads(captured)
    card_keys = set(_walk_keys(card))
    full_result = json.loads((out_dir / RESULT_NAME).read_text(encoding="utf-8"))

    assert rc == 0
    assert len(captured.encode("utf-8")) < 6000
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "fixture_input"
    assert card["provider_context_summary"]["recipe_count"] == 6
    assert card["provider_context_summary"]["context_packet_count"] == 6
    assert card["provider_context_summary"]["context_packets_exported"] is False
    assert card["provider_context_summary"]["source_module_count"] == len(
        PROVIDER_CONTEXT_SOURCE_MODULE_IDS
    )
    assert card["negative_case_coverage"]["expected_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["observed_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["private_state_scan_summary"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["provider_calls_authorized"] is False
    assert card["receipt_summary"]["full_receipts_written"] is True
    assert card["no_export_guards"]["receipt_paths_exported"] is False
    assert "context_packets" not in card_keys
    assert "source_module_imports" not in card_keys
    assert "observed_negative_cases" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "anti_claim" not in card_keys
    assert "hits" not in card_keys
    assert "scan_scope" not in card_keys
    assert full_result["status"] == "pass"
    assert set(full_result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert full_result["context_packets"]


def test_provider_context_bundle_card_stdout_is_compact_and_keeps_full_receipt(
    tmp_path: Path,
    capsys,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    out_dir = (
        public_root
        / "receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy"
    )
    rc = main(
        [
            "run-budget-bundle",
            "--input",
            str(
                public_root
                / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle"
            ),
            "--out",
            str(out_dir),
            "--card",
        ]
    )
    captured = capsys.readouterr().out
    card = json.loads(captured)
    card_keys = set(_walk_keys(card))
    full_receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))

    assert rc == 0
    assert len(captured.encode("utf-8")) < 6000
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "exported_provider_context_budget_bundle"
    assert card["bundle_id"] == "provider_context_budget_runtime_example"
    assert card["negative_case_coverage"]["expected_case_count"] == 0
    assert card["negative_case_coverage"]["observed_case_count"] == 0
    assert card["provider_context_summary"]["source_module_import_status"] == "pass"
    assert card["provider_context_summary"]["max_budget_bytes"] == 65536
    assert card["receipt_summary"]["receipt_count"] == 1
    assert card["no_export_guards"]["source_refs_exported"] is False
    assert "context_packets" not in card_keys
    assert "source_module_ids" not in card_keys
    assert "source_module_imports" not in card_keys
    assert "source_refs" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "anti_claim" not in card_keys
    assert full_receipt["status"] == "pass"
    assert full_receipt["context_packets"]


def test_provider_context_source_modules_are_exact_macro_body_imports(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    result = run_budget_bundle(
        public_root / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["source_module_import_status"] == "pass"
    assert result["source_module_ids"] == PROVIDER_CONTEXT_SOURCE_MODULE_IDS
    by_module = {
        row["module_id"]: row
        for row in result["source_module_imports"]
    }
    for module_id in PROVIDER_CONTEXT_SOURCE_MODULE_IDS:
        row = by_module[module_id]
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        target = (
            public_root
            / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle"
            / row["target_ref"]
        )
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()

        assert target.is_file()
        assert digest == source_digest
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == digest
        assert row["sha256_match"] is True
        assert row["required_anchor_count"] == row["present_anchor_count"]
        assert row["body_in_receipt"] is False


def test_provider_context_fixture_manifest_counts_source_open_body_floor() -> None:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/provider_context_recipe_budget_policy.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    body_imports = manifest["source_open_body_imports"]

    assert body_imports["status"] == "pass"
    assert body_imports["body_material_count"] == len(PROVIDER_CONTEXT_SOURCE_MODULE_IDS)
    assert body_imports["body_in_receipt"] is False
    assert set(body_imports["body_material_ids"]) == set(PROVIDER_CONTEXT_SOURCE_MODULE_IDS)
    assert "public_macro_standard_body" in body_imports["material_classes"]
    assert "public_macro_tool_body" in body_imports["material_classes"]
