"""The commands on the first screen have to run, not just read well.

Every other guard on README.md and QUICKSTART.md checks that a command is
*present*. That is what let `python3 -m pip install .` sit as the first
runnable line for as long as it did: the string was there, three tests
asserted it was there, and it had not worked on a stock macOS or Debian
`python3` since PEP 668 shipped. A cold reader's first command returned
`error: externally-managed-environment` and nothing in the repository
noticed, because nothing in the repository ran it.

So this module executes the documented first-contact route instead of
matching it, and separately refuses any first-screen command that installs
into the interpreter the reader's operating system depends on.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIRST_CONTACT_DOCS = ("README.md", "QUICKSTART.md")

# The documented no-install invocation, spelled exactly as the docs spell it.
SOURCE_FORM_PREFIX = "PYTHONPATH=src python3 -m plectis"


def _bash_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:bash|sh)\n(.*?)```", text, flags=re.DOTALL)


def _command_lines(text: str) -> list[str]:
    lines: list[str] = []
    for block in _bash_blocks(text):
        for raw in block.splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def test_no_documented_command_installs_into_the_system_interpreter() -> None:
    """`pip install` is legal only inside an environment the reader created.

    `python3 -m pip install .` is not a style preference — it is refused
    outright by Homebrew, Debian, and Ubuntu Python, which is what a reader
    arriving from GitHub actually has. An install command is acceptable here
    only when it routes through a virtual environment (`.venv/bin/python`),
    the Makefile's own environment, or an explicit example of the refusal.
    """
    offenders: list[str] = []
    for name in FIRST_CONTACT_DOCS:
        for line in _command_lines((MICROCOSM_ROOT / name).read_text(encoding="utf-8")):
            if "pip install" not in line:
                continue
            isolated = (
                line.startswith(".venv/")
                or line.startswith("make ")
                or "$(VENV_PYTHON)" in line
                or "-m venv" in line
            )
            if not isolated:
                offenders.append(f"{name}: {line}")
    assert not offenders, (
        "first-contact docs install into the reader's system interpreter, which "
        f"PEP 668 refuses: {offenders}"
    )


def test_first_runnable_readme_block_needs_no_install() -> None:
    """The first thing a reader is told to run must work on a bare clone."""
    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    blocks = _bash_blocks(readme)
    assert blocks, "README lost its runnable blocks"

    first = blocks[0]
    assert "git clone" in first
    assert SOURCE_FORM_PREFIX in first, (
        "the README's first runnable block no longer offers a route that works "
        "before anything is installed"
    )
    assert "pip install" not in first


def test_every_hero_command_works_before_anything_is_installed() -> None:
    """Not just the first one. Every command above the first heading.

    The check above tests `blocks[0]`, and on 2026-08-16 that was enough to
    call the front door repaired. It was not. Four paragraphs further down,
    still on the first screen and still above any heading, the README offered

        plectis comprehend --slice papers --format text

    which is the installed alias — for the install the same screen had just
    described as optional. A cold clone answered it with exit 127, and nothing
    noticed, because the evaluator written that morning to prove the documented
    route runs only ever ran the first block of it.

    A hero that says "no install" owes that promise to every command it
    contains, so this walks all of them.
    """
    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    hero = readme.split("\n## ", 1)[0]
    offenders = [
        line
        for line in _command_lines(hero)
        if line.startswith("plectis ") or line.startswith("./plectis")
    ]
    assert not offenders, (
        "the first screen promises a route that needs no install, then uses the "
        f"installed alias, which exits 127 on a fresh clone: {offenders}. Use "
        f"{SOURCE_FORM_PREFIX!r}, or move the command below the Install section."
    )


def test_documented_source_form_route_actually_runs(tmp_path: Path) -> None:
    """Run the documented no-install command end to end on a fresh project.

    This is the check that would have caught the PEP 668 failure: it runs the
    route a cold reader is given, against a project it has never seen, with no
    install step and no inherited environment.
    """
    project = tmp_path / "sample-project"
    project.mkdir()
    (project / "README.md").write_text("# Sample\n\nA small project.\n", encoding="utf-8")
    (project / "main.py").write_text("def main() -> int:\n    return 0\n", encoding="utf-8")

    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "PYTHONHOME"}
    }
    # `PYTHONPATH=src` as documented, resolved against the clone root the same
    # way a reader's shell would resolve it from inside the clone.
    env["PYTHONPATH"] = str(MICROCOSM_ROOT / "src")

    for verb in (["hello", str(project)], ["tour", "--format", "text", str(project)]):
        completed = subprocess.run(
            [sys.executable, "-m", "plectis", *verb],
            cwd=MICROCOSM_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert completed.returncode == 0, (
            f"documented source-form route failed for {verb[0]!r}: "
            f"rc={completed.returncode}\n{completed.stdout[-2000:]}\n"
            f"{completed.stderr[-2000:]}"
        )
        assert completed.stdout.strip(), f"{verb[0]!r} produced no output"

    # The run left a record beside the project and did not touch its source.
    assert (project / ".microcosm").is_dir()
    assert (project / "main.py").read_text(encoding="utf-8") == (
        "def main() -> int:\n    return 0\n"
    )


def test_pep668_refusal_is_named_where_a_reader_would_hit_it() -> None:
    """A reader who hits the refusal must be able to tell it apart from a bug."""
    quickstart = (MICROCOSM_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    for name, text in (("QUICKSTART.md", quickstart), ("README.md", readme)):
        assert "externally-managed-environment" in text, name
        assert "https://peps.python.org/pep-0668/" in text, name
