from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StrictJsonError(ValueError):
    """Raised when strict JSON parsing fails."""


class DuplicateJsonKeyError(StrictJsonError):
    """Raised when a JSON object repeats a key."""


class StrictJsonObjectError(StrictJsonError):
    """Raised when a JSONL row must be an object but is not."""


def _reject_duplicate_keys(source: str):
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise DuplicateJsonKeyError(f"{source}: duplicate JSON key {key!r}")
            seen[key] = value
        return seen

    return hook


def loads_json_strict(text: str, source: str = "<memory>") -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys(source))
    except DuplicateJsonKeyError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"{source}: invalid JSON: {exc}") from exc


def read_json_strict(path: str | Path) -> Any:
    source = Path(path)
    return loads_json_strict(source.read_text(encoding="utf-8"), str(source))


def read_jsonl_strict(path: str | Path) -> list[object]:
    source = Path(path)
    rows: list[object] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = loads_json_strict(line, f"{source}:{line_number}")
        if not isinstance(row, dict):
            raise StrictJsonObjectError(f"{source}:{line_number} is not a JSON object")
        rows.append(row)
    return rows
