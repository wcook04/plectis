"""
Implements organs derived fact provider runtime for the public Plectis package.

Callers enter through `build_result`, `result_card`, `run`,
`run_derived_fact_provider_runtime_bundle`, `build_parser`, and `main`; constants such as
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
    Read read JSON for `microcosm_core.organs.derived_fact_provider_runtime`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    Return fixture cases for `microcosm_core.organs.derived_fact_provider_runtime`.

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


def _defect_error_class(case: Mapping[str, Any], capsule_row: Mapping[str, Any]) -> str | None:
    """
    Return defect error class for the organs derived fact provider runtime flow.

    Inputs are `case` and `capsule_row`; notable helpers are `get`.
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
    Serialize `microcosm_core.organs.derived_fact_provider_runtime._evaluate_case` into the
    payload shape expected by organs derived fact provider runtime.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
    Serialize `microcosm_core.organs.derived_fact_provider_runtime.build_result` into the
    payload shape expected by organs derived fact provider runtime.

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
    Serialize `microcosm_core.organs.derived_fact_provider_runtime.result_card` into the
    payload shape expected by organs derived fact provider runtime.

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
    Serialize `microcosm_core.organs.derived_fact_provider_runtime._validation_receipt` into
    the payload shape expected by organs derived fact provider runtime.

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
    Serialize `microcosm_core.organs.derived_fact_provider_runtime._acceptance_receipt` into
    the payload shape expected by organs derived fact provider runtime.

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
    Return receipt ref for the organs derived fact provider runtime flow.

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
    Return run for `microcosm_core.organs.derived_fact_provider_runtime`.

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


def run_derived_fact_provider_runtime_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Produce the run derived fact provider runtime bundle value used by
    `microcosm_core.organs.derived_fact_provider_runtime`.

    Inputs are `input_path`, `out_dir`, and `command`; notable helpers are `run`.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    Register CLI syntax for
    `microcosm_core.organs.derived_fact_provider_runtime.build_parser`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
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
    Run the `microcosm_core.organs.derived_fact_provider_runtime` command-line entry point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
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
