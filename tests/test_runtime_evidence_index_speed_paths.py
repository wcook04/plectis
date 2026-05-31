from __future__ import annotations

from pathlib import Path

import pytest

from microcosm_core import bounded_paths
from microcosm_core import project_substrate
from microcosm_core import runtime_evidence_index


def test_runtime_evidence_index_streams_receipts_without_rglob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_root = public_root / "receipts"
    (receipt_root / "runtime_shell/demo").mkdir(parents=True)
    (receipt_root / "runtime_shell/demo/result_z.json").write_text(
        '{"status": "pass", "organ_id": "demo_z"}\n',
        encoding="utf-8",
    )
    (receipt_root / "runtime_shell/demo/result_a.json").write_text(
        '{"status": "pass", "organ_id": "demo_a"}\n',
        encoding="utf-8",
    )
    (receipt_root / "runtime_shell/demo/result_b.txt").write_text(
        "not evidence\n",
        encoding="utf-8",
    )
    (receipt_root / "acceptance/result_b.json").parent.mkdir(parents=True)
    (receipt_root / "acceptance/result_b.json").write_text(
        '{"status": "blocked", "organ_id": "demo_b"}\n',
        encoding="utf-8",
    )

    original_rglob = Path.rglob

    def fail_if_rglobbed(self: Path, *_args: object, **_kwargs: object) -> object:
        if self == receipt_root:
            raise AssertionError("runtime evidence index must not rglob receipts")
        return original_rglob(self, *_args, **_kwargs)

    monkeypatch.setattr(Path, "rglob", fail_if_rglobbed)

    payload = runtime_evidence_index.list_runtime_evidence(public_root, limit=2)

    assert payload["receipt_count"] == 3
    assert payload["returned_receipt_count"] == 2
    assert payload["truncated"] is True
    assert [row["receipt_ref"] for row in payload["evidence"]] == [
        "receipts/acceptance/result_b.json",
        "receipts/runtime_shell/demo/result_a.json",
    ]


def test_runtime_evidence_index_missing_receipts_root_is_empty(tmp_path: Path) -> None:
    payload = runtime_evidence_index.list_runtime_evidence(
        tmp_path / "microcosm-substrate",
    )

    assert payload["receipt_count"] == 0
    assert payload["returned_receipt_count"] == 0
    assert payload["evidence"] == []


def test_evidence_lists_share_bounded_path_selector() -> None:
    assert runtime_evidence_index._bounded_sorted_paths is bounded_paths.bounded_sorted_paths
    assert project_substrate._bounded_sorted_paths is bounded_paths.bounded_sorted_paths
