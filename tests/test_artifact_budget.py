"""The shipped distribution footprint stays under an explicit budget.

Plectis presents as a small offline tool but ships a large evidence/research
corpus via ``[tool.setuptools.data-files]``. ``scripts/check_artifact_budget.py``
measures that footprint from the manifest (no build backend needed) and bounds
it. These tests pin three things: the budget is set, the current artifact is
within it, and the brake actually bites when the corpus grows past the ceiling.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_artifact_budget.py"


def _load_budget_module():
    spec = importlib.util.spec_from_file_location("check_artifact_budget", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


budget_mod = _load_budget_module()


def test_budget_is_explicitly_set() -> None:
    budget = budget_mod.ARTIFACT_BUDGET
    assert budget["max_total_bytes"] > 0
    assert budget["max_total_files"] > 0
    assert budget["max_data_files_bytes"] > 0


def test_current_footprint_is_within_budget() -> None:
    stats = budget_mod.measure()
    failures = budget_mod._check(stats)
    assert failures == [], failures
    # The artifact is really being measured, not silently resolving to empty.
    assert stats["total_files"] > 100
    assert stats["data_files_bytes"] > 0
    assert stats["runtime_package_files"] > 0


def test_check_cli_passes_at_current_footprint() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Plectis artifact budget: pass" in result.stdout


def test_budget_rejects_corpus_growth_past_ceiling() -> None:
    # Greenwash-resistance: a footprint over any ceiling must fail the check, so
    # the guard is a real brake and not a no-op that rides a green CI.
    budget = budget_mod.ARTIFACT_BUDGET
    over_budget = {
        "total_bytes": budget["max_total_bytes"] + 1,
        "total_files": budget["max_total_files"] + 1,
        "data_files_bytes": budget["max_data_files_bytes"] + 1,
        "runtime_package_files": 0,
        "runtime_package_bytes": 0,
        "data_files_count": 0,
        "by_category": {},
    }
    failures = budget_mod._check(over_budget)
    assert failures
    assert any("exceeds budget" in failure for failure in failures)


def test_unset_budget_is_rejected() -> None:
    # A zeroed budget must not silently pass: an unset ceiling is a failure, not
    # an opt-out.
    stats = budget_mod.measure()
    original = dict(budget_mod.ARTIFACT_BUDGET)
    try:
        budget_mod.ARTIFACT_BUDGET["max_total_bytes"] = 0
        failures = budget_mod._check(stats)
        assert failures
        assert any("unset" in failure for failure in failures)
    finally:
        budget_mod.ARTIFACT_BUDGET.update(original)


def test_brake_stays_meaningful() -> None:
    # The ceiling cannot be neutered into uselessness: it must stay within a
    # small multiple of the current footprint, so a bulk corpus import is caught
    # rather than silently absorbed.
    stats = budget_mod.measure()
    assert budget_mod.ARTIFACT_BUDGET["max_total_bytes"] < 2 * int(stats["total_bytes"])
