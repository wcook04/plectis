"""
Bridge campaign DAG validation organ.

This organ surfaces the public ``bridge_campaign_dag`` engine-room capsule as a
first-class agent-orchestration organ. The capsule body stays in
``microcosm_core.engine_room.bridge_campaign_dag``; this file adds the standard
organ contract: bounded fixture cases, planted negative (rejected-campaign)
cases, a ``result_card`` projection, body-free receipt writes, and CLI dispatch.

The mechanism it surfaces: a *fan-in campaign DAG validator*. A bridge campaign
is a small directed graph of probe, reducer, and synthesis nodes that fan
several parallel reads into a single synthesis. The capsule validates one such
spec against a public-safe subset of the macro CR/VR rule families: it checks
schema and identity fields, that node labels are unique, that dependency edges
reference existing nodes, that the graph is acyclic (DFS cycle detection), that
exactly one synthesis node exists and transitively reaches a probe, that the
barrier names the synthesis, and that the requested worker count stays within
the provider's safe-parallelism ceiling. The runner exercises the validator
over positive specs (a linear chain and a fan-in) and self-falsifies: a campaign
with a dependency cycle and a campaign with two synthesis nodes are both
rejected, and the runner asserts the expected rejection rule id fires.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.bridge_campaign_dag_validation` as a documented Microcosm public source module.
- Mechanism: Keeps executable validation source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, SPEC, build_result, result_card, run, run_bridge_campaign_dag_validation_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, provider calls, agent dispatch, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates the campaign DAG validation to the surfaced capsule, and projection, serialization, and receipt behavior to file-local functions.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.bridge_campaign_dag, microcosm_core.receipts
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

from microcosm_core.engine_room.bridge_campaign_dag import validate_campaign
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "bridge_campaign_dag_validation"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a malformed campaign MUST be
# rejected, and the expected rule id must be among the firing rejections. The
# runner marks a case "negative" when its declared expectation is rejection.
EXPECTED_NEGATIVE_CASES = {
    "cycle_rejected": ("CR012",),
    "two_synthesis_rejected": ("CR013",),
}

CLAIM_CEILING = (
    "Validates a bridge campaign fan-in DAG against a public-safe subset of the "
    "macro CR/VR rule families over bounded public fixtures: schema and identity "
    "fields, unique node labels, existing dependency edges, acyclicity, exactly "
    "one synthesis node that reaches a probe, barrier alignment, and the provider "
    "safe-parallelism ceiling. It rejects malformed campaigns by recomputation. "
    "It does not dispatch agents, execute campaigns, prove provider correctness, "
    "authorize release, or claim full private-root equivalence."
)
ANTI_CLAIM = (
    "The bridge campaign DAG validation organ checks campaign specs over public "
    "fixture inputs only. It is not a dispatcher, does not run multi-agent "
    "execution, does not prove provider safety, does not export private macro "
    "state, credentials, provider state, or raw operator threads; it does not "
    "call providers or external solvers, and it does not authorize release or "
    "publication. A malformed campaign cannot pass because the validator "
    "recomputes the graph structure and rejects any spec that breaks a rule."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "dispatches_agents": False,
    "executes_campaigns": False,
    "provider_safety_proof": False,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Bridge campaign DAG validation",
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
    - Teleology: Implements `_read_json` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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


def _reject_codes(result_dict: Mapping[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_reject_codes` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
    - Preconditions: result_dict is a ValidationResult.to_dict() mapping with a decisions list.
    - Guarantee: Returns the ordered rule ids whose outcome is "reject".
    - Fails: Does not raise on well-formed input.
    - Reads: call arguments.
    - Writes: return values.
    """
    decisions = result_dict.get("decisions", [])
    return [
        str(decision.get("rule_id"))
        for decision in decisions
        if isinstance(decision, Mapping) and decision.get("outcome") == "reject"
    ]


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Run one bounded campaign-validation exercise and report observed-versus-expected.

    Each exercise validates one campaign spec against the surfaced capsule: a
    positive case expects the campaign to validate cleanly, while a negative case
    expects rejection with a specific rule id firing.
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries a campaign spec plus case_id, case_type, expected_ok, and optional provider/workers.
    - Guarantee: Returns a row capturing observed_ok, the validity verdict, and the firing reject rule ids.
    - Fails: Propagates only mapping/parse errors raised by the capsule.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))
    provider = str(case.get("provider") or "chatgpt")
    workers = int(case.get("workers") or 1)

    result = validate_campaign(case, provider=provider, workers=workers)
    observed_valid = bool(result.ok)
    reject_codes = _reject_codes(result.to_dict())
    expectation_met = observed_valid == expected_ok

    if case_type == "negative":
        expected_codes = EXPECTED_NEGATIVE_CASES.get(case_id, ())
        codes_present = all(code in reject_codes for code in expected_codes)
        observed_ok = (not observed_valid) and expectation_met and codes_present
    else:
        observed_ok = observed_valid and expectation_met

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "observed_valid": observed_valid,
        "expectation_met": expectation_met,
        "observed_ok": observed_ok,
        "provider": provider,
        "workers": workers,
        "reject_rule_ids": reject_codes,
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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
        "input_mode": "bridge_campaign_dag_fixture_cases",
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
    - Teleology: Implements `result_card` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `run` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
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


def run_bridge_campaign_dag_validation_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_bridge_campaign_dag_validation_bundle` for `microcosm_core.organs.bridge_campaign_dag_validation` as the runtime-spine entry point.
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
    - Teleology: Implements `build_parser` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
    """
    parser = argparse.ArgumentParser(
        description="Run the bridge campaign DAG validation organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-bridge-campaign-dag-validation-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.bridge_campaign_dag_validation` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass, 1 on fail.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-bridge-campaign-dag-validation-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
