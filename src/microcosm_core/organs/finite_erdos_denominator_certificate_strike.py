"""
Implements organs finite erdos denominator certificate strike for the public Plectis
package.

Callers enter through `build_result`, `result_card`, `run`,
`run_finite_erdos_denominator_certificate_strike_bundle`, `build_parser`, and `main`;
constants such as `ORGAN_ID`, `FIXTURE_ID`, `VALIDATOR_ID`, `SCHEMA_VERSION`, and 9 more pin
local fixture names; dependencies include `argparse`, `json`, `pathlib`, `typing`, and 1
more. It builds public fixture, result, card, or verdict structures while keeping private
substrate bodies out of the payload.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.finite_denominator_order_certificate import (
    ERROR_CODES,
    compute_finite_denominator_order_certificate,
    verify_finite_denominator_order_certificate,
)
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "finite_erdos_denominator_certificate_strike"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a forged certificate MUST be
# rejected by recomputation. The runner marks a case "negative" when its declared
# expectation is that a guard fires.
EXPECTED_NEGATIVE_CASES = {
    "forged_order_rejected": (ERROR_CODES["order"],),
    "forged_denominator_rejected": (ERROR_CODES["denominator"],),
}

CLAIM_CEILING = (
    "Computes the finite denominator-order certificate ord_Q(b) = lcm(F) for "
    "S_F(b) = sum_{n in F} 1/(b^n - 1) = P/Q in exact rational arithmetic over "
    "bounded public fixtures, and rejects forged certificates by recomputation. "
    "It does not prove the open infinite Erdos #257 problem, is not an oracle, "
    "prover, or provider result, and a holding certificate is a bounded "
    "computational witness, not a machine-checked proof of even the finite "
    "statement."
)
ANTI_CLAIM = (
    "The finite Erdos denominator-order certificate strike computes exact "
    "rationals and multiplicative orders over public fixture inputs only. It "
    "does not solve or claim to solve Erdos #257, does not export private macro "
    "state, credentials, provider state, or raw operator threads; it does not "
    "call providers or external solvers, and it does not authorize release or "
    "publication. A forged certificate cannot pass because the runner recomputes "
    "the truth and rejects any claimed value that disagrees."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "solves_erdos257": False,
    "infinite_problem_proof": False,
    "machine_checked_proof": False,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Finite Erdos denominator-order certificate strike",
    "fixture_id": FIXTURE_ID,
    "validator_id": VALIDATOR_ID,
    "result_name": RESULT_NAME,
    "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
    "anti_claim": ANTI_CLAIM,
    "authority_ceiling": AUTHORITY_CEILING,
}


def _read_json(path: Path) -> Mapping[str, Any]:
    """
    Read read JSON for `microcosm_core.organs.finite_erdos_denominator_certificate_strike`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    Produce the fixture cases value used by
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike`.

    Inputs are `input_path`; notable helpers are `Path`, `is_file`, `FileNotFoundError`,
    `_read_json`, and 1 more; invalid cases raise from the explicit checks in the body.
    """
    path = Path(input_path)
    if path.is_file():
        return [(path, _read_json(path))]
    rows = [(item, _read_json(item)) for item in sorted(path.glob("*.json"))]
    if not rows:
        raise FileNotFoundError(f"no JSON fixture cases under {path}")
    return rows


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serialize
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike._evaluate_case` into
    the payload shape expected by organs finite erdos denominator certificate strike.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    exercise = str(case.get("exercise") or "")
    case_id = str(case.get("case_id") or exercise)
    case_type = str(case.get("case_type") or "positive")
    support = [int(n) for n in case.get("support", [])]
    base = int(case.get("base", 0))

    if exercise in {"certificate_holds", "certificate_holds_after_reduction"}:
        cert = compute_finite_denominator_order_certificate(support, base)
        claimed = case.get("claimed")
        claimed_ok = True
        if isinstance(claimed, Mapping):
            verdict = verify_finite_denominator_order_certificate(support, base, claimed)
            claimed_ok = bool(verdict["valid"])
        require_reduction = exercise == "certificate_holds_after_reduction"
        observed_ok = (
            bool(cert.get("holds"))
            and claimed_ok
            and (not require_reduction or bool(cert.get("reduced")))
        )
        return {
            "case_id": case_id,
            "case_type": case_type,
            "exercise": exercise,
            "observed_ok": observed_ok,
            "support": cert.get("support"),
            "base": cert.get("base"),
            "numerator": cert.get("numerator"),
            "denominator": cert.get("denominator"),
            "order": cert.get("order"),
            "lcm": cert.get("lcm"),
            "reduced": cert.get("reduced"),
            "certificate_holds": cert.get("holds"),
            "observed_error_codes": [],
        }

    if exercise in {"forged_order_rejected", "forged_denominator_rejected"}:
        claimed = case.get("claimed")
        if not isinstance(claimed, Mapping):
            return {
                "case_id": case_id,
                "case_type": case_type,
                "exercise": exercise,
                "observed_ok": False,
                "observed_error_codes": ["ERDOS_CERT_MISSING_CLAIMED_FORGERY"],
            }
        verdict = verify_finite_denominator_order_certificate(support, base, claimed)
        expected_codes = EXPECTED_NEGATIVE_CASES.get(case_id, ())
        rejected = not verdict["valid"]
        codes_present = all(code in verdict["error_codes"] for code in expected_codes)
        # Negative case: the guard fires (the forged certificate is rejected with
        # the expected mismatch code) when recomputation catches the lie.
        return {
            "case_id": case_id,
            "case_type": case_type,
            "exercise": exercise,
            "observed_ok": rejected and codes_present,
            "rejected": rejected,
            "recomputed_denominator": verdict["recomputed"].get("denominator"),
            "recomputed_order": verdict["recomputed"].get("order"),
            "observed_error_codes": list(verdict["error_codes"]),
        }

    return {
        "case_id": case_id,
        "case_type": case_type,
        "exercise": exercise,
        "observed_ok": False,
        "observed_error_codes": ["ERDOS_CERT_UNKNOWN_EXERCISE"],
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    Serialize
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike.build_result` into
    the payload shape expected by organs finite erdos denominator certificate strike.

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
        "input_mode": "finite_erdos_denominator_certificate_fixture_cases",
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
    Serialize
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike.result_card` into the
    payload shape expected by organs finite erdos denominator certificate strike.

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
    Serialize
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike._validation_receipt`
    into the payload shape expected by organs finite erdos denominator certificate strike.

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
    Serialize
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike._acceptance_receipt`
    into the payload shape expected by organs finite erdos denominator certificate strike.

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
    Return receipt ref for the organs finite erdos denominator certificate strike flow.

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
    Return run for the organs finite erdos denominator certificate strike flow.

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


def run_finite_erdos_denominator_certificate_strike_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Compute run finite erdos denominator certificate strike bundle from `input_path`,
    `out_dir`, and `command`.

    Inputs are `input_path`, `out_dir`, and `command`; notable helpers are `run`.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    Register CLI syntax for
    `microcosm_core.organs.finite_erdos_denominator_certificate_strike.build_parser`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(
        description="Run the finite Erdos denominator-order certificate strike organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-finite-erdos-denominator-certificate-strike-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the `microcosm_core.organs.finite_erdos_denominator_certificate_strike` command-line
    entry point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-finite-erdos-denominator-certificate-strike-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
