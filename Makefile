PYTHON ?= python3

.PHONY: install test smoke ci clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[test]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest

smoke:
	PYTHONPATH=src $(PYTHON) -m microcosm_core hello .
	PYTHONPATH=src $(PYTHON) -m microcosm_core --version
	PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard

ci: install test smoke

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
