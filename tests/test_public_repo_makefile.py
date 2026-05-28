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
        "VENV ?= .venv",
        "VENV_PYTHON ?= $(VENV)/bin/python",
        "PUBLIC_TESTS ?=",
        ".PHONY: install venv test test-all smoke ci clean",
        "$(PYTHON) -m venv $(VENV)",
        "$(VENV_PYTHON) -m pip install --upgrade pip",
        '$(VENV_PYTHON) -m pip install -e ".[test]"',
        "PYTHONPATH=src $(VENV_PYTHON) -m pytest $(PUBLIC_TESTS)",
        "PYTHONPATH=src $(VENV_PYTHON) -m pytest",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core hello .",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core tour --card .",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core status --card .",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core authority --card",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core workingness --card",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core legibility-scorecard",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core --version",
        "PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard",
    ):
        assert required in text

    for target in ("venv", "install", "test", "test-all", "smoke", "ci", "clean"):
        assert re.search(rf"^{target}:", text, flags=re.MULTILINE)

    assert "--break-system-packages" not in text


def test_public_repo_makefile_ci_target_is_test_plus_smoke() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")

    assert re.search(r"^ci:\s+test\s+smoke$", text, flags=re.MULTILINE)
    assert "test-all: install" in text
    assert "microcosm_core.cli" not in text
