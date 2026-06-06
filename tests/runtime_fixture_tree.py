from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable


FIXTURE_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def _copy_file_prefer_hardlink(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination


def copytree_fixture(
    source: Path,
    destination: Path,
    *,
    prefer_hardlinks: bool = True,
) -> None:
    copy_function = _copy_file_prefer_hardlink if prefer_hardlinks else shutil.copy2
    shutil.copytree(
        source,
        destination,
        ignore=FIXTURE_COPY_IGNORE,
        copy_function=copy_function,
    )


def copy_microcosm_runtime_root(
    tmp_path: Path,
    source_root: Path,
    *,
    static_refs: Iterable[str],
    mutable_refs: Iterable[str],
) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    for ref in mutable_refs:
        copytree_fixture(
            source_root / ref,
            public_root / ref,
            prefer_hardlinks=False,
        )
    for ref in static_refs:
        copytree_fixture(
            source_root / ref,
            public_root / ref,
            prefer_hardlinks=True,
        )
    return public_root
