from __future__ import annotations

import hashlib
import json
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

from microcosm_core.organs.provider_context_recipe_budget_policy import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    REAL_SECTION_BODY_STATUS,
    RESULT_NAME,
    SOURCE_REFS,
    _line_count,
    _byte_size,
    _sha256,
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


@lru_cache(maxsize=None)
def _real_provider_context_section_body(recipe_id: str, section_id: str) -> str:
    from tools.meta.factory import run_prover_graph_benchmark as harness

    problem_set = harness._problem_set()
    pack, *_ = harness._provider_context_pack(
        problem=problem_set[2],
        recipe_id=recipe_id,
        provider="test",
        provider_model=None,
        premise_index=harness._premise_index(),
        problem_set=problem_set,
        local_foundry_by_problem={},
        max_tokens=256,
        temperature=0.0,
    )
    for section in pack["context_sections"]:
        if section["section_id"] == section_id:
            return str(section["content"])
    raise AssertionError(f"real provider-context section {section_id!r} not emitted")


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


def test_provider_context_sha256_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    payload = b"provider context body\n" * 4096
    source.write_bytes(payload)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("sha256 should stream source-module input")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(source) == hashlib.sha256(payload).hexdigest()


def test_provider_context_byte_size_prefers_real_text() -> None:
    assert _byte_size({"declared_byte_size": 1, "text": "real text"}) == 9
    assert _byte_size({"declared_byte_size": 17}) == 17


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


def test_provider_context_section_materials_are_source_backed(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/provider_context_recipe_budget_policy",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/provider_context_recipe_budget_policy_fixture_acceptance.json",
        command="pytest",
    )
    materials = json.loads(
        (FIXTURE_INPUT / "section_materials.json").read_text(encoding="utf-8")
    )
    public_source_refs = set(SOURCE_REFS)

    assert result["status"] == "pass"
    assert result["section_material_source_status"] == "pass"
    assert result["section_material_source_ref_count"] >= 1
    assert set(result["section_material_source_refs"]) <= public_source_refs
    for section in materials["sections"]:
        assert section["source_refs"]
        assert set(section["source_refs"]) <= public_source_refs
        assert section["source_anchors"]
        assert "synthetic" not in json.dumps(section).lower()


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
    assert result["real_section_body_status"] == "pass"
    assert result["real_section_body_count"] >= 6
    assert result["context_packets"][4]["omitted_section_ids"] == []
    fewshot = next(
        section
        for section in result["context_packets"][4]["included_sections"]
        if section["section_id"] == "fewshot_examples"
    )
    assert fewshot["byte_size_source"] == REAL_SECTION_BODY_STATUS
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["truth_side_material_authorized"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle_validation_result.json"
        )
    ]


def test_provider_context_budget_moves_when_section_text_changes(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    bundle = (
        public_root
        / "examples/provider_context_recipe_budget_policy/"
        "exported_provider_context_budget_bundle"
    )

    baseline = run_budget_bundle(
        bundle,
        public_root / "receipts/baseline/provider_context_recipe_budget_policy",
        command="pytest",
    )
    section_materials_path = bundle / "section_materials.json"
    section_materials = json.loads(section_materials_path.read_text(encoding="utf-8"))
    replacement_text = _real_provider_context_section_body(
        "fewshot_64kb",
        "fewshot_examples",
    )
    oversized_text = (replacement_text + "\n") * 120
    assert len(oversized_text.encode("utf-8")) > 65536
    for section in section_materials["sections"]:
        if section["section_id"] == "fewshot_examples":
            assert section["declared_byte_size"] == 60000
            section["text"] = oversized_text
    section_materials_path.write_text(
        json.dumps(section_materials, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    changed = run_budget_bundle(
        bundle,
        public_root / "receipts/changed/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert baseline["status"] == "pass"
    assert changed["status"] == "pass"
    baseline_fewshot = next(
        packet
        for packet in baseline["context_packets"]
        if packet["recipe_id"] == "fewshot_64kb"
    )
    changed_fewshot = next(
        packet
        for packet in changed["context_packets"]
        if packet["recipe_id"] == "fewshot_64kb"
    )
    assert baseline_fewshot["omitted_section_ids"] == []
    baseline_section = next(
        section
        for section in baseline_fewshot["included_sections"]
        if section["section_id"] == "fewshot_examples"
    )
    assert baseline_section["declared_byte_size"] == 60000
    assert baseline_section["accounted_byte_size"] == len(
        replacement_text.encode("utf-8")
    )
    assert baseline_section["byte_size_source"] == REAL_SECTION_BODY_STATUS
    assert changed_fewshot["omitted_section_ids"] == ["fewshot_examples"]
    changed_section = next(
        section
        for section in changed_fewshot["omitted_sections"]
        if section["section_id"] == "fewshot_examples"
    )
    assert changed_section["declared_byte_size"] == 60000
    assert changed_section["accounted_byte_size"] == len(
        oversized_text.encode("utf-8")
    )
    assert changed_section["byte_size_source"] == "text_body"
    assert changed_fewshot["included_byte_count"] < baseline_fewshot["included_byte_count"]


def test_provider_context_budget_finding_moves_with_real_body_bytes(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    bundle = (
        public_root
        / "examples/provider_context_recipe_budget_policy/"
        "exported_provider_context_budget_bundle"
    )
    recipes_path = bundle / "provider_context_recipes.json"
    recipes = json.loads(recipes_path.read_text(encoding="utf-8"))
    for recipe in recipes["recipes"]:
        if recipe["recipe_id"] == "minimal_4kb":
            recipe["emit_omitted_sections_manifest"] = False
    recipes_path.write_text(
        json.dumps(recipes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    no_overflow = run_budget_bundle(
        bundle,
        public_root / "receipts/no_overflow/provider_context_recipe_budget_policy",
        command="pytest",
    )
    assert no_overflow["status"] == "pass"
    assert no_overflow["all_expectations_met"] is True
    assert "PROVIDER_CONTEXT_OMITTED_SECTIONS_REQUIRED" not in no_overflow["error_codes"]

    real_statement_body = _real_provider_context_section_body(
        "minimal_4kb",
        "problem_statement",
    )
    oversized_statement = (real_statement_body + "\n") * 25
    assert len(oversized_statement.encode("utf-8")) > 4096

    section_materials_path = bundle / "section_materials.json"
    section_materials = json.loads(section_materials_path.read_text(encoding="utf-8"))
    for section in section_materials["sections"]:
        if section["section_id"] == "statement":
            assert section["declared_byte_size"] == 720
            section["text"] = oversized_statement
    section_materials_path.write_text(
        json.dumps(section_materials, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    overflow = run_budget_bundle(
        bundle,
        public_root / "receipts/overflow/provider_context_recipe_budget_policy",
        command="pytest",
    )

    minimal_packet = next(
        packet
        for packet in overflow["context_packets"]
        if packet["recipe_id"] == "minimal_4kb"
    )
    omitted_statement = next(
        section
        for section in minimal_packet["omitted_sections"]
        if section["section_id"] == "statement"
    )
    finding = next(
        item
        for item in overflow["findings"]
        if item["error_code"] == "PROVIDER_CONTEXT_OMITTED_SECTIONS_REQUIRED"
    )
    assert overflow["status"] == "blocked"
    assert overflow["all_expectations_met"] is True
    assert "PROVIDER_CONTEXT_OMITTED_SECTIONS_REQUIRED" in overflow["error_codes"]
    assert "statement" in minimal_packet["omitted_section_ids"]
    assert omitted_statement["declared_byte_size"] == 720
    assert omitted_statement["accounted_byte_size"] == len(
        oversized_statement.encode("utf-8")
    )
    assert omitted_statement["byte_size_source"] == "text_body"
    assert finding["negative_case_id"] == "recipe_floor"
    assert finding["subject_id"] == "minimal_4kb"


def test_provider_context_budget_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    bundle = (
        public_root
        / "examples/provider_context_recipe_budget_policy/"
        "exported_provider_context_budget_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_id = manifest["modules"][0]["module_id"]
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_budget_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert "PROVIDER_CONTEXT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_error_codes"] == [
        "PROVIDER_CONTEXT_SOURCE_MODULE_DIGEST_MISMATCH"
    ]
    assert result["source_module_imports"][0]["module_id"] == module_id
    assert result["private_state_scan"]["blocking_hit_count"] == 0


def test_provider_context_budget_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    bundle = (
        public_root
        / "examples/provider_context_recipe_budget_policy/"
        "exported_provider_context_budget_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_id = manifest["modules"][0]["module_id"]
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_budget_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert "PROVIDER_CONTEXT_SOURCE_MODULE_SOURCE_TARGET_MISMATCH" in result[
        "error_codes"
    ]
    assert result["source_module_error_codes"] == [
        "PROVIDER_CONTEXT_SOURCE_MODULE_SOURCE_TARGET_MISMATCH"
    ]
    assert result["source_module_imports"][0]["module_id"] == module_id
    assert result["private_state_scan"]["blocking_hit_count"] == 0


def test_provider_context_budget_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    bundle = (
        public_root
        / "examples/provider_context_recipe_budget_policy/"
        "exported_provider_context_budget_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_id = manifest["modules"][0]["module_id"]
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_budget_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    assert "PROVIDER_CONTEXT_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert "PROVIDER_CONTEXT_SOURCE_MODULE_SOURCE_TARGET_MISMATCH" in result[
        "error_codes"
    ]
    assert result["source_module_error_codes"] == [
        "PROVIDER_CONTEXT_SOURCE_MODULE_DIGEST_MISMATCH",
        "PROVIDER_CONTEXT_SOURCE_MODULE_SOURCE_TARGET_MISMATCH"
    ]
    assert result["source_module_imports"][0]["module_id"] == module_id
    assert result["private_state_scan"]["blocking_hit_count"] == 0


def test_provider_context_budget_rejects_manifest_body_text_receipt_boundary(
    tmp_path: Path,
) -> None:
    cases = {
        "missing": None,
        "true": True,
    }
    for case_id, value in cases.items():
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        shutil.copytree(
            MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
            public_root / "examples/provider_context_recipe_budget_policy",
        )
        bundle = (
            public_root
            / "examples/provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle"
        )
        manifest_path = bundle / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if value is None:
            manifest.pop("body_text_in_receipt", None)
        else:
            manifest["body_text_in_receipt"] = value
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run_budget_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            "provider_context_recipe_budget_policy",
            command="pytest",
        )

        assert result["status"] == "blocked"
        assert result["source_module_import_status"] == "blocked"
        assert result["source_module_error_codes"] == [
            "PROVIDER_CONTEXT_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN"
        ]
        assert "PROVIDER_CONTEXT_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in result[
            "error_codes"
        ]
        assert result["private_state_scan"]["blocking_hit_count"] == 0
        assert "body" not in _walk_keys(result)


def test_provider_context_budget_rejects_row_body_receipt_boundary(
    tmp_path: Path,
) -> None:
    cases = {
        "missing": None,
        "true": True,
    }
    for case_id, value in cases.items():
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        shutil.copytree(
            MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
            public_root / "examples/provider_context_recipe_budget_policy",
        )
        bundle = (
            public_root
            / "examples/provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle"
        )
        manifest_path = bundle / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        module_id = manifest["modules"][0]["module_id"]
        if value is None:
            manifest["modules"][0].pop("body_text_in_receipt", None)
        else:
            manifest["modules"][0]["body_text_in_receipt"] = value
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run_budget_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            "provider_context_recipe_budget_policy",
            command="pytest",
        )

        assert result["status"] == "blocked"
        assert result["source_module_import_status"] == "blocked"
        assert result["source_module_error_codes"] == [
            "PROVIDER_CONTEXT_SOURCE_MODULE_BODY_RECEIPT_BOUNDARY_INVALID"
        ]
        assert "PROVIDER_CONTEXT_SOURCE_MODULE_BODY_RECEIPT_BOUNDARY_INVALID" in result[
            "error_codes"
        ]
        assert result["source_module_imports"][0]["module_id"] == module_id
        assert result["source_module_imports"][0]["body_text_in_receipt"] is False
        assert result["private_state_scan"]["blocking_hit_count"] == 0
        assert "body" not in _walk_keys(result)


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
    manifest = json.loads(
        (
            public_root
            / "examples/provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle/source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["body_text_in_receipt"] is False
    assert all(
        row["body_text_in_receipt"] is False for row in manifest["modules"]
    )
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
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False


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
