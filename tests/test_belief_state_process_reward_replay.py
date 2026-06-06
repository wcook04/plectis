from __future__ import annotations

import hashlib
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
SOURCE_ROOT = MICROCOSM_ROOT.parent


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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


def _fixture_payloads(input_dir: Path = FIXTURE_INPUT) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for name in (
        "projection_protocol.json",
        "reward_policy.json",
        "task_episodes.json",
        "belief_states.json",
        "verifier_feedback.json",
        "reward_events.json",
        "trajectory_groups.json",
        "cold_replay.json",
    ):
        path = input_dir / name
        if path.is_file():
            payloads[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return payloads


def _copy_fixture_input(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/belief_state_process_reward_replay/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    return input_dir


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
    assert result["semantic_recompute_status"] == "pass"
    assert result["semantic_recompute_row_count"] == 6
    assert result["semantic_recompute_verified_count"] == 6
    assert result["semantic_recompute_blocked_count"] == 0
    assert result["authority_ceiling"]["hidden_reasoning_export_authorized"] is False
    assert result["authority_ceiling"]["live_rl_training_authorized"] is False
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["source_mutation_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_belief_state_process_reward_semantic_recompute_accepts_real_fixture() -> None:
    result = belief_reward_replay.validate_semantic_recompute(_fixture_payloads())

    assert result["status"] == "pass"
    assert result["semantic_recompute_row_count"] == 6
    assert result["semantic_recompute_verified_count"] == 6
    assert result["semantic_recompute_blocked_count"] == 0
    assert result["findings"] == []
    for row in result["semantic_recompute_rows"]:
        assert row["computed_verdict"] == "verified_semantic_recompute"
        assert row["reason_codes"] == []
        assert row["feedback_ref"]
        assert row["process_reward_ref"]
        assert row["trajectory_group_id"]
        assert row["cold_replay_ref"]
        assert row["body_in_receipt"] is False


def test_belief_state_process_reward_rejects_real_but_wrong_semantic_refs(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    rewards_path = input_dir / "reward_events.json"
    reward_payload = json.loads(rewards_path.read_text(encoding="utf-8"))
    reward_payload["reward_events"][0]["verifier_feedback_ref"] = "fb_shop_1"
    reward_payload["reward_events"][2]["verifier_feedback_ref"] = "fb_shop_2"
    rewards_path.write_text(
        json.dumps(reward_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    row_local = belief_reward_replay.validate_reward_events(reward_payload)
    row_local_by_id = {
        row["reward_event_id"]: row for row in row_local["reward_rows"]
    }
    result = run(input_dir, tmp_path / "receipts")
    semantic_by_id = {
        row["belief_state_id"]: row for row in result["semantic_recompute_rows"]
    }

    assert row_local["status"] == "pass"
    assert row_local_by_id["rew_terminal_process_1"]["reason_codes"] == []
    assert result["status"] == "blocked"
    assert result["semantic_recompute_status"] == "blocked"
    assert result["semantic_recompute_verified_count"] == 4
    assert result["semantic_recompute_blocked_count"] == 2
    assert "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH" in result["error_codes"]
    assert semantic_by_id["belief_terminal_1"]["computed_verdict"] == "blocked"
    assert semantic_by_id["belief_terminal_2"]["computed_verdict"] == "blocked"
    assert "process_reward_feedback_mismatch" in semantic_by_id[
        "belief_terminal_1"
    ]["reason_codes"]
    assert "outcome_reward_feedback_episode_mismatch" in semantic_by_id[
        "belief_terminal_1"
    ]["reason_codes"]
    assert "outcome_reward_feedback_episode_mismatch" in semantic_by_id[
        "belief_terminal_2"
    ]["reason_codes"]
    assert result["body_in_receipt"] is False


def test_belief_state_process_reward_quantity_perturbation_moves_semantics(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    belief_path = input_dir / "belief_states.json"
    belief_payload = json.loads(belief_path.read_text(encoding="utf-8"))
    belief_payload["belief_states"][0]["belief_discrepancy"] = 0.99
    belief_path.write_text(
        json.dumps(belief_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    row_local = belief_reward_replay.validate_belief_states(belief_payload)
    row_local_by_id = {
        row["belief_state_id"]: row for row in row_local["belief_state_rows"]
    }
    result = run(input_dir, tmp_path / "receipts")
    semantic_by_id = {
        row["belief_state_id"]: row for row in result["semantic_recompute_rows"]
    }

    assert row_local["status"] == "pass"
    assert row_local_by_id["belief_terminal_1"]["computed_verdict"] == (
        "accepted_belief_state"
    )
    assert result["status"] == "blocked"
    assert result["semantic_recompute_verified_count"] == 5
    assert result["semantic_recompute_blocked_count"] == 1
    assert semantic_by_id["belief_terminal_1"]["computed_verdict"] == "blocked"
    assert "belief_discrepancy_mismatch" in semantic_by_id["belief_terminal_1"][
        "reason_codes"
    ]
    assert "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH" in result["error_codes"]


def test_belief_state_process_reward_rejects_boolean_numeric_fields() -> None:
    belief_payload = json.loads((FIXTURE_INPUT / "belief_states.json").read_text())
    reward_payload = json.loads((FIXTURE_INPUT / "reward_events.json").read_text())
    belief_payload["belief_states"][0]["belief_discrepancy"] = True
    reward_payload["reward_events"][0]["reward_value"] = True
    reward_payload["reward_events"][1]["belief_discrepancy"] = False

    belief_result = belief_reward_replay.validate_belief_states(belief_payload)
    reward_result = belief_reward_replay.validate_reward_events(reward_payload)

    belief_by_id = {
        row["belief_state_id"]: row for row in belief_result["belief_state_rows"]
    }
    reward_by_id = {
        row["reward_event_id"]: row for row in reward_result["reward_rows"]
    }
    assert belief_result["status"] == "blocked"
    assert reward_result["status"] == "blocked"
    assert "missing_belief_discrepancy" in belief_by_id["belief_terminal_1"][
        "reason_codes"
    ]
    assert "missing_reward_value" in reward_by_id["rew_terminal_process_1"][
        "reason_codes"
    ]
    assert "missing_belief_discrepancy" in reward_by_id["rew_terminal_process_2"][
        "reason_codes"
    ]


def test_belief_state_process_reward_rejects_mutated_real_positive_feedback_linkage() -> None:
    feedback_payload = json.loads(
        (FIXTURE_INPUT / "verifier_feedback.json").read_text()
    )
    reward_payload = json.loads((FIXTURE_INPUT / "reward_events.json").read_text())

    good_feedback = belief_reward_replay.validate_verifier_feedback(feedback_payload)
    good_rewards = belief_reward_replay.validate_reward_events(reward_payload)
    good_feedback_by_id = {
        row["feedback_id"]: row for row in good_feedback["feedback_rows"]
    }
    good_reward_by_id = {
        row["reward_event_id"]: row for row in good_rewards["reward_rows"]
    }

    assert good_feedback["status"] == "pass"
    assert good_rewards["status"] == "pass"
    assert good_feedback["accepted_feedback_count"] == 6
    assert good_rewards["process_reward_count"] == 6
    assert good_rewards["outcome_reward_count"] == 3
    assert good_feedback_by_id["fb_terminal_1"]["computed_verdict"] == (
        "accepted_feedback"
    )
    assert good_reward_by_id["rew_terminal_process_1"]["computed_verdict"] == (
        "accepted_reward_event"
    )

    feedback_payload["feedback"][0].pop("evidence_refs")
    reward_payload["reward_events"][0].pop("verifier_feedback_ref")
    reward_payload["reward_events"][0]["verifier_bypassed"] = True

    mutated_feedback = belief_reward_replay.validate_verifier_feedback(
        feedback_payload
    )
    mutated_rewards = belief_reward_replay.validate_reward_events(reward_payload)
    mutated_feedback_by_id = {
        row["feedback_id"]: row for row in mutated_feedback["feedback_rows"]
    }
    mutated_reward_by_id = {
        row["reward_event_id"]: row for row in mutated_rewards["reward_rows"]
    }

    assert mutated_feedback["status"] == "blocked"
    assert mutated_rewards["status"] == "blocked"
    assert mutated_feedback["accepted_feedback_count"] == (
        good_feedback["accepted_feedback_count"] - 1
    )
    assert mutated_rewards["process_reward_count"] == (
        good_rewards["process_reward_count"] - 1
    )
    assert mutated_rewards["outcome_reward_count"] == good_rewards[
        "outcome_reward_count"
    ]
    assert mutated_feedback_by_id["fb_terminal_1"]["computed_verdict"] == "blocked"
    assert mutated_reward_by_id["rew_terminal_process_1"]["computed_verdict"] == (
        "blocked"
    )
    assert "missing_evidence_refs" in mutated_feedback_by_id["fb_terminal_1"][
        "reason_codes"
    ]
    assert "missing_verifier_feedback_ref" in mutated_reward_by_id[
        "rew_terminal_process_1"
    ]["reason_codes"]
    assert "verifier_bypassed" in mutated_reward_by_id["rew_terminal_process_1"][
        "reason_codes"
    ]
    assert {
        row["error_code"] for row in mutated_feedback["findings"]
    } == {"BELIEF_REWARD_VERIFIER_FEEDBACK_FLOOR_MISSING"}
    assert {row["error_code"] for row in mutated_rewards["findings"]} == {
        "BELIEF_REWARD_EVENT_FLOOR_MISSING"
    }


def test_belief_state_process_reward_run_blocks_verifier_bypass_positive_row(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    baseline = run(input_dir, tmp_path / "receipts/baseline")
    baseline_reward_by_id = {
        row["reward_event_id"]: row for row in baseline["reward_rows"]
    }
    baseline_semantic_by_id = {
        row["belief_state_id"]: row for row in baseline["semantic_recompute_rows"]
    }

    assert baseline["status"] == "pass"
    assert baseline["accepted_feedback_count"] == 6
    assert baseline["process_reward_count"] == 6
    assert baseline["semantic_recompute_verified_count"] == 6
    assert baseline["semantic_recompute_blocked_count"] == 0
    assert baseline_reward_by_id["rew_terminal_process_1"]["computed_verdict"] == (
        "accepted_reward_event"
    )
    assert baseline_semantic_by_id["belief_terminal_1"]["computed_verdict"] == (
        "verified_semantic_recompute"
    )

    feedback_path = input_dir / "verifier_feedback.json"
    feedback_payload = json.loads(feedback_path.read_text(encoding="utf-8"))
    feedback_payload["feedback"][0].pop("evidence_refs")
    feedback_path.write_text(
        json.dumps(feedback_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rewards_path = input_dir / "reward_events.json"
    reward_payload = json.loads(rewards_path.read_text(encoding="utf-8"))
    reward_payload["reward_events"][0].pop("verifier_feedback_ref")
    reward_payload["reward_events"][0]["verifier_bypassed"] = True
    rewards_path.write_text(
        json.dumps(reward_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, tmp_path / "receipts/verifier_bypass")
    reward_by_id = {row["reward_event_id"]: row for row in result["reward_rows"]}
    feedback_by_id = {row["feedback_id"]: row for row in result["feedback_rows"]}
    semantic_by_id = {
        row["belief_state_id"]: row for row in result["semantic_recompute_rows"]
    }

    assert result["status"] == "blocked"
    assert result["accepted_feedback_count"] == baseline["accepted_feedback_count"] - 1
    assert result["process_reward_count"] == baseline["process_reward_count"] - 1
    assert result["outcome_reward_count"] == baseline["outcome_reward_count"]
    assert result["semantic_recompute_verified_count"] == (
        baseline["semantic_recompute_verified_count"] - 1
    )
    assert result["semantic_recompute_blocked_count"] == (
        baseline["semantic_recompute_blocked_count"] + 1
    )
    assert result["semantic_recompute_status"] == "blocked"
    assert "BELIEF_REWARD_VERIFIER_FEEDBACK_FLOOR_MISSING" in result["error_codes"]
    assert "BELIEF_REWARD_EVENT_FLOOR_MISSING" in result["error_codes"]
    assert "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH" in result["error_codes"]
    assert feedback_by_id["fb_terminal_1"]["computed_verdict"] == "blocked"
    assert "missing_evidence_refs" in feedback_by_id["fb_terminal_1"][
        "reason_codes"
    ]
    assert reward_by_id["rew_terminal_process_1"]["computed_verdict"] == "blocked"
    assert "missing_verifier_feedback_ref" in reward_by_id[
        "rew_terminal_process_1"
    ]["reason_codes"]
    assert "verifier_bypassed" in reward_by_id["rew_terminal_process_1"][
        "reason_codes"
    ]
    assert semantic_by_id["belief_terminal_1"]["computed_verdict"] == "blocked"
    assert "process_reward_feedback_mismatch" in semantic_by_id[
        "belief_terminal_1"
    ]["reason_codes"]
    assert result["body_in_receipt"] is False


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
    source = SOURCE_ROOT / "system/lib/agent_execution_trace.py"
    target = (
        MICROCOSM_ROOT
        / "src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
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
    assert result["source_module_manifest_status"] == "pass"
    assert result["body_copied_material_count"] == 7
    assert (
        result["source_open_body_imports"]["body_material_status"]
        == "copied_non_secret_belief_state_process_reward_macro_body_landed"
    )
    assert result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert result["episode_count"] == 3
    assert result["process_reward_count"] == 6
    assert result["outcome_reward_count"] == 3
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["hidden_reasoning_export_authorized"] is False
    verification = result["body_import_verification"]
    assert verification["verification_status"] == "verified"
    assert verification["verification_mode"] == (
        "source_faithful_public_refactor_with_live_digest_relation"
    )
    assert verification["source_to_target_relation"] == (
        "source_faithful_public_refactor"
    )
    assert verification["digest_relation"] == "source_target_refactor_digests_recorded"
    assert verification["source_ref"] == "system/lib/agent_execution_trace.py"
    assert verification["target_file_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
    )
    assert verification["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/"
        "agent_execution_trace.py::build_public_belief_state_process_reward_trace"
    )
    assert verification["source_body_digest"] == _sha256(source)
    assert verification["target_body_digest"] == _sha256(target)
    assert verification["body_in_receipt"] is False


def test_belief_state_process_reward_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/belief_state_process_reward_replay",
        public_root / "examples/belief_state_process_reward_replay",
    )
    bundle = (
        public_root
        / "examples/belief_state_process_reward_replay/"
        "exported_belief_state_process_reward_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "sha256:" + ("0" * 64)
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_reward_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "belief_state_process_reward_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "BELIEF_REWARD_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_belief_state_process_reward_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/belief_state_process_reward_replay",
        public_root / "examples/belief_state_process_reward_replay",
    )
    bundle = (
        public_root
        / "examples/belief_state_process_reward_replay/"
        "exported_belief_state_process_reward_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_reward_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "belief_state_process_reward_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "BELIEF_REWARD_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_belief_state_process_reward_rejects_rehashed_source_module_body_swap(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/belief_state_process_reward_replay",
        public_root / "examples/belief_state_process_reward_replay",
    )
    bundle = (
        public_root
        / "examples/belief_state_process_reward_replay/"
        "exported_belief_state_process_reward_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = next(
        row
        for row in manifest["modules"]
        if row["module_id"] == "strict_json_source_body_import"
    )
    target = bundle / module["path"]
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n# rehashed source-module body swap keeps declared anchors\n",
        encoding="utf-8",
    )
    rehashed = _sha256(target)
    module["sha256"] = rehashed
    module["source_sha256"] = rehashed
    module["target_sha256"] = rehashed
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_reward_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "belief_state_process_reward_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "BELIEF_REWARD_SOURCE_MODULE_DIGEST_MISMATCH" not in result["error_codes"]
    assert (
        "BELIEF_REWARD_SOURCE_MODULE_SOURCE_AUTHORITY_MISMATCH"
        in result["error_codes"]
    )


def test_belief_state_process_reward_rejects_source_module_manifest_boundaries(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "missing_manifest",
            "BELIEF_REWARD_SOURCE_MODULE_MANIFEST_REQUIRED",
            "source_module_manifest",
        ),
        (
            "manifest_class_invalid",
            "BELIEF_REWARD_SOURCE_MODULE_CLASS_REQUIRED",
            "source_import_class",
        ),
        (
            "manifest_body_in_receipt",
            "BELIEF_REWARD_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
            "body_in_receipt",
        ),
        (
            "manifest_body_text_in_receipt",
            "BELIEF_REWARD_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
            "body_text_in_receipt",
        ),
        (
            "manifest_count_mismatch",
            "BELIEF_REWARD_SOURCE_MODULE_COUNT_MISMATCH",
            "module_count",
        ),
        (
            "row_class_invalid",
            "BELIEF_REWARD_SOURCE_MODULE_CLASS_REQUIRED",
            "source_import_class",
        ),
        (
            "row_material_class_invalid",
            "BELIEF_REWARD_SOURCE_MODULE_CLASS_REQUIRED",
            "material_class",
        ),
        (
            "row_body_boundary",
            "BELIEF_REWARD_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
            "source_module",
        ),
        (
            "target_missing",
            "BELIEF_REWARD_SOURCE_MODULE_TARGET_MISSING",
            "source_module",
        ),
    ]

    for case_id, expected_code, expected_subject_kind in cases:
        public_root = tmp_path / case_id / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        shutil.copytree(
            MICROCOSM_ROOT / "examples/belief_state_process_reward_replay",
            public_root / "examples/belief_state_process_reward_replay",
        )
        bundle = (
            public_root
            / "examples/belief_state_process_reward_replay/"
            "exported_belief_state_process_reward_bundle"
        )
        manifest_path = bundle / "source_module_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_module = manifest["modules"][0]

        if case_id == "missing_manifest":
            manifest_path.unlink()
        elif case_id == "manifest_class_invalid":
            manifest["source_import_class"] = "private_macro_body"
        elif case_id == "manifest_body_in_receipt":
            manifest["body_in_receipt"] = True
        elif case_id == "manifest_body_text_in_receipt":
            manifest["body_text_in_receipt"] = True
        elif case_id == "manifest_count_mismatch":
            manifest["module_count"] += 1
        elif case_id == "row_class_invalid":
            first_module["source_import_class"] = "private_macro_body"
        elif case_id == "row_material_class_invalid":
            first_module["material_class"] = "private_macro_body"
        elif case_id == "row_body_boundary":
            first_module["body_in_receipt"] = True
        elif case_id == "target_missing":
            (bundle / first_module["path"]).unlink()

        if manifest_path.exists():
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        result = run_reward_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            f"belief_state_process_reward_replay/{case_id}",
            command="pytest",
        )
        source_modules = result["source_module_imports"]

        assert result["status"] == "blocked"
        assert result["source_module_manifest_status"] == "blocked"
        assert source_modules["status"] == "blocked"
        assert source_modules["body_in_receipt"] is False
        assert source_modules["body_text_in_receipt"] is False
        assert expected_code in result["error_codes"]
        findings = [
            row
            for row in source_modules["findings"]
            if row["error_code"] == expected_code
        ]
        assert findings
        assert {row["subject_kind"] for row in findings} == {expected_subject_kind}
        assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert result["body_in_receipt"] is False
        receipt_text = json.dumps(result, sort_keys=True)
        assert "TRACE_OUTPUT_PRIVACY_BOUNDARY =" not in receipt_text
        assert "def build_public_belief_state_process_reward_trace(" not in receipt_text


def test_belief_state_process_reward_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["body_in_receipt"] is False
    assert manifest["body_text_in_receipt"] is False
    assert manifest["module_count"] == 7
    assert {
        row["module_id"] for row in manifest["modules"]
    } == {
        "belief_reward_extracted_patterns_ledger_body_import",
        "belief_reward_high_novelty_growth_receipt_body_import",
        "belief_reward_canonical_organ_model_body_import",
        "agent_execution_trace_runtime_body_import",
        "strict_json_source_body_import",
        "agent_execution_trace_standard_body_import",
        "extracted_pattern_route_readiness_tool_body_import",
    }

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix(
            "microcosm-substrate/"
        )
        text = target.read_text(encoding="utf-8")
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == row["source_sha256"]
        assert _sha256(target) == row["target_sha256"]
        assert row["source_sha256"] == row["target_sha256"]
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_belief_state_process_reward_freshness_tracks_live_source_authority(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())
    source_refs = {row["source_ref"] for row in manifest["modules"]}
    baseline = belief_reward_replay._freshness_basis(
        BUNDLE_INPUT,
        include_negative=False,
    )
    baseline_paths = {row["path"] for row in baseline["inputs"]}

    assert source_refs <= baseline_paths

    authority = tmp_path / "live_authority.py"
    authority.write_text("version = 1\n", encoding="utf-8")
    original_authority_path = belief_reward_replay._source_module_authority_path

    def authority_path(source_ref: str, *, public_root: Path) -> Path | None:
        if source_ref == "system/lib/strict_json.py":
            return authority
        return original_authority_path(source_ref, public_root=public_root)

    monkeypatch.setattr(
        belief_reward_replay,
        "_source_module_authority_path",
        authority_path,
    )
    first = belief_reward_replay._freshness_basis(BUNDLE_INPUT, include_negative=False)
    authority.write_text("version = 2\n", encoding="utf-8")
    second = belief_reward_replay._freshness_basis(BUNDLE_INPUT, include_negative=False)

    assert first["basis_digest"] != second["basis_digest"]
    assert first["missing_path_count"] == 0
    assert second["missing_path_count"] == 0


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
    assert first_card["validation"]["source_module_manifest_status"] == "pass"
    assert first_card["validation"]["body_material_count"] == 7
    assert (
        first_card["validation"]["body_material_status"]
        == "copied_non_secret_belief_state_process_reward_macro_body_landed"
    )
    assert "episode_rows" not in _walk_keys(first_card)
    assert "belief_state_rows" not in _walk_keys(first_card)
    assert "feedback_rows" not in _walk_keys(first_card)
    assert "reward_rows" not in _walk_keys(first_card)
    assert "source_module_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
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
