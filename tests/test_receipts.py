from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.receipts import write_json_atomic


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_receipt_writer_honors_runtime_read_only_gate(tmp_path, monkeypatch) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"before": true}\n', encoding="utf-8")
    before = receipt_path.read_text(encoding="utf-8")
    monkeypatch.setenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", "0")

    write_json_atomic(receipt_path, {"after": True})

    assert receipt_path.read_text(encoding="utf-8") == before


def test_receipt_writer_still_writes_by_default(tmp_path, monkeypatch) -> None:
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)

    write_json_atomic(receipt_path, {"status": "pass"})

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {"status": "pass"}


def test_receipt_writer_keeps_source_tree_receipts_read_only_under_pytest() -> None:
    receipt_paths = [
        MICROCOSM_ROOT / "receipts/runtime_shell/public_stripping_guard_lens.json",
        MICROCOSM_ROOT
        / "receipts/acceptance/first_wave/macro_projection_import_protocol_fixture_acceptance.json",
    ]
    before = {path: path.read_text(encoding="utf-8") for path in receipt_paths}

    for receipt_path in receipt_paths:
        write_json_atomic(receipt_path, {"status": "would_dirty_source_tree"})

    after = {path: path.read_text(encoding="utf-8") for path in receipt_paths}
    assert after == before
