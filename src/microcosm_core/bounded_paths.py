from __future__ import annotations

from bisect import insort
from collections.abc import Iterable
from pathlib import Path


def bounded_sorted_paths(rows: Iterable[Path], limit: int | None) -> tuple[int, list[Path]]:
    """Return the lexicographically first paths without sorting the full stream."""
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
