"""
Implements schemas for the public Plectis package.

Callers enter through `StrictJsonError`, `DuplicateJsonKeyError`, `StrictJsonObjectError`,
`loads_json_strict`, `read_json_strict`, and `read_jsonl_strict`; dependencies include
`json`, `pathlib`, and `typing`. Importing it does not authorize release work or hidden
private-state access; those effects live behind explicit calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StrictJsonError(ValueError):
        """
        Raised when strict Json Error fails inside `microcosm_core.schemas`.

        The dedicated type lets callers catch that failure without masking the original
        message.
        """


class DuplicateJsonKeyError(StrictJsonError):
        """
        Raised when duplicate Json Key Error fails inside `microcosm_core.schemas`.

        The dedicated type lets callers catch that failure without masking the original
        message.
        """


class StrictJsonObjectError(StrictJsonError):
        """
        Raised when strict Json Object Error fails inside `microcosm_core.schemas`.

        The dedicated type lets callers catch that failure without masking the original
        message.
        """


def _reject_duplicate_keys(source: str):
    """
    Compute reject duplicate keys from `source`.

    Inputs are `source`; notable helpers are `DuplicateJsonKeyError`; invalid cases raise
    from the explicit checks in the body.
    """
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """
        Derive hook without touching module import state.

        Inputs are `pairs`; notable helpers are `DuplicateJsonKeyError`; invalid cases raise
        from the explicit checks in the body.
        """
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise DuplicateJsonKeyError(f"{source}: duplicate JSON key {key!r}")
            seen[key] = value
        return seen

    return hook


def loads_json_strict(text: str, source: str = "<memory>") -> Any:
    """
    Compute loads JSON strict from `text` and `source`.

    Inputs are `text` and `source`; notable helpers are `loads`, `StrictJsonError`, and
    `_reject_duplicate_keys`; invalid cases raise from the explicit checks in the body.
    """
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys(source))
    except DuplicateJsonKeyError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"{source}: invalid JSON: {exc}") from exc


def read_json_strict(path: str | Path) -> Any:
    """
    Read read JSON strict for `microcosm_core.schemas`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    source = Path(path)
    return loads_json_strict(source.read_text(encoding="utf-8"), str(source))


def read_jsonl_strict(path: str | Path) -> list[object]:
    """
    Read read JSONl strict for `microcosm_core.schemas`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    source = Path(path)
    rows: list[object] = []
    with source.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            row = loads_json_strict(line, f"{source}:{line_number}")
            if not isinstance(row, dict):
                raise StrictJsonObjectError(
                    f"{source}:{line_number} is not a JSON object"
                )
            rows.append(row)
    return rows
