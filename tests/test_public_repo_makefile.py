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
        "PIP_CACHE_DIR ?= $(VENV)/.pip-cache",
        "PIP_ENV ?= PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_CACHE_DIR=$(PIP_CACHE_DIR)",
        "EXPORT_OUT ?= ../microcosm-substrate-export",
        "SMOKE_OUT ?= .microcosm/smoke",
        ".DEFAULT_GOAL := help",
        "PUBLIC_TESTS ?=",
        ".PHONY: help install venv test test-all smoke ci standalone-export clean",
        "Microcosm public repo commands:",
        "make install             create .venv and install test extras",
        "make test                run public entry and safety tests",
        "make test-all            run the full local test suite",
        "make smoke               run the first-screen CLI smoke route",
        "make ci                  run test plus smoke",
        "make standalone-export   export a release-gated standalone tree",
        "make clean               remove local build and cache files",
        "$(PYTHON) -m venv $(VENV)",
        "$(PIP_ENV) $(VENV_PYTHON) -m pip install --upgrade pip",
        '$(PIP_ENV) $(VENV_PYTHON) -m pip install -e ".[test]"',
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
        "> $(SMOKE_OUT)/tour-card.json",
        "> $(SMOKE_OUT)/status-card.json",
        "> $(SMOKE_OUT)/stripping-guard.json",
        "Microcosm smoke receipts written to %s",
        "PYTHONPATH=src $(VENV_PYTHON) -m microcosm_core.release_export --root . --out $(EXPORT_OUT) --force",
        "rm -rf $(SMOKE_OUT)",
    ):
        assert required in text

    for target in (
        "help",
        "venv",
        "install",
        "test",
        "test-all",
        "smoke",
        "ci",
        "standalone-export",
        "clean",
    ):
        assert re.search(rf"^{target}:", text, flags=re.MULTILINE)

    assert "--break-system-packages" not in text
    assert "PIP_DISABLE_PIP_VERSION_CHECK=1" in text
    assert "/Library/Caches/pip" not in text


def test_public_repo_makefile_ci_target_is_test_plus_smoke() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")

    assert re.search(r"^ci:\s+test\s+smoke$", text, flags=re.MULTILINE)
    assert "test-all: install" in text
    assert not re.search(r"^ci:.*standalone-export", text, flags=re.MULTILINE)
    assert "microcosm_core.cli" not in text
