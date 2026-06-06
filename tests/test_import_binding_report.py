from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core.import_binding_report import build_partial_import_binding_report
from microcosm_core.schemas import DuplicateJsonKeyError


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_import_binding_report_detects_examples_body_acceptance_zero(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "examples/demo/exported_demo_bundle/source_module_manifest.json",
        {
            "modules": [
                {
                    "body_copied": True,
                    "sha256_match": True,
                    "source_sha256": "abc",
                    "target_sha256": "abc"
                }
            ]
        },
    )
    _write_json(
        root / "core/fixture_manifests/demo.fixture_manifest.json",
        {"source_open_body_imports": {"status": "pass", "body_material_count": 1}},
    )
    _write_json(
        root / "core/acceptance/first_wave_acceptance.json",
        {
            "accepted_current_authority_organs": [
                {
                    "organ_id": "demo",
                    "status": "accepted_current_authority",
                    "copied_body_count": 0,
                    "source_module_manifest_status": "not_present"
                }
            ]
        },
    )

    report = build_partial_import_binding_report(root)

    row = report["rows"][0]
    assert row["organ_id"] == "demo"
    assert row["examples_body_present"] is True
    assert row["fixture_manifest_present"] is True
    assert "examples_body_present_acceptance_zero" in row["gap_codes"]
    assert "examples_body_present_acceptance_manifest_not_present" in row["gap_codes"]
    assert row["recommended_action"] == "bind_acceptance_to_verified_example_substrate"


def test_import_binding_report_detects_missing_fixture_manifest(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "examples/demo/exported_demo_bundle/source_module_manifest.json",
        {
            "modules": [
                {
                    "body_copied": True,
                    "sha256_match": True,
                    "source_sha256": "abc",
                    "target_sha256": "abc"
                }
            ]
        },
    )
    _write_json(
        root / "core/acceptance/first_wave_acceptance.json",
        {
            "accepted_current_authority_organs": [
                {"organ_id": "demo", "status": "accepted_current_authority"}
            ]
        },
    )

    report = build_partial_import_binding_report(root)

    row = report["rows"][0]
    assert "examples_body_present_fixture_manifest_missing" in row["gap_codes"]
    assert row["recommended_action"] == "add_or_migrate_fixture_manifest_for_existing_body_import"


def test_import_binding_report_ignores_unaccepted_draft_manifest(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "examples/demo/exported_demo_bundle/source_module_manifest.json",
        {
            "modules": [
                {
                    "body_copied": True,
                    "sha256_match": True,
                    "source_sha256": "abc",
                    "target_sha256": "abc",
                }
            ]
        },
    )
    _write_json(
        root / "examples/draft/exported_draft_bundle/source_module_manifest.json",
        {
            "modules": [
                {
                    "body_copied": True,
                    "sha256_match": True,
                    "source_sha256": "def",
                    "target_sha256": "def",
                }
            ]
        },
    )
    _write_json(
        root / "core/acceptance/first_wave_acceptance.json",
        {
            "accepted_current_authority_organs": [
                {"organ_id": "demo", "status": "accepted_current_authority"}
            ]
        },
    )

    report = build_partial_import_binding_report(root)

    assert [row["organ_id"] for row in report["rows"]] == ["demo"]


def test_import_binding_report_rejects_duplicate_manifest_keys(tmp_path: Path) -> None:
    root = tmp_path
    manifest_path = root / "examples/demo/exported_demo_bundle/source_module_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        (
            '{"modules": [], '
            '"modules": [{"body_copied": true, "sha256_match": true}]}\n'
        ),
        encoding="utf-8",
    )
    _write_json(
        root / "core/acceptance/first_wave_acceptance.json",
        {
            "accepted_current_authority_organs": [
                {"organ_id": "demo", "status": "accepted_current_authority"}
            ]
        },
    )

    with pytest.raises(DuplicateJsonKeyError, match="duplicate JSON key 'modules'"):
        build_partial_import_binding_report(root)
