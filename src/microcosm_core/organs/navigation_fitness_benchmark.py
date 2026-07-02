"""
Implements organs navigation fitness benchmark for the public Plectis package.

Callers enter through `build_result`, `result_card`, `run`,
`run_navigation_fitness_benchmark_bundle`, `build_parser`, and `main`; constants such as
`ORGAN_ID`, `FIXTURE_ID`, `VALIDATOR_ID`, `SCHEMA_VERSION`, and 9 more pin local fixture
names; dependencies include `argparse`, `json`, `pathlib`, `typing`, and 1 more. It builds
public fixture, result, card, or verdict structures while keeping private substrate bodies
out of the payload.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.navigation_fitness_benchmark import evaluate_case
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "navigation_fitness_benchmark"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a route packet whose declared
# expectation is contradicted by the capsule's benchmark recomputation MUST be
# rejected, and the expected reject marker (the recomputed sufficiency failure
# kind for the planted defect) must be observed. The runner marks a case
# "negative" when its declared case_type is "negative" (expected_ok false).
EXPECTED_NEGATIVE_CASES = {
    "missing_stable_id_rejected": ("missing_id",),
    "forbidden_first_route_rejected": ("forbidden_route",),
}

CLAIM_CEILING = (
    "Recomputes a curated route-packet navigation benchmark over bounded public "
    "fixtures: recall and precision of selected artifacts against expected stable "
    "ids, forbidden-first-route checks, scent-term coverage, latency status "
    "against a per-task budget, and sufficiency/latency debt candidates. Each "
    "case carries a planted expectation, and the runner accepts a case only when "
    "the recomputation matches it; planted negative cases are rejected by "
    "recomputation. It is not a live private kernel run, not an embedding "
    "benchmark, not a universal navigation benchmark, and not release authority."
)
ANTI_CLAIM = (
    "The navigation fitness benchmark organ evaluates curated route-packet "
    "fixtures over public inputs only. It does not run the private macro "
    "kernel.py, does not capture packets from the live route runner, does not "
    "validate embeddings, and does not claim universal navigation benchmark "
    "authority. It does not export private macro state, credentials, provider "
    "state, or raw operator threads, does not call providers or external "
    "solvers, and does not authorize release or publication. A packet whose "
    "declared expectation is false cannot pass because the capsule recomputes "
    "recall, precision, forbidden-route, scent, and latency verdicts and rejects "
    "any case whose recomputation contradicts the planted expectation."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "live_private_kernel_run": False,
    "embedding_benchmark": False,
    "universal_navigation_benchmark": False,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Navigation fitness benchmark",
    "fixture_id": FIXTURE_ID,
    "validator_id": VALIDATOR_ID,
    "result_name": RESULT_NAME,
    "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
    "anti_claim": ANTI_CLAIM,
    "authority_ceiling": AUTHORITY_CEILING,
}


def _read_json(path: Path) -> Mapping[str, Any]:
    """
    Read read JSON for `microcosm_core.organs.navigation_fitness_benchmark`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    Return fixture cases for `microcosm_core.organs.navigation_fitness_benchmark`.

    Inputs are `input_path`; notable helpers are `Path`, `is_file`, `FileNotFoundError`,
    `_read_json`, and 1 more; invalid cases raise at their explicit checks.
    """
    path = Path(input_path)
    if path.is_file():
        return [(path, _read_json(path))]
    rows = [(item, _read_json(item)) for item in sorted(path.glob("*.json"))]
    if not rows:
        raise FileNotFoundError(f"no JSON fixture cases under {path}")
    return rows


def _observed_failure_kinds(receipt: Mapping[str, Any]) -> list[str]:
    """
    Produce the observed failure kinds value used by
    `microcosm_core.organs.navigation_fitness_benchmark`.

    Inputs are `receipt`; notable helpers are `get` and `append`.
    """
    kinds: list[str] = []
    for row in receipt.get("task_results", []):
        if not isinstance(row, Mapping):
            continue
        failure_kind = row.get("sufficiency_failure_kind")
        if failure_kind and failure_kind not in kinds:
            kinds.append(str(failure_kind))
        if row.get("latency_status") in {"fail", "timeout"} and "latency_fail" not in kinds:
            kinds.append("latency_fail")
    return kinds


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.navigation_fitness_benchmark._evaluate_case` into the
    payload shape expected by organs navigation fitness benchmark.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))

    evaluation = evaluate_case(case)
    expectation_met = bool(evaluation.get("expectation_met"))
    observed_status = str(evaluation.get("observed_status") or "")
    receipt = evaluation.get("receipt") if isinstance(evaluation.get("receipt"), Mapping) else {}
    observed_failure_kinds = _observed_failure_kinds(receipt)
    accepted = expectation_met
    expectation_aligned = accepted == expected_ok

    if case_type == "negative":
        expected_markers = EXPECTED_NEGATIVE_CASES.get(case_id, ())
        markers_present = all(marker in observed_failure_kinds for marker in expected_markers)
        observed_ok = (not accepted) and expectation_aligned and bool(expected_markers) and markers_present
    else:
        observed_ok = accepted and expectation_aligned

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "accepted": accepted,
        "expectation_met": expectation_met,
        "expectation_aligned": expectation_aligned,
        "observed_ok": observed_ok,
        "observed_status": observed_status,
        "observed_failure_kinds": observed_failure_kinds,
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.navigation_fitness_benchmark.build_result` into the
    payload shape expected by organs navigation fitness benchmark.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    cases = [case for _path, case in _fixture_cases(input_path)]
    rows = [_evaluate_case(case) for case in cases]

    positive_rows = [row for row in rows if row["case_type"] == "positive"]
    negative_rows = [row for row in rows if row["case_type"] == "negative"]
    positive_pass = all(row["observed_ok"] for row in positive_rows)
    negative_observed = all(row["observed_ok"] for row in negative_rows)
    negative_ids = {row["case_id"] for row in negative_rows}
    expected_negatives_present = set(EXPECTED_NEGATIVE_CASES).issubset(negative_ids)
    status = (
        "pass"
        if positive_rows
        and negative_rows
        and positive_pass
        and negative_observed
        and expected_negatives_present
        else "fail"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "status": status,
        "created_at": utc_now(),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "input_mode": "navigation_fitness_benchmark_fixture_cases",
        "case_count": len(rows),
        "positive_case_count": len(positive_rows),
        "negative_case_count": len(negative_rows),
        "passed_positive_case_count": sum(1 for row in positive_rows if row["observed_ok"]),
        "observed_negative_case_count": sum(1 for row in negative_rows if row["observed_ok"]),
        "expected_negative_cases": {k: list(v) for k, v in EXPECTED_NEGATIVE_CASES.items()},
        "cases": rows,
        "body_in_receipt": False,
    }


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.navigation_fitness_benchmark.result_card` into the
    payload shape expected by organs navigation fitness benchmark.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": f"{ORGAN_ID}_board_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "case_count": result.get("case_count"),
        "positive_case_count": result.get("positive_case_count"),
        "negative_case_count": result.get("negative_case_count"),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _validation_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.navigation_fitness_benchmark._validation_receipt` into
    the payload shape expected by organs navigation fitness benchmark.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": f"{ORGAN_ID}_validation_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "fixture_id": FIXTURE_ID,
        "receipt_paths": dict(receipt_paths),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _acceptance_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.navigation_fitness_benchmark._acceptance_receipt` into
    the payload shape expected by organs navigation fitness benchmark.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": f"{ORGAN_ID}_acceptance_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "fixture_id": FIXTURE_ID,
        "real_substrate_disposition": "real_substrate_capsule",
        "generated_receipts": list(receipt_paths.values()),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _receipt_ref(out: Path, name: str) -> str:
    """
    Return receipt ref for the organs navigation fitness benchmark flow.

    Inputs are `out` and `name`; notable helpers are `as_posix`.
    """
    return (out / name).as_posix()


def run(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    Return run for `microcosm_core.organs.navigation_fitness_benchmark`.

    Inputs are `input_path`, `out_dir`, `command`, and `acceptance_out`; notable helpers are
    `build_result`, `Path`, `mkdir`, `write_json_atomic`, and 5 more.
    """
    result = build_result(input_path)
    if command:
        result["command"] = command
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt_paths = {
        "result": _receipt_ref(out, RESULT_NAME),
        "board": _receipt_ref(out, BOARD_NAME),
        "validation": _receipt_ref(out, VALIDATION_RECEIPT_NAME),
    }
    write_json_atomic(out / RESULT_NAME, result)
    write_json_atomic(out / BOARD_NAME, result_card(result))
    write_json_atomic(out / VALIDATION_RECEIPT_NAME, _validation_receipt(result, receipt_paths))
    if acceptance_out is not None:
        acceptance_paths = {**receipt_paths, "acceptance": Path(acceptance_out).as_posix()}
        write_json_atomic(Path(acceptance_out), _acceptance_receipt(result, acceptance_paths))
    return result


def run_navigation_fitness_benchmark_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Return run navigation fitness benchmark bundle for the organs navigation fitness
    benchmark flow.

    Inputs are `input_path`, `out_dir`, and `command`; notable helpers are `run`.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    Register CLI syntax for
    `microcosm_core.organs.navigation_fitness_benchmark.build_parser`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(
        description="Run the navigation fitness benchmark organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-navigation-fitness-benchmark-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the `microcosm_core.organs.navigation_fitness_benchmark` command-line entry point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-navigation-fitness-benchmark-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
