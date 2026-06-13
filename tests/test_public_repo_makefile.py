from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = MICROCOSM_ROOT / "Makefile"
CHECK_SMOKE_OUTPUTS = MICROCOSM_ROOT / "scripts" / "check_smoke_outputs.py"
PACKAGE_INSTALL_SMOKE = MICROCOSM_ROOT / "scripts" / "package_install_smoke.py"


def _accepted_organ_count(root: Path = MICROCOSM_ROOT) -> int:
    registry = json.loads((root / "core/organ_registry.json").read_text(encoding="utf-8"))
    return sum(
        1
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _live_workingness_import_signature() -> dict[str, object]:
    env = os.environ.copy()
    src_path = str(MICROCOSM_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else os.pathsep.join([src_path, env["PYTHONPATH"]])
    )
    result = subprocess.run(
        [sys.executable, "-m", "microcosm_core", "workingness", "--card"],
        cwd=MICROCOSM_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    preview = payload["source_body_import_exception_preview"]
    surface_counts = payload["surface_counts"]
    return {
        "source_body_import_exception_count": preview["count"],
        "source_body_import_exception_status": preview["status"],
        "rows_with_source_body_imports": surface_counts["rows_with_source_body_imports"],
        "source_open_body_material_count": surface_counts["source_open_body_material_count"],
    }


def _write_valid_smoke_outputs(smoke_out: Path) -> None:
    accepted_organ_count = _accepted_organ_count()
    workingness_import_signature = _live_workingness_import_signature()
    smoke_out.mkdir(parents=True)
    (smoke_out / "hello.txt").write_text(
        "Microcosm first screen\n",
        encoding="utf-8",
    )
    (smoke_out / "version.txt").write_text("microcosm 0.1.0\n", encoding="utf-8")
    _write_json(smoke_out / "first-screen-card.json", {"status": "pass"})
    _write_json(
        smoke_out / "tour-card.json",
        {
            "card_status": "clear",
            "status": "pass",
        },
    )
    _write_json(smoke_out / "status-card.json", {"status": "pass"})
    _write_json(
        smoke_out / "served-status-card.json",
        {
            "private_path_hit_count": 0,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "status": "pass",
        },
    )
    _write_json(
        smoke_out / "authority-card.json",
        {
            "authority_ceiling": {"release_authorized": False},
            "status": "pass",
            "surface_counts": {"organ_authority_count": accepted_organ_count},
            "unsafe_payload_bodies_exported": False,
        },
    )
    _write_json(
        smoke_out / "workingness-card.json",
        {
            "authority_ceiling": {"release_authorized": False},
            "card_status": "clear",
            "status": "pass",
            "source_body_import_exception_preview": {
                "count": workingness_import_signature[
                    "source_body_import_exception_count"
                ],
                "rows": [],
                "status": workingness_import_signature[
                    "source_body_import_exception_status"
                ],
            },
            "surface_counts": {
                "mapped_organ_count": accepted_organ_count,
                "missing_failure_modes_count": 0,
                "missing_standard_count": 0,
                "rows_with_source_body_imports": workingness_import_signature[
                    "rows_with_source_body_imports"
                ],
                "source_open_body_material_count": workingness_import_signature[
                    "source_open_body_material_count"
                ],
            },
        },
    )
    _write_json(
        smoke_out / "legibility-scorecard.json",
        {
            "release_authorized": False,
            "status": "pass",
            "unsafe_payload_bodies_in_receipt": False,
        },
    )
    _write_json(
        smoke_out / "stripping-guard.json",
        {
            "release_authorized": False,
            "status": "pass",
            "unsafe_payload_bodies_in_receipt": False,
        },
    )
    _write_json(
        smoke_out / "first-action.json",
        {
            "found": True,
            "first_action": {
                "command": (
                    "PYTHONPATH=src python3 -m microcosm_core "
                    "cold-reader-route-map run-route-map-bundle "
                    "--input fixtures/first_wave/cold_reader_route_map/input "
                    "--out .microcosm/first_action_runs/cold_reader_route_map"
                ),
            },
            "proof_path": {
                "runnable_validator": (
                    "PYTHONPATH=src python3 -m microcosm_core "
                    "cold-reader-route-map run-route-map-bundle "
                    "--input fixtures/first_wave/cold_reader_route_map/input "
                    "--out .microcosm/first_action_runs/cold_reader_route_map"
                ),
            },
            "reading_boundary": {"stop_condition": "stop at the route boundary"},
            "do_not_claim": "navigation metadata only",
        },
    )


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
        "SMOKE_ENV ?= MICROCOSM_RUNTIME_RECEIPT_WRITES=0",
        "TMPDIR ?= /tmp",
        "PYTEST_TMP_KEY ?= $(shell $(PYTHON) -c 'import hashlib, os; print(hashlib.sha256(os.getcwd().encode()).hexdigest()[:12])')",
        "PYTEST_TMP_KEY := $(PYTEST_TMP_KEY)",
        "PYTEST_TMP_ROOT ?= $(TMPDIR)/microcosm-substrate-test-tmp-$(PYTEST_TMP_KEY)",
        'PYTEST_RUN_ID ?= $(shell $(PYTHON) -c \'import os, time; print("%s-%s" % (os.getpid(), time.time_ns()))\')',
        "PYTEST_RUN_ID := $(PYTEST_RUN_ID)",
        "PYTEST_TMP ?= $(PYTEST_TMP_ROOT)/run-$(PYTEST_RUN_ID)",
        "PYTEST_BASETEMP ?= $(PYTEST_TMP)/pytest",
        "PYTEST_ENV ?= PYTHONPYCACHEPREFIX=$(PYTEST_TMP)/pycache TMPDIR=$(PYTEST_TMP)/tmp",
        "PYTEST_KEEP_TMP ?= 0",
        "PYTEST_ARGS ?=",
        "PACKAGE_SMOKE_TMP_ROOT ?= $(TMPDIR)/microcosm-substrate-package-smoke-$(PYTEST_TMP_KEY)",
        "PACKAGE_SMOKE_TMP ?= $(PACKAGE_SMOKE_TMP_ROOT)/run-$(PYTEST_RUN_ID)",
        "PACKAGE_SMOKE_KEEP_TMP ?= 0",
        ".DEFAULT_GOAL := help",
        "PUBLIC_TESTS ?=",
        "tests/test_package_data_contract.py",
        "tests/test_evidence_truth_floor.py",
        ".PHONY: help install venv test test-all smoke package-smoke ci standalone-export clean",
        "Microcosm public repo commands:",
        "make install             create .venv and install test extras",
        "make test                run public entry and safety tests",
        "make test-all            run full suite with pytest receipt writes blocked",
        "make smoke               validate and summarize the public smoke route",
        "make package-smoke       install local package in a fresh venv and run console cards",
        "make ci                  run test, smoke, and package-smoke",
        "make standalone-export   export a release-gated standalone tree",
        "make clean               remove local build and cache files",
        "$(PYTHON) -m venv $(VENV)",
        "$(PIP_ENV) $(VENV_PYTHON) -m pip install --upgrade pip",
        '$(PIP_ENV) $(VENV_PYTHON) -m pip install -e ".[test]"',
        "@mkdir -p $(PYTEST_TMP)/tmp $(PYTEST_TMP)/pycache",
        "PYTHONPATH=src $(PYTEST_ENV) $(VENV_PYTHON) -m pytest --basetemp=$(PYTEST_BASETEMP) $(PUBLIC_TESTS) $(PYTEST_ARGS)",
        'if [ "$(PYTEST_KEEP_TMP)" != "1" ]; then rm -rf "$(PYTEST_TMP)"; fi',
        "Note: make test-all is a broad macro-root drift-detection suite with tracked receipt writes blocked under pytest. Use make ci for the clean public verification floor.",
        "PYTHONPATH=src $(PYTEST_ENV) $(VENV_PYTHON) -m pytest --basetemp=$(PYTEST_BASETEMP) $(PYTEST_ARGS)",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core hello .",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core first-screen --card .",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core tour --card .",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core status --card .",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) scripts/served_status_smoke.py "
        "--root . --project . --out $(SMOKE_OUT)/served-status-card.json",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core authority --card",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core workingness --card",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core legibility-scorecard",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core --version",
        "$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core stripping-guard",
        '$(SMOKE_ENV) PYTHONPATH=src $(PYTHON) -m microcosm_core comprehend '
        '--first-action "where do I start with this clone?"',
        "> $(SMOKE_OUT)/first-screen-card.json",
        "> $(SMOKE_OUT)/tour-card.json",
        "> $(SMOKE_OUT)/status-card.json",
        "$(SMOKE_OUT)/served-status-card.json",
        "> $(SMOKE_OUT)/stripping-guard.json",
        "$(PYTHON) scripts/check_smoke_outputs.py --smoke-out $(SMOKE_OUT)",
        "$(PYTHON) scripts/package_install_smoke.py --source-root . --work-dir $(PACKAGE_SMOKE_TMP) --python $(PYTHON)",
        'if [ "$(PACKAGE_SMOKE_KEEP_TMP)" != "1" ]; then rm -rf "$(PACKAGE_SMOKE_TMP)"; fi',
        "ci: test smoke package-smoke",
        "PYTHONPATH=src $(VENV_PYTHON) -m microcosm_core.release_export --root . --out $(EXPORT_OUT) --force --summary",
        "rm -rf $(SMOKE_OUT) $(PYTEST_TMP_ROOT) $(PACKAGE_SMOKE_TMP_ROOT) .microcosm/test-tmp",
    ):
        assert required in text

    for target in (
        "help",
        "venv",
        "install",
        "test",
        "test-all",
        "smoke",
        "package-smoke",
        "ci",
        "standalone-export",
        "clean",
    ):
        assert re.search(rf"^{target}:", text, flags=re.MULTILINE)

    assert "--break-system-packages" not in text
    assert "PIP_DISABLE_PIP_VERSION_CHECK=1" in text
    assert "/Library/Caches/pip" not in text


def test_public_repo_makefile_smoke_target_writes_expected_artifacts() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")

    for smoke_artifact in (
        "hello.txt",
        "first-screen-card.json",
        "tour-card.json",
        "status-card.json",
        "authority-card.json",
        "workingness-card.json",
        "legibility-scorecard.json",
        "version.txt",
        "stripping-guard.json",
        "first-action.json",
    ):
        assert text.count(f"> $(SMOKE_OUT)/{smoke_artifact}") == 1
    assert text.count("--out $(SMOKE_OUT)/served-status-card.json") == 1
    assert text.count("scripts/check_smoke_outputs.py --smoke-out $(SMOKE_OUT)") == 1
    assert "Microcosm smoke receipts written to %s" not in text


def test_package_install_smoke_script_is_makefile_owned() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    script = PACKAGE_INSTALL_SMOKE.read_text(encoding="utf-8")

    assert PACKAGE_INSTALL_SMOKE.is_file()
    assert "scripts/package_install_smoke.py --source-root ." in text
    assert "PIP_DISABLE_PIP_VERSION_CHECK" in script
    assert "Microcosm package smoke: pass" in script
    assert "--no-deps" in script
    assert "first-screen" in script
    assert "tour" in script
    assert "status" in script
    assert "authority" in script
    assert "workingness" in script
    assert "legibility-scorecard" in script
    assert "release_authorized=false" in script
    assert "/Users/" in script
    assert "src/ai_workflow" in script


def test_check_smoke_outputs_prints_public_pass_summary(tmp_path: Path) -> None:
    smoke_out = tmp_path / "smoke"
    _write_valid_smoke_outputs(smoke_out)

    result = subprocess.run(
        [sys.executable, str(CHECK_SMOKE_OUTPUTS), "--smoke-out", str(smoke_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Microcosm smoke check: pass" in result.stdout
    assert f"receipts: {smoke_out}" in result.stdout
    accepted_organ_count = _accepted_organ_count()
    assert (
        f"authority: pass ({accepted_organ_count} organ authority rows, release false)"
        in result.stdout
    )
    assert (
        f"workingness: clear ({accepted_organ_count} mapped, "
        "0 missing standards, 0 missing failure modes, "
        f"{_live_workingness_import_signature()['source_body_import_exception_count']} "
        "source-body exceptions)"
        in result.stdout
    )
    assert "served status: pass (0 private path hits)" in result.stdout
    assert "first action: contract pass" in result.stdout
    assert "version: microcosm 0.1.0" in result.stdout
    assert result.stderr == ""


def test_check_smoke_outputs_fails_when_first_action_contract_is_unresolved(
    tmp_path: Path,
) -> None:
    smoke_out = tmp_path / "smoke"
    _write_valid_smoke_outputs(smoke_out)
    # The first-action block must be greenwash-resistant in its own right:
    # an unresolved contract (or a deleted check) may not ride a green smoke.
    _write_json(smoke_out / "first-action.json", {"found": False})

    result = subprocess.run(
        [sys.executable, str(CHECK_SMOKE_OUTPUTS), "--smoke-out", str(smoke_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Microcosm smoke check: fail" in result.stderr
    assert (
        "first-action.json: contract did not resolve the smoke goal"
        in result.stderr
    )


def test_check_smoke_outputs_fails_when_first_action_command_is_templated(
    tmp_path: Path,
) -> None:
    smoke_out = tmp_path / "smoke"
    _write_valid_smoke_outputs(smoke_out)
    payload = json.loads(
        (smoke_out / "first-action.json").read_text(encoding="utf-8"),
    )
    payload["first_action"]["command"] = (
        "PYTHONPATH=src python3 -m microcosm_core comprehend --organ <organ_id>"
    )
    _write_json(smoke_out / "first-action.json", payload)

    result = subprocess.run(
        [sys.executable, str(CHECK_SMOKE_OUTPUTS), "--smoke-out", str(smoke_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "first-action.json: command carries an unresolved placeholder" in result.stderr


def test_check_smoke_outputs_fails_when_workingness_is_not_clear(
    tmp_path: Path,
) -> None:
    smoke_out = tmp_path / "smoke"
    _write_valid_smoke_outputs(smoke_out)
    workingness = json.loads(
        (smoke_out / "workingness-card.json").read_text(encoding="utf-8"),
    )
    workingness["surface_counts"]["missing_standard_count"] = 1
    _write_json(smoke_out / "workingness-card.json", workingness)

    result = subprocess.run(
        [sys.executable, str(CHECK_SMOKE_OUTPUTS), "--smoke-out", str(smoke_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Microcosm smoke check: fail" in result.stderr
    assert (
        "workingness-card.json: expected surface_counts.missing_standard_count 0, got 1"
        in result.stderr
    )


def test_check_smoke_outputs_fails_when_workingness_import_signature_is_stale(
    tmp_path: Path,
) -> None:
    smoke_out = tmp_path / "smoke"
    _write_valid_smoke_outputs(smoke_out)
    workingness = json.loads(
        (smoke_out / "workingness-card.json").read_text(encoding="utf-8"),
    )
    preview = workingness["source_body_import_exception_preview"]
    preview["count"] = int(preview["count"]) + 1
    preview["status"] = "exceptions_visible"
    _write_json(smoke_out / "workingness-card.json", workingness)

    result = subprocess.run(
        [sys.executable, str(CHECK_SMOKE_OUTPUTS), "--smoke-out", str(smoke_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Microcosm smoke check: fail" in result.stderr
    assert "workingness-card.json: stale source-body import signature" in result.stderr
    assert "re-run `make smoke`" in result.stderr


def test_check_smoke_outputs_fails_when_a_card_is_empty(
    tmp_path: Path,
) -> None:
    smoke_out = tmp_path / "smoke"
    _write_valid_smoke_outputs(smoke_out)
    # A stale or partial `make smoke` can leave a 0-byte card behind; the check
    # must say so instead of emitting a cryptic "Expecting value" JSON error.
    (smoke_out / "tour-card.json").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CHECK_SMOKE_OUTPUTS), "--smoke-out", str(smoke_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Microcosm smoke check: fail" in result.stderr
    assert "tour-card.json: file is empty" in result.stderr


def test_public_repo_makefile_exposes_preflight_and_validate_targets() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")

    assert re.search(r"^check preflight:", text, flags=re.MULTILINE)
    assert re.search(r"^validate: ci doctrine-lattice-check$", text, flags=re.MULTILINE)
    assert "make check" in text
    assert "make validate" in text


def test_public_repo_makefile_ci_target_is_test_plus_smoke() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")

    assert re.search(
        r"^ci:\s+test\s+smoke\s+package-smoke$",
        text,
        flags=re.MULTILINE,
    )
    assert "test-all: install" in text
    assert not re.search(r"^ci:.*standalone-export", text, flags=re.MULTILINE)
    assert "microcosm_core.cli" not in text
