"""
Public-safe egress self-compliance gate capsule.

This source-faithful public refactor carries the macro egress policy shape from
`system/lib/egress_compliance.py`: routine permission ceremony is a violation
unless the same text names a real blocker; self-error language is a violation
unless it binds to a durable capture; and command handoff language is a
violation unless the text also records that the command was actually run.

It is phrase-membership policy, not taint analysis, sandboxing, or prompt
injection defense.

[PURPOSE]
- Teleology: Exposes `microcosm_core.engine_room.egress_self_compliance_gate` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, ORGAN_ID, SOURCE_REFS, SOURCE_TO_TARGET_RELATION, CLAIM_CEILING, ANTI_CLAIMS, PERMISSION_GATE_PHRASES, LEGITIMATE_BLOCKER_PHRASES, SELF_ERROR_TRIPWIRE_PHRASES, DURABLE_BINDING_PHRASES, COMMAND_DISPLACEMENT_PHRASES, COMMAND_EXECUTION_RECEIPT_PHRASES, DetectorResult, detect_permission_gate_without_blocker, detect_self_error_without_capture, detect_command_displacement_to_operator, DETECTORS, evaluate_text, evaluate_case, evaluate_fixture_dir, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_egress_self_compliance_gate_v1"
ORGAN_ID = "engine_room_egress_self_compliance_gate"
SOURCE_REFS = (
    "system/lib/egress_compliance.py",
    ".claude/hooks/runtime_hook.py",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Phrase-membership egress policy over agent output text. It is not taint "
    "analysis, not prompt-injection defense, not a sandbox, and not an "
    "information-flow proof."
)
ANTI_CLAIMS = (
    "not_taint_analysis",
    "not_prompt_injection_defense",
    "not_sandboxing",
    "not_information_flow_control",
)

PERMISSION_GATE_PHRASES = (
    "authorize the next wave",
    "authorize next wave",
    "redirect or proceed",
    "want me to continue",
    "ready to commit",
    "should i proceed",
    "let me know if you want",
    "shall i continue",
    "permission to continue",
    "ok to proceed",
)

LEGITIMATE_BLOCKER_PHRASES = (
    "destructive",
    "irreversible",
    "secret",
    "credential",
    "publication boundary",
    "remote push",
    "concurrent-owner conflict",
    "concurrent owner conflict",
    "validation failure",
    "owner unclear",
    "blast-radius",
    "blast radius",
    "private disclosure",
    "explicit no-commit",
)

SELF_ERROR_TRIPWIRE_PHRASES = (
    "i was wrong",
    "my mistake",
    "i miscounted",
    "i fabricated",
    "i claimed incorrectly",
    "i should not have",
)

DURABLE_BINDING_PHRASES = (
    "cap_",
    "workitem",
    "work item",
    "task ledger",
    "quick-capture",
    "captured",
    "failure mode",
)

COMMAND_DISPLACEMENT_PHRASES = (
    "you can run",
    "run this command",
    "try running",
    "next command for you",
)

COMMAND_EXECUTION_RECEIPT_PHRASES = (
    "i ran",
    "ran:",
    "exit code",
    "passed",
    "failed",
    "command output",
)


@dataclass(frozen=True)
class DetectorResult:
    """
    [ROLE]
    - Teleology: Groups `DetectorResult` data or behavior for `microcosm_core.engine_room.egress_self_compliance_gate` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.engine_room.egress_self_compliance_gate`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    diagnostic_id: str
    violation: bool
    matched_tripwires: tuple[str, ...]
    matched_legitimizers: tuple[str, ...]
    severity: str
    one_line_rule: str


def _body(text: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_body` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(text or "").lower()


def _matches(text: str, phrases: Sequence[str]) -> tuple[str, ...]:
    """
    [ACTION]
    - Teleology: Implements `_matches` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return tuple(phrase for phrase in phrases if phrase in text)


def detect_permission_gate_without_blocker(text: Any) -> DetectorResult | None:
    """
    [ACTION]
    - Teleology: Implements `detect_permission_gate_without_blocker` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    body = _body(text)
    matched_gates = _matches(body, PERMISSION_GATE_PHRASES)
    if not matched_gates:
        return None
    matched_blockers = _matches(body, LEGITIMATE_BLOCKER_PHRASES)
    violation = not matched_blockers
    return DetectorResult(
        diagnostic_id="permission_gate_without_blocker",
        violation=violation,
        matched_tripwires=matched_gates,
        matched_legitimizers=matched_blockers,
        severity="operational_pressure" if violation else "informational",
        one_line_rule=(
            "Ask for permission only after naming a real blast-radius blocker; "
            "otherwise take the safe bounded action and report receipts."
        ),
    )


def detect_self_error_without_capture(text: Any) -> DetectorResult | None:
    """
    [ACTION]
    - Teleology: Implements `detect_self_error_without_capture` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    body = _body(text)
    matched_tripwires = _matches(body, SELF_ERROR_TRIPWIRE_PHRASES)
    if not matched_tripwires:
        return None
    matched_bindings = _matches(body, DURABLE_BINDING_PHRASES)
    violation = not matched_bindings
    return DetectorResult(
        diagnostic_id="self_error_without_capture",
        violation=violation,
        matched_tripwires=matched_tripwires,
        matched_legitimizers=matched_bindings,
        severity="operational_pressure" if violation else "informational",
        one_line_rule=(
            "Self-detected mistakes must bind to a Task Ledger capture before "
            "they appear in operator-facing prose."
        ),
    )


def detect_command_displacement_to_operator(text: Any) -> DetectorResult | None:
    """
    [ACTION]
    - Teleology: Implements `detect_command_displacement_to_operator` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    body = _body(text)
    matched_tripwires = _matches(body, COMMAND_DISPLACEMENT_PHRASES)
    if not matched_tripwires:
        return None
    matched_receipts = _matches(body, COMMAND_EXECUTION_RECEIPT_PHRASES)
    violation = not matched_receipts
    return DetectorResult(
        diagnostic_id="command_displacement_to_operator",
        violation=violation,
        matched_tripwires=matched_tripwires,
        matched_legitimizers=matched_receipts,
        severity="operational_pressure" if violation else "informational",
        one_line_rule=(
            "Do not hand a safe in-scope command to the operator; run it and "
            "report the receipt unless a real blocker exists."
        ),
    )


DETECTORS = (
    detect_permission_gate_without_blocker,
    detect_self_error_without_capture,
    detect_command_displacement_to_operator,
)


def evaluate_text(text: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_text` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = [row for detector in DETECTORS if (row := detector(text)) is not None]
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "status": "red" if any(row.violation for row in rows) else "green",
        "violation_count": sum(1 for row in rows if row.violation),
        "rows": [asdict(row) for row in rows],
    }


def evaluate_case(case: Mapping[str, Any], *, path: str = "") -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_case` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    expected_status = str(case.get("expected_status") or "").strip().lower()
    receipt = evaluate_text(case.get("text") or "")
    expectation_met = bool(expected_status) and receipt["status"] == expected_status
    return {
        "case_id": str(case.get("case_id") or Path(path).stem),
        "path": path,
        "expected_status": expected_status,
        "observed_status": receipt["status"],
        "expectation_met": expectation_met,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_fixture_dir` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    cases: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path} did not contain a JSON object")
        cases.append(evaluate_case(payload, path=str(path)))
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": sum(1 for case in cases if case["expectation_met"]),
        "status": "pass" if cases and all(case["expectation_met"] for case in cases) else "fail",
        "cases": cases,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.engine_room.egress_self_compliance_gate` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate one text string")
    evaluate.add_argument("--text", required=True)
    evaluate.add_argument("--json", action="store_true")

    matrix = subparsers.add_parser("evaluate-fixtures", help="Evaluate fixture cases")
    matrix.add_argument("--input", required=True)
    matrix.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "evaluate":
        payload = evaluate_text(args.text)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {payload['status']}")
        return 0 if payload["status"] == "green" else 1
    payload = evaluate_fixture_dir(Path(args.input))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{ORGAN_ID}: {payload['status']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
