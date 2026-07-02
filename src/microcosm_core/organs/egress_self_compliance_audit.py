"""
Implements organs egress self compliance audit for the public Plectis package.

Callers enter through `build_result`, `result_card`, `run`,
`run_egress_self_compliance_audit_bundle`, `build_parser`, and `main`; constants such as
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

from microcosm_core.engine_room.egress_self_compliance_gate import evaluate_text
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "egress_self_compliance_audit"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a policy-violating text MUST
# be flagged red by the gate, and the expected diagnostic id must be among the
# firing violations. The runner marks a case "negative" when its declared
# expectation is rejection (expected_ok False), and recomputes the violating
# diagnostic ids from the live capsule rather than trusting the fixture.
EXPECTED_NEGATIVE_CASES = {
    "permission_gate_without_blocker": ("permission_gate_without_blocker",),
    "command_displacement_no_receipt": ("command_displacement_to_operator",),
}

CLAIM_CEILING = (
    "Audits a single agent-output text string against a phrase-membership egress "
    "self-compliance policy over bounded public fixtures: it fires a violation "
    "only when a tripwire phrase is present and the matching legitimiser phrase "
    "is absent across three detectors (permission-gate-without-blocker, "
    "self-error-without-capture, command-displacement-to-operator). It rejects "
    "policy-violating text by recomputation. It is phrase membership only: it "
    "does not perform taint analysis, prompt-injection defense, sandboxing, or "
    "information-flow proof, and it does not authorize release or publication."
)
ANTI_CLAIM = (
    "The egress self-compliance audit organ checks agent-output text over public "
    "fixture inputs only. It is a substring/phrase-membership policy, not a taint "
    "analyzer, not a prompt-injection defense, not a sandbox, and not an "
    "information-flow proof. It does not understand semantics, paraphrase, or "
    "adversarial evasion; a violation worded outside the known phrase tables is "
    "not detected, and benign text that happens to contain a tripwire phrase can "
    "be flagged. It does not export private state, credentials, or raw operator "
    "threads; it does not call providers or external solvers, and it does not "
    "authorize release or publication. A planted policy-violating text cannot "
    "pass because the gate recomputes the detector rows and flags any text whose "
    "tripwire fires without its legitimiser."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "taint_analysis": False,
    "prompt_injection_defense": False,
    "sandboxing": False,
    "information_flow_control": False,
    "semantic_understanding": False,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Egress self-compliance audit",
    "fixture_id": FIXTURE_ID,
    "validator_id": VALIDATOR_ID,
    "result_name": RESULT_NAME,
    "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
    "anti_claim": ANTI_CLAIM,
    "authority_ceiling": AUTHORITY_CEILING,
}


def _read_json(path: Path) -> Mapping[str, Any]:
    """
    Read read JSON for `microcosm_core.organs.egress_self_compliance_audit`.

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
    `microcosm_core.organs.egress_self_compliance_audit`.

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


def _violating_diagnostic_ids(receipt: Mapping[str, Any]) -> list[str]:
    """
    Compute violating diagnostic IDs from `receipt`.

    Inputs are `receipt`; notable helpers are `get`.
    """
    rows = receipt.get("rows", [])
    return [
        str(row.get("diagnostic_id"))
        for row in rows
        if isinstance(row, Mapping) and bool(row.get("violation"))
    ]


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.egress_self_compliance_audit._evaluate_case` into the
    payload shape expected by organs egress self compliance audit.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))
    text = str(case.get("text") or "")

    receipt = evaluate_text(text)
    observed_status = str(receipt.get("status") or "")
    # The gate reports "green" when no detector reports a violation; a positive
    # (compliant) text is "ok" when green, a negative (violating) text is "ok"
    # for the runner when it is correctly flagged red.
    observed_clean = observed_status == "green"
    violating_ids = _violating_diagnostic_ids(receipt)
    expectation_met = observed_clean == expected_ok

    if case_type == "negative":
        expected_ids = EXPECTED_NEGATIVE_CASES.get(case_id, ())
        ids_present = all(diag in violating_ids for diag in expected_ids)
        observed_ok = (not observed_clean) and expectation_met and ids_present
    else:
        observed_ok = observed_clean and expectation_met

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "observed_status": observed_status,
        "observed_clean": observed_clean,
        "expectation_met": expectation_met,
        "observed_ok": observed_ok,
        "violation_count": int(receipt.get("violation_count") or 0),
        "violating_diagnostic_ids": violating_ids,
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.egress_self_compliance_audit.build_result` into the
    payload shape expected by organs egress self compliance audit.

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
        "input_mode": "egress_self_compliance_fixture_cases",
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
    Serialize `microcosm_core.organs.egress_self_compliance_audit.result_card` into the
    payload shape expected by organs egress self compliance audit.

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
    Serialize `microcosm_core.organs.egress_self_compliance_audit._validation_receipt` into
    the payload shape expected by organs egress self compliance audit.

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
    Serialize `microcosm_core.organs.egress_self_compliance_audit._acceptance_receipt` into
    the payload shape expected by organs egress self compliance audit.

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
    Return receipt ref for the organs egress self compliance audit flow.

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
    Return run for `microcosm_core.organs.egress_self_compliance_audit`.

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


def run_egress_self_compliance_audit_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Derive run egress self compliance audit bundle without touching module import state.

    Inputs are `input_path`, `out_dir`, and `command`; notable helpers are `run`.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    Register CLI syntax for
    `microcosm_core.organs.egress_self_compliance_audit.build_parser`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(
        description="Run the egress self-compliance audit organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-egress-self-compliance-audit-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the `microcosm_core.organs.egress_self_compliance_audit` command-line entry point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-egress-self-compliance-audit-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
