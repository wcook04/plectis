"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.cold_clone_probe` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: REQUIRED_INPUTS, PATTERN_RECEIPTS, SUPPORTED_SUITES, DEFAULT_EMIT_REF, run_probe, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs.pattern_binding_contract, microcosm_core.receipts, microcosm_core.schemas, microcosm_core.validators.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import json
import shutil
import shlex
from pathlib import Path
from typing import Any

from microcosm_core.organs.pattern_binding_contract import validate as validate_pattern_binding
from microcosm_core.receipts import base_receipt, write_receipt
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators.secret_exclusion_scan import validate_scan as validate_secret_exclusion_scan


REQUIRED_INPUTS = [
    "fixtures/first_wave/pattern_binding_contract/input/patterns.jsonl",
    "fixtures/first_wave/pattern_binding_contract/input/source_capsules.json",
    "fixtures/first_wave/pattern_binding_contract/input/private_state_forbidden_terms.json",
    "fixtures/first_wave/pattern_binding_contract/input/authority_chain_handles.json",
]

PATTERN_RECEIPTS = [
    "receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json",
    "receipts/first_wave/pattern_binding_contract/source_capsules.json",
    "receipts/first_wave/pattern_binding_contract/omission_receipt.json",
    "receipts/first_wave/pattern_binding_contract/reference_capsule_resolver_receipt.json",
    "receipts/first_wave/pattern_binding_contract/authority_chain_handle_resolver_receipt.json",
]

SUPPORTED_SUITES = ("first-wave",)
DEFAULT_EMIT_REF = ".microcosm/cold_clone_probe.json"


def _path_exists(path: Path) -> bool:
    """
    [ACTION]
    OSError-tolerant existence probe for a filesystem path.

    - Teleology: let receipt-mirroring loops test for a path without aborting on permission/IO errors on a fresh clone.
    - Guarantee: returns True iff `path.exists()` succeeds and is truthy; returns False on any OSError.
    - Fails: never raises; OSError is swallowed and reported as False.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.exists()
    except OSError:
        return False


def _path_is_file(path: Path) -> bool:
    """
    [ACTION]
    OSError-tolerant regular-file probe for a filesystem path.

    - Teleology: gate fixture/receipt presence checks on a fresh clone without crashing on IO errors.
    - Guarantee: returns True iff `path.is_file()` succeeds and is truthy; returns False on any OSError.
    - Fails: never raises; OSError is swallowed and reported as False.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.is_file()
    except OSError:
        return False


def _mirror_missing_pattern_receipts(root_path: Path, source_dir: Path) -> None:
    """
    [ACTION]
    Copy freshly-generated pattern-binding receipts into their canonical clone-root slots.

    - Teleology: after the pattern-binding validator runs into a scratch dir, materialize its receipts at the stable PATTERN_RECEIPTS paths the probe expects.
    - Guarantee: for each canonical receipt ref that is absent under `root_path` but present in `source_dir`, copies the file into place (creating parents); the validation-result receipt is rewritten with `receipt_paths` set to PATTERN_RECEIPTS.
    - Fails: never returns a value; existing destinations and source files absent from `source_dir` are skipped. Filesystem/IO or JSON-decode errors (read_json_strict, copyfile, write_text) propagate to the caller.
    - Reads: source receipt files under `source_dir`; the mirrored validation-result JSON (via read_json_strict).
    - Writes: missing receipt files under `root_path` at PATTERN_RECEIPTS; rewrites pattern_binding_validation_result.json with the canonical receipt_paths list.
    - When-needed: when reconciling why a probe reports MISSING_PATTERN_BINDING_RECEIPT despite a passing validator run.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    for receipt_ref in PATTERN_RECEIPTS:
        destination = root_path / receipt_ref
        if _path_exists(destination):
            continue
        source = source_dir / Path(receipt_ref).name
        if not _path_is_file(source):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if destination.name == "pattern_binding_validation_result.json":
            payload = read_json_strict(destination)
            if isinstance(payload, dict):
                payload["receipt_paths"] = PATTERN_RECEIPTS
                destination.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )


def _bootstrap_command(suite: str, emit_ref: str) -> str:
    """
    [ACTION]
    Render the shell-safe bootstrap invocation recorded in the probe receipt.

    - Teleology: give the receipt a reproducible, copy-pasteable command that reproduces this probe run.
    - Guarantee: returns the `./bootstrap.sh --suite <suite> --emit <emit_ref>` string with both arguments shell-quoted via shlex.quote.
    - Fails: never raises; pure string formatting over its inputs.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return f"./bootstrap.sh --suite {shlex.quote(suite)} --emit {shlex.quote(emit_ref)}"


def run_probe(
    root: str | Path,
    suite: str = "first-wave",
    emit_ref: str | Path = DEFAULT_EMIT_REF,
) -> dict[str, Any]:
    """
    [ACTION]
    Run the cold-clone bootstrap probe over a checkout root and return its receipt.

    - Teleology: prove a fresh checkout can bootstrap the named first-wave suite with no private state leaking, gating the public-clone story; the core organ behind the CLI.
    - Guarantee: returns a receipt dict whose `status` is "pass" only when the suite is supported, all REQUIRED_INPUTS fixtures exist, the secret-exclusion scan passes, pattern-binding validates, and all PATTERN_RECEIPTS are present; on pass it carries the secret-exclusion scan, observed first-wave receipts, and receipt_paths.
    - Fails: never raises (the one risky call, validate_secret_exclusion_scan, is caught); instead returns a non-pass receipt — status "blocked_invalid_input" (UNKNOWN_COLD_CLONE_SUITE), "blocked_dependency_missing" (MISSING_FIXTURE_INPUT or MISSING_PATTERN_BINDING_RECEIPT), "blocked_command_unavailable" (COMMAND_UNAVAILABLE), or "blocked_secret_exclusion" (SECRET_EXCLUSION_SCAN_BLOCKED).
    - Reads: REQUIRED_INPUTS fixtures under `root`/fixtures/first_wave/; the secret-exclusion scan; pattern-binding input fixtures and receipts.
    - Writes: pattern-binding receipts into a scratch dir under `root`/.microcosm/ and mirrors missing canonical receipts (via _mirror_missing_pattern_receipts); does not itself write the `--emit` file (the CLI does).
    - When-needed: when verifying a cold clone bootstraps cleanly and privately before release.
    - Escalates-to: validate_secret_exclusion_scan, validate_pattern_binding, and the emitted receipt itself as the higher-fidelity evidence surface.
    - Non-goal: does not authorize release, public-safe equivalence beyond the secret-exclusion + pattern-binding checks, or whole-system correctness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    root_path = Path(root)
    emit_ref_text = str(emit_ref)
    receipt = base_receipt(
        "cold_clone_probe",
        suite,
        command=_bootstrap_command(suite, emit_ref_text),
    )
    receipt.update(
        {
            "suite": suite,
            "emit_ref": emit_ref_text,
            "receipt_paths": [emit_ref_text],
        }
    )
    if suite not in SUPPORTED_SUITES:
        receipt.update(
            {
                "status": "blocked_invalid_input",
                "blocked_dependency_codes": ["UNKNOWN_COLD_CLONE_SUITE"],
                "supported_suites": list(SUPPORTED_SUITES),
            }
        )
        return receipt
    missing_inputs = [path for path in REQUIRED_INPUTS if not _path_is_file(root_path / path)]
    if missing_inputs:
        receipt.update(
            {
                "status": "blocked_dependency_missing",
                "blocked_dependency_codes": ["MISSING_FIXTURE_INPUT"],
                "missing_inputs": missing_inputs,
            }
        )
        return receipt
    try:
        scan_receipt = validate_secret_exclusion_scan(root_path)
    except Exception as exc:
        receipt.update(
            {
                "status": "blocked_command_unavailable",
                "blocked_dependency_codes": ["COMMAND_UNAVAILABLE"],
                "error": str(exc),
            }
        )
        return receipt
    if scan_receipt["status"] != "pass":
        secret_scan = scan_receipt.get("secret_exclusion_scan", {"status": scan_receipt["status"]})
        receipt.update(
            {
                "status": "blocked_secret_exclusion",
                "blocked_dependency_codes": ["SECRET_EXCLUSION_SCAN_BLOCKED"],
                "secret_exclusion_scan": secret_scan,
                "private_state_scan": {
                    "compatibility_alias_for": "secret_exclusion_scan",
                    **secret_scan,
                },
            }
        )
        return receipt

    pattern_out = root_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
    pattern_result = validate_pattern_binding(
        root_path / "fixtures/first_wave/pattern_binding_contract/input",
        pattern_out,
        command="bootstrap pattern_binding_contract validate",
    )
    _mirror_missing_pattern_receipts(root_path, pattern_out)
    missing_receipts = [path for path in PATTERN_RECEIPTS if not _path_is_file(root_path / path)]
    if pattern_result["status"] != "pass" or missing_receipts:
        receipt.update(
            {
                "status": "blocked_dependency_missing",
                "blocked_dependency_codes": ["MISSING_PATTERN_BINDING_RECEIPT"],
                "missing_receipts": missing_receipts,
                "pattern_binding_status": pattern_result["status"],
            }
        )
        return receipt

    receipt.update(
        {
            "status": "pass",
            "secret_exclusion_scan": scan_receipt["secret_exclusion_scan"],
            "private_state_scan": {
                "compatibility_alias_for": "secret_exclusion_scan",
                **scan_receipt["secret_exclusion_scan"],
            },
            "first_wave_receipts_observed": PATTERN_RECEIPTS,
            "receipt_paths": [emit_ref_text, *PATTERN_RECEIPTS],
        }
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entry that runs the cold-clone probe and emits its receipt.

    - Teleology: proves a fresh checkout can bootstrap the first-wave suite with no private state, gating the public clone story.
    - Guarantee: on return, a probe receipt for the chosen suite is written to the `--emit` path and exit code matches its status.
    - Fails: invalid/missing `--emit` -> argparse error -> SystemExit(2); probe blocked (bad suite, missing fixtures, secret leak, missing receipts) -> return 1.
    - Reads: cwd fixtures under fixtures/first_wave/, secret-exclusion scan, pattern-binding receipts.
    - Writes: receipt JSON at the `--emit` path; mirrored pattern-binding receipts under the checkout root.
    - When-needed: verifying a cold clone bootstraps cleanly before release.
    - Escalates-to: run_probe, validate_secret_exclusion_scan, validate_pattern_binding.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="first-wave", choices=SUPPORTED_SUITES)
    parser.add_argument("--emit", required=True)
    args = parser.parse_args(argv)
    receipt = run_probe(Path.cwd(), suite=args.suite, emit_ref=args.emit)
    write_receipt(args.emit, receipt)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
