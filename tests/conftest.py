from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
TRACKED_RUNTIME_RECEIPTS = (MICROCOSM_ROOT / "receipts/runtime_shell").resolve(
    strict=False
)


def _is_tracked_runtime_receipt(path: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(TRACKED_RUNTIME_RECEIPTS)
    except ValueError:
        return False
    return True


@pytest.fixture(autouse=True)
def keep_tracked_runtime_shell_receipts_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_write_json_atomic = runtime_shell.write_json_atomic

    def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        if _is_tracked_runtime_receipt(Path(path)):
            return
        original_write_json_atomic(path, payload)

    monkeypatch.setattr(runtime_shell, "write_json_atomic", write_json_atomic)
