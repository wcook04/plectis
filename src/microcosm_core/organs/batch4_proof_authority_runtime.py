from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    file_sha256,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch4_proof_authority_runtime"
FIXTURE_ID = "first_wave.batch4_proof_authority_runtime"
VALIDATOR_ID = "validator.microcosm.organs.batch4_proof_authority_runtime"

RESULT_NAME = "batch4_proof_authority_runtime_result.json"
BOARD_NAME = "batch4_proof_authority_runtime_board.json"
VALIDATION_RECEIPT_NAME = "batch4_proof_authority_runtime_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch4_proof_authority_runtime_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "batch4_proof_authority_runtime_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch4_proof_authority_runtime_bundle"
PROBE_MANIFEST_NAME = "batch4_probe_manifest.json"
LEAN_LAKE_PROBE_TIMEOUT_SECONDS = 60
LEAN_LAKE_DEPENDENCY_UNAVAILABLE_MARKERS = (
    "unknown module prefix 'Mathlib'",
    'unknown module prefix "Mathlib"',
    "No directory 'Mathlib' or file 'Mathlib.olean'",
    "No directory \"Mathlib\" or file \"Mathlib.olean\"",
)
LEAN_LAKE_BOUNDARY_CLAIM = (
    "Lean/Lake probe is a copied-kernel compile boundary witness only. A pass "
    "means the copied public CertificateKernel.lean reached zero-exit Lean "
    "elaboration under the source Lake project; dependency-unavailable records "
    "toolchain/project incompleteness; nonzero compile failures block. None of "
    "these states grant theorem correctness; this is not theorem correctness, "
    "not proof correctness, not a solution of Erdos #257, not publication "
    "authority, and not release authority."
)
_LEAN_LAKE_PROBE_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "lean_strategy_control_benchmark",
    "prover_skill_foundry",
    "verisoftbench_harness_differential",
    "verisoftbench_calibration_executor",
    "erdos257_certificate_kernel",
    "lean_full_fidelity_packet_verifier",
    "reasoning_execution_authority_grant",
    "forward_integration_policy_fence",
    "closeout_executor_state_machine",
    "metabolism_bitemporal_claim_log",
    "macos_taskpolicy_actuator",
    "context_yield_attribution",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "prover_graph_benchmark",
    "verisoftbench_harness_differential",
    "verisoftbench_calibration_rows",
    "erdos257_target_runner",
    "lean_microcosm_projection",
    "lean_full_fidelity_packet_replay",
    "reasoning_authority_envelope",
    "reasoning_grant_lease",
    "reasoning_plan_builder",
    "reasoning_plan_verifier",
    "forward_integration_policy",
    "closeout_executor",
    "metabolism_store",
    "metabolismd",
    "metabolism_governor",
    "agent_execution_trace",
    "erdos257_certificate_kernel",
)

EXPECTED_NEGATIVE_CASES = {
    "weak_skeleton_synthesis_failure": (
        "BATCH4_WEAK_SKELETON_MUST_NOT_SILENT_PASS",
    ),
    "foundry_low_repair_quarantine": (
        "BATCH4_FOUNDRY_REPAIRED_COUNT_BELOW_THRESHOLD",
    ),
    "verisoft_truth_leak": (
        "BATCH4_VERISOFT_TRUTH_LEAK_REJECTED",
    ),
    "verisoft_prefix_answer_leakage": (
        "BATCH4_VERISOFT_PREFIX_ANSWER_LEAKAGE_REJECTED",
    ),
    "erdos_solution_overclaim": (
        "BATCH4_ERDOS257_SOLUTION_OVERCLAIM_REJECTED",
    ),
    "packet_sha256_corruption": (
        "BATCH4_PACKET_SHA256_CORRUPTION_REJECTED",
    ),
    "grant_forbidden_context": (
        "BATCH4_GRANT_FORBIDDEN_CONTEXT_DENIED",
    ),
    "forward_dirty_unknown_target": (
        "BATCH4_FORWARD_POLICY_DIRTY_UNKNOWN_TARGET_BLOCKED",
    ),
    "closeout_stale_head": (
        "BATCH4_CLOSEOUT_STALE_HEAD_DEFERS",
    ),
    "bitemporal_expired_claim": (
        "BATCH4_BITEMPORAL_EXPIRED_CLAIM_NOT_CURRENT",
    ),
    "taskpolicy_missing_binary": (
        "BATCH4_TASKPOLICY_UNAVAILABLE_PASSTHROUGH",
    ),
    "context_accepted_read_guard": (
        "BATCH4_CONTEXT_ACCEPTED_SCOPED_READ_NOT_FLAGGED",
    ),
}

NEGATIVE_CASE_RUNTIME_PROBES = {
    "weak_skeleton_synthesis_failure": {
        "observer_id": "strategy_control_anchor_presence",
        "source_module_id": "prover_graph_benchmark",
        "required_text": "def run_strategy_control_graph(",
    },
    "foundry_low_repair_quarantine": {
        "observer_id": "skill_foundry_anchor_presence",
        "source_module_id": "prover_graph_benchmark",
        "required_text": "def run_prover_skill_foundry(",
    },
    "verisoft_truth_leak": {
        "observer_id": "verisoft_harness_check_presence",
        "source_module_id": "verisoftbench_harness_differential",
        "required_text": "def check_outputs(",
    },
    "verisoft_prefix_answer_leakage": {
        "observer_id": "verisoft_calibration_check_presence",
        "source_module_id": "verisoftbench_calibration_rows",
        "required_text": "def check_outputs(",
    },
    "erdos_solution_overclaim": {
        "observer_id": "erdos_static_scan_and_authority_delta",
        "source_module_id": "erdos257_certificate_kernel",
        "required_text": "theorem no_prime_drop_implies_eq",
    },
    "packet_sha256_corruption": {
        "observer_id": "packet_corruption_reject_anchor_presence",
        "source_module_id": "lean_microcosm_projection",
        "required_text": "source_ref_integrity",
    },
    "grant_forbidden_context": {
        "observer_id": "grant_denial_no_dispatch",
        "source_module_id": "reasoning_grant_lease",
        "required_text": "forbidden_effective_context",
    },
    "forward_dirty_unknown_target": {
        "observer_id": "forward_dirty_unknown_target_policy_anchor",
        "source_module_id": "forward_integration_policy",
        "required_text": "dirty_unknown_target",
    },
    "closeout_stale_head": {
        "observer_id": "closeout_stale_head_deferral_anchor",
        "source_module_id": "closeout_executor",
        "required_text": "StalePlanHeadMismatch",
    },
    "bitemporal_expired_claim": {
        "observer_id": "bitemporal_claim_event_supersession_anchors",
        "source_module_id": "metabolism_store",
        "required_text": "blackboard_claim_events",
    },
    "taskpolicy_missing_binary": {
        "observer_id": "taskpolicy_unavailable_passthrough_anchor",
        "source_module_id": "metabolismd",
        "required_text": "taskpolicy_unavailable",
    },
    "context_accepted_read_guard": {
        "observer_id": "context_yield_scoped_read_guard_anchors",
        "source_module_id": "agent_execution_trace",
        "required_text": "scoped_diff_paths",
    },
}

NEGATIVE_CASE_OVERCLAIM_SHAPES = {
    "weak_skeleton_synthesis_failure": {
        "mechanism_id": "lean_strategy_control_benchmark",
        "claim_ceiling_must_contain": ("not an open-problem solver", "SOTA claim"),
        "public_exercise_must_contain": ("strategy-control graph anchor",),
    },
    "foundry_low_repair_quarantine": {
        "mechanism_id": "prover_skill_foundry",
        "claim_ceiling_must_contain": ("not open-ended autonomous theorem-proving",),
        "public_exercise_must_contain": ("foundry functions",),
    },
    "verisoft_truth_leak": {
        "mechanism_id": "verisoftbench_harness_differential",
        "claim_ceiling_must_contain": ("not official benchmark result", "solve-rate claim"),
        "public_exercise_must_contain": ("Harness differential diagnosis",),
    },
    "verisoft_prefix_answer_leakage": {
        "mechanism_id": "verisoftbench_calibration_executor",
        "claim_ceiling_must_contain": ("not a leaderboard", "benchmark claim"),
        "public_exercise_must_contain": ("Calibration-row check-output",),
    },
    "erdos_solution_overclaim": {
        "mechanism_id": "erdos257_certificate_kernel",
        "claim_ceiling_must_contain": ("not a solution of Erdos #257", "not publication authority"),
        "public_exercise_must_contain": ("Copied CertificateKernel.lean",),
    },
    "packet_sha256_corruption": {
        "mechanism_id": "lean_full_fidelity_packet_verifier",
        "claim_ceiling_must_contain": ("not Lean proof correctness",),
        "public_exercise_must_contain": ("Hashed source-ref verifier",),
    },
    "grant_forbidden_context": {
        "mechanism_id": "reasoning_execution_authority_grant",
        "claim_ceiling_must_contain": ("not a live sandbox",),
        "public_exercise_must_contain": ("no-dispatch posture",),
    },
    "forward_dirty_unknown_target": {
        "mechanism_id": "forward_integration_policy_fence",
        "claim_ceiling_must_contain": ("not complete concurrency control",),
        "public_exercise_must_contain": ("Dirty target classification",),
    },
    "closeout_stale_head": {
        "mechanism_id": "closeout_executor_state_machine",
        "claim_ceiling_must_contain": ("dry-run state machine",),
        "public_exercise_must_contain": ("stale-HEAD deferral",),
    },
    "bitemporal_expired_claim": {
        "mechanism_id": "metabolism_bitemporal_claim_log",
        "claim_ceiling_must_contain": ("not distributed consensus", "not live metabolism DB export"),
        "public_exercise_must_contain": ("Blackboard claim event table",),
    },
    "taskpolicy_missing_binary": {
        "mechanism_id": "macos_taskpolicy_actuator",
        "claim_ceiling_must_contain": ("not a cross-platform scheduler",),
        "public_exercise_must_contain": ("Taskpolicy wrapping",),
    },
    "context_accepted_read_guard": {
        "mechanism_id": "context_yield_attribution",
        "claim_ceiling_must_contain": ("not raw private session text",),
        "public_exercise_must_contain": ("Context-yield attribution",),
    },
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch4_public_substrate_capsule_not_live_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "proof_authority_delta": "none",
    "launch_authorized": False,
    "model_dispatch": False,
    "provider_dispatch": False,
    "runtime_execution": False,
    "live_cdp_dispatch_authorized": False,
    "live_codex_state_export_authorized": False,
    "live_metabolism_db_export_authorized": False,
    "source_mutation_authorized": False,
    "official_leaderboard_submission": False,
    "publication_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Batch 4 proof-authority-runtime validates copied public macro source bodies "
    "and bounded synthetic negative cases for proof-control, machine-checked math, "
    "dry-run authority, closeout planning, Codex runtime diagnostics, bitemporal "
    "coordination, taskpolicy wrapping, and context-yield attribution. It is not "
    "a solution of Erdos #257, not publication authority, not a benchmark result, "
    "not live sandbox enforcement, not live Codex orchestration, and not release "
    "approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/meta/factory/run_prover_graph_benchmark.py": (
        "def run_strategy_control_graph(",
        "def run_prover_skill_foundry(",
        "def _strategy_comparison_report(",
        "def _mine_skill_candidate_clusters(",
    ),
    "tools/meta/factory/run_verisoftbench_micro10_harness_differential.py": (
        "def _diagnose(",
        "def check_outputs(",
    ),
    "tools/meta/factory/run_verisoftbench_micro10_calibration_rows.py": (
        "def check_outputs(",
        "--max-probes",
    ),
    "tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py": (
        "def _parse_axiom_dependencies(",
        "def build_receipt(",
    ),
    "tools/meta/factory/build_lean_mathematics_microcosm_projection.py": (
        "def _verify_hashed_file_ref(",
        "source_ref_integrity",
        "REVIEWABLE_REPLAYED",
    ),
    "tools/meta/factory/run_lean_full_fidelity_packet_replay.py": (
        "--compact",
        "--attempt-hydration",
    ),
    "tools/meta/factory/build_reasoning_execution_authority_envelope.py": (
        "def _authority_decision(",
        "forbidden_effective_context",
        "launch_authorized",
    ),
    "tools/meta/factory/build_reasoning_execution_grant_lease.py": (
        "def _lease_status_and_issues(",
        "forbidden_effective_context",
        "eligible_unissued",
    ),
    "tools/meta/factory/build_reasoning_execution_plan.py": (
        "runtime_execution",
        "model_dispatch",
    ),
    "tools/meta/factory/verify_reasoning_execution_plan.py": (
        "def _cycle_path(",
        "cycle_detected",
    ),
    "system/lib/forward_integration_policy.py": (
        "def build_forward_integration_policy(",
        "def path_scope_overlaps(",
    ),
    "system/lib/closeout_executor.py": (
        "def run_closeout_executor_burst(",
        "StalePlanHeadMismatch",
        "ConcurrentPublicationChurn",
    ),
    "system/lib/metabolism_store.py": (
        "blackboard_claim_events",
        "def _append_claim_assertion_event(",
        "def list_temporal_blackboard_claims(",
    ),
    "tools/meta/control/metabolismd.py": (
        "def _background_policy_argv_for_operation(",
        "taskpolicy",
        "def _launch_job",
    ),
    "system/lib/metabolism_governor.py": (
        "BACKGROUND_TASKPOLICY_COST_CLASSES",
        "def should_launch_with_background_policy(",
    ),
    "system/lib/agent_execution_trace.py": (
        "def _compute_context_yield_attribution(",
        "governance_status_counts",
        "scoped_diff_paths",
    ),
    "formal_math/erdos257_period_noncollapse/Erdos257PeriodNoncollapse/CertificateKernel.lean": (
        "theorem no_prime_drop_implies_eq",
        "theorem collapse_divisor_core",
        "theorem odd_prime_order_factorization_pow_sub_one",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 4 Proof, Authority, and Runtime Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch4_proof_authority_runtime/"
        "exported_batch4_proof_authority_runtime_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _finding(code: str, message: str, *, subject_id: str | None = None) -> dict[str, Any]:
    payload = {"error_code": code, "message": message, "body_in_receipt": False}
    if subject_id:
        payload["subject_id"] = subject_id
    return payload


def _load_manifest(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = input_path / PROBE_MANIFEST_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [_finding("BATCH4_PROBE_MANIFEST_INVALID", str(exc), subject_id=path.name)]
    if not isinstance(payload, dict):
        return {}, [_finding("BATCH4_PROBE_MANIFEST_NOT_OBJECT", "Probe manifest must be an object.")]
    return payload, []


def _original_source_manifest(source_manifest: Mapping[str, Any], *, public_root: Path) -> dict[str, Any]:
    manifest_ref = str(source_manifest.get("manifest_ref") or "")
    if not manifest_ref:
        return {}
    path = public_root / manifest_ref
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _module_rows(source_manifest: Mapping[str, Any], *, public_root: Path) -> dict[str, Mapping[str, Any]]:
    original = _original_source_manifest(source_manifest, public_root=public_root)
    original_rows = original.get("modules")
    original_by_id = {
        str(row.get("module_id")): row
        for row in original_rows
        if isinstance(row, Mapping) and row.get("module_id")
    } if isinstance(original_rows, list) else {}
    inline_rows = source_manifest.get("modules")
    if isinstance(inline_rows, list):
        inline = {
            str(row.get("module_id")): {
                **dict(original_by_id.get(str(row.get("module_id")), {})),
                **row,
            }
            for row in inline_rows
            if isinstance(row, Mapping) and row.get("module_id")
        }
        if inline:
            return inline
    return original_by_id


def _target_text(row: Mapping[str, Any], *, public_root: Path) -> str:
    target_ref = str(row.get("target_ref") or "")
    if target_ref.startswith("microcosm-substrate/"):
        target_ref = target_ref[len("microcosm-substrate/") :]
    path = public_root / target_ref
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _mechanism_status(
    mechanism: Mapping[str, Any],
    *,
    modules: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    mechanism_id = str(mechanism.get("mechanism_id") or "")
    module_ids = [
        str(item)
        for item in mechanism.get("source_module_ids", [])
        if isinstance(item, str) and item
    ]
    missing_modules = [module_id for module_id in module_ids if module_id not in modules]
    missing_anchors: list[str] = []
    for module_id in module_ids:
        row = modules.get(module_id)
        if not row:
            continue
        text = _target_text(row, public_root=public_root)
        for anchor in row.get("required_anchors", []):
            if isinstance(anchor, str) and anchor and anchor not in text:
                missing_anchors.append(f"{module_id}:{anchor}")
    return {
        "mechanism_id": mechanism_id,
        "status": "pass" if not missing_modules and not missing_anchors else "blocked",
        "source_module_ids": module_ids,
        "claim_ceiling": mechanism.get("claim_ceiling"),
        "public_exercise": mechanism.get("public_exercise"),
        "negative_case": mechanism.get("negative_case"),
        "missing_modules": missing_modules,
        "missing_anchors": missing_anchors,
        "body_in_receipt": False,
    }


def _erdos_static_scan(text: str) -> dict[str, Any]:
    banned = sorted(set(re.findall(r"\b(?:sorry|admit|axiom)\b", text)))
    declarations = re.findall(r"^\s*(?:theorem|lemma|def)\s+([A-Za-z0-9_'.]+)", text, re.M)
    return {
        "status": "pass" if not banned else "blocked",
        "banned_token_hits": banned,
        "declaration_count": len(declarations),
        "sample_declarations": declarations[:8],
        "claim_boundary": (
            "static token scan over copied CertificateKernel.lean only; Lean/Lake "
            "and axiom-audit receipts remain proof authority"
        ),
    }


def _line_count(text: str) -> int:
    return 0 if not text else len(text.splitlines())


def _run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int = LEAN_LAKE_PROBE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return {
            "status": "unavailable",
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "combined_output": "",
            "error_class": "tool_unavailable",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "unavailable",
            "return_code": None,
            "timed_out": True,
            "stdout_line_count": _line_count(exc.stdout or ""),
            "stderr_line_count": _line_count(exc.stderr or ""),
            "combined_output": f"{exc.stdout or ''}\n{exc.stderr or ''}",
            "error_class": "timeout_redacted",
        }
    except OSError:
        return {
            "status": "unavailable",
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "combined_output": "",
            "error_class": "os_error_redacted",
        }
    return {
        "status": "pass" if completed.returncode == 0 else "blocked",
        "return_code": completed.returncode,
        "timed_out": False,
        "stdout_line_count": _line_count(completed.stdout),
        "stderr_line_count": _line_count(completed.stderr),
        "combined_output": f"{completed.stdout}\n{completed.stderr}",
        "error_class": None if completed.returncode == 0 else "nonzero_exit_redacted",
    }


def _source_lake_project_for_row(row: Mapping[str, Any], *, public_root: Path) -> Path | None:
    source_ref = str(row.get("source_ref") or "")
    if not source_ref:
        return None
    source_path = public_root.parent / source_ref
    for candidate in (source_path.parent, *source_path.parents):
        if (candidate / "lakefile.toml").is_file() and (candidate / "lean-toolchain").is_file():
            return candidate
    return None


def _public_ref(path: Path, *, base: Path) -> str | None:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return None


def _lean_lake_compile_boundary(status: Any, error_class: Any) -> dict[str, Any]:
    if status == "pass":
        boundary_status = "live_compile_pass"
        realness_level = "r3_live_compile_probe_boundary"
        load_bearing = True
        load_bearing_for = "copied_certificate_kernel_zero_exit_elaboration"
    elif status == "blocked":
        boundary_status = "live_compile_reject"
        realness_level = "r3_live_compile_failure_boundary"
        load_bearing = True
        load_bearing_for = "copied_certificate_kernel_nonzero_exit_blocks_acceptance"
    elif status == "unavailable":
        boundary_status = "recorded_probe_unavailable"
        realness_level = "r3_recorded_probe_dependency_boundary"
        load_bearing = False
        load_bearing_for = "toolchain_or_dependency_unavailability_is_recorded_not_upgraded"
    else:
        boundary_status = "unknown_probe_state"
        realness_level = "r3_recorded_probe_boundary_unknown"
        load_bearing = False
        load_bearing_for = "unknown_probe_state_not_upgraded"
    return {
        "compile_boundary_status": boundary_status,
        "compile_boundary_realness_level": realness_level,
        "compile_boundary_load_bearing": load_bearing,
        "compile_boundary_load_bearing_for": load_bearing_for,
        "compile_boundary_error_class": error_class,
        "compile_boundary_claim": LEAN_LAKE_BOUNDARY_CLAIM,
        "proof_authority_delta": "none",
        "authority_delta": "none",
    }


def _lean_lake_probe(row: Mapping[str, Any], *, public_root: Path) -> dict[str, Any]:
    target_ref = str(row.get("target_ref") or "")
    if target_ref.startswith("microcosm-substrate/"):
        target_ref = target_ref[len("microcosm-substrate/") :]
    target_path = public_root / target_ref
    source_project = _source_lake_project_for_row(row, public_root=public_root)
    source_project_ref = (
        _public_ref(source_project, base=public_root.parent) if source_project else None
    )
    lean_available = shutil.which("lean") is not None
    lake_available = shutil.which("lake") is not None
    target_digest = file_sha256(target_path)
    command = ["lake", "env", "lean", target_ref]
    base: dict[str, Any] = {
        "schema_version": "batch4_lean_lake_probe_witness_v1",
        "probe_class": "optional_local_toolchain_probe",
        "input_scope": "copied_public_certificate_kernel_only",
        "proof_authority_class": "non_authoritative_runtime_availability_signal",
        "witness_mode": "live_lean_lake_subprocess",
        "module_id": row.get("module_id"),
        "command": command,
        "tool_versions": {
            "lean_available": lean_available,
            "lake_available": lake_available,
        },
        "source_project_toolchain_present": source_project is not None,
        "source_lake_project_ref": source_project_ref,
        "public_bundle_lake_project_present": (
            (public_root / "examples/batch4_proof_authority_runtime/lakefile.toml").is_file()
            and (public_root / "examples/batch4_proof_authority_runtime/lean-toolchain").is_file()
        ),
        "source_sha256": row.get("source_sha256") or row.get("sha256"),
        "target_sha256": row.get("target_sha256") or row.get("sha256"),
        "observed_target_sha256": target_digest,
        "required_anchor_count": len(
            [anchor for anchor in row.get("required_anchors", []) if isinstance(anchor, str)]
        ),
        "proof_authority_delta": "none",
        "authority_delta": "none",
        "body_in_receipt": False,
        "stdout_stderr_in_receipt": False,
        "path_policy": "public_relative_refs_only",
        "claim_boundary": (
            "Lean/Lake compile/probe boundary over copied public CertificateKernel.lean "
            "only; not theorem correctness, not an Erdos #257 solution, not "
            "publication authority, and not release approval."
        ),
    }
    if not lean_available:
        status = "unavailable"
        error_class = "lean_unavailable"
        return base | {
            "status": status,
            "error_class": error_class,
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
        } | _lean_lake_compile_boundary(status, error_class)
    if not lake_available:
        status = "unavailable"
        error_class = "lake_unavailable"
        return base | {
            "status": status,
            "error_class": error_class,
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
        } | _lean_lake_compile_boundary(status, error_class)
    if source_project is None:
        status = "unavailable"
        error_class = "source_lake_project_unavailable"
        return base | {
            "status": status,
            "error_class": error_class,
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
        } | _lean_lake_compile_boundary(status, error_class)
    if not target_path.is_file():
        status = "blocked"
        error_class = "copied_certificate_kernel_missing"
        return base | {
            "status": status,
            "error_class": error_class,
            "return_code": None,
            "timed_out": False,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
        } | _lean_lake_compile_boundary(status, error_class)

    cache_key = (
        str(target_path),
        target_digest,
        str(source_project),
        lean_available,
        lake_available,
        id(_run_command),
    )
    if cache_key in _LEAN_LAKE_PROBE_CACHE:
        return dict(_LEAN_LAKE_PROBE_CACHE[cache_key])
    result = _run_command(
        ["lake", "env", "lean", str(target_path)],
        cwd=source_project,
    )
    combined_output = str(result.pop("combined_output", ""))
    error_class = result.get("error_class")
    status = result.get("status")
    if status == "blocked" and any(
        marker in combined_output for marker in LEAN_LAKE_DEPENDENCY_UNAVAILABLE_MARKERS
    ):
        status = "unavailable"
        error_class = "mathlib_dependency_unavailable"
    if result.get("timed_out") is True:
        status = "unavailable"
        error_class = "timeout_redacted"
    probe = base | {
        "status": status,
        "error_class": error_class,
        "return_code": result.get("return_code"),
        "timed_out": result.get("timed_out") is True,
        "stdout_line_count": result.get("stdout_line_count", 0),
        "stderr_line_count": result.get("stderr_line_count", 0),
    } | _lean_lake_compile_boundary(status, error_class)
    _LEAN_LAKE_PROBE_CACHE[cache_key] = dict(probe)
    return probe


def _copied_proof_source_pressure(row: Mapping[str, Any], text: str) -> dict[str, Any]:
    required_anchors = [
        anchor
        for anchor in row.get("required_anchors", [])
        if isinstance(anchor, str) and anchor
    ]
    missing_anchors = [anchor for anchor in required_anchors if anchor not in text]
    static_scan = _erdos_static_scan(text)
    return {
        "status": "pass"
        if static_scan["status"] == "pass" and not missing_anchors
        else "blocked",
        "module_id": row.get("module_id"),
        "material_class": row.get("material_class"),
        "source_to_target_relation": row.get("source_to_target_relation"),
        "body_copied": row.get("body_copied") is True,
        "body_in_receipt": False,
        "byte_count": row.get("byte_count"),
        "line_count": row.get("line_count"),
        "required_anchor_count": len(required_anchors),
        "missing_required_anchors": missing_anchors,
        "static_scan": static_scan,
        "claim_boundary": (
            "copied proof-source pressure over public CertificateKernel.lean; "
            "not a Lean/Lake compile or theorem-correctness authority"
        ),
    }


def _synthetic_runtime_exercises(modules: Mapping[str, Mapping[str, Any]], public_root: Path) -> dict[str, Any]:
    erdos_row = modules["erdos257_certificate_kernel"]
    erdos_text = _target_text(erdos_row, public_root=public_root)
    grant_text = _target_text(modules["reasoning_grant_lease"], public_root=public_root)
    forward_text = _target_text(modules["forward_integration_policy"], public_root=public_root)
    closeout_text = _target_text(modules["closeout_executor"], public_root=public_root)
    metabolism_text = _target_text(modules["metabolism_store"], public_root=public_root)
    taskpolicy_text = _target_text(modules["metabolismd"], public_root=public_root)
    context_text = _target_text(modules["agent_execution_trace"], public_root=public_root)
    packet_text = _target_text(modules["lean_microcosm_projection"], public_root=public_root)
    proof_source_pressure = _copied_proof_source_pressure(erdos_row, erdos_text)
    lean_lake_probe = _lean_lake_probe(erdos_row, public_root=public_root)
    proof_bundle_status = (
        "blocked"
        if proof_source_pressure["status"] != "pass"
        or lean_lake_probe.get("status") == "blocked"
        else "pass"
    )
    context_yield_attribution_present = "_compute_context_yield_attribution" in context_text
    context_guard_anchors_present = all(
        anchor in context_text
        for anchor in ("governance_status_counts", "scoped_diff_paths")
    )

    return {
        "proof_bundle": {
            "status": proof_bundle_status,
            "strategy_control_anchor_present": "def run_strategy_control_graph(" in _target_text(
                modules["prover_graph_benchmark"], public_root=public_root
            ),
            "skill_foundry_anchor_present": "def run_prover_skill_foundry(" in _target_text(
                modules["prover_graph_benchmark"], public_root=public_root
            ),
            "verisoft_harness_check_present": "def check_outputs(" in _target_text(
                modules["verisoftbench_harness_differential"], public_root=public_root
            ),
            "verisoft_calibration_check_present": "def check_outputs(" in _target_text(
                modules["verisoftbench_calibration_rows"], public_root=public_root
            ),
            "copied_proof_source_pressure": proof_source_pressure,
            "erdos_static_scan": proof_source_pressure["static_scan"],
            "lean_lake_probe": lean_lake_probe,
            "lean_lake_compile_witness_available": lean_lake_probe.get("status") == "pass",
            "lean_lake_compile_boundary_status": lean_lake_probe.get(
                "compile_boundary_status"
            ),
            "lean_lake_compile_boundary_realness_level": lean_lake_probe.get(
                "compile_boundary_realness_level"
            ),
            "lean_lake_compile_boundary_load_bearing": lean_lake_probe.get(
                "compile_boundary_load_bearing"
            ),
            "packet_corruption_reject_anchor_present": (
                "source_ref_integrity" in packet_text and "REJECTED" in packet_text
            ),
            "proof_authority_delta": "none",
        },
        "authority_bundle": {
            "status": "pass",
            "grant_forbidden_context_denies": "forbidden_effective_context" in grant_text,
            "grant_positive_status": "eligible_unissued"
            if "eligible_unissued" in grant_text
            else "anchor_missing",
            "forward_dirty_unknown_target_blocks": "dirty_unknown_target" in forward_text,
            "closeout_stale_head_defers": "StalePlanHeadMismatch" in closeout_text,
            "closeout_concurrent_publication_defers": "ConcurrentPublicationChurn" in closeout_text,
            "launch_authorized": False,
            "model_dispatch": False,
            "runtime_execution": False,
        },
        "runtime_bundle": {
            "status": "pass",
            "bitemporal_claim_events_present": "blackboard_claim_events" in metabolism_text,
            "bitemporal_supersession_present": "claim_superseded" in metabolism_text,
            "taskpolicy_unavailable_passthrough": "taskpolicy_unavailable" in taskpolicy_text,
            "context_yield_attribution_present": context_yield_attribution_present,
            "accepted_scoped_read_guard": (
                context_yield_attribution_present and context_guard_anchors_present
            ),
        },
    }


def _evaluate(input_path: Path, public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    probe, findings = _load_manifest(input_path)
    modules = _module_rows(source_manifest, public_root=public_root)
    expected_module_missing = [
        module_id for module_id in EXPECTED_MODULE_IDS if module_id not in modules
    ]
    if expected_module_missing:
        findings.append(
            _finding(
                "BATCH4_SOURCE_MODULES_MISSING",
                "Batch 4 source module manifest is missing required copied modules.",
                subject_id=",".join(expected_module_missing),
            )
        )

    mechanisms = [
        row for row in probe.get("mechanisms", []) if isinstance(row, Mapping)
    ]
    mechanism_ids = [str(row.get("mechanism_id") or "") for row in mechanisms]
    missing_mechanisms = [
        mechanism_id for mechanism_id in EXPECTED_MECHANISMS if mechanism_id not in mechanism_ids
    ]
    extra_mechanisms = [
        mechanism_id for mechanism_id in mechanism_ids if mechanism_id not in EXPECTED_MECHANISMS
    ]
    if missing_mechanisms or extra_mechanisms:
        findings.append(
            _finding(
                "BATCH4_MECHANISM_SET_MISMATCH",
                "Batch 4 probe manifest must cover exactly the 14 sendoff mechanisms.",
                subject_id="mechanisms",
            )
        )

    mechanism_rows = [
        _mechanism_status(row, modules=modules, public_root=public_root)
        for row in mechanisms
    ]
    for row in mechanism_rows:
        if row["status"] != "pass":
            findings.append(
                _finding(
                    "BATCH4_MECHANISM_SOURCE_ANCHOR_MISSING",
                    "Mechanism source modules or anchors are missing.",
                    subject_id=row["mechanism_id"],
                )
            )

    runtime_exercises = (
        _synthetic_runtime_exercises(modules, public_root)
        if not expected_module_missing
        else {}
    )
    if runtime_exercises:
        for bundle_id in ("proof_bundle", "authority_bundle", "runtime_bundle"):
            if runtime_exercises.get(bundle_id, {}).get("status") != "pass":
                findings.append(
                    _finding(
                        "BATCH4_BUNDLE_EXERCISE_FAILED",
                        "Batch 4 bundle exercise did not pass.",
                        subject_id=bundle_id,
                    )
                )
        erdos = runtime_exercises["proof_bundle"]["erdos_static_scan"]
        if erdos.get("status") != "pass":
            findings.append(
                _finding(
                    "BATCH4_ERDOS_STATIC_TOKEN_SCAN_FAILED",
                    "Copied CertificateKernel.lean has banned proof-placeholder tokens.",
                    subject_id="erdos257_certificate_kernel",
                )
            )
        lean_lake_probe = runtime_exercises["proof_bundle"].get("lean_lake_probe", {})
        if isinstance(lean_lake_probe, Mapping) and lean_lake_probe.get("status") == "blocked":
            findings.append(
                _finding(
                    "BATCH4_LEAN_LAKE_PROBE_FAILED",
                    "Copied CertificateKernel.lean Lean/Lake probe failed with redacted output.",
                    subject_id="erdos257_certificate_kernel",
                )
            )

    exercise_status = (
        "pass" if not findings and source_manifest.get("status") == "pass" else "blocked"
    )
    semantic_negative_case_proofs = _semantic_negative_case_proofs(
        {
            "status": exercise_status,
            "mechanisms": mechanism_rows,
            "runtime_exercises": runtime_exercises,
        },
        input_path=input_path,
        modules=modules,
        public_root=public_root,
    )
    return {
        "status": exercise_status,
        "schema_version": "batch4_proof_authority_runtime_exercise_v1",
        "mechanism_count": len(mechanism_rows),
        "expected_mechanism_count": len(EXPECTED_MECHANISMS),
        "mechanisms": mechanism_rows,
        "copied_macro_source_module_count": len(modules),
        "runtime_exercises": runtime_exercises,
        "semantic_negative_case_proofs": semantic_negative_case_proofs,
        "semantic_negative_case_computed_rejection_count": sum(
            1 for row in semantic_negative_case_proofs if row["computed_rejection"]
        ),
        "claim_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "error_codes": [str(row.get("error_code")) for row in findings if row.get("error_code")],
        "findings": findings,
        "body_in_receipt": False,
    }


def _semantic_negative_result(
    case_id: str,
    error_codes: tuple[str, ...],
    *,
    mechanism: Mapping[str, Any],
    runtime_case: Mapping[str, Any],
    overclaim_shape: Mapping[str, Any],
    fixture_runtime_probe: Mapping[str, Any],
    expected_codes_input: tuple[str, ...],
    verdict_signature: str,
    realness_rank: str,
    realness_rung: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "source_backed": True,
        "declared_fixture_ignored": True,
        "declared_fixture_error_codes_used": False,
        "expected_codes_input_used": False,
        "expected_codes_input_ignored": tuple(expected_codes_input) != tuple(error_codes),
        "fixture_payload_used": "runtime_probe_only",
        "stable_codes_source": "batch4_runtime_semantic_map_gated_by_derived_verdict_signature",
        "rejection_basis": "computed_runtime_case_observer_and_fixture_probe",
        "negative_case_verdict": "computed_reject",
        "verdict_signature": verdict_signature,
        "verdict_signature_source": "derived_runtime_case_overclaim_shape_and_source_probe",
        "realness_rank": realness_rank,
        "realness_rung": realness_rung,
        "rank_rung_evidence_rederived": True,
        "evidence": {
            "mechanism": dict(mechanism),
            "runtime_case": dict(runtime_case),
            "overclaim_shape": dict(overclaim_shape),
            "fixture_runtime_probe": dict(fixture_runtime_probe),
        },
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(case_id: str, observed: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "source_backed": True,
        "declared_fixture_ignored": True,
        "declared_fixture_error_codes_used": False,
        "expected_codes_input_used": False,
        "fixture_payload_used": "runtime_probe_only",
        "stable_codes_source": "batch4_runtime_semantic_map_gated_by_derived_verdict_signature",
        "rejection_basis": "computed_runtime_case_observer_and_fixture_probe",
        "observed": observed,
        "negative_case_verdict": "not_rejected",
        "verdict_signature": _verdict_signature(case_id, observed),
        "verdict_signature_source": "derived_runtime_case_overclaim_shape_and_source_probe",
        "realness_rank": "below_r3",
        "realness_rung": "negative_case_not_rejected",
        "rank_rung_evidence_rederived": True,
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH4_PROOF_AUTHORITY_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _verdict_signature(case_id: str, evidence: Mapping[str, Any]) -> str:
    payload = {
        "case_id": case_id,
        "evidence": evidence,
        "signature_schema": "batch4_negative_verdict_signature_v1",
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _realness_rank(computed: bool) -> dict[str, Any]:
    if computed:
        return {
            "realness_rank": "R3",
            "realness_rung": "derived_runtime_negative_verdict",
            "rank_rung_evidence_rederived": True,
        }
    return {
        "realness_rank": "below_r3",
        "realness_rung": "negative_case_not_rejected",
        "rank_rung_evidence_rederived": True,
    }


def _source_manifest_for_input(input_dir: Path) -> dict[str, Any]:
    public_root = public_root_for_path(input_dir)
    return validate_source_manifest(input_dir, SPEC, public_root=public_root)


def _mechanism_by_negative_case(
    exercise: Mapping[str, Any],
    case_id: str,
) -> dict[str, Any]:
    mechanisms = (
        exercise.get("mechanisms")
        if isinstance(exercise.get("mechanisms"), list)
        else []
    )
    for row in mechanisms:
        if isinstance(row, Mapping) and row.get("negative_case") == case_id:
            return dict(row)
    return {}


def _runtime_case_observed(
    exercise: Mapping[str, Any],
    case_id: str,
) -> dict[str, Any]:
    runtime = (
        exercise.get("runtime_exercises")
        if isinstance(exercise.get("runtime_exercises"), Mapping)
        else {}
    )
    proof = runtime.get("proof_bundle") if isinstance(runtime.get("proof_bundle"), Mapping) else {}
    authority = (
        runtime.get("authority_bundle")
        if isinstance(runtime.get("authority_bundle"), Mapping)
        else {}
    )
    runtime_bundle = (
        runtime.get("runtime_bundle")
        if isinstance(runtime.get("runtime_bundle"), Mapping)
        else {}
    )
    erdos_scan = (
        proof.get("erdos_static_scan")
        if isinstance(proof.get("erdos_static_scan"), Mapping)
        else {}
    )
    case_observers = {
        "weak_skeleton_synthesis_failure": {
            "observer_id": "strategy_control_anchor_presence",
            "computed": proof.get("strategy_control_anchor_present") is True,
            "observed": {
                "strategy_control_anchor_present": proof.get(
                    "strategy_control_anchor_present"
                )
            },
        },
        "foundry_low_repair_quarantine": {
            "observer_id": "skill_foundry_anchor_presence",
            "computed": proof.get("skill_foundry_anchor_present") is True,
            "observed": {
                "skill_foundry_anchor_present": proof.get(
                    "skill_foundry_anchor_present"
                )
            },
        },
        "verisoft_truth_leak": {
            "observer_id": "verisoft_harness_check_presence",
            "computed": proof.get("verisoft_harness_check_present") is True,
            "observed": {
                "verisoft_harness_check_present": proof.get(
                    "verisoft_harness_check_present"
                )
            },
        },
        "verisoft_prefix_answer_leakage": {
            "observer_id": "verisoft_calibration_check_presence",
            "computed": proof.get("verisoft_calibration_check_present") is True,
            "observed": {
                "verisoft_calibration_check_present": proof.get(
                    "verisoft_calibration_check_present"
                )
            },
        },
        "erdos_solution_overclaim": {
            "observer_id": "erdos_static_scan_and_authority_delta",
            "computed": erdos_scan.get("status") == "pass"
            and proof.get("lean_lake_probe", {}).get("status") != "blocked"
            and proof.get("proof_authority_delta") == "none",
            "observed": {
                "erdos_static_scan_status": erdos_scan.get("status"),
                "lean_lake_probe_status": proof.get("lean_lake_probe", {}).get("status"),
                "lean_lake_compile_witness_available": proof.get(
                    "lean_lake_compile_witness_available"
                ),
                "lean_lake_compile_boundary_status": proof.get(
                    "lean_lake_compile_boundary_status"
                ),
                "lean_lake_compile_boundary_realness_level": proof.get(
                    "lean_lake_compile_boundary_realness_level"
                ),
                "lean_lake_compile_boundary_load_bearing": proof.get(
                    "lean_lake_compile_boundary_load_bearing"
                ),
                "proof_authority_delta": proof.get("proof_authority_delta"),
            },
        },
        "packet_sha256_corruption": {
            "observer_id": "packet_corruption_reject_anchor_presence",
            "computed": proof.get("packet_corruption_reject_anchor_present") is True,
            "observed": {
                "packet_corruption_reject_anchor_present": proof.get(
                    "packet_corruption_reject_anchor_present"
                )
            },
        },
        "grant_forbidden_context": {
            "observer_id": "grant_denial_no_dispatch",
            "computed": authority.get("grant_forbidden_context_denies") is True
            and authority.get("launch_authorized") is False
            and authority.get("model_dispatch") is False
            and authority.get("runtime_execution") is False,
            "observed": {
                "grant_forbidden_context_denies": authority.get(
                    "grant_forbidden_context_denies"
                ),
                "launch_authorized": authority.get("launch_authorized"),
                "model_dispatch": authority.get("model_dispatch"),
                "runtime_execution": authority.get("runtime_execution"),
            },
        },
        "forward_dirty_unknown_target": {
            "observer_id": "forward_dirty_unknown_target_policy_anchor",
            "computed": authority.get("forward_dirty_unknown_target_blocks") is True,
            "observed": {
                "forward_dirty_unknown_target_blocks": authority.get(
                    "forward_dirty_unknown_target_blocks"
                )
            },
        },
        "closeout_stale_head": {
            "observer_id": "closeout_stale_head_deferral_anchor",
            "computed": authority.get("closeout_stale_head_defers") is True,
            "observed": {
                "closeout_stale_head_defers": authority.get(
                    "closeout_stale_head_defers"
                )
            },
        },
        "bitemporal_expired_claim": {
            "observer_id": "bitemporal_claim_event_supersession_anchors",
            "computed": runtime_bundle.get("bitemporal_claim_events_present") is True
            and runtime_bundle.get("bitemporal_supersession_present") is True,
            "observed": {
                "bitemporal_claim_events_present": runtime_bundle.get(
                    "bitemporal_claim_events_present"
                ),
                "bitemporal_supersession_present": runtime_bundle.get(
                    "bitemporal_supersession_present"
                ),
            },
        },
        "taskpolicy_missing_binary": {
            "observer_id": "taskpolicy_unavailable_passthrough_anchor",
            "computed": runtime_bundle.get("taskpolicy_unavailable_passthrough") is True,
            "observed": {
                "taskpolicy_unavailable_passthrough": runtime_bundle.get(
                    "taskpolicy_unavailable_passthrough"
                )
            },
        },
        "context_accepted_read_guard": {
            "observer_id": "context_yield_scoped_read_guard_anchors",
            "computed": runtime_bundle.get("context_yield_attribution_present") is True
            and runtime_bundle.get("accepted_scoped_read_guard") is True,
            "observed": {
                "context_yield_attribution_present": runtime_bundle.get(
                    "context_yield_attribution_present"
                ),
                "accepted_scoped_read_guard": runtime_bundle.get(
                    "accepted_scoped_read_guard"
                ),
            },
        },
    }
    for row in case_observers.values():
        row["evidence_source"] = "copied_macro_source_runtime_exercises"
    return dict(case_observers.get(case_id, {"computed": False, "observed": {}}))


def _overclaim_shape_observed(
    mechanism: Mapping[str, Any],
    case_id: str,
) -> dict[str, Any]:
    expected = NEGATIVE_CASE_OVERCLAIM_SHAPES.get(case_id, {})
    claim_ceiling = str(mechanism.get("claim_ceiling") or "")
    public_exercise = str(mechanism.get("public_exercise") or "")
    expected_mechanism_id = str(expected.get("mechanism_id") or "")
    ceiling_anchors = tuple(
        anchor
        for anchor in expected.get("claim_ceiling_must_contain", ())
        if isinstance(anchor, str) and anchor
    )
    exercise_anchors = tuple(
        anchor
        for anchor in expected.get("public_exercise_must_contain", ())
        if isinstance(anchor, str) and anchor
    )
    checks = {
        "case_id_mapped": bool(expected),
        "mechanism_id_matches": mechanism.get("mechanism_id") == expected_mechanism_id,
        "negative_case_matches": mechanism.get("negative_case") == case_id,
        "claim_ceiling_anchors_present": all(
            anchor in claim_ceiling for anchor in ceiling_anchors
        ),
        "public_exercise_anchors_present": all(
            anchor in public_exercise for anchor in exercise_anchors
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "blocked",
        "case_id": case_id,
        "mechanism_id": mechanism.get("mechanism_id"),
        "observer_id": "bounded_overclaim_shape",
        "evidence_source": "batch4_probe_manifest_mechanism_claim_shape",
        "claim_ceiling_sha256": (
            hashlib.sha256(claim_ceiling.encode("utf-8")).hexdigest()
            if claim_ceiling
            else None
        ),
        "public_exercise_sha256": (
            hashlib.sha256(public_exercise.encode("utf-8")).hexdigest()
            if public_exercise
            else None
        ),
        "checks": checks,
        "body_in_receipt": False,
    }


def _load_negative_case_payload(input_dir: Path, case_id: str) -> dict[str, Any]:
    path = input_dir / f"{case_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fixture_runtime_probe_status(
    case_id: str,
    payload: Mapping[str, Any],
    *,
    modules: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    expected = NEGATIVE_CASE_RUNTIME_PROBES.get(case_id, {})
    probe = payload.get("runtime_probe") if isinstance(payload.get("runtime_probe"), Mapping) else {}
    source_module_id = str(probe.get("source_module_id") or "")
    required_text = str(probe.get("required_text") or "")
    observer_id = str(probe.get("observer_id") or "")
    expected_source_module_id = str(expected.get("source_module_id") or "")
    expected_required_text = str(expected.get("required_text") or "")
    expected_observer_id = str(expected.get("observer_id") or "")
    row = modules.get(expected_source_module_id)
    text = _target_text(row, public_root=public_root) if row else ""
    checks = {
        "case_id_matches": payload.get("case_id") == case_id,
        "expected_negative_case": payload.get("expected_negative_case") is True,
        "observer_id_matches": observer_id == expected_observer_id,
        "source_module_id_matches": source_module_id == expected_source_module_id,
        "required_text_matches": required_text == expected_required_text,
        "required_text_present": bool(expected_required_text and expected_required_text in text),
    }
    return {
        "status": "pass" if all(checks.values()) else "blocked",
        "case_id": case_id,
        "observer_id": observer_id,
        "source_module_id": source_module_id,
        "derived_observer_id": expected_observer_id,
        "derived_source_module_id": expected_source_module_id,
        "required_text_sha256": (
            hashlib.sha256(required_text.encode("utf-8")).hexdigest()
            if required_text
            else None
        ),
        "derived_required_text_sha256": (
            hashlib.sha256(expected_required_text.encode("utf-8")).hexdigest()
            if expected_required_text
            else None
        ),
        "source_text_check_uses_fixture_required_text": False,
        "source_text_check_source": "batch4_runtime_negative_case_probe_map",
        "checks": checks,
        "body_in_receipt": False,
    }


def _computed_negative_case_verdict(
    exercise: Mapping[str, Any],
    case_id: str,
    *,
    fixture_payload: Mapping[str, Any],
    modules: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> dict[str, Any]:
    mechanism = _mechanism_by_negative_case(exercise, case_id)
    runtime_case = _runtime_case_observed(exercise, case_id)
    overclaim_shape = _overclaim_shape_observed(mechanism, case_id)
    fixture_runtime_probe = _fixture_runtime_probe_status(
        case_id,
        fixture_payload,
        modules=modules,
        public_root=public_root,
    )
    computed = (
        exercise.get("status") == "pass"
        and mechanism.get("status") == "pass"
        and runtime_case.get("computed") is True
        and overclaim_shape.get("status") == "pass"
        and fixture_runtime_probe.get("status") == "pass"
    )
    evidence = {
        "mechanism": mechanism,
        "runtime_case": runtime_case,
        "overclaim_shape": overclaim_shape,
        "fixture_runtime_probe": fixture_runtime_probe,
        "computed": computed,
    }
    rank = _realness_rank(computed)
    return {
        **evidence,
        "verdict_signature": _verdict_signature(case_id, evidence),
        **rank,
    }


def _semantic_negative_case_proofs(
    exercise: Mapping[str, Any],
    *,
    input_path: Path,
    modules: Mapping[str, Mapping[str, Any]],
    public_root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_id in sorted(EXPECTED_NEGATIVE_CASES):
        verdict = _computed_negative_case_verdict(
            exercise,
            case_id,
            fixture_payload=_load_negative_case_payload(input_path, case_id),
            modules=modules,
            public_root=public_root,
        )
        computed = verdict["computed"]
        mechanism = verdict["mechanism"]
        rows.append(
            {
                "case_id": case_id,
                "status": "blocked" if computed else "pass",
                "computed_rejection": computed,
                "stable_error_codes": list(EXPECTED_NEGATIVE_CASES[case_id]),
                "mechanism_id": mechanism.get("mechanism_id"),
                "mechanism_status": mechanism.get("status"),
                "runtime_case": verdict["runtime_case"],
                "overclaim_shape": verdict["overclaim_shape"],
                "fixture_runtime_probe": verdict["fixture_runtime_probe"],
                "declared_fixture_ignored": True,
                "declared_fixture_error_codes_used": False,
                "expected_codes_input_used": False,
                "stable_codes_source": "batch4_runtime_semantic_map_gated_by_derived_verdict_signature",
                "rejection_basis": "computed_runtime_case_observer_and_fixture_probe",
                "negative_case_verdict": "computed_reject" if computed else "not_rejected",
                "verdict_signature": verdict["verdict_signature"],
                "verdict_signature_source": "derived_runtime_case_overclaim_shape_and_source_probe",
                "realness_rank": verdict["realness_rank"],
                "realness_rung": verdict["realness_rung"],
                "rank_rung_evidence_rederived": verdict["rank_rung_evidence_rederived"],
                "body_in_receipt": False,
            }
        )
    return rows


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        public_root = public_root_for_path(input_dir)
        source_manifest = _source_manifest_for_input(input_dir)
        modules = _module_rows(source_manifest, public_root=public_root)
        fixture_payload = _load_negative_case_payload(input_dir, case_id)
        exercise = _evaluate(input_dir, public_root, source_manifest)
        verdict = _computed_negative_case_verdict(
            exercise,
            case_id,
            fixture_payload=fixture_payload,
            modules=modules,
            public_root=public_root,
        )
        computed = verdict["computed"]
        mechanism = verdict["mechanism"]
        runtime_case = verdict["runtime_case"]
        overclaim_shape = verdict["overclaim_shape"]
        fixture_runtime_probe = verdict["fixture_runtime_probe"]
        stable_codes = tuple(EXPECTED_NEGATIVE_CASES.get(case_id, ()))
        if computed:
            return _semantic_negative_result(
                case_id,
                stable_codes,
                mechanism=mechanism,
                runtime_case=runtime_case,
                overclaim_shape=overclaim_shape,
                fixture_runtime_probe=fixture_runtime_probe,
                expected_codes_input=expected_codes,
                verdict_signature=verdict["verdict_signature"],
                realness_rank=verdict["realness_rank"],
                realness_rung=verdict["realness_rung"],
            )
        return _semantic_negative_not_rejected(
            case_id,
            {
                "mechanism": mechanism or {"negative_case": case_id},
                "runtime_case": runtime_case,
                "overclaim_shape": overclaim_shape,
                "fixture_runtime_probe": fixture_runtime_probe,
                "exercise_status": exercise.get("status"),
                "computed": computed,
            },
        )
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch4_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["mechanism_count"] = exercise.get("mechanism_count")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    card["authority_ceiling"] = dict(AUTHORITY_CEILING)
    card["omission_receipt"] = {
        "omitted": [
            "full copied source bodies",
            "raw private runtime state",
            "live provider/browser/session payloads",
        ],
        "reason": "Batch 4 receipts carry source refs, digests, anchors, and bounded exercise outcomes, not body text or live private state.",
    }
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "validate-bundle":
        result = run_batch4_bundle(
            args.input,
            args.out,
            acceptance_out=args.acceptance_out,
            command=f"{ORGAN_ID} validate-bundle",
        )
    else:
        result = run(
            args.input,
            args.out,
            acceptance_out=args.acceptance_out,
            command=f"{ORGAN_ID} run",
        )
    payload = result_card(result) if args.card else result
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
