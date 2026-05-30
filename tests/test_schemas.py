from __future__ import annotations

from pathlib import Path

import pytest

from microcosm_core import schemas
from microcosm_core.schemas import (
    DuplicateJsonKeyError,
    StrictJsonObjectError,
    read_jsonl_strict,
)


def test_read_jsonl_strict_streams_rows_without_full_file_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "one"}\n\n{"id": "two"}\n', encoding="utf-8")
    original_read_text = Path.read_text

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            raise AssertionError("read_jsonl_strict should stream JSONL rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    assert read_jsonl_strict(path) == [{"id": "one"}, {"id": "two"}]


def test_read_jsonl_strict_keeps_line_numbered_duplicate_key_errors(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"ok": true}\n{"id": 1, "id": 2}\n', encoding="utf-8")

    with pytest.raises(DuplicateJsonKeyError) as excinfo:
        read_jsonl_strict(path)

    assert f"{path}:2" in str(excinfo.value)


def test_read_jsonl_strict_rejects_non_object_rows(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"ok": true}\n["not", "object"]\n', encoding="utf-8")

    with pytest.raises(StrictJsonObjectError) as excinfo:
        read_jsonl_strict(path)

    assert f"{path}:2 is not a JSON object" in str(excinfo.value)


def test_loads_json_strict_still_rejects_duplicate_keys() -> None:
    with pytest.raises(DuplicateJsonKeyError):
        schemas.loads_json_strict('{"a": 1, "a": 2}', "duplicate_fixture")
