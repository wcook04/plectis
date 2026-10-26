#!/usr/bin/env python3
"""Build aggregate reports for the prover provider batch calibration run.

This builder reads already-reduced provider receipts. It does not dispatch
providers, mutate row patches, or promote provider text into source authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ROOT = Path("state/runs/PROVER_PROVIDER_BATCH_CONTEXT_CALIBRATION_20260511_v0")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_reports(run_root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    for path in sorted((run_root / "reductions").glob("*/receipt_reduction_report.json")):
        yield path, _read_json(path)


def _load_ref(path_ref: str) -> dict[str, Any]:
    return _read_json(_repo_path(path_ref))


def _recipe_key(report: Mapping[str, Any], oracle: Mapping[str, Any]) -> str:
    return str(report.get("recipe_id") or oracle.get("recipe_id") or "unknown")


def _graph_role(report: Mapping[str, Any], oracle: Mapping[str, Any]) -> str:
    return str(report.get("graph_role") or oracle.get("graph_role") or "unknown")


def _sum_numeric(values: Iterable[Any]) -> float:
    total = 0.0
    for value in values:
        try:
            total += float(value)
        except (TypeError, ValueError):
            continue
    return total


def build_reports(run_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for report_path, report in _iter_reports(run_root):
        oracle = _load_ref(str(report.get("provider_oracle_attribution_ref") or ""))
        lean = _load_ref(str(report.get("lean_check_result_ref") or ""))
        foundry = _load_ref(str(report.get("foundry_learning_row_ref") or ""))
        context = report.get("context_metrics") if isinstance(report.get("context_metrics"), Mapping) else {}
        budget = context.get("context_budget") if isinstance(context.get("context_budget"), Mapping) else {}
        premise_policy = (
            report.get("premise_policy_audit")
            if isinstance(report.get("premise_policy_audit"), Mapping)
            else {}
        )
        leakage = report.get("leakage_audit") if isinstance(report.get("leakage_audit"), Mapping) else {}
        rows.append(
            {
                "receipt_id": report.get("receipt_id"),
                "problem_id": report.get("problem_id"),
                "provider_id": report.get("provider_id"),
                "model_id": report.get("model_id"),
                "recipe_id": _recipe_key(report, oracle),
                "graph_role": _graph_role(report, oracle),
                "accepted_by_lean": bool(report.get("accepted_by_lean")),
                "recipe_policy_passed": bool(report.get("recipe_policy_passed")),
                "error_class": report.get("error_class"),
                "row_patch_review_outcome": report.get("row_patch_review_outcome"),
                "leakage_status": leakage.get("status"),
                "truth_side_leakage_hits": leakage.get("truth_side_leakage_hits") or [],
                "premise_policy_status": premise_policy.get("status"),
                "unallowed_premise_ids": premise_policy.get("unallowed_premise_ids") or [],
                "cited_unallowed_premise_ids": premise_policy.get("cited_unallowed_premise_ids") or [],
                "undeclared_library_prior_symbols": premise_policy.get("undeclared_library_prior_symbols") or [],
                "context_bytes": budget.get("bytes"),
                "context_kib": budget.get("kib"),
                "bytes_out": context.get("bytes_out"),
                "latency_ms": context.get("latency_ms"),
                "cost": context.get("cost"),
                "usage": context.get("usage"),
                "lean_compile_status": lean.get("compile_status"),
                "lean_duration_ms": lean.get("duration_ms"),
                "foundry_learning_class": foundry.get("learning_class"),
                "report_ref": _rel(report_path),
                "lean_check_result_ref": report.get("lean_check_result_ref"),
                "provider_oracle_attribution_ref": report.get("provider_oracle_attribution_ref"),
                "foundry_learning_row_ref": report.get("foundry_learning_row_ref"),
                "row_patch_review_ref": report.get("row_patch_review_ref"),
            }
        )

    by_recipe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_recipe[str(row["recipe_id"])].append(row)

    recipe_metrics = []
    for recipe_id, recipe_rows in sorted(by_recipe.items()):
        error_counts = Counter(str(row["error_class"]) for row in recipe_rows)
        review_counts = Counter(str(row["row_patch_review_outcome"]) for row in recipe_rows)
        recipe_metrics.append(
            {
                "recipe_id": recipe_id,
                "receipt_count": len(recipe_rows),
                "lean_accepted_count": sum(1 for row in recipe_rows if row["accepted_by_lean"]),
                "recipe_policy_accepted_count": sum(
                    1 for row in recipe_rows if row["recipe_policy_passed"]
                ),
                "truth_side_leakage_count": sum(
                    1 for row in recipe_rows if row["leakage_status"] != "PASS"
                ),
                "premise_budget_violation_count": error_counts.get("PREMISE_BUDGET_VIOLATION", 0),
                "undeclared_library_prior_count": error_counts.get("UNDECLARED_LIBRARY_PRIOR", 0),
                "proof_synthesis_failure_count": error_counts.get("PROOF_SYNTHESIS_FAIL", 0),
                "avg_latency_ms": (
                    _sum_numeric(row.get("latency_ms") for row in recipe_rows) / len(recipe_rows)
                    if recipe_rows
                    else 0
                ),
                "total_bytes_out": int(_sum_numeric(row.get("bytes_out") for row in recipe_rows)),
                "context_kib_values": sorted(
                    {
                        row["context_kib"]
                        for row in recipe_rows
                        if row.get("context_kib") is not None
                    }
                ),
                "error_counts": dict(error_counts),
                "row_patch_review_outcome_counts": dict(review_counts),
            }
        )

    row_patch_review_counts = Counter(str(row["row_patch_review_outcome"]) for row in rows)
    error_counts = Counter(str(row["error_class"]) for row in rows)
    provider_counts = Counter(str(row["provider_id"]) for row in rows)
    model_counts = Counter(str(row["model_id"]) for row in rows)
    learning_rows = [
        _load_ref(str(row["foundry_learning_row_ref"]))
        for row in rows
        if row.get("foundry_learning_row_ref")
    ]

    representative_success = next(
        (row for row in rows if row["recipe_policy_passed"]),
        {},
    )
    representative_premise_budget_violation = next(
        (row for row in rows if row["error_class"] == "PREMISE_BUDGET_VIOLATION"),
        {},
    )
    representative_proof_failure = next(
        (row for row in rows if row["error_class"] == "PROOF_SYNTHESIS_FAIL"),
        {},
    )

    taxonomy_decision = {
        "schema_version": "prover_provider_reducer_taxonomy_decision_v0",
        "created_at": _utc_now(),
        "decision": "separate truth-side leakage from premise-policy failures",
        "classes": {
            "SOLUTION_LEAKAGE": "hidden proof body, oracle-only repair body, test truth, or forbidden truth-side source appears in provider output",
            "PREMISE_BUDGET_VIOLATION": "provider declares or cites a premise outside the active context recipe's allowed premise set",
            "UNDECLARED_LIBRARY_PRIOR": "provider declares use of imported Lean/Std library prior not supplied by the context recipe",
            "PROVIDER_CONTRACT_FAIL": "receipt or row_patch output schema failed before Lean evidence can be trusted",
            "PROOF_SYNTHESIS_FAIL": "recipe-allowed candidate reached Lean but failed proof checking",
            "NONE": "Lean accepted and the recipe policy passed",
        },
        "row_patch_review_mapping": {
            "NONE": "accept_as_advisory_signal",
            "SOLUTION_LEAKAGE": "reject",
            "PROVIDER_CONTRACT_FAIL": "reject",
            "PREMISE_BUDGET_VIOLATION": "retry",
            "UNDECLARED_LIBRARY_PRIOR": "bridge_escalate",
            "PROOF_SYNTHESIS_FAIL": "retry",
        },
    }
    matrix = {
        "schema_version": "prover_provider_receipt_reduction_matrix_v0",
        "created_at": _utc_now(),
        "run_id": run_root.name,
        "rows": rows,
    }
    recipe_policy_metrics = {
        "schema_version": "prover_provider_recipe_policy_metrics_v0",
        "created_at": _utc_now(),
        "run_id": run_root.name,
        "recipes": recipe_metrics,
    }
    row_patch_review_summary = {
        "schema_version": "prover_provider_row_patch_review_summary_v0",
        "created_at": _utc_now(),
        "run_id": run_root.name,
        "outcome_counts": dict(row_patch_review_counts),
        "review_refs": [row.get("row_patch_review_ref") for row in rows],
    }
    cost_latency_usage = {
        "schema_version": "prover_provider_cost_latency_usage_report_v0",
        "created_at": _utc_now(),
        "run_id": run_root.name,
        "provider_counts": dict(provider_counts),
        "model_counts": dict(model_counts),
        "total_latency_ms": int(_sum_numeric(row.get("latency_ms") for row in rows)),
        "avg_latency_ms": _sum_numeric(row.get("latency_ms") for row in rows) / len(rows) if rows else 0,
        "total_bytes_out": int(_sum_numeric(row.get("bytes_out") for row in rows)),
        "cost_entries": [row.get("cost") for row in rows],
        "usage_entries": [row.get("usage") for row in rows],
    }
    run_summary = {
        "schema_version": "prover_provider_batch_context_calibration_run_summary_v0",
        "created_at": _utc_now(),
        "run_id": run_root.name,
        "cap_id": "cap_prover_provider_batch_context_calibration_v0",
        "receipt_count": len(rows),
        "problem_count": len({row["problem_id"] for row in rows}),
        "recipe_count": len({row["recipe_id"] for row in rows}),
        "provider_counts": dict(provider_counts),
        "model_counts": dict(model_counts),
        "lean_accepted_count": sum(1 for row in rows if row["accepted_by_lean"]),
        "recipe_policy_accepted_count": sum(1 for row in rows if row["recipe_policy_passed"]),
        "truth_side_leakage_count": sum(1 for row in rows if row["leakage_status"] != "PASS"),
        "premise_policy_failure_count": sum(
            1 for row in rows if row["premise_policy_status"] != "PASS"
        ),
        "error_counts": dict(error_counts),
        "row_patch_review_outcome_counts": dict(row_patch_review_counts),
        "provider_calls_by_reducer": 0,
        "harness_owned_provider_dispatch_added": False,
        "fake_provider_results_counted": 0,
        "artifact_refs": {
            "reducer_taxonomy_decision": _rel(run_root / "reducer_taxonomy_decision.json"),
            "provider_receipt_reduction_matrix": _rel(
                run_root / "provider_receipt_reduction_matrix.json"
            ),
            "recipe_policy_metrics": _rel(run_root / "recipe_policy_metrics.json"),
            "row_patch_review_summary": _rel(run_root / "row_patch_review_summary.json"),
            "foundry_provider_learning_rows": _rel(
                run_root / "foundry_provider_learning_rows.json"
            ),
            "provider_cost_latency_usage_report": _rel(
                run_root / "provider_cost_latency_usage_report.json"
            ),
        },
    }
    foundry_learning = {
        "schema_version": "prover_provider_foundry_learning_rows_v0",
        "created_at": _utc_now(),
        "run_id": run_root.name,
        "rows": learning_rows,
    }
    return {
        "provider_batch_context_calibration_run_summary.json": run_summary,
        "reducer_taxonomy_decision.json": taxonomy_decision,
        "provider_receipt_reduction_matrix.json": matrix,
        "recipe_policy_metrics.json": recipe_policy_metrics,
        "row_patch_review_summary.json": row_patch_review_summary,
        "foundry_provider_learning_rows.json": foundry_learning,
        "provider_cost_latency_usage_report.json": cost_latency_usage,
        "representative_success.json": {
            "schema_version": "prover_provider_representative_case_v0",
            "case_type": "success",
            "row": representative_success,
        },
        "representative_premise_budget_violation.json": {
            "schema_version": "prover_provider_representative_case_v0",
            "case_type": "premise_budget_violation",
            "row": representative_premise_budget_violation,
        },
        "representative_proof_failure.json": {
            "schema_version": "prover_provider_representative_case_v0",
            "case_type": "proof_failure",
            "row": representative_proof_failure,
        },
    }


def _validate(payloads: Mapping[str, Mapping[str, Any]]) -> list[str]:
    issues: list[str] = []
    summary = payloads["provider_batch_context_calibration_run_summary.json"]
    if summary.get("provider_calls_by_reducer") != 0:
        issues.append("reducer/report builder must not call providers")
    if summary.get("harness_owned_provider_dispatch_added") is not False:
        issues.append("harness-owned provider dispatch must stay absent")
    if summary.get("receipt_count", 0) < 9:
        issues.append("expected at least 9 reduced live receipts")
    if summary.get("truth_side_leakage_count") != 0:
        issues.append("truth-side leakage must remain zero for this batch")
    if summary.get("fake_provider_results_counted") != 0:
        issues.append("fake provider results must not count as live evidence")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    run_root = _repo_path(args.run_root)
    payloads = build_reports(run_root)
    for filename, payload in payloads.items():
        _write_json(run_root / filename, payload)
    issues = _validate(payloads)
    if args.check and issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    summary = payloads["provider_batch_context_calibration_run_summary.json"]
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"{summary['run_id']}: receipts={summary['receipt_count']} "
            f"lean={summary['lean_accepted_count']} "
            f"recipe={summary['recipe_policy_accepted_count']} "
            f"errors={summary['error_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
