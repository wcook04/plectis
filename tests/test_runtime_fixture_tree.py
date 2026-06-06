from __future__ import annotations

from pathlib import Path

import runtime_fixture_tree
from runtime_fixture_tree import copy_microcosm_runtime_root


def _same_inode(left: Path, right: Path) -> bool:
    left_stat = left.stat()
    right_stat = right.stat()
    return (left_stat.st_dev, left_stat.st_ino) == (
        right_stat.st_dev,
        right_stat.st_ino,
    )


def test_copy_microcosm_runtime_root_hardlinks_static_files_and_copies_mutable(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    (source_root / "static").mkdir(parents=True)
    (source_root / "mutable").mkdir(parents=True)
    static_source = source_root / "static/example.json"
    mutable_source = source_root / "mutable/state.json"
    static_source.write_text('{"status": "static"}\n', encoding="utf-8")
    mutable_source.write_text('{"status": "mutable"}\n', encoding="utf-8")

    public_root = copy_microcosm_runtime_root(
        tmp_path / "work",
        source_root,
        static_refs=("static",),
        mutable_refs=("mutable",),
    )

    assert _same_inode(static_source, public_root / "static/example.json")
    assert not _same_inode(mutable_source, public_root / "mutable/state.json")


def test_copy_microcosm_runtime_root_falls_back_to_file_copy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "source"
    (source_root / "static").mkdir(parents=True)
    static_source = source_root / "static/example.json"
    static_source.write_text('{"status": "static"}\n', encoding="utf-8")
    monkeypatch.setattr(
        runtime_fixture_tree.os,
        "link",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("cross-device")),
    )

    public_root = copy_microcosm_runtime_root(
        tmp_path / "work",
        source_root,
        static_refs=("static",),
        mutable_refs=(),
    )

    static_copy = public_root / "static/example.json"
    assert static_copy.read_text(encoding="utf-8") == '{"status": "static"}\n'
    assert not _same_inode(static_source, static_copy)
