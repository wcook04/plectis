from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.belief_state_process_reward_replay as belief_reward_replay
from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_belief_state_process_reward_trace,
)
from microcosm_core.organs.belief_state_process_reward_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
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
    assert result["body_import_status"] == "extension_of_existing_public_refactor_landed"
    assert result["body_import_classification"] == "extension_of_existing_public_refactor"
    assert result["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 6
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
        assert "private_state_scan" not in keys
        assert "public_replacement_refs" not in keys


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
    assert result["bundle_id"] == "belief_state_process_reward_public_trace_refactor"
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == 6
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["episode_count"] == 3
    assert result["process_reward_count"] == 6
    assert result["outcome_reward_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["hidden_reasoning_export_authorized"] is False


def test_belief_state_process_reward_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "belief_state_process_reward_replay"
    )
    args = [
        "run-reward-bundle",
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
    assert first_card["belief_reward"]["episode_count"] == 3
    assert first_card["belief_reward"]["belief_state_count"] == 6
    assert first_card["belief_reward"]["accepted_feedback_count"] == 6
    assert first_card["belief_reward"]["process_reward_count"] == 6
    assert first_card["belief_reward"]["outcome_reward_count"] == 3
    assert first_card["belief_reward"]["cold_replay_pass_count"] == 3
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["public_trace_status"] == "pass"
    assert first_card["validation"]["public_trace_span_count"] == 6
    assert "episode_rows" not in _walk_keys(first_card)
    assert "belief_state_rows" not in _walk_keys(first_card)
    assert "feedback_rows" not in _walk_keys(first_card)
    assert "reward_rows" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "public_agent_execution_trace" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(belief_reward_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_belief_state_process_reward_has_public_trace_projection() -> None:
    trace = build_public_belief_state_process_reward_trace(BUNDLE_INPUT)

    assert trace["status"] == "pass"
    assert trace["schema_version"] == "public_agent_execution_trace_refactor_v0"
    assert trace["span_count"] == 6
    assert trace["body_in_receipt"] is False
    assert trace["summary"]["outcome_counts"] == {"process_reward_verified": 6}
    assert trace["audit"]["coverage"] == {
        "belief_state_summary_coverage": True,
        "feedback_ref_coverage": True,
        "process_reward_ref_coverage": True,
        "outcome_reward_ref_coverage": True,
        "cold_replay_receipt_coverage": True,
        "no_hidden_reasoning_export_coverage": True,
        "metadata_only_private_ref_coverage": True,
        "body_in_receipt": False,
    }
    assert {
        span["tool_name"] for span in trace["spans"]
    } == {"belief_state_process_reward_replay"}
