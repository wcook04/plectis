from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from microcosm_core.organs._crown_jewel_common import (
    SOURCE_IMPORT_CLASS,
    CrownJewelSpec,
    file_line_count,
    validate_negative_cases,
    validate_source_manifest,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _spec() -> CrownJewelSpec:
    return CrownJewelSpec(
        organ_id="test_crown_jewel_common",
        title="Test Crown Jewel Common",
        fixture_id="test.fixture",
        validator_id="validator.test",
        result_name="result.json",
        board_name="board.json",
        validation_receipt_name="validation.json",
        bundle_result_name="bundle_result.json",
        card_schema_version="test_card_v1",
        required_inputs=(),
        expected_negative_cases={},
        anti_claim="test only",
        authority_ceiling={},
        source_manifest_ref="microcosm-substrate/examples/test/source_module_manifest.json",
        source_required_anchors={},
        bundle_input_mode="test_bundle",
    )


def test_file_line_count_reports_zero_for_empty_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty.py"
    empty.write_text("", encoding="utf-8")

    assert file_line_count(empty) == 0


def test_validate_source_manifest_rejects_empty_file_reported_as_one_line(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = public_root / "examples/test"
    target = bundle / "empty.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")
    digest = _sha256(target)
    _write_json(
        bundle / "source_module_manifest.json",
        {
            "source_import_class": SOURCE_IMPORT_CLASS,
            "modules": [
                {
                    "source_ref": "macro/empty.py",
                    "path": "empty.py",
                    "target_ref": "microcosm-substrate/examples/test/empty.py",
                    "source_to_target_relation": "copied_non_secret_macro_body",
                    "body_copied": True,
                    "sha256": digest,
                    "source_sha256": digest,
                    "target_sha256": digest,
                    "line_count": 1,
                }
            ],
        },
    )

    result = validate_source_manifest(bundle, _spec(), public_root=public_root)

    assert result["status"] == "blocked"
    assert result["all_expected_digests_matched"] is True
    assert result["all_expected_line_counts_matched"] is False
    assert result["modules"][0]["line_count"] == 0
    assert result["modules"][0]["line_count_status"] == "mismatch"
    assert any(
        row["error_code"] == "CROWN_JEWEL_SOURCE_LINE_COUNT_MISMATCH"
        for row in result["findings"]
    )


def test_validate_negative_cases_semantic_evaluator_does_not_trust_declared_codes(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "declared_only.json",
        {
            "schema_version": "test_negative_case_v1",
            "status": "blocked",
            "error_codes": ["DECLARED_ONLY_ERROR"],
        },
    )

    result = validate_negative_cases(
        tmp_path,
        {"declared_only": ("DECLARED_ONLY_ERROR",)},
        negative_case_evaluator=lambda _case_id, _input_dir, _expected: {
            "status": "pass",
            "error_codes": [],
            "body_in_receipt": False,
        },
    )

    assert result["status"] == "blocked"
    assert result["observed_negative_cases"] == []
    assert result["missing_negative_cases"] == ["declared_only"]
    assert result["semantic_evaluator_used"] is True
    assert result["negative_case_semantics"] == [
        {
            "case_id": "declared_only",
            "status": "pass",
            "error_codes": [],
            "semantic_evaluator_used": True,
            "body_in_receipt": False,
        }
    ]
    assert {
        "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED",
        "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING",
    }.issubset({row["error_code"] for row in result["findings"]})


def test_validate_negative_cases_without_semantic_evaluator_rejects_label_only_fixture(
    tmp_path: Path,
) -> None:
    _write_json(
        tmp_path / "declared_only.json",
        {
            "schema_version": "test_negative_case_v1",
            "status": "blocked",
            "error_codes": ["DECLARED_ONLY_ERROR"],
        },
    )

    result = validate_negative_cases(
        tmp_path,
        {"declared_only": ("DECLARED_ONLY_ERROR",)},
    )

    assert result["status"] == "blocked"
    assert result["observed_negative_cases"] == []
    assert result["missing_negative_cases"] == ["declared_only"]
    assert result["error_codes"] == []
    assert result["semantic_evaluator_used"] is False
    assert result["negative_case_semantics"] == [
        {
            "case_id": "declared_only",
            "status": "missing_semantic_evaluator",
            "error_codes": [],
            "semantic_evaluator_used": False,
            "body_in_receipt": False,
        }
    ]
    assert {
        "CROWN_JEWEL_NEGATIVE_CASE_SEMANTIC_EVALUATOR_MISSING",
        "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING",
    }.issubset({row["error_code"] for row in result["findings"]})
