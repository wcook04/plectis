from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


SOURCE_REF = "tools/meta/control/mission_transaction_preflight.py"
KERNEL_SOURCE_REF = "system/lib/mission_transaction_landing_preflight.py"
SOURCE_SYMBOL_REFS = [
    "tools/meta/control/mission_transaction_preflight.py::build_parser",
    "tools/meta/control/mission_transaction_preflight.py::main",
    "system/lib/mission_transaction_landing_preflight.py::_dirty_tree_classification",
    "system/lib/mission_transaction_landing_preflight.py::_shared_index_quarantine",
    "system/lib/mission_transaction_landing_preflight.py::_landing_decision",
    "system/lib/mission_transaction_landing_preflight.py::build_mission_transaction_landing_preflight",
]
TARGET_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/"
    "mission_transaction_preflight.py"
)
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.mission_transaction_preflight::build_public_mission_transaction_preflight",
    "microcosm_core.macro_tools.mission_transaction_preflight::classify_checkpoint_lane_cases",
    "microcosm_core.macro_tools.mission_transaction_preflight::main",
]

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "public_snapshot_preflight_not_live_git_or_ledger_authority",
    "live_git_mutation_authorized": False,
    "live_task_ledger_mutation_authorized": False,
    "live_work_ledger_mutation_authorized": False,
    "live_claim_release_authorized": False,
    "broad_stage_authorized": False,
    "broad_checkpoint_requires_operator_authorization": True,
    "suspected_secret_requires_hard_stop": True,
    "dirty_tree_blocks_scoped_commit": False,
}
ANTI_CLAIM = (
    "Public mission transaction preflight classifies declared Work Ledger, Git-parent, "
    "and checkpoint-lane metadata. It does not inspect the live Git index, mutate ledgers, "
    "release claims, authorize broad staging, or prove that work landed."
)
SOURCE_FAITHFUL_DECISION_RULES = [
    "same_path_claim_conflict_blocks_landing",
    "expected_parent_mismatch_blocks_landing",
    "missing_owned_path_blocks_landing",
    "dirty_tree_blocks_broad_accidental_staging_not_scoped_owned_path_commit",
    "operator_authorization_required_for_broad_checkpoint",
    "suspected_secret_or_private_leakage_requires_hard_stop",
    "public_snapshot_preflight_cannot_claim_landed_work",
]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _claim_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "claims")
    if rows:
        return rows
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _claim_is_active_or_public_projection(claim: dict[str, Any]) -> bool:
    status = str(claim.get("status") or "active")
    return status not in {"expired", "released", "closed", "superseded"}


def _path_conflicts(claims: list[dict[str, Any]]) -> dict[str, Any]:
    path_owner: dict[str, str] = {}
    conflict_claim_ids: list[str] = []
    same_path_conflicts: list[dict[str, Any]] = []
    missing_owned_path_claim_ids: list[str] = []

    for claim in claims:
        if not _claim_is_active_or_public_projection(claim):
            continue
        claim_id = str(claim.get("claim_id") or "claim")
        owned_paths = _strings(claim.get("owned_paths", []))
        if not owned_paths:
            missing_owned_path_claim_ids.append(claim_id)
        for owned_path in owned_paths:
            prior_claim_id = path_owner.get(owned_path)
            if prior_claim_id:
                conflict_claim_ids.extend([prior_claim_id, claim_id])
                same_path_conflicts.append(
                    {
                        "path": owned_path,
                        "prior_claim_id": prior_claim_id,
                        "conflicting_claim_id": claim_id,
                        "body_in_receipt": False,
                    }
                )
            else:
                path_owner[owned_path] = claim_id

    return {
        "claim_conflict_recheck_status": (
            "live_conflict_detected" if same_path_conflicts else "no_conflict_in_public_snapshot"
        ),
        "conflict_claim_ids": sorted(set(conflict_claim_ids)),
        "same_path_conflict_claim_ids": sorted(
            {row["prior_claim_id"] for row in same_path_conflicts}
        ),
        "same_path_conflicts": same_path_conflicts,
        "missing_owned_path_claim_ids": sorted(set(missing_owned_path_claim_ids)),
    }


def _expected_parent_mismatches(
    claims: list[dict[str, Any]],
    repo_state: object,
) -> dict[str, Any]:
    parent_by_claim: dict[str, Any] = {}
    if isinstance(repo_state, dict) and isinstance(repo_state.get("current_parent_by_claim"), dict):
        parent_by_claim = repo_state["current_parent_by_claim"]

    mismatches: list[dict[str, Any]] = []
    unchecked_claim_ids: list[str] = []
    for claim in claims:
        if not _claim_is_active_or_public_projection(claim):
            continue
        claim_id = str(claim.get("claim_id") or "claim")
        expected = str(claim.get("expected_parent_sha") or "")
        actual = str(parent_by_claim.get(claim_id) or "")
        if expected and actual and expected != actual:
            mismatches.append(
                {
                    "claim_id": claim_id,
                    "expected_parent_sha": expected,
                    "current_parent_sha": actual,
                    "body_in_receipt": False,
                }
            )
        elif expected and not actual:
            unchecked_claim_ids.append(claim_id)

    if mismatches:
        status = "stale_parent_rejected"
    elif unchecked_claim_ids:
        status = "parent_not_rechecked_public_snapshot"
    else:
        status = "parent_ok_or_not_declared"
    return {
        "expected_parent_status": status,
        "stale_expected_parent_claim_ids": sorted(row["claim_id"] for row in mismatches),
        "expected_parent_mismatches": mismatches,
        "parent_unchecked_claim_ids": sorted(unchecked_claim_ids),
    }


def _recommended_checkpoint_lane(case: dict[str, Any]) -> str:
    if case.get("suspected_secret") is True:
        return "hard_stop"
    if (
        case.get("operator_authorized_broad_checkpoint") is True
        and case.get("broad_checkpoint_requested") is True
    ):
        return "broad_checkpoint"
    return "scoped_commit"


def classify_checkpoint_lane_cases(
    checkpoint_lane_policy: object,
    extra_cases: list[object] | None = None,
) -> dict[str, Any]:
    cases = list(_rows(checkpoint_lane_policy, "lane_cases"))
    for item in extra_cases or []:
        if isinstance(item, dict):
            cases.append(item)

    decisions: list[dict[str, Any]] = []
    recommended_lane_by_case: dict[str, str] = {}
    missing_selected_lane_case_ids: list[str] = []
    broad_authorization_required_case_ids: list[str] = []
    secret_requires_hard_stop_case_ids: list[str] = []
    dirty_tree_not_scoped_blocker_case_ids: list[str] = []
    selected_lane_mismatch_case_ids: list[str] = []

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or f"checkpoint_lane_case_{index}")
        selected_lane = str(case.get("selected_lane") or "").strip()
        recommended_lane = _recommended_checkpoint_lane(case)
        recommended_lane_by_case[case_id] = recommended_lane

        if not selected_lane:
            missing_selected_lane_case_ids.append(case_id)
        if selected_lane and selected_lane != recommended_lane:
            selected_lane_mismatch_case_ids.append(case_id)
        if (
            selected_lane == "broad_checkpoint"
            and case.get("operator_authorized_broad_checkpoint") is not True
        ):
            broad_authorization_required_case_ids.append(case_id)
        if case.get("suspected_secret") is True and selected_lane != "hard_stop":
            secret_requires_hard_stop_case_ids.append(case_id)
        if (
            case.get("dirty_tree_present") is True
            and case.get("owned_paths_isolated") is True
            and case.get("suspected_secret") is not True
            and (
                selected_lane == "hard_stop"
                or case.get("dirty_tree_blocks_scoped_lane") is True
            )
        ):
            dirty_tree_not_scoped_blocker_case_ids.append(case_id)

        decisions.append(
            {
                "case_id": case_id,
                "selected_lane": selected_lane or "missing",
                "recommended_lane": recommended_lane,
                "dirty_tree_present": case.get("dirty_tree_present") is True,
                "owned_paths_isolated": case.get("owned_paths_isolated") is True,
                "operator_authorized_broad_checkpoint": (
                    case.get("operator_authorized_broad_checkpoint") is True
                ),
                "suspected_secret": case.get("suspected_secret") is True,
                "body_in_receipt": False,
            }
        )

    violation_case_ids = sorted(
        set(
            missing_selected_lane_case_ids
            + broad_authorization_required_case_ids
            + secret_requires_hard_stop_case_ids
            + dirty_tree_not_scoped_blocker_case_ids
            + selected_lane_mismatch_case_ids
        )
    )
    return {
        "status": "pass" if not violation_case_ids else "blocked",
        "checkpoint_lane_decisions": decisions,
        "recommended_lane_by_case": recommended_lane_by_case,
        "missing_selected_lane_case_ids": sorted(set(missing_selected_lane_case_ids)),
        "broad_checkpoint_authorization_required_case_ids": sorted(
            set(broad_authorization_required_case_ids)
        ),
        "secret_requires_hard_stop_case_ids": sorted(
            set(secret_requires_hard_stop_case_ids)
        ),
        "dirty_tree_not_scoped_blocker_case_ids": sorted(
            set(dirty_tree_not_scoped_blocker_case_ids)
        ),
        "selected_lane_mismatch_case_ids": sorted(set(selected_lane_mismatch_case_ids)),
        "checkpoint_lane_violation_case_ids": violation_case_ids,
        "selection_policy": (
            "dirty_trees_block_broad_accidental_staging_not_scoped_owned_path_commits"
        ),
        "broad_checkpoint_requires_operator_authorization": True,
        "suspected_secret_requires_hard_stop": True,
        "dirty_tree_blocks_scoped_commit": False,
        "body_in_receipt": False,
    }


def _landing_decision(
    *,
    path_result: dict[str, Any],
    parent_result: dict[str, Any],
    checkpoint_result: dict[str, Any],
    subject_ids: list[str],
    owned_paths: list[str],
) -> dict[str, Any]:
    blockers = []
    if path_result["conflict_claim_ids"]:
        blockers.append("same_path_claim_conflict")
    if path_result["missing_owned_path_claim_ids"]:
        blockers.append("missing_owned_path")
    if parent_result["stale_expected_parent_claim_ids"]:
        blockers.append("expected_parent_mismatch")
    if checkpoint_result["checkpoint_lane_violation_case_ids"]:
        blockers.append("checkpoint_lane_violation")

    if blockers:
        status = "blocked"
        recommended_lane = "replan_before_landing"
        reason = "preflight_blockers_require_replan"
    else:
        status = "pass"
        recommended_lane = "scoped_commit"
        reason = "public_snapshot_clear_for_scoped_owned_path_commit"

    return {
        "status": status,
        "decision": "blocked_replan_required" if blockers else "pass_metadata_preflight",
        "recommended_lane": recommended_lane,
        "reason": reason,
        "blockers": blockers,
        "subject_ids": subject_ids,
        "owned_paths": owned_paths,
        "claims_work_landed": False,
        "body_in_receipt": False,
    }


def build_public_mission_transaction_preflight(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    claims_payload: object,
    repo_state: object | None = None,
    checkpoint_lane_policy: object | None = None,
    checkpoint_negative_cases: list[object] | None = None,
    require_exclusive: bool = True,
) -> dict[str, Any]:
    claims = _claim_rows(claims_payload)
    path_result = _path_conflicts(claims) if require_exclusive else {
        "claim_conflict_recheck_status": "exclusive_check_not_requested",
        "conflict_claim_ids": [],
        "same_path_conflict_claim_ids": [],
        "same_path_conflicts": [],
        "missing_owned_path_claim_ids": [],
    }
    parent_result = _expected_parent_mismatches(claims, repo_state or {})
    checkpoint_result = classify_checkpoint_lane_cases(
        checkpoint_lane_policy or {},
        checkpoint_negative_cases,
    )
    landing_decision = _landing_decision(
        path_result=path_result,
        parent_result=parent_result,
        checkpoint_result=checkpoint_result,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
    )

    checkpoint_lane_status = checkpoint_result.get("status")
    return {
        "schema_version": "public_mission_transaction_preflight_v1",
        "source_ref": SOURCE_REF,
        "source_refs": [SOURCE_REF, KERNEL_SOURCE_REF],
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_ref": TARGET_REF,
        "target_symbols": TARGET_SYMBOL_REFS,
        "subject_ids": subject_ids,
        "owned_paths": owned_paths,
        "require_exclusive": require_exclusive,
        "source_faithful_decision_rules": SOURCE_FAITHFUL_DECISION_RULES,
        **path_result,
        **parent_result,
        **checkpoint_result,
        "checkpoint_lane_status": checkpoint_lane_status,
        "status": landing_decision["status"],
        "landing_decision": landing_decision,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _load_extra_case(path: str) -> dict[str, Any]:
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        raise ValueError(f"checkpoint negative case must be a JSON object: {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", required=True)
    parser.add_argument("--repo-state")
    parser.add_argument("--checkpoint-lane-policy", required=True)
    parser.add_argument("--checkpoint-negative-case", action="append", default=[])
    parser.add_argument("--subject-id", action="append", default=[])
    parser.add_argument("--owned-path", action="append", default=[])
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    result = build_public_mission_transaction_preflight(
        subject_ids=[str(item) for item in args.subject_id],
        owned_paths=[str(item) for item in args.owned_path],
        claims_payload=read_json_strict(args.claims),
        repo_state=read_json_strict(args.repo_state) if args.repo_state else {},
        checkpoint_lane_policy=read_json_strict(args.checkpoint_lane_policy),
        checkpoint_negative_cases=[
            _load_extra_case(path) for path in args.checkpoint_negative_case
        ],
        require_exclusive=True,
    )
    if args.out:
        write_json_atomic(Path(args.out), result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
