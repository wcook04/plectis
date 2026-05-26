from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.organs.executable_doctrine_grammar import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    validate,
    validate_executable_grammar_metabolism_bundle,
    validate_standards_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/executable_doctrine_grammar/input"
GRAMMAR_EXPORTED_BUNDLE_INPUT = MICROCOSM_ROOT / "examples/executable_doctrine_grammar/exported_standards_bundle"
METABOLISM_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/executable_doctrine_grammar/exported_executable_grammar_metabolism_bundle"
)


def test_executable_doctrine_grammar_observes_required_negative_cases(tmp_path: Path) -> None:
    result = validate(
        GRAMMAR_FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["accepted_standard_ids"] == ["std_toy_navigation_route_plane"]
    assert result["valid_module_slugs"] == ["toy_navigation_route_plane"]
    assert result["invalid_module_slugs"] == ["broken_module"]
    assert "MISSING_TELEOLOGY" in result["error_codes"]
    assert "MISSING_RECEIPT_EXPECTATIONS" in result["error_codes"]
    assert "MISSING_GOVERNING_STANDARD" in result["error_codes"]
    assert "MISSING_ANTI_CLAIM" in result["error_codes"]
    assert "PROSE_STANDARD_NOT_EXECUTABLE_AUTHORITY" in result["error_codes"]
    assert "MACRO_DOCTRINE_BODY_IN_PUBLIC_FIXTURE" in result["error_codes"]
    assert "DUPLICATE_STANDARD_SLUG_CONFLICT" in result["error_codes"]
    assert "GRAMMAR_PASS_OVERCLAIMS_DOCTRINE_COMPLETE" in result["error_codes"]


def test_executable_doctrine_grammar_accepts_exported_standards_bundle(tmp_path: Path) -> None:
    result = validate_standards_bundle(
        GRAMMAR_EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_standards_bundle"
    assert result["bundle_id"] == "public_executable_doctrine_grammar_runtime_example"
    assert result["accepted_standard_ids"] == [
        "std_public_runtime_doctrine_grammar",
        "std_public_runtime_paper_module",
    ]
    assert result["valid_module_slugs"] == ["public_runtime_doctrine_grammar"]
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["private_state_scan"]["body_redacted"] is True
    assert result["receipt_paths"] == [
        "receipts/exported_standards_bundle_validation_result.json"
    ]

    receipt = json.loads((tmp_path / "receipts/exported_standards_bundle_validation_result.json").read_text(encoding="utf-8"))
    assert receipt["input_mode"] == "exported_standards_bundle"
    assert all(path.startswith("receipts/") for path in receipt["receipt_paths"])
    text = json.dumps(receipt, sort_keys=True)
    assert "matched_excerpt" not in text
    assert '"body"' not in text


def test_executable_doctrine_grammar_accepts_imported_executable_grammar_metabolism_bundle(
    tmp_path: Path,
) -> None:
    result = validate_executable_grammar_metabolism_bundle(
        METABOLISM_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_executable_grammar_metabolism_bundle"
    assert result["bundle_id"] == "public_executable_grammar_metabolism_macro_specimen"
    assert result["grammar_rule_count"] == 5
    assert result["grammar_case_count"] == 6
    assert result["source_capsule_count"] == 10
    assert result["provider_replay_bridge_case_count"] == 4
    assert result["body_copied_material_count"] == 3
    assert result["private_state_scan"]["status"] == "pass"
    assert result["private_state_scan"]["body_redacted"] is True
    assert result["receipt_paths"] == [
        "receipts/exported_executable_grammar_metabolism_bundle_validation_result.json"
    ]
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 3
    assert source_imports["body_in_receipt"] is False
    assert set(source_imports["body_material_ids"]) == {
        "executable_grammar_metabolism_readme_body_import",
        "executable_grammar_metabolism_board_body_import",
        "executable_grammar_metabolism_receipt_body_import",
    }
    source_modules = result["source_module_imports"]
    assert source_modules["status"] == "pass"
    assert source_modules["module_count"] == 3
    assert all(module["body_in_receipt"] is False for module in source_modules["modules"])
    assert all(module["sha256"] == module["actual_sha256"] for module in source_modules["modules"])

    receipt = json.loads(
        (
            tmp_path
            / "receipts/exported_executable_grammar_metabolism_bundle_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["body_text_in_receipt"] is False
    assert receipt["source_open_body_imports"]["body_material_count"] == 3
    assert receipt["body_copied_material_count"] == 3
    assert receipt["source_module_imports"]["source_module_manifest_ref"].endswith(
        "source_module_manifest.json"
    )
    assert receipt["source_root"] == (
        "self-indexing-cognitive-substrate/microcosms/executable_grammar_metabolism"
    )
    assert sorted(receipt["artifact_refs"]) == [
        "examples/executable_doctrine_grammar/exported_executable_grammar_metabolism_bundle/README.md",
        "examples/executable_doctrine_grammar/exported_executable_grammar_metabolism_bundle/grammar_board.json",
        "examples/executable_doctrine_grammar/exported_executable_grammar_metabolism_bundle/receipt.json",
    ]
    text = json.dumps(receipt, sort_keys=True)
    assert "matched_excerpt" not in text
    assert "private standards engine" in text
    assert "/Users/" not in text


def test_executable_doctrine_grammar_source_module_digest_tamper_blocks_bundle(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle_dir = (
        public_root
        / "examples/executable_doctrine_grammar/exported_executable_grammar_metabolism_bundle"
    )
    shutil.copytree(METABOLISM_BUNDLE_INPUT, bundle_dir)
    source_body = bundle_dir / "grammar_board.json"
    source_body.write_text(source_body.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = validate_executable_grammar_metabolism_bundle(
        bundle_dir,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["body_copied_material_count"] == 3
    assert "EXECUTABLE_GRAMMAR_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["body_text_in_receipt"] is False


def test_executable_doctrine_grammar_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/executable_doctrine_grammar",
        public_root / "fixtures/first_wave/executable_doctrine_grammar",
    )

    result = validate(
        public_root / "fixtures/first_wave/executable_doctrine_grammar/input",
        public_root / "receipts/first_wave/executable_doctrine_grammar",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        "receipts/first_wave/executable_doctrine_grammar/paper_module_validation_report.json",
        "receipts/first_wave/executable_doctrine_grammar/standards_group_index.json",
        "receipts/first_wave/executable_doctrine_grammar/standards_validation_report.json",
        "receipts/acceptance/first_wave/executable_doctrine_grammar_fixture_acceptance.json",
    ]
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS

    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/Users/willcook" not in text
        assert "src/ai_workflow" not in text
        payload = json.loads(text)
        for key in (
            "status",
            "organ_id",
            "fixture_id",
            "expected_negative_cases",
            "observed_negative_cases",
            "missing_negative_cases",
            "error_codes",
            "findings",
            "private_state_scan",
            "authority_ceiling",
            "anti_claim",
            "receipt_paths",
        ):
            assert key in payload
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)

    standards = json.loads(
        (
            public_root
            / "receipts/first_wave/executable_doctrine_grammar/standards_validation_report.json"
        ).read_text(encoding="utf-8")
    )
    assert standards["private_state_scan"]["status"] == "pass"
    assert standards["private_state_scan"]["body_redacted"] is True
    for hit in standards["private_state_scan"]["hits"]:
        assert "matched_excerpt" not in hit
        assert "body" not in hit
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_executable_doctrine_grammar_reports_duplicate_slug_and_overclaim(
    tmp_path: Path,
) -> None:
    result = validate(
        GRAMMAR_FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["duplicate_standard_slugs"] == ["duplicate_toy_standard"]
    assert "std_duplicate_a" in result["rejected_standard_ids"]
    assert "std_duplicate_b" in result["rejected_standard_ids"]
    assert "std_grammar_overclaim" in result["rejected_standard_ids"]
    assert result["authority_ceiling"]["doctrine_completeness_overclaim_rejected"] is True
