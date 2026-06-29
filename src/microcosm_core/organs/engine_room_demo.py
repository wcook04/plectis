"""
Accepted Engine Room composition organ.

This organ wraps the staged Engine Room capsules as one public runtime surface.
The capsules stay in ``microcosm_core.engine_room``; this file provides the
standard organ contract: fixture input, receipt writes, acceptance receipt,
runtime-shell runner, and CLI dispatch.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.engine_room_demo` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_NAME, SCHEMA_VERSION, CLAIM_CEILING, ANTI_CLAIM, AUTHORITY_CEILING, build_result, run, run_engine_room_demo_bundle, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.engine_room.demo, microcosm_core.receipts
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.demo import (
    EXPECTED_JEWEL_TARGETS,
    audit_controller_coverage,
    default_root,
)
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "engine_room_demo"
FIXTURE_ID = "first_wave.engine_room_demo"
VALIDATOR_ID = "validator.microcosm.organs.engine_room_demo"
RESULT_NAME = "engine_room_demo_result.json"
BOARD_NAME = "engine_room_demo_board.json"
VALIDATION_RECEIPT_NAME = "engine_room_demo_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = "engine_room_demo_fixture_acceptance.json"
SCHEMA_VERSION = "engine_room_demo_organ_v1"
CLAIM_CEILING = (
    "Validates the staged Engine Room composition demo over bounded public "
    "fixtures. It confirms 14 jewel targets, owned capsule surfaces, and the "
    "one-command capsule exercise chain. It is not production readiness, not "
    "private-root equivalence, not a frontier theorem-proving or security "
    "claim, and not release approval."
)
ANTI_CLAIM = (
    "The Engine Room demo is a public-safe composition of bounded symbolic "
    "prover, runtime, integrity, security, navigation, orchestration, and "
    "knowledge-routing capsules. It does not export private macro run state, "
    "credentials, provider/browser state, raw operator threads, third-party "
    "clones, or any release/publication authority."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "production_ready": False,
    "private_root_equivalence": False,
    "frontier_theorem_prover": False,
    "complete_security_proof": False,
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "source_mutation_authorized": False,
}


def _read_json(path: Path) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_read_json` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_cases` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = Path(input_path)
    if path.is_file():
        return [(path, _read_json(path))]
    rows = [(item, _read_json(item)) for item in sorted(path.glob("*.json"))]
    if not rows:
        raise FileNotFoundError(f"no JSON fixture cases under {path}")
    return rows


def _target_override_case(case: Mapping[str, Any], actual_targets: set[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_target_override_case` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    expected_targets = {
        str(value)
        for value in case.get("expected_jewel_targets", [])
        if str(value).strip()
    }
    missing_targets = sorted(expected_targets - actual_targets)
    return {
        "case_id": case.get("case_id", "target_override"),
        "case_type": case.get("case_type", "negative"),
        "status": "fail" if missing_targets else "pass",
        "observed_error_codes": (
            ["ENGINE_ROOM_EXPECTED_TARGET_MISSING"] if missing_targets else []
        ),
        "missing_jewel_targets": missing_targets,
    }


def _failed_capsule_rows(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_failed_capsule_rows` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    demo_receipt = receipt.get("demo_receipt")
    if not isinstance(demo_receipt, Mapping):
        return []
    rows = demo_receipt.get("rows")
    if not isinstance(rows, list):
        return []
    failed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("status") == "pass":
            continue
        failed.append(
            {
                "capsule_id": row.get("capsule_id"),
                "status": row.get("status"),
                "summary": row.get("summary"),
            }
        )
    return failed


def _evaluate_case(case: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate_case` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    case_type = str(case.get("case_type") or "positive")
    if case_type == "positive":
        receipt = audit_controller_coverage(
            root=root,
            run_exercises=bool(case.get("run_exercises", True)),
        )
        failed_capsules = _failed_capsule_rows(receipt)
        return {
            "case_id": case.get("case_id", "positive_controller_audit"),
            "case_type": case_type,
            "status": receipt.get("status"),
            "observed_error_codes": (
                ["ENGINE_ROOM_SUBCAPSULE_COMPOSITION_FAILED"] if failed_capsules else []
            ),
            "controller_completion_status": receipt.get("controller_completion_status"),
            "covered_jewel_count": receipt.get("covered_jewel_count"),
            "missing_surface_capsule_count": receipt.get("missing_surface_capsule_count"),
            "shared_integration_status": receipt.get("shared_integration_status"),
            "failed_subcapsule_count": len(failed_capsules),
            "failed_subcapsules": failed_capsules,
        }
    if case_type == "negative":
        actual_targets = set(
            audit_controller_coverage(root=root, run_exercises=False)[
                "covered_jewel_targets"
            ]
        )
        return _target_override_case(case, actual_targets)
    return {
        "case_id": case.get("case_id", "unknown_case"),
        "case_type": case_type,
        "status": "fail",
        "observed_error_codes": ["ENGINE_ROOM_UNKNOWN_CASE_TYPE"],
    }


def _fixture_ref(path: Path, *, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_fixture_ref` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved = path.resolve()
    for base in (public_root.resolve(), Path.cwd().resolve()):
        try:
            return resolved.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def build_result(input_path: str | Path, *, root: Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_result` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    microcosm_root = root or default_root()
    rows = [
        {
            "fixture_ref": _fixture_ref(path, public_root=microcosm_root),
            **_evaluate_case(case, root=microcosm_root),
        }
        for path, case in _fixture_cases(input_path)
    ]
    positive_rows = [row for row in rows if row["case_type"] == "positive"]
    negative_rows = [row for row in rows if row["case_type"] == "negative"]
    positive_pass = all(row["status"] == "pass" for row in positive_rows)
    negative_observed = all(row["status"] == "fail" for row in negative_rows)
    status = "pass" if positive_rows and positive_pass and negative_observed else "fail"
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
        "input_mode": "engine_room_demo_fixture_cases",
        "expected_jewel_targets": sorted(EXPECTED_JEWEL_TARGETS),
        "expected_jewel_count": len(EXPECTED_JEWEL_TARGETS),
        "case_count": len(rows),
        "positive_case_count": len(positive_rows),
        "negative_case_count": len(negative_rows),
        "passed_positive_case_count": sum(1 for row in positive_rows if row["status"] == "pass"),
        "observed_negative_case_count": sum(1 for row in negative_rows if row["status"] == "fail"),
        "cases": rows,
        "body_in_receipt": False,
    }


def _build_board(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "engine_room_demo_board_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "case_count": result.get("case_count"),
        "expected_jewel_count": result.get("expected_jewel_count"),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _build_validation_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_validation_receipt` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "engine_room_demo_validation_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "fixture_id": FIXTURE_ID,
        "receipt_paths": dict(receipt_paths),
        "body_in_receipt": False,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _build_acceptance_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_acceptance_receipt` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "engine_room_demo_acceptance_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "fixture_id": FIXTURE_ID,
        "real_substrate_disposition": "real_substrate_capsule",
        "generated_receipts": list(receipt_paths.values()),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def run(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    result = build_result(input_path)
    if command:
        result["command"] = command
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    public_root = default_root()
    receipt_paths = {
        "result": _fixture_ref(out / RESULT_NAME, public_root=public_root),
        "board": _fixture_ref(out / BOARD_NAME, public_root=public_root),
        "validation": _fixture_ref(out / VALIDATION_RECEIPT_NAME, public_root=public_root),
    }
    validation = _build_validation_receipt(result, receipt_paths)
    write_json_atomic(out / RESULT_NAME, result)
    write_json_atomic(out / BOARD_NAME, _build_board(result))
    write_json_atomic(out / VALIDATION_RECEIPT_NAME, validation)
    if acceptance_out is not None:
        acceptance = _build_acceptance_receipt(
            result,
            {
                **receipt_paths,
                "acceptance": _fixture_ref(Path(acceptance_out), public_root=public_root),
            },
        )
        write_json_atomic(Path(acceptance_out), acceptance)
    return result


def run_engine_room_demo_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_engine_room_demo_bundle` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `build_parser` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Run the accepted Engine Room demo organ.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-engine-room-demo-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.engine_room_demo` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-engine-room-demo-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
