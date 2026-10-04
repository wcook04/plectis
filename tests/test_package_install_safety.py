from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def smoke_module():
    script = Path(__file__).resolve().parents[1] / "scripts/package_install_smoke.py"
    spec = importlib.util.spec_from_file_location("package_install_safety", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("location", ["source", "ancestor", "descendant", "symlink"])
def test_package_smoke_rejects_overlapping_trees_before_deletion(
    tmp_path: Path, monkeypatch, smoke_module, location: str
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    sentinel = source / "keep.txt"
    sentinel.write_text("source must survive")
    if location == "source":
        work = source
    elif location == "ancestor":
        work = tmp_path
    elif location == "descendant":
        work = source / "scratch"
        work.mkdir()
        (work / "keep.txt").write_text("scratch must survive rejection")
    else:
        work = tmp_path / "source-alias"
        try:
            work.symlink_to(source, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlinks are unavailable: {exc}")

    def unexpected_delete(*args, **kwargs):
        pytest.fail("overlap validation must run before deleting anything")

    monkeypatch.setattr(smoke_module.shutil, "rmtree", unexpected_delete)
    with pytest.raises(SystemExit, match="must not overlap"):
        smoke_module.run_package_smoke(source, work, sys.executable)

    assert sentinel.read_text() == "source must survive"
    if location == "descendant":
        assert (work / "keep.txt").read_text() == "scratch must survive rejection"


def test_package_smoke_recreates_a_separate_existing_work_dir(
    tmp_path: Path, monkeypatch, smoke_module
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    work = tmp_path / "work"
    work.mkdir()
    (work / "previous-run.txt").write_text("stale output")

    def stop_after_cleanup(source_root: Path, work_dir: Path):
        assert source_root == source
        assert work_dir == work
        assert list(work.iterdir()) == []
        assert (source / "pyproject.toml").is_file()
        raise RuntimeError("staging reached")

    monkeypatch.setattr(smoke_module, "_stage_source_tree", stop_after_cleanup)
    with pytest.raises(RuntimeError, match="staging reached"):
        smoke_module.run_package_smoke(source, work, sys.executable)


def test_make_package_smoke_preserves_rejected_source_tree(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = tmp_path / "source"
    (source / "scripts").mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    sentinel = source / "keep.txt"
    sentinel.write_text("source must survive wrapper cleanup")
    shutil.copy2(repo_root / "Makefile", source / "Makefile")
    shutil.copy2(
        repo_root / "scripts/package_install_smoke.py",
        source / "scripts/package_install_smoke.py",
    )

    result = subprocess.run(
        ["make", "package-smoke", f"PYTHON={sys.executable}",
         f"PACKAGE_SMOKE_TMP={source}"],
        cwd=source, capture_output=True, text=True, check=False,
    )

    assert result.returncode != 0
    assert "must not overlap" in result.stderr
    assert sentinel.read_text() == "source must survive wrapper cleanup"
