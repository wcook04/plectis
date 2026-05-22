from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.agent_sabotage_scheming_monitor_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_sabotage_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_sabotage_scheming_monitor_replay/"
    "exported_sabotage_monitor_bundle"
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


def test_agent_sabotage_scheming_monitor_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_sabotage_scheming_monitor_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "agent_sabotage_scheming_monitor_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["episode_count"] == 3
    assert result["action_trace_count"] == 6
    assert result["monitor_score_count"] == 6
    assert result["attack_opportunity_count"] == 4
    assert result["counterfactual_replay_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["live_sabotage_authorized"] is False
    assert result["authority_ceiling"]["private_chain_of_thought_export_authorized"] is False
    assert result["authority_ceiling"]["deployment_risk_claim_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_agent_sabotage_scheming_monitor_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay",
        public_root / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input",
        public_root / "receipts/first_wave/agent_sabotage_scheming_monitor_replay",
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
        assert "private_chain_of_thought" not in keys
        assert "raw_harmful_payload" not in keys
        assert "exploit_instructions" not in keys
        assert "credential_value" not in keys
        assert "provider_payload" not in keys
        assert "real_target_identifier" not in keys


def test_agent_sabotage_scheming_monitor_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_sabotage_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "agent_sabotage_scheming_monitor_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_sabotage_monitor_bundle"
    assert result["bundle_id"] == "agent_sabotage_scheming_monitor_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["episode_count"] == 3
    assert result["monitor_score_count"] == 6
    assert result["counterfactual_replay_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["live_sabotage_authorized"] is False
