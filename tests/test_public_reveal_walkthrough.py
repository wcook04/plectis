from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs.public_reveal_walkthrough import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_reveal_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/public_reveal_walkthrough/input"
BUNDLE_INPUT = MICROCOSM_ROOT / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
PUBLIC_REVEAL_SOURCE_MODULE_IDS = {
    "public_reveal_first_slice_execution_receipt_body_import",
    "public_reveal_runtime_shell_reorientation_receipt_body_import",
    "public_reveal_clean_clone_state_fixture_receipt_body_import",
    "public_reveal_public_substrate_boundary_policy_body_import",
}


def _macro_source_path(ref: str) -> Path:
    path = MICROCOSM_ROOT.parent / ref
    if not path.is_file():
        pytest.skip("macro source-module parity check requires ai_workflow parent root")
    return path


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


def test_public_reveal_walkthrough_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/public_reveal_walkthrough",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/public_reveal_walkthrough_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["step_count"] == 5
    assert result["command_count"] >= 4
    assert "microcosm run --card examples/runtime_shell/demo_project" in result["commands"]
    assert "microcosm intake --card" in result["commands"]
    assert "microcosm authority --card" in result["commands"]
    assert "microcosm intake" not in result["commands"]
    assert "microcosm status" not in result["commands"]
    assert result["evidence_ref_count"] >= 4
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["reveal_board"]["primary_loop"].startswith("repo -> .microcosm")
    assert result["reveal_board"]["first_command"] == "python -m pip install -e '.[test]'"
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["public_runtime_refs"]
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_public_reveal_walkthrough_receipts_are_public_relative_and_secret_excluded(tmp_path: Path) -> None:
    public_root = tmp_path / "standalone-public-root"
    public_root.mkdir()
    shutil.copy2(MICROCOSM_ROOT / "pyproject.toml", public_root / "pyproject.toml")
    (public_root / "src/microcosm_core").mkdir(parents=True)
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/public_reveal_walkthrough",
        public_root / "fixtures/first_wave/public_reveal_walkthrough",
    )

    result = run(
        public_root / "fixtures/first_wave/public_reveal_walkthrough/input",
        public_root / "receipts/first_wave/public_reveal_walkthrough",
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
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert payload["public_runtime_refs"]
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_public_reveal_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_reveal_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_public_reveal_bundle"
    assert result["bundle_id"] == "public_reveal_walkthrough_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert "microcosm intake --card" in result["commands"]
    assert "microcosm authority --card" in result["commands"]
    assert "microcosm intake" not in result["commands"]
    assert "microcosm status" not in result["commands"]
    assert result["reveal_board"]["release_authorized"] is False
    assert result["reveal_board"]["first_command"] == "python -m pip install -e '.[test]'"
    assert result["public_claim"].startswith("Microcosm turns a repo")
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_copied_material_count"] == 4
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 4
    assert set(source_imports["body_material_ids"]) == PUBLIC_REVEAL_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {
        "public_macro_receipt_body": 3,
        "public_macro_tool_body": 1,
    }
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["public_runtime_refs"]
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_public_reveal_exported_bundle_card_is_compact(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "bundle-card"

    rc = main(
        [
            "run-reveal-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = out_dir / "exported_public_reveal_bundle_validation_result.json"

    assert rc == 0
    assert len(captured.encode("utf-8")) < 4000
    assert full_receipt.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "public_reveal_walkthrough"
    assert card["input_mode"] == "exported_public_reveal_bundle"
    assert card["bundle_id"] == "public_reveal_walkthrough_runtime_example"
    assert card["reveal_summary"]["step_count"] == 5
    assert card["reveal_summary"]["command_count"] == 8
    assert card["reveal_summary"]["evidence_ref_count"] == 11
    assert card["negative_case_coverage"]["expected_case_count"] == 0
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["hits_exported"] is False
    assert card["source_open_body_imports"]["status"] == "pass"
    assert card["source_open_body_imports"]["body_material_count"] == 4
    assert card["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert card["authority_ceiling"]["release_authorized"] is False
    assert card["no_export_guards"]["step_rows_exported"] is False
    assert card["no_export_guards"]["commands_exported"] is False
    assert card["no_export_guards"]["public_runtime_refs_exported"] is False
    assert card["output_economy"]["full_payload_drilldown"] == "rerun without --card"
    assert "steps" not in card
    assert "commands" not in card
    assert "evidence_refs" not in card
    assert "public_runtime_refs" not in card


def test_public_reveal_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4
    assert {row["module_id"] for row in modules} == PUBLIC_REVEAL_SOURCE_MODULE_IDS

    for row in modules:
        source_path = _macro_source_path(row["source_ref"])
        target_path = MICROCOSM_ROOT.parent / row["target_ref"]
        source_bytes = source_path.read_bytes()
        target_bytes = target_path.read_bytes()
        digest = hashlib.sha256(source_bytes).hexdigest()

        assert source_bytes == target_bytes
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        text = target_bytes.decode("utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_public_reveal_fixture_card_honors_acceptance_out(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "fixture-card"
    acceptance_out = tmp_path / "acceptance.json"

    rc = main(
        [
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(out_dir),
            "--acceptance-out",
            str(acceptance_out),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)

    assert rc == 0
    assert len(captured.encode("utf-8")) < 4000
    assert acceptance_out.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["input_mode"] == "first_wave_fixture"
    assert card["negative_case_coverage"]["expected_case_count"] == 4
    assert card["negative_case_coverage"]["observed_case_count"] == 4
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["no_export_guards"]["step_rows_exported"] is False
