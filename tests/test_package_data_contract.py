from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import tomllib

from microcosm_core import resource_root
from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = MICROCOSM_ROOT / "MANIFEST.in"


def test_source_distribution_manifest_keeps_public_repo_entry_surface() -> None:
    lines = set(MANIFEST.read_text(encoding="utf-8").splitlines())

    for required in (
        "include AGENTS.md",
        "include CONTRIBUTING.md",
        "include Makefile",
        "include SECURITY.md",
        "include bootstrap.sh",
        "graft .github/workflows",
        "graft atlas",
        "graft fixtures",
        "graft paper_modules",
        "graft scripts",
        "graft skills",
        "graft tests",
    ):
        assert required in lines

    for forbidden in (
        "prune .microcosm",
        "prune .pytest_cache",
        "prune .venv",
        "prune build",
        "prune dist",
        "prune examples/*/.microcosm",
        "prune examples/*/*/.microcosm",
        "prune microcosm-substrate",
        "global-exclude *.py[cod]",
    ):
        assert forbidden in lines


def test_package_data_contract_includes_first_screen_runtime_evidence() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]

    assert data_files["share/microcosm-substrate/core"] == ["core/*.json"]
    assert data_files["share/microcosm-substrate/standards"] == ["standards/*.json"]
    assert data_files["share/microcosm-substrate/receipts/runtime_shell"] == [
        "receipts/runtime_shell/*.json"
    ]
    for receipt_dir in (
        "corpus_readiness_mathlib_absence_gate",
        "formal_evidence_cell_anchor_resolver",
        "formal_math_lean_proof_witness",
        "formal_math_premise_retrieval",
        "formal_math_readiness_gate",
        "formal_math_verifier_trace_repair_loop",
        "lean_std_premise_index",
        "ring2_premise_retrieval_precision_recall_harness",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "verifier_lab_execution_spine",
    ):
        assert data_files[f"share/microcosm-substrate/receipts/first_wave/{receipt_dir}"] == [
            f"receipts/first_wave/{receipt_dir}/*.json"
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
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/*.json"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project/*.lean"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project/"
        "MicrocosmProofWitness"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/lake_project/"
        "MicrocosmProofWitness/*.lean"
    ]
    assert data_files[
        "share/microcosm-substrate/examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/source_modules/"
        "microcosm_core/organs"
    ] == [
        "examples/verifier_lab_execution_spine/"
        "exported_verifier_lab_execution_spine_bundle/source_modules/"
        "microcosm_core/organs/*.py"
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


def test_cli_proof_lab_defaults_follow_installed_data_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    venv = tmp_path / "venv"
    installed_root = venv / "share/microcosm-substrate"
    receipt_path = installed_root / runtime_shell.PROOF_LAB_RECEIPT_REF
    input_root = installed_root / runtime_shell.PROOF_LAB_BUNDLE_REF

    for rel in (
        "standards/std_microcosm_first_screen_composition_root.json",
        "core/organ_evidence_classes.json",
        "core/organ_registry.json",
    ):
        target = installed_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"schema_version": "fixture"}), encoding="utf-8")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    input_root.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    (input_root / "proof_lab_route.json").write_text(
        json.dumps({"route_id": "fixture"}),
        encoding="utf-8",
    )

    real_has_public_data = resource_root._has_public_data
    installed_root_resolved = installed_root.resolve(strict=False)

    def fake_has_public_data(root: Path) -> bool:
        root_resolved = Path(root).resolve(strict=False)
        if root_resolved == installed_root_resolved:
            return real_has_public_data(root)
        return False

    cli_module = importlib.import_module("microcosm_core.cli")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(resource_root.sys, "prefix", str(venv))
            patch.setattr(resource_root, "_has_public_data", fake_has_public_data)

            reloaded = importlib.reload(cli_module)

            assert reloaded.MICROCOSM_ROOT == installed_root
            assert reloaded.DEFAULT_PROOF_LAB_INPUT == input_root
            assert reloaded._canonical_proof_lab_receipt_path() == receipt_path
            freshness = reloaded._proof_lab_cache_freshness(
                str(input_root),
                receipt_path,
            )
            assert freshness["status"] == "current"
            assert freshness["input_status"] == "packaged_public_data"
            assert freshness["stale_input_count"] == 0
    finally:
        importlib.reload(cli_module)
