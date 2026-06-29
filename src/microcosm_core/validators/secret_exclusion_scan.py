"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.validators.secret_exclusion_scan` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SKIP_DIRS, SKIP_FILE_SUFFIXES, validate_scan, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
from collections.abc import Iterator
import os
from pathlib import Path
from typing import Any

from microcosm_core.receipts import base_receipt, write_receipt
from microcosm_core.secret_exclusion_scan import (
    PASS,
    is_text_scan_candidate,
    load_forbidden_classes,
    scan_paths,
)


SKIP_DIRS = {
    ".git",
    ".microcosm",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "microcosm-substrate",
    "node_modules",
}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}


def _is_local_residue(path: Path, root: Path) -> bool:
    """
    [ACTION]
    Filter local build/cache residue out of the secret-exclusion walk.

    - Teleology: keep the scan focused on real public substrate by dropping VCS/cache/build dirs, egg-info, compiled artifacts, and .DS_Store so they cannot inflate or mask hits.
    - Guarantee: returns True iff any path part is in SKIP_DIRS, ends with `.egg-info`, the suffix is in SKIP_FILE_SUFFIXES, or the name is `.DS_Store`; otherwise False.
    - Fails: never raises; a path outside `root` (ValueError on relative_to) is checked against its own parts instead of the relative ones.
    - When-needed: inspect when scan candidate counts look wrong or a residue directory is unexpectedly scanned or skipped.
    - Escalates-to: SKIP_DIRS / SKIP_FILE_SUFFIXES constants and `_iter_scan_paths` caller.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = rel.parts
    return (
        any(part in SKIP_DIRS for part in parts)
        or any(part.endswith(".egg-info") for part in parts)
        or path.suffix in SKIP_FILE_SUFFIXES
        or path.name == ".DS_Store"
    )


def _iter_scan_paths(root: Path) -> Iterator[Path]:
    """
    [ACTION]
    Yield the text-scan candidate file set under `root`.

    - Teleology: produce the exact path stream the secret-exclusion scanner consumes, pruning residue subtrees in-place so os.walk never descends into them.
    - Guarantee: yields each file under `root` that is both `is_text_scan_candidate` and not `_is_local_residue`; residue directories are removed from traversal before recursion.
    - Fails: never raises by itself; surfaces only OSError that `os.walk` would raise; an empty/absent tree yields nothing.
    - When-needed: inspect when a file you expected scanned is absent from hits or a residue path leaks into the scan.
    - Escalates-to: `is_text_scan_candidate` / `_is_local_residue` and the `validate_scan` caller.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _is_local_residue(current / dirname, root)
        ]
        for filename in filenames:
            path = current / filename
            if is_text_scan_candidate(path) and not _is_local_residue(path, root):
                yield path


def validate_scan(root: str | Path, policy: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    Public secret-exclusion validator: scan `root` and build the first-wave receipt.

    - Teleology: prove that the public tree excludes secrets, credentials, account/session payloads, and operator-conversation bodies before any release-facing surface trusts it.
    - Guarantee: returns a `base_receipt` dict whose `status` is the scan status (PASS only when there are no blocking hits) and whose `secret_exclusion_scan` carries the normalized, body-free scan over the walked candidate set.
    - Fails: never raises for ordinary input; returns a receipt with a BLOCKED status when blocking hits exist; propagates only errors from loading the policy or reading the tree (e.g. missing/invalid `forbidden_classes` policy).
    - When-needed: inspect when deciding whether the public tree is secret-clean, or when a release/publish gate reports a secret-exclusion block.
    - Escalates-to: `microcosm_core.secret_exclusion_scan.scan_paths` + `core/private_state_forbidden_classes.json` policy and `receipts/first_wave/secret_exclusion_scan.json`.
    - Non-goal: passing does not authorize release, publication, provider calls, private-root equivalence, source-body export, or whole-system correctness; it only attests the scanned candidate set carries no detected forbidden-class material.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root_path = Path(root)
    policy_path = (
        Path(policy)
        if policy is not None
        else root_path / "core/private_state_forbidden_classes.json"
    )
    forbidden_classes = load_forbidden_classes(policy_path)
    scan = scan_paths(
        _iter_scan_paths(root_path),
        forbidden_classes=forbidden_classes,
        display_root=root_path,
    )
    receipt = base_receipt("secret_exclusion_scan", "first_wave")
    receipt.update(
        {
            "status": PASS if scan["status"] == PASS else scan["status"],
            "secret_exclusion_scan": scan,
            "receipt_paths": ["receipts/first_wave/secret_exclusion_scan.json"],
        }
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entrypoint: run `validate_scan` over `--root` and write the receipt to `--out`.

    - Teleology: expose the secret-exclusion validator as a command so release/CI gates can run it and key on a process exit code.
    - Guarantee: writes the receipt to `--out` via `write_receipt` and returns 0 iff the receipt status is PASS, else 1.
    - Fails: argparse exits non-zero when required `--root`/`--out` are missing; otherwise non-PASS scans return exit 1 (no exception); propagates write/scan errors from the underlying calls.
    - When-needed: inspect when wiring the scan into a script/gate or when the command's exit code disagrees with the on-disk receipt status.
    - Escalates-to: `validate_scan` / `write_receipt` and the emitted `--out` receipt file.
    - Non-goal: exit 0 attests only the scanned tree is secret-clean per policy; it does not authorize release, publication, or treat the receipt as runtime-product completeness.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy")
    args = parser.parse_args(argv)

    receipt = validate_scan(args.root, args.policy)
    write_receipt(args.out, receipt)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
