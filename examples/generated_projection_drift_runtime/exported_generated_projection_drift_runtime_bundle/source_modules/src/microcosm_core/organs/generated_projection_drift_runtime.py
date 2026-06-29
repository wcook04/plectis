"""
Generated projection drift runtime organ.

This organ surfaces the public ``generated_projection_drift_gate`` engine-room
capsule as a first-class owner-routed drift-gate organ. The capsule body stays in
``microcosm_core.engine_room.generated_projection_drift_gate``; this file adds the
standard organ contract: bounded fixture cases, planted negative (rejected-owner)
cases, a ``result_card`` projection, body-free receipt writes, and CLI dispatch.

The mechanism it surfaces: an *owner-routed generated projection drift gate*. A
generated artifact (a builder output that must be reproducible from its source
authority) is modelled as an owner row carrying its declared artifact patterns,
source authorities, and a no-write check command. For each owner the gate
fingerprints the source and artifact files (SHA-256 per file, then a stable
SHA-256 over the file table), consults a prior-clean-receipt source-hash cache to
skip an unchanged owner's check, and otherwise runs the owner's declared no-write
check command. An owner is ``clean`` only when its check returns zero, its
required artifacts are present, and any required fact-authority lineage validates;
otherwise it is ``drift``. The runner exercises the gate over positive owners (a
passing no-write check and a prior-clean source-hash cache hit) and self-falsifies:
an owner whose generated artifact carries a planted byte and an owner whose
declared artifact never landed are both reported as drift by recomputation, and
the runner asserts the expected drift-reason marker fires.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.generated_projection_drift_runtime` as a documented Microcosm public source module.
- Mechanism: Keeps executable drift-gate source in the engine-room capsule as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, SCHEMA_VERSION, EXPECTED_NEGATIVE_CASES, AUTHORITY_CEILING, CLAIM_CEILING, ANTI_CLAIM, SPEC, build_result, result_card, run, run_generated_projection_drift_runtime_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, provider calls, file repair, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates the generated projection drift check to the surfaced capsule, and projection, serialization, and receipt behavior to file-local functions.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.generated_projection_drift_gate, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, and package data only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem reads, scratch-tree writes, and CLI argument reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.generated_projection_drift_gate import (
    evaluate_case as capsule_evaluate_case,
)
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "generated_projection_drift_runtime"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a drifted owner MUST be
# reported as drift, and the expected drift-reason marker must be among the
# owner's recomputed status_reasons. The runner marks a case "negative" when its
# declared expectation is rejection (expected_ok false / expected_status drift).
EXPECTED_NEGATIVE_CASES = {
    "planted_byte_drift": ("check_command_failed",),
    "missing_artifact_drift": ("artifact_missing",),
}

CLAIM_CEILING = (
    "Exercises an owner-routed generated projection drift gate over bounded "
    "public fixtures: per-file SHA-256 fingerprinting of source authorities and "
    "artifacts, a prior-clean-receipt source-hash skip cache, required-artifact "
    "presence, and each owner's declared no-write check command return code. It "
    "reports a drifted owner by recomputation. It does not prove that every macro "
    "owner uses true content-diff semantics, does not repair files, does not "
    "validate the full macro registry, and does not authorize public release."
)
ANTI_CLAIM = (
    "The generated projection drift runtime organ checks owner rows over public "
    "fixture inputs only. It is not a repair tool, does not regenerate artifacts, "
    "does not prove semantic content-diff equivalence for every macro builder, "
    "does not validate the entire generated-projection registry, and does not "
    "export private macro state, credentials, source bodies, or raw operator "
    "threads; it does not authorize release or publication. A drifted owner "
    "cannot pass because the gate recomputes the source and artifact fingerprints "
    "and runs the owner's no-write check, rejecting any owner whose check fails or "
    "whose required artifact is missing."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "repairs_files": False,
    "regenerates_artifacts": False,
    "semantic_content_diff_proof": False,
    "full_registry_validation": False,
    "oracle_or_prover": False,
    "provider_call": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Generated projection drift runtime",
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
    - Teleology: Implements `_read_json` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
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


def _owner_status_reasons(receipt: Mapping[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_owner_status_reasons` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: receipt is a check_projection_drift envelope with an owners list.
    - Guarantee: Returns the flattened, ordered drift-reason markers across every owner row.
    - Fails: Does not raise on well-formed input.
    - Reads: call arguments.
    - Writes: return values.
    """
    reasons: list[str] = []
    for owner in receipt.get("owners", []):
        if isinstance(owner, Mapping):
            for reason in owner.get("status_reasons", []):
                reasons.append(str(reason))
    return reasons


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Run one bounded drift-gate exercise and report observed-versus-expected.

    Each exercise materialises the case's declared file tree into a scratch repo,
    then calls the surfaced capsule to fingerprint the owner, consult the
    source-hash cache, and run the owner's no-write check command. A positive case
    expects every owner to validate cleanly, while a negative case expects an owner
    to be reported as drift with a specific drift-reason marker firing.
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: case carries owner rows, a file tree, and case_id, case_type, expected_ok plus an optional source_hash_cache / changed_paths / owner_ids.
    - Guarantee: Returns a row capturing observed_ok, the observed gate status, and the firing drift-reason markers.
    - Fails: Propagates only mapping/parse/filesystem errors raised by the capsule.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, scratch filesystem outputs scoped to a temporary directory.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))

    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_case_") as tmp:
        outcome = capsule_evaluate_case(case, scratch=Path(tmp), path=case_id)

    receipt = outcome.get("receipt", {})
    observed_status = str(outcome.get("observed_status") or "")
    observed_clean = observed_status == "clean"
    expectation_met = bool(outcome.get("expectation_met"))
    drift_reasons = _owner_status_reasons(receipt)

    if case_type == "negative":
        expected_markers = EXPECTED_NEGATIVE_CASES.get(case_id, ())
        markers_present = all(marker in drift_reasons for marker in expected_markers)
        observed_ok = (not observed_clean) and expectation_met and markers_present
    else:
        observed_ok = observed_clean and expectation_met

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "observed_status": observed_status,
        "expectation_met": expectation_met,
        "observed_ok": observed_ok,
        "observed_owner_count": outcome.get("observed_owner_count"),
        "drift_reasons": drift_reasons,
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases via _fixture_cases.
    - Guarantee: Returns the aggregated result envelope with a pass/fail status over positive and negative cases.
    - Fails: Propagates IO/JSON/filesystem errors raised by case loading or the capsule.
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
        "input_mode": "generated_projection_drift_gate_fixture_cases",
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
    - Teleology: Implements `result_card` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_validation_receipt` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_acceptance_receipt` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `run` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: input_path resolves to fixture cases; out_dir is writable.
    - Guarantee: Computes the result, writes body-free receipts, and returns the result envelope.
    - Fails: Propagates IO/JSON/filesystem errors raised by the body.
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


def run_generated_projection_drift_runtime_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_generated_projection_drift_runtime_bundle` for `microcosm_core.organs.generated_projection_drift_runtime` as the runtime-spine entry point.
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
    - Teleology: Implements `build_parser` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: none.
    - Guarantee: Returns a configured ArgumentParser; performs no IO.
    - Fails: Does not raise.
    - Reads: module constants.
    - Writes: return values.
    """
    parser = argparse.ArgumentParser(
        description="Run the generated projection drift runtime organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-generated-projection-drift-runtime-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.generated_projection_drift_runtime` while keeping the callable contract visible to source-module readers.
    - Preconditions: argv is a CLI argument vector or None.
    - Guarantee: Runs the organ and returns 0 on pass, 1 on fail.
    - Fails: Propagates argument-parsing and run errors.
    - Reads: call arguments.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-generated-projection-drift-runtime-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
