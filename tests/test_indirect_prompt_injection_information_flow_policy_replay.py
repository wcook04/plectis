from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_prompt_injection_trace,
)
from microcosm_core.organs import (
    indirect_prompt_injection_information_flow_policy_replay,
)
from microcosm_core.organs.indirect_prompt_injection_information_flow_policy_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_prompt_injection_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/"
    "indirect_prompt_injection_information_flow_policy_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/indirect_prompt_injection_information_flow_policy_replay/"
    "exported_prompt_injection_flow_bundle"
)
FIXTURE_MANIFESTS = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/"
    "indirect_prompt_injection_information_flow_policy_replay/fixture_manifest.json",
    MICROCOSM_ROOT
    / "core/fixture_manifests/"
    "indirect_prompt_injection_information_flow_policy_replay.fixture_manifest.json",
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


def test_indirect_prompt_injection_flow_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_document_count"] == 5
    assert result["untrusted_source_count"] == 3
    assert result["trusted_source_count"] == 2
    assert result["information_flow_count"] == 5
    assert result["policy_verdict_count"] == 5
    assert result["allow_count"] == 1
    assert result["warn_count"] == 1
    assert result["block_count"] == 2
    assert result["review_count"] == 1
    assert result["blocked_without_external_action_count"] == 2
    assert result["trusted_context_disclosure_count"] == 0
    assert result["untrusted_instruction_obeyed_count"] == 0
    assert result["cold_replay_pass_count"] == 5
    assert result["authority_ceiling"]["tool_output_instruction_authority_authorized"] is False
    assert result["authority_ceiling"]["raw_prompt_body_export_authorized"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert (
        result["body_import_classification"]
        == "extension_of_existing_public_refactor"
    )
    assert result["product_path_role"] == (
        "source_faithful_public_agent_execution_trace_refactor"
    )
    assert result["body_in_receipt"] is False
    assert result["body_import_verification"]["classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 5
    assert result["public_agent_execution_trace"]["summary"]["outcome_counts"] == {
        "allowed_sanitized": 1,
        "blocked": 2,
        "review_required": 1,
        "sanitized_warning": 1,
    }
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_indirect_prompt_injection_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
        public_root
        / "fixtures/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay/input",
        public_root
        / "receipts/first_wave/"
        "indirect_prompt_injection_information_flow_policy_replay",
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
        assert "raw_email_body" not in keys
        assert "raw_document_body" not in keys
        assert "raw_prompt_body" not in keys
        assert "raw_system_prompt" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "provider_payload" not in keys
        assert "hidden_system_message_body" not in keys
        assert "private_state_scan" not in keys


def test_indirect_prompt_injection_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_prompt_injection_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_prompt_injection_flow_bundle"
    assert (
        result["bundle_id"]
        == "indirect_prompt_injection_information_flow_policy_replay_public_trace_refactor_bundle"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["source_document_count"] == 5
    assert result["information_flow_count"] == 5
    assert result["block_count"] == 2
    assert result["review_count"] == 1
    assert result["cold_replay_pass_count"] == 5
    assert result["authority_ceiling"]["live_tool_call_authorized"] is False
    assert "public_replacement_refs" not in result
    assert "omitted_private_material" not in result
    assert result["body_import_verification"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["body_import_verification"]["classification"] == (
        "extension_of_existing_public_refactor"
    )
    assert result["body_import_verification"]["status"] == "pass"
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert (
        result["body_import_classification"]
        == "extension_of_existing_public_refactor"
    )
    assert result["body_in_receipt"] is False
    assert (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        in result["target_refs"]
    )
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["source_faithful_refactor"][
        "verification_mode"
    ] == "extension_of_existing_public_refactor"
    assert {
        span["tool_name"] for span in result["public_agent_execution_trace"]["spans"]
    } == {"prompt_injection_information_flow_policy"}


def test_indirect_prompt_injection_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "indirect_prompt_injection_information_flow_policy_replay"
    )
    args = [
        "run-prompt-injection-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 9
    assert first_card["prompt_injection_flow"]["source_document_count"] == 5
    assert first_card["prompt_injection_flow"]["information_flow_count"] == 5
    assert first_card["prompt_injection_flow"]["block_count"] == 2
    assert first_card["prompt_injection_flow"]["review_count"] == 1
    assert first_card["prompt_injection_flow"]["cold_replay_pass_count"] == 5
    assert first_card["public_trace"]["span_count"] == 5
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "source_rows" not in _walk_keys(first_card)
    assert "flow_rows" not in _walk_keys(first_card)
    assert "policy_verdict_rows" not in _walk_keys(first_card)
    assert "sanitized_output_rows" not in _walk_keys(first_card)
    assert "cold_replay_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "spans" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        indirect_prompt_injection_information_flow_policy_replay,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_public_agent_execution_trace_refactor_builds_prompt_injection_spans() -> None:
    trace = build_public_prompt_injection_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert (
        trace["bundle_id"]
        == "indirect_prompt_injection_information_flow_policy_replay_public_trace_refactor_bundle"
    )
    assert trace["span_count"] == 5
    assert trace["summary"]["action_kind_counts"] == {
        "answer": 2,
        "external_action": 1,
        "instruction_channel": 1,
        "state_mutation": 1,
    }
    assert trace["audit"]["coverage"]["source_document_coverage"] is True
    assert trace["audit"]["coverage"]["policy_verdict_coverage"] is True
    assert trace["audit"]["coverage"]["sanitized_output_coverage"] is True
    assert trace["audit"]["coverage"]["cold_replay_coverage"] is True
    assert trace["audit"]["coverage"]["trusted_context_non_disclosure"] is True
    assert trace["audit"]["coverage"]["untrusted_instruction_non_adoption"] is True
    assert "system/lib/agent_execution_trace.py" in trace["source_refs"]


def test_indirect_prompt_injection_fixture_manifests_bind_public_trace_refactor() -> None:
    for manifest_path in FIXTURE_MANIFESTS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert "body_redacted" not in manifest
        assert "public_replacement_refs" not in manifest
        assert "private_state_scan" not in manifest
        assert not manifest["authority_ceiling"].startswith(
            "synthetic_indirect_prompt_injection_information_flow_replay_receipts_only"
        )
        assert (
            manifest["body_import_status"]
            == "extension_of_existing_public_refactor_landed"
        )
        assert (
            manifest["product_path_role"]
            == "source_faithful_public_agent_execution_trace_refactor"
        )
        assert manifest["body_in_receipt"] is False
        assert manifest["body_import_verification"] == {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": (
                "microcosm-substrate/src/microcosm_core/macro_tools/"
                "agent_execution_trace.py"
            ),
            "validation_refs": [
                (
                    "microcosm-substrate/tests/"
                    "test_indirect_prompt_injection_information_flow_policy_replay.py"
                )
            ],
            "verification_mode": "extension_of_existing_public_refactor",
            "verification_status": "verified",
        }
        assert (
            "microcosm_core.macro_tools.agent_execution_trace::"
            "build_public_prompt_injection_trace"
            in manifest["fixture_runtime_refs"]
        )
        assert (
            "microcosm-substrate/src/microcosm_core/macro_tools/"
            "agent_execution_trace.py"
            in manifest["target_refs"]
        )
        assert set(manifest["negative_case_ids"]) == set(EXPECTED_NEGATIVE_CASES)
