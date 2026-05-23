from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_sandbox_policy_trace,
)
from microcosm_core.organs.agent_sandbox_policy_escape_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_sandbox_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/agent_sandbox_policy_escape_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_sandbox_policy_escape_replay/"
    "exported_sandbox_policy_escape_bundle"
)
FIXTURE_MANIFESTS = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_sandbox_policy_escape_replay/fixture_manifest.json",
    MICROCOSM_ROOT
    / "core/fixture_manifests/agent_sandbox_policy_escape_replay.fixture_manifest.json",
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


def test_agent_sandbox_policy_escape_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_sandbox_policy_escape_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_sandbox_policy_escape_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["action_request_count"] == 6
    assert result["policy_verdict_count"] == 6
    assert result["block_count"] == 4
    assert result["allow_count"] == 1
    assert result["review_count"] == 1
    assert result["side_effect_receipt_count"] == 6
    assert result["blocked_without_execution_count"] == 4
    assert result["rollback_verified_count"] == 2
    assert result["cold_replay_pass_count"] == 6
    assert result["authority_ceiling"]["live_sandbox_escape_authorized"] is False
    assert result["authority_ceiling"]["live_network_access_authorized"] is False
    assert result["authority_ceiling"]["host_filesystem_mutation_authorized"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 6
    assert result["public_agent_execution_trace"]["summary"]["outcome_counts"] == {
        "blocked": 4,
        "executed": 2,
    }
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_agent_sandbox_policy_escape_receipts_are_public_relative_and_secret_excluded(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sandbox_policy_escape_replay",
        public_root / "fixtures/first_wave/agent_sandbox_policy_escape_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_sandbox_policy_escape_replay/input",
        public_root / "receipts/first_wave/agent_sandbox_policy_escape_replay",
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
        assert "raw_environment" not in keys
        assert "raw_tool_output_body" not in keys
        assert "executable_payload" not in keys
        assert "provider_payload" not in keys
        assert "host_absolute_path" not in keys
        assert "private_state_scan" not in keys


def test_agent_sandbox_policy_escape_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_sandbox_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sandbox_policy_escape_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_sandbox_policy_escape_bundle"
    assert result["bundle_id"] == "agent_sandbox_policy_escape_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["action_request_count"] == 6
    assert result["policy_verdict_count"] == 6
    assert result["blocked_without_execution_count"] == 4
    assert result["cold_replay_pass_count"] == 6
    assert result["authority_ceiling"]["live_sandbox_escape_authorized"] is False
    assert "public_replacement_refs" not in result
    assert "omitted_private_material" not in result
    assert result["body_import_verification"]["verification_mode"] == (
        "extension_of_existing_public_refactor"
    )
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
    } == {"sandbox_policy_action"}


def test_public_agent_execution_trace_refactor_builds_sandbox_policy_spans() -> None:
    trace = build_public_sandbox_policy_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["bundle_id"] == "agent_sandbox_policy_escape_replay_runtime_example"
    assert trace["span_count"] == 6
    assert trace["summary"]["action_kind_counts"] == {
        "environment_secret_read": 1,
        "filesystem_delete": 1,
        "filesystem_write": 1,
        "mock_database_update": 1,
        "network_request": 1,
        "shell_command": 1,
    }
    assert trace["audit"]["coverage"]["policy_verdict_coverage"] is True
    assert trace["audit"]["coverage"]["side_effect_receipt_coverage"] is True
    assert trace["audit"]["coverage"]["cold_replay_coverage"] is True
    assert "system/lib/agent_execution_trace.py" in trace["source_refs"]


def test_agent_sandbox_policy_fixture_manifests_bind_public_trace_refactor() -> None:
    for manifest_path in FIXTURE_MANIFESTS:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert "body_redacted" not in manifest
        assert "public_replacement_refs" not in manifest
        assert "private_state_scan" not in manifest
        assert not manifest["authority_ceiling"].startswith(
            "synthetic_agent_sandbox_policy_escape_replay_receipts_only"
        )
        assert (
            manifest["body_import_status"]
            == "extension_of_existing_public_refactor_landed"
        )
        assert manifest["body_in_receipt"] is False
        assert manifest["body_import_verification"] == {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": (
                "microcosm-substrate/src/microcosm_core/macro_tools/"
                "agent_execution_trace.py"
            ),
            "validation_refs": [
                "microcosm-substrate/tests/test_agent_sandbox_policy_escape_replay.py"
            ],
            "verification_mode": "extension_of_existing_public_refactor",
            "verification_status": "verified",
        }
        assert (
            "microcosm_core.macro_tools.agent_execution_trace::"
            "build_public_sandbox_policy_trace"
            in manifest["fixture_runtime_refs"]
        )
        assert (
            "microcosm-substrate/src/microcosm_core/macro_tools/"
            "agent_execution_trace.py"
            in manifest["target_refs"]
        )
        assert set(manifest["negative_case_ids"]) == set(EXPECTED_NEGATIVE_CASES)
