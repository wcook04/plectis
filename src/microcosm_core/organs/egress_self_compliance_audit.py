"""
Egress self-compliance audit organ.

This organ surfaces the public ``egress_self_compliance_gate`` engine-room
capsule as a first-class agent-reliability organ. The capsule body stays in
``microcosm_core.engine_room.egress_self_compliance_gate``; this file adds the
standard organ contract: bounded fixture cases, planted negative (policy
violation) cases, a ``result_card`` projection, body-free receipt writes, and
CLI dispatch.

The mechanism it surfaces: a *phrase-membership egress self-compliance policy*
over a single agent-output text string. The capsule runs three detectors, each
of which fires only when a tripwire phrase is present and the corresponding
legitimiser phrase is absent: (1) permission-gate-without-blocker — permission
ceremony ("should I proceed?", "let me know if you want") with no named
blast-radius blocker ("destructive", "publication boundary", "remote push");
(2) self-error-without-capture — self-correction language ("my mistake", "I
miscounted") with no durable binding ("cap_", "task ledger", "captured");
(3) command-displacement-to-operator — handing a command to the operator ("you
can run", "try running") with no execution receipt ("I ran", "exit code",
"passed"). The gate returns ``green`` when no detector reports a violation and
``red`` when any does. The runner exercises the gate over positive texts (a
permission gate that names a real blocker, and a captured self-error) and
self-falsifies: a bare permission gate and a command displaced to the operator
without a receipt are both flagged ``red``, and the runner asserts the expected
violating diagnostic id fires by recomputation.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.egress_self_compliance_audit` as a documented Microcosm public source module.
- Mechanism: Keeps executable detection source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, SPEC, build_result, result_card, run, run_egress_self_compliance_audit_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, taint analysis, prompt-injection defense, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates the egress self-compliance detection to the surfaced capsule, and projection, serialization, and receipt behavior to file-local functions.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.egress_self_compliance_gate, microcosm_core.receipts
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
    [ACTION]
    - Teleology: Implements `_read_json` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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


def _violating_diagnostic_ids(receipt: Mapping[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_violating_diagnostic_ids` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
    - Preconditions: receipt is an evaluate_text() mapping carrying a rows list.
    - Guarantee: Returns the ordered diagnostic ids whose row reports violation True.
    - Fails: Does not raise on well-formed input.
    - Reads: call arguments.
    - Writes: return values.
    """
    rows = receipt.get("rows", [])
    return [
        str(row.get("diagnostic_id"))
        for row in rows
        if isinstance(row, Mapping) and bool(row.get("violation"))
    ]


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Run one bounded egress self-compliance exercise and report observed-versus-expected.

    Each exercise evaluates one agent-output text against the surfaced capsule: a
    positive case expects the gate to return green (no violation), while a
    negative case expects red with a specific violating diagnostic id firing.
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries a text plus case_id, case_type, and expected_ok.
    - Guarantee: Returns a row capturing observed_ok, the green/red verdict, and the firing violating diagnostic ids.
    - Fails: Propagates only mapping/parse errors raised by the capsule.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `run` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
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


def run_egress_self_compliance_audit_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_egress_self_compliance_audit_bundle` for `microcosm_core.organs.egress_self_compliance_audit` as the runtime-spine entry point.
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
    - Teleology: Implements `build_parser` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
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
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.egress_self_compliance_audit` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass, 1 on fail.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
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
