from __future__ import annotations

import fnmatch
import importlib
import json
import os
from pathlib import Path
import tomllib

from microcosm_core import resource_root
from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = MICROCOSM_ROOT / "MANIFEST.in"
PUBLIC_DATA_SUFFIXES = {
    ".json",
    ".jsonl",
    ".lean",
    ".md",
    ".mjs",
    ".olean",
    ".py",
    ".ts",
    ".tsx",
    ".toml",
    ".trace",
    ".txt",
    ".yaml",
    ".yml",
}
PUBLIC_DATA_FILENAMES = {
    "checkpoint",
    "lean-toolchain",
    "pre-commit",
    "prepare-commit-msg",
}


def _source_relative(path: Path) -> str:
    return path.relative_to(MICROCOSM_ROOT).as_posix()


def _is_packaged_by_data_files(data_files: dict[str, list[str]], rel_path: str) -> bool:
    return any(
        fnmatch.fnmatchcase(rel_path, pattern)
        for patterns in data_files.values()
        for pattern in patterns
    )


def _expected_public_data_files(top_level: str) -> dict[str, list[str]]:
    public_root = MICROCOSM_ROOT / top_level
    public_dirs = sorted(
        {
            path.parent
            for path in public_root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.endswith(".pyc")
        }
    )
    expected: dict[str, list[str]] = {}
    for public_dir in public_dirs:
        rel_dir = _source_relative(public_dir)
        suffixes = sorted(
            {
                path.suffix
                for path in public_dir.iterdir()
                if path.is_file() and path.suffix in PUBLIC_DATA_SUFFIXES
            }
        )
        patterns = [f"{rel_dir}/*{suffix}" for suffix in suffixes]
        patterns.extend(
            f"{rel_dir}/{path.name}"
            for path in sorted(public_dir.iterdir(), key=lambda item: item.name)
            if path.is_file() and path.name in PUBLIC_DATA_FILENAMES
        )
        if patterns:
            expected[f"share/microcosm-substrate/{rel_dir}"] = patterns
    return expected


def test_source_distribution_manifest_keeps_public_repo_entry_surface() -> None:
    lines = set(MANIFEST.read_text(encoding="utf-8").splitlines())

    for required in (
        "include .gitignore",
        "include AGENTS.md",
        "include CONTRIBUTING.md",
        "include ARCHITECTURE.md",
        "include ORGANS.md",
        "include Makefile",
        "include QUICKSTART.md",
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

    assert data_files["share/microcosm-substrate"] == [
        ".gitignore",
        "AGENTS.md",
        "ANTI_PRINCIPLES.md",
        "ARCHITECTURE.md",
        "AXIOMS.md",
        "CONSTITUTION.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "MANIFEST.in",
        "Makefile",
        "ORGANS.md",
        "PRINCIPLES.md",
        "QUICKSTART.md",
        "README.md",
        "SECURITY.md",
        "bootstrap.sh",
        "pyproject.toml",
    ]
    assert data_files["share/microcosm-substrate/core"] == ["core/*.json"]
    assert data_files["share/microcosm-substrate/.github/workflows"] == [
        ".github/workflows/*.yml"
    ]
    assert data_files["share/microcosm-substrate/atlas"] == ["atlas/*.json"]
    assert data_files["share/microcosm-substrate/core/preflight_support"] == [
        "core/preflight_support/*.json"
    ]
    assert data_files["share/microcosm-substrate/src/microcosm_core/macro_tools"] == [
        "src/microcosm_core/macro_tools/*.py"
    ]
    assert data_files["share/microcosm-substrate/paper_modules"] == [
        "paper_modules/*.md"
    ]
    assert data_files["share/microcosm-substrate/scripts"] == ["scripts/*.py"]
    assert data_files["share/microcosm-substrate/skills"] == ["skills/*.md"]
    assert data_files["share/microcosm-substrate/standards"] == ["standards/*.json"]
    assert data_files["share/microcosm-substrate/receipts/acceptance"] == [
        "receipts/acceptance/*.json",
        "receipts/acceptance/pattern_assimilation_step",
    ]
    assert data_files["share/microcosm-substrate/receipts/acceptance/first_wave"] == [
        "receipts/acceptance/first_wave/*.json"
    ]
    assert data_files["share/microcosm-substrate/receipts/preflight"] == [
        "receipts/preflight/*.json"
    ]
    assert data_files["share/microcosm-substrate/receipts/runtime_shell"] == [
        "receipts/runtime_shell/*.json"
    ]
    for receipt_dir in (
        "agent_route_observability_runtime",
        "executable_doctrine_grammar",
        "mission_transaction_work_spine",
        "navigation_hologram_route_plane",
        "pattern_assimilation_step",
        "pattern_binding_contract",
        "proof_diagnostic_evidence_spine",
    ):
        assert data_files[f"share/microcosm-substrate/receipts/first_wave/{receipt_dir}"] == [
            f"receipts/first_wave/{receipt_dir}/*.json"
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
    for receipt_dir in (
        "prediction_oracle_reconciliation",
        "spatial_world_model_counterfactual_simulation_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "standards_meta_diagnostics",
        "agent_monitor_redteam_falsification_replay",
        "agent_sabotage_scheming_monitor_replay",
    ):
        assert data_files[f"share/microcosm-substrate/receipts/first_wave/{receipt_dir}"] == [
            f"receipts/first_wave/{receipt_dir}/*.json"
        ]

    for rel in (
        "examples/macro_projection_import_protocol/exported_projection_import_bundle",
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle",
        "examples/pattern_binding_contract/exported_substrate_bundle",
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle",
    ):
        assert f"share/microcosm-substrate/{rel}" in data_files


def test_package_data_contract_includes_all_public_fixture_directories() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]

    expected = _expected_public_data_files("fixtures")
    observed = {
        key: data_files.get(key)
        for key in expected
        if key.startswith("share/microcosm-substrate/fixtures/")
    }

    assert observed == expected
    assert "share/microcosm-substrate/fixtures" not in data_files


def test_package_data_contract_includes_all_public_example_directories() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]

    expected = _expected_public_data_files("examples")
    observed = {
        key: data_files.get(key)
        for key in expected
        if key.startswith("share/microcosm-substrate/examples/")
    }

    assert observed == expected
    assert "share/microcosm-substrate/examples" not in data_files


def test_package_data_contract_covers_runtime_demo_projection_dependencies() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text()
    )
    target_refs = sorted(
        {
            str(row.get("target_ref") or "")
            for row in protocol.get("copied_material", [])
            if isinstance(row, dict) and row.get("target_ref")
        }
    )

    missing_targets = [
        ref
        for ref in target_refs
        if not (MICROCOSM_ROOT / ref).is_file()
        or not _is_packaged_by_data_files(data_files, ref)
    ]

    assert missing_targets == []
    assert _is_packaged_by_data_files(
        data_files,
        "receipts/preflight/dependency_preflight.json",
    )


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
