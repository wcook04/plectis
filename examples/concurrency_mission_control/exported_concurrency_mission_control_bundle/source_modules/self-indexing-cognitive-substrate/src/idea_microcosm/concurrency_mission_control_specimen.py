"""Compile the concurrency and work-metabolism specimen artifacts.

[PURPOSE]
Show how claimed work moves through leases, dependencies, receipts, closeout, and residuals.

[INTERFACE]
Expose builder functions that emit the mission board, bridge artifact, README, and receipt.

[FLOW]
Evaluate synthetic lane cases, classify blocked or accepted transactions, and summarize bridge state.

[DEPENDENCIES]
Uses only JSON fixtures, pathlib writes, UTC timestamps, and release-local Task Ledger specimens.

[CONSTRAINTS]
Represents a public-safe synthetic transaction fixture, not private mission-control runtime authority.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPECIMEN_ID = "concurrency_transaction_mission_control_microcosm"
DEFAULT_OUTPUT_PATH = "microcosms/concurrency_mission_control/mission_board.json"
DEFAULT_RECEIPT_PATH = "microcosms/concurrency_mission_control/receipt.json"
DEFAULT_WORK_METABOLISM_BRIDGE_PATH = "microcosms/concurrency_mission_control/work_metabolism_bridge.json"
DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH = "microcosms/concurrency_mission_control/provider_repair_bridge.json"
DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH = (
    "microcosms/concurrency_mission_control/task_ledger_residual_replay_bridge.json"
)
README_PATH = "microcosms/concurrency_mission_control/README.md"
TASK_LEDGER_EVENTS_PATH = "microcosms/task_ledger_cap_economy/events.jsonl"
TASK_LEDGER_PROJECTION_PATH = "microcosms/task_ledger_cap_economy/projection.json"
TASK_LEDGER_RECEIPT_PATH = "microcosms/task_ledger_cap_economy/receipt.json"
TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH = (
    "microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json"
)
PROVIDER_CANARY_BOARD_PATH = "microcosms/provider_harness_canary/canary_board.json"
PROVIDER_CANARY_RECEIPT_PATH = "microcosms/provider_harness_canary/receipt.json"
AUTHORITY_POSTURE = "public_safe_synthetic_transaction_fixture_not_private_mission_control_runtime"
BRIDGE_AUTHORITY_POSTURE = (
    "public_safe_synthetic_work_metabolism_bridge_not_private_ledger_or_runtime_authority"
)
PROVIDER_REPAIR_BRIDGE_AUTHORITY_POSTURE = (
    "public_safe_provider_repair_transaction_bridge_not_real_provider_or_live_concurrency_authority"
)
TASK_LEDGER_RESIDUAL_REPLAY_AUTHORITY_POSTURE = (
    "public_safe_task_ledger_residual_replay_bridge_not_private_task_or_work_ledger_authority"
)

PUBLIC_PRIOR_ART_BOUNDARIES: tuple[dict[str, str], ...] = (
    {
        "prior_art_id": "event_sourcing_event_log",
        "name": "Event Sourcing",
        "url": "https://martinfowler.com/eaaDev/EventSourcing.html",
        "already_public_component": "state changes captured as a sequence of events that can be queried or replayed",
        "boundary": "Do not claim append-only event history or replay as the contribution by itself.",
    },
    {
        "prior_art_id": "temporal_durable_execution",
        "name": "Temporal Durable Execution",
        "url": "https://temporal.io/blog/what-is-durable-execution",
        "already_public_component": "crash-proof long-running workflow execution with persisted progress",
        "boundary": "Do not claim reliable long-running execution or workflow persistence as the contribution by itself.",
    },
    {
        "prior_art_id": "azure_saga_distributed_transactions",
        "name": "Saga distributed transactions pattern",
        "url": "https://learn.microsoft.com/en-us/azure/architecture/patterns/saga",
        "already_public_component": "multi-step local transactions with compensating actions when a step fails",
        "boundary": "Do not claim transaction sequencing, orchestration, or compensation as the contribution by itself.",
    },
    {
        "prior_art_id": "opentelemetry_observability_signals",
        "name": "OpenTelemetry observability",
        "url": "https://opentelemetry.io/docs/",
        "already_public_component": "vendor-neutral traces, metrics, and logs for observability",
        "boundary": "Do not claim telemetry, logs, or receipts as the contribution by themselves.",
    },
)


FIXTURE_CASES = (
    {
        "case_id": "case.independent_lanes_complete",
        "expected_decision": "accept",
        "lanes": [
            {
                "lane_id": "lane.release_registry_refresh",
                "requested_status": "complete",
                "owner_paths": ["registry/release_candidates.json", "state/release_candidate_portfolio.json"],
                "depends_on": [],
                "receipt_ref": "receipts/release_candidate_portfolio.json",
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
            {
                "lane_id": "lane.cold_sandbox_probe",
                "requested_status": "complete",
                "owner_paths": ["receipts/cold_sandbox_probe_latest.json", "state/artifact_manifest.json"],
                "depends_on": ["lane.release_registry_refresh"],
                "receipt_ref": "receipts/cold_sandbox_probe_latest.json",
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
        ],
    },
    {
        "case_id": "case.overlap_claim_rejected",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.candidate_registry_update",
                "requested_status": "running",
                "owner_paths": ["registry/release_candidates.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
            {
                "lane_id": "lane.website_card_preview",
                "requested_status": "running",
                "owner_paths": ["registry/release_candidates.json", "website/cards/generated/microcosm_cards.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
        ],
    },
    {
        "case_id": "case.duplicate_validation_command_rejected",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.focused_pytest_primary",
                "requested_status": "running",
                "owner_paths": ["receipts/focused_pytest_meta_diagnostics.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
                "command_key": "pytest:tests/test_microcosm_contract.py::test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse",
                "command_family": "focused_pytest",
                "command_budget_ms": 5000,
                "observed_wait_ms": 0,
            },
            {
                "lane_id": "lane.focused_pytest_duplicate",
                "requested_status": "running",
                "owner_paths": ["receipts/focused_pytest_meta_diagnostics_duplicate.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
                "command_key": "pytest:tests/test_microcosm_contract.py::test_meta_diagnostics_workbench_specimen_routes_meta_failures_without_authority_collapse",
                "command_family": "focused_pytest",
                "command_budget_ms": 5000,
                "observed_wait_ms": 38000,
            },
        ],
    },
    {
        "case_id": "case.dependency_not_ready",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.scaffold_refresh",
                "requested_status": "pending",
                "owner_paths": ["self-indexing-cognitive-substrate"],
                "public_boundary": "manifest-included public-safe synthetic microcosm root, not a private source grant",
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
            {
                "lane_id": "lane.clone_probe_refresh",
                "requested_status": "running",
                "owner_paths": ["receipts/git_clone_probe_latest.json"],
                "depends_on": ["lane.scaffold_refresh"],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
        ],
    },
    {
        "case_id": "case.stale_lease_rejected",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.long_running_probe",
                "requested_status": "running",
                "owner_paths": ["microcosms/concurrency_mission_control/mission_board.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2026-05-12T23:59:00Z",
            }
        ],
    },
    {
        "case_id": "case.complete_without_receipt_rejected",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.unreceipted_success",
                "requested_status": "complete",
                "owner_paths": ["microcosms/concurrency_mission_control/receipt.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            }
        ],
    },
    {
        "case_id": "case.supervised_scope_missing_contract_rejected",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.concurrency_leaf_refresh",
                "requested_status": "running",
                "parent_scope_id": "scope.public_microcosm_concurrency_wave",
                "owner_paths": ["microcosms/concurrency_mission_control/mission_board.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
            {
                "lane_id": "lane.meta_diagnostic_route_refresh",
                "requested_status": "running",
                "parent_scope_id": "scope.public_microcosm_concurrency_wave",
                "owner_paths": ["microcosms/meta_diagnostics_workbench/diagnostic_board.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
        ],
    },
    {
        "case_id": "case.supervised_scope_missing_finalizer_rejected",
        "expected_decision": "block",
        "supervision_contract": {
            "parent_scope_id": "scope.public_microcosm_concurrency_closeout",
            "claim_policy": "children_must_claim_disjoint_owner_paths",
            "finalizer_policy": "parent_scope_closes_only_with_finalizer_receipt",
            "residue_budget": "zero_unrouted_residuals",
            "finalizer_receipt_ref": None,
        },
        "lanes": [
            {
                "lane_id": "lane.concurrency_leaf_receipted",
                "requested_status": "complete",
                "parent_scope_id": "scope.public_microcosm_concurrency_closeout",
                "owner_paths": ["microcosms/concurrency_mission_control/receipt.json"],
                "depends_on": [],
                "receipt_ref": "microcosms/concurrency_mission_control/receipt.json",
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
            {
                "lane_id": "lane.root_validate_receipted",
                "requested_status": "complete",
                "parent_scope_id": "scope.public_microcosm_concurrency_closeout",
                "owner_paths": ["receipts/validation_run.json"],
                "depends_on": ["lane.concurrency_leaf_receipted"],
                "receipt_ref": "receipts/validation_run.json",
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
        ],
    },
    {
        "case_id": "case.misanchored_claim_requires_rehome",
        "expected_decision": "block",
        "lanes": [
            {
                "lane_id": "lane.generated_index_refresh",
                "requested_status": "running",
                "declared_anchor_id": "phase.declared_but_dormant",
                "anchor_status": "declared_anchor_runtime_dormant",
                "work_item_id": None,
                "owner_paths": ["navigation/microcosm_index.json"],
                "depends_on": [],
                "receipt_ref": None,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            }
        ],
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_sha256(payload: dict[str, Any]) -> str:
    stable_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _repair_row(failure: dict[str, Any]) -> dict[str, Any]:
    failure_class = failure["failure_class"]
    repair_contracts = {
        "write_scope_conflict": "Give one lane the owner path, split the write set, or wait until the current claim finalizes.",
        "duplicate_command_run": "Attach to the active command, reuse a fresh completed receipt, or narrow the command key before launching another run.",
        "dependency_not_complete": "Finish or downgrade the dependency before starting the dependent lane.",
        "stale_lease": "Refresh the claim lease or mark the lane blocked before continuing work.",
        "missing_receipt": "Write a receipt with command, result, evidence refs, and omissions before declaring the lane complete.",
        "supervised_scope_missing_contract": "Declare parent_scope_id, claim_policy, finalizer_policy, and residue_budget before treating child claims as one supervised wave.",
        "missing_parent_finalizer": "Write the parent finalizer receipt, with child receipts and residual disposition, before declaring the supervised scope closed.",
        "misanchored_claim": "Rehome the lane under an explicit WorkItem, supervised scope, or live owner before continuing mutation.",
    }
    return {
        "failure_class": failure_class,
        "lane_id": failure["lane_id"],
        "repair_contract": repair_contracts[failure_class],
        "source_failure": failure,
    }


def _evaluate_case(case: dict[str, Any], generated_at: str) -> dict[str, Any]:
    lanes = [dict(row) for row in case["lanes"]]
    lane_status = {lane["lane_id"]: lane["requested_status"] for lane in lanes}
    active_owner: dict[str, str] = {}
    active_command: dict[str, str] = {}
    failures: list[dict[str, Any]] = []
    observed_failure_classes: list[str] = []
    now = _parse_utc(generated_at)

    def add_failure(failure: dict[str, Any]) -> None:
        failures.append(failure)
        if failure["failure_class"] not in observed_failure_classes:
            observed_failure_classes.append(failure["failure_class"])

    for lane in lanes:
        lane_id = lane["lane_id"]
        status = lane["requested_status"]
        for dep in lane.get("depends_on", []):
            if lane_status.get(dep) != "complete":
                add_failure(
                    {
                        "failure_class": "dependency_not_complete",
                        "lane_id": lane_id,
                        "dependency_lane_id": dep,
                        "dependency_status": lane_status.get(dep, "missing"),
                    }
                )

        if status in {"running", "complete"}:
            lease_expires_at = lane.get("lease_expires_at")
            if isinstance(lease_expires_at, str) and _parse_utc(lease_expires_at) <= now:
                add_failure(
                    {
                        "failure_class": "stale_lease",
                        "lane_id": lane_id,
                        "lease_expires_at": lease_expires_at,
                        "generated_at": generated_at,
                    }
                )

        if status == "complete" and not lane.get("receipt_ref"):
            add_failure(
                {
                    "failure_class": "missing_receipt",
                    "lane_id": lane_id,
                    "requested_status": status,
                }
            )

        if status in {"running", "complete"}:
            for owner_path in lane.get("owner_paths", []):
                previous = active_owner.get(owner_path)
                if previous and previous != lane_id:
                    add_failure(
                        {
                            "failure_class": "write_scope_conflict",
                            "lane_id": lane_id,
                            "conflicting_lane_id": previous,
                            "owner_path": owner_path,
                        }
                    )
                else:
                    active_owner[owner_path] = lane_id

        if status == "running":
            command_key = lane.get("command_key")
            if isinstance(command_key, str) and command_key:
                previous_command_lane = active_command.get(command_key)
                if previous_command_lane and previous_command_lane != lane_id:
                    add_failure(
                        {
                            "failure_class": "duplicate_command_run",
                            "lane_id": lane_id,
                            "conflicting_lane_id": previous_command_lane,
                            "command_key": command_key,
                            "command_family": lane.get("command_family"),
                            "command_budget_ms": lane.get("command_budget_ms"),
                            "observed_wait_ms": lane.get("observed_wait_ms"),
                            "wait_policy": "attach_or_reuse_active_command_key",
                        }
                    )
                else:
                    active_command[command_key] = lane_id

        if (
            status in {"running", "complete"}
            and lane.get("anchor_status") == "declared_anchor_runtime_dormant"
            and not lane.get("work_item_id")
            and not lane.get("parent_scope_id")
        ):
            add_failure(
                {
                    "failure_class": "misanchored_claim",
                    "lane_id": lane_id,
                    "declared_anchor_id": lane.get("declared_anchor_id"),
                    "anchor_status": lane.get("anchor_status"),
                    "repair_policy": "rehome_before_mutation",
                }
            )

    parent_scope_ids = sorted(
        {
            str(lane["parent_scope_id"])
            for lane in lanes
            if lane.get("parent_scope_id") and lane.get("requested_status") in {"running", "complete"}
        }
    )
    supervision_contract = case.get("supervision_contract")
    if parent_scope_ids and not isinstance(supervision_contract, dict):
        add_failure(
            {
                "failure_class": "supervised_scope_missing_contract",
                "lane_id": lanes[0]["lane_id"],
                "parent_scope_ids": parent_scope_ids,
                "missing_fields": ["parent_scope_id", "claim_policy", "finalizer_policy", "residue_budget"],
            }
        )
    elif isinstance(supervision_contract, dict):
        required_fields = ["parent_scope_id", "claim_policy", "finalizer_policy", "residue_budget"]
        missing_fields = [field for field in required_fields if not supervision_contract.get(field)]
        contract_parent_scope = supervision_contract.get("parent_scope_id")
        if contract_parent_scope and str(contract_parent_scope) not in parent_scope_ids:
            missing_fields.append("matching_child_parent_scope")
        if missing_fields:
            add_failure(
                {
                    "failure_class": "supervised_scope_missing_contract",
                    "lane_id": lanes[0]["lane_id"],
                    "parent_scope_ids": parent_scope_ids,
                    "missing_fields": missing_fields,
                }
            )
        all_children_complete = bool(parent_scope_ids) and all(
            lane.get("requested_status") == "complete"
            for lane in lanes
            if lane.get("parent_scope_id") == contract_parent_scope
        )
        if all_children_complete and not supervision_contract.get("finalizer_receipt_ref"):
            add_failure(
                {
                    "failure_class": "missing_parent_finalizer",
                    "lane_id": lanes[0]["lane_id"],
                    "parent_scope_id": contract_parent_scope,
                    "finalizer_policy": supervision_contract.get("finalizer_policy"),
                    "residue_budget": supervision_contract.get("residue_budget"),
                }
            )

    evaluator_status = "block" if failures else "accept"
    return {
        "case_id": case["case_id"],
        "lanes": lanes,
        "expected_decision": case["expected_decision"],
        "evaluator_decision": {
            "evaluator_status": evaluator_status,
            "failure_classes": observed_failure_classes,
            "failures": failures,
            "repair_rows": [_repair_row(failure) for failure in failures],
            "status_authority": "mission_transaction_evaluator_only",
            "lane_self_status_used_as_authority": False,
        },
        "case_status": "ok" if evaluator_status == case["expected_decision"] else "failed",
    }


def _case_source_capsule(case: dict[str, Any], output_path: str) -> dict[str, Any]:
    case_id = str(case["case_id"])
    decision = case["evaluator_decision"]
    failure_classes = list(decision["failure_classes"])
    repair_rows = list(decision["repair_rows"])
    source_clip = {
        "case_id": case_id,
        "lanes": case["lanes"],
        "expected_decision": case["expected_decision"],
        "evaluator_decision": decision,
        "case_status": case["case_status"],
    }
    evaluator_status = str(decision["evaluator_status"])
    return {
        "capsule_id": f"source_capsule.concurrency_mission_control.{case_id}",
        "status": "ok",
        "source_class": "public_safe_concurrency_transaction_case",
        "source_ref": f"{output_path}:cases.{case_id}",
        "clip_hash_algorithm": "sha256",
        "clip_hash": _json_sha256(source_clip),
        "source_clip": source_clip,
        "semantic_carryforward": {
            "case_id": case_id,
            "expected_decision": case["expected_decision"],
            "evaluator_status": evaluator_status,
            "transaction_status": "closed_local_fixture_only" if evaluator_status == "accept" else "routed_fail_closed",
            "failure_classes": failure_classes,
            "repair_route_count": len(repair_rows),
            "lane_count": len(case["lanes"]),
            "lane_ids": [lane["lane_id"] for lane in case["lanes"]],
            "owner_path_count": sum(len(lane.get("owner_paths", [])) for lane in case["lanes"]),
            "receipt_ref_count": len([lane for lane in case["lanes"] if lane.get("receipt_ref")]),
            "status_authority": decision["status_authority"],
            "lane_self_status_used_as_authority": decision["lane_self_status_used_as_authority"],
            "carryforward_rule": "Carry transaction cases forward only with evaluator status, repair rows, lane owner boundaries, and anti-claims; lane requested status remains input evidence.",
        },
        "repair_route_refs": [
            f"{output_path}:cases.{case_id}.evaluator_decision.repair_rows.{index}"
            for index, _repair_row in enumerate(repair_rows)
        ],
        "omission_boundary": "No private mission-control runtime, private Task Ledger row, Work Ledger session body, provider state, raw operator voice, or hosted orchestration state is included.",
        "authority_boundary": "Local synthetic transaction fixture capsule only; not scheduler authority, hosted orchestration proof, public release approval, production concurrency safety evidence, or private-runtime equivalence.",
        "anti_claims": [
            "private mission-control runtime exported",
            "hosted orchestration proof",
            "public release approval",
            "production concurrency safety evidence",
            "private-runtime equivalence",
        ],
    }


def _source_capsule_provenance(cases: list[dict[str, Any]], output_path: str) -> dict[str, Any]:
    capsules = [_case_source_capsule(case, output_path) for case in cases]
    return {
        "kind": "source_capsule_provenance",
        "schema_version": "source_capsule_provenance_v0",
        "status": "ok",
        "hash_algorithm": "sha256",
        "source_capsules": capsules,
        "carryforward_contract": {
            "source_board": output_path,
            "required_fields": [
                "source_clip",
                "clip_hash",
                "semantic_carryforward",
                "repair_route_refs",
                "anti_claims",
            ],
            "authority_rule": "concurrency_transaction_cases_may_carry_forward_only_with_evaluator_status_and_repair_rows",
        },
        "summary": {
            "capsule_count": len(capsules),
            "transaction_case_capsule_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule["source_class"] == "public_safe_concurrency_transaction_case"
                ]
            ),
            "public_safe_source_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule["source_class"] == "public_safe_concurrency_transaction_case"
                ]
            ),
            "hashed_source_clip_count": len([capsule for capsule in capsules if capsule.get("clip_hash")]),
            "semantic_carryforward_count": len(
                [capsule for capsule in capsules if capsule.get("semantic_carryforward")]
            ),
            "accepted_capsule_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule["semantic_carryforward"]["transaction_status"] == "closed_local_fixture_only"
                ]
            ),
            "blocked_capsule_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule["semantic_carryforward"]["transaction_status"] == "routed_fail_closed"
                ]
            ),
            "repair_routed_capsule_count": len(
                [capsule for capsule in capsules if capsule["semantic_carryforward"]["repair_route_count"] > 0]
            ),
            "evaluator_authority_preserved_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule["semantic_carryforward"]["status_authority"]
                    == "mission_transaction_evaluator_only"
                ]
            ),
            "lane_self_status_authority_count": len(
                [
                    capsule
                    for capsule in capsules
                    if capsule["semantic_carryforward"]["lane_self_status_used_as_authority"] is True
                ]
            ),
        },
        "anti_claims": [
            "local diagnostics only",
            "not private mission-control runtime export",
            "not hosted orchestration proof",
            "not public release approval",
            "not production concurrency safety evidence",
            "not private-runtime equivalence",
        ],
    }


def _provider_capsule_index(provider_board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    provenance = provider_board.get("source_capsule_provenance", {})
    capsules = provenance.get("source_capsules", []) if isinstance(provenance, dict) else []
    by_case_id: dict[str, dict[str, Any]] = {}
    for capsule in capsules:
        if not isinstance(capsule, dict):
            continue
        carryforward = capsule.get("semantic_carryforward", {})
        if isinstance(carryforward, dict) and carryforward.get("case_id"):
            by_case_id[str(carryforward["case_id"])] = capsule
    return by_case_id


def _provider_repair_owner_paths(failure_class: str | None) -> list[str]:
    if failure_class == "schema_failure":
        return [
            "src/idea_microcosm/provider_harness_canary_specimen.py",
            "microcosms/provider_harness_canary/canary_board.json",
        ]
    if failure_class == "answer_mismatch":
        return [
            "microcosms/provider_harness_canary/canary_board.json",
            "microcosms/provider_harness_canary/receipt.json",
        ]
    if failure_class == "provider_route_unavailable":
        return [
            "microcosms/provider_harness_canary/receipt.json",
            "microcosms/concurrency_mission_control/provider_repair_bridge.json",
        ]
    return ["microcosms/provider_harness_canary/receipt.json"]


def _provider_to_concurrency_repair_loop(
    root: Path,
    generated_at: str,
    *,
    output_path: str,
) -> dict[str, Any]:
    provider_board = _load_optional_json(root / PROVIDER_CANARY_BOARD_PATH)
    provider_cases = [
        row
        for row in provider_board.get("cases", [])
        if isinstance(row, dict)
    ]
    provider_capsules = _provider_capsule_index(provider_board)
    failures: list[dict[str, Any]] = []
    if provider_board.get("status") != "ok":
        failures.append({"source": PROVIDER_CANARY_BOARD_PATH, "reason": "provider canary board must be ok"})
    if not provider_cases:
        failures.append({"source": PROVIDER_CANARY_BOARD_PATH, "reason": "provider canary cases missing"})

    bridge_rows: list[dict[str, Any]] = []
    source_capsules: list[dict[str, Any]] = []
    anti_claims = [
        "provider repair loop proves real provider quality",
        "provider repair loop proves live concurrency repair",
        "provider repair loop approves public release",
        "provider repair loop exports private provider harness",
        "provider repair loop proves private-runtime equivalence",
    ]
    for index, case in enumerate(provider_cases):
        case_id = str(case.get("case_id", f"case.{index}"))
        decision = case.get("evaluator_decision", {}) if isinstance(case.get("evaluator_decision"), dict) else {}
        repair_route = case.get("repair_route", {}) if isinstance(case.get("repair_route"), dict) else {}
        status_channels = case.get("status_channels", {}) if isinstance(case.get("status_channels"), dict) else {}
        provider_response = case.get("provider_response", {}) if isinstance(case.get("provider_response"), dict) else {}
        failure_class = decision.get("failure_class")
        evaluator_status = str(decision.get("evaluator_status"))
        provider_self_attestation_used = decision.get("provider_self_attestation_used_as_authority") is True
        transaction_status = (
            "provider_pass_recorded_as_receipt_only"
            if evaluator_status == "pass"
            else "provider_repair_routed_fail_closed"
        )
        repair_required = evaluator_status != "pass"
        bridge_case_id = f"provider_concurrency.{case_id}"
        next_case = (
            f"provider_concurrency.{provider_cases[index + 1].get('case_id')}"
            if index + 1 < len(provider_cases)
            else "provider_concurrency.closeout"
        )
        source_clip = {
            "provider_case_id": case_id,
            "provider_response": provider_response,
            "status_channels": status_channels,
            "evaluator_decision": decision,
            "provider_repair_route": repair_route,
            "provider_source_capsule": {
                "capsule_id": provider_capsules.get(case_id, {}).get("capsule_id"),
                "clip_hash": provider_capsules.get(case_id, {}).get("clip_hash"),
                "source_ref": provider_capsules.get(case_id, {}).get("source_ref"),
            },
        }
        clip_hash = _json_sha256(source_clip)
        semantic_carryforward = {
            "case_id": bridge_case_id,
            "provider_case_id": case_id,
            "provider_variant": provider_response.get("provider_variant"),
            "provider_evaluator_status": evaluator_status,
            "provider_failure_class": failure_class,
            "provider_owner_lane": repair_route.get("owner_lane"),
            "restart_point": repair_route.get("restart_from"),
            "transaction_status": transaction_status,
            "transaction_claim_status": "running" if repair_required else "complete",
            "repair_required": repair_required,
            "final_status_authority": "provider_evaluator_then_mission_transaction_evaluator",
            "provider_self_attestation_used_as_authority": provider_self_attestation_used,
            "carryforward_rule": "Provider canary outcomes may enter mission transactions only through evaluator status, scoped owner paths, replay seeds, repair routes, and anti-claims.",
        }
        row = {
            "case_id": bridge_case_id,
            "provider_case_id": case_id,
            "input_or_trigger": "provider_canary_evaluator_result",
            "source_clip": source_clip,
            "source_clip_hash": clip_hash,
            "semantic_carryforward": semantic_carryforward,
            "transformation": "provider_evaluator_result_to_transaction_claim_and_replay_seed",
            "evaluator_or_validator": "provider_canary_evaluator_then_mission_transaction_evaluator",
            "outcome": transaction_status,
            "provider_evaluator_result": {
                "evaluator_status": evaluator_status,
                "failure_class": failure_class,
                "provider_self_attestation_used_as_authority": provider_self_attestation_used,
            },
            "transaction_claim": {
                "lane_id": f"lane.provider_repair.{case_id.replace('case.', '')}",
                "requested_status": "running" if repair_required else "complete",
                "owner_paths": _provider_repair_owner_paths(failure_class),
                "depends_on": ["lane.provider_harness_canary"],
                "receipt_ref": None if repair_required else PROVIDER_CANARY_RECEIPT_PATH,
                "lease_expires_at": "2030-05-13T04:00:00Z",
            },
            "repair_route": {
                "failure_class": failure_class,
                "owner_lane": repair_route.get("owner_lane"),
                "restart_from": repair_route.get("restart_from"),
                "next_action": repair_route.get("next_action"),
                "transaction_repair": (
                    "claim scoped repair owner paths, rerun provider canary, then rebuild concurrency mission-control"
                    if repair_required
                    else "record provider pass receipt without promoting it to public or hosted authority"
                ),
            },
            "restart_point": repair_route.get("restart_from") or "receipt_record",
            "replay_seed": {
                "command": (
                    "PYTHONPATH=src python3 -m idea_microcosm.cli "
                    "build-provider-harness-canary-specimen --root . --write-receipt"
                ),
                "variant": provider_response.get("provider_variant"),
            },
            "teaching_rule": (
                "A provider self-label never closes a transaction; evaluator failure becomes a scoped repair lane."
                if repair_required
                else "A provider pass is recorded as local fixture evidence and still grants no public authority."
            ),
            "evidence_refs": [
                PROVIDER_CANARY_BOARD_PATH,
                PROVIDER_CANARY_RECEIPT_PATH,
                output_path,
                DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
            ],
            "anti_claims": list(anti_claims),
            "next_case": next_case,
            "authority": {
                "evaluator_authority_preserved": not provider_self_attestation_used,
                "self_attestation_authority": provider_self_attestation_used,
                "authority_boundary": "provider_evaluator_status_drives_repair_transaction_not_provider_self_attestation",
            },
        }
        source_capsule = {
            "capsule_id": f"source_capsule.provider_concurrency_repair.{case_id}",
            "status": "ok",
            "source_class": "public_safe_provider_to_concurrency_bridge_row",
            "source_ref": f"{DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH}:bridge_rows.{bridge_case_id}",
            "clip_hash_algorithm": "sha256",
            "clip_hash": clip_hash,
            "source_clip": source_clip,
            "semantic_carryforward": semantic_carryforward,
            "repair_route_ref": f"{DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH}:bridge_rows.{bridge_case_id}.repair_route",
            "restart_point_ref": f"{DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH}:bridge_rows.{bridge_case_id}.restart_point",
            "teaching_rule_ref": f"{DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH}:bridge_rows.{bridge_case_id}.teaching_rule",
            "omission_boundary": "No real provider transcript, private harness state, private Work Ledger claim, hosted CI trace, or raw operator voice is included.",
            "authority_boundary": "Provider-to-concurrency bridge capsule only; evaluator status and mission transaction receipt remain bounded fixture authority.",
            "anti_claims": list(anti_claims),
        }
        bridge_rows.append(row)
        source_capsules.append(source_capsule)

    authority_collapse_count = sum(
        1
        for row in bridge_rows
        if row["provider_evaluator_result"]["provider_self_attestation_used_as_authority"] is True
    )
    if authority_collapse_count:
        failures.append({"source": PROVIDER_CANARY_BOARD_PATH, "reason": "provider self-attestation entered authority"})
    failure_or_block_count = sum(
        1
        for row in bridge_rows
        if row["provider_evaluator_result"]["evaluator_status"] in {"fail", "block"}
    )
    source_capsule_provenance = {
        "kind": "source_capsule_provenance",
        "schema_version": "source_capsule_provenance_v0",
        "status": "ok" if not failures else "failed",
        "hash_algorithm": "sha256",
        "source_capsules": source_capsules,
        "carryforward_contract": {
            "source_board": PROVIDER_CANARY_BOARD_PATH,
            "target_board": output_path,
            "required_fields": [
                "source_clip",
                "clip_hash",
                "semantic_carryforward",
                "repair_route_ref",
                "restart_point_ref",
                "teaching_rule_ref",
                "anti_claims",
            ],
            "authority_rule": "provider_canary_evaluator_result_drives_transaction_repair_not_self_attestation",
        },
        "summary": {
            "capsule_count": len(source_capsules),
            "provider_repair_capsule_count": len(source_capsules),
            "public_safe_source_count": len(source_capsules),
            "hashed_source_clip_count": len([capsule for capsule in source_capsules if capsule.get("clip_hash")]),
            "semantic_carryforward_count": len(
                [capsule for capsule in source_capsules if capsule.get("semantic_carryforward")]
            ),
            "repair_routed_capsule_count": failure_or_block_count,
            "teaching_rule_capsule_count": len(source_capsules),
            "evaluator_authority_preserved_count": len(source_capsules) - authority_collapse_count,
            "self_attestation_authority_count": authority_collapse_count,
        },
    }
    status = "ok" if not failures else "failed"
    summary = {
        "case_count": len(bridge_rows),
        "provider_case_count": len(provider_cases),
        "provider_failure_or_block_count": failure_or_block_count,
        "transaction_claim_count": len(bridge_rows),
        "repair_route_count": sum(1 for row in bridge_rows if row["semantic_carryforward"]["repair_required"]),
        "restart_point_count": len([row for row in bridge_rows if row.get("restart_point")]),
        "replay_seed_count": len([row for row in bridge_rows if row.get("replay_seed")]),
        "teaching_rule_count": len([row for row in bridge_rows if row.get("teaching_rule")]),
        "source_capsule_count": source_capsule_provenance["summary"]["capsule_count"],
        "semantic_carryforward_count": source_capsule_provenance["summary"]["semantic_carryforward_count"],
        "hashed_source_clip_count": source_capsule_provenance["summary"]["hashed_source_clip_count"],
        "evaluator_authority_count": len(bridge_rows) - authority_collapse_count,
        "self_attestation_authority_count": authority_collapse_count,
        "blocked_public_claim_count": len(anti_claims),
        "authority_collapse_count": authority_collapse_count,
        "provider_self_attested_rejected_count": sum(
            1 for row in provider_cases if row.get("provider_self_attestation_rejected") is True
        ),
    }
    return {
        "kind": "provider_to_concurrency_repair_loop",
        "schema_version": "provider_to_concurrency_repair_loop_v0",
        "id": "microcosm.concurrency_mission_control.provider_to_concurrency_repair_loop",
        "generated_at": generated_at,
        "status": status,
        "pattern_family": "provider_to_concurrency_repair_loop",
        "selected_native_pattern": "provider evaluator failures become transaction-scoped repair and replay cases",
        "layman_summary": "A provider can say it passed, but only the evaluator can make that result usable; failures become repair lanes with replay commands.",
        "technical_summary": "Provider canary cases are transformed into transaction claims with source clips, hashes, restart points, teaching rules, and fail-closed anti-claims.",
        "source_owner": "idea_microcosm.concurrency_mission_control_specimen",
        "builder_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
        "generated_by": {
            "source_refs": [
                PROVIDER_CANARY_BOARD_PATH,
                PROVIDER_CANARY_RECEIPT_PATH,
                "src/idea_microcosm/provider_harness_canary_specimen.py",
                "src/idea_microcosm/concurrency_mission_control_specimen.py",
            ],
            "projection_not_authority": True,
        },
        "authority_posture": PROVIDER_REPAIR_BRIDGE_AUTHORITY_POSTURE,
        "source_board": PROVIDER_CANARY_BOARD_PATH,
        "target_board": output_path,
        "bridge_rows": bridge_rows,
        "source_capsule_provenance": source_capsule_provenance,
        "authority": {
            "authority_class": "evaluator_driven_transaction_repair",
            "self_attestation_count": authority_collapse_count,
            "evaluator_authority_count": summary["evaluator_authority_count"],
            "forbidden_promotions": [
                "provider_self_attested_status_to_transaction_accept",
                "local_fixture_pass_to_public_release_ready",
                "bridge_projection_to_private_runtime_equivalence",
            ],
            "fail_closed_gates": [
                "provider_evaluator_gate",
                "mission_transaction_gate",
                "receipt_gate",
                "publication_gate",
            ],
            "public_claims_blocked": anti_claims,
        },
        "route": {
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "expected_output": DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
            "first_evidence": PROVIDER_CANARY_BOARD_PATH,
            "next_artifact": DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
            "next_microcosm": "task_ledger_cap_economy_microcosm",
            "cold_agent_instruction": "Open provider_repair_bridge.json, recompute a source_clip_hash, then inspect the matching repair_route before accepting any provider self-status.",
        },
        "cross_links": {
            "portfolio_ref": "state/release_candidate_portfolio.json",
            "branch_graph_ref": "microcosms/specimen_suite/release_microcosm_ontology.json",
            "pattern_transfer_ref": "microcosms/demo_receipt_storyboard/storyboard.json:pattern.provider_to_concurrency_repair_loop",
            "receipt_ref": DEFAULT_RECEIPT_PATH,
            "related_microcosms": [
                "provider_harness_evaluator_authority_split_microcosm",
                "concurrency_transaction_mission_control_microcosm",
                "task_ledger_cap_economy_microcosm",
            ],
            "next_refinement": "Route provider repair claims into the Task Ledger cap-economy residual queue.",
        },
        "summary": summary,
        "status_block": {
            "case_count": summary["case_count"],
            "capsule_count": summary["source_capsule_count"],
            "evidence_ref_count": 4,
            "repair_route_count": summary["repair_route_count"],
            "teaching_rule_count": summary["teaching_rule_count"],
            "blocked_claim_count": summary["blocked_public_claim_count"],
            "missing_ref_count": 0,
            "validation_status": status,
            "next_gap": "task_ledger_provider_repair_residuals",
            "next_owner": "task_ledger_cap_economy_microcosm",
        },
        "anti_claims": anti_claims,
        "public_safety_boundary": "Synthetic provider canary and synthetic transaction rows only; no private provider transcript, Work Ledger body, raw operator voice, or hosted runtime state is included.",
        "claim_boundary": "This bridge proves only a local fixture route from provider evaluator result to transaction repair row; it is not provider quality, live concurrency safety, public-release, or publication evidence.",
        "failures": failures,
    }


def _task_ledger_residual_replay_bridge(
    root: Path,
    generated_at: str,
    *,
    mission_board: dict[str, Any],
    work_metabolism_bridge: dict[str, Any],
) -> dict[str, Any]:
    residual_bridge = _load_optional_json(root / TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH)
    mechanism = residual_bridge.get("mechanism", {}) if isinstance(residual_bridge.get("mechanism"), dict) else {}
    residual_cases = [row for row in mechanism.get("cases", []) if isinstance(row, dict)]
    residual_summary = (
        residual_bridge.get("summary", {})
        if isinstance(residual_bridge.get("summary"), dict)
        else {}
    )
    residual_status_block = (
        residual_bridge.get("status", {})
        if isinstance(residual_bridge.get("status"), dict)
        else {}
    )
    failures: list[dict[str, str]] = []
    if residual_summary.get("validation_status") != "ok" and residual_status_block.get("validation_status") != "ok":
        failures.append({"source": TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH, "reason": "provider residual bridge must be ok"})
    if not residual_cases:
        failures.append({"source": TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH, "reason": "provider residual cases missing"})
    if mission_board.get("status") != "ok":
        failures.append({"source": DEFAULT_OUTPUT_PATH, "reason": "mission board must be ok"})
    if work_metabolism_bridge.get("status") != "ok":
        failures.append({"source": DEFAULT_WORK_METABOLISM_BRIDGE_PATH, "reason": "work-metabolism bridge must be ok"})

    anti_claims = [
        "task ledger residual replay bridge approves public release",
        "task ledger residual replay bridge exposes private Task Ledger or Work Ledger rows",
        "task ledger residual replay bridge proves live concurrency repair",
        "task ledger residual replay bridge closes provider repairs without evaluator authority",
        "task ledger residual replay bridge proves hosted-public readiness",
    ]
    replay_cases: list[dict[str, Any]] = []
    source_capsules: list[dict[str, Any]] = []
    for index, residual_case in enumerate(residual_cases):
        case_id = str(residual_case.get("case_id", f"task_ledger_residual.{index}"))
        semantic = (
            residual_case.get("semantic_carryforward", {})
            if isinstance(residual_case.get("semantic_carryforward"), dict)
            else {}
        )
        repair_route = (
            residual_case.get("repair_route", {})
            if isinstance(residual_case.get("repair_route"), dict)
            else {}
        )
        repair_required = semantic.get("repair_required") is True
        replay_case_id = case_id.replace("task_ledger_provider_residual.", "task_ledger_residual_replay.")
        source_clip = {
            "task_ledger_residual_case_id": case_id,
            "source_bridge_case_id": semantic.get("source_bridge_case_id"),
            "provider_case_id": semantic.get("provider_case_id"),
            "provider_evaluator_status": semantic.get("provider_evaluator_status"),
            "provider_failure_class": semantic.get("provider_failure_class"),
            "residual_status": semantic.get("residual_status"),
            "residual_event_type": semantic.get("residual_event_type"),
            "repair_required": repair_required,
            "restart_point": semantic.get("restart_point") or residual_case.get("restart_point"),
            "upstream_source_clip_hash": semantic.get("upstream_source_clip_hash"),
            "task_ledger_residual_source_clip_hash": residual_case.get("source_clip_hash"),
            "residual_repair_route": repair_route,
            "evidence_refs": residual_case.get("evidence_refs", []),
        }
        source_clip_hash = _json_sha256(source_clip)
        transaction_claim = {
            "lane_id": f"lane.task_ledger_residual_replay.{replay_case_id.rsplit('.', 1)[-1]}",
            "requested_status": "running" if repair_required else "complete",
            "owner_paths": [
                DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
                TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
            ],
            "depends_on": [
                "lane.provider_repair_residual_bridge",
                "lane.concurrency_mission_control",
            ],
            "receipt_ref": DEFAULT_RECEIPT_PATH if not repair_required else None,
            "lease_expires_at": "2030-05-13T04:00:00Z",
        }
        replay_seed = {
            "command": (
                "PYTHONPATH=src python3 -m idea_microcosm.cli "
                "build-concurrency-mission-control-specimen --root . --write-receipt"
            ),
            "source_residual_case_id": case_id,
            "restart_point": source_clip["restart_point"],
            "refresh_required": repair_required,
        }
        row_anti_claims = sorted(set(residual_case.get("anti_claims", []) + anti_claims))
        semantic_carryforward = {
            "case_id": replay_case_id,
            "source_residual_case_id": case_id,
            "provider_case_id": semantic.get("provider_case_id"),
            "provider_evaluator_status": semantic.get("provider_evaluator_status"),
            "provider_failure_class": semantic.get("provider_failure_class"),
            "residual_status": semantic.get("residual_status"),
            "repair_required": repair_required,
            "restart_point": source_clip["restart_point"],
            "transaction_status": (
                "task_ledger_residual_replay_seed_open"
                if repair_required
                else "task_ledger_residual_receipt_closed"
            ),
            "final_status_authority": "task_ledger_residual_validator_then_mission_transaction_evaluator",
            "self_attestation_used_as_authority": False,
            "carryforward_rule": "Open residual work items must re-enter concurrency as replay seeds with refreshed claims; receipt-only residuals stay bounded evidence and grant no public authority.",
        }
        row = {
            "case_id": replay_case_id,
            "input_or_trigger": "task_ledger_provider_repair_residual",
            "source_clip": source_clip,
            "source_clip_hash": source_clip_hash,
            "semantic_carryforward": semantic_carryforward,
            "transformation": "task_ledger_residual_event_to_concurrency_replay_seed",
            "evaluator_or_validator": "task_ledger_residual_validator_then_mission_transaction_evaluator",
            "outcome": semantic_carryforward["transaction_status"],
            "transaction_claim": transaction_claim,
            "repair_route": {
                "route_id": f"concurrency_residual_replay_route.{replay_case_id.rsplit('.', 1)[-1]}",
                "status": "residual_replay_open" if repair_required else "receipt_record_closed",
                "source_residual_route_id": repair_route.get("route_id"),
                "restart_point": source_clip["restart_point"],
                "next_action": (
                    "refresh scoped provider repair claim and rerun concurrency mission-control"
                    if repair_required
                    else "keep receipt-only residual closed without promoting it to release authority"
                ),
                "transaction_repair": repair_route.get("transaction_repair"),
                "repair_required": repair_required,
            },
            "restart_point": source_clip["restart_point"],
            "replay_seed": replay_seed,
            "teaching_rule": (
                "A Task Ledger residual is not closeout prose; open residuals become replay seeds with claim, lease, evidence, and evaluator authority."
                if repair_required
                else "A receipt-only residual records bounded evidence and still does not prove public release or live provider quality."
            ),
            "evidence_refs": sorted(
                set(
                    residual_case.get("evidence_refs", [])
                    + [
                        TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                        DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
                        DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
                        DEFAULT_OUTPUT_PATH,
                    ]
                )
            ),
            "anti_claims": row_anti_claims,
            "next_case": (
                residual_cases[index + 1].get("case_id")
                if index + 1 < len(residual_cases)
                else "task_ledger_residual_replay.closeout"
            ),
            "authority": {
                "evaluator_authority_preserved": True,
                "self_attestation_authority": False,
                "authority_boundary": "task ledger residuals become replay seeds only after validator and mission transaction evaluator gates",
            },
        }
        source_capsules.append(
            {
                "capsule_id": f"source_capsule.task_ledger_residual_replay.{replay_case_id}",
                "status": "ok",
                "source_class": "public_safe_task_ledger_residual_replay_case",
                "source_ref": f"{DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH}:cases.{replay_case_id}",
                "clip_hash_algorithm": "sha256",
                "clip_hash": source_clip_hash,
                "source_clip": source_clip,
                "semantic_carryforward": semantic_carryforward,
                "repair_route_ref": f"{DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH}:cases.{replay_case_id}.repair_route",
                "restart_point_ref": f"{DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH}:cases.{replay_case_id}.restart_point",
                "teaching_rule_ref": f"{DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH}:cases.{replay_case_id}.teaching_rule",
                "omission_boundary": "No private Task Ledger row body, Work Ledger session body, provider transcript, hosted trace, or raw operator voice is included.",
                "authority_boundary": "Task Ledger residual replay capsule only; validator and mission transaction evaluator remain the bounded fixture authority.",
                "anti_claims": row_anti_claims,
            }
        )
        replay_cases.append(row)

    repair_route_count = sum(1 for row in replay_cases if row["semantic_carryforward"]["repair_required"])
    authority_collapse_count = sum(
        1 for row in replay_cases if row["authority"]["self_attestation_authority"] is True
    )
    source_capsule_provenance = {
        "kind": "source_capsule_provenance",
        "schema_version": "source_capsule_provenance_v0",
        "status": "ok" if not failures else "failed",
        "hash_algorithm": "sha256",
        "source_capsules": source_capsules,
        "carryforward_contract": {
            "source_bridge": TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
            "target_board": DEFAULT_OUTPUT_PATH,
            "required_fields": [
                "source_clip",
                "clip_hash",
                "semantic_carryforward",
                "repair_route_ref",
                "restart_point_ref",
                "teaching_rule_ref",
                "anti_claims",
            ],
            "authority_rule": "task_ledger_residuals_reenter_concurrency_only_through_validator_and_mission_transaction_evaluator",
        },
        "summary": {
            "capsule_count": len(source_capsules),
            "residual_replay_capsule_count": len(source_capsules),
            "public_safe_source_count": len(source_capsules),
            "hashed_source_clip_count": len(source_capsules),
            "semantic_carryforward_count": len(source_capsules),
            "repair_routed_capsule_count": repair_route_count,
            "teaching_rule_capsule_count": len(source_capsules),
            "evaluator_authority_preserved_count": len(source_capsules) - authority_collapse_count,
            "self_attestation_authority_count": authority_collapse_count,
        },
    }
    summary = {
        "case_count": len(replay_cases),
        "source_residual_case_count": len(residual_cases),
        "source_capsule_count": len(source_capsules),
        "semantic_carryforward_count": len(source_capsules),
        "hashed_source_clip_count": len(source_capsules),
        "replay_seed_count": len([row for row in replay_cases if row.get("replay_seed")]),
        "repair_route_count": repair_route_count,
        "restart_point_count": len([row for row in replay_cases if row.get("restart_point")]),
        "teaching_rule_count": len([row for row in replay_cases if row.get("teaching_rule")]),
        "open_residual_replay_count": repair_route_count,
        "closed_residual_replay_count": len(replay_cases) - repair_route_count,
        "evaluator_authority_count": len(source_capsules) - authority_collapse_count,
        "self_attestation_authority_count": authority_collapse_count,
        "blocked_public_claim_count": len(anti_claims),
        "authority_collapse_count": authority_collapse_count,
        "missing_ref_count": 0,
        "validation_status": "ok" if not failures else "failed",
        "next_gap": "github_export_scope_manifest_hardening",
        "next_owner": "public_release_package_manifest_gate_microcosm",
    }
    return {
        "kind": "task_ledger_residual_to_concurrency_replay_bridge",
        "schema_version": "task_ledger_residual_to_concurrency_replay_bridge_v0",
        "id": "microcosm.concurrency_mission_control.task_ledger_residual_replay_bridge",
        "microcosm_id": "concurrency_transaction_mission_control_microcosm",
        "pattern_family": "task_ledger_residual_to_concurrency_replay",
        "selected_native_pattern": "Task Ledger residuals re-enter concurrency as replay seeds with refreshed claims",
        "layman_summary": "An unfinished provider repair does not disappear into a note. It becomes a replay seed that tells concurrency where to restart.",
        "technical_summary": "Provider repair residual cases from the Task Ledger cap-economy microcosm are converted into concurrency replay claims with source hashes, restart points, teaching rules, evaluator authority, and fail-closed anti-claims.",
        "source_owner": "idea_microcosm.concurrency_mission_control_specimen",
        "builder_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
        "generated_at": generated_at,
        "generated_by": {
            "source_refs": [
                TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                TASK_LEDGER_PROJECTION_PATH,
                DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
                DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
                "src/idea_microcosm/task_ledger_specimen.py",
                "src/idea_microcosm/concurrency_mission_control_specimen.py",
            ],
            "projection_not_authority": True,
        },
        "status": "ok" if not failures else "failed",
        "authority_posture": TASK_LEDGER_RESIDUAL_REPLAY_AUTHORITY_POSTURE,
        "source_bridge": TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
        "target_board": DEFAULT_OUTPUT_PATH,
        "mechanism": {"cases": replay_cases},
        "source_capsule_provenance": source_capsule_provenance,
        "authority": {
            "authority_class": "task_ledger_residual_validator_then_concurrency_replay",
            "self_attestation_count": authority_collapse_count,
            "evaluator_authority_count": summary["evaluator_authority_count"],
            "forbidden_promotions": [
                "residual_event_to_live_concurrency_success",
                "local_replay_seed_to_public_release_ready",
                "task_ledger_projection_to_private_runtime_export",
            ],
            "fail_closed_gates": [
                "task_ledger_residual_gate",
                "mission_transaction_gate",
                "receipt_gate",
                "publication_gate",
            ],
            "public_claims_blocked": anti_claims,
        },
        "route": {
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "expected_output": DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
            "first_evidence": TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
            "next_artifact": DEFAULT_RECEIPT_PATH,
            "next_microcosm": "public_release_package_manifest_gate_microcosm",
            "cold_agent_instruction": "Open task_ledger_residual_replay_bridge.json, recompute a source_clip_hash, then follow an open residual repair_route back into the concurrency builder command.",
        },
        "cross_links": {
            "portfolio_ref": "state/release_candidate_portfolio.json",
            "branch_graph_ref": "microcosms/specimen_suite/release_microcosm_ontology.json",
            "pattern_transfer_ref": "microcosms/demo_receipt_storyboard/storyboard.json:pattern.work_metabolism_to_concurrency_bridge",
            "receipt_ref": DEFAULT_RECEIPT_PATH,
            "related_microcosms": [
                "task_ledger_cap_economy_microcosm",
                "provider_harness_evaluator_authority_split_microcosm",
                "concurrency_transaction_mission_control_microcosm",
            ],
            "next_refinement": "Harden the package manifest gate against GitHub export scope overclaims.",
        },
        "summary": summary,
        "status_block": {
            "case_count": summary["case_count"],
            "capsule_count": summary["source_capsule_count"],
            "evidence_ref_count": 4,
            "repair_route_count": summary["repair_route_count"],
            "teaching_rule_count": summary["teaching_rule_count"],
            "blocked_claim_count": summary["blocked_public_claim_count"],
            "missing_ref_count": summary["missing_ref_count"],
            "validation_status": summary["validation_status"],
            "next_gap": summary["next_gap"],
            "next_owner": summary["next_owner"],
        },
        "public_safety_boundary": "Synthetic residual replay bridge only; no private Task Ledger row bodies, private Work Ledger sessions, raw operator voice, provider transcripts, or hosted release state are included.",
        "claim_boundary": "This bridge proves a local fixture route from Task Ledger residual to concurrency replay seed; it is not live concurrency repair, provider quality, public release, or private-runtime equivalence evidence.",
        "anti_claims": anti_claims,
        "failures": failures,
    }


def _build_work_metabolism_bridge(
    root: Path,
    generated_at: str,
    mission_board: dict[str, Any],
    provider_repair_bridge: dict[str, Any],
) -> dict[str, Any]:
    task_projection = _load_optional_json(root / TASK_LEDGER_PROJECTION_PATH)
    task_subjects = [
        row
        for row in task_projection.get("subjects", [])
        if isinstance(row, dict)
    ]
    closed_work_count = sum(1 for row in task_subjects if row.get("latest_status") == "closed")
    residual_count = sum(len(row.get("open_work_item_event_ids", [])) for row in task_subjects)
    mission_summary = mission_board.get("summary", {}) if isinstance(mission_board.get("summary"), dict) else {}
    bridge_failures: list[dict[str, str]] = []
    if task_projection.get("status") != "ok":
        bridge_failures.append({"source": TASK_LEDGER_PROJECTION_PATH, "reason": "task ledger projection must be ok"})
    if task_projection.get("failure_routing_status") != "all_failures_have_work_items":
        bridge_failures.append({"source": TASK_LEDGER_PROJECTION_PATH, "reason": "ledger failures must route to work_item events"})
    if mission_board.get("status") != "ok":
        bridge_failures.append({"source": DEFAULT_OUTPUT_PATH, "reason": "mission board must be ok"})
    if int(mission_summary.get("lane_self_status_authority_count", 1)) != 0:
        bridge_failures.append({"source": DEFAULT_OUTPUT_PATH, "reason": "lane self-status cannot be authority"})
    if provider_repair_bridge.get("status") != "ok":
        bridge_failures.append(
            {"source": DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH, "reason": "provider repair bridge must be ok"}
        )
    provider_bridge_summary = (
        provider_repair_bridge.get("summary", {}) if isinstance(provider_repair_bridge.get("summary"), dict) else {}
    )

    transaction_path = [
        {
            "step_id": "capture",
            "surface": "operator_intent_fixture",
            "evidence_refs": [TASK_LEDGER_EVENTS_PATH],
            "result": "intent enters the public-safe Task Ledger fixture as append-only events",
            "authority_boundary": "synthetic fixture events are not private Task Ledger export",
        },
        {
            "step_id": "shape",
            "surface": "cap_or_workitem_fixture",
            "evidence_refs": [TASK_LEDGER_PROJECTION_PATH],
            "result": "validation failures and side findings resolve to durable work_item events",
            "authority_boundary": "Task Ledger projection summarizes events but does not replace event source authority",
        },
        {
            "step_id": "claim_or_lease",
            "surface": "mission_lane_fixture",
            "evidence_refs": [DEFAULT_OUTPUT_PATH],
            "result": "lanes carry owner paths, dependencies, lease expiry, requested status, and receipt refs",
            "authority_boundary": "a Work Ledger lease is coordination evidence, not Task Ledger source authority",
        },
        {
            "step_id": "mutate_or_plan",
            "surface": "mission_transaction_evaluator",
            "evidence_refs": [DEFAULT_OUTPUT_PATH],
            "result": "overlap, duplicate command run, stale lease, unmet dependency, and missing receipt failures emit repair rows",
            "authority_boundary": "lane self-status is input only; the evaluator binds status",
        },
        {
            "step_id": "provider_repair_replay",
            "surface": "provider_to_concurrency_repair_loop",
            "evidence_refs": [
                PROVIDER_CANARY_BOARD_PATH,
                DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
            ],
            "result": "provider evaluator failures become scoped transaction claims, replay seeds, restart points, and teaching rules",
            "authority_boundary": "provider self-attestation stays observation; evaluator and transaction receipt remain authority",
        },
        {
            "step_id": "validate",
            "surface": "local_validator_fixture",
            "evidence_refs": ["src/idea_microcosm/validators.py", "receipts/validation_run.json"],
            "result": "local validator checks bridge, ledger, mission board, receipt, and anti-claims",
            "authority_boundary": "local validation is not hosted-public or publication proof",
        },
        {
            "step_id": "commit_or_receipt",
            "surface": "receipt_gate",
            "evidence_refs": [DEFAULT_RECEIPT_PATH, DEFAULT_WORK_METABOLISM_BRIDGE_PATH],
            "result": "receipt carries evidence refs, omissions, and bridge summary before success is claimable",
            "authority_boundary": "receipt status is bounded to the command and fixture evidence it names",
        },
        {
            "step_id": "closeout",
            "surface": "closed_subject_projection",
            "evidence_refs": [TASK_LEDGER_PROJECTION_PATH],
            "result": "closed fixture work remains inspectable by subject, latest event, and evidence refs",
            "authority_boundary": "closeout prose is not the backlog; durable events are",
        },
        {
            "step_id": "residual",
            "surface": "open_work_item_projection",
            "evidence_refs": [
                TASK_LEDGER_PROJECTION_PATH,
                TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                DEFAULT_OUTPUT_PATH,
            ],
            "result": "open work_item events and blocked mission cases stay visible as next-action pressure",
            "authority_boundary": "blocked local cases do not become public-release blockers unless a public gate says so",
        },
        {
            "step_id": "residual_replay",
            "surface": "task_ledger_residual_to_concurrency_replay_bridge",
            "evidence_refs": [
                TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
                DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
                DEFAULT_OUTPUT_PATH,
            ],
            "result": "provider repair residuals re-enter concurrency as replay seeds with restart points and scoped claims",
            "authority_boundary": "Task Ledger residual projection is input evidence; validator and mission transaction evaluator remain authority",
        },
        {
            "step_id": "projection_update",
            "surface": "release_witness_projection",
            "evidence_refs": [
                DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
                "microcosms/specimen_suite/release_microcosm_ontology.json",
                "microcosms/specimen_suite/quality_delta_board.json",
            ],
            "result": "release projections can point reviewers at the bridge without exposing private ledger state",
            "authority_boundary": "generated release projections are reviewer interfaces, not source authority",
        },
    ]
    authority_boundaries = [
        "Type B advice is not substrate authority.",
        "Work Ledger lease is not Task Ledger source authority.",
        "Local validation is not hosted-public or publication proof.",
        "Generated projection is not source authority.",
        "Lane self-status is not mission-control status authority.",
        "Command self-label is not singleflight status authority.",
    ]
    evidence_refs = [
        TASK_LEDGER_EVENTS_PATH,
        TASK_LEDGER_PROJECTION_PATH,
        TASK_LEDGER_RECEIPT_PATH,
        PROVIDER_CANARY_BOARD_PATH,
        PROVIDER_CANARY_RECEIPT_PATH,
        DEFAULT_OUTPUT_PATH,
        DEFAULT_RECEIPT_PATH,
        DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
        DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
        TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
        DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
        "src/idea_microcosm/concurrency_mission_control_specimen.py",
        "src/idea_microcosm/validators.py",
    ]
    authority_collapse_count = 0
    return {
        "kind": "work_metabolism_bridge",
        "schema_version": "work_metabolism_bridge_v0",
        "id": "microcosm.concurrency_mission_control.work_metabolism_bridge",
        "generated_at": generated_at,
        "status": "ok" if not bridge_failures else "failed",
        "mission_thread_id": "work_becomes_durable_substrate",
        "selected_contribution": "self_indexing_cognitive_substrate",
        "authority_posture": BRIDGE_AUTHORITY_POSTURE,
        "input": {
            "operator_intent_fixture": {
                "source_ref": TASK_LEDGER_EVENTS_PATH,
                "event_count": task_projection.get("event_count"),
                "event_type_counts": task_projection.get("event_type_counts", {}),
            },
            "cap_or_workitem_fixture": {
                "source_ref": TASK_LEDGER_PROJECTION_PATH,
                "subject_count": task_projection.get("subject_count"),
                "work_item_count": task_projection.get("work_item_count"),
                "failure_routing_status": task_projection.get("failure_routing_status"),
            },
            "transaction_control_fixture": {
                "source_ref": DEFAULT_OUTPUT_PATH,
                "case_count": mission_summary.get("case_count"),
                "accept_count": mission_summary.get("accept_count"),
                "block_count": mission_summary.get("block_count"),
                "repair_row_count": mission_summary.get("repair_row_count"),
                "duplicate_command_run_count": mission_summary.get("duplicate_command_run_count"),
            },
            "provider_repair_fixture": {
                "source_ref": DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
                "provider_case_count": provider_bridge_summary.get("provider_case_count"),
                "repair_route_count": provider_bridge_summary.get("repair_route_count"),
                "teaching_rule_count": provider_bridge_summary.get("teaching_rule_count"),
                "authority_collapse_count": provider_bridge_summary.get("authority_collapse_count"),
            },
            "task_ledger_provider_residual_fixture": {
                "source_ref": TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                "target_replay_ref": DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
                "next_gap": "task_ledger_residuals_to_concurrency_stale_lease_replay",
            },
        },
        "transaction_path": transaction_path,
        "authority_boundaries": authority_boundaries,
        "public_prior_art_boundaries": list(PUBLIC_PRIOR_ART_BOUNDARIES),
        "evidence_refs": evidence_refs,
        "result": {
            "closed_work_count": closed_work_count,
            "residual_count": residual_count,
            "blocked_or_fail_closed_count": int(mission_summary.get("block_count", 0)),
            "duplicate_command_run_count": int(mission_summary.get("duplicate_command_run_count", 0)),
            "provider_repair_bridge_case_count": int(provider_bridge_summary.get("case_count", 0)),
            "provider_repair_bridge_repair_route_count": int(provider_bridge_summary.get("repair_route_count", 0)),
            "authority_collapse_count": authority_collapse_count,
        },
        "next_gap": "github_export_scope_manifest_hardening",
        "next_owner": "public_release_package_manifest_gate_microcosm",
        "summary": {
            "transaction_step_count": len(transaction_path),
            "authority_boundary_count": len(authority_boundaries),
            "prior_art_boundary_count": len(PUBLIC_PRIOR_ART_BOUNDARIES),
            "evidence_ref_count": len(evidence_refs),
            "closed_work_count": closed_work_count,
            "residual_count": residual_count,
            "blocked_or_fail_closed_count": int(mission_summary.get("block_count", 0)),
            "duplicate_command_run_count": int(mission_summary.get("duplicate_command_run_count", 0)),
            "provider_repair_bridge_case_count": int(provider_bridge_summary.get("case_count", 0)),
            "provider_repair_bridge_repair_route_count": int(provider_bridge_summary.get("repair_route_count", 0)),
            "provider_repair_bridge_teaching_rule_count": int(provider_bridge_summary.get("teaching_rule_count", 0)),
            "authority_collapse_count": authority_collapse_count,
            "task_ledger_projection_status": task_projection.get("status"),
            "mission_board_status": mission_board.get("status"),
            "provider_repair_bridge_status": provider_repair_bridge.get("status"),
            "next_gap": "github_export_scope_manifest_hardening",
            "next_owner": "public_release_package_manifest_gate_microcosm",
        },
        "public_safety_boundary": "Synthetic bridge only; no private Task Ledger rows, private Work Ledger sessions, raw operator voice, provider state, or hosted release state is included.",
        "claim_boundary": "The bridge claims composition of public-safe fixtures under authority boundaries, not event sourcing, durable workflows, sagas, observability, novelty proof, or deployment proof.",
        "anti_claims": [
            "work metabolism bridge proves event sourcing is novel",
            "work metabolism bridge proves durable workflow novelty",
            "work metabolism bridge proves saga or compensation novelty",
            "work metabolism bridge proves observability novelty",
            "work metabolism bridge exposes private Task Ledger or Work Ledger state",
            "work metabolism bridge grants hosted-public or publication authority",
        ],
        "failures": bridge_failures,
    }


def _readme() -> str:
    return "\n".join(
        [
            "# Concurrency Transaction Mission Control",
            "",
            "This specimen is a public-safe toy analogue for mission-control transaction discipline.",
            "It is not the private mission-control runtime, not a live scheduler, and not a publication claim.",
            "",
            "Run it from the release root:",
            "",
            "```bash",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "```",
            "",
            "The fixture evaluates nine synthetic mission cases: independent lanes, overlapping owner paths, duplicate focused validation, an unmet dependency, a stale lease, a completed lane without a receipt, an unsupervised parent scope, a missing parent finalizer, and a misanchored claim.",
            "The evaluator is the status authority; lane self-status and command self-labels are only input evidence.",
            "Duplicate command-key rows model the broader singleflight rule: attach to an active validation or reuse a fresh receipt before launching another slow command.",
            "Supervised-scope rows model multi-agent waves: child claims are not enough unless a parent scope declares claim policy, finalizer policy, residue budget, and a closeout receipt.",
            "The `source_capsule_provenance` section hashes every transaction case and carries forward only evaluator status, repair rows, lane owner boundaries, and anti-claims.",
            "",
            "`provider_repair_bridge.json` connects provider canary evaluator failures to scoped transaction repair rows.",
            "Inspect it to follow provider output, evaluator rejection, transaction claim, replay seed, restart point, teaching rule, and blocked public claims.",
            "Provider self-attestation is recorded as evidence but never closes a transaction.",
            "",
            "`work_metabolism_bridge.json` connects this transaction fixture to the Task Ledger cap-economy projection.",
            "Inspect it to follow the public-safe path from intent fixture to cap/work item, claim/lease, mutation planning, validation, receipt, closeout, residual, and release projection update.",
            "The bridge is explicitly not event sourcing, durable execution, saga orchestration, or observability novelty by itself.",
            "",
            "`task_ledger_residual_replay_bridge.json` closes the loop back from Task Ledger provider residuals into concurrency replay seeds.",
            "Inspect it to follow an open residual work item into a transaction claim, restart point, replay command, teaching rule, and fail-closed anti-claims.",
            "The residual is input evidence only; the validator and mission transaction evaluator remain the status authority.",
            "",
            "The boundary is fail-closed: no private session state, provider route, task ledger event body, runtime claim, or hosted release claim is included.",
            "",
        ]
    )


def _preserve_leaf_entry_card(existing_text: str, next_text: str) -> str:
    begin = "<!-- BEGIN leaf_entry_card -->"
    end = "<!-- END leaf_entry_card -->"
    start = existing_text.find(begin)
    stop = existing_text.find(end)
    if start == -1 or stop == -1 or stop < start:
        return next_text
    block = existing_text[start : stop + len(end)].strip()
    return f"{next_text.rstrip()}\n\n{block}\n"


def build_concurrency_mission_control_specimen(
    root: Path,
    *,
    output_path: str = DEFAULT_OUTPUT_PATH,
    receipt_path: str = DEFAULT_RECEIPT_PATH,
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or _utc_now()
    cases = [_evaluate_case(case, generated_at) for case in FIXTURE_CASES]
    failures = [case for case in cases if case["case_status"] != "ok"]
    block_count = sum(1 for case in cases if case["evaluator_decision"]["evaluator_status"] == "block")
    accept_count = sum(1 for case in cases if case["evaluator_decision"]["evaluator_status"] == "accept")
    failure_classes = [
        failure["failure_class"]
        for case in cases
        for failure in case["evaluator_decision"]["failures"]
    ]
    repair_row_count = sum(len(case["evaluator_decision"]["repair_rows"]) for case in cases)

    required_failure_classes = {
        "write_scope_conflict",
        "duplicate_command_run",
        "dependency_not_complete",
        "stale_lease",
        "missing_receipt",
        "supervised_scope_missing_contract",
        "missing_parent_finalizer",
        "misanchored_claim",
    }
    missing_failure_classes = sorted(required_failure_classes - set(failure_classes))
    if missing_failure_classes:
        failures.append({"case_id": "mission_control.failure_coverage", "missing_failure_classes": missing_failure_classes})
    if accept_count < 1 or block_count < 8:
        failures.append({"case_id": "mission_control.status_mix", "reason": "fixture must include one accepted case and eight blocked cases"})
    source_capsule_provenance = _source_capsule_provenance(cases, output_path)
    provenance_summary = source_capsule_provenance["summary"]
    if provenance_summary["capsule_count"] != len(cases):
        failures.append({"case_id": "mission_control.source_capsules", "reason": "source capsules must cover every transaction case"})
    if provenance_summary["hashed_source_clip_count"] != len(cases):
        failures.append({"case_id": "mission_control.source_capsules", "reason": "source capsules must hash every transaction case"})
    if provenance_summary["semantic_carryforward_count"] != len(cases):
        failures.append({"case_id": "mission_control.source_capsules", "reason": "source capsules must carry forward every transaction case"})
    if provenance_summary["lane_self_status_authority_count"]:
        failures.append({"case_id": "mission_control.source_capsules", "reason": "source capsules must not promote lane self-status into authority"})

    status = "ok" if not failures else "failed"
    board = {
        "kind": "concurrency_transaction_mission_control_specimen",
        "schema_version": "concurrency_transaction_mission_control_specimen_v0",
        "generated_at": generated_at,
        "status": status,
        "candidate_id": SPECIMEN_ID,
        "authority_posture": AUTHORITY_POSTURE,
        "source_refs": [
            "strategy/open_subphases.json",
            "strategy/ledger.jsonl",
            "registry/release_candidates.json",
            "state/release_candidate_portfolio.json",
            PROVIDER_CANARY_BOARD_PATH,
            DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
            TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
            DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
        ],
        "summary": {
            "case_count": len(cases),
            "accept_count": accept_count,
            "block_count": block_count,
            "repair_row_count": repair_row_count,
            "write_scope_conflict_count": failure_classes.count("write_scope_conflict"),
            "duplicate_command_run_count": failure_classes.count("duplicate_command_run"),
            "command_key_lane_count": sum(
                1
                for case in cases
                for lane in case["lanes"]
                if isinstance(lane.get("command_key"), str) and lane["command_key"]
            ),
            "dependency_block_count": failure_classes.count("dependency_not_complete"),
            "stale_lease_count": failure_classes.count("stale_lease"),
            "missing_receipt_block_count": failure_classes.count("missing_receipt"),
            "supervised_scope_missing_contract_count": failure_classes.count("supervised_scope_missing_contract"),
            "missing_parent_finalizer_count": failure_classes.count("missing_parent_finalizer"),
            "misanchored_claim_count": failure_classes.count("misanchored_claim"),
            "parent_scope_lane_count": sum(
                1
                for case in cases
                for lane in case["lanes"]
                if isinstance(lane.get("parent_scope_id"), str) and lane["parent_scope_id"]
            ),
            "status_authority_nodes": ["mission_transaction_evaluator", "receipt_gate"],
            "lane_self_status_authority_count": 0,
            "source_capsule_count": provenance_summary["capsule_count"],
            "semantic_carryforward_count": provenance_summary["semantic_carryforward_count"],
            "hashed_source_clip_count": provenance_summary["hashed_source_clip_count"],
            "source_capsule_lane_self_status_authority_count": provenance_summary[
                "lane_self_status_authority_count"
            ],
            "source_capsule_evaluator_authority_preserved_count": provenance_summary[
                "evaluator_authority_preserved_count"
            ],
        },
        "authority_trace": [
            {
                "node_id": "lane_request",
                "authority_role": "declares requested status owner paths dependencies and receipts",
                "status_authority": False,
            },
            {
                "node_id": "mission_transaction_evaluator",
                "authority_role": "classifies owner path conflicts stale leases dependency gaps and missing receipts",
                "status_authority": True,
            },
            {
                "node_id": "receipt_gate",
                "authority_role": "records evaluator decision and boundaries",
                "status_authority": True,
            },
        ],
        "cases": cases,
        "source_capsule_provenance": source_capsule_provenance,
        "public_safety_boundary": "Synthetic mission lanes only; no private mission-control runtime, private task ledger payload, provider state, raw operator voice, or host session state is included.",
        "claim_boundary": "Fixture-level proof of transaction gating only; not a scheduler, hosted orchestration result, public release, or private-runtime equivalence claim.",
        "publication_boundary": "Publication stays blocked until disclosure, license, citation, clean-run, clone-run, and hosted gate receipts are current.",
        "anti_claims": [
            "This is not the private mission-control runtime.",
            "This is not evidence that live autonomous concurrency is production-safe.",
            "This is not a claim of public release readiness.",
        ],
        "failures": failures,
    }
    provider_repair_bridge = _provider_to_concurrency_repair_loop(
        root,
        generated_at,
        output_path=output_path,
    )
    if provider_repair_bridge["status"] != "ok":
        failures.append(
            {
                "case_id": "mission_control.provider_repair_bridge",
                "failures": provider_repair_bridge["failures"],
            }
        )
        board["status"] = "failed"
        provider_repair_bridge["status"] = "failed"
    board["provider_to_concurrency_repair_loop_ref"] = DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH
    board["provider_to_concurrency_repair_loop_summary"] = provider_repair_bridge["summary"]
    board["summary"]["provider_repair_bridge_status"] = provider_repair_bridge["status"]
    board["summary"]["provider_repair_bridge_case_count"] = provider_repair_bridge["summary"]["case_count"]
    board["summary"]["provider_repair_bridge_repair_route_count"] = provider_repair_bridge["summary"]["repair_route_count"]
    board["summary"]["provider_repair_bridge_replay_seed_count"] = provider_repair_bridge["summary"]["replay_seed_count"]
    board["summary"]["provider_repair_bridge_teaching_rule_count"] = provider_repair_bridge["summary"]["teaching_rule_count"]
    board["summary"]["provider_repair_bridge_source_capsule_count"] = provider_repair_bridge["summary"]["source_capsule_count"]
    board["summary"]["provider_repair_bridge_authority_collapse_count"] = provider_repair_bridge["summary"][
        "authority_collapse_count"
    ]
    work_metabolism_bridge = _build_work_metabolism_bridge(root, generated_at, board, provider_repair_bridge)
    if work_metabolism_bridge["status"] != "ok":
        failures.append({"case_id": "mission_control.work_metabolism_bridge", "failures": work_metabolism_bridge["failures"]})
        board["status"] = "failed"
        work_metabolism_bridge["status"] = "failed"
    board["work_metabolism_bridge_ref"] = DEFAULT_WORK_METABOLISM_BRIDGE_PATH
    board["work_metabolism_bridge_summary"] = work_metabolism_bridge["summary"]
    board["summary"]["work_metabolism_bridge_status"] = work_metabolism_bridge["status"]
    board["summary"]["work_metabolism_transaction_step_count"] = work_metabolism_bridge["summary"]["transaction_step_count"]
    board["summary"]["work_metabolism_authority_collapse_count"] = work_metabolism_bridge["summary"]["authority_collapse_count"]
    board["summary"]["next_gap_after_bridge"] = work_metabolism_bridge["summary"]["next_gap"]
    task_ledger_residual_replay_bridge = _task_ledger_residual_replay_bridge(
        root,
        generated_at,
        mission_board=board,
        work_metabolism_bridge=work_metabolism_bridge,
    )
    if task_ledger_residual_replay_bridge["status"] != "ok":
        failures.append(
            {
                "case_id": "mission_control.task_ledger_residual_replay_bridge",
                "failures": task_ledger_residual_replay_bridge["failures"],
            }
        )
        board["status"] = "failed"
        task_ledger_residual_replay_bridge["status"] = "failed"
    board["task_ledger_residual_replay_bridge_ref"] = DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH
    board["task_ledger_residual_replay_bridge_summary"] = task_ledger_residual_replay_bridge["summary"]
    board["summary"]["task_ledger_residual_replay_bridge_status"] = task_ledger_residual_replay_bridge["status"]
    board["summary"]["task_ledger_residual_replay_case_count"] = task_ledger_residual_replay_bridge["summary"][
        "case_count"
    ]
    board["summary"]["task_ledger_residual_replay_repair_route_count"] = task_ledger_residual_replay_bridge[
        "summary"
    ]["repair_route_count"]
    board["summary"]["task_ledger_residual_replay_replay_seed_count"] = task_ledger_residual_replay_bridge[
        "summary"
    ]["replay_seed_count"]
    board["summary"]["task_ledger_residual_replay_teaching_rule_count"] = task_ledger_residual_replay_bridge[
        "summary"
    ]["teaching_rule_count"]
    board["summary"]["task_ledger_residual_replay_source_capsule_count"] = task_ledger_residual_replay_bridge[
        "summary"
    ]["source_capsule_count"]
    board["summary"]["task_ledger_residual_replay_authority_collapse_count"] = task_ledger_residual_replay_bridge[
        "summary"
    ]["authority_collapse_count"]
    board["summary"]["task_ledger_residual_replay_open_count"] = task_ledger_residual_replay_bridge["summary"][
        "open_residual_replay_count"
    ]
    status = board["status"]
    _write_json(root / DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH, provider_repair_bridge)
    _write_json(root / DEFAULT_WORK_METABOLISM_BRIDGE_PATH, work_metabolism_bridge)
    _write_json(root / DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH, task_ledger_residual_replay_bridge)
    _write_json(root / output_path, board)
    readme_file = root / README_PATH
    readme_file.parent.mkdir(parents=True, exist_ok=True)
    existing_readme = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""
    readme_file.write_text(_preserve_leaf_entry_card(existing_readme, _readme()), encoding="utf-8")

    result: dict[str, Any] = {
        "kind": "concurrency_mission_control_build",
        "schema_version": "concurrency_mission_control_build_v0",
        "generated_at": generated_at,
        "status": status,
        "output": output_path,
        "case_count": len(cases),
        "accept_count": accept_count,
        "block_count": block_count,
        "repair_row_count": repair_row_count,
        "work_metabolism_bridge": DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
        "work_metabolism_bridge_status": work_metabolism_bridge["status"],
        "work_metabolism_transaction_step_count": work_metabolism_bridge["summary"]["transaction_step_count"],
        "provider_repair_bridge": DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
        "provider_repair_bridge_status": provider_repair_bridge["status"],
        "provider_repair_bridge_case_count": provider_repair_bridge["summary"]["case_count"],
        "provider_repair_bridge_repair_route_count": provider_repair_bridge["summary"]["repair_route_count"],
        "provider_repair_bridge_source_capsule_count": provider_repair_bridge["summary"]["source_capsule_count"],
        "provider_repair_bridge_teaching_rule_count": provider_repair_bridge["summary"]["teaching_rule_count"],
        "provider_repair_bridge_authority_collapse_count": provider_repair_bridge["summary"]["authority_collapse_count"],
        "task_ledger_residual_replay_bridge": DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
        "task_ledger_residual_replay_bridge_status": task_ledger_residual_replay_bridge["status"],
        "task_ledger_residual_replay_case_count": task_ledger_residual_replay_bridge["summary"]["case_count"],
        "task_ledger_residual_replay_repair_route_count": task_ledger_residual_replay_bridge["summary"][
            "repair_route_count"
        ],
        "task_ledger_residual_replay_source_capsule_count": task_ledger_residual_replay_bridge["summary"][
            "source_capsule_count"
        ],
        "task_ledger_residual_replay_teaching_rule_count": task_ledger_residual_replay_bridge["summary"][
            "teaching_rule_count"
        ],
        "task_ledger_residual_replay_authority_collapse_count": task_ledger_residual_replay_bridge["summary"][
            "authority_collapse_count"
        ],
        "authority_collapse_count": work_metabolism_bridge["summary"]["authority_collapse_count"],
        "source_capsule_count": board["summary"]["source_capsule_count"],
        "semantic_carryforward_count": board["summary"]["semantic_carryforward_count"],
        "hashed_source_clip_count": board["summary"]["hashed_source_clip_count"],
        "source_capsule_lane_self_status_authority_count": board["summary"][
            "source_capsule_lane_self_status_authority_count"
        ],
        "write_scope_conflict_count": failure_classes.count("write_scope_conflict"),
        "duplicate_command_run_count": failure_classes.count("duplicate_command_run"),
        "command_key_lane_count": board["summary"]["command_key_lane_count"],
        "dependency_block_count": failure_classes.count("dependency_not_complete"),
        "stale_lease_count": failure_classes.count("stale_lease"),
        "missing_receipt_block_count": failure_classes.count("missing_receipt"),
        "supervised_scope_missing_contract_count": failure_classes.count("supervised_scope_missing_contract"),
        "missing_parent_finalizer_count": failure_classes.count("missing_parent_finalizer"),
        "misanchored_claim_count": failure_classes.count("misanchored_claim"),
        "parent_scope_lane_count": board["summary"]["parent_scope_lane_count"],
        "failure_count": len(failures),
        "failures": failures,
    }
    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.concurrency_mission_control",
            "generated_at": generated_at,
            "owner": "idea_microcosm.concurrency_mission_control_specimen",
            "claim_ref": f"candidate.{SPECIMEN_ID}",
            "claim_tier": "fixture_validated",
            "command": "python -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "result": status,
            "status": status,
            "evidence_refs": [
                output_path,
                f"{output_path}:source_capsule_provenance",
                DEFAULT_WORK_METABOLISM_BRIDGE_PATH,
                DEFAULT_PROVIDER_REPAIR_BRIDGE_PATH,
                DEFAULT_TASK_LEDGER_RESIDUAL_REPLAY_BRIDGE_PATH,
                PROVIDER_CANARY_BOARD_PATH,
                PROVIDER_CANARY_RECEIPT_PATH,
                README_PATH,
                TASK_LEDGER_EVENTS_PATH,
                TASK_LEDGER_PROJECTION_PATH,
                TASK_LEDGER_RECEIPT_PATH,
                TASK_LEDGER_PROVIDER_RESIDUAL_BRIDGE_PATH,
                "registry/release_candidates.json",
                "src/idea_microcosm/concurrency_mission_control_specimen.py",
                "src/idea_microcosm/validators.py",
                "skills/cold_start_agent.md",
            ],
            "omissions": [
                "This receipt validates a synthetic transaction fixture only; it does not expose private mission-control state or assert hosted orchestration readiness.",
                "The work-metabolism bridge consumes public-safe fixture projections only; it does not expose private Task Ledger or Work Ledger rows.",
                "The provider repair bridge consumes the synthetic provider canary board only; it does not expose real provider transcripts, hosted evaluation traces, or production concurrency repair evidence.",
                "The residual replay bridge consumes the public-safe Task Ledger provider residual bridge only; it does not expose private Task Ledger or Work Ledger row bodies.",
                "Lane requests are fixture rows. The evaluator and receipt gate are the only status authority in this specimen.",
            ],
            "summary": board["summary"],
        }
        _write_json(root / receipt_path, receipt)
        result["receipt_written"] = receipt_path
    return result
