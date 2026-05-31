from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import receipts
from microcosm_core.receipts import write_json_atomic, write_local_state_json_atomic


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_receipt_writer_honors_runtime_read_only_gate(tmp_path, monkeypatch) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"before": true}\n', encoding="utf-8")
    before = receipt_path.read_text(encoding="utf-8")
    monkeypatch.setenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", "0")

    write_json_atomic(receipt_path, {"after": True})

    assert receipt_path.read_text(encoding="utf-8") == before


def test_receipt_writer_trims_runtime_read_only_gate(tmp_path, monkeypatch) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text('{"before": true}\n', encoding="utf-8")
    before = receipt_path.read_text(encoding="utf-8")
    monkeypatch.setenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", " false ")

    write_json_atomic(receipt_path, {"after": True})

    assert receipt_path.read_text(encoding="utf-8") == before


def test_local_state_writer_ignores_runtime_read_only_gate(
    tmp_path, monkeypatch
) -> None:
    state_path = tmp_path / ".microcosm" / "routes.json"
    monkeypatch.setenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", "0")

    write_local_state_json_atomic(state_path, {"status": "pass"})

    assert json.loads(state_path.read_text(encoding="utf-8")) == {"status": "pass"}


def test_receipt_writer_still_writes_by_default(tmp_path, monkeypatch) -> None:
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)

    write_json_atomic(receipt_path, {"status": "pass"})

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {"status": "pass"}


def test_receipt_writer_preserves_created_at_for_timestamp_only_rewrites(
    tmp_path, monkeypatch
) -> None:
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)

    write_json_atomic(
        receipt_path,
        {"created_at": "2026-01-01T00:00:00+00:00", "status": "pass"},
    )
    write_json_atomic(
        receipt_path,
        {"created_at": "2099-01-01T00:00:00+00:00", "status": "pass"},
    )

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {
        "created_at": "2026-01-01T00:00:00+00:00",
        "status": "pass",
    }

    write_json_atomic(
        receipt_path,
        {"created_at": "2099-01-01T00:00:00+00:00", "status": "blocked"},
    )

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {
        "created_at": "2099-01-01T00:00:00+00:00",
        "status": "blocked",
    }


def test_receipt_writer_ignores_duplicate_key_previous_receipt(
    tmp_path, monkeypatch
) -> None:
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)
    receipt_path.write_text(
        (
            '{"created_at": "2026-01-01T00:00:00+00:00", '
            '"created_at": "2099-01-01T00:00:00+00:00", '
            '"status": "pass"}'
        ),
        encoding="utf-8",
    )

    write_json_atomic(
        receipt_path,
        {"created_at": "2030-01-01T00:00:00+00:00", "status": "pass"},
    )

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {
        "created_at": "2030-01-01T00:00:00+00:00",
        "status": "pass",
    }


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


def test_receipt_writer_blocks_tracked_receipts_by_default_outside_pytest(
    tmp_path: Path, monkeypatch
) -> None:
    tracked_root = tmp_path / "receipts"
    receipt_path = tracked_root / "runtime_shell/public_status_card.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"before": true}\n', encoding="utf-8")
    before = receipt_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        receipts, "TRACKED_RECEIPTS_ROOT", tracked_root.resolve(strict=False)
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_TRACKED_RECEIPT_WRITES", raising=False)

    write_json_atomic(receipt_path, {"after": True})

    assert receipt_path.read_text(encoding="utf-8") == before


def test_receipt_writer_blocks_symlinked_tracked_receipt_path_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    tracked_root = tmp_path / "receipts"
    receipt_path = tracked_root / "runtime_shell/linked_status_card.json"
    receipt_path.parent.mkdir(parents=True)
    outside_target = tmp_path / "outside_status_card.json"
    outside_target.write_text('{"before": true}\n', encoding="utf-8")
    try:
        receipt_path.symlink_to(outside_target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    monkeypatch.setattr(
        receipts, "TRACKED_RECEIPTS_ROOT", tracked_root.resolve(strict=False)
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_TRACKED_RECEIPT_WRITES", raising=False)

    assert receipts.is_tracked_receipt_path(receipt_path) is True

    write_json_atomic(receipt_path, {"after": True})

    assert receipt_path.is_symlink()
    assert outside_target.read_text(encoding="utf-8") == '{"before": true}\n'


def test_local_state_writer_keeps_tracked_receipts_read_only_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    tracked_root = tmp_path / "receipts"
    receipt_path = tracked_root / "runtime_shell/public_status_card.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"before": true}\n', encoding="utf-8")
    before = receipt_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        receipts, "TRACKED_RECEIPTS_ROOT", tracked_root.resolve(strict=False)
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MICROCOSM_TRACKED_RECEIPT_WRITES", raising=False)

    write_local_state_json_atomic(receipt_path, {"after": True})

    assert receipt_path.read_text(encoding="utf-8") == before


def test_local_state_writer_blocks_symlinked_tracked_receipt_path_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    tracked_root = tmp_path / "receipts"
    receipt_path = tracked_root / "runtime_shell/linked_status_card.json"
    receipt_path.parent.mkdir(parents=True)
    outside_target = tmp_path / "outside_status_card.json"
    outside_target.write_text('{"before": true}\n', encoding="utf-8")
    try:
        receipt_path.symlink_to(outside_target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    monkeypatch.setattr(
        receipts, "TRACKED_RECEIPTS_ROOT", tracked_root.resolve(strict=False)
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MICROCOSM_TRACKED_RECEIPT_WRITES", raising=False)

    assert receipts.is_tracked_receipt_path(receipt_path) is True

    write_local_state_json_atomic(receipt_path, {"after": True})

    assert receipt_path.is_symlink()
    assert outside_target.read_text(encoding="utf-8") == '{"before": true}\n'


def test_receipt_writer_allows_explicit_tracked_receipt_refresh(
    tmp_path: Path, monkeypatch
) -> None:
    tracked_root = tmp_path / "receipts"
    receipt_path = tracked_root / "acceptance/first_wave/example.json"
    receipt_path.parent.mkdir(parents=True)

    monkeypatch.setattr(
        receipts, "TRACKED_RECEIPTS_ROOT", tracked_root.resolve(strict=False)
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.setenv("MICROCOSM_TRACKED_RECEIPT_WRITES", "1")

    write_json_atomic(receipt_path, {"status": "refreshed"})

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {
        "status": "refreshed"
    }


def test_receipt_writer_trims_explicit_tracked_receipt_refresh_flag(
    tmp_path: Path, monkeypatch
) -> None:
    tracked_root = tmp_path / "receipts"
    receipt_path = tracked_root / "acceptance/first_wave/example.json"
    receipt_path.parent.mkdir(parents=True)

    monkeypatch.setattr(
        receipts, "TRACKED_RECEIPTS_ROOT", tracked_root.resolve(strict=False)
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("MICROCOSM_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)
    monkeypatch.setenv("MICROCOSM_TRACKED_RECEIPT_WRITES", " 1 ")

    write_json_atomic(receipt_path, {"status": "refreshed"})

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == {
        "status": "refreshed"
    }
