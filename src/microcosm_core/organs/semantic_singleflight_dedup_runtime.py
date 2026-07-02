"""
Implements organs semantic singleflight dedup runtime for the public Plectis package.

Callers enter through `build_result`, `result_card`, `run`,
`run_semantic_singleflight_dedup_bundle`, `build_parser`, and `main`; constants such as
`ORGAN_ID`, `FIXTURE_ID`, `VALIDATOR_ID`, `SCHEMA_VERSION`, and 9 more pin local fixture
names; dependencies include `argparse`, `json`, `tempfile`, `pathlib`, and 2 more. It builds
public fixture, result, card, or verdict structures while keeping private substrate bodies
out of the payload.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.command_run_singleflight import (
    build_command_key,
    run_command_singleflight,
)
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "semantic_singleflight_dedup_runtime"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative case the runner asserts on: a scoped file mutation MUST
# flip the content key, and a missing command MUST be rejected. The runner marks
# a case "negative" when its declared expectation is that a guard fires.
EXPECTED_NEGATIVE_CASES = {
    "scope_mutation_changes_key": ("SINGLEFLIGHT_STALE_STATE_CANNOT_DEDUP",),
    "missing_command_rejected": ("SINGLEFLIGHT_EMPTY_ARGV_REJECTED",),
}

CLAIM_CEILING = (
    "Keys and dedups command runs by a repo-state fingerprint -- argv, resolved "
    "cwd, git HEAD, a scoped dirty-tree fingerprint, and an env fingerprint -- "
    "over bounded public fixture commands. It does not guarantee global mutual "
    "exclusion, does not replace a lock service, does not prove cross-host "
    "correctness, and is not a job scheduler, a daemon, or release approval."
)
ANTI_CLAIM = (
    "The semantic singleflight dedup runtime computes content keys and collapses "
    "duplicate command runs over public fixtures only. It does not export private "
    "macro run state, credentials, provider state, or raw operator threads; it "
    "does not authorize release or publication; and a stale repo state cannot "
    "answer for a different run because the key folds repo state in."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "global_mutual_exclusion": False,
    "distributed_lock_service": False,
    "cross_host_correctness_proof": False,
    "job_scheduler": False,
    "production_ready": False,
    "private_root_equivalence": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Semantic singleflight dedup runtime",
    "fixture_id": FIXTURE_ID,
    "validator_id": VALIDATOR_ID,
    "result_name": RESULT_NAME,
    "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
    "anti_claim": ANTI_CLAIM,
    "authority_ceiling": AUTHORITY_CEILING,
}


def _read_json(path: Path) -> Mapping[str, Any]:
    """
    Read read JSON for `microcosm_core.organs.semantic_singleflight_dedup_runtime`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    Return fixture cases for `microcosm_core.organs.semantic_singleflight_dedup_runtime`.

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


def _simple_command(message: str) -> list[str]:
    """
    Compute simple command from `message`.

    Inputs are `message`.
    """
    import sys

    return [sys.executable, "-c", f"print({message!r})"]


def _counter_command(counter_path: Path) -> list[str]:
    """
    Return counter command for the organs semantic singleflight dedup runtime flow.

    Inputs are `counter_path`.
    """
    import sys

    code = (
        "from pathlib import Path\n"
        "import fcntl\n"
        f"path = Path({str(counter_path)!r})\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "with path.open('a+', encoding='utf-8') as fh:\n"
        "    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)\n"
        "    fh.seek(0)\n"
        "    value = int((fh.read().strip() or '0')) + 1\n"
        "    fh.seek(0)\n"
        "    fh.truncate()\n"
        "    fh.write(str(value))\n"
        "    fh.flush()\n"
        "print(f'counter={value}')\n"
    )
    return [sys.executable, "-c", code]


def _evaluate_case(case: Mapping[str, Any], *, scratch: Path) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.semantic_singleflight_dedup_runtime._evaluate_case`
    into the payload shape expected by organs semantic singleflight dedup runtime.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    exercise = str(case.get("exercise") or "")
    case_id = str(case.get("case_id") or exercise)
    case_type = str(case.get("case_type") or "positive")
    work = scratch / case_id
    state = work / "state"
    cwd = work / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)

    if exercise == "single_leader":
        receipt = run_command_singleflight(
            _simple_command("singleflight fixture work"),
            state_root=state,
            cwd=cwd,
            resource_class="fixture",
        )
        observed_ok = (
            receipt.role == "leader"
            and receipt.exit_code == 0
            and "fixture work" in receipt.stdout
        )
        return {
            "case_id": case_id,
            "case_type": case_type,
            "observed_ok": observed_ok,
            "observed_role": receipt.role,
            "observed_error_codes": [],
        }

    if exercise == "completed_reuse":
        counter = work / "reuse_counter.txt"
        command = _counter_command(counter)
        first = run_command_singleflight(command, state_root=state, cwd=cwd)
        second = run_command_singleflight(
            command, state_root=state, cwd=cwd, reuse_completed=True
        )
        counter_value = counter.read_text(encoding="utf-8").strip()
        observed_ok = (
            first.role == "leader"
            and second.role == "reused"
            and first.run_id == second.run_id
            and counter_value == "1"
        )
        return {
            "case_id": case_id,
            "case_type": case_type,
            "observed_ok": observed_ok,
            "observed_role": second.role,
            "counter_value": counter_value,
            "observed_error_codes": [],
        }

    if exercise == "scope_mutation_changes_key":
        scoped = cwd / "scoped.txt"
        scoped.write_text("before\n", encoding="utf-8")
        before = build_command_key(
            argv=_simple_command("scope"),
            cwd=cwd,
            resource_class="fixture",
            scope_paths=["scoped.txt"],
        )
        scoped.write_text("after\n", encoding="utf-8")
        after = build_command_key(
            argv=_simple_command("scope"),
            cwd=cwd,
            resource_class="fixture",
            scope_paths=["scoped.txt"],
        )
        key_changed = before["dirty_fingerprint"] != after["dirty_fingerprint"]
        # Negative case: the guard fires (stale state cannot dedup) when the key flips.
        return {
            "case_id": case_id,
            "case_type": case_type,
            "observed_ok": key_changed,
            "key_changed": key_changed,
            "observed_error_codes": (
                ["SINGLEFLIGHT_STALE_STATE_CANNOT_DEDUP"] if key_changed else []
            ),
        }

    if exercise == "missing_command_rejected":
        rejected = False
        error_text = ""
        try:
            run_command_singleflight([], state_root=state, cwd=cwd)
        except ValueError as exc:
            rejected = True
            error_text = str(exc)
        return {
            "case_id": case_id,
            "case_type": case_type,
            "observed_ok": rejected,
            "error": error_text,
            "observed_error_codes": (
                ["SINGLEFLIGHT_EMPTY_ARGV_REJECTED"] if rejected else []
            ),
        }

    return {
        "case_id": case_id,
        "case_type": case_type,
        "observed_ok": False,
        "observed_error_codes": ["SINGLEFLIGHT_UNKNOWN_EXERCISE"],
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.semantic_singleflight_dedup_runtime.build_result` into
    the payload shape expected by organs semantic singleflight dedup runtime.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    cases = _fixture_cases(input_path)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_") as tmp:
        scratch = Path(tmp)
        for _path, case in cases:
            rows.append(_evaluate_case(case, scratch=scratch))

    positive_rows = [row for row in rows if row["case_type"] == "positive"]
    negative_rows = [row for row in rows if row["case_type"] == "negative"]
    positive_pass = all(row["observed_ok"] for row in positive_rows)
    negative_observed = all(row["observed_ok"] for row in negative_rows)
    # Every declared negative case id must be present and observed.
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
        "input_mode": "semantic_singleflight_dedup_fixture_cases",
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
    Serialize `microcosm_core.organs.semantic_singleflight_dedup_runtime.result_card` into
    the payload shape expected by organs semantic singleflight dedup runtime.

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
    `microcosm_core.organs.semantic_singleflight_dedup_runtime._validation_receipt` into the
    payload shape expected by organs semantic singleflight dedup runtime.

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
    `microcosm_core.organs.semantic_singleflight_dedup_runtime._acceptance_receipt` into the
    payload shape expected by organs semantic singleflight dedup runtime.

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
    Return receipt ref for `microcosm_core.organs.semantic_singleflight_dedup_runtime`.

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
    Return run for `microcosm_core.organs.semantic_singleflight_dedup_runtime`.

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


def run_semantic_singleflight_dedup_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Return run semantic singleflight dedup bundle for the organs semantic singleflight dedup
    runtime flow.

    Inputs are `input_path`, `out_dir`, and `command`; notable helpers are `run`.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    Register CLI syntax for
    `microcosm_core.organs.semantic_singleflight_dedup_runtime.build_parser`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(description="Run the semantic singleflight dedup runtime organ.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-semantic-singleflight-dedup-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the `microcosm_core.organs.semantic_singleflight_dedup_runtime` command-line entry
    point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-semantic-singleflight-dedup-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
