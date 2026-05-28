from __future__ import annotations

import json

from microcosm_core.receipts import write_json_atomic


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
