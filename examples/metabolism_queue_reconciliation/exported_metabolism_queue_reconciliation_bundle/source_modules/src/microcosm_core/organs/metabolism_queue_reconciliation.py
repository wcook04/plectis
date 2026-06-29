"""
Metabolism queue reconciliation organ.

This organ surfaces the public ``metabolism_runtime`` engine-room capsule as a
first-class durable-queue-and-reconciliation organ. The capsule body stays in
``microcosm_core.engine_room.metabolism_runtime``; this file adds the standard
organ contract: bounded fixture cases, planted negative (rejected-state) cases,
a ``result_card`` projection, body-free receipt writes, and CLI dispatch.

The mechanism it surfaces: a *synthetic durable job queue with cold-start
reconciliation*. The capsule stands up a temp/in-memory SQLite store, enqueues
jobs under an active-idempotency uniqueness guard, leases a job to a worker,
recovers a lease that has expired, projects active blackboard claims after a
contradiction event, and reconciles the queue/run/log triple against a small
taxonomy of inconsistency rules that require operator review rather than
auto-repair. The runner exercises the capsule over positive shapes (lease
recovery moving an expired claim to ``recoverable`` with a healthy reconcile,
and a claim-event projection where a contradiction invalidates the assertion)
and self-falsifies: a store where a job is marked ``running`` with no run row,
and a store where a run is finalized while its job is still ``running``, are
both rejected by the capsule's reconciler, and the runner asserts the expected
reconciliation rule id fires for each planted defect.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.metabolism_queue_reconciliation` as a documented Microcosm public source module.
- Mechanism: Keeps executable runtime/reconciliation source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, SPEC, build_result, result_card, run, run_metabolism_queue_reconciliation_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, provider calls, agent dispatch, live-database export, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates queue, lease, blackboard, and reconciliation computation to the surfaced capsule, and projection, serialization, and receipt behavior to file-local functions.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.metabolism_runtime, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, and package data only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem reads, the per-run temp scratch store, and CLI argument reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.metabolism_runtime import evaluate_case
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "metabolism_queue_reconciliation"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a synthetic store carrying a
# queue/run inconsistency MUST be rejected by the capsule's reconciler, and the
# expected reconciliation rule id must be among the firing rules. The runner
# marks a case "negative" when its declared expectation is rejection.
EXPECTED_NEGATIVE_CASES = {
    "running_job_no_run_row_rejected": ("running_job_no_run_row",),
    "finalized_run_running_job_rejected": ("run_finalized_but_job_running",),
}

CLAIM_CEILING = (
    "Exercises a synthetic SQLite durable-queue capsule over bounded public "
    "fixtures: an active-idempotency uniqueness guard, lease claim and expired-"
    "lease recovery to a recoverable state, a blackboard claim-event projection "
    "where a contradiction invalidates an assertion, and a cold-start "
    "reconciliation taxonomy over the job/run/log triple. It rejects inconsistent "
    "store states by recomputation, asserting the expected reconciliation rule "
    "id fires. It does not ship the private live metabolism database, does not "
    "dispatch agents or call providers, does not auto-repair ambiguous state, is "
    "not a distributed database, and does not authorize release or publication."
)
ANTI_CLAIM = (
    "The metabolism queue reconciliation organ runs against a per-case synthetic "
    "temp SQLite store seeded from public fixtures only. It is not the live "
    "private metabolism runtime, does not export the production queue database, "
    "scheduler daemon, provider state, credentials, or raw operator threads; it "
    "does not dispatch agents, call providers, or auto-repair ambiguous runtime "
    "state, and it does not authorize release or publication. A planted "
    "inconsistency cannot pass because the capsule's reconciler recomputes the "
    "job/run/log relationship and emits the matching review rule."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "dispatches_agents": False,
    "exports_live_queue_database": False,
    "calls_providers": False,
    "auto_repairs_ambiguous_state": False,
    "distributed_database": False,
    "oracle_or_prover": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Metabolism queue reconciliation",
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
    - Teleology: Implements `_read_json` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
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


def _fired_reconciliation_rules(receipt: Mapping[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_fired_reconciliation_rules` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
    - Preconditions: receipt is a capsule evaluate_case result whose inner receipt may carry a reconciliation payload with rule_counts.
    - Guarantee: Returns the ordered list of reconciliation rule ids the capsule reported firing, or an empty list when none are present.
    - Fails: Does not raise on well-formed input.
    - Reads: call arguments.
    - Writes: return values.
    """
    inner = receipt.get("receipt")
    reconciliation = inner.get("reconciliation") if isinstance(inner, Mapping) else None
    if not isinstance(reconciliation, Mapping):
        return []
    rule_counts = reconciliation.get("rule_counts")
    if not isinstance(rule_counts, Mapping):
        return []
    return [str(rule) for rule, count in rule_counts.items() if int(count or 0) > 0]


def _evaluate_case(case: Mapping[str, Any], *, scratch: Path) -> dict[str, Any]:
    """
    [ACTION]
    Run one bounded queue/reconciliation exercise and report observed-versus-expected.

    Each exercise runs one synthetic-store scenario against the surfaced capsule:
    a positive case expects the capsule to compute the queue/blackboard scenario
    cleanly (capsule case status ``pass`` with no reconciliation defect), while a
    negative case expects the capsule's reconciler to reject a planted store
    inconsistency by firing a specific reconciliation rule id.
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries case_id, case_type, expected_ok, and the case_kind the capsule dispatches on; scratch is a writable temp root.
    - Guarantee: Returns a row capturing observed_ok, the capsule status, and the firing reconciliation rule ids.
    - Fails: Propagates ValueError for unknown capsule case kinds and any runner/JSON errors raised by the capsule.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, a per-case scratch directory created by the capsule.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))

    # The capsule expects pass for every well-formed scenario it can run; the
    # synthetic store either computes cleanly or correctly detects its planted
    # defect, so the capsule's own expected_status stays "pass" in both shapes.
    capsule_case = {**case, "expected_status": "pass"}
    observed = evaluate_case(capsule_case, scratch=scratch, path=case_id)
    capsule_status = str(observed.get("observed_status") or "")
    capsule_clean = capsule_status == "pass" and bool(observed.get("expectation_met"))
    fired_rules = _fired_reconciliation_rules(observed)

    if case_type == "negative":
        expected_rules = EXPECTED_NEGATIVE_CASES.get(case_id, ())
        rules_present = bool(expected_rules) and all(rule in fired_rules for rule in expected_rules)
        # A negative passes only when the capsule rejected the store by firing
        # the expected reconciliation rule(s) and the declared expectation was
        # rejection (expected_ok is False).
        observed_ok = capsule_clean and rules_present and (expected_ok is False)
    else:
        # A positive passes only when the capsule computed the scenario cleanly,
        # the declared expectation was acceptance, and no reconciliation rule
        # fired (a clean store needs no operator review).
        observed_ok = capsule_clean and (expected_ok is True) and not fired_rules

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "capsule_status": capsule_status,
        "capsule_clean": capsule_clean,
        "observed_ok": observed_ok,
        "case_kind": str(observed.get("case_kind") or ""),
        "fired_reconciliation_rules": fired_rules,
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases via _fixture_cases.
    - Guarantee: Returns the aggregated result envelope with a pass/fail status over positive and negative cases.
    - Fails: Propagates IO/JSON/runtime errors raised by case loading or capsule evaluation.
    - Reads: declared filesystem inputs, module constants, imported helpers.
    - Writes: return values, a transient temp scratch tree removed before return.
    """
    cases = [case for _path, case in _fixture_cases(input_path)]
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_") as tmp:
        scratch = Path(tmp)
        rows = [_evaluate_case(case, scratch=scratch) for case in cases]

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
        "input_mode": "metabolism_queue_reconciliation_fixture_cases",
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
    - Teleology: Implements `result_card` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `run` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases; out_dir is writable.
    - Guarantee: Computes the result, writes body-free receipts, and returns the result envelope.
    - Fails: Propagates IO/JSON/runtime errors raised by the body.
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


def run_metabolism_queue_reconciliation_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_metabolism_queue_reconciliation_bundle` for `microcosm_core.organs.metabolism_queue_reconciliation` as the runtime-spine entry point.
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
    - Teleology: Implements `build_parser` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
    """
    parser = argparse.ArgumentParser(
        description="Run the metabolism queue reconciliation organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-metabolism-queue-reconciliation-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.metabolism_queue_reconciliation` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass, 1 on fail.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-metabolism-queue-reconciliation-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
