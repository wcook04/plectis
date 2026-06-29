"""
Navigation fitness benchmark organ.

This organ surfaces the public ``navigation_fitness_benchmark`` engine-room
capsule as a first-class navigation-quality organ. The capsule body stays in
``microcosm_core.engine_room.navigation_fitness_benchmark``; this file adds the
standard organ contract: bounded fixture cases, planted negative (rejected by
recomputation) cases, a ``result_card`` projection, body-free receipt writes,
and CLI dispatch.

The mechanism it surfaces: a *route-packet fitness benchmark*. Each cold-task
case carries a navigation task (expected stable ids, forbidden first routes, a
latency budget, scent terms) and a route packet (the artifacts a router
actually selected, the first-contact command, and the observed wall time). The
capsule recomputes recall and precision against the expected ids, checks the
first route against the forbidden list, scores scent-term coverage, derives a
latency verdict against the budget, and collects sufficiency and latency debt
candidates. Each fixture case also carries a planted expectation; the capsule
re-derives the benchmark and reports whether the recomputation matches that
expectation (``expectation_met``).

The runner exercises the capsule over positive cases (a packet whose recomputed
benchmark matches its declared expectation) and self-falsifies: two cases plant
a route defect together with a deliberately wrong expectation that the defective
route is fine. The capsule's recomputation contradicts the planted claim, so it
rejects the case, and the runner asserts that the expected reject marker (the
recomputed sufficiency failure kind for the planted defect) is present.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.navigation_fitness_benchmark` as a documented Microcosm public source module.
- Mechanism: Keeps executable benchmark source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, SPEC, build_result, result_card, run, run_navigation_fitness_benchmark_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, live-kernel runs, embedding evaluation, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates the route-packet benchmark recomputation to the surfaced capsule, and projection, serialization, and receipt behavior to file-local functions.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.navigation_fitness_benchmark, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, and package data only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem reads and CLI argument reads are the only admitted runtime variability.
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
    [ACTION]
    - Teleology: Implements `_read_json` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies a path to a JSON object file.
    - Guarantee: On success returns the parsed mapping.
    - Fails: Propagates IO and JSON errors; raises ValueError when the payload is not a JSON object.
    - Reads: declared filesystem inputs.
    - Writes: return values.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path is a JSON file or a directory containing JSON case files.
    - Guarantee: Returns the ordered list of (path, case) pairs.
    - Fails: Raises FileNotFoundError when a directory holds no JSON cases.
    - Reads: declared filesystem inputs.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `_observed_failure_kinds` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: receipt is the capsule benchmark receipt with a task_results list.
    - Guarantee: Returns the ordered, de-duplicated sufficiency failure kinds the recomputation emitted, with latency-budget failures appended as "latency_fail".
    - Fails: Does not raise on well-formed input.
    - Reads: call arguments.
    - Writes: return values.
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
    [ACTION]
    Run one bounded route-packet benchmark exercise and report observed-versus-expected.

    Each exercise hands one fixture case to the surfaced capsule, which recomputes
    the navigation benchmark and reports whether the recomputation matches the
    case's planted expectation. A positive case expects the expectation to be met
    (the capsule accepts the case cleanly); a negative case plants a route defect
    plus a deliberately wrong expectation, so the recomputation contradicts the
    claim and the case is rejected with a specific failure marker firing.
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries a navigation benchmark fixture plus case_id, case_type, expected_ok, and the capsule's expected_status / expected_summary / expected_task_statuses payload.
    - Guarantee: Returns a row capturing observed_ok, the recomputation verdict, and the observed sufficiency failure markers.
    - Fails: Propagates only mapping/parse errors raised by the capsule.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases via _fixture_cases.
    - Guarantee: Returns the aggregated result envelope with a pass/fail status over positive and negative cases.
    - Fails: Propagates IO/JSON/validation errors raised by case loading.
    - Reads: declared filesystem inputs, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: result is a build_result envelope.
    - Guarantee: Returns a body-free status card with claim ceiling and anti-claim.
    - Fails: Propagates mapping access errors only.
    - Reads: call arguments, module constants.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: result is a build_result envelope; receipt_paths names the written receipts.
    - Guarantee: Returns a body-free validation receipt.
    - Fails: Propagates mapping access errors only.
    - Reads: call arguments, module constants.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: result is a build_result envelope; receipt_paths names the written receipts.
    - Guarantee: Returns a body-free acceptance receipt marking real-substrate disposition.
    - Fails: Propagates mapping access errors only.
    - Reads: call arguments, module constants.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: out is a directory path and name is a receipt filename.
    - Guarantee: Returns the posix path string for the receipt.
    - Fails: Does not raise.
    - Reads: call arguments.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases; out_dir is writable.
    - Guarantee: Computes the result, writes body-free receipts, and returns the result envelope.
    - Fails: Propagates IO/JSON/validation errors raised by the body.
    - Reads: declared filesystem inputs, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
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
    [ACTION]
    - Teleology: Implements `run_navigation_fitness_benchmark_bundle` for `microcosm_core.organs.navigation_fitness_benchmark` as the runtime-spine entry point.
    - Preconditions: input_path resolves to fixture cases; out_dir is writable.
    - Guarantee: Delegates to run and returns its result envelope.
    - Fails: Propagates errors raised by run.
    - Reads: declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `build_parser` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.navigation_fitness_benchmark` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass, 1 on fail.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
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
