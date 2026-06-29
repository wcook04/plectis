"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.bounded_paths` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: bounded_sorted_paths
- Reads: call arguments, module constants, imported helpers.
- Writes: return values and any explicit side effects performed by exported entry points.
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

from bisect import insort
from collections.abc import Iterable
from pathlib import Path


def bounded_sorted_paths(rows: Iterable[Path], limit: int | None) -> tuple[int, list[Path]]:
    """
    [ACTION]
    Return the lexicographically first paths without sorting the full stream.
    - Teleology: Implements `bounded_sorted_paths` for `microcosm_core.bounded_paths` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if limit is None:
        sorted_rows = sorted(rows)
        return len(sorted_rows), sorted_rows
    row_limit = max(limit, 0)
    if row_limit == 0:
        return sum(1 for _ in rows), []
    selected: list[Path] = []
    count = 0
    for row in rows:
        count += 1
        if len(selected) < row_limit:
            insort(selected, row)
        elif row < selected[-1]:
            selected.pop()
            insort(selected, row)
    return count, selected
