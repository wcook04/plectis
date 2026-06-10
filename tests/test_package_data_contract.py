from __future__ import annotations

import fnmatch
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tomllib

from microcosm_core import resource_root
from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = MICROCOSM_ROOT / "MANIFEST.in"
ACCEPTANCE_PATH = MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json"
SUBSTRATE_LEDGER_PATH = MICROCOSM_ROOT / "core/substrate_substitution_ledger.json"
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
GENERATED_DATA_DIR_NAMES = {
    ".microcosm",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}


def _source_relative(path: Path) -> str:
    return path.relative_to(MICROCOSM_ROOT).as_posix()


def _committed_public_refs(top_level: str) -> set[str] | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(MICROCOSM_ROOT),
                "ls-tree",
                "-r",
                "--name-only",
                "HEAD",
                "--",
                top_level,
            ],
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def _accepted_organ_ids() -> set[str]:
    payload = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
    return {
        str(row.get("organ_id") or "")
        for row in payload.get("accepted_current_authority_organs", [])
        if isinstance(row, dict) and row.get("status") == "accepted_current_authority"
    }


def _accepted_public_roots(top_level: str) -> set[str]:
    accepted = _accepted_organ_ids()
    roots: set[str] = set()
    for organ_id in accepted:
        if top_level == "examples":
            roots.add(f"examples/{organ_id}")
        elif top_level == "fixtures":
            roots.add(f"fixtures/first_wave/{organ_id}")
            roots.add(f"fixtures/second_wave/{organ_id}")

    ledger = json.loads(SUBSTRATE_LEDGER_PATH.read_text(encoding="utf-8"))
    for row in ledger.get("organ_substrate_dispositions", []):
        if not isinstance(row, dict) or row.get("organ_id") not in accepted:
            continue
        for field in ("source_module_manifest_refs", "microcosm_target_refs"):
            for ref in row.get(field, []) or []:
                if not isinstance(ref, str) or not ref.startswith(f"{top_level}/"):
                    continue
                parts = PurePosixPath(ref).parts
                if top_level == "examples" and len(parts) >= 2:
                    roots.add("/".join(parts[:2]))
                elif top_level == "fixtures" and len(parts) >= 3:
                    roots.add("/".join(parts[:3]))
    return roots


def _is_accepted_public_ref(ref: str, roots: set[str]) -> bool:
    return any(ref == root or ref.startswith(f"{root}/") for root in roots)


def _is_packaged_by_data_files(data_files: dict[str, list[str]], rel_path: str) -> bool:
    return any(
        fnmatch.fnmatchcase(rel_path, pattern)
        for patterns in data_files.values()
        for pattern in patterns
    )


def _contains_generated_data_dir(path: Path) -> bool:
    return any(part in GENERATED_DATA_DIR_NAMES for part in path.parts)


def _contains_generated_data_part(ref: str) -> bool:
    return any(part in GENERATED_DATA_DIR_NAMES for part in PurePosixPath(ref).parts)


def _expected_public_data_files(top_level: str) -> dict[str, list[str]]:
    public_root = MICROCOSM_ROOT / top_level
    committed_refs = _committed_public_refs(top_level)
    accepted_roots = _accepted_public_roots(top_level)
    public_dirs = sorted(
        {
            (MICROCOSM_ROOT / ref).parent
            for ref in (
                committed_refs
                if committed_refs is not None
                else (
                    _source_relative(path)
                    for path in public_root.rglob("*")
                    if path.is_file()
                )
            )
            if (MICROCOSM_ROOT / ref).is_file()
            and _is_accepted_public_ref(ref, accepted_roots)
            and not _contains_generated_data_dir(
                (MICROCOSM_ROOT / ref).relative_to(public_root)
            )
            and not (MICROCOSM_ROOT / ref).name.endswith(".pyc")
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
        "include .github/PULL_REQUEST_TEMPLATE.md",
        "include AGENTS.md",
        "include AGENT_ROUTES.md",
        "include CLAUDE.md",
        "include CONTRIBUTING.md",
        "include CODEX.md",
        "include CURSOR.md",
        "include FIRST_ACTION.md",
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
        "AGENT_ROUTES.md",
        "ANTI_PRINCIPLES.md",
        "ARCHITECTURE.md",
        "AXIOMS.md",
        "CLAUDE.md",
        "CONSTITUTION.md",
        "CONTRIBUTING.md",
        "CODEX.md",
        "CURSOR.md",
        "FIRST_ACTION.md",
        "LICENSE",
        "MANIFEST.in",
        "Makefile",
        "NOTICE",
        "ORGANS.md",
        "PRINCIPLES.md",
        "PROVENANCE.md",
        "QUICKSTART.md",
        "RELEASE_DISCIPLINE.md",
        "RELEASE_REVIEW.md",
        "README.md",
        "SECURITY.md",
        "bootstrap.sh",
        "pyproject.toml",
    ]
    assert data_files["share/microcosm-substrate/core"] == ["core/*.json"]
    assert data_files["share/microcosm-substrate/.github/workflows"] == [
        ".github/workflows/*.yml"
    ]
    assert data_files["share/microcosm-substrate/.github"] == [
        ".github/PULL_REQUEST_TEMPLATE.md"
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
    # The comprehension product (join index -> first-action contracts) must ship
    # with the package: without receipts/code_lens the installed share tree has
    # no graph substrate and `comprehend` is dev-tree-only.
    assert data_files["share/microcosm-substrate/receipts/code_lens"] == [
        "receipts/code_lens/*.json"
    ]
    assert data_files["share/microcosm-substrate/receipts/code_lens/read_packs"] == [
        "receipts/code_lens/read_packs/*.json"
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


def test_provider_adapter_files_stay_thin_and_route_to_canonical_agent_contract() -> None:
    for name in ("CLAUDE.md", "CODEX.md", "CURSOR.md"):
        text = (MICROCOSM_ROOT / name).read_text(encoding="utf-8")

        assert "The canonical public agent\ncontract is `AGENTS.md`" in text
        assert "do not duplicate or override it here" in text
        assert "./bootstrap.sh --dry-run" in text
        assert "hello --reader agent" in text
        assert "does not authorize release, publication, provider calls" in text
        assert "private-root equivalence, proof correctness" in text
        assert len(text.splitlines()) <= 16


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


def test_package_data_contract_excludes_generated_runtime_state() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]

    generated_keys = [
        key for key in data_files if _contains_generated_data_part(key)
    ]
    generated_patterns = [
        pattern
        for patterns in data_files.values()
        for pattern in patterns
        if _contains_generated_data_part(pattern)
    ]

    assert generated_keys == []
    assert generated_patterns == []


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
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/source_modules/system/control/orchestration.py",
    )
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


def test_resource_root_follows_prefix_install_module_layout(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prefix = tmp_path / "install-prefix"
    site_package = prefix / "lib/python3.13/site-packages/microcosm_core"
    installed_root = prefix / "share/microcosm-substrate"
    module_file = site_package / "resource_root.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# installed module placeholder\n", encoding="utf-8")
    for rel in (
        "standards/std_microcosm_first_screen_composition_root.json",
        "core/organ_evidence_classes.json",
        "core/organ_registry.json",
    ):
        target = installed_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"schema_version": "fixture"}), encoding="utf-8")

    monkeypatch.setattr(resource_root.sys, "prefix", str(tmp_path / "python-prefix"))
    monkeypatch.setattr(resource_root, "__file__", str(module_file))

    assert resource_root.installed_microcosm_root() == installed_root
    assert resource_root.microcosm_root() == installed_root
