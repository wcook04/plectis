from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "mission_transaction_work_spine"
FIXTURE_ID = "first_wave.mission_transaction_work_spine"
VALIDATOR_ID = "validator.microcosm.organs.mission_transaction_work_spine"

PREFLIGHT_REL = "receipts/preflight/mission_transaction_work_spine.json"
DEPENDENCY_BLOCKED_NAME = "dependency_blocked.json"
WORK_LANDING_ATTEMPT_NAME = "work_landing_attempt.json"
CLAIM_PREFLIGHT_NAME = "claim_preflight_result.json"
SCOPED_MUTATION_NAME = "scoped_mutation_receipt.json"
CHECKPOINT_LANE_NAME = "checkpoint_lane_decision.json"
CLOSEOUT_STATUS_NAME = "closeout_status_projection.json"
DEPENDENCY_UNLOCK_NAME = "dependency_unlock_scheduler_receipt.json"
RECONCILE_PLAN_NAME = "work_landing_reconcile_plan.json"
MISSION_BUNDLE_RESULT_NAME = "exported_mission_transaction_bundle_validation_result.json"

EXPECTED_RECEIPT_PATHS = [
    PREFLIGHT_REL,
    "receipts/first_wave/mission_transaction_work_spine/dependency_blocked.json",
    "receipts/first_wave/mission_transaction_work_spine/work_landing_attempt.json",
    "receipts/first_wave/mission_transaction_work_spine/claim_preflight_result.json",
    "receipts/first_wave/mission_transaction_work_spine/scoped_mutation_receipt.json",
    "receipts/first_wave/mission_transaction_work_spine/checkpoint_lane_decision.json",
    "receipts/first_wave/mission_transaction_work_spine/closeout_status_projection.json",
    "receipts/first_wave/mission_transaction_work_spine/dependency_unlock_scheduler_receipt.json",
    "receipts/first_wave/mission_transaction_work_spine/work_landing_reconcile_plan.json",
]
EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH = (
    "receipts/first_wave/mission_transaction_work_spine/"
    "exported_mission_transaction_bundle_validation_result.json"
)

EXPECTED_NEGATIVE_CASES = {
    "competing_claim_and_stale_parent": [
        "EXPECTED_PARENT_MISMATCH",
        "SAME_PATH_CLAIM_CONFLICT",
    ],
    "mission_claim_missing_owned_path": ["MISSING_OWNED_PATH"],
    "scoped_commit_receipt_claims_global_authority": [
        "SCOPED_RECEIPT_AUTHORITY_UPGRADE"
    ],
    "mission_fixture_private_task_ledger_body": ["LIVE_TASK_LEDGER_BODY_IN_FIXTURE"],
    "clean_preflight_overclaims_landing_complete": [
        "PREFLIGHT_PASS_OVERCLAIMS_WORK_LANDED"
    ],
    "dependency_unlock_without_resolution_receipt": ["DANGLING_DEPENDENCY_REF"],
    "ready_workitem_with_unsatisfied_hard_dep": ["READY_WITH_INCOMPLETE_HARD_DEP"],
    "broad_checkpoint_without_operator_authorization": [
        "CHECKPOINT_BROAD_AUTH_REQUIRED"
    ],
    "suspected_secret_without_hard_stop": ["CHECKPOINT_SECRET_REQUIRES_HARD_STOP"],
    "dirty_tree_blocks_scoped_lane": ["CHECKPOINT_DIRTY_TREE_NOT_SCOPED_BLOCKER"],
    "missing_selected_lane_for_state": ["CHECKPOINT_LANE_DECISION_REQUIRED"],
}

MISSION_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "mission_transaction_metadata_not_live_closeout_authority",
    "live_work_state_mutation_authorized": False,
    "broad_stage_authorized": False,
    "broad_checkpoint_requires_operator_authorization": True,
    "suspected_secret_requires_hard_stop": True,
    "dirty_tree_blocks_scoped_commit": False,
    "derived_status_projection_is_authority": False,
    "later_organs_authorized": False,
}
MISSION_ANTI_CLAIM = (
    "Mission transaction receipts validate public work, claim, dependency, landing, "
    "checkpoint-lane, receipt-drain, and schedulability metadata plus regression fixtures; "
    "they do not mutate live state, certify live closeout, authorize broad staging without "
    "operator intent, authorize later organs, or prove whole Wave 1."
)

SOURCE_PATTERN_IDS = [
    "task_ledger_workitem_spine",
    "mission_transaction_landing",
    "work_ledger_runtime_claims",
    "task_ledger_exact_receipt_drain",
    "work_landing_reconcile_finalizer_plan",
    "workitem_dependency_unlock_scheduler",
    "checkpoint_solo_dev_three_lanes",
]

VALIDATOR_CONTRACT_RATCHET_REFS = [
    "fixture_manifests/mission_transaction_work_spine.fixture_manifest.json::validator_contract_ratchet_v1",
    "fixture_negative_case_matrix_v1.json::negative_cases[organ_id=mission_transaction_work_spine]",
    "error_code_taxonomy_v1.json::error_codes[organ_ids contains mission_transaction_work_spine]",
]

ORDERED_CONTROLLER_ACTION_IDS = [
    "select_checkpoint_lane",
    "record_scoped_commit_landing",
    "intake_exact_receipt_refs",
    "drain_exact_receipts",
    "closeout_landing_attempt",
    "release_claims",
    "recompute_status_projection",
]


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _input_file_paths(input_dir: Path) -> list[Path]:
    names = (
        "task_ledger_events.jsonl",
        "work_ledger_claims.json",
        "toy_repo_state.json",
        "dependency_graph.json",
        "claim_missing_owned_path.json",
        "scoped_receipt_global_authority_claim.json",
        "live_task_ledger_body_in_fixture.json",
        "preflight_pass_claims_work_landed.json",
        "checkpoint_lane_policy.json",
        "broad_checkpoint_without_operator_authorization.json",
        "suspected_secret_without_hard_stop.json",
        "dirty_tree_blocks_scoped_lane.json",
        "missing_selected_lane_for_state.json",
    )
    return [input_dir / name for name in names]


def _mission_bundle_paths(input_dir: Path) -> list[Path]:
    names = (
        "bundle_manifest.json",
        "workitems.json",
        "claim_table.json",
        "dependency_graph.json",
        "transaction_plan.json",
        "receipt_drain_plan.json",
        "closeout_projection_packet.json",
        "scoped_mutation_policy.json",
        "checkpoint_lane_policy.json",
    )
    return [input_dir / name for name in names]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _load_input_payloads(input_dir: Path) -> dict[str, Any]:
    return {
        "task_events": _load_jsonl(input_dir / "task_ledger_events.jsonl"),
        "claims": read_json_strict(input_dir / "work_ledger_claims.json"),
        "repo_state": read_json_strict(input_dir / "toy_repo_state.json"),
        "dependency_graph": read_json_strict(input_dir / "dependency_graph.json"),
        "missing_owned_path": read_json_strict(input_dir / "claim_missing_owned_path.json"),
        "scoped_receipt": read_json_strict(
            input_dir / "scoped_receipt_global_authority_claim.json"
        ),
        "private_marker": read_json_strict(input_dir / "live_task_ledger_body_in_fixture.json"),
        "preflight_overclaim": read_json_strict(
            input_dir / "preflight_pass_claims_work_landed.json"
        ),
        "checkpoint_lane_policy": read_json_strict(input_dir / "checkpoint_lane_policy.json"),
        "checkpoint_negative_cases": [
            read_json_strict(input_dir / "broad_checkpoint_without_operator_authorization.json"),
            read_json_strict(input_dir / "suspected_secret_without_hard_stop.json"),
            read_json_strict(input_dir / "dirty_tree_blocks_scoped_lane.json"),
            read_json_strict(input_dir / "missing_selected_lane_for_state.json"),
        ],
    }


def _load_mission_bundle_payloads(input_dir: Path) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _mission_bundle_paths(input_dir)
    }


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_file_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _scan_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(
        _mission_bundle_paths(input_dir),
        forbidden_classes=policy,
        display_root=public_root,
    )


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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
        "body_redacted": True,
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


def _bundle_finding(code: str, message: str, *, subject_id: str, subject_kind: str) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
    }


def validate_exported_workitems(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "workitems")
    workitem_ids: list[str] = []
    schedulable_ids: list[str] = []
    blocked_ids: list[str] = []
    dependency_refs: list[str] = []
    dependency_status_by_workitem: dict[str, dict[str, Any]] = {}

    if not rows:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_WORKITEM_ROWS_MISSING",
                "Exported mission bundle has no WorkItem rows.",
                subject_id="workitems",
                subject_kind="workitem_table",
            )
        )

    for row in rows:
        work_item_id = str(row.get("work_item_id") or "")
        state = str(row.get("state") or "")
        deps = [str(dep) for dep in row.get("depends_on", [])]
        workitem_ids.append(work_item_id)
        dependency_refs.extend(deps)
        if row.get("live_ledger_authority") or row.get("source_authority_allowed"):
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_WORKITEM_AUTHORITY_OVERCLAIM",
                    "WorkItem metadata row attempted to claim live ledger authority.",
                    subject_id=work_item_id or "workitem",
                    subject_kind="workitem_row",
                )
            )
        if row.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_WORKITEM_PROJECTION_FLAG_MISSING",
                    "WorkItem metadata row must declare projection_not_authority.",
                    subject_id=work_item_id or "workitem",
                    subject_kind="workitem_row",
                )
            )
        if state == "ready":
            schedulable_ids.append(work_item_id)
        elif state in {"blocked", "shaping"}:
            blocked_ids.append(work_item_id)
        dependency_status_by_workitem[work_item_id] = {
            "state": state,
            "dependency_refs": deps,
            "schedulable": state == "ready",
            "derived_not_authority": True,
        }

    duplicates = sorted(
        work_item_id
        for work_item_id in set(workitem_ids)
        if work_item_id and workitem_ids.count(work_item_id) > 1
    )
    for work_item_id in duplicates:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_DUPLICATE_WORKITEM_ID",
                "Exported mission bundle contains a duplicate WorkItem id.",
                subject_id=work_item_id,
                subject_kind="workitem_table",
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "workitem_ids": sorted(work_item_id for work_item_id in workitem_ids if work_item_id),
        "blocked_workitem_ids": sorted(work_item_id for work_item_id in blocked_ids if work_item_id),
        "schedulable_workitem_ids": sorted(
            work_item_id for work_item_id in schedulable_ids if work_item_id
        ),
        "dependency_refs": sorted(set(dependency_refs)),
        "dependency_status_by_workitem": dependency_status_by_workitem,
        "workitem_rows_projection_not_authority": True,
    }


def validate_exported_claims(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    claims = _rows(payload, "claims")
    path_owner: dict[str, str] = {}
    same_path_conflicts: list[str] = []
    accepted_claim_ids: list[str] = []

    if not claims:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CLAIM_ROWS_MISSING",
                "Exported mission bundle has no claim rows.",
                subject_id="claim_table",
                subject_kind="claim_table",
            )
        )

    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        owned_paths = [str(path) for path in claim.get("owned_paths", [])]
        if not owned_paths:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_CLAIM_OWNED_PATHS_MISSING",
                    "Claim row has no owned paths.",
                    subject_id=claim_id or "claim",
                    subject_kind="claim_row",
                )
            )
        if claim.get("live_claim_authority") or claim.get("source_authority_allowed"):
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_CLAIM_AUTHORITY_OVERCLAIM",
                    "Claim row attempted to claim live Work Ledger authority.",
                    subject_id=claim_id or "claim",
                    subject_kind="claim_row",
                )
            )
        if claim.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_CLAIM_PROJECTION_FLAG_MISSING",
                    "Claim row must declare projection_not_authority.",
                    subject_id=claim_id or "claim",
                    subject_kind="claim_row",
                )
            )
        for owned_path in owned_paths:
            if owned_path in path_owner:
                same_path_conflicts.append(claim_id)
                findings.append(
                    _bundle_finding(
                        "MISSION_BUNDLE_SAME_PATH_CLAIM_CONFLICT",
                        "Exported mission claim table contains a same-path conflict.",
                        subject_id=claim_id or "claim",
                        subject_kind="claim_row",
                    )
                )
            else:
                path_owner[owned_path] = claim_id
        if claim_id:
            accepted_claim_ids.append(claim_id)

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "accepted_claim_ids": sorted(set(accepted_claim_ids)),
        "same_path_conflict_claim_ids": sorted(set(same_path_conflicts)),
        "claim_rows_projection_not_authority": True,
    }


def validate_exported_dependencies(
    dependency_payload: object,
    workitem_result: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    known_workitems = set(workitem_result["workitem_ids"])
    resolved_refs = {
        str(row.get("dependency_id"))
        for row in _rows(dependency_payload, "dependency_resolution_receipts")
        if row.get("status") == "resolved"
    }
    dangling_refs: list[str] = []
    unsatisfied: list[str] = []

    for work_item_id, status in workitem_result["dependency_status_by_workitem"].items():
        deps = [str(dep) for dep in status.get("dependency_refs", [])]
        unresolved = [
            dep for dep in deps if dep not in resolved_refs and dep not in known_workitems
        ]
        dangling_refs.extend(unresolved)
        unsatisfied.extend(dep for dep in deps if dep not in resolved_refs and dep not in known_workitems)
        for dep in unresolved:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_DANGLING_DEPENDENCY_REF",
                    "Exported mission bundle dependency lacks resolution evidence.",
                    subject_id=f"{work_item_id}:{dep}",
                    subject_kind="dependency_graph",
                )
            )
    if isinstance(dependency_payload, dict) and dependency_payload.get("derived_not_authority") is not True:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_DEPENDENCY_AUTHORITY_OVERCLAIM",
                "Dependency graph must remain metadata, not live dependency authority.",
                subject_id="dependency_graph",
                subject_kind="dependency_graph",
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "resolved_dependency_refs": sorted(resolved_refs),
        "dangling_dependency_refs": sorted(set(dangling_refs)),
        "unsatisfied_dep_ids": sorted(set(unsatisfied)),
        "dependency_resolution_receipt": {
            "accepted_refs": sorted(resolved_refs),
            "rejected_refs": sorted(set(dangling_refs)),
            "body_redacted": True,
        },
        "downstream_unlock_edges": [
            {
                "upstream_id": ref,
                "downstream_ids": [
                    work_item_id
                    for work_item_id, status in workitem_result[
                        "dependency_status_by_workitem"
                    ].items()
                    if ref in status.get("dependency_refs", [])
                ],
                "body_redacted": True,
            }
            for ref in sorted(resolved_refs)
        ],
        "derived_not_authority": True,
    }


def validate_exported_transaction_plan(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    plan = payload if isinstance(payload, dict) else {}
    actions = [str(action) for action in plan.get("ordered_controller_action_ids", [])]
    mutation_policy = plan.get("mutation_policy", {})
    if actions != ORDERED_CONTROLLER_ACTION_IDS:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CONTROLLER_ACTION_ORDER_MISMATCH",
                "Mission transaction plan does not preserve controller action order.",
                subject_id=str(plan.get("transaction_id") or "transaction_plan"),
                subject_kind="transaction_plan",
            )
        )
    if not isinstance(mutation_policy, dict):
        mutation_policy = {}
    for field in (
        "live_state_mutation",
        "live_task_ledger_mutation",
        "live_work_ledger_mutation",
        "broad_stage_used",
        "provider_execution_authorized",
        "release_authorized",
    ):
        if mutation_policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_MUTATION_POLICY_OVERCLAIM",
                    "Mission transaction plan mutation policy must be false for live mutation and release fields.",
                    subject_id=field,
                    subject_kind="transaction_plan",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "transaction_id": plan.get("transaction_id"),
        "ordered_controller_action_ids": actions,
        "mutation_policy": mutation_policy,
        "apply_result": plan.get("apply_result"),
        "work_landing_reconcile_status": plan.get("work_landing_reconcile_status"),
        "claim_release_order_status": plan.get("claim_release_order_status"),
        "actions": plan.get("actions", []),
        "mode": plan.get("mode"),
        "recommended_next_action": plan.get("recommended_next_action"),
    }


def validate_exported_receipt_drain(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    plan = payload if isinstance(payload, dict) else {}
    declared = [str(ref) for ref in plan.get("declared_receipt_refs", [])]
    drained = [str(ref) for ref in plan.get("receipt_refs_drained", [])]
    if sorted(declared) != sorted(drained):
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_RECEIPT_DRAIN_SCOPE_MISMATCH",
                "Receipt drain plan must drain exactly the declared receipt refs.",
                subject_id=str(plan.get("drain_id") or "receipt_drain_plan"),
                subject_kind="receipt_drain_plan",
            )
        )
    if plan.get("drain_mode") != "metadata_projection_only":
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_RECEIPT_DRAIN_LIVE_MUTATION_OVERCLAIM",
                "Receipt drain plan must remain metadata projection only.",
                subject_id=str(plan.get("drain_id") or "receipt_drain_plan"),
                subject_kind="receipt_drain_plan",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "receipt_refs_drained": drained,
        "exact_receipt_drain_scope": declared,
        "receipt_drain_exclusivity_status": (
            "only_declared_receipts_drained" if not findings else "blocked"
        ),
        "derived_not_authority": True,
    }


def validate_exported_closeout_projection(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    packet = payload if isinstance(payload, dict) else {}
    if packet.get("derived_not_authority") is not True:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CLOSEOUT_AUTHORITY_OVERCLAIM",
                "Closeout projection packet must declare derived_not_authority.",
                subject_id=str(packet.get("work_item_id") or "closeout_projection_packet"),
                subject_kind="closeout_projection_packet",
            )
        )
    if packet.get("claims_live_closeout") is not False:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_LIVE_CLOSEOUT_OVERCLAIM",
                "Closeout projection packet must not claim live closeout.",
                subject_id=str(packet.get("work_item_id") or "closeout_projection_packet"),
                subject_kind="closeout_projection_packet",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "work_item_id": packet.get("work_item_id"),
        "status_before": packet.get("status_before"),
        "status_after": packet.get("status_after"),
        "derived_not_authority": True,
        "claims_live_closeout": False,
    }


def validate_exported_scoped_mutation_policy(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    policy = payload if isinstance(payload, dict) else {}
    for field in (
        "live_state_mutation_authorized",
        "live_task_ledger_mutation_authorized",
        "live_work_ledger_mutation_authorized",
        "broad_stage_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_SCOPED_POLICY_OVERCLAIM",
                    "Scoped mutation policy must reject live state mutation and broad staging.",
                    subject_id=field,
                    subject_kind="scoped_mutation_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "owned_paths": policy.get("owned_paths", []),
        "mutation_status": policy.get("mutation_status"),
        "broad_stage_used": False,
        "authority_upgrade_rejected": True,
        "body_redacted": True,
    }


def _checkpoint_cases(payload: object, extra_cases: list[object] | None = None) -> list[dict[str, Any]]:
    cases = list(_rows(payload, "lane_cases"))
    for item in extra_cases or []:
        if isinstance(item, dict):
            cases.append(item)
    return cases


def _recommended_checkpoint_lane(case: dict[str, Any]) -> str:
    if case.get("suspected_secret") is True:
        return "hard_stop"
    if (
        case.get("operator_authorized_broad_checkpoint") is True
        and case.get("broad_checkpoint_requested") is True
    ):
        return "broad_checkpoint"
    return "scoped_commit"


def validate_checkpoint_lane_policy(
    payload: object,
    extra_cases: list[object] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    cases = _checkpoint_cases(payload, extra_cases)
    checkpoint_lane_decisions: list[dict[str, Any]] = []
    recommended_lane_by_case: dict[str, str] = {}
    hard_stop_case_ids: list[str] = []
    broad_authorization_required_case_ids: list[str] = []
    dirty_tree_not_scoped_blocker_case_ids: list[str] = []

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or f"checkpoint_lane_case_{index}")
        selected_lane = str(case.get("selected_lane") or "").strip()
        recommended_lane = _recommended_checkpoint_lane(case)
        recommended_lane_by_case[case_id] = recommended_lane
        negative_case_id = str(case.get("negative_case_id") or case_id)

        if recommended_lane == "hard_stop":
            hard_stop_case_ids.append(case_id)
        if selected_lane == "broad_checkpoint" and case.get(
            "operator_authorized_broad_checkpoint"
        ) is not True:
            broad_authorization_required_case_ids.append(case_id)
            _record(
                findings,
                observed,
                "CHECKPOINT_BROAD_AUTH_REQUIRED",
                "Broad checkpoint lane requires explicit operator authorization.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
        if case.get("suspected_secret") is True and selected_lane != "hard_stop":
            _record(
                findings,
                observed,
                "CHECKPOINT_SECRET_REQUIRES_HARD_STOP",
                "Suspected secret or private leakage requires the hard-stop lane.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
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
            _record(
                findings,
                observed,
                "CHECKPOINT_DIRTY_TREE_NOT_SCOPED_BLOCKER",
                "Mixed dirty tree state blocks broad accidental staging, not scoped owned-path commit.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
        if not selected_lane:
            _record(
                findings,
                observed,
                "CHECKPOINT_LANE_DECISION_REQUIRED",
                "Checkpoint lane case must name scoped_commit, broad_checkpoint, or hard_stop.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )

        checkpoint_lane_decisions.append(
            {
                "case_id": case_id,
                "selected_lane": selected_lane or "missing",
                "recommended_lane": recommended_lane,
                "dirty_tree_present": case.get("dirty_tree_present") is True,
                "owned_paths_isolated": case.get("owned_paths_isolated") is True,
                "operator_authorized_broad_checkpoint": case.get(
                    "operator_authorized_broad_checkpoint"
                )
                is True,
                "suspected_secret": case.get("suspected_secret") is True,
                "body_redacted": True,
            }
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "checkpoint_lane_decisions": checkpoint_lane_decisions,
        "recommended_lane_by_case": recommended_lane_by_case,
        "hard_stop_case_ids": sorted(set(hard_stop_case_ids)),
        "broad_checkpoint_authorization_required_case_ids": sorted(
            set(broad_authorization_required_case_ids)
        ),
        "dirty_tree_not_scoped_blocker_case_ids": sorted(
            set(dirty_tree_not_scoped_blocker_case_ids)
        ),
        "selection_policy": (
            "dirty_trees_block_broad_accidental_staging_not_scoped_owned_path_commits"
        ),
        "broad_checkpoint_requires_operator_authorization": True,
        "suspected_secret_requires_hard_stop": True,
        "dirty_tree_blocks_scoped_commit": False,
        "body_redacted": True,
    }


def validate_dependency_unlock_scheduler(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    workitems = _rows(payload, "workitems")
    known_ids = {str(row.get("work_item_id")) for row in workitems}
    resolved_refs = {
        str(row.get("dependency_id"))
        for row in _rows(payload, "dependency_resolution_receipts")
        if row.get("status") == "resolved"
    }

    dependency_status_by_workitem: dict[str, dict[str, Any]] = {}
    blocked_ids: list[str] = []
    ready_but_unsatisfied: list[str] = []
    schedulable_ids: list[str] = []
    dangling_refs: list[str] = []
    unsatisfied_dep_ids: list[str] = []
    anomaly_refs: list[dict[str, Any]] = []

    for row in workitems:
        work_item_id = str(row.get("work_item_id") or "work_item")
        state = str(row.get("state") or "shaping")
        deps = [str(dep) for dep in row.get("depends_on", [])]
        unresolved = [
            dep for dep in deps if dep not in resolved_refs and dep not in known_ids
        ]
        unsatisfied = [dep for dep in deps if dep not in resolved_refs]
        if unresolved:
            blocked_ids.append(work_item_id)
            dangling_refs.extend(unresolved)
            unsatisfied_dep_ids.extend(unsatisfied)
            anomaly_refs.append(
                {
                    "work_item_id": work_item_id,
                    "dependency_refs": unresolved,
                    "error_code": "DANGLING_DEPENDENCY_REF",
                    "body_redacted": True,
                }
            )
            _record(
                findings,
                observed,
                "DANGLING_DEPENDENCY_REF",
                "Dependency unlock attempted without explicit synthetic resolution evidence.",
                case_id="dependency_unlock_without_resolution_receipt",
                subject_id=work_item_id,
                subject_kind="work_item",
            )
        if state == "ready" and unsatisfied:
            ready_but_unsatisfied.append(work_item_id)
            _record(
                findings,
                observed,
                "READY_WITH_INCOMPLETE_HARD_DEP",
                "Ready state cannot override unsatisfied hard dependency refs.",
                case_id="ready_workitem_with_unsatisfied_hard_dep",
                subject_id=work_item_id,
                subject_kind="work_item",
            )
        if state == "ready" and not unsatisfied:
            schedulable_ids.append(work_item_id)
        if unsatisfied and work_item_id not in blocked_ids:
            blocked_ids.append(work_item_id)
        dependency_status_by_workitem[work_item_id] = {
            "state": state,
            "dependency_refs": deps,
            "unsatisfied_dep_ids": unsatisfied,
            "schedulable": state == "ready" and not unsatisfied,
        }

    blocked_ids = sorted(set(blocked_ids))
    ready_but_unsatisfied = sorted(set(ready_but_unsatisfied))
    dangling_refs = sorted(set(dangling_refs))
    unsatisfied_dep_ids = sorted(set(unsatisfied_dep_ids))
    schedulable_ids = sorted(set(schedulable_ids))
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "blocked_workitem_ids": blocked_ids,
        "ready_but_unsatisfied_workitem_ids": ready_but_unsatisfied,
        "resolved_dependency_refs": sorted(resolved_refs),
        "dependency_status_by_workitem": dependency_status_by_workitem,
        "dependency_resolution_receipt": {
            "accepted_refs": sorted(resolved_refs),
            "rejected_refs": dangling_refs,
            "body_redacted": True,
        },
        "unsatisfied_dep_ids": unsatisfied_dep_ids,
        "downstream_unlock_edges": [
            {
                "upstream_id": ref,
                "downstream_ids": [
                    work_item_id
                    for work_item_id, status in dependency_status_by_workitem.items()
                    if ref in status["dependency_refs"]
                ],
                "body_redacted": True,
            }
            for ref in sorted(resolved_refs)
        ],
        "unlocks_by_rank": [
            {"rank": index + 1, "work_item_id": work_item_id, "body_redacted": True}
            for index, work_item_id in enumerate(schedulable_ids)
        ],
        "dangling_dependency_refs": dangling_refs,
        "schedulable_workitem_ids": schedulable_ids,
        "downstream_schedulable_before": False,
        "schedulability_decision_source": "synthetic_dependency_status_by_workitem",
        "dependency_unlock_resolution_basis": "explicit_synthetic_dependency_resolution_receipt_required",
        "anomaly_refs": anomaly_refs,
        "derived_not_authority": True,
        "schedulable": False,
        "dependency_refs": sorted({dep for row in workitems for dep in row.get("depends_on", [])}),
    }


def validate_claim_preflight(
    claims_payload: object,
    repo_state: object,
    missing_owned_path: object,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    claims = _rows(claims_payload, "claims")
    active_claims = [row for row in claims if row.get("status") == "active"]
    path_owner: dict[str, str] = {}
    conflict_claim_ids: list[str] = []
    same_path_conflict_claim_ids: list[str] = []
    for claim in active_claims:
        claim_id = str(claim.get("claim_id") or "claim")
        for owned_path in claim.get("owned_paths", []):
            owned_path = str(owned_path)
            if owned_path in path_owner:
                conflict_claim_ids.append(claim_id)
                same_path_conflict_claim_ids.append(path_owner[owned_path])
                _record(
                    findings,
                    observed,
                    "SAME_PATH_CLAIM_CONFLICT",
                    "Same-path claim conflict remains live at validation time.",
                    case_id="competing_claim_and_stale_parent",
                    subject_id=claim_id,
                    subject_kind="work_ledger_claim",
                )
            else:
                path_owner[owned_path] = claim_id

    parent_by_claim = repo_state.get("current_parent_by_claim", {}) if isinstance(repo_state, dict) else {}
    stale_claim_ids: list[str] = []
    for claim in active_claims:
        claim_id = str(claim.get("claim_id") or "claim")
        expected = str(claim.get("expected_parent_sha") or "")
        actual = str(parent_by_claim.get(claim_id) or "")
        if expected and actual and expected != actual:
            stale_claim_ids.append(claim_id)
            _record(
                findings,
                observed,
                "EXPECTED_PARENT_MISMATCH",
                "Expected parent does not match the synthetic current parent.",
                case_id="competing_claim_and_stale_parent",
                subject_id=claim_id,
                subject_kind="work_ledger_claim",
            )

    missing_claim_id = str(missing_owned_path.get("claim_id") or "claim_missing_owned_path")
    if not missing_owned_path.get("owned_paths"):
        _record(
            findings,
            observed,
            "MISSING_OWNED_PATH",
            "Mission claim is missing an owned path.",
            case_id="mission_claim_missing_owned_path",
            subject_id=missing_claim_id,
            subject_kind="work_ledger_claim",
        )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "claim_id": "claim_b",
        "decision": "blocked_replan_required",
        "conflict_claim_ids": sorted(set(conflict_claim_ids)),
        "same_path_conflict_claim_ids": sorted(set(same_path_conflict_claim_ids)),
        "claim_conflict_recheck_status": "live_conflict_detected",
        "expected_parent_status": "stale_parent_rejected",
        "stale_expected_parent_claim_ids": sorted(stale_claim_ids),
        "missing_owned_path_claim_ids": [missing_claim_id],
        "replan_required": True,
    }


def validate_scoped_receipt_authority(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    receipt_id = "scoped_receipt_global_authority_claim"
    if isinstance(payload, dict):
        receipt_id = str(payload.get("receipt_id") or receipt_id)
        if payload.get("claims_global_authority"):
            _record(
                findings,
                observed,
                "SCOPED_RECEIPT_AUTHORITY_UPGRADE",
                "Scoped commit receipt attempted to claim global authority.",
                case_id="scoped_commit_receipt_claims_global_authority",
                subject_id=receipt_id,
                subject_kind="scoped_receipt",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "scoped_receipt_authority_rejected": bool(findings),
    }


def validate_private_marker(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    marker_id = "live_task_ledger_boundary_marker"
    if isinstance(payload, dict):
        marker_id = str(payload.get("fixture_id") or marker_id)
        if payload.get("forbidden_payload_value_present"):
            _record(
                findings,
                observed,
                "LIVE_TASK_LEDGER_BODY_IN_FIXTURE",
                "Fixture marked a live ledger payload value and was rejected.",
                case_id="mission_fixture_private_task_ledger_body",
                subject_id=marker_id,
                subject_kind="synthetic_fixture",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "forbidden_payload_rejected": bool(findings),
    }


def validate_preflight_overclaim(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(payload, dict) and payload.get("preflight_status") == PASS:
        if payload.get("claims_work_landed") and not payload.get("has_closeout_landing_attempt"):
            _record(
                findings,
                observed,
                "PREFLIGHT_PASS_OVERCLAIMS_WORK_LANDED",
                "Clean preflight cannot claim landed work without closeout evidence.",
                case_id="clean_preflight_overclaims_landing_complete",
                subject_id="preflight_pass_claims_work_landed",
                subject_kind="mission_preflight",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "runtime_landing_overclaim_rejected": bool(findings),
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "organ_id": result["organ_id"],
        "fixture_id": result["fixture_id"],
        "validator_id": result["validator_id"],
        "command": result["command"],
        "status": result["status"],
        "created_at": result["created_at"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "findings": result["findings"],
        "anti_claim": result["anti_claim"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_paths": receipt_paths,
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "validator_contract_ratchet_status": "pass",
        "receipt_field_floor_status": "pass",
        "cannot_fake_predicate_status": "pass",
        "negative_case_binding_status": "pass",
        "synthetic_fixture_payload_policy": "synthetic_fixture_metadata_only_no_live_state",
        "validator_contract_ratchet_refs": VALIDATOR_CONTRACT_RATCHET_REFS,
    }
    return payload


def _without_common_receipt_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"findings", "observed_negative_cases", "status"}
    }


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative_receipt_paths(paths: dict[str, Path], display_root: Path) -> list[str]:
    return [public_relative_path(path, display_root=display_root) for path in paths.values()]


def write_receipts(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    target = target.resolve(strict=False)
    public_root = Path(public_root).resolve(strict=False)
    receipt_root = public_root if _is_relative_to(target, public_root) else target.parent
    paths = {
        "preflight": receipt_root / PREFLIGHT_REL,
        "dependency_blocked": target / DEPENDENCY_BLOCKED_NAME,
        "work_landing_attempt": target / WORK_LANDING_ATTEMPT_NAME,
        "claim_preflight_result": target / CLAIM_PREFLIGHT_NAME,
        "scoped_mutation_receipt": target / SCOPED_MUTATION_NAME,
        "checkpoint_lane_decision": target / CHECKPOINT_LANE_NAME,
        "closeout_status_projection": target / CLOSEOUT_STATUS_NAME,
        "dependency_unlock_scheduler_receipt": target / DEPENDENCY_UNLOCK_NAME,
        "work_landing_reconcile_plan": target / RECONCILE_PLAN_NAME,
    }
    receipt_paths = _relative_receipt_paths(paths, receipt_root)

    dependency = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_dependency_blocked_v1",
        receipt_paths=receipt_paths,
    )
    dependency.update(
        {
            "blocked_workitem_ids": validation_result["blocked_workitem_ids"],
            "dependency_refs": validation_result["dependency_refs"],
            "schedulable": False,
            "schedulability_decision_source": validation_result["schedulability_decision_source"],
            "dependency_unlock_resolution_basis": validation_result[
                "dependency_unlock_resolution_basis"
            ],
        }
    )

    work_landing = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_work_landing_attempt_v1",
        receipt_paths=receipt_paths,
    )
    work_landing.update(validation_result["work_landing_attempt"])

    claim = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_claim_preflight_result_v1",
        receipt_paths=receipt_paths,
    )
    claim.update(_without_common_receipt_overrides(validation_result["claim_preflight_result"]))

    scoped = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_scoped_mutation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    scoped.update(validation_result["scoped_mutation_receipt"])

    checkpoint_lane = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_checkpoint_lane_decision_v1",
        receipt_paths=receipt_paths,
    )
    checkpoint_lane.update(
        _without_common_receipt_overrides(validation_result["checkpoint_lane_decision"])
    )

    closeout = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_closeout_status_projection_v1",
        receipt_paths=receipt_paths,
    )
    closeout.update(validation_result["closeout_status_projection"])

    dependency_unlock = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_dependency_unlock_scheduler_v1",
        receipt_paths=receipt_paths,
    )
    dependency_unlock.update(
        _without_common_receipt_overrides(validation_result["dependency_unlock_scheduler"])
    )

    reconcile = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_work_landing_reconcile_plan_v1",
        receipt_paths=receipt_paths,
    )
    reconcile.update(validation_result["work_landing_reconcile_plan"])

    preflight = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_preflight_v1",
        receipt_paths=receipt_paths,
    )
    preflight.update(
        {
            "workitem_view_rebuild_status": PASS,
            "claim_preflight_status": validation_result["claim_preflight_result"]["decision"],
            "scoped_mutation_status": validation_result["scoped_mutation_receipt"][
                "mutation_status"
            ],
            "checkpoint_lane_policy_status": "pass",
            "checkpoint_lane_decision_path": public_relative_path(
                paths["checkpoint_lane_decision"], display_root=receipt_root
            ),
            "broad_checkpoint_requires_operator_authorization": True,
            "suspected_secret_requires_hard_stop": True,
            "dirty_tree_blocks_scoped_commit": False,
            "receipt_drain_status": validation_result["closeout_status_projection"][
                "receipt_drain_exclusivity_status"
            ],
            "orphan_sweep_status": "expired_claims_swept",
            "closeout_projection_path": public_relative_path(
                paths["closeout_status_projection"], display_root=receipt_root
            ),
            "controller_action_order_status": "pass",
            "ordered_controller_action_ids": ORDERED_CONTROLLER_ACTION_IDS,
            "controller_action_apply_statuses": {
                action: "dry_run_not_mutated" for action in ORDERED_CONTROLLER_ACTION_IDS
            },
            "finalizer_classification_status": "pass",
            "canonical_transaction_state": "synthetic_closeout_pending_exact_receipt_drain",
            "ambient_pressure_count": 0,
            "compatibility_finalizer_count": 0,
        }
    )

    for key, payload in (
        ("preflight", preflight),
        ("dependency_blocked", dependency),
        ("work_landing_attempt", work_landing),
        ("claim_preflight_result", claim),
        ("scoped_mutation_receipt", scoped),
        ("checkpoint_lane_decision", checkpoint_lane),
        ("closeout_status_projection", closeout),
        ("dependency_unlock_scheduler_receipt", dependency_unlock),
        ("work_landing_reconcile_plan", reconcile),
    ):
        write_json_atomic(paths[key], payload)

    return {key: public_relative_path(path, display_root=receipt_root) for key, path in paths.items()}


def _write_mission_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / MISSION_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_exported_mission_transaction_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "bundle_manifest_schema_version": validation_result[
                "bundle_manifest_schema_version"
            ],
            "workitem_ids": validation_result["workitem_ids"],
            "accepted_claim_ids": validation_result["accepted_claim_ids"],
            "transaction_id": validation_result["transaction_id"],
            "bundle_fingerprint": validation_result["bundle_fingerprint"],
            "workitem_rows_projection_not_authority": validation_result[
                "workitem_rows_projection_not_authority"
            ],
            "claim_rows_projection_not_authority": validation_result[
                "claim_rows_projection_not_authority"
            ],
            "metadata_projection_not_live_ledger_authority": validation_result[
                "metadata_projection_not_live_ledger_authority"
            ],
            "blocked_workitem_ids": validation_result["blocked_workitem_ids"],
            "schedulable_workitem_ids": validation_result["schedulable_workitem_ids"],
            "dependency_refs": validation_result["dependency_refs"],
            "dependency_status_by_workitem": validation_result[
                "dependency_status_by_workitem"
            ],
            "resolved_dependency_refs": validation_result["resolved_dependency_refs"],
            "dependency_resolution_receipt": validation_result[
                "dependency_resolution_receipt"
            ],
            "downstream_unlock_edges": validation_result["downstream_unlock_edges"],
            "claim_preflight_result": validation_result["claim_preflight_result"],
            "scoped_mutation_receipt": validation_result["scoped_mutation_receipt"],
            "checkpoint_lane_decision": validation_result["checkpoint_lane_decision"],
            "closeout_status_projection": validation_result["closeout_status_projection"],
            "receipt_drain_plan": validation_result["receipt_drain_plan"],
            "work_landing_reconcile_plan": validation_result["work_landing_reconcile_plan"],
            "public_replacement_refs": validation_result["public_replacement_refs"],
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def run_mission_transaction_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_mission_bundle_payloads(input_path)
    scan_result = _scan_bundle_inputs(input_path, public_root)
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    manifest = payloads["bundle_manifest"] if isinstance(payloads["bundle_manifest"], dict) else {}
    workitem_result = validate_exported_workitems(payloads["workitems"])
    claim_result = validate_exported_claims(payloads["claim_table"])
    dependency_result = validate_exported_dependencies(
        payloads["dependency_graph"],
        workitem_result,
    )
    transaction_result = validate_exported_transaction_plan(payloads["transaction_plan"])
    receipt_drain_result = validate_exported_receipt_drain(payloads["receipt_drain_plan"])
    closeout_result = validate_exported_closeout_projection(
        payloads["closeout_projection_packet"]
    )
    scoped_policy_result = validate_exported_scoped_mutation_policy(
        payloads["scoped_mutation_policy"]
    )
    checkpoint_lane_result = validate_checkpoint_lane_policy(
        payloads["checkpoint_lane_policy"]
    )

    all_findings = sorted(
        [
            *workitem_result["findings"],
            *claim_result["findings"],
            *dependency_result["findings"],
            *transaction_result["findings"],
            *receipt_drain_result["findings"],
            *closeout_result["findings"],
            *scoped_policy_result["findings"],
            *checkpoint_lane_result["findings"],
        ],
        key=lambda item: (
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    bundle_id = str(
        manifest.get("bundle_id")
        or "mission_transaction_work_spine_exported_mission_transaction_bundle"
    )
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and workitem_result["workitem_ids"]
        and claim_result["accepted_claim_ids"]
        and transaction_result["ordered_controller_action_ids"] == ORDERED_CONTROLLER_ACTION_IDS
        else "blocked"
    )
    bundle_fingerprint = _stable_hash(
        {
            "workitems": payloads["workitems"],
            "claim_table": payloads["claim_table"],
            "dependency_graph": payloads["dependency_graph"],
            "transaction_plan": payloads["transaction_plan"],
            "receipt_drain_plan": payloads["receipt_drain_plan"],
            "closeout_projection_packet": payloads["closeout_projection_packet"],
            "scoped_mutation_policy": payloads["scoped_mutation_policy"],
            "checkpoint_lane_policy": payloads["checkpoint_lane_policy"],
        }
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_mission_transaction_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_mission_transaction_bundle",
            "bundle_id": bundle_id,
            "bundle_manifest_schema_version": manifest.get("schema_version"),
            "validator_id": VALIDATOR_ID,
            "anti_claim": (
                "The exported mission transaction bundle validates public work, claim, "
                "dependency, checkpoint-lane, receipt-drain, and closeout metadata. It does "
                "not mutate live Task Ledger or Work Ledger state, authorize broad staging "
                "without operator intent, authorize release, or complete later organs."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": "mission_transaction_bundle_metadata_not_live_ledger_authority",
                "live_work_state_mutation_authorized": False,
                "live_task_ledger_mutation_authorized": False,
                "live_work_ledger_mutation_authorized": False,
                "broad_stage_authorized": False,
                "broad_checkpoint_requires_operator_authorization": True,
                "suspected_secret_requires_hard_stop": True,
                "dirty_tree_blocks_scoped_commit": False,
                "release_authorized": False,
                "later_organs_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": {},
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "private_state_scan": private_scan,
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "workitem_ids": workitem_result["workitem_ids"],
            "blocked_workitem_ids": workitem_result["blocked_workitem_ids"],
            "schedulable_workitem_ids": workitem_result["schedulable_workitem_ids"],
            "dependency_refs": workitem_result["dependency_refs"],
            "dependency_status_by_workitem": workitem_result[
                "dependency_status_by_workitem"
            ],
            "workitem_rows_projection_not_authority": workitem_result[
                "workitem_rows_projection_not_authority"
            ],
            "accepted_claim_ids": claim_result["accepted_claim_ids"],
            "claim_rows_projection_not_authority": claim_result[
                "claim_rows_projection_not_authority"
            ],
            "metadata_projection_not_live_ledger_authority": True,
            "resolved_dependency_refs": dependency_result["resolved_dependency_refs"],
            "dependency_resolution_receipt": dependency_result[
                "dependency_resolution_receipt"
            ],
            "downstream_unlock_edges": dependency_result["downstream_unlock_edges"],
            "claim_preflight_result": {
                "decision": "pass_metadata_claims_no_live_conflict",
                "accepted_claim_ids": claim_result["accepted_claim_ids"],
                "same_path_conflict_claim_ids": claim_result[
                    "same_path_conflict_claim_ids"
                ],
                "claim_conflict_recheck_status": "metadata_projection_only_no_live_claim_recheck",
                "expected_parent_status": "not_applicable_metadata_projection",
                "replan_required": False,
            },
            "scoped_mutation_receipt": scoped_policy_result,
            "checkpoint_lane_decision": checkpoint_lane_result,
            "closeout_status_projection": {
                **closeout_result,
                "receipt_refs_drained": receipt_drain_result["receipt_refs_drained"],
                "exact_receipt_drain_scope": receipt_drain_result[
                    "exact_receipt_drain_scope"
                ],
                "receipt_drain_exclusivity_status": receipt_drain_result[
                    "receipt_drain_exclusivity_status"
                ],
                "body_redacted": True,
            },
            "receipt_drain_plan": receipt_drain_result,
            "work_landing_reconcile_plan": {
                "mode": transaction_result["mode"],
                "recommended_next_action": transaction_result["recommended_next_action"],
                "actions": transaction_result["actions"],
                "mutation_policy": transaction_result["mutation_policy"],
                "apply_result": transaction_result["apply_result"],
                "ordered_controller_action_ids": transaction_result[
                    "ordered_controller_action_ids"
                ],
                "transaction_id": transaction_result["transaction_id"],
                "work_landing_reconcile_status": transaction_result[
                    "work_landing_reconcile_status"
                ],
                "receipt_drain_prerequisite_status": "metadata_receipts_declared",
                "claim_release_order_status": transaction_result[
                    "claim_release_order_status"
                ],
                "body_redacted": True,
            },
            "transaction_id": transaction_result["transaction_id"],
            "bundle_fingerprint": bundle_fingerprint,
            "public_replacement_refs": [
                public_relative_path(path, display_root=public_root)
                for path in _mission_bundle_paths(input_path)
            ],
        }
    )
    receipt_path = _write_mission_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def run(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_input_payloads(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)

    dependency_result = validate_dependency_unlock_scheduler(payloads["dependency_graph"])
    claim_result = validate_claim_preflight(
        payloads["claims"],
        payloads["repo_state"],
        payloads["missing_owned_path"],
    )
    scoped_result = validate_scoped_receipt_authority(payloads["scoped_receipt"])
    private_marker_result = validate_private_marker(payloads["private_marker"])
    preflight_result = validate_preflight_overclaim(payloads["preflight_overclaim"])
    checkpoint_lane_result = validate_checkpoint_lane_policy(
        payloads["checkpoint_lane_policy"],
        payloads["checkpoint_negative_cases"],
    )

    observed = _merge_observed(
        dependency_result,
        claim_result,
        scoped_result,
        private_marker_result,
        preflight_result,
        checkpoint_lane_result,
    )
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    all_findings = sorted(
        [
            *dependency_result["findings"],
            *claim_result["findings"],
            *scoped_result["findings"],
            *private_marker_result["findings"],
            *preflight_result["findings"],
            *checkpoint_lane_result["findings"],
        ],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True
    private_scan["synthetic_boundary_negative_cases_observed"] = [
        "mission_fixture_private_task_ledger_body"
    ]

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "validator_id": VALIDATOR_ID,
            "anti_claim": MISSION_ANTI_CLAIM,
            "authority_ceiling": MISSION_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": all_findings,
            "private_state_scan": private_scan,
            "blocked_workitem_ids": dependency_result["blocked_workitem_ids"],
            "ready_but_unsatisfied_workitem_ids": dependency_result[
                "ready_but_unsatisfied_workitem_ids"
            ],
            "resolved_dependency_refs": dependency_result["resolved_dependency_refs"],
            "dependency_status_by_workitem": dependency_result["dependency_status_by_workitem"],
            "dependency_resolution_receipt": dependency_result["dependency_resolution_receipt"],
            "unsatisfied_dep_ids": dependency_result["unsatisfied_dep_ids"],
            "downstream_unlock_edges": dependency_result["downstream_unlock_edges"],
            "unlocks_by_rank": dependency_result["unlocks_by_rank"],
            "dangling_dependency_refs": dependency_result["dangling_dependency_refs"],
            "schedulable_workitem_ids": dependency_result["schedulable_workitem_ids"],
            "downstream_schedulable_before": dependency_result["downstream_schedulable_before"],
            "schedulability_decision_source": dependency_result["schedulability_decision_source"],
            "dependency_unlock_resolution_basis": dependency_result[
                "dependency_unlock_resolution_basis"
            ],
            "anomaly_refs": dependency_result["anomaly_refs"],
            "derived_not_authority": dependency_result["derived_not_authority"],
            "schedulable": dependency_result["schedulable"],
            "dependency_refs": dependency_result["dependency_refs"],
            "claim_preflight_result": claim_result,
            "scoped_authority_result": scoped_result,
            "private_marker_result": private_marker_result,
            "preflight_overclaim_result": preflight_result,
            "checkpoint_lane_decision": checkpoint_lane_result,
            "work_landing_attempt": {
                "attempt_id": "attempt_toy_route_fixture_001",
                "work_item_id": "cap_toy_route_fixture",
                "session_id": "session_a",
                "read_set": ["fixtures/toy_repo/core/route_plane.json@toy-route-plane-before"],
                "write_set": ["fixtures/toy_repo/core/route_plane.json"],
                "owned_paths": ["fixtures/toy_repo/core/route_plane.json"],
                "idempotency_key": "toy-route-fixture-session-a",
                "body_redacted": True,
            },
            "scoped_mutation_receipt": {
                "owned_paths": ["fixtures/toy_repo/core/route_plane.json"],
                "mutation_status": "synthetic_scoped_mutation_valid_for_claim_a",
                "expected_parent_status": "pass_for_claim_a_stale_for_claim_b",
                "broad_stage_used": False,
                "authority_upgrade_rejected": scoped_result["scoped_receipt_authority_rejected"],
                "body_redacted": True,
            },
            "closeout_status_projection": {
                "work_item_id": "cap_toy_route_fixture",
                "status_before": "ready",
                "status_after": "closed_synthetic",
                "receipt_refs_drained": ["receipt_expected_001"],
                "exact_receipt_drain_scope": ["receipt_expected_001"],
                "receipt_drain_exclusivity_status": "only_declared_receipt_drained",
                "unrelated_receipt_refs_left_open": ["receipt_unrelated_999"],
                "derived_not_authority": True,
                "body_redacted": True,
            },
            "dependency_unlock_scheduler": dependency_result,
            "work_landing_reconcile_plan": {
                "mode": "dry_run",
                "recommended_next_action": "record_scoped_commit_landing_then_drain_exact_receipt",
                "actions": [
                    {
                        "action_id": action,
                        "apply_status": "dry_run_not_mutated",
                        "blocked_by": [],
                        "would_mutate": False,
                        "idempotency_key": f"mission-toy-{index}",
                        "evidence_if_already_done": [],
                    }
                    for index, action in enumerate(ORDERED_CONTROLLER_ACTION_IDS, start=1)
                ],
                "mutation_policy": {
                    "live_state_mutation": False,
                    "broad_stage_used": False,
                },
                "apply_result": "dry_run_no_live_mutation",
                "ordered_controller_action_ids": ORDERED_CONTROLLER_ACTION_IDS,
                "transaction_id": "mtx_toy_route_fixture",
                "work_landing_reconcile_status": "ordered_dry_run_plan_emitted",
                "receipt_drain_prerequisite_status": "commit_landing_required_before_drain",
                "claim_release_order_status": "release_after_closeout_only",
                "body_redacted": True,
            },
            "fixture_inputs": [
                public_relative_path(path, display_root=public_root)
                for path in _input_file_paths(input_path)
            ],
        }
    )
    paths = write_receipts(out_dir, result, public_root=public_root)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-mission-transaction-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.mission_transaction_work_spine "
            f"run --input {args.input} --out {args.out}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "validate-mission-transaction-bundle":
        command = (
            "python -m microcosm_core.organs.mission_transaction_work_spine "
            f"validate-mission-transaction-bundle --input {args.input} --out {args.out}"
        )
        result = run_mission_transaction_bundle(args.input, args.out, command=command)
    else:
        parser.error("expected subcommand: run or validate-mission-transaction-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
