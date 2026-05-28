from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_cli_lightweight_reader_choices_match_composition_contract() -> None:
    from microcosm_core import cli
    from microcosm_core import first_screen_composition

    assert cli.TEXT_READER_CHOICES == first_screen_composition.TEXT_READER_CHOICES


def test_cli_version_flag_reports_package_version() -> None:
    pyproject = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    package_version = pyproject["project"]["version"]

    env = os.environ.copy()
    src = str(MICROCOSM_ROOT / "src")
    env["PYTHONPATH"] = (
        src
        if not env.get("PYTHONPATH")
        else src + os.pathsep + env["PYTHONPATH"]
    )
    result = subprocess.run(
        [sys.executable, "-m", "microcosm_core.cli", "--version"],
        cwd=MICROCOSM_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"microcosm {package_version}"
    assert result.stderr == ""


def test_package_module_entry_delegates_to_cli() -> None:
    pyproject = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    package_version = pyproject["project"]["version"]

    env = os.environ.copy()
    src = str(MICROCOSM_ROOT / "src")
    env["PYTHONPATH"] = (
        src
        if not env.get("PYTHONPATH")
        else src + os.pathsep + env["PYTHONPATH"]
    )
    result = subprocess.run(
        [sys.executable, "-m", "microcosm_core", "--version"],
        cwd=MICROCOSM_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"microcosm {package_version}"
    assert result.stderr == ""


def test_evidence_list_startup_does_not_import_first_screen_composition() -> None:
    env = os.environ.copy()
    src = str(MICROCOSM_ROOT / "src")
    env["PYTHONPATH"] = (
        src
        if not env.get("PYTHONPATH")
        else src + os.pathsep + env["PYTHONPATH"]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "importtime",
            "-m",
            "microcosm_core.cli",
            "evidence",
            "list",
        ],
        cwd=MICROCOSM_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert '"schema_version": "microcosm_runtime_evidence_v1"' in result.stdout
    assert "microcosm_core.first_screen_composition" not in result.stderr
