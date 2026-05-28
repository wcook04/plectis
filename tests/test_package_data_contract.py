from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib

from microcosm_core import resource_root
from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_package_data_contract_includes_first_screen_runtime_evidence() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]

    assert data_files["share/microcosm-substrate/core"] == ["core/*.json"]
    assert data_files["share/microcosm-substrate/standards"] == ["standards/*.json"]
    assert data_files["share/microcosm-substrate/receipts/runtime_shell"] == [
        "receipts/runtime_shell/*.json"
    ]
    assert data_files[
        "share/microcosm-substrate/receipts/first_wave/verifier_lab_kernel"
    ] == ["receipts/first_wave/verifier_lab_kernel/*.json"]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_kernel/"
        "exported_verifier_lab_kernel_bundle"
    ] == ["examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/*.json"]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_kernel/"
        "exported_verifier_lab_kernel_bundle/source_modules/microcosm_core/organs"
    ] == [
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/"
        "source_modules/microcosm_core/organs/*.py"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/public_reveal_walkthrough/"
        "exported_public_reveal_bundle"
    ] == [
        "examples/public_reveal_walkthrough/exported_public_reveal_bundle/*.json"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle"
    ] == [
        "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/*.json",
        "examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/*.jsonl",
    ]
    assert data_files[
        "share/microcosm-substrate/examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/source_modules/system/lib"
    ] == [
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/system/lib/*.py"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/macro_projection_import_protocol/"
        "exported_projection_import_bundle/source_modules/tools/meta/observability"
    ] == [
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "source_modules/tools/meta/observability/*.py"
    ]


def test_installed_proof_lab_cache_freshness_ignores_install_mtimes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    venv = tmp_path / "venv"
    installed_root = venv / "share/microcosm-substrate"
    receipt_path = installed_root / runtime_shell.PROOF_LAB_RECEIPT_REF
    input_root = installed_root / runtime_shell.PROOF_LAB_BUNDLE_REF
    receipt_path.parent.mkdir(parents=True)
    input_root.mkdir(parents=True)
    receipt_path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    input_file = input_root / "bundle_manifest.json"
    input_file.write_text(json.dumps({"schema_version": "fixture"}), encoding="utf-8")
    os.utime(receipt_path, (1, 1))
    os.utime(input_file, (2, 2))

    monkeypatch.setattr(resource_root.sys, "prefix", str(venv))

    freshness = runtime_shell._proof_lab_cache_freshness(installed_root, receipt_path)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "packaged_public_data"
    assert freshness["tracked_input_count"] == 1
    assert freshness["stale_input_count"] == 0
