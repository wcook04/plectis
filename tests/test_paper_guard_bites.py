# SPDX-FileCopyrightText: 2026 Will Cook
# SPDX-License-Identifier: CC-BY-4.0
"""Prove that the paper's self-check still catches false facts.

``scripts/check_public_system_paper.py`` mixes two kinds of check. Some verify
*facts* --- that a count in the paper matches the registry, that a pinned commit
is the one described, that the reported test results match the stored receipt.
Others require particular *phrasings* to be present, so that specific honesty
commitments cannot quietly leave the prose.

The two kinds have different standing. A phrasing anchor may legitimately be
re-pointed when the paper is rewritten. A fact check may not: weakening one to
make a rewrite pass would turn the guard into decoration, and the paper's own
argument would then rest on a check that no longer checks anything --- exactly
the failure the paper reports finding elsewhere in this repository.

This test defends the distinction mechanically. It corrupts one fact at a time
and asserts the guard notices. If someone later relaxes a fact check, this test
fails even if the paper itself still passes.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "plectis-public-system.tex"
CHECKER = ROOT / "scripts" / "check_public_system_paper.py"

# Each case corrupts one fact the guard is responsible for. The pair is
# (original macro definition, corrupted macro definition).
FACT_MUTATIONS = [
    pytest.param(
        r"\newcommand{\componentcount}{88}",
        r"\newcommand{\componentcount}{87}",
        id="component-count",
    ),
    pytest.param(
        r"\newcommand{\leanfilecount}{58}",
        r"\newcommand{\leanfilecount}{57}",
        id="lean-file-count",
    ),
    pytest.param(
        r"\newcommand{\mathcount}{20}",
        r"\newcommand{\mathcount}{19}",
        id="family-count",
    ),
    pytest.param(
        r"\newcommand{\copiedsourcecount}{21}",
        r"\newcommand{\copiedsourcecount}{22}",
        id="evidence-route-count",
    ),
    pytest.param(
        r"\newcommand{\snapshotshort}{57ffb7f5830c}",
        r"\newcommand{\snapshotshort}{57ffb7f5830d}",
        id="pinned-commit",
    ),
]


def _failure_count() -> int:
    """Run the guard and return how many failures it reports."""
    proc = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr
    if "check: pass" in output:
        return 0
    match = re.search(r"(\d+) failure", output)
    if match is None:
        raise AssertionError(f"cannot read a failure count from guard output:\n{output}")
    return int(match.group(1))


@pytest.fixture
def paper_text():
    """Restore the paper verbatim however the test exits."""
    original = PAPER.read_text()
    try:
        yield original
    finally:
        PAPER.write_text(original)


@pytest.mark.parametrize("truth,lie", FACT_MUTATIONS)
def test_guard_catches_a_corrupted_fact(paper_text, truth, lie):
    baseline = _failure_count()

    assert truth in paper_text, (
        f"the macro {truth!r} is no longer in the paper, so this test is not "
        "exercising anything. Update the mutation rather than deleting it."
    )

    PAPER.write_text(paper_text.replace(truth, lie))
    corrupted = _failure_count()

    assert corrupted > baseline, (
        f"corrupting {truth!r} to {lie!r} did not increase the guard's failure "
        f"count ({baseline} -> {corrupted}). A fact check has been weakened or "
        "removed."
    )
