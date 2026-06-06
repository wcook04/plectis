"""Public-safe navigation fitness benchmark capsule.

This is a source-faithful public refactor of `system/lib/navigation_fitness.py`.
It preserves the benchmark core: each cold-task fixture carries expected stable
ids, forbidden first routes, latency budgets, and route-packet artifacts; the
evaluator reports recall, precision, latency status, and debt candidates.

The capsule evaluates public route-packet fixtures. It does not run the private
macro `kernel.py`, does not validate embeddings, and does not claim universal
navigation benchmark authority. A live-kernel claim requires packets captured
from the real route runner.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_navigation_fitness_benchmark_v1"
ORGAN_ID = "engine_room_navigation_fitness_benchmark"
SOURCE_REFS = ("system/lib/navigation_fitness.py",)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Curated route-packet benchmark evaluator for expected stable ids, "
    "forbidden first routes, and latency budgets. It is not a live private "
    "kernel run, not an embedding benchmark, not a universal navigation "
    "benchmark, and not release authority."
)
ANTI_CLAIMS = (
    "not_live_private_kernel_run",
    "not_embedding_benchmark",
    "not_universal_navigation_benchmark",
    "not_release_authority",
)
DEFAULT_LATENCY_BUDGET_MS = 1500


@dataclass(frozen=True)
class NavigationFitnessTask:
    task_id: str
    family: str
    task_prompt: str
    route_type: str
    expected_artifacts: tuple[str, ...]
    forbidden_first_routes: tuple[str, ...] = ()
    latency_budget_ms: int = DEFAULT_LATENCY_BUDGET_MS
    route_role: str = "first_contact"
    scent_terms: tuple[str, ...] = ()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _as_strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def task_from_mapping(row: Mapping[str, Any]) -> NavigationFitnessTask:
    return NavigationFitnessTask(
        task_id=_string(row.get("task_id")) or "unknown_task",
        family=_string(row.get("family")) or "public_fixture",
        task_prompt=_string(row.get("task_prompt")),
        route_type=_string(row.get("route_type")) or "context_pack",
        expected_artifacts=_as_strings(row.get("expected_artifacts")),
        forbidden_first_routes=_as_strings(row.get("forbidden_first_routes")),
        latency_budget_ms=int(row.get("latency_budget_ms") or DEFAULT_LATENCY_BUDGET_MS),
        route_role=_string(row.get("route_role")) or "first_contact",
        scent_terms=_as_strings(row.get("scent_terms")),
    )


def _percentile(values: Sequence[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(int(value) for value in values)
    index = min(len(ordered) - 1, max(0, math.ceil((percentile / 100.0) * len(ordered)) - 1))
    return ordered[index]


def _match_expected(expected: set[str], selected: set[str]) -> tuple[list[str], list[str]]:
    found: list[str] = []
    missing: list[str] = []
    for item in sorted(expected):
        if item.endswith("*"):
            prefix = item[:-1]
            if any(candidate.startswith(prefix) for candidate in selected):
                found.append(item)
            else:
                missing.append(item)
        elif item in selected:
            found.append(item)
        else:
            missing.append(item)
    return found, missing


def _packet_artifacts(packet: Mapping[str, Any]) -> set[str]:
    artifacts = set(_as_strings(packet.get("selected_artifacts")))
    selected_rows = packet.get("selected_rows")
    if isinstance(selected_rows, Sequence) and not isinstance(selected_rows, (str, bytes)):
        for row in selected_rows:
            if not isinstance(row, Mapping):
                continue
            kind_id = _string(row.get("kind_id"))
            row_id = _string(row.get("row_id"))
            if kind_id and row_id:
                artifacts.add(f"{kind_id}:{row_id}")
            for item in _as_strings(row.get("artifact_ids")):
                artifacts.add(item)
    return artifacts


def _packet_scent_text(packet: Mapping[str, Any]) -> str:
    parts = [
        packet.get("summary"),
        packet.get("title"),
        packet.get("route_hint"),
        packet.get("first_contact_command"),
        " ".join(_as_strings(packet.get("selected_artifacts"))),
    ]
    selected_rows = packet.get("selected_rows")
    if isinstance(selected_rows, Sequence) and not isinstance(selected_rows, (str, bytes)):
        for row in selected_rows:
            if isinstance(row, Mapping):
                parts.extend([row.get("title"), row.get("summary"), row.get("reason")])
    return " ".join(str(part or "") for part in parts).lower()


def _scent_status(task: NavigationFitnessTask, packet: Mapping[str, Any]) -> tuple[str, list[str]]:
    terms = [term.lower() for term in task.scent_terms if term]
    if not terms:
        return "unscored", []
    text = _packet_scent_text(packet)
    missing = [term for term in terms if term not in text]
    return ("pass" if not missing else "fail", missing)


def evaluate_task(task: NavigationFitnessTask, packet: Mapping[str, Any]) -> dict[str, Any]:
    selected = _packet_artifacts(packet)
    expected = set(task.expected_artifacts)
    found, missing = _match_expected(expected, selected)
    first_contact_command = _string(packet.get("first_contact_command"))
    command_used = _string(packet.get("command_used")) or first_contact_command
    forbidden_hits = [route for route in task.forbidden_first_routes if route and route in first_contact_command]
    wall_ms = int(packet.get("wall_ms") or 0)
    timed_out = bool(packet.get("timed_out"))
    error = packet.get("error")
    scent_status, missing_scent_terms = _scent_status(task, packet)
    recall = 1.0 if not expected else len(found) / len(expected)
    precision = 1.0 if not selected else len(found) / max(1, len(selected))

    if timed_out:
        sufficiency_status = "fail"
        failure_kind = "route_timeout"
    elif error:
        sufficiency_status = "fail"
        failure_kind = "route_error"
    elif missing:
        sufficiency_status = "fail"
        failure_kind = "missing_id"
    elif scent_status == "fail":
        sufficiency_status = "fail"
        failure_kind = "weak_scent"
    elif forbidden_hits:
        sufficiency_status = "fail"
        failure_kind = "forbidden_route"
    else:
        sufficiency_status = "pass"
        failure_kind = None

    latency_status = "timeout" if timed_out else "pass" if wall_ms <= task.latency_budget_ms else "fail"
    return {
        "task_id": task.task_id,
        "family": task.family,
        "task_prompt": task.task_prompt,
        "route_type": task.route_type,
        "route_role": task.route_role,
        "command_used": command_used,
        "first_contact_command": first_contact_command,
        "wall_ms": wall_ms,
        "latency_budget_ms": task.latency_budget_ms,
        "latency_status": latency_status,
        "selected_artifacts": sorted(selected),
        "selected_artifact_count": len(selected),
        "expected_artifacts": sorted(expected),
        "found_expected_artifacts": found,
        "missing_expected_artifacts": missing,
        "recall_at_packet": round(recall, 4),
        "precision_at_packet": round(precision, 4),
        "forbidden_first_route_hits": forbidden_hits,
        "scent_status": scent_status,
        "missing_scent_terms": missing_scent_terms,
        "sufficiency_status": sufficiency_status,
        "sufficiency_failure_kind": failure_kind,
        "timed_out": timed_out,
        "error": error,
    }


def _route_type_metrics(results: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for result in results:
        buckets.setdefault(_string(result.get("route_type")) or "unknown", []).append(result)
    metrics: dict[str, dict[str, Any]] = {}
    for route_type, rows in sorted(buckets.items()):
        metrics[route_type] = {
            "task_count": len(rows),
            "sufficiency_pass_count": sum(1 for row in rows if row.get("sufficiency_status") == "pass"),
            "sufficiency_fail_count": sum(1 for row in rows if row.get("sufficiency_status") == "fail"),
            "latency_fail_count": sum(1 for row in rows if row.get("latency_status") in {"fail", "timeout"}),
        }
    return metrics


def _debt_candidates(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    debts: list[dict[str, Any]] = []
    for result in results:
        task_id = _string(result.get("task_id"))
        if result.get("sufficiency_status") == "fail":
            debts.append(
                {
                    "debt_id": f"sufficiency:{task_id}",
                    "debt_class": "sufficiency_debt",
                    "repair_class": result.get("sufficiency_failure_kind"),
                    "missing_expected_artifacts": list(result.get("missing_expected_artifacts") or []),
                    "forbidden_first_route_hits": list(result.get("forbidden_first_route_hits") or []),
                }
            )
        if result.get("latency_status") in {"fail", "timeout"}:
            debts.append(
                {
                    "debt_id": f"latency:{task_id}",
                    "debt_class": "latency_debt",
                    "wall_ms": result.get("wall_ms"),
                    "latency_budget_ms": result.get("latency_budget_ms"),
                    "latency_status": result.get("latency_status"),
                }
            )
    return debts


def evaluate_benchmark(benchmark: Mapping[str, Any]) -> dict[str, Any]:
    cases = [case for case in (benchmark.get("cases") or []) if isinstance(case, Mapping)]
    results = [
        evaluate_task(task_from_mapping(case.get("task") if isinstance(case.get("task"), Mapping) else {}), case.get("packet") if isinstance(case.get("packet"), Mapping) else {})
        for case in cases
    ]
    wall_values = [int(result.get("wall_ms") or 0) for result in results]
    debts = _debt_candidates(results)
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": "pass" if results else "fail",
        "suite": _string(benchmark.get("suite")) or "public_fixture",
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "summary": {
            "task_count": len(results),
            "sufficiency_pass_count": sum(1 for result in results if result.get("sufficiency_status") == "pass"),
            "sufficiency_fail_count": sum(1 for result in results if result.get("sufficiency_status") == "fail"),
            "latency_pass_count": sum(1 for result in results if result.get("latency_status") == "pass"),
            "latency_fail_count": sum(1 for result in results if result.get("latency_status") in {"fail", "timeout"}),
            "p50_wall_ms": _percentile(wall_values, 50),
            "p95_wall_ms": _percentile(wall_values, 95),
            "debt_candidate_count": len(debts),
        },
        "route_type_metrics": _route_type_metrics(results),
        "task_results": results,
        "debt_candidates": debts,
    }


def evaluate_case(case: Mapping[str, Any], *, path: str = "") -> dict[str, Any]:
    receipt = evaluate_benchmark(case.get("benchmark") if isinstance(case.get("benchmark"), Mapping) else {})
    expected_summary = case.get("expected_summary") if isinstance(case.get("expected_summary"), Mapping) else {}
    summary_checks = [
        {
            "field": field,
            "expected": expected,
            "observed": receipt["summary"].get(field),
            "ok": receipt["summary"].get(field) == expected,
        }
        for field, expected in expected_summary.items()
    ]
    expected_task_statuses = case.get("expected_task_statuses") if isinstance(case.get("expected_task_statuses"), Mapping) else {}
    by_task = {str(row.get("task_id")): row for row in receipt["task_results"]}
    task_checks = []
    for task_id, expectation in expected_task_statuses.items():
        expected = expectation if isinstance(expectation, Mapping) else {}
        observed = by_task.get(str(task_id), {})
        checks = {
            key: observed.get(key) == value
            for key, value in expected.items()
        }
        task_checks.append(
            {
                "task_id": task_id,
                "expected": dict(expected),
                "observed": {key: observed.get(key) for key in expected},
                "ok": all(checks.values()),
            }
        )
    expectation_met = receipt["status"] == (_string(case.get("expected_status")) or "pass") and all(
        row["ok"] for row in summary_checks + task_checks
    )
    return {
        "case_id": _string(case.get("case_id")) or Path(path).stem,
        "path": path,
        "expected_status": _string(case.get("expected_status")) or "pass",
        "observed_status": receipt["status"],
        "expectation_met": expectation_met,
        "summary_checks": summary_checks,
        "task_checks": task_checks,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"{path} did not contain a JSON object")
        cases.append(evaluate_case(payload, path=str(path)))
    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engine Room navigation fitness benchmark capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("evaluate-benchmark", help="Evaluate a public benchmark JSON file.")
    evaluate.add_argument("--benchmark", required=True)
    evaluate.add_argument("--json", action="store_true")

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "evaluate-benchmark":
        benchmark = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
        if not isinstance(benchmark, Mapping):
            print("benchmark must be a JSON object", file=__import__("sys").stderr)
            return 2
        receipt = evaluate_benchmark(benchmark)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {receipt['status']} tasks={receipt['summary']['task_count']}")
        return 0 if receipt["status"] == "pass" else 1
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
