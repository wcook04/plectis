from __future__ import annotations

import re
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = MICROCOSM_ROOT / "Makefile"


def test_public_repo_makefile_exposes_standard_command_surface() -> None:
    assert MAKEFILE.is_file()

    text = MAKEFILE.read_text(encoding="utf-8")

    for required in (
        "PYTHON ?= python3",
        "PUBLIC_TESTS ?=",
        ".PHONY: install test test-all smoke ci clean",
        "$(PYTHON) -m pip install --upgrade pip",
        '$(PYTHON) -m pip install -e ".[test]"',
        "PYTHONPATH=src $(PYTHON) -m pytest $(PUBLIC_TESTS)",
        "PYTHONPATH=src $(PYTHON) -m pytest",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core hello .",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core --version",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard",
    ):
        assert required in text

    for target in ("install", "test", "test-all", "smoke", "ci", "clean"):
        assert re.search(rf"^{target}:", text, flags=re.MULTILINE)


def test_public_repo_makefile_ci_target_is_test_plus_smoke() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")

    assert re.search(r"^ci:\s+test\s+smoke$", text, flags=re.MULTILINE)
    assert "test-all: install" in text
    assert "microcosm_core.cli" not in text
