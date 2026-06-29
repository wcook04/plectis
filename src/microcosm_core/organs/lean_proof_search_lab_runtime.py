"""
Lean proof-search lab runtime organ.

This organ surfaces the public ``lean_proof_search_lab`` engine-room capsule as a
first-class formal-math organ. The capsule body stays in
``microcosm_core.engine_room.lean_proof_search_lab``; this file adds the standard
organ contract: bounded fixture cases, planted negative cases, a ``result_card``
projection, body-free receipt writes, and CLI dispatch.

The mechanism it surfaces: a *symbolic Lean proof-search lab*. For a finite set
of public toy theorems it runs an and/or candidate-tactic search, checks each
candidate body with the installed Lean subprocess, refuses to forward any oracle
proof body (a forward-leakage firewall over ``FORBIDDEN_FORWARD_FIELDS``), runs a
problem-id ablation that fails any policy which only works because it memorised
the problem id, and runs a ``#print axioms`` cleanliness gate that rejects
``sorry``-tainted candidates. It self-falsifies: a forward oracle leak, an
axiom-tainted candidate, and a problem-id-memorising policy are each rejected by
recomputation.

This is a *gated external-tool witness*. Lean is an optional dependency, so the
organ has two honest states and never fakes a pass:

* **Unlocked** -- the ``lean`` binary is on ``PATH``: the organ runs the real
  Lean subprocess search and reports ``tool_present_and_verified`` (a genuine
  pass) or ``tool_present_but_failed`` (a real failure: a positive search did not
  close, or a planted negative was not rejected).
* **Locked** -- Lean is absent: the organ does not run, does not claim any proof
  was verified, and returns the terminal state ``locked`` with the unlock
  instructions. A locked organ is not a failure and is not a pass.

The runtime-spine entry point (``run_lean_proof_search_lab_runtime_bundle``)
operates the exported bundle as a declared standalone contract and never spawns
Lean, so the runtime spine stays fast and portable on machines without Lean.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.lean_proof_search_lab_runtime` as a documented Microcosm public source module.
- Mechanism: Keeps the executable proof-search source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, UNLOCK_INSTRUCTIONS, SPEC, lean_available, build_result, result_card, run, run_lean_proof_search_lab_runtime_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, the Lean subprocess side effects requested by the capsule, and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, provider calls, neural theorem proving, oracle-body forwarding, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Probes for the Lean binary; when present it delegates the proof search to the surfaced capsule and classifies positive (search closed clean) versus negative (oracle leak, axiom taint, or problem-id ablation rejected) cases; when absent it returns a body-free locked receipt.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.lean_proof_search_lab, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, and the optional Lean subprocess only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem reads, CLI argument reads, and the optional Lean subprocess are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.lean_proof_search_lab import evaluate_fixture_dir
from microcosm_core.receipts import utc_now, write_json_atomic

ORGAN_ID = "lean_proof_search_lab_runtime"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# Optional-dependency probe target. Lean is exercised only through the surfaced
# capsule's own subprocess calls; this organ probes the binary's presence and
# never discloses its absolute path in a receipt.
REQUIRED_TOOL = "lean"

# Terminal tool states. ``locked`` is distinct from both pass and fail: a locked
# organ ran nothing and claims nothing.
TOOL_PRESENT_AND_VERIFIED = "tool_present_and_verified"
TOOL_PRESENT_BUT_FAILED = "tool_present_but_failed"
TOOL_MISSING = "tool_missing"

EXECUTION_LIVE = "live_lean_subprocess_verified"
EXECUTION_LOCKED = "tool_missing_locked"
EXECUTION_STANDALONE = "standalone_exported_contract"

UNLOCK_INSTRUCTIONS = (
    "Install Lean 4 so the `lean` binary is on PATH, then re-run. The elan "
    "version manager places `lean` and `lake` on PATH and selects the toolchain "
    "named by a project's lean-toolchain file; see https://lean-lang.org/install/. "
    "Once `lean` resolves, this organ runs the real proof-search subprocess and "
    "reports tool_present_and_verified instead of locked."
)

# The planted negative cases the runner asserts on: each forged or memorising
# scenario MUST be rejected by recomputation with the named failure kind. The
# runner marks a case "negative" when its declared expectation is rejection
# (expected_status == "fail").
EXPECTED_NEGATIVE_CASES = {
    "oracle_field_negative": "oracle_firewall_violation",
    "nested_oracle_field_negative": "oracle_firewall_violation",
    "sorry_axiom_negative": "axiom_taint_detected",
    "memorized_policy_negative": "problem_id_ablation_failure",
}

CLAIM_CEILING = (
    "Runs a symbolic Lean proof-search lab over bounded public toy theorems with "
    "the installed Lean subprocess: an and/or candidate-tactic search, a forward "
    "oracle-leak firewall, a problem-id ablation, and a #print axioms cleanliness "
    "gate. It rejects forged or memorising scenarios by recomputation. Lean is an "
    "optional dependency: when the lean binary is absent the organ is locked and "
    "verifies nothing rather than faking a pass. It is not neural theorem "
    "proving, does not solve any open mathematical problem, does not forward "
    "oracle proof bodies, and does not authorize release or publication."
)

ANTI_CLAIM = (
    "The Lean proof-search lab runtime organ searches and Lean-checks bounded "
    "public toy theorems only. It is not neural theorem proving, does not solve "
    "open problems, does not forward an oracle proof body or oracle-needed "
    "premise ids, and does not export private macro state, credentials, provider "
    "state, or raw operator threads; it does not call providers and does not "
    "authorize release or publication. When Lean is installed, a candidate that "
    "leaks a forward oracle field, depends on sorry, or only works because it "
    "memorised the problem id cannot pass, because the capsule recomputes the "
    "search, the firewall, the axiom audit, and the problem-id ablation. When "
    "Lean is absent, the organ is locked and asserts no verification at all."
)

AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "neural_theorem_proving": False,
    "solves_open_problem": False,
    "oracle_body_forwarding": False,
    "external_tool_required": True,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Lean proof-search lab runtime",
    "fixture_id": FIXTURE_ID,
    "validator_id": VALIDATOR_ID,
    "result_name": RESULT_NAME,
    "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
    "required_tool": REQUIRED_TOOL,
    "anti_claim": ANTI_CLAIM,
    "authority_ceiling": AUTHORITY_CEILING,
}


def lean_available() -> bool:
    """
    [ACTION]
    - Teleology: Implements `lean_available` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: None; reads only the process PATH.
    - Guarantee: Returns True when the `lean` binary resolves on PATH, else False; never discloses the resolved absolute path.
    - Fails: Does not raise.
    - Reads: process environment PATH.
    - Writes: return values.
    """
    return shutil.which(REQUIRED_TOOL) is not None


def _locked_result(command: str | None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_locked_result` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: Called only when the Lean binary is absent.
    - Guarantee: Returns a body-free locked envelope that claims no verification and carries the unlock instructions.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
    """
    result = {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "status": "locked",
        "tool_state": TOOL_MISSING,
        "execution_witness_mode": EXECUTION_LOCKED,
        "lean_available": False,
        "required_tool": REQUIRED_TOOL,
        "created_at": utc_now(),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "input_mode": "lean_proof_search_lab_fixture_cases",
        "case_count": 0,
        "positive_case_count": 0,
        "negative_case_count": 0,
        "passed_positive_case_count": 0,
        "observed_negative_case_count": 0,
        "expected_negative_cases": dict(EXPECTED_NEGATIVE_CASES),
        "cases": [],
        "unlock_instructions": UNLOCK_INSTRUCTIONS,
        "verification_performed": False,
        "body_in_receipt": False,
    }
    if command:
        result["command"] = command
    return result


def _classify_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_classify_case` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: case is a capsule evaluate_case row with expected_status, observed_status, observed_failure_kind, and expectation_met.
    - Guarantee: Returns a distilled body-free row separating positive (search closed clean) from negative (rejected with the expected failure kind), with observed_ok recomputed from the capsule expectation.
    - Fails: Propagates only mapping access errors.
    - Reads: call arguments, module constants.
    - Writes: return values.
    """
    case_id = str(case.get("case_id") or "")
    expected_status = str(case.get("expected_status") or "pass")
    observed_status = str(case.get("observed_status") or "")
    observed_failure_kind = case.get("observed_failure_kind")
    expectation_met = bool(case.get("expectation_met"))
    case_type = "positive" if expected_status == "pass" else "negative"
    if case_type == "positive":
        observed_ok = expectation_met and observed_status == "pass"
    else:
        expected_failure_kind = EXPECTED_NEGATIVE_CASES.get(case_id)
        observed_ok = (
            expectation_met
            and observed_status == "fail"
            and (expected_failure_kind is None or observed_failure_kind == expected_failure_kind)
        )
    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_status": expected_status,
        "observed_status": observed_status,
        "observed_failure_kind": observed_failure_kind,
        "expectation_met": expectation_met,
        "observed_ok": observed_ok,
    }


def build_result(input_path: str | Path, command: str | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to a directory of capsule fixture cases.
    - Guarantee: When Lean is present, runs the real proof search and returns a pass/fail envelope (tool_present_and_verified / tool_present_but_failed); when Lean is absent, returns the locked envelope without verifying anything.
    - Fails: Propagates IO/JSON/subprocess errors raised by the surfaced capsule under live evaluation.
    - Reads: declared filesystem inputs, module constants, imported helpers, the optional Lean subprocess.
    - Writes: return values.
    """
    if not lean_available():
        return _locked_result(command)

    receipt = evaluate_fixture_dir(Path(input_path))
    rows = [_classify_case(case) for case in receipt.get("cases", [])]
    positive_rows = [row for row in rows if row["case_type"] == "positive"]
    negative_rows = [row for row in rows if row["case_type"] == "negative"]
    positive_pass = all(row["observed_ok"] for row in positive_rows)
    negative_pass = all(row["observed_ok"] for row in negative_rows)
    negative_ids = {row["case_id"] for row in negative_rows}
    expected_negatives_present = set(EXPECTED_NEGATIVE_CASES).issubset(negative_ids)
    verified = bool(
        positive_rows
        and negative_rows
        and positive_pass
        and negative_pass
        and expected_negatives_present
    )
    status = "pass" if verified else "fail"
    tool_state = TOOL_PRESENT_AND_VERIFIED if verified else TOOL_PRESENT_BUT_FAILED
    result = {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "status": status,
        "tool_state": tool_state,
        "execution_witness_mode": EXECUTION_LIVE,
        "lean_available": True,
        "required_tool": REQUIRED_TOOL,
        "created_at": utc_now(),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "input_mode": "lean_proof_search_lab_fixture_cases",
        "case_count": len(rows),
        "positive_case_count": len(positive_rows),
        "negative_case_count": len(negative_rows),
        "passed_positive_case_count": sum(1 for row in positive_rows if row["observed_ok"]),
        "observed_negative_case_count": sum(1 for row in negative_rows if row["observed_ok"]),
        "expected_negative_cases": dict(EXPECTED_NEGATIVE_CASES),
        "cases": rows,
        "verification_performed": True,
        "body_in_receipt": False,
    }
    if command:
        result["command"] = command
    return result


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: result is a build_result envelope.
    - Guarantee: Returns a body-free status card with the tool state, claim ceiling, and anti-claim.
    - Fails: Propagates mapping access errors only.
    - Reads: call arguments, module constants.
    - Writes: return values.
    """
    return {
        "schema_version": f"{ORGAN_ID}_board_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "tool_state": result.get("tool_state"),
        "lean_available": result.get("lean_available"),
        "case_count": result.get("case_count"),
        "positive_case_count": result.get("positive_case_count"),
        "negative_case_count": result.get("negative_case_count"),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _validation_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
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
        "tool_state": result.get("tool_state"),
        "lean_available": result.get("lean_available"),
        "fixture_id": FIXTURE_ID,
        "receipt_paths": dict(receipt_paths),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _acceptance_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
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
        "tool_state": result.get("tool_state"),
        "lean_available": result.get("lean_available"),
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
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `run` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases; out_dir is writable.
    - Guarantee: Computes the result (live Lean when present, locked when absent), writes body-free receipts, and returns the result envelope.
    - Fails: Propagates IO/JSON/subprocess errors raised by the body.
    - Reads: declared filesystem inputs, module constants, imported helpers, the optional Lean subprocess.
    - Writes: return values, declared filesystem outputs.
    """
    result = build_result(input_path, command=command)
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


def run_lean_proof_search_lab_runtime_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_lean_proof_search_lab_runtime_bundle` for `microcosm_core.organs.lean_proof_search_lab_runtime` as the runtime-spine entry point.
    - Preconditions: input_path names the exported bundle directory; out_dir is writable.
    - Guarantee: Validates the exported bundle as a declared standalone contract WITHOUT spawning Lean, so the runtime spine stays portable on machines without Lean; the returned receipt records that no live Lean verification was performed.
    - Fails: Raises FileNotFoundError when a declared required bundle file is missing.
    - Reads: declared filesystem inputs, module constants.
    - Writes: return values, declared filesystem outputs.
    """
    bundle = Path(input_path)
    required = ["bundle_manifest.json", "source_module_manifest.json", "docs/README.md"]
    missing = [name for name in required if not (bundle / name).is_file()]
    fixture_count = len(sorted(bundle.glob("*.json")))
    status = "pass" if not missing else "fail"
    result = {
        "schema_version": f"{ORGAN_ID}_bundle_contract_v1",
        "organ_id": ORGAN_ID,
        "status": status,
        "tool_state": "standalone_contract_not_executed",
        "execution_witness_mode": EXECUTION_STANDALONE,
        "lean_executed": False,
        "verification_performed": False,
        "input_mode": f"exported_{ORGAN_ID}_bundle",
        "declared_required_files_present": not missing,
        "missing_required_files": missing,
        "fixture_case_file_count": fixture_count,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "note": (
            "Declared standalone exported contract; this spine path does not spawn "
            "Lean. Live Lean verification runs via `run` against the live fixture "
            "directory on a machine where the lean binary is installed."
        ),
        "body_in_receipt": False,
    }
    if command:
        result["command"] = command
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out / RESULT_NAME, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `build_parser` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
    """
    parser = argparse.ArgumentParser(
        description="Run the Lean proof-search lab runtime organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-lean-proof-search-lab-runtime-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.lean_proof_search_lab_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass or locked, 1 on fail; locked is an honest non-failure exit.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} tool_state={result.get('tool_state')}")
        return 0 if result["status"] in {"pass", "locked"} else 1
    if args.command == "run-lean-proof-search-lab-runtime-bundle":
        result = run_lean_proof_search_lab_runtime_bundle(args.input, args.out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} ({result['execution_witness_mode']})")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
