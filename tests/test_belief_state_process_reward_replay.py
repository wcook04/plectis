from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.belief_state_process_reward_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_reward_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/belief_state_process_reward_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/belief_state_process_reward_replay/"
    "exported_belief_state_process_reward_bundle"
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


def test_belief_state_process_reward_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/belief_state_process_reward_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "belief_state_process_reward_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["episode_count"] == 3
    assert result["accepted_episode_count"] == 3
    assert result["belief_state_count"] == 6
    assert result["accepted_belief_state_count"] == 6
    assert result["accepted_feedback_count"] == 6
    assert result["process_reward_count"] == 6
    assert result["outcome_reward_count"] == 3
    assert result["trajectory_group_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["hidden_reasoning_export_authorized"] is False
    assert result["authority_ceiling"]["live_rl_training_authorized"] is False
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_belief_state_process_reward_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/belief_state_process_reward_replay",
        public_root / "fixtures/first_wave/belief_state_process_reward_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/belief_state_process_reward_replay/input",
        public_root / "receipts/first_wave/belief_state_process_reward_replay",
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
        assert "hidden_chain_of_thought" not in keys
        assert "raw_chain_of_thought" not in keys
        assert "private_reasoning_body" not in keys
        assert "provider_payload" not in keys
        assert "gold_answer_body" not in keys
        assert "live_training_run_id" not in keys
        assert "benchmark_submission_id" not in keys


def test_belief_state_process_reward_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_reward_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "belief_state_process_reward_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_belief_state_process_reward_bundle"
    assert result["bundle_id"] == "belief_state_process_reward_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["episode_count"] == 3
    assert result["process_reward_count"] == 6
    assert result["outcome_reward_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["hidden_reasoning_export_authorized"] is False
