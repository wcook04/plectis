#!/usr/bin/env python3
"""Run hidden VeriSoftBench harness differential controls for micro-10.

This is a control lane, not a solving lane. It uses the official
VeriSoftBench annex and ground-truth proofs only to diagnose whether the local
row executor is false-negative contaminated. Ground truth is never persisted as
provider context, never counted as a solve, and never authorizes a public claim.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
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
from tools.meta.factory import run_verisoftbench_micro10_calibration_rows as row_executor


SCHEMA_VERSION = "verisoftbench_harness_differential_receipt_v0"
MANIFEST_SCHEMA_VERSION = "verisoftbench_harness_differential_manifest_v0"
CHECK_SCHEMA_VERSION = "verisoftbench_harness_differential_check_v0"
CLAIM_BOUNDARY = "truth_side_control_not_scored_not_provider_context"
OWNER_ID = calibration.OWNER_ID
WORK_ITEM_ID = calibration.WORK_ITEM_ID

ANNEX_REPO_ROOT = Path("annexes/verisoftbench/repo")
OFFICIAL_DATASET_PATH = ANNEX_REPO_ROOT / "data/verisoftbench.jsonl"
HARNESS_DIFFERENTIAL_ROOT = calibration.CALIBRATION_ROOT / "harness_differential"
HARNESS_DIFFERENTIAL_MANIFEST_PATH = HARNESS_DIFFERENTIAL_ROOT / "harness_differential_manifest.json"
HARNESS_RECEIPT_NAME = "harness_differential_receipt.json"


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


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _task_slug(task_id: str) -> str:
    return task_id.replace(":", "_")


def receipt_dir(task_id: str, *, repo_root: Path = REPO_ROOT) -> Path:
    return _repo_path(HARNESS_DIFFERENTIAL_ROOT / _task_slug(task_id), repo_root=repo_root)


def receipt_path(task_id: str) -> Path:
    return HARNESS_DIFFERENTIAL_ROOT / _task_slug(task_id) / HARNESS_RECEIPT_NAME


def _load_official_modules(repo_root: Path):
    annex_root = _repo_path(ANNEX_REPO_ROOT, repo_root=repo_root)
    if not annex_root.exists():
        raise FileNotFoundError(f"missing VeriSoftBench annex at {ANNEX_REPO_ROOT}")
    if str(annex_root) not in sys.path:
        sys.path.insert(0, str(annex_root))
    from core.lean_interface import LeanREPL  # type: ignore
    import utils.utils as official_utils  # type: ignore

    return LeanREPL, official_utils


def _dataset_entries(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    path = _repo_path(OFFICIAL_DATASET_PATH, repo_root=repo_root)
    entries: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return entries
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            task_id = f"verisoftbench:{row.get('id')}"
            if task_id in calibration.VERISOFTBENCH_TASK_IDS:
                entries[task_id] = row
    return entries


def _clean_error(value: str) -> dict[str, Any]:
    text = str(value or "")
    lowered = text.lower()
    if not text:
        error_class = None
    elif "timeout" in lowered or "timed out" in lowered:
        error_class = "timeout"
    elif "unknown identifier" in lowered or "unknown constant" in lowered:
        error_class = "unknown_identifier"
    elif "application type mismatch" in lowered:
        error_class = "application_type_mismatch"
    elif "failed to synthesize" in lowered:
        error_class = "failed_to_synthesize"
    elif "declaration uses 'sorry'" in lowered or "sorry" in lowered:
        error_class = "incomplete_proof_rejected"
    elif "tactic" in lowered:
        error_class = "tactic_failure"
    else:
        error_class = "lean_failure"
    excerpt = re.sub(r"\s+", " ", text).strip()[:500]
    return {
        "error_class": error_class,
        "error_digest": _sha256_text(text) if text else None,
        "error_excerpt": excerpt or None,
    }


def _repair_statement_and_ground_truth(
    *,
    official_utils: Any,
    thm_stmt: str,
    gt_proof: str,
    lean_root: str,
    rel_path: str,
    thm_name: str,
) -> tuple[str, str]:
    sep_idx, sep_pat = official_utils.find_decl_body_separator(thm_stmt)
    gt_stripped = gt_proof.strip()
    body_pats = {
        ":=\\s+by\\b",
        ":=\\s+match\\b",
        ":=\\s+calc\\b",
        ":=\\s+fun\\b",
        ":=\\s+lambda\\b",
        ":=\\s+λ\\b",
        ":=\\s+begin\\b",
        "\\bwhere\\b",
        "(?<!<)\\|\\s+(?!<)\\S",
    }
    if sep_idx > 0 and sep_pat in body_pats:
        proof_from_stmt = "\n  " + thm_stmt[sep_idx:]
        thm_stmt = thm_stmt[:sep_idx].rstrip()
        if gt_stripped.startswith(":=") and not any(
            re.match(pattern, gt_stripped)
            for pattern in [
                r":=\s+by\b",
                r":=\s+match\b",
                r":=\s+calc\b",
                r":=\s+fun\b",
                r":=\s+lambda\b",
                r":=\s+λ\b",
                r":=\s+begin\b",
            ]
        ):
            gt_proof = proof_from_stmt
    elif gt_stripped.startswith(":=") and not any(
        re.match(pattern, gt_stripped)
        for pattern in [
            r":=\s+by\b",
            r":=\s+match\b",
            r":=\s+calc\b",
            r":=\s+fun\b",
            r":=\s+lambda\b",
            r":=\s+λ\b",
            r":=\s+begin\b",
        ]
    ):
        gt_sep_idx, gt_sep_pat = official_utils.find_decl_body_separator(gt_proof)
        if gt_sep_idx > 0 and gt_sep_pat not in (":=", ":"):
            gt_proof = gt_proof[gt_sep_idx:]
        elif sep_idx > 0 and thm_stmt[sep_idx : sep_idx + 2] == ":=":
            thm_stmt = thm_stmt[:sep_idx].rstrip()

    gt_proof = re.sub(
        r"\n\n(?=/--|/-|example\b|def\b|theorem\b|lemma\b|#|open\b|namespace\b|section\b).*",
        "",
        gt_proof,
        flags=re.DOTALL,
    )

    if lean_root == "formal-snarks-project":
        unfold_line = (
            "  unfold AGMProofSystemInstantiation.check_poly "
            "AGMProofSystemInstantiation.pairing_poly "
            "AGMProofSystemInstantiation.proof_element_G1_as_poly "
            "AGMProofSystemInstantiation.proof_element_G2_as_poly at eqn\n"
            "  simp only [] at eqn\n"
        )
        gt_proof = re.sub(
            r"(simp_rw \[\w+\] at eqn\n)(  simp only \[monomial_zero)",
            r"\1" + unfold_line + r"\2",
            gt_proof,
        )

    if "BLAKE3/ApplyRounds" in rel_path or "BLAKE3.ApplyRounds" in thm_name:
        pass

    return thm_stmt, gt_proof


def _official_context(
    *,
    entry: Mapping[str, Any],
    workspace_root: Path,
    official_utils: Any,
) -> tuple[str, str, str, str]:
    lean_root = str(entry.get("lean_root") or "")
    rel_path = str(entry.get("rel_path") or "")
    imports = entry.get("imports") if isinstance(entry.get("imports"), list) else []
    local_ctx = str(entry.get("local_ctxs") or entry.get("local_ctx") or "")
    thm_name = str(entry.get("thm_name") or "")
    thm_stmt = str(entry.get("thm_stmt") or "")
    gt_proof = str(entry.get("ground_truth_proof") or "")
    suffix = str(entry.get("suffix") or "")
    thm_stmt, gt_proof = _repair_statement_and_ground_truth(
        official_utils=official_utils,
        thm_stmt=thm_stmt,
        gt_proof=gt_proof,
        lean_root=lean_root,
        rel_path=rel_path,
        thm_name=thm_name,
    )

    fallback_ctx = "\n".join(str(value) for value in imports) + "\n" + local_ctx
    decl_kw_re = (
        r"(?:def |structure |class |instance |theorem |lemma |namespace |section |end |"
        r"@\[|private |protected |noncomputable |open |set_option |variable |abbrev |inductive |mutual\b)"
    )
    fallback_ctx = re.sub(r":=\s*\n(\s*\n)*(?=\s*" + decl_kw_re + r")", ":= sorry\n\n", fallback_ctx)
    fallback_ctx = re.sub(
        r"^def\s+(\w+)\s+(\([^)]+:\s*Type\*?\))\s*:=",
        r"abbrev \1 \2 :=",
        fallback_ctx,
        flags=re.MULTILINE,
    )

    source_path = workspace_root.parent / lean_root / rel_path
    if source_path.exists():
        full_file_content = source_path.read_text(encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            verif_local_context = official_utils.get_content_before_theorem(
                full_file_content,
                thm_stmt,
                thm_name=thm_name,
            )
        if verif_local_context is None:
            ns_parts = thm_name.rsplit(".", 1)
            if len(ns_parts) > 1:
                ns_name = ns_parts[0]
                last_component = ns_name.rsplit(".", 1)[-1]
                end_pattern = re.compile(
                    r"^end\s+"
                    + re.escape(ns_name)
                    + r"\s*$|^end\s+"
                    + re.escape(last_component)
                    + r"\s*$",
                    re.MULTILINE,
                )
                matches = list(end_pattern.finditer(full_file_content))
                if matches:
                    verif_local_context = full_file_content[: matches[-1].start()]
                else:
                    verif_local_context = fallback_ctx
            else:
                verif_local_context = fallback_ctx
    else:
        verif_local_context = fallback_ctx

    verif_local_context = re.sub(
        r"^noncomputable\s+(theorem|lemma)\b",
        r"\1",
        verif_local_context,
        flags=re.MULTILINE,
    )
    verif_local_context = re.sub(
        r"(prove_correct\??\s+\w+)\s+by\n.*?(?=\n\n|\n(?:prove_correct|theorem|lemma|def|--[^\n]*\n\n))",
        r"\1 by sorry",
        verif_local_context,
        flags=re.DOTALL,
    )

    stmt_lines = thm_stmt.split("\n")
    if stmt_lines and stmt_lines[0].strip().startswith("@[") and stmt_lines[0].strip().endswith("]"):
        attr = stmt_lines[0].strip()
        ctx_lines = verif_local_context.rstrip().split("\n")
        if ctx_lines and ctx_lines[-1].strip() == attr:
            thm_stmt = "\n".join(stmt_lines[1:])

    if "BLAKE3/ApplyRounds" in rel_path or "BLAKE3.ApplyRounds" in thm_name:
        lines = verif_local_context.split("\n")
        last_import = -1
        for index, line in enumerate(lines):
            if line.strip().startswith("import "):
                last_import = index
        if last_import >= 0:
            lines.insert(last_import + 1, "\nset_option maxRecDepth 16384\nset_option maxHeartbeats 0")
        else:
            lines.insert(0, "set_option maxRecDepth 16384\nset_option maxHeartbeats 0")
        verif_local_context = "\n".join(lines)
        verif_local_context = re.sub(r"\(by\b\n.*?\)", "(by sorry)", verif_local_context, flags=re.DOTALL)

    return verif_local_context, thm_stmt, gt_proof, suffix


def _official_ground_truth_check(
    *,
    entry: Mapping[str, Any],
    workspace_root: Path,
    repo_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        LeanREPL, official_utils = _load_official_modules(repo_root)
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "duration_ms": 0,
            **_clean_error(str(exc)),
        }

    lean_root = str(entry.get("lean_root") or "")
    rel_path = str(entry.get("rel_path") or "")
    thm_name = str(entry.get("thm_name") or "")
    gt_proof = str(entry.get("ground_truth_proof") or "")
    if not gt_proof.strip():
        return {
            "status": "FAIL",
            "duration_ms": 0,
            **_clean_error("empty ground_truth_proof"),
        }
    source_path = workspace_root.parent / lean_root / rel_path
    if not source_path.exists():
        return {
            "status": "UNAVAILABLE",
            "duration_ms": 0,
            **_clean_error(f"source file unavailable: {source_path}"),
        }

    try:
        local_context, thm_stmt, gt_proof, suffix = _official_context(
            entry=entry,
            workspace_root=workspace_root,
            official_utils=official_utils,
        )
        full_file_content = source_path.read_text(encoding="utf-8")
        remaining_mutual_content = official_utils.get_remaining_mutual_content(
            full_file_content,
            thm_stmt,
            local_context,
        )
        content = official_utils.format_generated_lean(
            local_context,
            thm_stmt,
            gt_proof,
            "",
            suffix,
            remaining_mutual_content,
        )
        temp_path = source_path.with_name(
            f"{source_path.stem}_{thm_name.rsplit('.', 1)[-1]}_harness_gt_control.lean"
        )
        temp_path.write_text(content, encoding="utf-8")
        result = row_executor._run_lake_env_lean(
            temp_path,
            workspace_root=workspace_root,
            timeout_seconds=timeout_seconds,
        )
        temp_path.unlink(missing_ok=True)
        status = str(result.get("compile_status") or "FAIL")
        if status == "BLOCKED":
            status = "UNAVAILABLE"
        error_text = "" if status == "PASS" else str(result.get("stdout") or "") + "\n" + str(result.get("stderr") or "")
    except subprocess.TimeoutExpired as exc:
        status = "TIMEOUT"
        error_text = str(exc)
    except Exception as exc:
        status = "FAIL"
        error_text = f"{type(exc).__name__}: {exc}"
        try:
            temp_path.unlink(missing_ok=True)  # type: ignore[name-defined]
        except Exception:
            pass
    return {
        "status": status,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "control_implementation": "annex_context_original_file_adjacent_lake_env_lean",
        "timeout_seconds": timeout_seconds,
        "lean_source_persisted": False,
        **_clean_error(error_text),
    }


def _statement_decl_name(statement: str) -> str | None:
    match = re.search(r"\b(?:theorem|lemma)\s+([^\s(:]+)", statement)
    return match.group(1) if match else None


def _active_namespace(prefix: str) -> str:
    stack: list[str] = []
    for line in prefix.splitlines():
        stripped = line.strip()
        if stripped.startswith("namespace "):
            name = stripped.split(None, 1)[1].strip()
            if name:
                stack.extend(part for part in name.split(".") if part)
        elif stripped.startswith("end"):
            parts = stripped.split()
            if len(parts) == 1:
                if stack:
                    stack.pop()
            elif stack and stack[-1] == parts[-1]:
                stack.pop()
    return ".".join(stack)


def _support_prefix_ground_truth_check(
    *,
    entry: Mapping[str, Any],
    workspace_root: Path,
    out_dir: Path,
    repo_root: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    try:
        _, official_utils = _load_official_modules(repo_root)
    except Exception as exc:
        return (
            {
                "status": "UNAVAILABLE",
                "duration_ms": 0,
                "lean_source_persisted": False,
                **_clean_error(str(exc)),
            },
            {
                "expected_full_name": entry.get("thm_name"),
                "statement_decl_name": None,
                "active_namespace": None,
                "double_namespace_suspected": False,
                "short_name_axioms_check_status": "NOT_RUN",
            },
        )

    lean_root = str(entry.get("lean_root") or "")
    rel_path = str(entry.get("rel_path") or "")
    thm_name = str(entry.get("thm_name") or "")
    source_path = workspace_root.parent / lean_root / rel_path
    if not source_path.exists():
        return (
            {
                "status": "UNAVAILABLE",
                "duration_ms": 0,
                "lean_source_persisted": False,
                **_clean_error(f"source file unavailable: {source_path}"),
            },
            {
                "expected_full_name": thm_name,
                "statement_decl_name": None,
                "active_namespace": None,
                "double_namespace_suspected": False,
                "short_name_axioms_check_status": "NOT_RUN",
            },
        )

    source = source_path.read_text(encoding="utf-8")
    short_name = thm_name.rsplit(".", 1)[-1]
    prefix, extraction = scope_support.extract_pre_target_prefix(source, theorem_name=short_name)
    thm_stmt = str(entry.get("thm_stmt") or "")
    gt_proof = str(entry.get("ground_truth_proof") or "")
    thm_stmt, gt_proof = _repair_statement_and_ground_truth(
        official_utils=official_utils,
        thm_stmt=thm_stmt,
        gt_proof=gt_proof,
        lean_root=lean_root,
        rel_path=rel_path,
        thm_name=thm_name,
    )
    decl_name = _statement_decl_name(thm_stmt)
    namespace = _active_namespace(prefix)
    theorem_name_check = {
        "expected_full_name": thm_name,
        "statement_decl_name": decl_name,
        "active_namespace": namespace or None,
        "double_namespace_suspected": bool(decl_name and "." in decl_name and namespace and decl_name.startswith(namespace + ".")),
        "short_name_axioms_check_status": "NOT_RUN",
    }
    if extraction.get("status") != scope_support.STATUS_READY:
        return (
            {
                "status": "FAIL",
                "duration_ms": int((time.monotonic() - started) * 1000),
                "lean_source_persisted": False,
                "support_extraction_status": extraction.get("status"),
                **_clean_error(str(extraction)),
            },
            theorem_name_check,
        )

    try:
        remaining_mutual_content = official_utils.get_remaining_mutual_content(source, thm_stmt, prefix)
        content = official_utils.format_generated_lean(
            prefix,
            thm_stmt,
            gt_proof,
            "",
            str(entry.get("suffix") or ""),
            remaining_mutual_content,
        )
        temp_path = out_dir / "support_prefix_ground_truth_control.tmp.lean"
        temp_path.write_text(content, encoding="utf-8")
        result = row_executor._run_lake_env_lean(
            temp_path,
            workspace_root=workspace_root,
            timeout_seconds=timeout_seconds,
        )
        temp_path.unlink(missing_ok=True)
    except subprocess.TimeoutExpired as exc:
        result = {
            "compile_status": "TIMEOUT",
            "exit_code": None,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timeout": True,
            "stdout": "",
            "stderr": str(exc),
        }
    except Exception as exc:
        result = {
            "compile_status": "FAIL",
            "exit_code": None,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timeout": False,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }
        try:
            (out_dir / "support_prefix_ground_truth_control.tmp.lean").unlink(missing_ok=True)
        except OSError:
            pass

    status = str(result.get("compile_status") or "FAIL")
    if status == "BLOCKED":
        status = "UNAVAILABLE"
    return (
        {
            "status": status,
            "duration_ms": result.get("duration_ms"),
            "timeout": result.get("timeout"),
            "exit_code": result.get("exit_code"),
            "lean_source_persisted": False,
            **_clean_error(str(result.get("stdout") or "") + "\n" + str(result.get("stderr") or "")),
        },
        theorem_name_check,
    )


def _row_status(task_id: str, *, repo_root: Path) -> dict[str, Any]:
    path = _repo_path(row_executor.row_receipt_path(task_id), repo_root=repo_root)
    row = _read_json_if_exists(path)
    if not row:
        return {
            "status": "missing_row_execution_receipt",
            "receipt_ref": None,
            "provider_candidate_status": None,
            "support_prefix_sorry_check": "NOT_RUN",
        }
    provider_plan = row.get("provider_plan") if isinstance(row.get("provider_plan"), Mapping) else {}
    statement_scope = str(row.get("statement_scope_status") or "")
    if statement_scope == "PASS":
        sorry_status = "PASS"
    elif statement_scope == "TIMEOUT" or row.get("status") == "blocked_statement_scope_timeout":
        sorry_status = "TIMEOUT"
    elif statement_scope:
        sorry_status = "FAIL"
    else:
        sorry_status = "NOT_RUN"
    return {
        "status": row.get("status"),
        "failure_class": row.get("failure_class"),
        "lean_status": row.get("lean_status"),
        "receipt_ref": _rel(path, repo_root=repo_root),
        "provider_candidate_status": provider_plan.get("provider_output_kind") or "not_present",
        "support_prefix_sorry_check": sorry_status,
    }


def _diagnose(
    *,
    official_status: str,
    support_gt_status: str,
    support_sorry_status: str,
    row_status: str,
    provider_candidate_status: str,
) -> str:
    if official_status in {"UNAVAILABLE", "TIMEOUT"}:
        return "official_control_unavailable_or_timeout"
    if official_status != "PASS":
        return "environment_or_official_ground_truth_failure"
    if support_gt_status == "PASS":
        if row_status in {
            "direct_local_probe_rejected_with_receipt",
            "direct_local_probe_timeout_with_receipt",
            "blocked_statement_scope_timeout",
        }:
            return "real_proof_search_needed"
        return "harness_validated_no_scored_solve"
    if support_gt_status == "TIMEOUT" or support_sorry_status == "TIMEOUT":
        return "timeout_artifact"
    if support_gt_status in {"FAIL", "UNAVAILABLE"}:
        return "statement_scope_or_support_prefix_bug"
    if provider_candidate_status == "decision_point_plan_or_nonproof":
        return "provider_prompt_or_schema_gap"
    return "unknown"


def run_task(
    task_id: str,
    *,
    repo_root: Path = REPO_ROOT,
    timeout_seconds: int = 180,
    force: bool = False,
) -> dict[str, Any]:
    out_dir = receipt_dir(task_id, repo_root=repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_path = out_dir / HARNESS_RECEIPT_NAME
    if not force and existing_path.exists():
        existing = _read_json_if_exists(existing_path)
        if existing.get("schema_version") == SCHEMA_VERSION:
            return existing
    created_at = _utc_now()
    entries = _dataset_entries(repo_root=repo_root)
    entry = entries.get(task_id)
    workspace_root = row_executor._workspace_root(repo_root=repo_root)
    row_status = _row_status(task_id, repo_root=repo_root)
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
        "score_counted": False,
        "accepted_by_lean": False,
        "solved": False,
        "truth_side_control": {
            "ground_truth_used": True,
            "ground_truth_used_for_provider": False,
            "ground_truth_persisted": False,
            "provider_prompt_refs": [],
            "public_projection_allowed": False,
        },
        "local_row_executor_status": row_status.get("status"),
        "local_row_executor_failure_class": row_status.get("failure_class"),
        "provider_candidate_status": row_status.get("provider_candidate_status"),
        "support_prefix_sorry_check": row_status.get("support_prefix_sorry_check"),
        "receipt_refs": [row_status.get("receipt_ref")],
    }
    if entry is None:
        receipt = {
            **base,
            "status": "blocked_official_dataset_entry_missing",
            "official_ground_truth_check": "UNAVAILABLE",
            "original_file_replacement_check": "UNAVAILABLE",
            "support_prefix_ground_truth_check": "NOT_RUN",
            "generated_theorem_name_check": {
                "expected_full_name": task_id,
                "actual_decl_names": [],
                "double_namespace_suspected": False,
                "short_name_axioms_check_status": "NOT_RUN",
            },
            "diagnosis": "official_control_unavailable_or_timeout",
            "issues": [f"{task_id} missing from {OFFICIAL_DATASET_PATH}"],
        }
        receipt["receipt_refs"] = [ref for ref in receipt["receipt_refs"] if ref]
        _write_json(out_dir / HARNESS_RECEIPT_NAME, receipt)
        return receipt
    if workspace_root is None:
        receipt = {
            **base,
            "status": "blocked_workspace_missing",
            "official_ground_truth_check": "UNAVAILABLE",
            "original_file_replacement_check": "UNAVAILABLE",
            "support_prefix_ground_truth_check": "NOT_RUN",
            "generated_theorem_name_check": {
                "expected_full_name": entry.get("thm_name"),
                "actual_decl_names": [],
                "double_namespace_suspected": False,
                "short_name_axioms_check_status": "NOT_RUN",
            },
            "diagnosis": "official_control_unavailable_or_timeout",
            "issues": ["pinned Lean workspace missing from oracle environment gate receipt"],
        }
        receipt["receipt_refs"] = [ref for ref in receipt["receipt_refs"] if ref]
        _write_json(out_dir / HARNESS_RECEIPT_NAME, receipt)
        return receipt

    official = _official_ground_truth_check(
        entry=entry,
        workspace_root=workspace_root,
        repo_root=repo_root,
        timeout_seconds=timeout_seconds,
    )
    support_gt, theorem_name_check = _support_prefix_ground_truth_check(
        entry=entry,
        workspace_root=workspace_root,
        out_dir=out_dir,
        repo_root=repo_root,
        timeout_seconds=timeout_seconds,
    )
    diagnosis = _diagnose(
        official_status=str(official.get("status") or ""),
        support_gt_status=str(support_gt.get("status") or ""),
        support_sorry_status=str(row_status.get("support_prefix_sorry_check") or ""),
        row_status=str(row_status.get("status") or ""),
        provider_candidate_status=str(row_status.get("provider_candidate_status") or ""),
    )
    receipt = {
        **base,
        "status": "harness_differential_receipt_recorded",
        "official_ground_truth_check": official.get("status"),
        "original_file_replacement_check": official.get("status"),
        "official_ground_truth_control": official,
        "original_file_replacement_control": {
            "status": official.get("status"),
            "control_implementation": "annex_verisoftbench_LeanREPL_verify_proof_local_original_file_adjacent_temp_replacement",
        },
        "support_prefix_ground_truth_check": support_gt.get("status"),
        "support_prefix_ground_truth_control": support_gt,
        "generated_theorem_name_check": {
            **theorem_name_check,
            "actual_decl_names": [],
        },
        "diagnosis": diagnosis,
        "source_metadata": {
            "lean_root": entry.get("lean_root"),
            "rel_path": entry.get("rel_path"),
            "thm_name": entry.get("thm_name"),
            "official_dataset_ref": _rel(OFFICIAL_DATASET_PATH, repo_root=repo_root),
            "ground_truth_proof_sha256": _sha256_text(str(entry.get("ground_truth_proof") or "")),
            "ground_truth_proof_length": len(str(entry.get("ground_truth_proof") or "")),
        },
        "receipt_refs": [
            row_status.get("receipt_ref"),
            _rel(OFFICIAL_DATASET_PATH, repo_root=repo_root),
        ],
    }
    receipt["receipt_refs"] = [ref for ref in receipt["receipt_refs"] if ref]
    _write_json(out_dir / HARNESS_RECEIPT_NAME, receipt)
    return receipt


def run_tasks(
    *,
    repo_root: Path = REPO_ROOT,
    task_ids: Sequence[str] = calibration.VERISOFTBENCH_TASK_IDS,
    timeout_seconds: int = 180,
    force: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for task_id in task_ids:
        receipt = run_task(
            task_id,
            repo_root=repo_root,
            timeout_seconds=timeout_seconds,
            force=force,
        )
        rows.append(
            {
                "task_id": task_id,
                "diagnosis": receipt.get("diagnosis"),
                "official_ground_truth_check": receipt.get("official_ground_truth_check"),
                "support_prefix_ground_truth_check": receipt.get("support_prefix_ground_truth_check"),
                "local_row_executor_status": receipt.get("local_row_executor_status"),
                "receipt_ref": _rel(receipt_dir(task_id, repo_root=repo_root) / HARNESS_RECEIPT_NAME, repo_root=repo_root),
            }
        )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at": _utc_now(),
        "work_item_id": WORK_ITEM_ID,
        "benchmark": "VeriSoftBench",
        "slice_id": "verisoftbench_micro_10_v0",
        "planned_task_ids": list(calibration.VERISOFTBENCH_TASK_IDS),
        "attempted_task_count": len(rows),
        "row_receipt_count": len(rows),
        "official_ground_truth_status_counts": dict(
            Counter(str(row.get("official_ground_truth_check") or "unknown") for row in rows)
        ),
        "support_prefix_ground_truth_status_counts": dict(
            Counter(str(row.get("support_prefix_ground_truth_check") or "unknown") for row in rows)
        ),
        "diagnosis_counts": dict(Counter(str(row.get("diagnosis") or "unknown") for row in rows)),
        "truth_side_control": {
            "ground_truth_used_for_provider": False,
            "ground_truth_persisted": False,
            "public_projection_allowed": False,
            "purpose": "hidden_harness_control_only",
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "official_leaderboard_submission": False,
        "public_claim_allowed": False,
        "rows": rows,
    }
    _write_json(_repo_path(HARNESS_DIFFERENTIAL_MANIFEST_PATH, repo_root=repo_root), manifest)
    return manifest


def _harness_receipts(*, repo_root: Path) -> list[dict[str, Any]]:
    root = _repo_path(HARNESS_DIFFERENTIAL_ROOT, repo_root=repo_root)
    receipts: list[dict[str, Any]] = []
    for path in sorted(root.glob(f"verisoftbench_*/{HARNESS_RECEIPT_NAME}")):
        payload = _read_json_if_exists(path)
        if payload:
            payload["_receipt_ref"] = _rel(path, repo_root=repo_root)
            receipts.append(payload)
    return receipts


def check_outputs(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    issues: list[str] = []
    manifest_path = _repo_path(HARNESS_DIFFERENTIAL_MANIFEST_PATH, repo_root=repo_root)
    manifest = _read_json_if_exists(manifest_path)
    if not manifest:
        issues.append(f"missing {HARNESS_DIFFERENTIAL_MANIFEST_PATH}")
        rows: list[Mapping[str, Any]] = []
    elif manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        issues.append("harness differential manifest schema mismatch")
        rows = []
    else:
        rows = [row for row in manifest.get("rows") or [] if isinstance(row, Mapping)]
        if manifest.get("public_claim_allowed") is not False:
            issues.append("harness manifest public_claim_allowed must be false")
        truth = manifest.get("truth_side_control") if isinstance(manifest.get("truth_side_control"), Mapping) else {}
        if truth.get("ground_truth_used_for_provider") is not False:
            issues.append("ground truth must not be used for provider")
        if truth.get("ground_truth_persisted") is not False:
            issues.append("ground truth must not be persisted")

    for row in rows:
        ref = str(row.get("receipt_ref") or "")
        path = _repo_path(ref, repo_root=repo_root)
        if not path.exists():
            issues.append(f"missing harness receipt {ref}")
            continue
        receipt = _read_json(path)
        if receipt.get("schema_version") != SCHEMA_VERSION:
            issues.append(f"harness receipt schema mismatch: {ref}")
        if receipt.get("public_claim_allowed") is not False:
            issues.append(f"harness receipt public_claim_allowed must be false: {ref}")
        truth = receipt.get("truth_side_control") if isinstance(receipt.get("truth_side_control"), Mapping) else {}
        if truth.get("ground_truth_used_for_provider") is not False:
            issues.append(f"harness receipt leaked ground truth to provider: {ref}")
        if truth.get("ground_truth_persisted") is not False:
            issues.append(f"harness receipt persisted ground truth: {ref}")
        if receipt.get("score_counted") is not False:
            issues.append(f"harness receipt must not be score-counted: {ref}")
        if receipt.get("official_leaderboard_submission") is not False:
            issues.append(f"harness receipt claims official leaderboard submission: {ref}")
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "harness_differential_manifest_ref": str(HARNESS_DIFFERENTIAL_MANIFEST_PATH),
        "row_receipt_count": len(rows),
        "owner_id": OWNER_ID,
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root)
    if args.check:
        result = check_outputs(repo_root=repo_root)
    else:
        result = run_tasks(
            repo_root=repo_root,
            task_ids=tuple(args.task_ids) if args.task_ids else calibration.VERISOFTBENCH_TASK_IDS,
            timeout_seconds=args.timeout_seconds,
            force=args.force,
        )
    if args.json or args.check:
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(
            "verisoftbench_micro_10_harness_differential: "
            f"receipts={result.get('row_receipt_count')} "
            f"diagnoses={result.get('diagnosis_counts')}"
        )
    status = result.get("status") if isinstance(result, Mapping) else None
    return 0 if not args.check or status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
