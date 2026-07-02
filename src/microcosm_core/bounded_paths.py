"""Orders path collections deterministically while enforcing bounded result sizes."""
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
