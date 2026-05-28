PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON ?= $(VENV)/bin/python
PIP_CACHE_DIR ?= $(VENV)/.pip-cache
PIP_ENV ?= PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_CACHE_DIR=$(PIP_CACHE_DIR)
EXPORT_OUT ?= ../microcosm-substrate-export
SMOKE_OUT ?= .microcosm/smoke
TMPDIR ?= /tmp
PYTEST_TMP_KEY ?= $(shell $(PYTHON) -c 'import hashlib, os; print(hashlib.sha256(os.getcwd().encode()).hexdigest()[:12])')
PYTEST_TMP ?= $(TMPDIR)/microcosm-substrate-test-tmp-$(PYTEST_TMP_KEY)
PYTEST_BASETEMP ?= $(PYTEST_TMP)/pytest
PYTEST_ENV ?= PYTHONPYCACHEPREFIX=$(PYTEST_TMP)/pycache TMPDIR=$(PYTEST_TMP)/tmp
PYTEST_ARGS ?=
.DEFAULT_GOAL := help
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

.PHONY: help install venv test test-all smoke ci standalone-export clean

help:
	@printf '%s\n' \
		"Microcosm public repo commands:" \
		"  make install             create .venv and install test extras" \
		"  make test                run public entry and safety tests" \
		"  make test-all            run macro-root suite; may refresh tracked receipts" \
		"  make smoke               run the first-screen CLI smoke route" \
		"  make ci                  run test plus smoke" \
		"  make standalone-export   export a release-gated standalone tree" \
		"  make clean               remove local build and cache files"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON)

install: $(VENV_PYTHON)
	$(PIP_ENV) $(VENV_PYTHON) -m pip install --upgrade pip
	$(PIP_ENV) $(VENV_PYTHON) -m pip install -e ".[test]"

test: install
	@mkdir -p $(PYTEST_TMP)/tmp $(PYTEST_TMP)/pycache
	PYTHONPATH=src $(PYTEST_ENV) $(VENV_PYTHON) -m pytest --basetemp=$(PYTEST_BASETEMP) $(PUBLIC_TESTS) $(PYTEST_ARGS)

test-all: install
	@printf '%s\n' "Note: make test-all is a macro-root drift-refresh suite and may update tracked generated receipts/projections. Use make ci for the clean public verification floor."
	@mkdir -p $(PYTEST_TMP)/tmp $(PYTEST_TMP)/pycache
	PYTHONPATH=src $(PYTEST_ENV) $(VENV_PYTHON) -m pytest --basetemp=$(PYTEST_BASETEMP) $(PYTEST_ARGS)

smoke:
	@mkdir -p $(SMOKE_OUT)
	@PYTHONPATH=src $(PYTHON) -m microcosm_core hello . > $(SMOKE_OUT)/hello.txt
	@PYTHONPATH=src $(PYTHON) -m microcosm_core tour --card . > $(SMOKE_OUT)/tour-card.json
	@PYTHONPATH=src $(PYTHON) -m microcosm_core status --card . > $(SMOKE_OUT)/status-card.json
	@PYTHONPATH=src $(PYTHON) -m microcosm_core authority --card > $(SMOKE_OUT)/authority-card.json
	@PYTHONPATH=src $(PYTHON) -m microcosm_core workingness --card > $(SMOKE_OUT)/workingness-card.json
	@PYTHONPATH=src $(PYTHON) -m microcosm_core legibility-scorecard > $(SMOKE_OUT)/legibility-scorecard.json
	@PYTHONPATH=src $(PYTHON) -m microcosm_core --version > $(SMOKE_OUT)/version.txt
	@PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard > $(SMOKE_OUT)/stripping-guard.json
	@printf 'Microcosm smoke receipts written to %s\n' "$(SMOKE_OUT)"

ci: test smoke

standalone-export: install
	PYTHONPATH=src $(VENV_PYTHON) -m microcosm_core.release_export --root . --out $(EXPORT_OUT) --force

clean:
	rm -rf $(SMOKE_OUT) $(PYTEST_TMP) .microcosm/test-tmp .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
