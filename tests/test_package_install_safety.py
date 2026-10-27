from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def smoke_module():
    script = Path(__file__).resolve().parents[1] / "scripts/release/package_install_smoke.py"
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
    (source / "scripts/release").mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    sentinel = source / "keep.txt"
    sentinel.write_text("source must survive wrapper cleanup")
    shutil.copy2(repo_root / "Makefile", source / "Makefile")
    shutil.copy2(
        repo_root / "scripts/release/package_install_smoke.py",
        source / "scripts/release/package_install_smoke.py",
    )

    result = subprocess.run(
        ["make", "package-smoke", f"PYTHON={sys.executable}",
         f"PACKAGE_SMOKE_TMP={source}"],
        cwd=source, capture_output=True, text=True, check=False,
    )

    assert result.returncode != 0
    assert "must not overlap" in result.stderr
    assert sentinel.read_text() == "source must survive wrapper cleanup"


def test_package_staging_keeps_maintained_builders_and_drops_generated_output(tmp_path, smoke_module):
    source = tmp_path / "repo"
    for relative in ("scripts/build/build_map.py", "build/generated.py",
                     "scripts/build/__pycache__/build_map.pyc"):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    staged = smoke_module._stage_source_tree(source, tmp_path / "work")
    assert (staged / "scripts/build/build_map.py").read_text() == "fixture"
    assert not (staged / "build").exists()
    assert not (staged / "scripts/build/__pycache__").exists()


@pytest.mark.parametrize("wheel_names", [
    ["plectis-0.0.0-py3-none-any.whl"], [], ["other-0.0.0-py3-none-any.whl"],
    ["plectis-0.0.0-py3-none-any.whl", "plectis-0.0.1-py3-none-any.whl"],
])
def test_package_smoke_installs_only_the_single_built_wheel(
    tmp_path, monkeypatch, smoke_module, wheel_names
):
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[project]\nname='plectis'\n")
    work = tmp_path / "work"
    installed = []

    def run(argv, **kwargs):
        assert "PYTHONPATH" not in kwargs.get("env", {})
        if argv[1:4] == ["-I", "-m", "venv"]:
            assert kwargs["cwd"] == work / "project"
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "wheel" in argv:
            wheel_dir = Path(argv[argv.index("--wheel-dir") + 1])
            wheel_dir.mkdir()
            for name in wheel_names:
                (wheel_dir / name).write_bytes(b"test-only wheel inventory")
            return subprocess.CompletedProcess(argv, 0, "", "")
        if "install" in argv:
            assert "--no-index" in argv
            assert "--no-deps" in argv
            installed.append(Path(argv[-1]))
            raise RuntimeError("explicit wheel install reached")
        pytest.fail(f"unexpected command: {argv}")

    monkeypatch.setattr(smoke_module, "_run", run)
    if len(wheel_names) == 1 and wheel_names[0].startswith("plectis-"):
        with pytest.raises(RuntimeError, match="explicit wheel install reached"):
            smoke_module.run_package_smoke(source, work, sys.executable)
        assert installed == [work / "wheelhouse" / wheel_names[0]]
    else:
        with pytest.raises(SystemExit, match="exactly one Plectis wheel"):
            smoke_module.run_package_smoke(source, work, sys.executable)
        assert installed == []
