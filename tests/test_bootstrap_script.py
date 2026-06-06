from __future__ import annotations

import json
import os
import subprocess
import tomllib
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
    assert (
        "Usage: ./bootstrap.sh [--suite SUITE] [--emit RECEIPT_PATH] "
        "[--dry-run] [--version]"
        in result.stdout
    )
    assert "--suite SUITE" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--version" in result.stdout
    assert "first-wave" in result.stdout
    assert ".microcosm/cold_clone_probe.json" in result.stdout
    assert "Microcosm cold-clone probe passed" in result.stdout
    assert "receipt: <receipt path>" in result.stdout
    assert "next: README.md#public-repo-map and README.md#component-map" in result.stdout
    assert result.stderr == ""


def test_bootstrap_argument_errors_preserve_usage_boundary() -> None:
    unknown = _run_bootstrap("--bogus")
    missing_suite = _run_bootstrap("--suite")
    missing_emit = _run_bootstrap("--emit", "--suite")
    unknown_suite = _run_bootstrap("--suite", "missing-suite")

    assert unknown.returncode == 2
    assert "unknown argument: --bogus" in unknown.stderr
    assert "Usage: ./bootstrap.sh" in unknown.stderr

    assert missing_suite.returncode == 2
    assert "missing value for --suite" in missing_suite.stderr
    assert "Usage: ./bootstrap.sh" in missing_suite.stderr

    assert missing_emit.returncode == 2
    assert "missing value for --emit" in missing_emit.stderr
    assert "Usage: ./bootstrap.sh" in missing_emit.stderr

    assert unknown_suite.returncode == 2
    assert "unknown suite: missing-suite" in unknown_suite.stderr
    assert "supported suites: first-wave" in unknown_suite.stderr
    assert "Microcosm cold-clone probe passed" not in unknown_suite.stdout


def test_bootstrap_version_is_no_side_effect_public_entry() -> None:
    pyproject = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())

    result = _run_bootstrap("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == f"microcosm {pyproject['project']['version']}"
    assert result.stderr == ""


def test_bootstrap_dry_run_reports_command_without_running_probe(tmp_path: Path) -> None:
    argv_log = tmp_path / "fake_python_argv.txt"
    receipt = tmp_path / "dry_run_cold_clone_probe.json"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$@\" > \"$MICROCOSM_FAKE_PYTHON_ARGS\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["MICROCOSM_PYTHON"] = str(fake_python)
    env["MICROCOSM_FAKE_PYTHON_ARGS"] = str(argv_log)

    result = _run_bootstrap(
        "--suite",
        "first-wave",
        "--emit",
        str(receipt),
        "--dry-run",
        env=env,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "Microcosm cold-clone probe dry run",
        "suite: first-wave",
        f"receipt: {receipt}",
        f"python: {fake_python}",
        "pythonpath: src",
        (
            f"command: PYTHONPATH=src {fake_python} -m "
            f"microcosm_core.cold_clone_probe --suite first-wave "
            f"--emit {receipt}"
        ),
        "next: README.md#public-repo-map and README.md#component-map",
    ]
    assert not argv_log.exists()
    assert not receipt.exists()


def test_bootstrap_custom_emit_writes_bound_probe_receipt(tmp_path: Path) -> None:
    receipt = tmp_path / "cold_clone_probe_custom.json"
    env = os.environ.copy()
    env["MICROCOSM_RECEIPT_WRITES"] = "1"
    env["MICROCOSM_RUNTIME_RECEIPT_WRITES"] = "1"

    result = _run_bootstrap(
        "--suite",
        "first-wave",
        "--emit",
        str(receipt),
        env=env,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "Microcosm cold-clone probe passed",
        "suite: first-wave",
        f"receipt: {receipt}",
        "next: README.md#public-repo-map and README.md#component-map",
    ]
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "cold_clone_probe_receipt_v1"
    assert payload["status"] == "pass"
    assert payload["emit_ref"] == str(receipt)
    assert payload["receipt_paths"][0] == str(receipt)
    assert payload["command"] == (
        f"./bootstrap.sh --suite first-wave --emit {receipt}"
    )
    assert payload["secret_exclusion_scan"]["status"] == "pass"
    assert payload["private_state_scan"]["status"] == "pass"


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
        "next: README.md#public-repo-map and README.md#component-map",
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
        "next: README.md#public-repo-map and README.md#component-map",
    ]
    assert argv_log.read_text(encoding="utf-8").splitlines() == [
        "-m",
        "microcosm_core.cold_clone_probe",
        "--suite",
        "first-wave",
        "--emit",
        ".microcosm/cold_clone_probe.json",
    ]
