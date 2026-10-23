"""Real isolated imports and generated-worker execution without the old runtime."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import venv

import pytest


ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts/release/verify_operations_install.py"


@pytest.fixture
def isolated_python(tmp_path):
    """A stdlib-only installation with neither pip nor distribution metadata."""
    environment = tmp_path / "venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    completed = subprocess.run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True, text=True, check=True, timeout=15,
    )
    library = Path(completed.stdout.strip())
    working = tmp_path / "unrelated-project"
    working.mkdir()
    return python, library, working


def copy_components(library):
    shutil.copytree(ROOT / "src/plectis", library / "plectis",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def run_smoke(python, working, *arguments, isolated=True):
    # A caller's source checkout must never rescue an incomplete installation.
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
                   "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [str(python), *(["-I"] if isolated else []), "-B", str(SMOKE), *arguments],
        cwd=working, env=environment, capture_output=True, text=True, timeout=45,
    )


def test_components_work_as_the_only_copied_package(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    # Establish that this proves copy portability, not an accidental dependency
    # on the old runtime or a pip-generated plectis.dist-info directory.
    probe = subprocess.run(
        [str(python), "-I", "-c",
         "import importlib.util, importlib.metadata; "
         f"import plectis; assert plectis.__version__ == {version!r}; "
         "assert importlib.util.find_spec('microcosm_core') is None; "
         "assert importlib.util.find_spec('pip') is None; "
         "assert not [d for d in importlib.metadata.distributions() "
         "if d.metadata['Name'] == 'plectis']"],
        cwd=working, capture_output=True, text=True, timeout=15,
    )
    assert probe.returncode == 0, probe.stderr
    completed = run_smoke(python, working, "--require-compatibility")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "passed"
    assert result["repair"]["score"] == 10
    assert result["repair"]["unknown_effect_retained"] is True
    assert result["publish"]["stale_worker"] == "rejected"
    assert result["publish"]["historical_retry"] == "replayed"
    assert result["compatibility"]["continuation"] == ["read"]
    assert all(Path(origin).is_relative_to(library)
               for origin in result["installed_modules"].values())
    assert list(working.iterdir()) == []


def test_missing_install_cannot_use_inherited_pythonpath_or_working_directory(isolated_python):
    python, _, working = isolated_python
    # Both common shadowing routes are present; -I must ignore both.
    shutil.copytree(ROOT / "src/plectis", working / "plectis")
    completed = run_smoke(python, working, "--require-compatibility")
    assert completed.returncode != 0
    assert "No module named 'plectis'" in completed.stderr
    assert not completed.stdout


def test_editable_checkout_import_is_rejected(isolated_python):
    python, library, working = isolated_python
    (library / "checkout.pth").write_text(str(ROOT / "src") + "\n", encoding="utf-8")
    completed = run_smoke(python, working)
    assert completed.returncode != 0
    assert "outside this Python installation" in completed.stderr
    assert not completed.stdout
    assert list(working.iterdir()) == []


def test_missing_generated_repair_kernel_fails_the_smoke(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    (library / "plectis/repair/_generated/Repair.py").unlink()
    completed = run_smoke(python, working)
    assert completed.returncode != 0
    assert "kernel" in completed.stderr
    assert not completed.stdout


def test_missing_compatibility_is_rejected_when_required(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    shutil.rmtree(library / "plectis/compatibility")
    completed = run_smoke(python, working, "--require-compatibility")
    assert completed.returncode != 0
    assert "plectis.compatibility" in completed.stderr
    assert not completed.stdout


def test_smoke_explains_required_isolation(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    completed = run_smoke(python, working, isolated=False)
    assert completed.returncode != 0
    assert "python -I" in completed.stderr
    assert not completed.stdout
