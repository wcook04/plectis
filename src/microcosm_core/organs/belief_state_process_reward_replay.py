from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_belief_state_process_reward_trace,
)
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "belief_state_process_reward_replay"
FIXTURE_ID = "first_wave.belief_state_process_reward_replay"
VALIDATOR_ID = "validator.microcosm.organs.belief_state_process_reward_replay"

RESULT_NAME = "belief_state_process_reward_replay_result.json"
BOARD_NAME = "belief_state_process_reward_replay_board.json"
VALIDATION_RECEIPT_NAME = "belief_state_process_reward_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "belief_state_process_reward_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_belief_state_process_reward_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "reward_policy.json",
    "task_episodes.json",
    "belief_states.json",
    "verifier_feedback.json",
    "reward_events.json",
    "trajectory_groups.json",
    "cold_replay.json",
)
NEGATIVE_INPUT_NAMES = (
    "hidden_chain_of_thought_export.json",
    "neural_judge_only_process_label.json",
    "hidden_gold_label.json",
    "reward_by_formatting.json",
    "verifier_bypass.json",
    "benchmark_performance_claim.json",
    "final_answer_only_scoring.json",
)

EXPECTED_NEGATIVE_CASES = {
    "hidden_chain_of_thought_export": ["BELIEF_REWARD_HIDDEN_COT_EXPORT"],
    "neural_judge_only_process_label": ["BELIEF_REWARD_NEURAL_JUDGE_ONLY_LABEL"],
    "hidden_gold_label": ["BELIEF_REWARD_HIDDEN_GOLD_LABEL"],
    "reward_by_formatting": ["BELIEF_REWARD_FORMAT_REWARD_HACK"],
    "verifier_bypass": ["BELIEF_REWARD_VERIFIER_BYPASS"],
    "benchmark_performance_claim": ["BELIEF_REWARD_BENCHMARK_CLAIM"],
    "final_answer_only_scoring": ["BELIEF_REWARD_FINAL_ANSWER_ONLY"],
}

REQUIRED_TASK_TYPES = (
    "terminal_investigation",
    "mock_purchase",
    "formal_planning_toy",
)
REQUIRED_BELIEF_FIELDS = (
    "belief_state_id",
    "episode_id",
    "step_id",
    "observation_digest_ref",
    "belief_state_json",
    "predicted_next_evidence",
    "feedback_ref",
    "belief_discrepancy",
    "trajectory_group_id",
    "body_redacted",
    "private_ref_metadata_only",
)
FORBIDDEN_KEYS = (
    "hidden_chain_of_thought",
    "raw_chain_of_thought",
    "private_reasoning_body",
    "provider_payload",
    "hidden_gold_label",
    "gold_answer_body",
    "live_training_run_id",
    "benchmark_submission_id",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_agent_execution_trace_refactor_over_belief_state_process_reward_policy"
    ),
    "hidden_reasoning_export_authorized": False,
    "live_rl_training_authorized": False,
    "neural_judge_only_authorized": False,
    "hidden_gold_label_authorized": False,
    "benchmark_score_claim_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Belief-state process reward replay validates a source-faithful public "
    "agent-execution trace refactor over belief summaries, verifier or feedback "
    "observations, process rewards, outcome rewards, reward-hacking trap results, "
    "trajectory groups, cold replay, negative cases, secret-exclusion scan, and "
    "authority ceilings. It does not export hidden reasoning, run RL, use hidden "
    "gold labels, rely on neural-judge-only labels, claim benchmark performance, "
    "call providers, mutate source, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[str(case_id)].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def _negative_rows(payloads: dict[str, object]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads.values():
        nested = _rows(payload, "negative_cases")
        if nested:
            rows.extend(nested)
        elif isinstance(payload, dict):
            rows.append(payload)
    return rows


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    body_import = protocol.get("body_import_verification", {})
    if not isinstance(body_import, dict):
        body_import = {}
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 5
        or "belief_state_process_reward_replay_compound" not in source_pattern_ids
        or len(projection_receipts) < 2
        or "system/lib/agent_execution_trace.py" not in source_refs
        or "codex/standards/std_agent_execution_trace.json" not in source_refs
        or not any(ref.endswith("macro_tools/agent_execution_trace.py") for ref in target_refs)
        or not any(
            ref.endswith("organs/belief_state_process_reward_replay.py")
            for ref in target_refs
        )
        or not any(
            ref.endswith("build_public_belief_state_process_reward_trace")
            for ref in target_symbols
        )
        or not any(ref.endswith("run_reward_bundle") for ref in target_symbols)
        or not public_runtime_refs
        or not _strings(protocol.get("reimplemented"))
        or not _strings(protocol.get("omitted"))
        or protocol.get("body_import_status")
        != "extension_of_existing_public_refactor_landed"
        or body_import.get("verification_status") != "verified"
        or body_import.get("body_import_classification")
        != "extension_of_existing_public_refactor"
        or protocol.get("body_in_receipt") is not False
    ):
        findings.append(
            _finding(
                "BELIEF_REWARD_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, projection receipts, target refs, target symbols, public runtime refs, body-import verification, reimplemented pieces, and omissions.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for field in (
        "copied_hidden_reasoning",
        "copied_provider_payloads",
        "copied_private_memory_bodies",
    ):
        if protocol.get(field) is not False:
            findings.append(
                _finding(
                    "BELIEF_REWARD_PRIVATE_BODY_COPY_CLAIM",
                    "Projection protocol must explicitly deny copying hidden reasoning, provider payloads, or private memory bodies.",
                    case_id="projection_protocol_floor",
                    subject_id=field,
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "target_refs": target_refs,
        "target_symbols": target_symbols,
        "public_runtime_refs": public_runtime_refs,
        "body_import_status": protocol.get("body_import_status"),
        "body_import_verification": body_import,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_reward_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    required_fields = set(_strings(policy.get("required_belief_state_fields")))
    reward_sources = set(_strings(policy.get("allowed_process_reward_sources")))
    findings: list[dict[str, Any]] = []
    if not set(REQUIRED_BELIEF_FIELDS).issubset(required_fields):
        findings.append(
            _finding(
                "BELIEF_REWARD_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Reward policy must require observation digest, typed belief state, prediction, feedback, discrepancy, trajectory, and redaction fields.",
                case_id="reward_policy_floor",
                subject_id=str(policy.get("policy_id") or "reward_policy"),
                subject_kind="reward_policy",
            )
        )
    if not {"deterministic_verifier", "observed_environment_feedback"}.issubset(
        reward_sources
    ):
        findings.append(
            _finding(
                "BELIEF_REWARD_POLICY_SOURCE_FLOOR_MISSING",
                "Process reward sources must include deterministic verifier and observed environment feedback refs.",
                case_id="reward_policy_floor",
                subject_id=str(policy.get("policy_id") or "reward_policy"),
                subject_kind="reward_policy",
            )
        )
    for field in (
        "hidden_reasoning_export_authorized",
        "neural_judge_only_authorized",
        "hidden_gold_label_authorized",
        "live_rl_training_authorized",
        "benchmark_score_claim_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "BELIEF_REWARD_POLICY_AUTHORITY_OVERCLAIM",
                    "Belief-state reward policy cannot authorize hidden reasoning export, neural-judge-only labels, hidden gold labels, live RL, provider calls, benchmark claims, or release.",
                    case_id="reward_policy_floor",
                    subject_id=field,
                    subject_kind="reward_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "required_belief_state_fields": sorted(required_fields),
        "allowed_process_reward_sources": sorted(reward_sources),
        "minimum_reliability_score": float(policy.get("minimum_reliability_score") or 0),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_task_episodes(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "episodes")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        task_type = str(row.get("task_type") or "")
        if task_type not in REQUIRED_TASK_TYPES:
            reasons.append("unknown_task_type")
        for field in (
            "episode_id",
            "task_spec_hash",
            "trajectory_group_id",
            "outcome_reward_ref",
            "cold_replay_ref",
        ):
            if not row.get(field):
                reasons.append(f"missing_{field}")
        if not _strings(row.get("observation_digest_refs")):
            reasons.append("missing_observation_digest_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if row.get("private_ref_metadata_only") is not True:
            reasons.append("private_ref_not_metadata_only")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "episode_id": str(row.get("episode_id") or ""),
                "task_type": task_type,
                "trajectory_group_id": row.get("trajectory_group_id"),
                "observation_digest_count": len(
                    _strings(row.get("observation_digest_refs"))
                ),
                "outcome_reward_ref": row.get("outcome_reward_ref"),
                "cold_replay_ref": row.get("cold_replay_ref"),
                "computed_verdict": "accepted_episode" if not reasons else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    task_types = {row["task_type"] for row in accepted if not row["reason_codes"]}
    if (
        len(rows) < 3
        or not set(REQUIRED_TASK_TYPES).issubset(task_types)
        or any(row["reason_codes"] for row in accepted)
    ):
        findings.append(
            _finding(
                "BELIEF_REWARD_EPISODE_FLOOR_MISSING",
                "Positive fixture must include three redacted partially observable episodes with spec hashes, observation digests, outcome refs, and cold replay refs.",
                case_id="episode_floor",
                subject_id="task_episodes",
                subject_kind="episode_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "episode_count": len(rows),
        "accepted_episode_count": sum(1 for row in accepted if not row["reason_codes"]),
        "task_types": sorted(task_types),
        "episode_rows": sorted(accepted, key=lambda row: row["episode_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_belief_states(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "belief_states")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        belief_id = str(row.get("belief_state_id") or "")
        reasons: list[str] = []
        missing = [
            field
            for field in REQUIRED_BELIEF_FIELDS
            if field not in row or row.get(field) in (None, "", [])
        ]
        if missing:
            reasons.append("missing_required_fields")
        belief_state = row.get("belief_state_json")
        if not isinstance(belief_state, dict):
            reasons.append("belief_state_not_typed_json")
        elif _has_forbidden_key(belief_state):
            reasons.append("forbidden_private_payload_key")
        if not _strings(row.get("predicted_next_evidence")):
            reasons.append("missing_predicted_next_evidence")
        if not row.get("feedback_ref"):
            reasons.append("missing_feedback_ref")
        if not isinstance(row.get("belief_discrepancy"), (int, float)):
            reasons.append("missing_belief_discrepancy")
        if row.get("hidden_chain_of_thought_exported") is not False:
            reasons.append("hidden_reasoning_export")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if row.get("private_ref_metadata_only") is not True:
            reasons.append("private_ref_not_metadata_only")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "belief_state_id": belief_id,
                "episode_id": row.get("episode_id"),
                "step_id": row.get("step_id"),
                "observation_digest_ref": row.get("observation_digest_ref"),
                "predicted_next_evidence_count": len(
                    _strings(row.get("predicted_next_evidence"))
                ),
                "feedback_ref": row.get("feedback_ref"),
                "belief_discrepancy": row.get("belief_discrepancy"),
                "trajectory_group_id": row.get("trajectory_group_id"),
                "computed_verdict": "accepted_belief_state"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    if len(rows) < 6 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_BELIEF_STATE_FLOOR_MISSING",
                "Positive fixture must expose typed redacted belief-state JSON with observation digest, prediction, feedback, discrepancy, and trajectory refs.",
                case_id="belief_state_floor",
                subject_id="belief_states",
                subject_kind="belief_state_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "belief_state_count": len(rows),
        "accepted_belief_state_count": sum(
            1 for row in accepted if not row["reason_codes"]
        ),
        "belief_state_rows": sorted(accepted, key=lambda row: row["belief_state_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_verifier_feedback(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "feedback")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        score = float(row.get("reliability_score") or 0)
        if row.get("feedback_kind") not in {
            "deterministic_verifier",
            "observed_environment_feedback",
        }:
            reasons.append("unknown_feedback_kind")
        if score < 0.8:
            reasons.append("reliability_below_floor")
        if row.get("neural_judge_only") is True:
            reasons.append("neural_judge_only")
        if row.get("hidden_gold_label_present") is True:
            reasons.append("hidden_gold_label")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "feedback_id": str(row.get("feedback_id") or ""),
                "episode_id": row.get("episode_id"),
                "feedback_kind": row.get("feedback_kind"),
                "reliability_score": score,
                "evidence_ref_count": len(_strings(row.get("evidence_refs"))),
                "computed_verdict": "accepted_feedback" if not reasons else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    if len(rows) < 6 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_VERIFIER_FEEDBACK_FLOOR_MISSING",
                "Positive fixture must carry reliable deterministic verifier or observed feedback refs, not neural-judge-only or hidden-gold labels.",
                case_id="verifier_feedback_floor",
                subject_id="verifier_feedback",
                subject_kind="feedback_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "feedback_count": len(rows),
        "accepted_feedback_count": sum(
            1 for row in accepted if not row["reason_codes"]
        ),
        "feedback_rows": sorted(accepted, key=lambda row: row["feedback_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_reward_events(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "reward_events")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        reward_kind = str(row.get("reward_kind") or "")
        if reward_kind not in {"process", "outcome"}:
            reasons.append("unknown_reward_kind")
        if not row.get("belief_state_id") and reward_kind == "process":
            reasons.append("missing_belief_state_ref")
        if not row.get("verifier_feedback_ref"):
            reasons.append("missing_verifier_feedback_ref")
        if not isinstance(row.get("reward_value"), (int, float)):
            reasons.append("missing_reward_value")
        if not isinstance(row.get("belief_discrepancy"), (int, float)):
            reasons.append("missing_belief_discrepancy")
        if row.get("reward_hacking_trap_result") != PASS:
            reasons.append("reward_hacking_trap_failed")
        if row.get("reward_by_formatting") is True:
            reasons.append("reward_by_formatting")
        if row.get("verifier_bypassed") is True:
            reasons.append("verifier_bypassed")
        if row.get("final_answer_only_scoring") is True:
            reasons.append("final_answer_only_scoring")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "reward_event_id": str(row.get("reward_event_id") or ""),
                "episode_id": row.get("episode_id"),
                "belief_state_id": row.get("belief_state_id"),
                "reward_kind": reward_kind,
                "reward_value": row.get("reward_value"),
                "belief_discrepancy": row.get("belief_discrepancy"),
                "verifier_feedback_ref": row.get("verifier_feedback_ref"),
                "reward_hacking_trap_result": row.get("reward_hacking_trap_result"),
                "computed_verdict": "accepted_reward_event"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    process_count = sum(
        1
        for row in accepted
        if row["reward_kind"] == "process" and not row["reason_codes"]
    )
    outcome_count = sum(
        1
        for row in accepted
        if row["reward_kind"] == "outcome" and not row["reason_codes"]
    )
    if process_count < 6 or outcome_count < 3 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_EVENT_FLOOR_MISSING",
                "Positive fixture must carry process and outcome rewards tied to feedback refs, belief discrepancy, and reward-hacking trap results.",
                case_id="reward_event_floor",
                subject_id="reward_events",
                subject_kind="reward_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "reward_event_count": len(rows),
        "process_reward_count": process_count,
        "outcome_reward_count": outcome_count,
        "reward_rows": sorted(accepted, key=lambda row: row["reward_event_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_trajectory_groups(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "trajectory_groups")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if not row.get("trajectory_group_id"):
            reasons.append("missing_trajectory_group_id")
        if not _strings(row.get("episode_ids")):
            reasons.append("missing_episode_ids")
        if not _strings(row.get("process_reward_refs")):
            reasons.append("missing_process_reward_refs")
        if not row.get("outcome_reward_ref"):
            reasons.append("missing_outcome_reward_ref")
        if row.get("reward_alignment") != "aligned":
            reasons.append("reward_alignment_not_aligned")
        if row.get("cold_replay_status") != PASS:
            reasons.append("cold_replay_not_pass")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "trajectory_group_id": str(row.get("trajectory_group_id") or ""),
                "episode_ids": _strings(row.get("episode_ids")),
                "process_reward_ref_count": len(_strings(row.get("process_reward_refs"))),
                "outcome_reward_ref": row.get("outcome_reward_ref"),
                "reward_alignment": row.get("reward_alignment"),
                "cold_replay_status": row.get("cold_replay_status"),
                "computed_verdict": "accepted_trajectory_group"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    if len(rows) < 3 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_TRAJECTORY_GROUP_FLOOR_MISSING",
                "Positive fixture must group each task trajectory with process rewards, outcome reward, alignment verdict, and cold replay pass.",
                case_id="trajectory_group_floor",
                subject_id="trajectory_groups",
                subject_kind="trajectory_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "trajectory_group_count": len(rows),
        "accepted_trajectory_group_count": sum(
            1 for row in accepted if not row["reason_codes"]
        ),
        "trajectory_group_rows": sorted(
            accepted, key=lambda row: row["trajectory_group_id"]
        ),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cold_replay(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "cold_replays")
    findings: list[dict[str, Any]] = []
    passing = [
        row
        for row in rows
        if row.get("status") == PASS
        and row.get("body_redacted") is True
        and row.get("private_ref_metadata_only") is True
    ]
    if len(passing) < 3:
        findings.append(
            _finding(
                "BELIEF_REWARD_COLD_REPLAY_FLOOR_MISSING",
                "Positive fixture must include redacted cold replay receipts for all three trajectory groups.",
                case_id="cold_replay_floor",
                subject_id="cold_replay",
                subject_kind="cold_replay_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": len(passing),
        "cold_replay_rows": [
            {
                "replay_id": str(row.get("replay_id") or ""),
                "trajectory_group_id": str(row.get("trajectory_group_id") or ""),
                "status": row.get("status"),
                "evidence_refs": _strings(row.get("evidence_refs")),
                "body_in_receipt": False,
                "private_ref_metadata_only": row.get("private_ref_metadata_only") is True,
            }
            for row in rows
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_negative_cases(payloads: dict[str, object]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _negative_rows(payloads):
        case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or "")
        subject_id = str(row.get("case_id") or case_id or "negative_case")
        if row.get("hidden_chain_of_thought_exported") is True or _has_forbidden_key(row):
            _record(
                findings,
                observed,
                "BELIEF_REWARD_HIDDEN_COT_EXPORT",
                "Belief-state summaries cannot export hidden chain-of-thought or private reasoning bodies.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("neural_judge_only") is True and not row.get("verifier_receipt_ref"):
            _record(
                findings,
                observed,
                "BELIEF_REWARD_NEURAL_JUDGE_ONLY_LABEL",
                "Process reward labels need observable verifier or feedback refs; neural-judge-only labels are not admitted.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("hidden_gold_label_present") is True:
            _record(
                findings,
                observed,
                "BELIEF_REWARD_HIDDEN_GOLD_LABEL",
                "Hidden gold labels cannot appear in public process-reward fixtures.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("reward_by_formatting") is True or row.get(
            "reward_hacking_trap_result"
        ) == "fail":
            _record(
                findings,
                observed,
                "BELIEF_REWARD_FORMAT_REWARD_HACK",
                "Reward-by-formatting and failed reward-hacking traps must block claim admission.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("verifier_bypassed") is True or (
            row.get("verifier_feedback_required") is True
            and not row.get("verifier_feedback_ref")
        ):
            _record(
                findings,
                observed,
                "BELIEF_REWARD_VERIFIER_BYPASS",
                "Verifier or observed feedback refs cannot be bypassed by a process reward claim.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("benchmark_performance_claim") is True:
            _record(
                findings,
                observed,
                "BELIEF_REWARD_BENCHMARK_CLAIM",
                "Public belief-state process reward replay cannot claim benchmark performance.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("final_answer_only_scoring") is True:
            _record(
                findings,
                observed,
                "BELIEF_REWARD_FINAL_ANSWER_ONLY",
                "Final-answer-only scoring is not process reward; observation, belief, feedback, and reward receipts are required.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
    return {
        "status": PASS,
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    public_trace = build_public_belief_state_process_reward_trace(input_dir)

    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    projection = validate_projection_protocol(payloads["projection_protocol"])
    reward_policy = validate_reward_policy(payloads["reward_policy"])
    episodes = validate_task_episodes(payloads["task_episodes"])
    belief_states = validate_belief_states(payloads["belief_states"])
    feedback = validate_verifier_feedback(payloads["verifier_feedback"])
    rewards = validate_reward_events(payloads["reward_events"])
    trajectories = validate_trajectory_groups(payloads["trajectory_groups"])
    cold_replay = validate_cold_replay(payloads["cold_replay"])
    negatives = validate_negative_cases(negative_payloads)

    observed = _merge_observed(
        projection,
        reward_policy,
        episodes,
        belief_states,
        feedback,
        rewards,
        trajectories,
        cold_replay,
        negatives,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        reward_policy,
        episodes,
        belief_states,
        feedback,
        rewards,
        trajectories,
        cold_replay,
        negatives,
    )
    positive_findings = _merge_findings(
        projection,
        reward_policy,
        episodes,
        belief_states,
        feedback,
        rewards,
        trajectories,
        cold_replay,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and public_trace["status"] == PASS
        and not positive_findings
        and projection["status"] == PASS
        and reward_policy["status"] == PASS
        and episodes["status"] == PASS
        and belief_states["status"] == PASS
        and feedback["status"] == PASS
        and rewards["status"] == PASS
        and trajectories["status"] == PASS
        and cold_replay["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "belief_state_process_reward_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id")
        if isinstance(bundle_manifest, dict)
        else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "public_agent_execution_trace": public_trace,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_status": "extension_of_existing_public_refactor_landed",
        "body_import_classification": "extension_of_existing_public_refactor",
        "product_path_role": "source_faithful_public_agent_execution_trace_refactor",
        "body_import_verification": {
            "verification_status": "verified",
            "body_import_classification": "extension_of_existing_public_refactor",
            "public_trace_status": public_trace["status"],
            "public_trace_span_count": public_trace["span_count"],
            "trace_digest": public_trace["summary"]["trace_digest"],
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": (
                "microcosm-substrate/src/microcosm_core/macro_tools/"
                "agent_execution_trace.py::build_public_belief_state_process_reward_trace"
            ),
        },
        "body_in_receipt": False,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "reward_policy_id": reward_policy["policy_id"],
        "allowed_process_reward_sources": reward_policy[
            "allowed_process_reward_sources"
        ],
        "minimum_reliability_score": reward_policy["minimum_reliability_score"],
        "episode_count": episodes["episode_count"],
        "accepted_episode_count": episodes["accepted_episode_count"],
        "belief_state_count": belief_states["belief_state_count"],
        "accepted_belief_state_count": belief_states["accepted_belief_state_count"],
        "feedback_count": feedback["feedback_count"],
        "accepted_feedback_count": feedback["accepted_feedback_count"],
        "reward_event_count": rewards["reward_event_count"],
        "process_reward_count": rewards["process_reward_count"],
        "outcome_reward_count": rewards["outcome_reward_count"],
        "trajectory_group_count": trajectories["trajectory_group_count"],
        "accepted_trajectory_group_count": trajectories[
            "accepted_trajectory_group_count"
        ],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "episode_rows": episodes["episode_rows"],
        "belief_state_rows": belief_states["belief_state_rows"],
        "feedback_rows": feedback["feedback_rows"],
        "reward_rows": rewards["reward_rows"],
        "trajectory_group_rows": trajectories["trajectory_group_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "belief_state_process_reward_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "belief_state_process_reward_replay_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "typed_belief_summaries_not_hidden_reasoning",
                "count": result["accepted_belief_state_count"],
                "authority": "belief_state_json is a public summary with hidden reasoning explicitly absent",
            },
            {
                "mechanic_id": "verifier_backed_process_reward",
                "count": result["accepted_feedback_count"],
                "authority": "process reward is tied to deterministic verifier or observed feedback refs",
            },
            {
                "mechanic_id": "process_and_outcome_joint_replay",
                "count": result["reward_event_count"],
                "authority": "process and outcome rewards are replayed together before claim admission",
            },
            {
                "mechanic_id": "reward_hacking_traps_and_cold_replay",
                "count": result["cold_replay_pass_count"],
                "authority": "reward-hacking trap pass and cold replay receipts bound every trajectory group",
            },
        ],
        "episode_rows": result["episode_rows"],
        "belief_state_rows": result["belief_state_rows"],
        "feedback_rows": result["feedback_rows"],
        "reward_rows": result["reward_rows"],
        "trajectory_group_rows": result["trajectory_group_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "belief_state_process_reward_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "belief_state_process_reward_replay_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "episode_count": result["episode_count"],
        "belief_state_count": result["belief_state_count"],
        "accepted_feedback_count": result["accepted_feedback_count"],
        "process_reward_count": result["process_reward_count"],
        "outcome_reward_count": result["outcome_reward_count"],
        "trajectory_group_count": result["trajectory_group_count"],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "belief_state_process_reward_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "reward_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs.belief_state_process_reward_replay run"
    ),
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_reward_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "belief_state_process_reward_replay run-reward-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_belief_state_process_reward_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": (
            "exported_belief_state_process_reward_bundle_validation_result_v1"
        ),
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="belief_state_process_reward_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-reward-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-reward-bundle":
        result = run_reward_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
