from __future__ import annotations

import os
import subprocess
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _run_bootstrap(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["./bootstrap.sh", *args],
        cwd=MICROCOSM_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_bootstrap_help_is_no_side_effect_public_entry() -> None:
    result = _run_bootstrap("--help")

    assert result.returncode == 0
    assert "Usage: ./bootstrap.sh [--suite SUITE] [--emit RECEIPT_PATH]" in result.stdout
    assert "--suite SUITE" in result.stdout
    assert "first-wave" in result.stdout
    assert ".microcosm/cold_clone_probe.json" in result.stdout
    assert result.stderr == ""


def test_bootstrap_argument_errors_preserve_usage_boundary() -> None:
    unknown = _run_bootstrap("--bogus")
    missing_suite = _run_bootstrap("--suite")
    missing_emit = _run_bootstrap("--emit", "--suite")

    assert unknown.returncode == 2
    assert "unknown argument: --bogus" in unknown.stderr
    assert "Usage: ./bootstrap.sh" in unknown.stderr

    assert missing_suite.returncode == 2
    assert "missing value for --suite" in missing_suite.stderr
    assert "Usage: ./bootstrap.sh" in missing_suite.stderr

    assert missing_emit.returncode == 2
    assert "missing value for --emit" in missing_emit.stderr
    assert "Usage: ./bootstrap.sh" in missing_emit.stderr


def test_bootstrap_honors_microcosm_python_override(tmp_path: Path) -> None:
    argv_log = tmp_path / "fake_python_argv.txt"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$@\" > \"$MICROCOSM_FAKE_PYTHON_ARGS\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["MICROCOSM_PYTHON"] = str(fake_python)
    env["PYTHON"] = str(tmp_path / "missing-python")
    env["MICROCOSM_FAKE_PYTHON_ARGS"] = str(argv_log)

    result = _run_bootstrap(
        "--suite",
        "first-wave",
        "--emit",
        "receipts/cold_clone_probe_test.json",
        env=env,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "Microcosm cold-clone probe passed",
        "suite: first-wave",
        "receipt: receipts/cold_clone_probe_test.json",
    ]
    assert argv_log.read_text(encoding="utf-8").splitlines() == [
        "-m",
        "microcosm_core.cold_clone_probe",
        "--suite",
        "first-wave",
        "--emit",
        "receipts/cold_clone_probe_test.json",
    ]


def test_bootstrap_default_emit_uses_ignored_local_state(tmp_path: Path) -> None:
    argv_log = tmp_path / "fake_python_argv.txt"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$@\" > \"$MICROCOSM_FAKE_PYTHON_ARGS\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["MICROCOSM_PYTHON"] = str(fake_python)
    env["MICROCOSM_FAKE_PYTHON_ARGS"] = str(argv_log)

    result = _run_bootstrap(env=env)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "Microcosm cold-clone probe passed",
        "suite: first-wave",
        "receipt: .microcosm/cold_clone_probe.json",
    ]
    assert argv_log.read_text(encoding="utf-8").splitlines() == [
        "-m",
        "microcosm_core.cold_clone_probe",
        "--suite",
        "first-wave",
        "--emit",
        ".microcosm/cold_clone_probe.json",
    ]
