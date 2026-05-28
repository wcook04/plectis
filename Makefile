PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON ?= $(VENV)/bin/python
PUBLIC_TESTS ?= \
	tests/test_public_entry_docs.py \
	tests/test_secret_exclusion_scan.py \
	tests/test_private_state_scan.py \
	tests/test_public_repo_ci.py \
	tests/test_public_repo_makefile.py \
	tests/test_readme_first_screen_entry.py \
	tests/test_observatory_browser_styles.py \
	tests/test_proof_lab_cache_action_hint.py \
	tests/test_release_export.py

.PHONY: install venv test test-all smoke ci clean

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON)

install: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[test]"

test: install
	PYTHONPATH=src $(VENV_PYTHON) -m pytest $(PUBLIC_TESTS)

test-all: install
	PYTHONPATH=src $(VENV_PYTHON) -m pytest

smoke:
	PYTHONPATH=src $(PYTHON) -m microcosm_core hello .
	PYTHONPATH=src $(PYTHON) -m microcosm_core tour --card .
	PYTHONPATH=src $(PYTHON) -m microcosm_core status --card .
	PYTHONPATH=src $(PYTHON) -m microcosm_core authority --card
	PYTHONPATH=src $(PYTHON) -m microcosm_core workingness --card
	PYTHONPATH=src $(PYTHON) -m microcosm_core legibility-scorecard
	PYTHONPATH=src $(PYTHON) -m microcosm_core --version
	PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard

ci: test smoke

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
