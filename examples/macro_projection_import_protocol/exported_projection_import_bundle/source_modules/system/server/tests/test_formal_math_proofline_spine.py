from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.generated_projection_registry import get_projection_owner
from tools.meta.factory import build_formal_math_proofline_spine as proofline


RUN_ID = "initial_failure_score_20260512T195745Z"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(repo_root: Path, *, include_microgate: bool = True) -> Path:
    root = repo_root / proofline.MICROCOSM_ROOT
    run_root = root / f"run_{RUN_ID}"
    _write_json(
        root / "latest.json",
        {
            "schema_version": "formal_math_decision_point_microcosm_latest_v0",
            "latest_run_id": RUN_ID,
            "latest_run_dir": str(proofline._run_root(RUN_ID)),
            "baseline_status": "completed",
            "attempted_count": 30,
            "selected_packet_count": 30,
            "benchmark_claims_allowed": False,
            "next_workitem": "cap_quick_formal_math_decision_point_trace_cockpit_f07303ffe2e8",
        },
    )
    _write_json(
        run_root / "failure_score_receipt.json",
        {
            "schema_version": "formal_math_initial_failure_score_v0",
            "run_id": RUN_ID,
            "baseline_status": "completed",
            "attempted_count": 30,
            "benchmark_claims_allowed": False,
            "provider_calls_made": True,
            "prover_oracle_calls_made": False,
            "failure_class_counts": {
                "construction_strategy_failure": 20,
                "oracle_unavailable": 30,
                "premise_context_selection_failure": 9,
                "progress_signal_missing": 30,
                "provider_dispatch_failure": 1,
                "output_schema_failure": 0,
            },
            "cost_latency": {
                "tool_use": {
                    "provider_transform_jobs": 30,
                    "lean_oracle_calls": 0,
                    "comparator_calls": 0,
                    "repair_attempts": 0,
                }
            },
        },
    )
    _write_jsonl(
        run_root / "decision_point_traces.jsonl",
        [
            {
                "trace_id": "trace_verisoftbench_2",
                "task_id": "verisoftbench:2",
                "provider_status": "ok",
                "output_schema_valid": True,
                "provider_job_id": "tj_ok",
            },
            {
                "trace_id": "trace_verisoftbench_3",
                "task_id": "verisoftbench:3",
                "provider_status": "timeout",
                "output_schema_valid": None,
                "provider_job_id": "tj_timeout",
            },
        ],
    )
    _write_jsonl(run_root / "provider_jobs.jsonl", [{"job_id": "tj_ok"}, {"job_id": "tj_timeout"}])
    _write_jsonl(run_root / "residual_candidates.jsonl", [{"trace_id": "trace_verisoftbench_2"}])
    _write_json(
        repo_root / proofline.RESIDUAL_RECEIPT_PATH,
        {
            "schema_version": "formal_math_residual_corpus_index_receipt_v0",
            "status": "PASS",
            "candidate_count": 40,
            "run_count": 3,
            "latest_run_id": RUN_ID,
            "claim_boundary": "private_residual_corpus_not_public_benchmark_result",
            "summary": {
                "by_provider_status": {"ok": 34, "timeout": 6},
                "by_residual_class": {"oracle_unavailable": 40},
            },
        },
    )
    _write_json(
        repo_root / proofline.RESIDUAL_INDEX_PATH,
        {
            "schema_version": "formal_math_residual_corpus_index_v0",
            "candidate_count": 40,
            "run_count": 3,
            "summary": {"by_provider_status": {"ok": 34, "timeout": 6}},
        },
    )
    _write_json(
        run_root / "oracle_ingress_selection_receipt.json",
        {
            "schema_version": "formal_math_oracle_ingress_selection_receipt_v0",
            "claim_boundary": "oracle_ingress_selection_not_oracle_result_not_benchmark_score",
            "selected_candidates": [
                {
                    "task_id": "verisoftbench:2",
                    "benchmark_id": "verisoftbench",
                    "trace_id": "trace_verisoftbench_2",
                    "provider": {
                        "status": "ok",
                        "output_schema_valid": True,
                        "provider_receipt_ref": "state/compute_workers/receipts/2026-05/rc_ok.json",
                    },
                }
            ],
            "provider_native_compatibility": {
                "status": "current_hosted_lane_accepts_nvext_guided_json",
                "evidence_ref": "state/compute_workers/receipts/2026-05/rc_ok.json",
                "provider_native_field": "nvext.guided_json",
                "compatibility_watch": "watch only",
            },
        },
    )
    if include_microgate:
        _write_json(
            run_root / "oracle_ingress_microgate_receipt.json",
            {
                "schema_version": "formal_math_oracle_ingress_microgate_receipt_v0",
                "status": "blocked_reducer_contract_mismatch",
                "claim_boundary": "not_benchmark_result_not_theorem_success",
            },
        )
    _write_json(
        run_root / "formal_problem_resolution_receipt.json",
        {
            "schema_version": "formal_math_formal_problem_resolution_receipt_v0",
            "run_id": RUN_ID,
            "candidate_count": 29,
            "selected_candidate_count": 4,
            "resolved_count": 28,
            "selected_candidate_resolved_count": 4,
            "unresolved_count": 1,
            "unresolved_sample": [{"task_id": "verisoftbench:10"}],
            "claim_boundary": "not_benchmark_result_not_theorem_success",
        },
    )
    transform_ref = (
        run_root
        / "oracle_ingress_adapter_transform_jobs/state/compute_workers/transform_jobs/2026-05/tj_proof.json"
    )
    provider_ref = repo_root / "state/compute_workers/receipts/2026-05/rc_proof.json"
    row_patch_ref = repo_root / "state/compute_workers/row_patches/2026-05/rp_proof.json"
    lean_check_ref = run_root / "oracle_ingress_adapter_reducer_run/reductions/rc_proof/lean_check_result.json"
    reduction_ref = (
        run_root
        / "oracle_ingress_adapter_reducer_run/reductions/rc_proof/receipt_reduction_report.json"
    )
    for path in (transform_ref, provider_ref, row_patch_ref, lean_check_ref, reduction_ref):
        _write_json(path, {"ok": True})
    transform_ref_rel = transform_ref.relative_to(repo_root).as_posix()
    provider_ref_rel = provider_ref.relative_to(repo_root).as_posix()
    row_patch_ref_rel = row_patch_ref.relative_to(repo_root).as_posix()
    lean_check_ref_rel = lean_check_ref.relative_to(repo_root).as_posix()
    reduction_ref_rel = reduction_ref.relative_to(repo_root).as_posix()
    _write_json(
        run_root / "oracle_ingress_adapter_receipt.json",
        {
            "schema_version": "formal_math_oracle_ingress_adapter_receipt_v0",
            "status": "resolved_but_lean_rejected",
            "claim_boundary": "not_benchmark_result_not_theorem_success",
            "selected_candidate": {"task_id": "verisoftbench:2", "benchmark_id": "verisoftbench"},
            "transform_job": {
                "built": True,
                "transform_job_id": "tj_proof",
                "transform_job_ref": transform_ref_rel,
            },
            "provider_dispatch": {
                "attempted": True,
                "provider": "nvidia_nim",
                "model": "deepseek-ai/deepseek-v4-flash",
                "row": {
                    "provider_id": "nvidia_nim",
                    "model_id": "deepseek-ai/deepseek-v4-flash",
                    "provider_status": "ok",
                    "provider_receipt_id": "rc_proof",
                    "provider_receipt_ref": provider_ref_rel,
                    "row_patch_ref": row_patch_ref_rel,
                    "transform_job_ref": transform_ref_rel,
                    "validation_result": {"passed": True, "violations": []},
                    "transmitted_request_extras": {
                        "provider_native_field": "nvext.guided_json",
                        "structured_output": True,
                    },
                },
            },
            "reducer": {
                "invoked": True,
                "latest_reduction": {
                    "accepted_by_lean": False,
                    "error_class": "PROOF_SYNTHESIS_FAIL",
                    "lean_check_result": lean_check_ref_rel,
                    "receipt_reduction_report": reduction_ref_rel,
                },
            },
        },
    )
    _write_json(
        run_root / "oracle_environment_gate_receipt.json",
        {
            "schema_version": "formal_math_oracle_environment_gate_receipt_v0",
            "status": "environment_available_same_candidate_lean_rejected",
            "claim_boundary": "not_benchmark_result_not_theorem_success",
            "benchmark_claims_allowed": False,
            "selected_candidate": {"task_id": "verisoftbench:2", "benchmark_id": "verisoftbench"},
            "selected_candidate_environment_fields": {
                "source_repo": "ArkLib",
                "source_commit": "779e3ec",
                "lean_toolchain": "leanprover/lean4:v4.22.0",
            },
            "adapter_artifacts": {
                "provider_receipt_ref": provider_ref_rel,
                "row_patch_ref": row_patch_ref_rel,
                "transform_job_ref": transform_ref_rel,
            },
            "provider_dispatch": {
                "performed_by_environment_gate": False,
                "new_provider_calls": 0,
            },
            "workspace": {"workspace_root": "/tmp/ArkLib", "exists": True},
            "import_only_check": {"compile_status": "PASS"},
            "same_candidate_reduce_existing": {
                "result": {
                    "compile_status": "FAIL",
                    "stderr_ref": "stderr.txt",
                    "unknown_module_prefix": False,
                    "accepted_by_lean": False,
                }
            },
            "arklib_available_for_candidate": True,
            "lean_rejection_is_proof_level": True,
        },
    )
    return run_root


def _nested_keys(payload: object) -> set[str]:
    if isinstance(payload, dict):
        keys = set(payload)
        for value in payload.values():
            keys.update(_nested_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for value in payload:
            keys.update(_nested_keys(value))
        return keys
    return set()


def test_proofline_spine_classifies_lineage_without_body_leakage(tmp_path: Path) -> None:
    _fixture(tmp_path)

    spine = proofline.build_spine(run_id=RUN_ID, repo_root=tmp_path)
    receipt = proofline.build_receipt(spine)

    assert spine["schema_version"] == "formal_math_proofline_spine_v0"
    assert spine["current_state"]["state"] == "proof_level_rejected"
    assert spine["current_state"]["active_bottleneck"] == "proof_synthesis_or_repair_quality"
    assert spine["gate_status"]["proof_hypothesis_correctness"] == "proof_level_rejected"
    assert spine["gate_status"]["environment_gate"] == "passed"
    assert spine["facets"]["routing_facet"]["latest_json_routing_classification"] == (
        "cockpit_downstream_or_stale_as_primary_route"
    )
    assert spine["next_action"]["action_type"] == "shape_or_run_one_row_proof_repair"
    assert receipt["status"] == "PASS"
    assert _nested_keys(spine).isdisjoint(proofline.FORBIDDEN_BODY_KEYS)


def test_proofline_check_tolerates_superseded_missing_microgate_receipt(tmp_path: Path) -> None:
    _fixture(tmp_path, include_microgate=False)

    receipt = proofline.write_outputs(run_id=RUN_ID, repo_root=tmp_path)
    check = proofline.check_outputs(run_id=RUN_ID, repo_root=tmp_path)

    assert receipt["status"] == "PASS"
    assert check["status"] == "PASS"
    assert (tmp_path / proofline.SPINE_PATH).exists()
    assert (tmp_path / proofline.RECEIPT_PATH).exists()


def test_proofline_check_flags_forbidden_body_keys(tmp_path: Path) -> None:
    _fixture(tmp_path)
    proofline.write_outputs(run_id=RUN_ID, repo_root=tmp_path)
    spine_path = tmp_path / proofline.SPINE_PATH
    payload = json.loads(spine_path.read_text(encoding="utf-8"))
    payload["leak"] = {"lean_proof_body": "by exact hidden"}
    _write_json(spine_path, payload)

    check = proofline.check_outputs(run_id=RUN_ID, repo_root=tmp_path)

    assert check["status"] == "FAIL"
    assert any("forbidden body-like keys" in issue for issue in check["issues"])


def test_proofline_generated_projection_owner_registered() -> None:
    owner = get_projection_owner("formal_math_proofline_spine_projection")

    assert str(proofline.SPINE_PATH) in owner.artifacts
    assert str(proofline.RECEIPT_PATH) in owner.artifacts
    assert owner.check_command == (
        "./repo-python",
        "tools/meta/factory/build_formal_math_proofline_spine.py",
        "--check",
    )
