"""Published markdown tables must fit the column GitHub renders them in.

GitHub renders markdown into a 1012px content column, and a table has no
wrapping escape. A long file path or identifier in a cell has no break
opportunity anywhere in it, so it pushes the table past the column and the
reader gets a horizontal scrollbar with every other column squashed into a
sliver. `<wbr>` and `style` are both stripped by GitHub's sanitiser, so there is
no markup or CSS fix — the only fix is structural, and the only guard is a check.

Exported bundles are excluded: they are byte-identical frozen copies of upstream
sources, and the refresh boundary owns them. Fixing one here would break the
copy check; it has to be fixed upstream and re-exported.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
CHECKER = MICROCOSM_ROOT / "scripts" / "check_markdown_table_render.py"

# Surfaces a reader actually opens, and which we own outright.
GUARDED = [
    "README.md",
    "ORGANS.md",
    "AGENT_ROUTES.md",
    "ARCHITECTURE.md",
    "FIRST_ACTION.md",
    "ANTI_PRINCIPLES.md",
    "RELEASE_REVIEW.md",
    "paper_modules",
    "docs",
]


def test_checker_is_present():
    assert CHECKER.exists(), f"missing {CHECKER}"


def test_guarded_markdown_fits_the_rendered_column():
    targets = [str(MICROCOSM_ROOT / p) for p in GUARDED if (MICROCOSM_ROOT / p).exists()]
    assert targets, "no guarded markdown surfaces found"
    proc = subprocess.run(
        [sys.executable, str(CHECKER), "--fail-on", "overflow", *targets],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "markdown table(s) exceed GitHub's 1012px content column, so they render "
        "with a horizontal scrollbar:\n\n" + proc.stdout
    )


def test_no_stripped_or_copy_breaking_markup():
    """`<wbr>` is stripped by GitHub so it is dead weight; zero-width spaces and
    soft hyphens survive but corrupt copy-paste of paths and identifiers."""
    offenders = []
    for path in MICROCOSM_ROOT.rglob("*.md"):
        if "exported_" in str(path) or "/.git/" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in ("<wbr>", "&shy;", "​"):
            if token in text:
                offenders.append(f"{path.relative_to(MICROCOSM_ROOT)}: {token!r}")
    assert not offenders, "\n".join(offenders)
