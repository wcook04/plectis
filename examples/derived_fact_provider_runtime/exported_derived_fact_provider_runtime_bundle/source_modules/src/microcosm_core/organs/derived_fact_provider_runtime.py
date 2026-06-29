"""
Derived fact provider runtime organ.

This organ surfaces the public ``derived_fact_provider_engine`` engine-room
capsule as a first-class registry-backed fact-provider organ. The capsule body
stays in ``microcosm_core.engine_room.derived_fact_provider_engine``; this file
adds the standard organ contract: bounded fixture cases, planted negative
(rejected-provider) cases, a ``result_card`` projection, body-free receipt
writes, and CLI dispatch.

The mechanism it surfaces: a *registry-backed derived fact provider*. A fact
registry is a small list of authored rows; each row names a provider that
resolves a value from a public-safe root. The capsule supports three provider
shapes: ``json_pointer`` (RFC 6901 pointer resolution over a JSON source,
including list-index traversal), ``glob_count`` (count of files matching a glob,
with optional excluded prefixes), and ``callable`` (named computed facts such as
git-tracked file counts). Provider failures do not crash the ledger: they become
error-as-data rows carrying ``provider_status="error"``, an ``error_class``, and
a repair hint, and they degrade the receipt status from ``ok`` to ``degraded``.
The runner exercises the provider over positive registries (clean pointer/glob
resolution and a git-backed callable with a pointer array index) and
self-falsifies: a registry whose source path is absent and a registry naming an
unsupported provider type are both rejected, and the runner asserts the expected
``error_class`` marker fires on the planted-defect fact.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.derived_fact_provider_runtime` as a documented Microcosm public source module.
- Mechanism: Keeps executable provider source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, SPEC, build_result, result_card, run, run_derived_fact_provider_runtime_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, doctrine truth auditing, full macro fact-registry export, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates the registry/provider evaluation to the surfaced capsule, and projection, serialization, and receipt behavior to file-local functions.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.derived_fact_provider_engine, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, and the git binary only where individual call bodies (and the surfaced capsule's callable facts) reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem reads, the git subprocess used by callable facts, and CLI argument reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.derived_fact_provider_engine import evaluate_case
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "derived_fact_provider_runtime"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a malformed registry MUST be
# rejected, and the expected provider error_class must be the one the capsule
# emits on the planted-defect fact row. The runner marks a case "negative" when
# its declared expectation is rejection (expected_ok is false). Each value is
# the exact ``error_class`` string the surfaced capsule records for the defect.
EXPECTED_NEGATIVE_CASES = {
    "missing_source_path_rejected": "FileNotFoundError",
    "unknown_provider_type_rejected": "ValueError",
}

CLAIM_CEILING = (
    "Exercises a registry-backed derived fact provider over bounded public "
    "fixture roots: it resolves json_pointer (RFC 6901, including list-index "
    "traversal), glob_count (with excluded prefixes), and named callable facts "
    "(git-tracked counts), and it turns provider failures into error-as-data "
    "rows that degrade the receipt status rather than crash the ledger. "
    "Positive cases must resolve to the expected values with a clean receipt; "
    "negative cases must be rejected by recomputation with the expected provider "
    "error_class firing on the planted-defect fact. It is not a doctrine truth "
    "auditor, not a full macro fact-registry export, not semantic claim "
    "validation, and it does not authorize release or publication."
)
ANTI_CLAIM = (
    "The derived fact provider runtime organ evaluates authored fact registries "
    "over public fixture roots only. It does not audit whether prose claims are "
    "true, does not export the full macro fact registry, does not perform "
    "semantic claim validation, does not export private macro state, "
    "credentials, or raw operator threads, and it does not authorize release or "
    "publication. A clean provider receipt means the registered facts resolved "
    "against the supplied root, not that any downstream claim is true. A "
    "malformed registry cannot pass because the provider recomputes each row and "
    "records the planted defect as an error-as-data row with the expected "
    "error_class."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "doctrine_truth_auditor": False,
    "full_macro_registry_export": False,
    "semantic_claim_validation": False,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Derived fact provider runtime",
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
    - Teleology: Implements `_read_json` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
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


def _defect_error_class(case: Mapping[str, Any], capsule_row: Mapping[str, Any]) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `_defect_error_class` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries an optional defect_fact_id; capsule_row is one evaluate_case row.
    - Guarantee: Returns the error_class the capsule recorded for the planted-defect fact, or None when absent.
    - Fails: Does not raise on well-formed input.
    - Reads: call arguments.
    - Writes: return values.
    """
    defect_fact_id = str(case.get("defect_fact_id") or "")
    if not defect_fact_id:
        return None
    facts = capsule_row.get("receipt", {}).get("ledger", {}).get("facts", [])
    for fact in facts:
        if isinstance(fact, Mapping) and str(fact.get("id")) == defect_fact_id:
            if fact.get("provider_status") == "error":
                return str(fact.get("error_class") or "")
            return None
    return None


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Run one bounded fact-provider exercise and report observed-versus-expected.

    Each exercise evaluates one authored registry against the surfaced capsule: a
    positive case expects every provider row to resolve cleanly to the expected
    values with an ``ok`` receipt, while a negative case expects the registry to
    be rejected with a specific provider ``error_class`` firing on the
    planted-defect fact.
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries a registry plus case_id, case_type, expected_ok, and the capsule's evaluate_case payload (files/git_tracked/expected_values/expected_error_ids/expected_status); negatives additionally carry defect_fact_id.
    - Guarantee: Returns a row capturing observed_ok, the capsule expectation verdict, observed status, and the firing defect error_class.
    - Fails: Propagates only mapping/parse/subprocess errors raised by the capsule.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))

    capsule_row = evaluate_case(case, path=case_id)
    expectation_met = bool(capsule_row.get("expectation_met"))
    observed_status = str(capsule_row.get("observed_status") or "")
    defect_error_class = _defect_error_class(case, capsule_row)

    if case_type == "negative":
        expected_marker = EXPECTED_NEGATIVE_CASES.get(case_id)
        marker_present = (
            expected_marker is not None
            and defect_error_class is not None
            and defect_error_class == expected_marker
        )
        observed_ok = (not expected_ok) and expectation_met and observed_status == "degraded" and marker_present
    else:
        observed_ok = expected_ok and expectation_met and observed_status == "ok"

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "expectation_met": expectation_met,
        "observed_status": observed_status,
        "observed_ok": observed_ok,
        "expected_error_class": EXPECTED_NEGATIVE_CASES.get(case_id),
        "observed_error_class": defect_error_class,
        "value_checks": list(capsule_row.get("value_checks") or []),
        "error_checks": list(capsule_row.get("error_checks") or []),
        "unexpected_error_ids": list(capsule_row.get("unexpected_error_ids") or []),
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases via _fixture_cases.
    - Guarantee: Returns the aggregated result envelope with a pass/fail status over positive and negative cases.
    - Fails: Propagates IO/JSON/subprocess errors raised by case loading or capsule evaluation.
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
        "input_mode": "derived_fact_provider_registry_fixture_cases",
        "case_count": len(rows),
        "positive_case_count": len(positive_rows),
        "negative_case_count": len(negative_rows),
        "passed_positive_case_count": sum(1 for row in positive_rows if row["observed_ok"]),
        "observed_negative_case_count": sum(1 for row in negative_rows if row["observed_ok"]),
        "expected_negative_cases": {k: v for k, v in EXPECTED_NEGATIVE_CASES.items()},
        "cases": rows,
        "body_in_receipt": False,
    }


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `run` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases; out_dir is writable.
    - Guarantee: Computes the result, writes body-free receipts, and returns the result envelope.
    - Fails: Propagates IO/JSON/subprocess errors raised by the body.
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


def run_derived_fact_provider_runtime_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_derived_fact_provider_runtime_bundle` for `microcosm_core.organs.derived_fact_provider_runtime` as the runtime-spine entry point.
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
    - Teleology: Implements `build_parser` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
    """
    parser = argparse.ArgumentParser(
        description="Run the derived fact provider runtime organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-derived-fact-provider-runtime-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.derived_fact_provider_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass, 1 on fail.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-derived-fact-provider-runtime-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
