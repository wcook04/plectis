#!/usr/bin/env python3
"""Run local evaluator-backed rows for the VeriSoftBench micro-10 slice.

This is the execution layer below the external calibration board.  It does not
call a provider.  It materializes each row from the no-solve manifest, extracts
the pre-target support prefix from the pinned ArkLib workspace, and runs a small
Lean probe suite.  Provider output remains separate; solved means Lean accepts a
generated row proof body.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import build_external_benchmark_calibration_spine as calibration
from tools.meta.factory import build_formal_math_statement_scope_support as scope_support


SCHEMA_VERSION = "external_benchmark_row_execution_receipt_v0"
MANIFEST_SCHEMA_VERSION = "external_benchmark_row_execution_manifest_v0"
CHECK_SCHEMA_VERSION = "external_benchmark_row_execution_check_v0"
OWNER_ID = calibration.OWNER_ID
WORK_ITEM_ID = calibration.WORK_ITEM_ID
BENCHMARK_MANIFEST_PATH = Path("state/benchmarks/verisoftbench_no_solve_manifest_v0/manifest.json")
RUN_ROOT = calibration.RUN_ROOT
ROW_EXECUTION_ROOT = calibration.CALIBRATION_ROOT / "row_execution"
ROW_EXECUTION_MANIFEST_PATH = ROW_EXECUTION_ROOT / "row_execution_manifest.json"
ROW_RECEIPT_NAME = "row_execution_receipt.json"
STATEMENT_CHECK_NAME = "statement_scope_check.lean"
STATEMENT_STDOUT_NAME = "statement_scope_check_stdout.txt"
STATEMENT_STDERR_NAME = "statement_scope_check_stderr.txt"
SUPPORT_PREFIX_NAME = "pretarget_scope_support.lean"
CLAIM_BOUNDARY = "micro_slice_row_execution_not_official_benchmark_score"

LOCAL_PROBES: tuple[tuple[str, str], ...] = (
    ("simp", "  simp"),
    ("simp_all", "  simp_all"),
    ("omega", "  omega"),
    ("aesop", "  aesop"),
    ("first_simp_omega_aesop", "  first\n  | simp\n  | omega\n  | aesop"),
)

BLOCKING_STATUSES = {
    "blocked_not_materialized",
    "blocked_workspace_missing",
    "blocked_source_missing",
    "blocked_target_not_found",
    "blocked_target_declaration_present",
    "blocked_statement_scope",
    "blocked_statement_scope_timeout",
    "blocked_no_reducer",
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _task_slug(task_id: str) -> str:
    return task_id.replace(":", "_")


def row_dir(task_id: str, *, repo_root: Path = REPO_ROOT) -> Path:
    return _repo_path(ROW_EXECUTION_ROOT / _task_slug(task_id), repo_root=repo_root)


def row_receipt_path(task_id: str) -> Path:
    return ROW_EXECUTION_ROOT / _task_slug(task_id) / ROW_RECEIPT_NAME


def _manifest_tasks(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    manifest = _read_json(_repo_path(BENCHMARK_MANIFEST_PATH, repo_root=repo_root))
    rows: dict[str, dict[str, Any]] = {}
    for row in manifest.get("tasks") or []:
        if not isinstance(row, Mapping):
            continue
        raw_id = str(row.get("benchmark_task_id") or "")
        task_id = f"verisoftbench:{raw_id}"
        if task_id in calibration.VERISOFTBENCH_TASK_IDS:
            rows[task_id] = dict(row)
    return rows


def _resolution_rows(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    receipt = _read_json_if_exists(_repo_path(RUN_ROOT / "formal_problem_resolution_receipt.json", repo_root=repo_root))
    rows: dict[str, dict[str, Any]] = {}
    for row in receipt.get("resolved") or []:
        if isinstance(row, Mapping) and isinstance(row.get("task_id"), str):
            rows[str(row["task_id"])] = dict(row)
    return rows


def _workspace_root(*, repo_root: Path) -> Path | None:
    receipt = _read_json_if_exists(_repo_path(RUN_ROOT / "oracle_environment_gate_receipt.json", repo_root=repo_root))
    workspace = receipt.get("workspace") if isinstance(receipt.get("workspace"), Mapping) else {}
    ref = workspace.get("workspace_root")
    if not ref:
        return None
    path = Path(str(ref))
    return path if path.exists() else None


def _model_payload(task: Mapping[str, Any]) -> dict[str, Any]:
    payload = task.get("model_facing_payload")
    return dict(payload) if isinstance(payload, Mapping) else {}


def _short_theorem_name(value: str) -> str:
    stripped = str(value or "").strip()
    return stripped.split(".")[-1] if stripped else ""


def _statement_source(statement: str, proof_body: str) -> str:
    body = proof_body.rstrip()
    header = statement.rstrip()
    if header.endswith(":= by"):
        return f"{header}\n{body}\n"
    if header.endswith(":="):
        return f"{header} by\n{body}\n"
    return f"{header} := by\n{body}\n"


def _candidate_source(*, support_prefix: str, statement: str, proof_body: str, theorem_name: str) -> str:
    print_axioms = _short_theorem_name(theorem_name)
    return "\n".join(
        [
            support_prefix.rstrip(),
            "",
            "/- VeriSoftBench micro-10 row execution probe. -/",
            _statement_source(statement, proof_body).rstrip(),
            "",
            f"#print axioms {print_axioms}",
            "",
        ]
    )


def _run_lake_env_lean(path: Path, *, workspace_root: Path, timeout_seconds: int) -> dict[str, Any]:
    if not shutil.which("lake"):
        return {
            "compile_status": "BLOCKED",
            "exit_code": None,
            "duration_ms": 0,
            "timeout": False,
            "stdout": "",
            "stderr": "lake executable not available",
        }
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            ["lake", "env", "lean", str(path.resolve())],
            cwd=workspace_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "compile_status": "PASS" if process.returncode == 0 else "FAIL",
            "exit_code": process.returncode,
            "duration_ms": duration_ms,
            "timeout": False,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        else:
            stdout, stderr = exc.stdout or "", exc.stderr or ""
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "compile_status": "TIMEOUT",
            "exit_code": None,
            "duration_ms": duration_ms,
            "timeout": True,
            "stdout": stdout or "",
            "stderr": stderr or "",
        }


def _write_lean_result(
    *,
    source_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    result: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    _write_text(stdout_path, str(result.get("stdout") or ""))
    _write_text(stderr_path, str(result.get("stderr") or ""))
    return {
        "lean_source_ref": _rel(source_path, repo_root=repo_root),
        "lean_source_sha256": _sha256_file(source_path),
        "stdout_ref": _rel(stdout_path, repo_root=repo_root),
        "stdout_sha256": _sha256_file(stdout_path),
        "stderr_ref": _rel(stderr_path, repo_root=repo_root),
        "stderr_sha256": _sha256_file(stderr_path),
        "compile_status": result.get("compile_status"),
        "exit_code": result.get("exit_code"),
        "duration_ms": result.get("duration_ms"),
        "timeout": result.get("timeout"),
    }


def _provider_plan_status(resolution_row: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    row_patch_ref = str(resolution_row.get("provider_row_patch_ref") or "")
    receipt_ref = str(resolution_row.get("provider_receipt_ref") or "")
    row_patch = _read_json_if_exists(_repo_path(row_patch_ref, repo_root=repo_root)) if row_patch_ref else {}
    proposed = row_patch.get("proposed_value") if isinstance(row_patch.get("proposed_value"), Mapping) else {}
    return {
        "provider_receipt_ref": receipt_ref or None,
        "provider_row_patch_ref": row_patch_ref or None,
        "provider_output_has_lean_proof_body": isinstance(proposed.get("lean_proof_body"), str),
        "provider_output_kind": (
            "proof_body_candidate" if isinstance(proposed.get("lean_proof_body"), str) else "decision_point_plan_or_nonproof"
        ),
    }


def run_row(
    task_id: str,
    *,
    repo_root: Path = REPO_ROOT,
    timeout_seconds: int = 90,
    max_probes: int | None = None,
) -> dict[str, Any]:
    created_at = _utc_now()
    tasks = _manifest_tasks(repo_root=repo_root)
    resolutions = _resolution_rows(repo_root=repo_root)
    task = tasks.get(task_id)
    resolution = resolutions.get(task_id) or {}
    workspace_root = _workspace_root(repo_root=repo_root)
    out_dir = row_dir(task_id, repo_root=repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "benchmark": "VeriSoftBench",
        "slice_id": "verisoftbench_micro_10_v0",
        "task_id": task_id,
        "work_item_id": WORK_ITEM_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "official_leaderboard_submission": False,
        "public_claim_allowed": False,
        "protocol_arm": "B_support_prefix_direct_probe",
        "attempt_count": 1,
        "provider_dispatch_attempted": False,
        "provider_status": None,
        "accepted_by_lean": False,
        "solved": False,
        "receipt_refs": [],
    }
    if task is None:
        receipt = {
            **base,
            "status": "blocked_not_materialized",
            "materialization_status": "missing_from_no_solve_manifest",
            "failure_class": "blocked_not_materialized",
            "issues": [f"{task_id} not found in {BENCHMARK_MANIFEST_PATH}"],
        }
        _write_json(out_dir / ROW_RECEIPT_NAME, receipt)
        return receipt
    if workspace_root is None:
        receipt = {
            **base,
            "status": "blocked_workspace_missing",
            "materialization_status": "manifest_task_available",
            "failure_class": "blocked_workspace_missing",
            "issues": ["pinned ArkLib workspace missing from oracle environment gate receipt"],
        }
        _write_json(out_dir / ROW_RECEIPT_NAME, receipt)
        return receipt

    model_payload = _model_payload(task)
    rel_path = str(model_payload.get("rel_path") or "")
    theorem_name = str(model_payload.get("theorem_name") or "")
    statement = str(model_payload.get("theorem_statement") or model_payload.get("target_theorem") or "")
    source_path = workspace_root / rel_path
    provider_plan = _provider_plan_status(resolution, repo_root=repo_root) if resolution else {}
    if not source_path.exists():
        receipt = {
            **base,
            "status": "blocked_source_missing",
            "materialization_status": "manifest_task_available",
            "statement_scope_status": "not_run_source_missing",
            "failure_class": "blocked_source_missing",
            "source_metadata": {
                "rel_path": rel_path,
                "source_path": str(source_path),
                "source_exists": False,
            },
            "provider_plan": provider_plan,
        }
        _write_json(out_dir / ROW_RECEIPT_NAME, receipt)
        return receipt

    prefix, extraction = scope_support.extract_pre_target_prefix(
        source_path.read_text(encoding="utf-8"),
        theorem_name=_short_theorem_name(theorem_name),
    )
    support_prefix_path = out_dir / SUPPORT_PREFIX_NAME
    if extraction.get("status") != scope_support.STATUS_READY:
        status = (
            "blocked_target_not_found"
            if extraction.get("status") == scope_support.STATUS_TARGET_NOT_FOUND
            else "blocked_target_declaration_present"
        )
        receipt = {
            **base,
            "status": status,
            "materialization_status": "manifest_task_available",
            "statement_scope_status": extraction.get("status"),
            "failure_class": status,
            "source_metadata": {
                "rel_path": rel_path,
                "source_path": str(source_path),
                "source_exists": True,
                **extraction,
            },
            "provider_plan": provider_plan,
        }
        _write_json(out_dir / ROW_RECEIPT_NAME, receipt)
        return receipt

    _write_text(support_prefix_path, prefix)
    statement_source_path = out_dir / STATEMENT_CHECK_NAME
    statement_source = _candidate_source(
        support_prefix=prefix,
        statement=statement,
        proof_body="  sorry",
        theorem_name=theorem_name,
    )
    _write_text(statement_source_path, statement_source)
    statement_result = _run_lake_env_lean(
        statement_source_path,
        workspace_root=workspace_root,
        timeout_seconds=timeout_seconds,
    )
    statement_check = _write_lean_result(
        source_path=statement_source_path,
        stdout_path=out_dir / STATEMENT_STDOUT_NAME,
        stderr_path=out_dir / STATEMENT_STDERR_NAME,
        result=statement_result,
        repo_root=repo_root,
    )
    if statement_check.get("compile_status") != "PASS":
        scope_timeout = statement_check.get("compile_status") == "TIMEOUT"
        status = "blocked_statement_scope_timeout" if scope_timeout else "blocked_statement_scope"
        receipt = {
            **base,
            "status": status,
            "materialization_status": "manifest_task_available",
            "statement_scope_status": statement_check.get("compile_status"),
            "failure_class": "statement_scope_timeout" if scope_timeout else "blocked_statement_scope",
            "source_metadata": {
                "rel_path": rel_path,
                "source_path": str(source_path),
                "source_exists": True,
                **extraction,
            },
            "support_prefix_ref": _rel(support_prefix_path, repo_root=repo_root),
            "support_prefix_sha256": _sha256_file(support_prefix_path),
            "statement_scope_check": statement_check,
            "provider_plan": provider_plan,
            "receipt_refs": [statement_check.get("lean_source_ref"), statement_check.get("stdout_ref"), statement_check.get("stderr_ref")],
        }
        receipt["receipt_refs"] = [ref for ref in receipt["receipt_refs"] if ref]
        _write_json(out_dir / ROW_RECEIPT_NAME, receipt)
        return receipt

    probe_rows: list[dict[str, Any]] = []
    probes = LOCAL_PROBES[:max_probes] if max_probes is not None else LOCAL_PROBES
    for index, (probe_id, proof_body) in enumerate(probes):
        probe_source_path = out_dir / f"tactic_probe_{index:02d}_{probe_id}.lean"
        probe_source = _candidate_source(
            support_prefix=prefix,
            statement=statement,
            proof_body=proof_body,
            theorem_name=theorem_name,
        )
        _write_text(probe_source_path, probe_source)
        probe_result = _run_lake_env_lean(
            probe_source_path,
            workspace_root=workspace_root,
            timeout_seconds=timeout_seconds,
        )
        probe_row = {
            "probe_id": probe_id,
            "proof_body": proof_body,
            **_write_lean_result(
                source_path=probe_source_path,
                stdout_path=out_dir / f"tactic_probe_{index:02d}_{probe_id}_stdout.txt",
                stderr_path=out_dir / f"tactic_probe_{index:02d}_{probe_id}_stderr.txt",
                result=probe_result,
                repo_root=repo_root,
            ),
        }
        probe_rows.append(probe_row)
        if probe_row.get("compile_status") == "PASS":
            break

    accepted_probe = next((row for row in probe_rows if row.get("compile_status") == "PASS"), None)
    probe_manifest_path = out_dir / "tactic_probe_manifest.json"
    probe_manifest = {
        "schema_version": "external_benchmark_row_tactic_probe_manifest_v0",
        "created_at": _utc_now(),
        "task_id": task_id,
        "probe_count": len(probe_rows),
        "accepted_probe_id": accepted_probe.get("probe_id") if accepted_probe else None,
        "rows": probe_rows,
    }
    _write_json(probe_manifest_path, probe_manifest)
    duration_ms = int(sum(int(row.get("duration_ms") or 0) for row in probe_rows) + int(statement_check.get("duration_ms") or 0))
    probe_status_counts = Counter(str(row.get("compile_status") or "unknown") for row in probe_rows)
    if accepted_probe:
        status = "direct_local_probe_accepted"
        lean_status = "PASS"
        failure_class = "none"
    elif probe_status_counts.get("TIMEOUT"):
        status = "direct_local_probe_timeout_with_receipt"
        lean_status = "TIMEOUT"
        failure_class = "direct_local_probe_timeout"
    else:
        status = "direct_local_probe_rejected_with_receipt"
        lean_status = "FAIL"
        failure_class = "direct_local_probe_rejected"
    receipt = {
        **base,
        "status": status,
        "materialization_status": "manifest_task_available",
        "statement_scope_status": "PASS",
        "lean_status": lean_status,
        "accepted_by_lean": bool(accepted_probe),
        "solved": bool(accepted_probe),
        "failure_class": failure_class,
        "source_metadata": {
            "rel_path": rel_path,
            "source_path": str(source_path),
            "source_exists": True,
            "theorem_name": theorem_name,
            **extraction,
        },
        "support_prefix_ref": _rel(support_prefix_path, repo_root=repo_root),
        "support_prefix_sha256": _sha256_file(support_prefix_path),
        "statement_scope_check": statement_check,
        "direct_local_probes": {
            "probe_manifest_ref": _rel(probe_manifest_path, repo_root=repo_root),
            "probe_count": len(probe_rows),
            "accepted_probe_id": accepted_probe.get("probe_id") if accepted_probe else None,
            "accepted_probe_ref": accepted_probe.get("lean_source_ref") if accepted_probe else None,
            "compile_status_counts": dict(probe_status_counts),
        },
        "duration_ms": duration_ms,
        "provider_plan": provider_plan,
        "receipt_refs": [
            _rel(support_prefix_path, repo_root=repo_root),
            _rel(probe_manifest_path, repo_root=repo_root),
            statement_check.get("lean_source_ref"),
            statement_check.get("stdout_ref"),
            statement_check.get("stderr_ref"),
            provider_plan.get("provider_receipt_ref"),
            provider_plan.get("provider_row_patch_ref"),
        ],
    }
    receipt["receipt_refs"] = [ref for ref in receipt["receipt_refs"] if ref]
    _write_json(out_dir / ROW_RECEIPT_NAME, receipt)
    return receipt


def run_rows(
    *,
    repo_root: Path = REPO_ROOT,
    task_ids: Sequence[str] = calibration.VERISOFTBENCH_TASK_IDS,
    timeout_seconds: int = 90,
    max_consecutive_blockers: int = 3,
    max_probes: int | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    consecutive_blocker: str | None = None
    consecutive_blocker_count = 0
    stopped_early = False
    for task_id in task_ids:
        receipt = run_row(
            task_id,
            repo_root=repo_root,
            timeout_seconds=timeout_seconds,
            max_probes=max_probes,
        )
        rows.append(
            {
                "task_id": task_id,
                "status": receipt.get("status"),
                "accepted_by_lean": receipt.get("accepted_by_lean"),
                "failure_class": receipt.get("failure_class"),
                "receipt_ref": _rel(row_dir(task_id, repo_root=repo_root) / ROW_RECEIPT_NAME, repo_root=repo_root),
            }
        )
        status = str(receipt.get("status") or "")
        if status in BLOCKING_STATUSES:
            if status == consecutive_blocker:
                consecutive_blocker_count += 1
            else:
                consecutive_blocker = status
                consecutive_blocker_count = 1
            if consecutive_blocker_count >= max_consecutive_blockers:
                stopped_early = True
                break
        else:
            consecutive_blocker = None
            consecutive_blocker_count = 0
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at": _utc_now(),
        "work_item_id": WORK_ITEM_ID,
        "benchmark": "VeriSoftBench",
        "slice_id": "verisoftbench_micro_10_v0",
        "planned_task_ids": list(calibration.VERISOFTBENCH_TASK_IDS),
        "attempted_task_count": len(rows),
        "row_receipt_count": len(rows),
        "stopped_early": stopped_early,
        "stop_policy": {
            "max_consecutive_blockers": max_consecutive_blockers,
            "consecutive_blocker": consecutive_blocker if stopped_early else None,
        },
        "provider_dispatch_attempted": False,
        "provider_dispatch_policy": "not_called_by_local_row_executor_v0",
        "local_probe_policy": {
            "available_probe_ids": [probe_id for probe_id, _ in LOCAL_PROBES],
            "max_probes_per_row": max_probes if max_probes is not None else len(LOCAL_PROBES),
        },
        "status_counts": dict(Counter(str(row.get("status") or "unknown") for row in rows)),
        "accepted_by_lean_count": sum(1 for row in rows if row.get("accepted_by_lean") is True),
        "rows": rows,
        "claim_boundary": CLAIM_BOUNDARY,
        "public_claim_allowed": False,
    }
    _write_json(_repo_path(ROW_EXECUTION_MANIFEST_PATH, repo_root=repo_root), manifest)
    return manifest


def check_outputs(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    issues: list[str] = []
    manifest_path = _repo_path(ROW_EXECUTION_MANIFEST_PATH, repo_root=repo_root)
    manifest = _read_json_if_exists(manifest_path)
    if not manifest:
        issues.append(f"missing {ROW_EXECUTION_MANIFEST_PATH}")
    elif manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        issues.append("row execution manifest schema mismatch")
    rows = manifest.get("rows") if isinstance(manifest.get("rows"), list) else []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        receipt_ref = str(row.get("receipt_ref") or "")
        receipt_path = _repo_path(receipt_ref, repo_root=repo_root)
        if not receipt_path.exists():
            issues.append(f"missing row receipt {receipt_ref}")
            continue
        receipt = _read_json(receipt_path)
        if receipt.get("schema_version") != SCHEMA_VERSION:
            issues.append(f"row receipt schema mismatch: {receipt_ref}")
        if receipt.get("official_leaderboard_submission") is not False:
            issues.append(f"row receipt claims official leaderboard submission: {receipt_ref}")
        if receipt.get("public_claim_allowed") is not False:
            issues.append(f"row receipt public_claim_allowed must be false: {receipt_ref}")
        status = str(receipt.get("status") or "")
        if status in {
            "direct_local_probe_accepted",
            "direct_local_probe_rejected_with_receipt",
            "direct_local_probe_timeout_with_receipt",
        }:
            if receipt.get("statement_scope_status") != "PASS":
                issues.append(f"direct local row missing PASS statement scope: {receipt_ref}")
            probe_manifest = ((receipt.get("direct_local_probes") or {}).get("probe_manifest_ref"))
            if not probe_manifest or not _repo_path(str(probe_manifest), repo_root=repo_root).exists():
                issues.append(f"direct local row missing probe manifest: {receipt_ref}")
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "row_execution_manifest_ref": str(ROW_EXECUTION_MANIFEST_PATH),
        "row_receipt_count": len(rows),
        "owner_id": OWNER_ID,
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--max-consecutive-blockers", type=int, default=3)
    parser.add_argument("--max-probes", type=int, default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root)
    if args.check:
        result = check_outputs(repo_root=repo_root)
    else:
        result = run_rows(
            repo_root=repo_root,
            task_ids=tuple(args.task_ids) if args.task_ids else calibration.VERISOFTBENCH_TASK_IDS,
            timeout_seconds=args.timeout_seconds,
            max_consecutive_blockers=args.max_consecutive_blockers,
            max_probes=args.max_probes,
        )
    if args.json or args.check:
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(
            f"verisoftbench_micro_10_rows: receipts={result.get('row_receipt_count')} "
            f"accepted={result.get('accepted_by_lean_count')}"
        )
    status = result.get("status") if isinstance(result, Mapping) else None
    return 0 if not args.check or status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
