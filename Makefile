PYTHON ?= python3
PUBLIC_TESTS ?= \
	tests/test_public_entry_docs.py \
	tests/test_secret_exclusion_scan.py \
	tests/test_private_state_scan.py \
	tests/test_public_repo_ci.py \
	tests/test_public_repo_makefile.py \
	tests/test_release_export.py

.PHONY: install test test-all smoke ci clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[test]"

test: install
	PYTHONPATH=src $(PYTHON) -m pytest $(PUBLIC_TESTS)

test-all: install
	PYTHONPATH=src $(PYTHON) -m pytest

smoke:
	PYTHONPATH=src $(PYTHON) -m microcosm_core hello .
	PYTHONPATH=src $(PYTHON) -m microcosm_core --version
	PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard

ci: test smoke

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
