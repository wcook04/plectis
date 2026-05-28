from __future__ import annotations

import subprocess
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _run_bootstrap(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["./bootstrap.sh", *args],
        cwd=MICROCOSM_ROOT,
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
    assert "receipts/cold_clone_probe.json" in result.stdout
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
