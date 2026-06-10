PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON ?= $(VENV)/bin/python
PIP_CACHE_DIR ?= $(VENV)/.pip-cache
PIP_ENV ?= PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_CACHE_DIR=$(PIP_CACHE_DIR)
EXPORT_OUT ?= ../microcosm-substrate-export
SMOKE_OUT ?= .microcosm/smoke
SMOKE_ENV ?= MICROCOSM_RUNTIME_RECEIPT_WRITES=0
FLIGHT_RECORDER_OUT ?= .microcosm/skeptic-flight-recorder
FLIGHT_RECORDER_VERIFY_DIR ?= $(FLIGHT_RECORDER_OUT)
TMPDIR ?= /tmp
PYTEST_TMP_KEY ?= $(shell $(PYTHON) -c 'import hashlib, os; print(hashlib.sha256(os.getcwd().encode()).hexdigest()[:12])')
PYTEST_TMP_KEY := $(PYTEST_TMP_KEY)
PYTEST_TMP_ROOT ?= $(TMPDIR)/microcosm-substrate-test-tmp-$(PYTEST_TMP_KEY)
PYTEST_RUN_ID ?= $(shell $(PYTHON) -c 'import os, time; print("%s-%s" % (os.getpid(), time.time_ns()))')
PYTEST_RUN_ID := $(PYTEST_RUN_ID)
PYTEST_TMP ?= $(PYTEST_TMP_ROOT)/run-$(PYTEST_RUN_ID)
PYTEST_BASETEMP ?= $(PYTEST_TMP)/pytest
PYTEST_ENV ?= PYTHONPYCACHEPREFIX=$(PYTEST_TMP)/pycache TMPDIR=$(PYTEST_TMP)/tmp
PYTEST_KEEP_TMP ?= 0
PYTEST_ARGS ?=
PACKAGE_SMOKE_TMP_ROOT ?= $(TMPDIR)/microcosm-substrate-package-smoke-$(PYTEST_TMP_KEY)
PACKAGE_SMOKE_TMP ?= $(PACKAGE_SMOKE_TMP_ROOT)/run-$(PYTEST_RUN_ID)
PACKAGE_SMOKE_KEEP_TMP ?= 0
.DEFAULT_GOAL := help
PUBLIC_TESTS ?= \
	tests/test_public_entry_docs.py \
	tests/test_secret_exclusion_scan.py \
	tests/test_private_state_scan.py \
	tests/test_public_repo_ci.py \
	tests/test_public_repo_makefile.py \
	tests/test_package_data_contract.py \
	tests/test_readme_first_screen_entry.py \
	tests/test_observatory_browser_styles.py \
	tests/test_proof_lab_cache_action_hint.py \
	tests/test_proof_lab_card.py \
	tests/test_batch12_release_claim_language_gate.py \
	tests/test_evidence_truth_floor.py \
	tests/test_release_export.py \
	tests/test_first_action_demo.py
PUBLIC_TESTS += tests/test_substrate_substitution_ledger.py

.PHONY: help install venv test test-all smoke package-smoke ci standalone-export clean
.PHONY: doctrine-lattice-check doctrine-lattice-entry-card
.PHONY: flight-recorder flight-recorder-verify
.PHONY: check preflight validate

help:
	@printf '%s\n' \
		"Microcosm public repo commands:" \
		"  make install             create .venv and install test extras" \
		"  make test                run public entry and safety tests" \
		"  make test-all            run full suite with pytest receipt writes blocked" \
		"  make smoke               validate and summarize the public smoke route" \
		"  make flight-recorder     write a public-safe evaluator proof packet" \
		"  make flight-recorder-verify verify an existing flight-recorder packet" \
		"  make package-smoke       install local package in a fresh venv and run console cards" \
		"  make ci                  run test, smoke, and package-smoke" \
		"  make check               fast preflight: organ evidence-class registry integrity" \
		"  make validate            full pre-commit floor: ci + doctrine-lattice drift check" \
		"  make standalone-export   export a release-gated standalone tree" \
		"  make doctrine-lattice-check check generated doctrine-lattice coverage" \
		"  make doctrine-lattice-entry-card write generated doctrine-lattice agent entry card" \
		"  make clean               remove local build and cache files"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON)

install: $(VENV_PYTHON)
	$(PIP_ENV) $(VENV_PYTHON) -m pip install --upgrade pip
	$(PIP_ENV) $(VENV_PYTHON) -m pip install -e ".[test]"

test: install
	@mkdir -p $(PYTEST_TMP)/tmp $(PYTEST_TMP)/pycache
	@status=0; PYTHONPATH=src $(PYTEST_ENV) $(VENV_PYTHON) -m pytest --basetemp=$(PYTEST_BASETEMP) $(PUBLIC_TESTS) $(PYTEST_ARGS) || status=$$?; if [ "$(PYTEST_KEEP_TMP)" != "1" ]; then rm -rf "$(PYTEST_TMP)"; fi; exit $$status

test-all: install
	@printf '%s\n' "Note: make test-all is a broad macro-root drift-detection suite with tracked receipt writes blocked under pytest. Use make ci for the clean public verification floor."
	@mkdir -p $(PYTEST_TMP)/tmp $(PYTEST_TMP)/pycache
	@status=0; PYTHONPATH=src $(PYTEST_ENV) $(VENV_PYTHON) -m pytest --basetemp=$(PYTEST_BASETEMP) $(PYTEST_ARGS) || status=$$?; if [ "$(PYTEST_KEEP_TMP)" != "1" ]; then rm -rf "$(PYTEST_TMP)"; fi; exit $$status

smoke:
	@mkdir -p $(SMOKE_OUT)
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core hello . > $(SMOKE_OUT)/hello.txt
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core first-screen --card . > $(SMOKE_OUT)/first-screen-card.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core tour --card . > $(SMOKE_OUT)/tour-card.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core status --card . > $(SMOKE_OUT)/status-card.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) scripts/served_status_smoke.py --root . --project . --out $(SMOKE_OUT)/served-status-card.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core authority --card > $(SMOKE_OUT)/authority-card.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core workingness --card > $(SMOKE_OUT)/workingness-card.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core legibility-scorecard > $(SMOKE_OUT)/legibility-scorecard.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core comprehend --first-action "where do I start with this clone?" > $(SMOKE_OUT)/first-action.json
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core --version > $(SMOKE_OUT)/version.txt
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard > $(SMOKE_OUT)/stripping-guard.json
	@$(PYTHON) scripts/check_smoke_outputs.py --smoke-out $(SMOKE_OUT)

flight-recorder:
	@mkdir -p $(FLIGHT_RECORDER_OUT)
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) scripts/skeptic_flight_recorder.py --root . --out $(FLIGHT_RECORDER_OUT) --python $(PYTHON)

flight-recorder-verify:
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) scripts/skeptic_flight_recorder.py verify $(FLIGHT_RECORDER_VERIFY_DIR) --root .

package-smoke:
	@status=0; $(PYTHON) scripts/package_install_smoke.py --source-root . --work-dir $(PACKAGE_SMOKE_TMP) --python $(PYTHON) || status=$$?; if [ "$(PACKAGE_SMOKE_KEEP_TMP)" != "1" ]; then rm -rf "$(PACKAGE_SMOKE_TMP)"; fi; exit $$status

ci: test smoke package-smoke

check preflight:
	@$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -c "from microcosm_core.runtime_shell import _load_evidence_class_registry; from pathlib import Path; _load_evidence_class_registry(Path('.'))"
	@printf '%s\n' "Microcosm preflight: organ evidence-class registry loads cleanly."

validate: ci doctrine-lattice-check

standalone-export: install
	PYTHONPATH=src $(VENV_PYTHON) -m microcosm_core.release_export --root . --out $(EXPORT_OUT) --force --summary

doctrine-lattice-check:
	PYTHONPATH=src $(PYTHON) -m microcosm_core doctrine-lattice check --root .

doctrine-lattice-entry-card:
	PYTHONPATH=src $(PYTHON) -m microcosm_core doctrine-lattice write-entry-card --root .

clean:
	rm -rf $(SMOKE_OUT) $(PYTEST_TMP_ROOT) $(PACKAGE_SMOKE_TMP_ROOT) .microcosm/test-tmp .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
