from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_mcp_tool_authority_trace,
)
import microcosm_core.organs.mcp_tool_authority_replay as mcp_tool_authority_replay
from microcosm_core.organs.mcp_tool_authority_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SOURCE_MODULE_IMPORT_STATUS,
    main,
    run,
    run_tool_authority_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle"
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


def test_mcp_tool_authority_replay_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/mcp_tool_authority_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "mcp_tool_authority_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["tool_count"] == 3
    assert result["tool_classes"] == [
        "readonly_lookup",
        "untrusted_result",
        "write_side_effect",
    ]
    assert result["call_count"] == 3
    assert result["write_side_effect_count"] == 1
    assert result["approved_side_effect_count"] == 1
    assert result["untrusted_result_count"] == 1
    assert result["output_instruction_ignored_count"] == 1
    assert result["rollback_receipt_count"] == 1
    assert result["cold_replay_pass_count"] == 3
    assert (
        result["authority_ceiling"]["live_mcp_account_access_authorized"] is False
    )
    assert result["authority_ceiling"]["credential_export_authorized"] is False
    assert (
        result["authority_ceiling"][
            "untrusted_tool_output_instruction_authorized"
        ]
        is False
    )
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_mcp_tool_authority_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mcp_tool_authority_replay",
        public_root / "fixtures/first_wave/mcp_tool_authority_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/mcp_tool_authority_replay/input",
        public_root / "receipts/first_wave/mcp_tool_authority_replay",
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
        keys = _walk_keys(json.loads(text))
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "token_value" not in keys
        assert "provider_payload" not in keys
        assert "raw_tool_payload" not in keys
        assert "raw_tool_result" not in keys
        assert "private_account_id" not in keys
        assert "private_state_scan" not in keys
        assert "body_redacted" not in keys


def test_mcp_tool_authority_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_tool_authority_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_mcp_tool_authority_bundle"
    assert result["bundle_id"] == "mcp_tool_authority_public_trace_refactor"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["tool_count"] == 3
    assert result["call_count"] == 3
    assert result["approved_side_effect_count"] == 1
    assert result["output_instruction_ignored_count"] == 1
    assert result["cold_replay_pass_count"] == 3
    assert result["body_import_status"] == SOURCE_MODULE_IMPORT_STATUS
    assert result["body_import_classification"] == (
        "copied_non_secret_public_mcp_tool_authority_macro_body_import"
    )
    assert result["product_path_role"] == (
        "copied_non_secret_macro_body_plus_public_agent_execution_trace_refactor"
    )
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] >= 6
    assert result["body_material_status"] == SOURCE_MODULE_IMPORT_STATUS
    assert result["body_copied_material_count"] >= 6
    assert result["body_import_verification"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 3
    assert (
        result["public_agent_execution_trace"]["audit"]["coverage"][
            "untrusted_output_data_boundary_coverage"
        ]
        is True
    )
    assert "public_replacement_refs" not in result
    assert "private_state_scan" not in result
    assert (
        result["authority_ceiling"]["live_mcp_account_access_authorized"] is False
    )


def test_mcp_tool_authority_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay"
    )
    args = [
        "run-tool-authority-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["tool_authority"]["tool_count"] == 3
    assert first_card["tool_authority"]["call_count"] == 3
    assert first_card["source_body_floor"]["body_material_count"] >= 6
    assert first_card["source_body_floor"]["body_material_status"] == (
        SOURCE_MODULE_IMPORT_STATUS
    )
    assert "call_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "public_agent_execution_trace" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(mcp_tool_authority_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_mcp_tool_authority_source_modules_are_exact_macro_body_imports() -> None:
    manifest_path = BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] >= 6
    assert manifest["body_in_receipt"] is False

    repo_root = MICROCOSM_ROOT.parent
    for row in manifest["modules"]:
        source = repo_root / row["source_ref"]
        target_ref = row["target_ref"].removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref

        assert source.is_file(), row["module_id"]
        assert target.is_file(), row["module_id"]
        source_digest = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
        assert source_digest == target_digest == row["sha256"]
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        body = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in body


def test_public_agent_execution_trace_refactor_builds_mcp_tool_authority_spans() -> None:
    trace = build_public_mcp_tool_authority_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["span_count"] == 3
    assert trace["source_faithful_refactor"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert trace["audit"]["coverage"]["capability_scope_coverage"] is True
    assert trace["audit"]["coverage"]["write_side_effect_approval_coverage"] is True
    assert trace["audit"]["coverage"]["rollback_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["cold_replay_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["body_in_receipt"] is False
