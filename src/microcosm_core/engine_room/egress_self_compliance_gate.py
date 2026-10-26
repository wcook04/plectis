"""
Implements engine room egress self compliance gate for the public Plectis package.

Callers enter through `DetectorResult`, `detect_permission_gate_without_blocker`,
`detect_self_error_without_capture`, `detect_command_displacement_to_operator`,
`evaluate_text`, `evaluate_case`, and 2 more; constants such as `SCHEMA_VERSION`,
`ORGAN_ID`, `SOURCE_REFS`, `SOURCE_TO_TARGET_RELATION`, and 9 more pin local fixture names;
dependencies include `argparse`, `json`, `dataclasses`, `pathlib`, and 1 more. The
implementation is source-owned engine-room code, so receipts and tests should name these
callables directly.
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
    Record object for Detector Result.

    It keeps `diagnostic_id`, `violation`, `matched_tripwires`, `matched_legitimizers`,
    `severity`, and `one_line_rule` together for the engine room egress self compliance gate
    flow.
    """
    diagnostic_id: str
    violation: bool
    matched_tripwires: tuple[str, ...]
    matched_legitimizers: tuple[str, ...]
    severity: str
    one_line_rule: str


def _body(text: Any) -> str:
    """
    Derive body without touching module import state.

    Inputs are `text`; notable helpers are `lower`.
    """
    return str(text or "").lower()


def _matches(text: str, phrases: Sequence[str]) -> tuple[str, ...]:
    """Return literal phrase matches using the verified edge-aware scanner."""
    from plectis.components.egress_policy import evaluate

    result = evaluate({"text": text, "groups": [list(phrases)], "policy": False})
    return tuple(result["matches"][0])


# Each pair keeps the original detector order, phrases, and public descriptions.
_POLICY_GROUPS = (
    (PERMISSION_GATE_PHRASES, LEGITIMATE_BLOCKER_PHRASES,
     "permission_gate_without_blocker",
     "Ask for permission only after naming a real blast-radius blocker; "
     "otherwise take the safe bounded action and report receipts."),
    (SELF_ERROR_TRIPWIRE_PHRASES, DURABLE_BINDING_PHRASES,
     "self_error_without_capture",
     "Self-detected mistakes must bind to a Task Ledger capture before "
     "they appear in operator-facing prose."),
    (COMMAND_DISPLACEMENT_PHRASES, COMMAND_EXECUTION_RECEIPT_PHRASES,
     "command_displacement_to_operator",
     "Do not hand a safe in-scope command to the operator; run it and "
     "report the receipt unless a real blocker exists."),
)


def _verified_policy(text: Any, indices: Sequence[int]) -> tuple[list[DetectorResult], bool]:
    from plectis.components.egress_policy import evaluate

    # Python str/lower normalization is explicitly outside the verified core.
    body = _body(text)
    entries = [_POLICY_GROUPS[index] for index in indices]
    groups = [list(group) for trigger, legitimizer, _, _ in entries
              for group in (trigger, legitimizer)]
    result = evaluate({"text": body, "groups": groups, "policy": True})
    rows = []
    for index, (_, _, diagnostic, rule) in enumerate(entries):
        trigger, legitimizer = result["matches"][2 * index:2 * index + 2]
        violation = result["violations"][index]
        if trigger:
            rows.append(DetectorResult(
                diagnostic_id=diagnostic,
                violation=violation,
                matched_tripwires=tuple(trigger),
                matched_legitimizers=tuple(legitimizer),
                severity="operational_pressure" if violation else "informational",
                one_line_rule=rule,
            ))
    return rows, result["red"]


def detect_permission_gate_without_blocker(text: Any) -> DetectorResult | None:
    rows, _ = _verified_policy(text, (0,))
    return rows[0] if rows else None


def detect_self_error_without_capture(text: Any) -> DetectorResult | None:
    rows, _ = _verified_policy(text, (1,))
    return rows[0] if rows else None


def detect_command_displacement_to_operator(text: Any) -> DetectorResult | None:
    rows, _ = _verified_policy(text, (2,))
    return rows[0] if rows else None


DETECTORS = (
    detect_permission_gate_without_blocker,
    detect_self_error_without_capture,
    detect_command_displacement_to_operator,
)


def evaluate_text(text: Any) -> dict[str, Any]:
    """Evaluate all three rules in one verified-worker request."""
    rows, red = _verified_policy(text, (0, 1, 2))
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "status": "red" if red else "green",
        "violation_count": sum(1 for row in rows if row.violation),
        "rows": [asdict(row) for row in rows],
    }


def evaluate_case(case: Mapping[str, Any], *, path: str = "") -> dict[str, Any]:
    """
    Serialize `microcosm_core.engine_room.egress_self_compliance_gate.evaluate_case` into
    the payload shape expected by engine room egress self compliance gate.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
    Serialize `microcosm_core.engine_room.egress_self_compliance_gate.evaluate_fixture_dir`
    into the payload shape expected by engine room egress self compliance gate.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
    Run `microcosm_core.engine_room.egress_self_compliance_gate` as a command-line entry
    point.

    The command parses argv, calls this module's builders or validators, and returns the
    status code used by the process wrapper.
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
