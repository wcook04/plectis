#!/usr/bin/env python3
"""Build the one-row formal-math proof-repair lane contract.

This is the narrow lane after the proofline spine reaches proof-level Lean
rejection. It binds the selected failed specimen and all required evidence refs
for a future one-row repair attempt, but it does not dispatch a provider or
claim theorem success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import generated_projection_registry
from tools.meta.factory import build_formal_math_proofline_spine as proofline


INPUT_SCHEMA_VERSION = "formal_math_proof_repair_input_packet_v0"
RECEIPT_SCHEMA_VERSION = "formal_math_proof_repair_lane_receipt_v0"
CHECK_SCHEMA_VERSION = "formal_math_proof_repair_lane_check_v0"
OWNER_ID = "formal_math_proof_repair_lane_projection"
PRIMARY_OWNER = proofline.PRIMARY_OWNER
REPAIR_WORK_ITEM_ID = "cap_quick_formal_math_proof_repair_residual_eval_e_75029451f405"
DEFAULT_RUN_ID = proofline.DEFAULT_RUN_ID
RUN_ROOT = proofline.MICROCOSM_ROOT / f"run_{DEFAULT_RUN_ID}"
INPUT_PACKET_NAME = "proof_repair_input_packet.json"
RECEIPT_NAME = "proof_repair_receipt.json"
CLAIM_BOUNDARY = "private_proof_repair_lane_not_public_benchmark_result"
LANE_NOT_READY_STATUS = "proof_repair_lane_not_ready_contract_landed"
LANE_READY_STATUS = "proof_repair_lane_ready_contract_landed"
LANE_ATTEMPT_COMPLETED_STATUS = "proof_repair_lane_attempt_completed_with_receipt"
PROOF_REPAIR_TERMINAL_STATUSES = [
    "proof_repair_lean_accepted",
    "proof_repair_lean_rejected_with_receipt",
    "proof_repair_provider_schema_failed",
    "proof_repair_provider_unavailable",
    "proof_repair_blocked_no_trickle_or_credentials",
    "proof_repair_blocked_prompt_boundary",
    "proof_repair_timeout",
]

FORBIDDEN_INLINE_KEYS = {
    "answer",
    "candidate_body",
    "decision_point_plan",
    "formal_answer",
    "ground_truth_proof",
    "ideal_body",
    "lean_proof_body",
    "model_facing_payload",
    "prompt",
    "prompt_body",
    "prompt_messages",
    "provider_output",
    "repair_body",
    "retrieval_body",
    "solution",
    "source_proof_body",
}


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _run_root(run_id: str) -> Path:
    return proofline.MICROCOSM_ROOT / f"run_{run_id}"


def _input_packet_path(run_id: str) -> Path:
    return _run_root(run_id) / INPUT_PACKET_NAME


def _receipt_path(run_id: str) -> Path:
    return _run_root(run_id) / RECEIPT_NAME


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nested_keys(payload: object) -> set[str]:
    if isinstance(payload, Mapping):
        keys = {str(key) for key in payload}
        for value in payload.values():
            keys.update(_nested_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for value in payload:
            keys.update(_nested_keys(value))
        return keys
    return set()


def _forbidden_keys_present(payload: object) -> list[str]:
    return sorted(_nested_keys(payload).intersection(FORBIDDEN_INLINE_KEYS))


def _artifact_ref(path: str | Path | None, *, repo_root: Path, must_exist: bool = True) -> dict[str, Any]:
    ref = str(path or "")
    candidate = _repo_path(ref, repo_root=repo_root) if ref else Path("")
    exists = bool(ref) and candidate.exists()
    row: dict[str, Any] = {
        "ref": _rel(candidate, repo_root=repo_root) if ref else None,
        "exists": exists,
        "must_exist": must_exist,
    }
    if exists and candidate.is_file():
        row["sha256"] = _sha256_file(candidate)
    return row


def _load_work_item(work_item_id: str, *, repo_root: Path) -> dict[str, Any]:
    ledger_path = _repo_path("state/task_ledger/ledger.json", repo_root=repo_root)
    if not ledger_path.exists():
        return {}
    ledger = _read_json(ledger_path)
    for row in ledger.get("work_items") or []:
        if isinstance(row, Mapping) and row.get("id") == work_item_id:
            return dict(row)
    return {}


def _work_item_readiness(work_item: Mapping[str, Any]) -> dict[str, Any]:
    missing = list(work_item.get("missing_contracts") or [])
    projection = work_item.get("projection_completeness")
    if isinstance(projection, Mapping) and projection.get("has_satisfaction_contract") is False:
        if "satisfaction_contract" not in missing:
            missing.append("satisfaction_contract")
    state = str(work_item.get("state") or "unknown")
    lane_ready = not missing and state not in {"captured", "unknown"}
    return {
        "work_item_id": REPAIR_WORK_ITEM_ID,
        "state": state,
        "triage_status": work_item.get("triage_status"),
        "missing_contracts": sorted(set(str(item) for item in missing)),
        "lane_ready": lane_ready,
        "readiness": "owner_native_lane_ready" if lane_ready else "captured_missing_satisfaction_contract",
    }


def _adapter_artifacts(
    *,
    adapter_receipt: Mapping[str, Any],
    env_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = env_receipt.get("adapter_artifacts")
    if isinstance(artifacts, Mapping):
        return dict(artifacts)
    row = (
        adapter_receipt.get("provider_dispatch", {}).get("row", {})
        if isinstance(adapter_receipt.get("provider_dispatch"), Mapping)
        else {}
    )
    transform_job = adapter_receipt.get("transform_job")
    if not isinstance(transform_job, Mapping):
        transform_job = {}
    return {
        "adapter_receipt_ref": _rel(RUN_ROOT / "oracle_ingress_adapter_receipt.json"),
        "formal_problem_resolution_receipt_ref": _rel(RUN_ROOT / "formal_problem_resolution_receipt.json"),
        "provider_receipt_id": row.get("provider_receipt_id"),
        "provider_receipt_ref": row.get("provider_receipt_ref"),
        "row_patch_ref": row.get("row_patch_ref"),
        "transform_job_ref": row.get("transform_job_ref") or transform_job.get("transform_job_ref"),
    }


def _env_result(env_receipt: Mapping[str, Any]) -> dict[str, Any]:
    same = env_receipt.get("same_candidate_reduce_existing")
    if not isinstance(same, Mapping):
        return {}
    result = same.get("result")
    return dict(result) if isinstance(result, Mapping) else {}


def _selected_candidate(
    *,
    proofline_spine: Mapping[str, Any],
    env_receipt: Mapping[str, Any],
    adapter_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    selected = env_receipt.get("selected_candidate") or adapter_receipt.get("selected_candidate") or {}
    row = dict(selected) if isinstance(selected, Mapping) else {}
    if not row.get("task_id"):
        current_state = proofline_spine.get("current_state")
        if isinstance(current_state, Mapping):
            row["task_id"] = current_state.get("best_specimen")
    return row


def _refs_exist(refs: Mapping[str, Mapping[str, Any]]) -> bool:
    return all(row.get("exists") for row in refs.values() if row.get("must_exist", True))


def build_input_packet(*, run_id: str = DEFAULT_RUN_ID, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    run_root = _repo_path(_run_root(run_id), repo_root=repo_root)
    proofline_spine = _read_json(_repo_path(proofline.SPINE_PATH, repo_root=repo_root))
    adapter_receipt = _read_json(run_root / "oracle_ingress_adapter_receipt.json")
    env_receipt = _read_json(run_root / "oracle_environment_gate_receipt.json")
    repair_work_item = _load_work_item(REPAIR_WORK_ITEM_ID, repo_root=repo_root)

    next_action = proofline_spine.get("next_action") if isinstance(proofline_spine.get("next_action"), Mapping) else {}
    facets = proofline_spine.get("facets") if isinstance(proofline_spine.get("facets"), Mapping) else {}
    proof_repair_attempt_facet = (
        facets.get("proof_repair_attempt_facet")
        if isinstance(facets.get("proof_repair_attempt_facet"), Mapping)
        else {}
    )
    support_affordance_facet = (
        facets.get("support_affordance_finder_facet")
        if isinstance(facets.get("support_affordance_finder_facet"), Mapping)
        else {}
    )
    current_state = proofline_spine.get("current_state") if isinstance(proofline_spine.get("current_state"), Mapping) else {}
    artifacts = _adapter_artifacts(adapter_receipt=adapter_receipt, env_receipt=env_receipt)
    env_fields = (
        env_receipt.get("selected_candidate_environment_fields")
        if isinstance(env_receipt.get("selected_candidate_environment_fields"), Mapping)
        else {}
    )
    workspace = env_receipt.get("workspace") if isinstance(env_receipt.get("workspace"), Mapping) else {}
    env_result = _env_result(env_receipt)
    adapter_reducer = adapter_receipt.get("reducer") if isinstance(adapter_receipt.get("reducer"), Mapping) else {}
    latest_reduction = (
        adapter_reducer.get("latest_reduction")
        if isinstance(adapter_reducer.get("latest_reduction"), Mapping)
        else {}
    )
    readiness = _work_item_readiness(repair_work_item)

    failed_stdout_ref = env_result.get("stdout_ref")
    failed_stderr_ref = (
        next_action.get("input_refs", {}).get("failed_lean_output_ref")
        if isinstance(next_action.get("input_refs"), Mapping)
        else None
    ) or env_result.get("stderr_ref")
    input_refs = {
        "proofline_spine_ref": _artifact_ref(proofline.SPINE_PATH, repo_root=repo_root),
        "proofline_receipt_ref": _artifact_ref(proofline.RECEIPT_PATH, repo_root=repo_root),
        "adapter_receipt_ref": _artifact_ref(
            artifacts.get("adapter_receipt_ref") or run_root / "oracle_ingress_adapter_receipt.json",
            repo_root=repo_root,
        ),
        "environment_gate_receipt_ref": _artifact_ref(
            run_root / "oracle_environment_gate_receipt.json",
            repo_root=repo_root,
        ),
        "formal_problem_transform_job_ref": _artifact_ref(artifacts.get("transform_job_ref"), repo_root=repo_root),
        "current_failed_hypothesis_row_patch_ref": _artifact_ref(artifacts.get("row_patch_ref"), repo_root=repo_root),
        "current_provider_receipt_ref": _artifact_ref(artifacts.get("provider_receipt_ref"), repo_root=repo_root),
        "failed_lean_stdout_ref": _artifact_ref(failed_stdout_ref, repo_root=repo_root),
        "failed_lean_stderr_ref": _artifact_ref(failed_stderr_ref, repo_root=repo_root),
        "adapter_lean_check_result_ref": _artifact_ref(latest_reduction.get("lean_check_result"), repo_root=repo_root),
        "adapter_reduction_report_ref": _artifact_ref(latest_reduction.get("receipt_reduction_report"), repo_root=repo_root),
        "proof_repair_attempt_receipt_ref": _artifact_ref(
            run_root / "proof_repair_attempt_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "proof_repair_attempt_evaluator_result_ref": _artifact_ref(
            str(next_action.get("evaluator_result_ref") or ""),
            repo_root=repo_root,
            must_exist=bool(next_action.get("evaluator_result_ref")),
        ),
        "support_affordance_finder_receipt_ref": _artifact_ref(
            run_root / "formal_support_affordance_finder/affordance_finder_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "support_affordance_declaration_index_ref": _artifact_ref(
            run_root / "formal_support_affordance_finder/local_declaration_index.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "support_affordance_tactic_probe_manifest_ref": _artifact_ref(
            run_root / "formal_support_affordance_finder/tactic_probe_manifest.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "strategy_context_source_ref": _artifact_ref(
            _run_root(run_id) / "decision_point_traces.jsonl",
            repo_root=repo_root,
        ),
    }

    packet = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "run_id": run_id,
        "proofline_id": proofline_spine.get("proofline_id"),
        "work_item_id": PRIMARY_OWNER,
        "repair_work_item_id": REPAIR_WORK_ITEM_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "benchmark_claims_allowed": False,
        "candidate": _selected_candidate(
            proofline_spine=proofline_spine,
            env_receipt=env_receipt,
            adapter_receipt=adapter_receipt,
        ),
        "current_state": {
            "state": current_state.get("state"),
            "active_bottleneck": current_state.get("active_bottleneck"),
        },
        "environment": {
            "source_repo": env_fields.get("source_repo"),
            "source_commit": env_fields.get("source_commit"),
            "lean_toolchain": env_fields.get("lean_toolchain"),
            "required_imports": env_fields.get("required_imports") or [],
            "workspace_ref": workspace.get("workspace_root"),
            "workspace_ref_type": "external_run_local_workspace_not_repo_artifact",
        },
        "input_refs": input_refs,
        "input_ref_digest": _sha256_json(input_refs),
        "failed_judgment": {
            "adapter_error_class": latest_reduction.get("error_class"),
            "environment_compile_status": env_result.get("compile_status"),
            "accepted_by_lean": env_result.get("accepted_by_lean"),
            "unknown_module_prefix": env_result.get("unknown_module_prefix"),
            "proof_level": env_receipt.get("lean_rejection_is_proof_level"),
        },
        "support_affordance_finder": {
            "status": support_affordance_facet.get("status") or "not_run",
            "accessible_declaration_count": support_affordance_facet.get("accessible_declaration_count"),
            "matched_declaration_count": support_affordance_facet.get("matched_declaration_count"),
            "direct_local_acceptance": support_affordance_facet.get("direct_local_acceptance"),
            "recommended_next_action": support_affordance_facet.get("recommended_next_action"),
            "receipt_ref": input_refs["support_affordance_finder_receipt_ref"]["ref"],
            "declaration_index_ref": input_refs["support_affordance_declaration_index_ref"]["ref"],
            "tactic_probe_manifest_ref": input_refs["support_affordance_tactic_probe_manifest_ref"]["ref"],
        },
        "prior_repair_attempt": {
            "status": proof_repair_attempt_facet.get("status") or "not_run",
            "provider_dispatch_attempted": proof_repair_attempt_facet.get("provider_dispatch_attempted"),
            "provider_status": proof_repair_attempt_facet.get("provider_status"),
            "model_id": proof_repair_attempt_facet.get("model_id"),
            "evaluator_status": proof_repair_attempt_facet.get("evaluator_status"),
            "accepted_by_lean": proof_repair_attempt_facet.get("accepted_by_lean"),
            "latest_failure_class": proof_repair_attempt_facet.get("latest_failure_class"),
            "missing_identifier": proof_repair_attempt_facet.get("missing_identifier"),
            "attempt_receipt_ref": input_refs["proof_repair_attempt_receipt_ref"]["ref"],
            "evaluator_result_ref": next_action.get("evaluator_result_ref"),
        },
        "proofline_next_action": next_action,
        "provider_repair_request_contract": {
            "attempt_count": 1,
            "candidate_locked": True,
            "provider_retry_requires_new_strategy_after_terminal_attempt": True,
            "materialize_body_at_dispatch_from_refs": True,
            "current_failed_hypothesis_body_ref": input_refs["current_failed_hypothesis_row_patch_ref"]["ref"],
            "failed_lean_output_refs": [
                input_refs["failed_lean_stdout_ref"]["ref"],
                input_refs["failed_lean_stderr_ref"]["ref"],
            ],
            "strategy_context_source_ref": input_refs["strategy_context_source_ref"]["ref"],
            "response_contract": {
                "format": "json_object",
                "required_fields": [
                    "lean_proof_body",
                    "repaired_lean_proof_body",
                    "repair_rationale",
                    "expected_failure_modes",
                    "dependencies_used",
                    "premise_ids_used",
                    "notes",
                    "confidence",
                    "omissions",
                ],
                "success_requires_reducer": True,
            },
            "allowed_statuses": list(PROOF_REPAIR_TERMINAL_STATUSES),
            "forbidden_anti_patterns": [
                "target_theorem_self_reference",
                "invented_unavailable_identifier",
                "provider_text_without_Lean_reducer_receipt",
            ],
            "satisfaction_requires": [
                "support_affordance_finder_receipt_before_any_new_provider_retry",
                "live_trickle_nim_inventory_or_provider_unavailable_receipt",
                "strict_json_canary_receipt",
                "one_repair_invocation_receipt_when_canary_passes",
                "arklib_lake_env_lean_reducer_result_when_provider_schema_passes",
            ],
        },
        "dispatch_policy": {
            "provider_dispatch_allowed_now": bool(readiness["lane_ready"])
            and proof_repair_attempt_facet.get("status") not in PROOF_REPAIR_TERMINAL_STATUSES,
            "provider_dispatch_performed_by_this_builder": False,
            "lean_reducer_invoked_by_this_builder": False,
            "reason": (
                "owner-native repair WorkItem must carry satisfaction contract before dispatch"
                if not readiness["lane_ready"]
                else "one terminal repair attempt already has an evaluator receipt; require a new strategy before retry"
                if proof_repair_attempt_facet.get("status") in PROOF_REPAIR_TERMINAL_STATUSES
                else "repair lane contract is ready; dispatch remains an explicit next action"
            ),
        },
        "owner_readiness": readiness,
        "leakage_guard": {
            "truth_side_material_forbidden": True,
            "ground_truth_proof_visible": False,
            "inline_body_policy": "refs_hashes_and_contract_only_no_provider_or_proof_body_inline",
            "forbidden_inline_keys": sorted(FORBIDDEN_INLINE_KEYS),
        },
    }
    packet["leakage_guard"]["forbidden_inline_keys_present"] = _forbidden_keys_present(packet)
    return packet


def validate_input_packet(packet: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if packet.get("schema_version") != INPUT_SCHEMA_VERSION:
        issues.append("input packet schema mismatch")
    if packet.get("claim_boundary") != CLAIM_BOUNDARY:
        issues.append("claim boundary mismatch")
    if packet.get("benchmark_claims_allowed") is not False:
        issues.append("benchmark_claims_allowed must be false")
    current_state = packet.get("current_state") if isinstance(packet.get("current_state"), Mapping) else {}
    if current_state.get("state") != proofline.CURRENT_STATE:
        issues.append("current_state must remain proof_level_rejected")
    if current_state.get("active_bottleneck") != proofline.ACTIVE_BOTTLENECK:
        issues.append("active_bottleneck must remain proof_synthesis_or_repair_quality")
    candidate = packet.get("candidate") if isinstance(packet.get("candidate"), Mapping) else {}
    if candidate.get("task_id") != "verisoftbench:2":
        issues.append("repair candidate must be verisoftbench:2")
    input_refs = packet.get("input_refs") if isinstance(packet.get("input_refs"), Mapping) else {}
    if not input_refs:
        issues.append("input_refs must be present")
    else:
        for name, row in input_refs.items():
            if not isinstance(row, Mapping):
                issues.append(f"input ref {name} must be an object")
                continue
            if row.get("must_exist", True) and not row.get("exists"):
                issues.append(f"missing input ref: {name} -> {row.get('ref')}")
    if _forbidden_keys_present(packet):
        issues.append(f"forbidden inline body-like keys present: {_forbidden_keys_present(packet)}")
    dispatch = packet.get("dispatch_policy") if isinstance(packet.get("dispatch_policy"), Mapping) else {}
    if dispatch.get("provider_dispatch_performed_by_this_builder") is not False:
        issues.append("builder must not dispatch provider")
    if dispatch.get("lean_reducer_invoked_by_this_builder") is not False:
        issues.append("builder must not invoke reducer")
    return issues


def build_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    issues = validate_input_packet(packet)
    readiness = packet.get("owner_readiness") if isinstance(packet.get("owner_readiness"), Mapping) else {}
    lane_ready = bool(readiness.get("lane_ready"))
    prior_attempt = packet.get("prior_repair_attempt") if isinstance(packet.get("prior_repair_attempt"), Mapping) else {}
    attempt_status = str(prior_attempt.get("status") or "not_run")
    attempt_completed = attempt_status in PROOF_REPAIR_TERMINAL_STATUSES
    proofline_next_action = (
        packet.get("proofline_next_action") if isinstance(packet.get("proofline_next_action"), Mapping) else {}
    )
    if issues:
        status = "FAIL"
    elif attempt_completed:
        status = LANE_ATTEMPT_COMPLETED_STATUS
    elif lane_ready:
        status = LANE_READY_STATUS
    else:
        status = LANE_NOT_READY_STATUS
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": status,
        "issues": issues,
        "projection_owner_id": OWNER_ID,
        "input_packet_ref": _rel(_input_packet_path(str(packet.get("run_id") or DEFAULT_RUN_ID))),
        "receipt_ref": _rel(_receipt_path(str(packet.get("run_id") or DEFAULT_RUN_ID))),
        "work_item_id": packet.get("work_item_id"),
        "repair_work_item_id": packet.get("repair_work_item_id"),
        "claim_boundary": packet.get("claim_boundary"),
        "benchmark_claims_allowed": packet.get("benchmark_claims_allowed"),
        "candidate": packet.get("candidate"),
        "current_state": packet.get("current_state"),
        "failed_judgment": packet.get("failed_judgment"),
        "owner_readiness": readiness,
        "proof_repair_attempt": {
            "status": attempt_status,
            "provider_dispatch_performed": bool(prior_attempt.get("provider_dispatch_attempted")),
            "lean_reducer_invoked": prior_attempt.get("evaluator_status") is not None,
            "accepted_by_lean": prior_attempt.get("accepted_by_lean"),
            "latest_failure_class": prior_attempt.get("latest_failure_class"),
            "missing_identifier": prior_attempt.get("missing_identifier"),
            "reason": (
                "terminal_attempt_recorded_require_new_strategy_before_retry"
                if attempt_completed
                else "contract_landing_only"
            ),
        },
        "support_affordance_finder": packet.get("support_affordance_finder"),
        "next_action": proofline_next_action
        if attempt_completed and proofline_next_action
        else {
            "action_type": "shape_repair_workitem_or_run_one_row_repair_once_contract_ready",
            "candidate": (packet.get("candidate") or {}).get("task_id")
            if isinstance(packet.get("candidate"), Mapping)
            else None,
            "allowed_statuses": (
                (packet.get("provider_repair_request_contract") or {}).get("allowed_statuses")
                if isinstance(packet.get("provider_repair_request_contract"), Mapping)
                else []
            ),
        },
        "leakage_guard": packet.get("leakage_guard"),
    }


def write_outputs(*, run_id: str = DEFAULT_RUN_ID, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    packet = build_input_packet(run_id=run_id, repo_root=repo_root)
    receipt = build_receipt(packet)
    _write_json(_repo_path(_input_packet_path(run_id), repo_root=repo_root), packet)
    _write_json(_repo_path(_receipt_path(run_id), repo_root=repo_root), receipt)
    return receipt


def check_outputs(*, run_id: str = DEFAULT_RUN_ID, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    expected_packet = build_input_packet(run_id=run_id, repo_root=repo_root)
    expected_receipt = build_receipt(expected_packet)
    packet_path = _repo_path(_input_packet_path(run_id), repo_root=repo_root)
    receipt_path = _repo_path(_receipt_path(run_id), repo_root=repo_root)
    issues: list[str] = []
    if not packet_path.exists():
        issues.append(f"missing {_input_packet_path(run_id)}")
    else:
        actual_packet = _read_json(packet_path)
        issues.extend(f"actual input packet invalid: {issue}" for issue in validate_input_packet(actual_packet))
        if actual_packet != expected_packet:
            issues.append(f"{_input_packet_path(run_id)} is stale")
    if not receipt_path.exists():
        issues.append(f"missing {_receipt_path(run_id)}")
    else:
        actual_receipt = _read_json(receipt_path)
        if actual_receipt != expected_receipt:
            issues.append(f"{_receipt_path(run_id)} is stale")
    try:
        owner = generated_projection_registry.get_projection_owner(OWNER_ID)
    except KeyError:
        issues.append(f"generated projection owner {OWNER_ID} is not registered")
    else:
        artifacts = set(owner.artifacts)
        if str(_input_packet_path(DEFAULT_RUN_ID)) not in artifacts or str(_receipt_path(DEFAULT_RUN_ID)) not in artifacts:
            issues.append("generated projection owner does not cover proof repair outputs")
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "input_packet_ref": str(_input_packet_path(run_id)),
        "receipt_ref": str(_receipt_path(run_id)),
        "lane_status": expected_receipt.get("status"),
        "candidate": (expected_packet.get("candidate") or {}).get("task_id")
        if isinstance(expected_packet.get("candidate"), Mapping)
        else None,
        "owner_readiness": expected_packet.get("owner_readiness"),
        "provider_dispatch_performed": (
            (expected_receipt.get("proof_repair_attempt") or {}).get("provider_dispatch_performed")
            if isinstance(expected_receipt.get("proof_repair_attempt"), Mapping)
            else False
        ),
        "lean_reducer_invoked": (
            (expected_receipt.get("proof_repair_attempt") or {}).get("lean_reducer_invoked")
            if isinstance(expected_receipt.get("proof_repair_attempt"), Mapping)
            else False
        ),
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root)
    if args.check:
        result = check_outputs(run_id=args.run_id, repo_root=repo_root)
    else:
        result = write_outputs(run_id=args.run_id, repo_root=repo_root)
    if args.json or args.check:
        print(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "status": result.get("status"),
                    "input_packet_ref": str(_input_packet_path(args.run_id)),
                    "receipt_ref": str(_receipt_path(args.run_id)),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    return 0 if result.get("status") == "PASS" or str(result.get("status", "")).startswith("proof_repair_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
