#!/usr/bin/env python3
"""Build the formal-math Lab-to-Oracle proofline spine.

The spine is a generated, body-safe lineage object over the private formal-math
receipts. It makes the current control-plane truth derivable from one JSON
contract without copying provider outputs, prompt payloads, Lean proof bodies,
ground-truth proofs, or hidden answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import generated_projection_registry


SCHEMA_VERSION = "formal_math_proofline_spine_v0"
RECEIPT_SCHEMA_VERSION = "formal_math_proofline_spine_receipt_v0"
CHECK_SCHEMA_VERSION = "formal_math_proofline_spine_check_v0"
OWNER_ID = "formal_math_proofline_spine_projection"
PRIMARY_OWNER = "cap_formal_math_decision_point_microcosm_v0"
DEFAULT_RUN_ID = "initial_failure_score_20260512T195745Z"
MICROCOSM_ROOT = Path("state/benchmarks/formal_math_decision_point_microcosm_v0")
SPINE_PATH = MICROCOSM_ROOT / "proofline_spine.json"
RECEIPT_PATH = MICROCOSM_ROOT / "proofline_spine_receipt.json"
RESIDUAL_INDEX_PATH = Path("state/prover/residual_corpus_index.json")
RESIDUAL_RECEIPT_PATH = Path("state/prover/residual_corpus_index_receipt.json")
CLAIM_BOUNDARY = "private_lab_oracle_lineage_not_public_benchmark_result"
CURRENT_STATE = "proof_level_rejected"
ACTIVE_BOTTLENECK = "proof_synthesis_or_repair_quality"

REQUIRED_COMMITS = {
    "provider_smoke_repair": "673c27209283940d52d40cbfa8305fce7de7d525",
    "thirty_packet_lab_baseline": "4df5eb468961695bed550060112ce412d27624d6",
    "oracle_contract_microgate": "80aa59a652e6e6645276f1d755e5b47b1442d208",
    "proof_hypothesis_adapter": "95248cdd9c4ca10c93ae76cea8906425e2df76cb",
    "environment_gate": "67c69f54026d36c97d9834ab100306f4a7b90bb2",
    "environment_gate_task_ledger_intake": "3f5610d14291012819f9ec995956d3757f9f709f",
}

FORBIDDEN_BODY_KEYS = {
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
    return MICROCOSM_ROOT / f"run_{run_id}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object row at {path}:{line_number}")
        rows.append(payload)
    return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    text = value if isinstance(value, str) else _canonical_json(value)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    return sorted(_nested_keys(payload).intersection(FORBIDDEN_BODY_KEYS))


def _counter(values: Sequence[Any]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _git_in_history(commit: str, *, repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _artifact_ref(path: str | Path, *, repo_root: Path, must_exist: bool = True) -> dict[str, Any]:
    candidate = _repo_path(path, repo_root=repo_root)
    return {
        "ref": _rel(candidate, repo_root=repo_root),
        "exists": candidate.exists(),
        "must_exist": must_exist,
    }


def _count_baseline(traces: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    provider_status_counts = _counter([row.get("provider_status") or "unknown" for row in traces])
    schema_counts = _counter([row.get("output_schema_valid") for row in traces])
    schema_valid_count = sum(1 for row in traces if row.get("output_schema_valid") is True)
    timeout_count = provider_status_counts.get("timeout", 0)
    provider_ok_count = provider_status_counts.get("ok", 0)
    return {
        "trace_count": len(traces),
        "provider_status_counts": provider_status_counts,
        "output_schema_valid_counts": schema_counts,
        "provider_ok_count": provider_ok_count,
        "schema_valid_count": schema_valid_count,
        "timeout_count": timeout_count,
        "classification": (
            f"mostly_passed_{schema_valid_count}_schema_valid_{timeout_count}_timeout"
            if provider_ok_count and timeout_count
            else "passed"
            if provider_ok_count == len(traces) and schema_valid_count == len(traces)
            else "incomplete"
        ),
    }


def _timeout_residuals(traces: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in traces:
        if row.get("provider_status") != "timeout":
            continue
        rows.append(
            {
                "residual_type": "provider_timeout_retained",
                "task_id": row.get("task_id"),
                "trace_id": row.get("trace_id"),
                "provider_job_id": row.get("provider_job_id"),
                "provider_status": row.get("provider_status"),
                "owner": PRIMARY_OWNER,
            }
        )
    return rows


def _proof_repair_failure_class(
    proof_repair_evaluator: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    result_ref = str(proof_repair_evaluator.get("result_ref") or "")
    if not result_ref:
        return {"class": "not_available"}
    reduction = _read_json_if_exists(_repo_path(result_ref, repo_root=repo_root))
    snippets: list[str] = []
    for key in ("stdout_ref", "stderr_ref"):
        ref = str(reduction.get(key) or "")
        if not ref:
            continue
        path = _repo_path(ref, repo_root=repo_root)
        if path.exists():
            snippets.append(path.read_text(encoding="utf-8")[:4000])
    text = "\n".join(snippets)
    lowered = text.lower()
    if "unknown identifier" in lowered:
        missing_identifier = None
        marker = "unknown identifier '"
        if marker in text:
            tail = text.split(marker, 1)[1]
            missing_identifier = tail.split("'", 1)[0]
        return {
            "class": "invented_or_unavailable_identifier",
            "missing_identifier": missing_identifier,
            "evaluator_result_ref": result_ref,
        }
    if "exact" in lowered and "type mismatch" in lowered:
        return {"class": "strategy_type_mismatch", "evaluator_result_ref": result_ref}
    return {"class": "lean_rejected_after_repair_attempt", "evaluator_result_ref": result_ref}


def _selected_candidate(adapter_receipt: Mapping[str, Any], env_receipt: Mapping[str, Any]) -> dict[str, Any]:
    selected = env_receipt.get("selected_candidate") or adapter_receipt.get("selected_candidate") or {}
    return dict(selected) if isinstance(selected, Mapping) else {}


def _adapter_refs(adapter_receipt: Mapping[str, Any], env_receipt: Mapping[str, Any]) -> dict[str, Any]:
    adapter_artifacts = env_receipt.get("adapter_artifacts")
    if isinstance(adapter_artifacts, Mapping):
        return dict(adapter_artifacts)
    row = (
        adapter_receipt.get("provider_dispatch", {}).get("row", {})
        if isinstance(adapter_receipt.get("provider_dispatch"), Mapping)
        else {}
    )
    transform_job = adapter_receipt.get("transform_job") if isinstance(adapter_receipt.get("transform_job"), Mapping) else {}
    return {
        "provider_receipt_id": row.get("provider_receipt_id"),
        "provider_receipt_ref": row.get("provider_receipt_ref"),
        "row_patch_ref": row.get("row_patch_ref"),
        "transform_job_ref": row.get("transform_job_ref") or transform_job.get("transform_job_ref"),
    }


def _lineage_edges() -> list[dict[str, str]]:
    return [
        {"from": "provider_smoke_repair", "to": "thirty_packet_lab_baseline", "relationship": "enabled"},
        {"from": "thirty_packet_lab_baseline", "to": "residual_corpus_refresh", "relationship": "emitted"},
        {"from": "thirty_packet_lab_baseline", "to": "oracle_ingress_selection", "relationship": "sampled"},
        {"from": "oracle_ingress_selection", "to": "oracle_ingress_contract_microgate", "relationship": "gated"},
        {"from": "oracle_ingress_contract_microgate", "to": "formal_problem_resolution", "relationship": "required_adapter"},
        {"from": "formal_problem_resolution", "to": "proof_hypothesis_adapter", "relationship": "provided_formal_problem"},
        {"from": "proof_hypothesis_adapter", "to": "environment_gate", "relationship": "provided_proof_hypothesis_receipt"},
        {"from": "environment_gate", "to": "lean_reducer_judgment", "relationship": "classified"},
        {"from": "lean_reducer_judgment", "to": "proof_repair_or_candidate_selection_next", "relationship": "unblocks_next_action"},
    ]


def _activity(
    *,
    activity_id: str,
    activity_type: str,
    status: str,
    source_receipt_ref: str | None = None,
    commit_ref: str | None = None,
    input_entity_refs: Sequence[str] = (),
    output_entity_refs: Sequence[str] = (),
    claim_boundary: str = CLAIM_BOUNDARY,
) -> dict[str, Any]:
    return {
        "activity_id": activity_id,
        "activity_type": activity_type,
        "status": status,
        "source_receipt_ref": source_receipt_ref,
        "commit_ref": commit_ref,
        "input_entity_refs": list(input_entity_refs),
        "output_entity_refs": list(output_entity_refs),
        "claim_boundary": claim_boundary,
    }


def build_spine(*, run_id: str = DEFAULT_RUN_ID, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    run_root = _repo_path(_run_root(run_id), repo_root=repo_root)
    latest = _read_json(_repo_path(MICROCOSM_ROOT / "latest.json", repo_root=repo_root))
    failure_receipt = _read_json(run_root / "failure_score_receipt.json")
    traces = _read_jsonl(run_root / "decision_point_traces.jsonl")
    residual_receipt = _read_json(_repo_path(RESIDUAL_RECEIPT_PATH, repo_root=repo_root))
    residual_index = _read_json(_repo_path(RESIDUAL_INDEX_PATH, repo_root=repo_root))
    selection_receipt = _read_json(run_root / "oracle_ingress_selection_receipt.json")
    microgate_receipt = _read_json_if_exists(run_root / "oracle_ingress_microgate_receipt.json")
    formal_problem_resolution = _read_json(run_root / "formal_problem_resolution_receipt.json")
    adapter_receipt = _read_json(run_root / "oracle_ingress_adapter_receipt.json")
    env_receipt = _read_json(run_root / "oracle_environment_gate_receipt.json")
    proof_repair_attempt_receipt = _read_json_if_exists(run_root / "proof_repair_attempt_receipt.json")
    support_affordance_root = run_root / "formal_support_affordance_finder"
    support_affordance_receipt = _read_json_if_exists(support_affordance_root / "affordance_finder_receipt.json")

    baseline = _count_baseline(traces)
    selected_candidate = _selected_candidate(adapter_receipt, env_receipt)
    adapter_refs = _adapter_refs(adapter_receipt, env_receipt)
    reducer = adapter_receipt.get("reducer") if isinstance(adapter_receipt.get("reducer"), Mapping) else {}
    latest_reduction = (
        reducer.get("latest_reduction") if isinstance(reducer.get("latest_reduction"), Mapping) else {}
    )
    workspace = env_receipt.get("workspace") if isinstance(env_receipt.get("workspace"), Mapping) else {}
    environment_fields = (
        env_receipt.get("selected_candidate_environment_fields")
        if isinstance(env_receipt.get("selected_candidate_environment_fields"), Mapping)
        else {}
    )
    import_check = (
        env_receipt.get("import_only_check")
        if isinstance(env_receipt.get("import_only_check"), Mapping)
        else {}
    )
    same_candidate = (
        env_receipt.get("same_candidate_reduce_existing")
        if isinstance(env_receipt.get("same_candidate_reduce_existing"), Mapping)
        else {}
    )
    candidate_result = (
        same_candidate.get("result") if isinstance(same_candidate.get("result"), Mapping) else {}
    )
    provider_row = (
        adapter_receipt.get("provider_dispatch", {}).get("row", {})
        if isinstance(adapter_receipt.get("provider_dispatch"), Mapping)
        else {}
    )
    provider_native_compatibility = (
        selection_receipt.get("provider_native_compatibility")
        if isinstance(selection_receipt.get("provider_native_compatibility"), Mapping)
        else {}
    )
    proof_repair_attempt_status = str(proof_repair_attempt_receipt.get("status") or "")
    proof_repair_evaluator = (
        proof_repair_attempt_receipt.get("evaluator")
        if isinstance(proof_repair_attempt_receipt.get("evaluator"), Mapping)
        else {}
    )
    proof_repair_failure = _proof_repair_failure_class(
        proof_repair_evaluator,
        repo_root=repo_root,
    )
    support_affordance_status = str(support_affordance_receipt.get("status") or "")
    proof_repair_provider = (
        proof_repair_attempt_receipt.get("provider_dispatch")
        if isinstance(proof_repair_attempt_receipt.get("provider_dispatch"), Mapping)
        else {}
    )
    proof_repair_provider_row = (
        proof_repair_provider.get("row")
        if isinstance(proof_repair_provider.get("row"), Mapping)
        else {}
    )
    proof_repair_transmitted = (
        proof_repair_provider_row.get("transmitted_request_extras")
        if isinstance(proof_repair_provider_row.get("transmitted_request_extras"), Mapping)
        else {}
    )
    adapter_transmitted = (
        provider_row.get("transmitted_request_extras")
        if isinstance(provider_row.get("transmitted_request_extras"), Mapping)
        else {}
    )
    structured_output_field = str(
        proof_repair_transmitted.get("provider_native_field")
        or adapter_transmitted.get("provider_native_field")
        or "unknown"
    )
    structured_output_request_shape = (
        "passed_current_nim_structured_output_lane:"
        + structured_output_field.replace(":", "_").replace("/", "_")
        if structured_output_field != "unknown"
        else "unknown"
    )
    selected_candidates = selection_receipt.get("selected_candidates")
    if not isinstance(selected_candidates, list):
        selected_candidates = []

    latest_next_workitem = latest.get("next_workitem")
    cockpit_id = "cap_quick_formal_math_decision_point_trace_cockpit_f07303ffe2e8"
    latest_routing_classification = (
        "cockpit_downstream_or_stale_as_primary_route"
        if latest_next_workitem == cockpit_id
        else "latest_route_not_cockpit"
    )
    microgate_status = str(microgate_receipt.get("status") or "not_present")
    adapter_status = str(adapter_receipt.get("status") or "unknown")
    env_status = str(env_receipt.get("status") or "unknown")
    gate_status = {
        "provider_repair": "passed",
        "provider_viability": "passed",
        "structured_output_request_shape": structured_output_request_shape,
        "lab_baseline": str(failure_receipt.get("baseline_status") or "unknown"),
        "baseline_scale": baseline["classification"],
        "residual_corpus": "passed" if residual_receipt.get("status") == "PASS" else "failed",
        "oracle_selection": "passed" if selected_candidates else "unknown",
        "oracle_microgate": (
            "adapter_required_then_resolved"
            if microgate_status == "blocked_reducer_contract_mismatch" and adapter_status == "resolved_but_lean_rejected"
            else microgate_status
        ),
        "formal_problem_resolution": (
            "passed" if int(formal_problem_resolution.get("resolved_count") or 0) > 0 else "unknown"
        ),
        "artifact_type_adapter": "passed" if adapter_receipt.get("transform_job", {}).get("built") else "unknown",
        "proof_hypothesis_adapter": "passed" if provider_row.get("validation_result", {}).get("passed") else "unknown",
        "environment_gate": "passed" if env_status.startswith("environment_available") else env_status,
        "environment_resolution": "passed_for_ArkLib_verisoftbench_2"
        if env_receipt.get("arklib_available_for_candidate")
        else "unknown",
        "lean_reducer": "reached" if reducer.get("invoked") or candidate_result else "unknown",
        "proof_hypothesis_correctness": "proof_level_rejected"
        if env_receipt.get("lean_rejection_is_proof_level")
        else "unknown",
        "support_affordance_finder": support_affordance_status or "not_run",
        "proof_repair_attempt": proof_repair_attempt_status or "not_run",
        "public_benchmark_claim": "forbidden",
    }

    entities = {
        "baseline_run_root": _artifact_ref(run_root, repo_root=repo_root),
        "latest_projection": _artifact_ref(MICROCOSM_ROOT / "latest.json", repo_root=repo_root),
        "failure_score_receipt": _artifact_ref(run_root / "failure_score_receipt.json", repo_root=repo_root),
        "decision_point_traces": _artifact_ref(run_root / "decision_point_traces.jsonl", repo_root=repo_root),
        "provider_jobs": _artifact_ref(run_root / "provider_jobs.jsonl", repo_root=repo_root),
        "residual_candidates": _artifact_ref(run_root / "residual_candidates.jsonl", repo_root=repo_root),
        "residual_corpus_index": _artifact_ref(RESIDUAL_INDEX_PATH, repo_root=repo_root),
        "residual_corpus_receipt": _artifact_ref(RESIDUAL_RECEIPT_PATH, repo_root=repo_root),
        "oracle_selection_receipt": _artifact_ref(run_root / "oracle_ingress_selection_receipt.json", repo_root=repo_root),
        "oracle_microgate_receipt": _artifact_ref(
            run_root / "oracle_ingress_microgate_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "formal_problem_resolution_receipt": _artifact_ref(
            run_root / "formal_problem_resolution_receipt.json",
            repo_root=repo_root,
        ),
        "adapter_receipt": _artifact_ref(run_root / "oracle_ingress_adapter_receipt.json", repo_root=repo_root),
        "environment_gate_receipt": _artifact_ref(
            run_root / "oracle_environment_gate_receipt.json",
            repo_root=repo_root,
        ),
        "transform_job": _artifact_ref(
            str(adapter_refs.get("transform_job_ref") or ""),
            repo_root=repo_root,
            must_exist=bool(adapter_refs.get("transform_job_ref")),
        ),
        "provider_receipt": _artifact_ref(
            str(adapter_refs.get("provider_receipt_ref") or ""),
            repo_root=repo_root,
            must_exist=bool(adapter_refs.get("provider_receipt_ref")),
        ),
        "row_patch": _artifact_ref(
            str(adapter_refs.get("row_patch_ref") or ""),
            repo_root=repo_root,
            must_exist=bool(adapter_refs.get("row_patch_ref")),
        ),
        "reducer_lean_check": _artifact_ref(
            str(latest_reduction.get("lean_check_result") or ""),
            repo_root=repo_root,
            must_exist=bool(latest_reduction.get("lean_check_result")),
        ),
        "reducer_reduction_report": _artifact_ref(
            str(latest_reduction.get("receipt_reduction_report") or ""),
            repo_root=repo_root,
            must_exist=bool(latest_reduction.get("receipt_reduction_report")),
        ),
        "arklib_workspace_ref": {
            "ref": workspace.get("workspace_root"),
            "exists_recorded_in_environment_gate": workspace.get("exists"),
            "must_exist": False,
            "ref_type": "external_run_local_workspace_not_repo_artifact",
        },
        "proof_repair_attempt_receipt": _artifact_ref(
            run_root / "proof_repair_attempt_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "proof_repair_inventory_receipt": _artifact_ref(
            run_root / "proof_repair_model_inventory_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "proof_repair_canary_receipt": _artifact_ref(
            run_root / "proof_repair_model_canary_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "proof_repair_evaluator_result": _artifact_ref(
            str(proof_repair_evaluator.get("result_ref") or ""),
            repo_root=repo_root,
            must_exist=bool(proof_repair_evaluator.get("result_ref")),
        ),
        "support_affordance_finder_receipt": _artifact_ref(
            support_affordance_root / "affordance_finder_receipt.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "support_affordance_declaration_index": _artifact_ref(
            support_affordance_root / "local_declaration_index.json",
            repo_root=repo_root,
            must_exist=False,
        ),
        "support_affordance_tactic_manifest": _artifact_ref(
            support_affordance_root / "tactic_probe_manifest.json",
            repo_root=repo_root,
            must_exist=False,
        ),
    }

    activities = {
        "provider_smoke_repair": _activity(
            activity_id="provider_smoke_repair",
            activity_type="provider_dispatch_repair",
            status="passed",
            commit_ref=REQUIRED_COMMITS["provider_smoke_repair"],
            output_entity_refs=["provider_receipt"],
        ),
        "thirty_packet_lab_baseline": _activity(
            activity_id="thirty_packet_lab_baseline",
            activity_type="initial_failure_score_baseline",
            status=str(failure_receipt.get("baseline_status") or "unknown"),
            source_receipt_ref=entities["failure_score_receipt"]["ref"],
            commit_ref=REQUIRED_COMMITS["thirty_packet_lab_baseline"],
            input_entity_refs=["latest_projection"],
            output_entity_refs=["failure_score_receipt", "decision_point_traces", "provider_jobs"],
        ),
        "residual_corpus_refresh": _activity(
            activity_id="residual_corpus_refresh",
            activity_type="residual_index_projection",
            status="passed" if residual_receipt.get("status") == "PASS" else "failed",
            source_receipt_ref=entities["residual_corpus_receipt"]["ref"],
            input_entity_refs=["residual_candidates", "decision_point_traces"],
            output_entity_refs=["residual_corpus_index", "residual_corpus_receipt"],
            claim_boundary=str(residual_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
        "oracle_ingress_selection": _activity(
            activity_id="oracle_ingress_selection",
            activity_type="oracle_candidate_selection",
            status="passed" if selected_candidates else "unknown",
            source_receipt_ref=entities["oracle_selection_receipt"]["ref"],
            input_entity_refs=["decision_point_traces"],
            output_entity_refs=["oracle_selection_receipt"],
            claim_boundary=str(selection_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
        "oracle_ingress_contract_microgate": _activity(
            activity_id="oracle_ingress_contract_microgate",
            activity_type="reducer_contract_gate",
            status=gate_status["oracle_microgate"],
            source_receipt_ref=entities["oracle_microgate_receipt"]["ref"],
            commit_ref=REQUIRED_COMMITS["oracle_contract_microgate"],
            input_entity_refs=["oracle_selection_receipt"],
            output_entity_refs=["oracle_microgate_receipt"],
            claim_boundary=str(microgate_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
        "formal_problem_resolution": _activity(
            activity_id="formal_problem_resolution",
            activity_type="formal_problem_resolution",
            status=gate_status["formal_problem_resolution"],
            source_receipt_ref=entities["formal_problem_resolution_receipt"]["ref"],
            input_entity_refs=["oracle_selection_receipt", "decision_point_traces"],
            output_entity_refs=["formal_problem_resolution_receipt"],
            claim_boundary=str(formal_problem_resolution.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
        "proof_hypothesis_adapter": _activity(
            activity_id="proof_hypothesis_adapter",
            activity_type="decision_point_to_proof_hypothesis_adapter",
            status=gate_status["proof_hypothesis_adapter"],
            source_receipt_ref=entities["adapter_receipt"]["ref"],
            commit_ref=REQUIRED_COMMITS["proof_hypothesis_adapter"],
            input_entity_refs=["formal_problem_resolution_receipt", "oracle_selection_receipt"],
            output_entity_refs=["adapter_receipt", "transform_job", "provider_receipt", "row_patch"],
            claim_boundary=str(adapter_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
        "environment_gate": _activity(
            activity_id="environment_gate",
            activity_type="candidate_specific_lean_environment_gate",
            status=gate_status["environment_gate"],
            source_receipt_ref=entities["environment_gate_receipt"]["ref"],
            commit_ref=REQUIRED_COMMITS["environment_gate"],
            input_entity_refs=["adapter_receipt", "provider_receipt", "row_patch"],
            output_entity_refs=["environment_gate_receipt", "arklib_workspace_ref"],
            claim_boundary=str(env_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
        "lean_reducer_judgment": _activity(
            activity_id="lean_reducer_judgment",
            activity_type="lean_reducer_judgment",
            status=gate_status["proof_hypothesis_correctness"],
            source_receipt_ref=entities["environment_gate_receipt"]["ref"],
            input_entity_refs=["provider_receipt", "row_patch", "arklib_workspace_ref"],
            output_entity_refs=["environment_gate_receipt", "reducer_lean_check"],
            claim_boundary=str(env_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        ),
    }
    if proof_repair_attempt_status:
        activities["proof_repair_attempt"] = _activity(
            activity_id="proof_repair_attempt",
            activity_type="one_row_external_model_proof_repair_attempt",
            status=proof_repair_attempt_status,
            source_receipt_ref=entities["proof_repair_attempt_receipt"]["ref"],
            input_entity_refs=["proof_repair_attempt_receipt", "row_patch", "environment_gate_receipt"],
            output_entity_refs=["proof_repair_attempt_receipt", "proof_repair_evaluator_result"],
            claim_boundary=str(proof_repair_attempt_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        )
    if support_affordance_status:
        activities["support_affordance_finder"] = _activity(
            activity_id="support_affordance_finder",
            activity_type="deterministic_local_math_affordance_scan",
            status=support_affordance_status,
            source_receipt_ref=entities["support_affordance_finder_receipt"]["ref"],
            input_entity_refs=["proof_repair_attempt_receipt", "environment_gate_receipt"],
            output_entity_refs=[
                "support_affordance_finder_receipt",
                "support_affordance_declaration_index",
                "support_affordance_tactic_manifest",
            ],
            claim_boundary=str(support_affordance_receipt.get("claim_boundary") or CLAIM_BOUNDARY),
        )

    commit_lineage = {
        label: {
            "commit": commit,
            "in_history": _git_in_history(commit, repo_root=repo_root),
        }
        for label, commit in REQUIRED_COMMITS.items()
    }

    residuals = [
        {
            "residual_type": "proof_level_rejection",
            "candidate": selected_candidate.get("task_id"),
            "status": "active_bottleneck",
            "evidence_ref": entities["environment_gate_receipt"]["ref"],
            "next_action": "proof_level_repair_or_candidate_level_proof_synthesis",
        },
        {
            "residual_type": "native_reducer_workspace_support_missing",
            "status": "isolated_by_environment_gate",
            "evidence_ref": entities["environment_gate_receipt"]["ref"],
        },
        {
            "residual_type": "unresolved_formal_problem_prefix",
            "status": "retained",
            "sample": formal_problem_resolution.get("unresolved_sample") or [],
            "evidence_ref": entities["formal_problem_resolution_receipt"]["ref"],
        },
        {
            "residual_type": "nim_structured_output_compatibility_watch",
            "status": provider_native_compatibility.get("status") or "current_lane_evidence_only",
            "evidence_ref": provider_native_compatibility.get("evidence_ref"),
            "watch": provider_native_compatibility.get("compatibility_watch"),
            "latest_repair_provider_native_field": structured_output_field,
        },
        {
            "residual_type": "latest_json_routes_to_cockpit",
            "status": latest_routing_classification,
            "latest_next_workitem": latest_next_workitem,
        },
        *_timeout_residuals(traces),
    ]
    if proof_repair_attempt_status == "proof_repair_lean_rejected_with_receipt":
        residuals.append(
            {
                "residual_type": "proof_repair_attempt_rejected",
                "candidate": selected_candidate.get("task_id"),
                "status": "retained_as_failed_repair_residual",
                "evidence_ref": entities["proof_repair_attempt_receipt"]["ref"],
                "evaluator_result_ref": proof_repair_evaluator.get("result_ref"),
                "model_id": (
                    (proof_repair_attempt_receipt.get("model_selection") or {}).get("selected_model_id")
                    if isinstance(proof_repair_attempt_receipt.get("model_selection"), Mapping)
                    else None
                ),
                "next_action": "do_not_loop_without_new_repair_strategy_or_candidate_selection",
            }
        )
        if support_affordance_status:
            residuals.append(
                {
                    "residual_type": "support_affordance_provider_attempt_rejected",
                    "candidate": selected_candidate.get("task_id"),
                    "status": proof_repair_failure.get("class"),
                    "missing_identifier": proof_repair_failure.get("missing_identifier"),
                    "finder_receipt_ref": entities["support_affordance_finder_receipt"]["ref"],
                    "evidence_ref": entities["proof_repair_attempt_receipt"]["ref"],
                    "evaluator_result_ref": proof_repair_evaluator.get("result_ref"),
                    "next_action": (
                        "use support-affordance packet to choose a new premise or strategy before any provider retry"
                    ),
                }
            )

    if proof_repair_attempt_status == "proof_repair_lean_accepted":
        next_action = {
            "action_type": "promote_lean_accepted_repair_candidate_through_owner_apply_lane",
            "candidate": selected_candidate.get("task_id"),
            "attempt_status": proof_repair_attempt_status,
            "attempt_receipt_ref": entities["proof_repair_attempt_receipt"]["ref"],
            "evaluator_result_ref": proof_repair_evaluator.get("result_ref"),
            "owner_hint": PRIMARY_OWNER,
            "owner_readiness": "repair_attempt_evaluator_accepted_requires_apply_lane_review",
        }
    elif proof_repair_attempt_status == "proof_repair_lean_rejected_with_receipt":
        next_action = {
            "action_type": "capture_rejected_repair_residual_or_select_next_repair_strategy",
            "candidate": selected_candidate.get("task_id"),
            "attempt_status": proof_repair_attempt_status,
            "attempt_receipt_ref": entities["proof_repair_attempt_receipt"]["ref"],
            "evaluator_result_ref": proof_repair_evaluator.get("result_ref"),
            "support_affordance_finder_status": support_affordance_status or "not_run",
            "latest_failure_class": proof_repair_failure.get("class"),
            "missing_identifier": proof_repair_failure.get("missing_identifier"),
            "must_preserve": [
                "no automatic second repair attempt",
                "no truth-side proof body exposure",
                "no public benchmark score",
                "provider output remains non-authoritative until Lean accepts it",
            ],
            "owner_hint": "cap_quick_formal_math_proof_repair_residual_eval_e_75029451f405",
            "owner_readiness": "one_attempt_completed_no_loop",
        }
    elif proof_repair_attempt_status in {
        "proof_repair_provider_schema_failed",
        "proof_repair_provider_unavailable",
        "proof_repair_blocked_no_trickle_or_credentials",
        "proof_repair_blocked_prompt_boundary",
        "proof_repair_timeout",
    }:
        next_action = {
            "action_type": "repair_provider_or_prompt_boundary_block_before_new_proof_repair",
            "candidate": selected_candidate.get("task_id"),
            "attempt_status": proof_repair_attempt_status,
            "attempt_receipt_ref": entities["proof_repair_attempt_receipt"]["ref"],
            "owner_hint": "cap_quick_formal_math_proof_repair_residual_eval_e_75029451f405",
            "owner_readiness": "attempt_blocked_with_receipt",
        }
    else:
        next_action = {
            "action_type": "shape_or_run_one_row_proof_repair",
            "candidate": selected_candidate.get("task_id"),
            "environment": {
                "source_repo": environment_fields.get("source_repo"),
                "source_commit": environment_fields.get("source_commit"),
                "lean_toolchain": environment_fields.get("lean_toolchain"),
                "workspace_ref": workspace.get("workspace_root"),
            },
            "input_refs": {
                "failed_lean_output_ref": candidate_result.get("stderr_ref"),
                "formal_problem_ref": entities["transform_job"]["ref"],
                "current_row_patch_ref": entities["row_patch"]["ref"],
                "strategy_context_source_ref": entities["decision_point_traces"]["ref"],
            },
            "must_preserve": [
                "no truth-side proof body exposure",
                "no public benchmark score",
                "provider output remains non-authoritative until Lean accepts it",
            ],
            "owner_hint": "cap_quick_formal_math_proof_repair_residual_eval_e_75029451f405",
            "owner_readiness": "captured_missing_satisfaction_contract_until_rechecked",
        }

    spine: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "proofline_id": f"formal_math_decision_point_microcosm_v0:{run_id}",
        "run_id": run_id,
        "claim_boundary": CLAIM_BOUNDARY,
        "benchmark_claims_allowed": False,
        "current_state": {
            "state": CURRENT_STATE,
            "active_bottleneck": ACTIVE_BOTTLENECK,
            "best_specimen": selected_candidate.get("task_id"),
            "why_not_provider": "provider proof-hypothesis job succeeded and schema validated",
            "why_not_adapter": "adapter produced reducer-valid proof-hypothesis transform job",
            "why_not_environment": "candidate ArkLib imports pass under pinned Lake environment",
            "why_not_public_score": "Lean did not accept the proof hypothesis and benchmark_claims_allowed=false",
        },
        "primary_owner": PRIMARY_OWNER,
        "supporting_owners": {
            "acceptance_boundary": [
                "cap_prover_formal_problem_ladder_eval_v0",
                "tools/meta/factory/reduce_prover_provider_receipts.py",
                "tools/meta/factory/build_formal_math_oracle_ingress_adapter.py",
                "tools/meta/factory/build_formal_math_oracle_environment_gate.py",
            ],
            "residual": "cap_formal_math_residual_corpus_index_v0",
            "observability": [
                "cap_formal_math_prover_observability_v0",
                "cap_quick_formal_math_decision_point_trace_cockpit_f07303ffe2e8",
            ],
            "future_loop": "cap_prover_continuous_lab_oracle_evolve_loop_v0",
            "next_lane_candidate": next_action["owner_hint"],
        },
        "entities": entities,
        "activities": activities,
        "agents": {
            "provider_model": {
                "provider": provider_row.get("provider_id"),
                "model": provider_row.get("model_id"),
                "structured_output_field": (
                    provider_row.get("transmitted_request_extras", {}).get("provider_native_field")
                    if isinstance(provider_row.get("transmitted_request_extras"), Mapping)
                    else None
                ),
            },
            "tools": [
                "tools/meta/factory/run_formal_math_initial_failure_score.py",
                "tools/meta/factory/build_formal_math_residual_corpus_index.py",
                "tools/meta/factory/build_formal_math_oracle_ingress_adapter.py",
                "tools/meta/factory/build_formal_math_oracle_environment_gate.py",
                "tools/meta/factory/reduce_prover_provider_receipts.py",
                "Lean/Lake pinned workspace",
            ],
        },
        "facets": {
            "provider_facet": {
                "provider_status_counts": baseline["provider_status_counts"],
                "provider_ok_count": baseline["provider_ok_count"],
                "proof_hypothesis_provider_status": provider_row.get("provider_status"),
                "proof_hypothesis_provider_receipt_ref": adapter_refs.get("provider_receipt_ref"),
                "nim_guided_json_compatibility": provider_native_compatibility,
            },
            "schema_facet": {
                "output_schema_valid_counts": baseline["output_schema_valid_counts"],
                "baseline_schema_valid_count": baseline["schema_valid_count"],
                "proof_hypothesis_schema_valid": provider_row.get("validation_result", {}).get("passed"),
            },
            "baseline_facet": {
                "baseline_status": failure_receipt.get("baseline_status"),
                "attempted_count": failure_receipt.get("attempted_count"),
                "selected_packet_count": latest.get("selected_packet_count"),
                "scale_classification": baseline["classification"],
                "tool_use": (failure_receipt.get("cost_latency") or {}).get("tool_use"),
            },
            "residual_facet": {
                "candidate_count": residual_receipt.get("candidate_count"),
                "run_count": residual_receipt.get("run_count"),
                "summary": residual_receipt.get("summary") or residual_index.get("summary"),
            },
            "adapter_facet": {
                "adapter_status": adapter_status,
                "transform_job_built": adapter_receipt.get("transform_job", {}).get("built"),
                "formal_problem_resolution": {
                    "candidate_count": formal_problem_resolution.get("candidate_count"),
                    "resolved_count": formal_problem_resolution.get("resolved_count"),
                    "selected_candidate_resolved_count": formal_problem_resolution.get(
                        "selected_candidate_resolved_count"
                    ),
                    "unresolved_count": formal_problem_resolution.get("unresolved_count"),
                },
            },
            "environment_facet": {
                "environment_status": env_status,
                "arklib_available_for_candidate": env_receipt.get("arklib_available_for_candidate"),
                "import_status": import_check.get("compile_status"),
                "candidate_status": candidate_result.get("compile_status"),
                "unknown_module_prefix": candidate_result.get("unknown_module_prefix"),
                "workspace_ref": workspace.get("workspace_root"),
                "workspace_ref_type": "external_run_local_workspace_not_repo_artifact",
            },
            "lean_judgment_facet": {
                "reducer_invoked": reducer.get("invoked"),
                "adapter_reducer_accepted_by_lean": latest_reduction.get("accepted_by_lean"),
                "adapter_reducer_error_class": latest_reduction.get("error_class"),
                "environment_candidate_accepted_by_lean": candidate_result.get("accepted_by_lean"),
                "lean_rejection_is_proof_level": env_receipt.get("lean_rejection_is_proof_level"),
            },
            "proof_repair_attempt_facet": {
                "status": proof_repair_attempt_status or "not_run",
                "provider_dispatch_attempted": proof_repair_provider.get("attempted"),
                "provider_status": (
                    proof_repair_provider_row.get("provider_status")
                    if isinstance(proof_repair_provider_row, Mapping)
                    else None
                ),
                "provider_native_field": structured_output_field,
                "model_id": (
                    (proof_repair_attempt_receipt.get("model_selection") or {}).get("selected_model_id")
                    if isinstance(proof_repair_attempt_receipt.get("model_selection"), Mapping)
                    else None
                ),
                "evaluator_kind": proof_repair_evaluator.get("kind"),
                "evaluator_invoked": proof_repair_evaluator.get("invoked"),
                "evaluator_status": proof_repair_evaluator.get("status"),
                "accepted_by_lean": proof_repair_evaluator.get("accepted_by_lean"),
                "attempt_receipt_ref": entities["proof_repair_attempt_receipt"]["ref"]
                if proof_repair_attempt_status
                else None,
                "latest_failure_class": proof_repair_failure.get("class"),
                "missing_identifier": proof_repair_failure.get("missing_identifier"),
            },
            "support_affordance_finder_facet": {
                "status": support_affordance_status or "not_run",
                "accessible_declaration_count": support_affordance_receipt.get("accessible_declaration_count"),
                "matched_declaration_count": support_affordance_receipt.get("matched_declaration_count"),
                "direct_local_acceptance": support_affordance_receipt.get("direct_local_acceptance"),
                "prior_failure_class": support_affordance_receipt.get("prior_failure_class"),
                "recommended_next_action": support_affordance_receipt.get("recommended_next_action"),
                "receipt_ref": entities["support_affordance_finder_receipt"]["ref"]
                if support_affordance_status
                else None,
                "declaration_index_ref": entities["support_affordance_declaration_index"]["ref"]
                if support_affordance_status
                else None,
                "tactic_probe_manifest_ref": entities["support_affordance_tactic_manifest"]["ref"]
                if support_affordance_status
                else None,
            },
            "claim_boundary_facet": {
                "claim_boundary": CLAIM_BOUNDARY,
                "public_benchmark_claim": "forbidden",
                "provider_output_counts_as_theorem_success": False,
            },
            "leakage_guard_facet": {
                "status": "PASS",
                "forbidden_body_key_check": "PASS",
                "truth_side_bodies_included": False,
                "provider_bodies_included": False,
                "prompt_payloads_included": False,
                "row_patch_ref_only": True,
            },
            "routing_facet": {
                "latest_next_workitem": latest_next_workitem,
                "latest_json_routing_classification": latest_routing_classification,
                "cockpit_role": "downstream_display_not_proofline_authority",
            },
            "next_action_facet": next_action,
        },
        "gate_status": gate_status,
        "lineage_edges": _lineage_edges(),
        "authoritative_refs": [
            entities["failure_score_receipt"],
            entities["residual_corpus_index"],
            entities["residual_corpus_receipt"],
            entities["oracle_selection_receipt"],
            entities["formal_problem_resolution_receipt"],
            entities["adapter_receipt"],
            entities["environment_gate_receipt"],
            entities["support_affordance_finder_receipt"],
            entities["support_affordance_declaration_index"],
            entities["support_affordance_tactic_manifest"],
        ],
        "projection_refs": [
            entities["latest_projection"],
            {
                "ref": "Task Ledger option-surface cards for formal-math/prover WorkItems",
                "exists": True,
                "must_exist": False,
                "authority": "projection_browse_only_events_are_authority",
            },
        ],
        "residuals": residuals,
        "blocked_claims": [
            {
                "claim": "public benchmark score",
                "status": "forbidden",
                "reason": "Lean/comparator did not accept a theorem proof",
            },
            {
                "claim": "provider output as theorem success",
                "status": "forbidden",
                "reason": "provider text remains a draft proof hypothesis until Lean accepts it",
            },
        ],
        "next_action": next_action,
        "display_surfaces": {
            "cockpit": {
                "work_item_id": cockpit_id,
                "role": "downstream_display_not_authority",
                "latest_json_points_here": latest_next_workitem == cockpit_id,
                "routing_classification": latest_routing_classification,
            }
        },
        "workitem_bindings": {
            "primary": PRIMARY_OWNER,
            "acceptance_boundary": "cap_prover_formal_problem_ladder_eval_v0",
            "residual": "cap_formal_math_residual_corpus_index_v0",
            "observability": "cap_formal_math_prover_observability_v0",
            "cockpit_display": cockpit_id,
            "next_lane_candidate": next_action["owner_hint"],
            "next_lane_readiness": next_action["owner_readiness"],
        },
        "freshness": {
            "required_commits": commit_lineage,
            "latest_run_id": latest.get("latest_run_id"),
            "latest_json_baseline_status": latest.get("baseline_status"),
            "latest_json_routing_classification": latest_routing_classification,
        },
        "leakage_guard": {
            "status": "PASS",
            "forbidden_body_keys_present": [],
            "body_policy": "refs_hashes_counts_statuses_only",
            "body_like_source_refs_only": [
                "provider_receipt",
                "row_patch",
                "decision_point_traces",
                "transform_job",
            ],
        },
    }
    spine["leakage_guard"]["forbidden_body_keys_present"] = _forbidden_keys_present(spine)
    spine["facets"]["leakage_guard_facet"]["forbidden_body_key_check"] = (
        "PASS" if not spine["leakage_guard"]["forbidden_body_keys_present"] else "FAIL"
    )
    return spine


def build_receipt(spine: Mapping[str, Any]) -> dict[str, Any]:
    issues = validate_spine(spine)
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "projection_owner_id": OWNER_ID,
        "spine_ref": _rel(SPINE_PATH),
        "receipt_ref": _rel(RECEIPT_PATH),
        "proofline_id": spine.get("proofline_id"),
        "claim_boundary": spine.get("claim_boundary"),
        "current_state": (spine.get("current_state") or {}).get("state")
        if isinstance(spine.get("current_state"), Mapping)
        else None,
        "active_bottleneck": (spine.get("current_state") or {}).get("active_bottleneck")
        if isinstance(spine.get("current_state"), Mapping)
        else None,
        "next_action": spine.get("next_action"),
        "latest_json_routing_classification": (
            (spine.get("facets") or {})
            .get("routing_facet", {})
            .get("latest_json_routing_classification")
            if isinstance(spine.get("facets"), Mapping)
            else None
        ),
        "gate_status": spine.get("gate_status"),
        "blocked_claims": spine.get("blocked_claims"),
        "leakage_guard": spine.get("leakage_guard"),
    }


def validate_spine(spine: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if spine.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version mismatch")
    if spine.get("claim_boundary") != CLAIM_BOUNDARY:
        issues.append("claim boundary mismatch")
    if spine.get("benchmark_claims_allowed") is not False:
        issues.append("benchmark_claims_allowed must be false")
    current_state = spine.get("current_state") if isinstance(spine.get("current_state"), Mapping) else {}
    if current_state.get("state") != CURRENT_STATE:
        issues.append("current_state must be proof_level_rejected")
    if current_state.get("active_bottleneck") != ACTIVE_BOTTLENECK:
        issues.append("active_bottleneck must be proof_synthesis_or_repair_quality")
    if not spine.get("next_action"):
        issues.append("next_action must be non-null")
    gate_status = spine.get("gate_status") if isinstance(spine.get("gate_status"), Mapping) else {}
    if gate_status.get("public_benchmark_claim") != "forbidden":
        issues.append("public benchmark claim must remain forbidden")
    if gate_status.get("proof_hypothesis_correctness") != "proof_level_rejected":
        issues.append("proof hypothesis correctness must be proof_level_rejected")
    facets = spine.get("facets") if isinstance(spine.get("facets"), Mapping) else {}
    routing = facets.get("routing_facet") if isinstance(facets.get("routing_facet"), Mapping) else {}
    if routing.get("latest_json_routing_classification") not in {
        "cockpit_downstream_or_stale_as_primary_route",
        "latest_route_not_cockpit",
    }:
        issues.append("latest/cockpit routing classification missing")
    forbidden_keys = _forbidden_keys_present(spine)
    if forbidden_keys:
        issues.append(f"forbidden body-like keys present in spine: {forbidden_keys}")
    for ref in spine.get("authoritative_refs") or []:
        if not isinstance(ref, Mapping):
            issues.append("authoritative_refs entries must be objects")
            continue
        if ref.get("must_exist", True) and not ref.get("exists"):
            issues.append(f"missing authoritative ref: {ref.get('ref')}")
    try:
        owner = generated_projection_registry.get_projection_owner(OWNER_ID)
    except KeyError:
        issues.append(f"generated projection owner {OWNER_ID} is not registered")
    else:
        artifacts = set(owner.artifacts)
        if str(SPINE_PATH) not in artifacts or str(RECEIPT_PATH) not in artifacts:
            issues.append("generated projection owner does not cover proofline outputs")
    return issues


def write_outputs(*, run_id: str = DEFAULT_RUN_ID, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    spine = build_spine(run_id=run_id, repo_root=repo_root)
    receipt = build_receipt(spine)
    _write_json(_repo_path(SPINE_PATH, repo_root=repo_root), spine)
    _write_json(_repo_path(RECEIPT_PATH, repo_root=repo_root), receipt)
    return receipt


def check_outputs(*, run_id: str = DEFAULT_RUN_ID, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    spine_path = _repo_path(SPINE_PATH, repo_root=repo_root)
    receipt_path = _repo_path(RECEIPT_PATH, repo_root=repo_root)
    expected_spine = build_spine(run_id=run_id, repo_root=repo_root)
    expected_receipt = build_receipt(expected_spine)
    issues: list[str] = []
    if not spine_path.exists():
        issues.append(f"missing {SPINE_PATH}")
    else:
        actual_spine = _read_json(spine_path)
        actual_issues = validate_spine(actual_spine)
        issues.extend(f"actual spine invalid: {issue}" for issue in actual_issues)
        if actual_spine != expected_spine:
            issues.append(f"{SPINE_PATH} is stale")
    if not receipt_path.exists():
        issues.append(f"missing {RECEIPT_PATH}")
    else:
        actual_receipt = _read_json(receipt_path)
        if _forbidden_keys_present(actual_receipt):
            issues.append(
                f"forbidden body-like keys present in receipt: {_forbidden_keys_present(actual_receipt)}"
            )
        if actual_receipt != expected_receipt:
            issues.append(f"{RECEIPT_PATH} is stale")
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "spine_ref": str(SPINE_PATH),
        "receipt_ref": str(RECEIPT_PATH),
        "current_state": (expected_spine.get("current_state") or {}).get("state"),
        "active_bottleneck": (expected_spine.get("current_state") or {}).get(
            "active_bottleneck"
        ),
        "next_action_type": (expected_spine.get("next_action") or {}).get("action_type"),
        "latest_json_routing_classification": (
            (expected_spine.get("facets") or {})
            .get("routing_facet", {})
            .get("latest_json_routing_classification")
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
                    "spine_ref": str(SPINE_PATH),
                    "receipt_ref": str(RECEIPT_PATH),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
